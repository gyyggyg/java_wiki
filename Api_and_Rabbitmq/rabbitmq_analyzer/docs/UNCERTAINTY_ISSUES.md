# RabbitMQ Analyzer - 不确定性问题清单

> 本文档记录当前分析器无法处理的"不确定性"场景，供后续迭代完善。

---

## 1. 外部配置中心

### 问题描述

当配置值存储在外部配置中心（如 Nacos、Apollo、Consul）时，本地配置文件中只有占位符或根本没有对应配置，无法解析出实际值。

### 示例

```java
@RabbitListener(queues = "${order.queue.name}")
public void handleOrder(OrderMessage msg) { ... }
```

```yaml
# application.yml - 本地没有这个配置，实际值在 Nacos 中
# order.queue.name: ???
```

### 影响

- 队列名、交换机名、路由键等无法解析
- 链路匹配失败

### 可能的解决方向

1. **接入配置中心 API**：通过 Nacos/Apollo 的 Open API 获取配置
2. **导出配置快照**：要求用户提供配置中心的导出文件
3. **环境变量注入**：运行分析器时通过环境变量传入关键配置

---

## 2. 条件性配置 (@Profile)

### 问题描述

Spring 的 `@Profile` 或 `@ConditionalOnProperty` 等条件注解会导致同一个 Bean 在不同环境下有不同的配置，静态分析无法确定运行时使用哪个。

### 示例

```java
@Profile("prod")
@Bean
public Queue orderQueue() {
    return new Queue("prod.order.queue");
}

@Profile("dev")
@Bean
public Queue orderQueue() {
    return new Queue("dev.order.queue");
}
```

### 影响

- 同一个 Bean 方法可能返回不同的队列名
- 分析结果可能与实际运行环境不符

### 可能的解决方向

1. **指定目标环境**：用户指定分析哪个 profile（如 `--profile=prod`）
2. **列出所有可能值**：报告中标注"prod 环境为 X，dev 环境为 Y"
3. **默认选择 prod**：对于面向生产的分析，默认使用 prod profile

---

## 3. 运行时动态值

### 问题描述

当消息目标（交换机、路由键）由运行时逻辑决定时，静态分析只能列出所有可能的值，无法确定实际使用哪个。

### 示例

```java
public void sendOrder(Order order) {
    String routingKey = order.isVip() ? "order.vip" : "order.normal";
    rabbitTemplate.convertAndSend("order.exchange", routingKey, order);
}
```

### 影响

- 路由键有多个候选值
- 链路可能匹配到多条路径

### 可能的解决方向

1. **列出所有候选值**：LLM 分析代码分支，输出所有可能的值
2. **条件标注**：报告中标注"当 order.isVip()=true 时为 X，否则为 Y"
3. **概率估计**：基于代码逻辑推断哪个分支更常见

---

## 4. 跨服务链路

### 问题描述

在微服务架构中，Producer 和 Consumer 可能在不同的服务中，单项目分析无法得到完整的消息流转链路。

### 示例

```
订单服务 (Producer)          库存服务 (Consumer)
    │                             │
    │  order.exchange             │
    └────────────────────────────►│
                                  ▼
                            order.queue
```

### 影响

- 只能看到半条链路
- 无法追踪消息的最终去向

### 可能的解决方向

1. **多项目聚合分析**：同时分析多个服务的代码图
2. **消息契约中心**：维护一个中央的 Exchange/Queue 注册表
3. **运行时追踪**：结合 APM（如 SkyWalking）的链路追踪数据

---

## 5. 非标准实现

### 问题描述

部分代码可能不使用 Spring AMQP 的标准注解和 Template，而是直接使用 RabbitMQ Java Client。

### 示例

```java
// 直接使用 RabbitMQ Java Client
ConnectionFactory factory = new ConnectionFactory();
Connection connection = factory.newConnection();
Channel channel = connection.createChannel();
channel.basicPublish("exchange", "routingKey", null, message.getBytes());
```

### 影响

- 基于 `@RabbitListener` 和 `AmqpTemplate` 的锚点查询会遗漏这些组件

### 可能的解决方向

1. **扩展锚点查询**：增加对 `ConnectionFactory`、`Channel` 等的查询
2. **代码模式匹配**：识别 `basicPublish`、`basicConsume` 等方法调用

---

## 6. 延迟消息插件

### 问题描述

使用 RabbitMQ 延迟消息插件（`rabbitmq_delayed_message_exchange`）实现延迟消息时，走的是不同于 TTL+DLX 的机制。

### 示例

```java
@Bean
public CustomExchange delayedExchange() {
    Map<String, Object> args = new HashMap<>();
    args.put("x-delayed-type", "direct");
    return new CustomExchange("delayed.exchange", "x-delayed-message", true, false, args);
}
```

### 影响

- 当前只识别 TTL + DLX 的延迟模式
- 使用延迟插件的链路无法正确匹配

### 可能的解决方向

1. **识别 CustomExchange**：检测 `x-delayed-message` 类型的交换机
2. **新增匹配场景**：在链路匹配中增加延迟插件的处理逻辑

---

## 7. Headers Exchange

### 问题描述

Headers Exchange 基于消息头（Headers）而非路由键进行匹配，当前的路由键匹配逻辑不适用。

### 示例

```java
@Bean
public Binding headersBinding() {
    return BindingBuilder
        .bind(queue())
        .to(headersExchange())
        .where("format").matches("pdf")
        .and("type").matches("report");
}
```

### 影响

- Headers Exchange 的绑定条件无法解析
- 链路匹配可能不准确

### 可能的解决方向

1. **解析 Headers 条件**：在绑定配置中提取 `where().matches()` 的条件
2. **扩展匹配逻辑**：对 Headers Exchange 进行消息头匹配

---

## 当前状态总结

| 问题 | 优先级 | 难度 | 状态 |
|-----|--------|------|------|
| 外部配置中心 | 高 | 中 | 待处理 |
| 条件性配置 | 中 | 低 | 待处理 |
| 运行时动态值 | 中 | 中 | 待处理 |
| 跨服务链路 | 高 | 高 | 待处理 |
| 非标准实现 | 低 | 中 | 待处理 |
| 延迟消息插件 | 中 | 低 | 待处理 |
| Headers Exchange | 低 | 中 | 待处理 |

---

## 建议迭代顺序

1. **第一阶段**：条件性配置 + 延迟消息插件（低难度，快速见效）
2. **第二阶段**：外部配置中心 + 运行时动态值（需要额外输入源）
3. **第三阶段**：跨服务链路（需要架构级支持）
