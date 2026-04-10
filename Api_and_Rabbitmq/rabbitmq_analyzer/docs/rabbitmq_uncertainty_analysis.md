# RabbitMQ 分析器 - 不确定性内容处理

## 一、需要提取的信息

通过确定性规则找到组件后，还需要从源码中提取具体的配置值，才能进行后续的链路匹配。

| 组件 | 需要提取的信息 |
| --- | --- |
| 消费者 | 监听的队列名 |
| 生产者 | 目标交换机、路由键 |
| 队列配置 | 队列名、死信交换机、死信路由键 |
| 交换机配置 | 交换机名、类型 |
| 绑定配置 | 绑定的队列、交换机、路由键 |

---

## 二、为什么这些信息是不确定的

这些值写在源码里，但开发者的写法多种多样，无法用固定的正则规则覆盖所有情况。

| 写法类型 | 示例 |
| --- | --- |
| 直接写字符串 | queues = "mall.order.cancel" |
| 用枚举 | queues = QueueEnum.ORDER.getName() |
| 用常量 | queues = QueueConstants.ORDER |
| 用配置占位符 | queues = "${mq.queue.name}" |

---

## 三、LLM 的处理方式

### 3.1 整体思路

把组件的源码发给 LLM，告诉它需要提取什么信息，LLM 阅读源码后返回结构化的 JSON。

### 3.2 具体示例

**示例 1：消费者 - 提取队列名**

> 源码：@RabbitListener(queues = "mall.order.cancel")
>
> LLM 返回：{ "queue_name": "mall.order.cancel" }

**示例 2：生产者 - 提取交换机和路由键**

> 源码：amqpTemplate.convertAndSend("mall.order.direct.ttl", "mall.order.cancel.ttl", orderId)
>
> LLM 返回：{ "exchange": "mall.order.direct.ttl", "routing_key": "mall.order.cancel.ttl" }

**示例 3：队列配置 - 提取队列名和死信配置**

> 源码：QueueBuilder.durable("mall.order.cancel.ttl").withArgument("x-dead-letter-exchange", "mall.order.direct").build()
>
> LLM 返回：{ "queue_name": "mall.order.cancel.ttl", "dlx.exchange": "mall.order.direct" }

### 3.3 枚举引用的特殊处理

如果源码里用的是枚举：

> 源码：@RabbitListener(queues = QueueEnum.ORDER_CANCEL.getName())
>
> LLM 返回：{ "queue_name": null, "queue_expression": "QueueEnum.ORDER_CANCEL.getName()" }

脚本拿到 queue_expression 后，查预建的枚举映射表，得到实际的队列名。

---

## 四、提取完成后

LLM 提取出具体值后，就可以用确定性规则进行链路匹配了。

根据 RabbitMQ 的路由规则（交换机类型、路由键匹配、死信转发），将生产者和消费者串成完整的消息流转链路：

> CancelOrderSender → mall.order.direct.ttl → mall.order.cancel.ttl → (TTL到期) → mall.order.direct → mall.order.cancel → CancelOrderReceiver
