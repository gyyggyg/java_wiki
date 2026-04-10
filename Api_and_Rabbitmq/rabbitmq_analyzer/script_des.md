# RabbitMQ Flow Analyzer v3 完整解析

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RabbitMQ Flow Analyzer                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│   │   Step 1     │    │   Step 2     │    │   Step 3     │         │
│   │  确定性查询   │ →  │  LLM 提取    │ →  │  确定性匹配   │         │
│   └──────────────┘    └──────────────┘    └──────────────┘         │
│         ↓                   ↓                   ↓                   │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│   │  Neo4j 图库  │    │  GPT-4.1    │    │  规则引擎     │         │
│   │  Cypher查询  │    │  结构化输出  │    │  链路匹配     │         │
│   └──────────────┘    └──────────────┘    └──────────────┘         │
│                                                                     │
│                              ↓                                      │
│                    ┌──────────────────┐                            │
│                    │   Step 4         │                            │
│                    │   生成报告       │                            │
│                    │   (Markdown)     │                            │
│                    └──────────────────┘                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 为什么这样设计？

| 步骤 | 用什么 | 为什么 |
|------|--------|--------|
| Step 1 | Cypher 查询 | **确定性**：基于 Spring AMQP 标准注解，查出来的一定是 RabbitMQ 组件 |
| Step 2 | LLM | **灵活性**：代码写法多样（枚举、常量、SpEL），用 LLM 理解语义 |  
| Step 3 | 规则匹配 | **确定性**：RabbitMQ 路由规则是固定的，不需要 LLM 猜 |

**核心思想：能确定的用规则，不能确定的用 LLM。**

---

## 二、数据模型

### RabbitMQ 消息流转模型

```
┌──────────┐     ┌──────────┐     ┌─────────┐     ┌─────────┐     ┌──────────┐
│ Producer │ ──► │ Exchange │ ──► │ Binding │ ──► │  Queue  │ ──► │ Consumer │
└──────────┘     └──────────┘     └─────────┘     └─────────┘     └──────────┘
     │                │                │               │               │
     │                │                │               │               │
   发消息          路由器           路由规则         消息缓冲         收消息
     │                │                │               │               │
     ▼                ▼                ▼               ▼               ▼
┌──────────┐     ┌──────────┐     ┌─────────┐     ┌─────────┐     ┌──────────┐
│ exchange │     │  name    │     │exchange │     │  name   │     │  queue   │
│routing_key│    │  type    │     │ queue   │     │  dlx    │     │  class   │
└──────────┘     └──────────┘     │rout_key │     │  ttl    │     │  method  │
                                  └─────────┘     └─────────┘     └──────────┘
```

### 对应的数据结构

```python
# 代码位置：第 242-292 行

@dataclass
class Producer:
    class_name: str              # 哪个类发的消息
    exchange: Optional[str]      # 发到哪个交换机
    routing_key: Optional[str]   # 用什么路由键

@dataclass
class Consumer:
    class_name: str              # 哪个类收的消息
    method_name: str             # 哪个方法处理
    queue_name: Optional[str]    # 监听哪个队列
    payload_type: str            # 消息体类型

@dataclass
class ExchangeConfig:
    exchange_name: Optional[str] # 交换机名称
    exchange_type: str           # direct/topic/fanout/headers

@dataclass
class QueueConfig:
    queue_name: Optional[str]    # 队列名称
    dlx_exchange: Optional[str]  # 死信交换机（延迟消息用）
    dlx_routing_key: Optional[str]
    ttl_ms: Optional[int]        # 消息存活时间

@dataclass
class BindingConfig:
    queue_name: Optional[str]    # 绑定的队列
    exchange_name: Optional[str] # 绑定的交换机
    routing_key: Optional[str]   # 路由键
```

### 为什么要分开存？

因为在 Java 代码中，它们**分散在不同地方定义**：

```
项目结构：
├── config/
│   └── RabbitMQConfig.java      ← Exchange, Queue, Binding 在这里 (@Bean)
├── service/
│   └── OrderService.java        ← Producer 在这里 (AmqpTemplate.send)
└── listener/
    └── OrderListener.java       ← Consumer 在这里 (@RabbitListener)
```

---

