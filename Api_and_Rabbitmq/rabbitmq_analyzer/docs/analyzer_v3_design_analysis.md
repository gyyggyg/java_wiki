# RabbitMQ 分析器 v3 设计分析

本文档分析 analyzer_v3.py 的设计逻辑：哪些用确定性规则，哪些用 LLM。

---

## 一、整体架构

| 步骤 | 处理方式 | 作用 |
| --- | --- | --- |
| Step 1 | 确定性规则 | 从 Neo4j 查询 RabbitMQ 组件 |
| Step 2 | LLM | 从源码提取具体值（队列名、交换机名等） |
| Step 3 | 确定性规则 | 基于 RabbitMQ 路由规则匹配链路 |
| Step 4 | 模板渲染 | 生成 Markdown 报告 |

---

## 二、确定性规则处理的内容

### 2.1 组件发现

| 组件类型 | 查询规则 |
| --- | --- |
| 消费者 | 方法/类带有 @RabbitListener 或 @RabbitHandler |
| 生产者 | 类中注入了 AmqpTemplate 或 RabbitTemplate |
| 队列配置 | @Bean 方法返回 Queue 类型 |
| 交换机配置 | @Bean 方法返回 Exchange 类型 |
| 绑定配置 | @Bean 方法返回 Binding 类型 |

### 2.2 枚举预查询

查询项目中的消息队列枚举，建立映射表：

> QueueEnum.ORDER_CANCEL → { exchange, queue, routingKey }

### 2.3 链路匹配

基于 RabbitMQ 路由规则匹配 Producer → Consumer 链路：
- direct：路由键精确匹配
- topic：通配符匹配
- fanout：广播
- 死信转发：TTL 队列 → DLX → 目标队列

### 2.4 Bean 引用解析

绑定中的参数名对应 @Bean 方法名，查表获取队列/交换机名。

---

## 三、LLM 处理的内容

### 3.1 为什么需要 LLM

Step 1 通过查询注解，找到了 RabbitMQ 组件。比如查到了一个消费者类 CancelOrderReceiver。

但是，要生成完整的文档，光知道"这是一个消费者"还不够。我们还需要知道：这个消费者监听的是哪个队列？

这个信息写在源码里。问题是，开发者写代码的方式五花八门：

写法一：直接写字符串
```java
@RabbitListener(queues = "mall.order.cancel")
```

写法二：用枚举
```java
@RabbitListener(queues = QueueEnum.ORDER_CANCEL.getName())
```

写法三：用常量
```java
@RabbitListener(queues = QueueConstants.ORDER_QUEUE)
```

写法四：用配置
```java
@RabbitListener(queues = "${rabbitmq.queue.order}")
```

如果用正则表达式来提取，需要为每种写法写不同的规则，很麻烦，也容易漏掉新的写法。

所以，这里用 LLM 来做。LLM 能"读懂"代码，不管是哪种写法，它都能理解并提取出需要的信息。

### 3.2 LLM 具体做了什么

简单说：脚本把源码发给 LLM，告诉它要提取什么，LLM 返回一个 JSON。

下面用消费者举例，完整展示这个过程。

---

**第一步：脚本准备输入**

脚本从 Neo4j 查到了消费者的源码：

```java
@Component
@RabbitListener(queues = "mall.order.cancel")
public class CancelOrderReceiver {
    @Autowired
    private OmsPortalOrderService portalOrderService;

    @RabbitHandler
    public void handle(Long orderId) {
        portalOrderService.cancelOrder(orderId);
    }
}
```

**第二步：脚本构造 Prompt 发给 LLM**

脚本把源码塞进一个 Prompt 模板里，发给 LLM：

```
你是一个 Java Spring AMQP 代码分析专家。

任务：分析以下 RabbitMQ 消费者代码，提取监听信息。

类名：CancelOrderReceiver
方法名：handle

源码：
@Component
@RabbitListener(queues = "mall.order.cancel")
public class CancelOrderReceiver {
    @Autowired
    private OmsPortalOrderService portalOrderService;

    @RabbitHandler
    public void handle(Long orderId) {
        portalOrderService.cancelOrder(orderId);
    }
}

请从代码中提取消费者监听的队列名。

输出 JSON 格式：
{
    "queue_name": "解析出的队列名称，如果无法确定则为 null",
    "queue_expression": "原始表达式（如果是枚举或变量引用）"
}
```

