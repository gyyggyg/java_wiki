# RabbitMQ 分析器 - 详细流程分析

## 一、整体流程

脚本分四个步骤执行：

| 步骤 | 名称 | 处理方式 | 作用 |
| --- | --- | --- | --- |
| Step 1 | 确定性查询 | Neo4j Cypher | 找到所有 RabbitMQ 相关的节点 |
| Step 2 | LLM 提取 | 调用 LLM | 从节点的源码中提取具体配置值 |
| Step 3 | 确定性匹配 | 规则匹配 | 根据配置值把生产者和消费者串成链路 |
| Step 4 | 报告生成 | 模板渲染 | 输出 Markdown 文档 |

---

## 二、Step 1：确定性查询（找节点）

### 2.1 查询的内容

从 Neo4j 图数据库中查询 6 类信息：

| 查询目标 | 节点类型 | 查询条件 | 返回的属性 |
| --- | --- | --- | --- |
| 枚举常量 | Enum + EnumConstant | 枚举名含 Queue/MQ/Message | enum_class, constant_name, source_code |
| 消费者 | Class + Method | 注解含 @RabbitListener 或 @RabbitHandler | class_name, method_name, source_code, SE_What/Why/How |
| 生产者 | Class + Field | 字段类型含 AmqpTemplate 或 RabbitTemplate | class_name, source_code, SE_What |
| 队列配置 | Method | @Bean + 返回类型含 Queue | method_name, source_code, SE_What |
| 交换机配置 | Method | @Bean + 返回类型含 Exchange | method_name, source_code, SE_What |
| 绑定配置 | Method | @Bean + 返回类型含 Binding | method_name, source_code, SE_What |

### 2.2 枚举预处理

查到枚举后，用正则提取构造函数参数，建立映射表：

> 输入：QUEUE_ORDER_CANCEL("mall.order.direct", "mall.order.cancel", "mall.order.cancel")
>
> 输出映射：QueueEnum.QUEUE_ORDER_CANCEL → { exchange: "mall.order.direct", queue: "mall.order.cancel", routing_key: "mall.order.cancel" }

这个映射表在 Step 2 解析枚举引用时会用到。

### 2.3 Step 1 的结果

执行完 Step 1 后，脚本得到了：
- 一批消费者节点（知道类名、方法名、源码）
- 一批生产者节点（知道类名、源码）
- 一批队列/交换机/绑定配置节点（知道方法名、源码）
- 一个枚举映射表

但是，此时还不知道：
- 消费者监听的队列名是什么
- 生产者发送到哪个交换机、用什么路由键
- 队列/交换机/绑定的具体配置值

这些信息藏在源码里，需要 Step 2 来提取。

---

## 三、Step 2：LLM 提取（从源码中提取配置值）

### 3.1 为什么需要 LLM

源码里的写法多种多样：

| 写法 | 示例 |
| --- | --- |
| 直接写字符串 | queues = "mall.order.cancel" |
| 用枚举 | queues = QueueEnum.ORDER.getName() |
| 用常量 | queues = QueueConstants.ORDER |
| 用配置 | queues = "${mq.queue.name}" |

无法用固定的正则覆盖所有情况，所以用 LLM 来"读懂"代码。

### 3.2 LLM 的工作方式

对每个组件，脚本构造一个 Prompt，把源码发给 LLM，让它返回 JSON。

**消费者的 Prompt 示例：**

```
你是一个 Java Spring AMQP 代码分析专家。

任务：分析以下 RabbitMQ 消费者代码，提取监听信息。

类名：CancelOrderReceiver
方法名：handle

源码：
@RabbitListener(queues = "mall.order.cancel")
public class CancelOrderReceiver {
    @RabbitHandler
    public void handle(Long orderId) { ... }
}

输出 JSON：
{ "queue_name": "队列名", "queue_expression": "原始表达式" }
```

**LLM 返回：**

```
{ "queue_name": "mall.order.cancel", "queue_expression": "mall.order.cancel" }
```

### 3.3 各组件提取的字段