## 三、Step 1 - 确定性查询

### 查询流程图

```
                         Neo4j 图数据库
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  查询枚举常量  │    │  查询消费者   │    │  查询生产者   │
│ (QueueEnum等) │    │(@RabbitListener)│   │(AmqpTemplate) │
└───────────────┘    └───────────────┘    └───────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ enum_values   │    │  consumers    │    │  producers    │
│   字典缓存    │    │    列表       │    │    列表       │
└───────────────┘    └───────────────┘    └───────────────┘

        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  查询队列配置  │    │ 查询交换机配置 │    │  查询绑定配置  │
│ (@Bean Queue) │    │(@Bean Exchange)│    │ (@Bean Binding)│
└───────────────┘    └───────────────┘    └───────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│    queues     │    │   exchanges   │    │   bindings    │
│     列表      │    │     列表      │    │     列表      │
└───────────────┘    └───────────────┘    └───────────────┘
```

### 各查询的 Cypher 语句

#### 1. 查询枚举常量（第 352-374 行）

**目的**：很多项目把队列名、交换机名定义在枚举里，先缓存起来方便后续解析。

```cypher
MATCH (e:Enum)-[:DECLARES]->(ec:EnumConstant)
WHERE e.name CONTAINS 'Queue' OR e.name CONTAINS 'MQ' OR e.name CONTAINS 'Message'
   OR ec.source_code CONTAINS 'exchange' OR ec.source_code CONTAINS 'queue'
RETURN e.name as enum_class,
       ec.name as constant_name,
       ec.source_code as source_code
```

**查询逻辑**：
```
找枚举类 → 名字包含 Queue/MQ/Message
        → 或者源码包含 exchange/queue
```

**解析结果存储**：
```python
# 假设枚举定义是: ORDER_CANCEL("mall.order.direct", "mall.order.cancel", "mall.order.cancel")
self.enum_values["QueueEnum.ORDER_CANCEL"] = {
    'exchange': "mall.order.direct",
    'queue': "mall.order.cancel",
    'routing_key': "mall.order.cancel"
}
```

#### 2. 查询消费者（第 430-464 行）

```cypher
MATCH (c:Class)-[:DECLARES]->(m:Method)
WHERE m.modifiers CONTAINS '@RabbitHandler'
   OR m.modifiers CONTAINS '@RabbitListener'
   OR c.modifiers CONTAINS '@RabbitListener'
RETURN c.name, c.source_code, m.name, m.source_code, m.parameters, ...
```

**查询逻辑**：
```
找方法 → 有 @RabbitHandler 注解
      → 或有 @RabbitListener 注解
      → 或所属类有 @RabbitListener 注解
```

#### 3. 查询生产者（第 466-499 行）

```cypher
MATCH (c:Class)-[:DECLARES]->(f:Field)
WHERE f.type CONTAINS 'AmqpTemplate' OR f.type CONTAINS 'RabbitTemplate'
RETURN DISTINCT c.name, c.source_code, ...
```

**查询逻辑**：
```
找类 → 有 AmqpTemplate 或 RabbitTemplate 类型的字段
     → 说明这个类可以发消息
```

#### 4. 查询配置（第 501-553 行）

```cypher
-- 队列
MATCH (c:Class)-[:DECLARES]->(m:Method)
WHERE m.modifiers CONTAINS '@Bean'
  AND m.return_type CONTAINS 'Queue'
  AND NOT m.return_type CONTAINS 'Binding'

-- 交换机
WHERE m.modifiers CONTAINS '@Bean'
  AND m.return_type CONTAINS 'Exchange'

-- 绑定
WHERE m.modifiers CONTAINS '@Bean'
  AND m.return_type CONTAINS 'Binding'
```

**查询逻辑**：
```
找 @Bean 方法 → 返回 Queue/Exchange/Binding 类型
```

---

## 四、Step 2 - LLM 提取
**LLM 的核心任务 = 从代码中"读懂"队列名/交换机名/路由键是什么**

### LLM 提取流程