**第三步：LLM 分析源码**

LLM 收到 Prompt 后，阅读源码。

它看到 `@RabbitListener(queues = "mall.order.cancel")` 这行代码。

它知道：
- @RabbitListener 是 Spring AMQP 的消费者注解
- queues 参数指定监听的队列
- 这里 queues 的值是字符串 "mall.order.cancel"

**第四步：LLM 返回 JSON**

LLM 把提取的信息组织成 JSON 返回：

```json
{
    "queue_name": "mall.order.cancel",
    "queue_expression": "mall.order.cancel"
}
```

**第五步：脚本使用这个值**

脚本拿到 `queue_name = "mall.order.cancel"`，就知道这个消费者监听的是 mall.order.cancel 队列。

后续在 Step 3 链路匹配时，就可以把发送到 mall.order.cancel 队列的生产者和这个消费者关联起来。

---

### 3.3 其他组件的处理方式

同样的逻辑，应用到其他组件：

**生产者**

源码里有：
```java
amqpTemplate.convertAndSend("mall.order.direct.ttl", "mall.order.cancel.ttl", orderId, ...);
```

LLM 提取出：
- exchange = mall.order.direct.ttl（第一个参数是交换机）
- routing_key = mall.order.cancel.ttl（第二个参数是路由键）

**队列配置**

源码里有：
```java
return QueueBuilder.durable("mall.order.cancel.ttl")
        .withArgument("x-dead-letter-exchange", "mall.order.direct")
        .withArgument("x-dead-letter-routing-key", "mall.order.cancel")
        .build();
```

LLM 提取出：
- queue_name = mall.order.cancel.ttl（durable 的参数是队列名）
- dlx.exchange = mall.order.direct（x-dead-letter-exchange 是死信交换机）
- dlx.routing_key = mall.order.cancel（x-dead-letter-routing-key 是死信路由键）

**交换机配置**

源码里有：
```java
return new DirectExchange("mall.order.direct");
```

LLM 提取出：
- exchange_name = mall.order.direct
- exchange_type = direct（从 DirectExchange 类名推断）

**绑定配置**

源码里有：
```java
public Binding orderBinding(Queue orderQueue, DirectExchange orderDirect) {
    return BindingBuilder.bind(orderQueue).to(orderDirect).with("mall.order.cancel");
}
```

LLM 提取出：
- queue_bean = orderQueue（方法参数名，后续查表得到实际队列名）
- exchange_bean = orderDirect（方法参数名，后续查表得到实际交换机名）
- routing_key = mall.order.cancel（with 的参数是路由键）

### 3.4 枚举引用的特殊处理

如果源码里用的是枚举：

```java
@RabbitListener(queues = QueueEnum.ORDER_CANCEL.getName())
```

LLM 无法直接知道 QueueEnum.ORDER_CANCEL.getName() 返回什么值。

它只能返回：
```json
{
    "queue_name": null,
    "queue_expression": "QueueEnum.ORDER_CANCEL.getName()"
}
```

脚本拿到 queue_expression 后，发现里面有 `QueueEnum.ORDER_CANCEL`。

脚本在 Step 1 已经预先查询了项目里所有的枚举，建立了映射表：
> QueueEnum.ORDER_CANCEL → { queue: "mall.order.cancel", ... }

查表后，得到实际的队列名 mall.order.cancel。

---

## 四、总结

| 任务 | 处理方式 |
| --- | --- |
| 发现 RabbitMQ 组件 | 确定性规则（查注解） |
| 提取队列名、交换机名、路由键 | LLM 阅读源码，输出 JSON |
| 解析枚举引用 | LLM 提取表达式 + 查枚举映射表 |
| 匹配消息链路 | 确定性规则（RabbitMQ 路由协议） |

一句话总结：LLM 在这里的作用就是"看代码，把字符串值挑出来"。