| 组件 | LLM 提取的字段 |
| --- | --- |
| 消费者 | queue_name, queue_expression |
| 生产者 | exchange, exchange_expression, routing_key, routing_key_expression |
| 队列配置 | queue_name, queue_expression, dlx.exchange, dlx.routing_key, ttl_ms |
| 交换机配置 | exchange_name, exchange_expression, exchange_type |
| 绑定配置 | queue_name, queue_bean, exchange_name, exchange_bean, routing_key |

### 3.4 LLM 返回后的处理

脚本拿到 LLM 返回的 JSON 后，调用 _resolve_value 方法做进一步解析：

1. 如果值含有 "()"（如 QueueEnum.ORDER.getName()），说明是枚举引用，去查枚举映射表
2. 否则直接使用 LLM 返回的值

### 3.5 Bean 引用解析

绑定配置比较特殊，LLM 可能返回 queue_bean = "orderQueue"，这是方法参数名。

脚本建立映射：@Bean 方法名 → 队列名/交换机名

然后根据 queue_bean 查表，得到实际的队列名。

### 3.6 Step 2 的结果

执行完 Step 2 后，每个组件都有了具体的配置值：
- 消费者：queue_name = "mall.order.cancel"
- 生产者：exchange = "mall.order.direct.ttl", routing_key = "mall.order.cancel.ttl"
- 队列配置：queue_name = "mall.order.cancel.ttl", dlx_exchange = "mall.order.direct"
- 交换机配置：exchange_name = "mall.order.direct", exchange_type = "direct"
- 绑定配置：queue_name = "mall.order.cancel", exchange_name = "mall.order.direct", routing_key = "mall.order.cancel"

---

## 四、Step 3：确定性匹配（串链路）

### 4.1 匹配逻辑

有了具体的配置值，就可以根据 RabbitMQ 的路由规则把生产者和消费者串起来。

脚本遍历所有 (生产者, 消费者) 组合，尝试两种匹配：

**场景 1：直接匹配**

> 生产者发到的交换机 == 绑定的交换机
> 且 绑定的队列 == 消费者监听的队列
> 且 路由键匹配（根据交换机类型判断）

**场景 2：TTL + 死信匹配**

> 生产者发到的交换机 == TTL 队列绑定的交换机
> 且 TTL 队列的死信交换机 == 目标队列绑定的交换机
> 且 目标队列 == 消费者监听的队列

### 4.2 路由键匹配规则

根据交换机类型不同，匹配规则不同：

| 交换机类型 | 匹配规则 |
| --- | --- |
| direct | 路由键必须精确相等 |
| topic | 支持通配符（* 匹配一个词，# 匹配多个词） |
| fanout | 忽略路由键，直接匹配 |
| headers | 宽松匹配 |

### 4.3 Step 3 的结果

匹配成功后，得到一条完整的链路：

```
CancelOrderSender
    → mall.order.direct.ttl（交换机）
    → mall.order.cancel.ttl（TTL 队列）
    → mall.order.direct（死信交换机，TTL 到期转发）
    → mall.order.cancel（目标队列）
    → CancelOrderReceiver.handle（消费者）
```

---

## 五、Step 4：报告生成

把 Step 3 匹配出的链路，加上各组件的详细信息，渲染成 Markdown 文档。

报告内容包括：
- 概览（组件数量统计）
- 消息流转链路（流程图 + 文字描述）
- 组件详情（消费者、生产者、队列、交换机、绑定）

---

## 六、总结

| 步骤 | 输入 | 输出 | 处理方式 |
| --- | --- | --- | --- |
| Step 1 | Neo4j 图数据库 | 组件节点 + 源码 | 确定性 Cypher 查询 |
| Step 2 | 组件源码 | 具体配置值（队列名、交换机名等） | LLM 提取 + 枚举查表 |
| Step 3 | 配置值 | 完整链路 | 确定性规则匹配 |
| Step 4 | 链路 + 组件信息 | Markdown 文档 | 模板渲染 |

核心思想：
- Step 1 和 Step 3 是确定性的（基于规范和协议）
- Step 2 是不确定性的（需要 LLM 理解多样的代码写法）
- LLM 的作用就是"从源码中提取配置值"，提取完成后，后续的链路匹配完全是确定性的