```
┌─────────────────────────────────────────────────────────────────┐
│                        对每个组件                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐     │
│  │  组件源码   │  +   │ Prompt模板  │  →   │  LLM 调用   │     │
│  │ source_code │      │  (角色+任务) │      │  GPT-4.1等   │     │
│  └─────────────┘      └─────────────┘      └─────────────┘     │
│                                                   │             │
│                                                   ▼             │
│                                            ┌─────────────┐     │
│                                            │  JSON 输出  │     │
│                                            │ {queue_name │     │
│                                            │  exchange   │     │
│                                            │  routing_key}│    │
│                                            └─────────────┘     │
│                                                   │             │
│                                                   ▼             │
│                                            ┌─────────────┐     │
│                                            │ 枚举值解析  │     │
│                                            │_resolve_value│    │
│                                            └─────────────┘     │
│                                                   │             │
│                                                   ▼             │
│                                            ┌─────────────┐     │
│                                            │  最终值存储  │     │
│                                            │ consumer.   │     │
│                                            │ queue_name  │     │
│                                            └─────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 为什么需要 LLM？

因为代码写法太多样：

```java
// 写法1: 硬编码字符串
@RabbitListener(queues = "mall.order.cancel")

// 写法2: 常量引用
@RabbitListener(queues = QueueConstants.ORDER_CANCEL)

// 写法3: 枚举方法调用
@RabbitListener(queues = QueueEnum.ORDER_CANCEL.getName())

// 写法4: 配置占位符
@RabbitListener(queues = "${rabbitmq.queue.order}")

// 写法5: SpEL 表达式
@RabbitListener(queues = "#{config.orderQueue}")

// 写法6: @QueueBinding 声明式
@RabbitListener(bindings = @QueueBinding(
    value = @Queue("mall.order.cancel"),
    exchange = @Exchange("mall.order.direct"),
    key = "mall.order.cancel"
))
```

**用正则写死根本覆盖不全，所以交给 LLM 理解。**

### Prompt 模板结构（以 Consumer 为例）

```
┌────────────────────────────────────────────────────────┐
│  角色设定                                               │
│  "你是一个 Java Spring AMQP 代码分析专家"               │
├────────────────────────────────────────────────────────┤
│  任务描述                                               │
│  "分析以下 RabbitMQ 消费者代码，提取监听信息"           │
├────────────────────────────────────────────────────────┤
│  输入数据                                               │
│  - 类名: {class_name}                                  │
│  - 方法名: {method_name}                               │
│  - 源码: {source_code}                                 │
├────────────────────────────────────────────────────────┤
│  分析要求                                               │
│  - 队列可能是硬编码、常量、枚举、配置占位符...          │
│  - 请尽可能解析出实际的队列名称                         │
├────────────────────────────────────────────────────────┤
│  输出格式                                               │
│  {                                                     │
│    "queue_name": "解析出的队列名称",                   │
│    "queue_expression": "原始表达式",                   │
│    "binding_info": { exchange, routing_key } | null   │
│  }                                                     │
└────────────────────────────────────────────────────────┘
```

### 枚举值解析逻辑（第 376-428 行）

```
LLM 返回: queue_expression = "QueueEnum.ORDER_CANCEL.getName()"
                                    │
                                    ▼
                        ┌─────────────────────┐
                        │  正则匹配提取       │
                        │  enum_class: QueueEnum│
                        │  constant: ORDER_CANCEL│
                        │  getter: getName     │
                        └─────────────────────┘
                                    │
                                    ▼
                        ┌─────────────────────┐
                        │  查找缓存           │
                        │  enum_values[       │
                        │   "QueueEnum.       │
                        │    ORDER_CANCEL"    │
                        │  ]                  │
                        └─────────────────────┘
                                    │
                                    ▼
                        ┌─────────────────────┐
                        │  根据 getter 返回值  │
                        │  getName → queue    │
                        │  getExchange → exchange│
                        │  getRoutingKey → routing_key│
                        └─────────────────────┘
                                    │
                                    ▼
                            "mall.order.cancel"
```

**代码实现**：

```python
def _resolve_enum_ref(self, ref: str) -> Optional[str]:
    # 匹配: EnumClass.CONSTANT.getXxx()
    match = re.search(r'(\w+)\.(\w+)\.(get\w+)\(\)', ref)
    if match:
        enum_class = match.group(1)   # QueueEnum
        constant = match.group(2)      # ORDER_CANCEL
        getter = match.group(3).lower() # getname

        key = f"{enum_class}.{constant}"
        if key in self.enum_values:
            vals = self.enum_values[key]
            if 'exchange' in getter:
                return vals.get('exchange')
            elif 'name' in getter or 'queue' in getter:
                return vals.get('queue')
            elif 'route' in getter or 'key' in getter:
                return vals.get('routing_key')
    return None
```

---

## 五、Step 3 - 确定性链路匹配

**核心问题：哪个 Producer 的消息会被哪个 Consumer 收到？**

### 匹配思路

Producer 和 Consumer 之间没有直接关系，需要通过 Binding 作为"桥梁"来匹配：

```
Producer 知道:  exchange + routing_key   （我要发到哪）
Consumer 知道:  queue_name               （我要从哪收）
Binding 知道:   exchange + queue + routing_key  （谁连着谁）

匹配逻辑：找一个 Binding，使得
  - Binding.exchange == Producer.exchange
  - Binding.queue == Consumer.queue
  - Binding.routing_key 匹配 Producer.routing_key
```

### 具体例子

假设系统里有这些组件：

```
Producers（发消息的）:
  ┌─────────────────────────────────────────────────────┐
  │ P1: OrderService                                    │
  │     exchange = "mall.order.direct"                  │
  │     routing_key = "mall.order.cancel"               │
  ├─────────────────────────────────────────────────────┤
  │ P2: PayService                                      │
  │     exchange = "mall.pay.direct"                    │
  │     routing_key = "mall.pay.success"                │
  └─────────────────────────────────────────────────────┘

Consumers（收消息的）:
  ┌─────────────────────────────────────────────────────┐
  │ C1: OrderCancelListener                             │
  │     queue_name = "mall.order.cancel"                │
  ├─────────────────────────────────────────────────────┤
  │ C2: PaySuccessListener                              │
  │     queue_name = "mall.pay.success"                 │
  └─────────────────────────────────────────────────────┘

Bindings（连接关系）:
  ┌─────────────────────────────────────────────────────┐
  │ B1: exchange="mall.order.direct"                    │
  │     queue="mall.order.cancel"                       │
  │     routing_key="mall.order.cancel"                 │
  ├─────────────────────────────────────────────────────┤
  │ B2: exchange="mall.pay.direct"                      │
  │     queue="mall.pay.success"                        │
  │     routing_key="mall.pay.success"                  │
  └─────────────────────────────────────────────────────┘
```

### 双重循环匹配过程

穷举所有 Producer × Consumer 组合，逐个检查：

```
第1轮: P1(OrderService) × C1(OrderCancelListener)
       │
       ├─ 检查 B1:
       │    P1.exchange == B1.exchange?  ✓ (mall.order.direct)
       │    B1.queue == C1.queue?        ✓ (mall.order.cancel)
       │    routing_key 匹配?            ✓
       │    → 匹配成功！记录链路
       │
       └─ 结果: OrderService → mall.order.direct → mall.order.cancel → OrderCancelListener

第2轮: P1(OrderService) × C2(PaySuccessListener)
       │
       ├─ 检查 B1:
       │    P1.exchange == B1.exchange?  ✓
       │    B1.queue == C2.queue?        ✗ (mall.order.cancel ≠ mall.pay.success)
       │    → 不匹配
       │
       ├─ 检查 B2:
       │    P1.exchange == B2.exchange?  ✗ (mall.order.direct ≠ mall.pay.direct)
       │    → 不匹配
       │
       └─ 结果: 无链路

第3轮: P2(PayService) × C1(OrderCancelListener)
       │
       └─ 结果: 无链路（exchange 不匹配）

第4轮: P2(PayService) × C2(PaySuccessListener)
       │
       ├─ 检查 B2:
       │    P2.exchange == B2.exchange?  ✓ (mall.pay.direct)
       │    B2.queue == C2.queue?        ✓ (mall.pay.success)
       │    routing_key 匹配?            ✓
       │    → 匹配成功！记录链路
       │
       └─ 结果: PayService → mall.pay.direct → mall.pay.success → PaySuccessListener
```

### 最终输出

```
flows = [
  { P1 → C1: OrderService → OrderCancelListener },
  { P2 → C2: PayService → PaySuccessListener }
]
```

### 代码实现

```python
def match_flows(self):
    flows = []

    for producer in self.producers:          # 遍历每个生产者
        for consumer in self.consumers:      # 遍历每个消费者

            # 尝试直接匹配（常规消息）
            flow = self._try_direct_match(producer, consumer)

            # 直接匹配失败，尝试 DLX 匹配（延迟消息）
            if not flow:
                flow = self._try_dlx_match(producer, consumer)

            if flow:
                flows.append(flow)

    return flows


def _try_direct_match(self, producer, consumer):
    """检查 producer 的消息能否通过某个 binding 到达 consumer"""

    for binding in self.bindings:
        # 条件1: producer 发到的 exchange == binding 的 exchange
        if binding.exchange_name != producer.exchange:
            continue

        # 条件2: binding 的 queue == consumer 监听的 queue
        if binding.queue_name != consumer.queue_name:
            continue

        # 条件3: routing_key 匹配
        if not self._match_routing_key(producer.routing_key, binding.routing_key):
            continue

        # 三个条件都满足 → 链路成立
        return {"producer": producer, "consumer": consumer, ...}

    return None  # 没找到匹配的 binding
```

### Routing Key 匹配规则

```
┌─────────────────────────────────────────────────────────────────┐
│                    Exchange 类型决定匹配规则                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐                                                   │
│  │  fanout  │ → 忽略 routing_key，所有队列都收到                │
│  └──────────┘                                                   │
│                                                                 │
│  ┌──────────┐                                                   │
│  │  direct  │ → 精确匹配 routing_key                           │
│  └──────────┘   producer.key == binding.key                    │
│                                                                 │
│  ┌──────────┐                                                   │
│  │  topic   │ → 通配符匹配                                      │
│  └──────────┘   * = 一个单词，# = 零或多个单词                  │
│                                                                 │
│                 例: binding.key = "order.*.cancel"             │
│                     producer.key = "order.123.cancel" → 匹配 ✓ │
│                     producer.key = "order.cancel" → 不匹配 ✗    │
│                                                                 │
│  ┌──────────┐                                                   │
│  │ headers  │ → 基于消息头匹配（代码未实现，宽松匹配）          │
│  └──────────┘                                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**代码实现**（第 779-829 行）：

```python
def _match_routing_key(self, exchange_type, producer_key, binding_key):
    exchange_type = (exchange_type or "direct").lower()

    if exchange_type == "fanout":
        return True  # fanout 忽略 routing_key

    if exchange_type == "headers":
        return True  # 暂不支持，宽松匹配

    if not producer_key or not binding_key:
        return True  # 缺失时宽松匹配

    if exchange_type == "direct":
        return producer_key == binding_key  # 精确匹配

    if exchange_type == "topic":
        return self._match_topic_pattern(producer_key, binding_key)

    return producer_key == binding_key
```

### DLX（死信/延迟）匹配逻辑

DLX 匹配和直接匹配思路一样，只是**多了一跳**：

```
直接匹配（1 跳）:
  Producer → Exchange → Queue → Consumer

DLX 匹配（2 跳）:
  Producer → Exchange → TTL Queue → (等待超时) → DLX Exchange → Queue → Consumer
                            ↑
                      消息在这里等 N 秒
                      超时后自动转发到死信交换机
```

### DLX 具体例子

场景：**订单 30 分钟未支付自动取消**

```
组件配置:

Producer: OrderService
  ┌─────────────────────────────────────────────────────┐
  │ exchange = "mall.order.direct"                      │
  │ routing_key = "mall.order.cancel.ttl"  ← 发到TTL队列│
  └─────────────────────────────────────────────────────┘

TTL Queue: mall.order.cancel.ttl
  ┌─────────────────────────────────────────────────────┐
  │ queue_name = "mall.order.cancel.ttl"                │
  │ dlx_exchange = "mall.order.direct"    ← 超时后转发  │
  │ dlx_routing_key = "mall.order.cancel" ← 用这个路由键│
  │ ttl = 1800000 (30分钟)                              │
  └─────────────────────────────────────────────────────┘

Bindings:
  ┌─────────────────────────────────────────────────────┐
  │ B1: exchange="mall.order.direct"                    │
  │     queue="mall.order.cancel.ttl"                   │
  │     routing_key="mall.order.cancel.ttl"             │
  ├─────────────────────────────────────────────────────┤
  │ B2: exchange="mall.order.direct"                    │
  │     queue="mall.order.cancel"                       │
  │     routing_key="mall.order.cancel"                 │
  └─────────────────────────────────────────────────────┘

Consumer: OrderCancelListener
  ┌─────────────────────────────────────────────────────┐
  │ queue_name = "mall.order.cancel"                    │
  └─────────────────────────────────────────────────────┘
```

### DLX 匹配过程

本质是**两次直接匹配**，中间用 TTL Queue 的死信配置连接：

```
第1跳: Producer → TTL Queue
       │
       ├─ 检查 B1:
       │    Producer.exchange == B1.exchange?  ✓ (mall.order.direct)
       │    routing_key 匹配?                  ✓ (mall.order.cancel.ttl)
       │    → 找到 TTL Queue: mall.order.cancel.ttl
       │
       └─ 这个队列有死信配置吗?
            dlx_exchange = "mall.order.direct"     ✓ 有
            dlx_routing_key = "mall.order.cancel"  ✓ 有

第2跳: DLX Exchange → Consumer
       │
       ├─ 检查 B2:
       │    TTL_Queue.dlx_exchange == B2.exchange?  ✓ (mall.order.direct)
       │    B2.routing_key == TTL_Queue.dlx_routing_key?  ✓ (mall.order.cancel)
       │    B2.queue == Consumer.queue?  ✓ (mall.order.cancel)
       │    → 匹配成功！
       │
       └─ 完整链路:
            OrderService
              → mall.order.direct
              → mall.order.cancel.ttl (等待30分钟)
              → mall.order.direct (死信交换机)
              → mall.order.cancel
              → OrderCancelListener
```

### 代码实现

```python
def _try_dlx_match(self, producer, consumer):
    """检查 producer 的消息能否通过 TTL+死信 到达 consumer"""

    # 第1跳: 找 Producer 发到的 TTL 队列
    for ttl_binding in self.bindings:
        if ttl_binding.exchange_name != producer.exchange:
            continue

        # 找到这个队列，检查是否配了死信
        ttl_queue = self._find_queue_by_name(ttl_binding.queue_name)
        if not ttl_queue or not ttl_queue.dlx_exchange:
            continue  # 没配死信，跳过

        # 第2跳: 找死信交换机绑定的目标队列
        for target_binding in self.bindings:
            if target_binding.exchange_name != ttl_queue.dlx_exchange:
                continue

            # 检查死信路由键匹配
            if target_binding.routing_key and ttl_queue.dlx_routing_key:
                if target_binding.routing_key != ttl_queue.dlx_routing_key:
                    continue

            # 目标队列 == Consumer 监听的队列?
            if target_binding.queue_name == consumer.queue_name:
                return {
                    "type": "ttl_dlx",
                    "producer": producer,
                    "consumer": consumer,
                    "ttl_queue": ttl_queue,
                    ...
                }

    return None  # 没找到 DLX 链路
```

---

## 六、Step 4 - 报告生成

### 报告结构

```
┌─────────────────────────────────────────────────────────────────┐
│                  rabbitmq_flow_report_v3.md                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  # RabbitMQ 消息流分析报告                                       │
│  > 生成时间: 2024-xx-xx                                         │
│                                                                 │
│  ## 概览                                                        │
│  ┌─────────────────────────────────────────┐                   │
│  │ 组件类型 │ 数量 │                        │                   │
│  │ 消费者   │  5   │                        │                   │
│  │ 生产者   │  3   │                        │                   │
│  │ ...      │ ...  │                        │                   │
│  └─────────────────────────────────────────┘                   │
│                                                                 │
│  ## 消息流转链路                                                 │
│  ### 链路 1: OrderService → OrderListener                       │
│  **业务场景**: xxx                                               │
│  **流转机制**: 直接发送 / TTL延迟+死信转发                        │
│  **流转路径**:                                                   │
│    1. OrderService 发送消息                                     │
│    2. mall.order.direct (exchange)                              │
│    3. mall.order.cancel (queue)                                 │
│    4. OrderListener.handle() 消费消息                           │
│                                                                 │
│  ```mermaid                                                     │
│  graph LR                                                       │
│    N0([OrderService]) --> N1{{mall.order.direct}}              │
│    N1 --> N2[(mall.order.cancel)]                              │
│    N2 --> N3([OrderListener])                                  │
│  ```                                                            │
│                                                                 │
│  ## 组件详情                                                     │
│  ### 消费者                                                      │
│  ### 生产者                                                      │
│  ### 队列配置                                                    │
│  ### 交换机配置                                                  │
│  ### 绑定关系                                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Mermaid 图节点形状

```
节点类型        形状语法              显示效果
─────────────────────────────────────────────────
producer       N0([name])           (  name  )   圆角矩形
consumer       N1([name])           (  name  )   圆角矩形
exchange       N2{{{name}}}         {  name  }   菱形
dlx            N3{{{name}}}         {  name  }   菱形
queue          N4[(name)]           [(  name  )] 圆柱形
ttl_queue      N5[(name)]           [(  name  )] 圆柱形
```

---

## 七、主流程串联

```
┌─────────────────────────────────────────────────────────────────┐
│                        async def run()                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │  1. query_components()                                   │  │
│   │     - _query_enum_constants()  → enum_values            │  │
│   │     - _query_consumers()       → consumers              │  │
│   │     - _query_producers()       → producers              │  │
│   │     - _query_queue_configs()   → queues                 │  │
│   │     - _query_exchange_configs()→ exchanges              │  │
│   │     - _query_binding_configs() → bindings               │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │  2. await extract_with_llm()                             │  │
│   │     - 对每个 consumer: LLM提取 → _resolve_value()        │  │
│   │     - 对每个 producer: LLM提取 → _resolve_value()        │  │
│   │     - 对每个 queue/exchange/binding: LLM提取             │  │
│   │     - _resolve_bean_references()                        │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │  3. match_flows()                                        │  │
│   │     - 双重循环 producer × consumer                       │  │
│   │     - _try_direct_match()                               │  │
│   │     - _try_dlx_match()                                  │  │
│   │     → flows 列表                                         │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │  4. generate_report(flows)                               │  │
│   │     - _write_header()                                   │  │
│   │     - _write_overview()                                 │  │
│   │     - _write_flows() + _write_mermaid()                 │  │
│   │     - _write_components()                               │  │
│   │     → Markdown 文件                                      │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 八、问题总结（写死的地方）

```
┌─────────────────────────────────────────────────────────────────┐
│                         硬编码问题汇总                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 枚举解析                                                     │
│     ├─ 假设构造函数参数顺序: (exchange, queue, routing_key)     │
│     └─ 假设 getter 方法名包含特定关键字                          │
│                                                                 │
│  2. 查询条件                                                     │
│     ├─ 消费者: 只查 @RabbitListener/@RabbitHandler              │
│     ├─ 生产者: 只查有 AmqpTemplate 字段的类                      │
│     └─ 配置: 只查 @Bean 方法                                     │
│                                                                 │
│  3. 漏掉的定义方式                                               │
│     ├─ @RabbitListener + @QueueBinding 声明式                   │
│     ├─ 配置文件定义                                              │
│     └─ RabbitMQ 服务端预创建                                     │
│                                                                 │
│  4. 链路匹配                                                     │
│     └─ 依赖字符串精确匹配，任一环节解析失败就断链                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 九、复现要点清单

如果你要从零复现这个代码：

| 步骤 | 要点 |
|------|------|
| 1. 定义数据结构 | 按 RabbitMQ 五大概念定义 dataclass |
| 2. 写 Cypher 查询 | 基于 Spring AMQP 注解查组件 |
| 3. 设计 Prompt | 让 LLM 输出固定 JSON 格式 |
| 4. 实现枚举解析 | 缓存枚举值 + 正则匹配 getter |
| 5. 实现链路匹配 | Producer.exchange → Binding → Consumer.queue |
| 6. 实现 DLX 匹配 | 多一跳：TTL Queue 的 dlx_exchange |
| 7. 生成 Markdown | 表格 + Mermaid 流程图 |
