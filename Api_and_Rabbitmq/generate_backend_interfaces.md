# `generate_backend_interfaces.py` 说明文档

本文档解释脚本 `scripts/generate_backend_interfaces.py` **做什么**、**依赖什么**、**如何运行**、以及它是如何从 `mall` 项目的代码图谱里“扫描”出后端对外部系统的集成接口信息，并生成 `backend_interfaces.md` 的。

---

## 1. 这份脚本要解决什么问题？

在 `mall` 这种后端项目里，**“对外部系统的集成点”** 往往散落在很多地方（消息队列、定时任务、缓存 key、ES 索引、Mongo 集合、对象存储客户端等）。如果靠人工翻代码：

- 需要懂 Java + Spring 注解
- 需要全局搜索/跳转
- 还容易遗漏（尤其是隐藏在配置/常量/枚举里的 key）

这个脚本的目标是：**自动生成一份后端集成接口清单**（默认输出 `backend_interfaces.md`），让你在不读 Java 源码的情况下，也能快速回答类似问题：

- RabbitMQ 有哪些消费者/生产者？分别用的交换机、路由键、队列是什么？
- 有没有订单超时取消这类定时任务？cron 是多少？
- ES 索引有哪些？索引字段是什么类型、分词器是什么？
- MongoDB 有哪些集合？哪些字段建了索引？
- Redis 用了哪些 key？key 的模式长什么样？TTL 是多少？
- 项目里是否接入了阿里云 OSS 或 MinIO？端点/桶名从哪里取？

---

## 2. 输入与输出

### 2.1 输入（脚本依赖的数据源）

脚本并不是直接解析 Java 文件；它依赖两类输入：

1. **Neo4j 代码图谱（核心）**
   - 你的 Java 代码库已被解析为 Neo4j 图谱：类、方法、字段、枚举、注解、调用关系等都在图里。
   - 图谱中很多节点还带有解释字段：`SE_What / SE_Why / SE_When / SE_How`（用于生成“用途/目的/场景/逻辑”等文字说明）。

2. **Spring 配置文件（用于把 `${xxx}` 解析成真实值）**
   - 脚本会递归读取项目中的 `application.yml`（以及某些 profile 的 `application-xxx.yml` / `application-dev.yml`）
   - 把配置项压平成 `a.b.c = value` 这种形式，供后续替换 `${a.b.c}` 或 `redis.key.xxx` 之类的引用

### 2.2 输出

默认输出文件：项目根目录下的 `backend_interfaces.md`。

文档结构固定为 6 大章：

1. 概览（含 Mermaid 架构图）
2. RabbitMQ（消费者 / 生产者调用链 / 队列交换机配置）
3. 定时任务
4. 数据存储（Elasticsearch / MongoDB）
5. Redis
6. 对象存储（Aliyun OSS / MinIO）

---

## 3. 关键概念速通

### 3.1 “注解”是什么？

在 Spring 生态里，很多功能都靠“注解”标识，例如：

- `@RabbitListener`：表示“这个方法/类在监听某个 RabbitMQ 队列”
- `@Scheduled`：表示“这是一个定时任务”
- `@Document`：表示“这个类映射到 ES 索引或 Mongo 集合”
- `@Value("${...}")`：表示“从配置文件读一个值注入到字段”
- `@Bean`：表示“这个方法会创建并注册一个组件（例如 Queue/Exchange/Binding）”

脚本本质上就是在图谱里找：**哪些类/方法/字段带了这些标记**，再把它们组织成文档。

### 3.2 “Neo4j 代码图谱”里有什么？

图谱把代码拆成节点（Class/Method/Field/Enum/EnumConstant...），并用边表达关系（DECLARES/CALLS/USES...）。

本脚本最常用的两类关系：

- `(:Class)-[:DECLARES]->(:Method)`：某个类声明了某个方法
- `(:Method)-[:CALLS]->(:Method)`：某个方法调用了另一个方法

这些关系能让脚本回答：**“谁调用了发送消息的方法？”** 这种跨文件问题。

---

## 4. 脚本总体流程（从启动到生成文档）

脚本入口在文件末尾：

1. 创建 `BackendInterfaceGenerator`（连接 Neo4j + 加载配置 + 预加载枚举常量）
2. 调用 `generate_report()` 生成 6 个章节
3. 写入 `backend_interfaces.md`
4. finally 关闭 Neo4j 连接

你可以把它当成以下流水线：

```text
连接 Neo4j
  ↓
加载 application*.yml，形成 “配置字典”
  ↓
从 Neo4j 读取所有枚举常量，形成 “枚举常量参数字典”
  ↓
逐类扫描：RabbitMQ / Scheduled / ES+Mongo / Redis / OSS
  ↓
把扫描结果拼成 Markdown
  ↓
写入 backend_interfaces.md
```

下面按模块把“核心逻辑与细节”展开。

---

## 5. 配置解析：`ConfigParser`（把 `${xxx}` 变成真实值）

脚本的配置解析器做了 3 件关键事：

### 5.1 搜索并读取配置文件

- 递归查找 `application.yml`
- 跳过路径包含 `target` 的文件（避免扫描构建产物）
- 对每个 `application.yml`：
  - 优先使用环境变量 `CONFIG_PROFILE` 或 `SPRING_PROFILES_ACTIVE`
  - 否则尝试读 YAML 内部的 `spring.profiles.active`
  - 如果最终得到 profile，则加载同目录的 `application-{profile}.yml`
  - 如果没有 profile，则“兜底”加载 `application-dev.yml`（如果存在）

### 5.2 “压平”YAML 成扁平键值

例如 YAML：

```yaml
redis:
  key:
    admin: mall:ums:admin
```

会变成字典项：

```text
redis.key.admin = "mall:ums:admin"
```

### 5.3 `get()`：解析 `${xxx}` 以及“按 key 查值”

`ConfigParser.get(key)` 的行为可以理解为：

- 如果传入 `${redis.key.admin}` → 会去掉 `${}` 得到 `redis.key.admin` 再查字典
- 如果传入 `redis.key.admin` → 直接查字典
- 找不到时：
  - 如果你传了 `default` 就返回 `default`
  - 否则返回“原始 key”（这会让输出里出现 `Unknown` 或原样字符串）

> 为什么要做这一步？  
> 因为很多队列名/Redis key/OSS endpoint 都写在配置里，代码里是 `${...}` 引用；脚本需要把它“还原成最终值”。

---

## 6. 枚举解析：把 `QueueEnum.XXX.getExchange()` 还原成字符串

在 `mall` 项目里，RabbitMQ 的交换机/队列/路由键经常写在枚举里，比如（示意）：

```java
QUEUE_ORDER_CANCEL("mall.order.direct", "mall.order.cancel", "mall.order.cancel")
```

代码里可能写成：

```java
QueueEnum.QUEUE_ORDER_CANCEL.getExchange()
```

脚本为了解析这种写法，会：

1. 从 Neo4j 查所有 `Enum -> EnumConstant`，拿到常量的 `source_code`
2. 用正则从 `source_code` 里提取构造参数中的字符串列表（例如上面提到的 3 个字符串）
3. 在遇到表达式 `EnumName.CONSTANT.getXxx()` 时，根据 getter 名推断你要哪个参数：
   - 对 `QueueEnum` 做了专门映射：
     - `getExchange()` → 第 1 个参数
     - `getName()` → 第 2 个参数
     - `getRouteKey()` → 第 3 个参数
   - 其他枚举：默认返回第 1 个参数

这样，文档里就能输出最终的：

- `mall.order.direct.ttl`
- `mall.order.cancel.ttl`
- `mall.order.cancel`

---

## 7. “是否启用”的判断：为什么会出现 `disabled`？

脚本在 RabbitMQ 消费者 / 定时任务章节，会标记：

> `disabled (class is not a Spring bean)`

意思是：**虽然检测到了注解（比如 @Scheduled），但这个类不是 Spring 管理的组件**，实际运行时不会被框架加载，也就不会执行/监听。

脚本的判断策略（经验法则）：

- 如果类的 `modifiers` 或源码里出现以下注解之一，就当作“Spring Bean”：
  - `@Component`, `@Service`, `@Configuration`, `@Controller`, `@RestController`, `@Repository`

注意：这是静态判断，不是 100% 精确（比如通过 XML 注册 Bean 的情况脚本未必能识别）。

---

## 8. RabbitMQ 扫描逻辑（消费者 / 生产者 / 组件配置）

RabbitMQ 这一章由三段组成：

### 8.1 消费者（Consumers）

脚本在 Neo4j 中寻找：

- 某个类 `c` 声明的方法 `m`
- 方法或类的修饰信息里包含：
  - `@RabbitListener`（监听队列）
  - 或 `@RabbitHandler`（处理消息的方法）

拿到这些方法后，脚本会提取：

- **队列名**：从注解参数里解析 `queues="xxx"`  
  然后用 `ConfigParser.get()` 做一次“配置替换”（例如把 `${mq.queue.cancel}` 替换成真正队列名）
- **消息载体**：从 `m.parameters` 里拿第一个参数类型（例如 `Long`）
- **目的/逻辑**：用 `SE_Why / SE_What / SE_How` 生成文本（缺失则写“暂无描述”）
- **是否禁用**：用“Spring Bean 判定”标记 disabled

文档里的一个真实例子（来自当前生成的 `backend_interfaces.md`）：

- 消费者：`CancelOrderReceiver.handle`
- 监听队列：`mall.order.cancel`
- 消息载体：`Long`
- 处理逻辑：由 `SE_How` 生成（解释这个方法怎么处理订单取消）

### 8.2 生产者（Producers）+ “谁触发了发送”

脚本的策略是：

1. 先找“发送组件”：类里声明了 `RabbitTemplate` 或 `AmqpTemplate` 类型字段的类
2. 在这些发送组件里找“真正发送的方法”：方法源码中包含 `convertAndSend`
3. 再借助 Neo4j 的 `CALLS` 关系，找“谁调用了这个发送方法”（最多 15 条）

然后对每条调用链生成表格列：

- 触发业务方（caller class）
- 触发方法（caller method）
- 交换机（Exchange）
- 路由键（Routing Key）
- 业务场景（caller 的 `SE_What`）

交换机与路由键的解析：

- 从 `convertAndSend(exchange, routingKey, message...)` 正则抓前两个参数
- 如果参数是枚举 getter：用“枚举解析”还原
- 如果参数是配置 key：用 `ConfigParser.get()` 还原

此外脚本会生成一张 Mermaid 消息流向图，并附带一个“延迟机制”子图（TTL → DLX → Consumer），用于表达典型的“延迟取消订单”模式。

当前输出里就有一条典型例子：

- `OmsPortalOrderServiceImpl.sendDelayMessageCancelOrder`
  → 发送到 `mall.order.direct.ttl : mall.order.cancel.ttl`

### 8.3 队列/交换机/绑定配置（Queue / Exchange / Binding）

脚本会扫描所有 `@Bean` 方法，并且满足任一条件：

- 返回类型包含 `Queue` / `Exchange` / `Binding`
- 或源码包含 `QueueBuilder` / `ExchangeBuilder` / `BindingBuilder`

然后从源码中额外提取常见高级配置（如果有）：

- `x-dead-letter-exchange`（DLX：死信交换机）
- `x-dead-letter-routing-key`（DLK：死信路由键）
- `x-message-ttl`（TTL 毫秒）

这些值如果是枚举表达式也会尝试解析。

---

## 9. 定时任务扫描逻辑（Scheduled）

脚本在 Neo4j 中寻找带 `@Scheduled` 的方法：

- 解析 cron：从方法源码里正则提取 `cron="..."`
  - 如果提取不到，就显示 `FixedRate/Delay`（表示可能是 `fixedRate/fixedDelay` 之类写法）
- 生成字段：
  - class、method、schedule
  - disabled 判定（是否 Spring Bean）
  - `任务描述`（SE_What）
  - `执行逻辑`（SE_How）

当前输出里展示了一个定时任务，但被判定为 disabled：

- `OrderTimeOutCancelTask.cancelTimeOutOrder`
- cron：`0 0/10 * ? * ?`
- disabled：class 不是 Spring Bean

> 这条提示对排查“为什么生产环境没跑定时任务”非常有用：有些类看上去写了 `@Scheduled`，但没被注册到容器里。

---

## 10. 数据存储扫描逻辑（Elasticsearch / MongoDB）

这一章的入口是：扫描所有带 `@Document` 的类（Spring Data 体系的标记）。

### 10.1 如何区分 ES vs Mongo？

脚本用一个非常实用的启发式判断：

- 如果注解或源码里出现 `indexName` → 当作 **Elasticsearch**
- 否则 → 当作 **MongoDB**

### 10.2 Elasticsearch：索引名、分片副本、字段结构

对 ES 类，脚本会：

- 从 `@Document(indexName="...")` 或源码里解析索引名
- 解析分片/副本：`shards=...`，`replicas=...`
- 用 Neo4j 查询该类声明的字段（`DECLARES -> Field`）
- 对字段做 ES 相关标注提取：
  - 如果字段有 `@Field(...)`：
    - 提取 `type=FieldType.Xxx`
    - 提取 `analyzer="..."`（如 `ik_max_word`）
  - 如果字段有 `@Id`：标记为 `ID`

最终生成“字段结构”表格。

当前输出中的真实例子：

- 索引：`pms`
- 映射类：`EsProduct`
- 字段里能看到：
  - `name` 是 `Text` + `ik_max_word`
  - `brandName` 是 `Keyword`
  - `attrValueList` 是 `Nested`

### 10.3 MongoDB：集合名、索引字段、文档结构

对 Mongo 类，脚本会：

- 解析集合名：
  - 如果 `@Document(collection="xxx")` 存在就用它
  - 否则用默认规则：类名首字母小写（例如 `MemberReadHistory` → `memberReadHistory`）
- 字段索引：如果字段修饰符里包含 `@Indexed`，就把字段名收集到“索引字段”
- 文档结构表格：
  - 字段名、Java 类型
  - 字段说明来自字段的 `SE_What`

---

## 11. Redis 扫描逻辑（Key 模式 + TTL）

Redis 这一章的难点是：**很多 key 是“拼出来的”**，不是写死字符串。

脚本采取“尽量还原”的策略，输出的 key 往往是这种形式：

```text
mall:ums:admin:${expr:username}
```

其中：

- `mall:ums:admin:` 是确定的前缀（来自配置或字符串字面量）
- `${expr:username}` 表示运行时变量部分（脚本无法知道具体用户名，就用占位符表达）

### 11.1 Redis 相关类的筛选

脚本在 Neo4j 中找：

- 类里有字段 `@Value("${...}")`
- 字段名包含 `REDIS` 或 `key`
- 并排除一些明显不是 key 的配置（DATABASE/HOST/PORT/PASSWORD）
- 同时类里还要存在“疑似 Redis 操作”的方法（方法源码包含 `redis` 或 `Redis`）

### 11.2 把 `@Value("${redis.key.xxx}")` 解析成真实前缀

脚本会预先扫描全图谱所有相关字段，建立：

`字段名 -> 配置解析后的值`

例如：

- 字段名 `REDIS_KEY_ADMIN`
- 修饰符 `@Value("${redis.key.admin}")`
- 通过配置解析得到 `mall:ums:admin`
- 后续看到代码里拼接 `REDIS_KEY_ADMIN + ":" + username`，就能把前缀替换成 `mall:ums:admin`

### 11.3 Key 模式提取（启发式规则）

脚本对每个方法源码做多种正则/启发式抽取，常见覆盖：

1. **字符串拼接**（`String key = a + b + c;`）
   - 字面量 `"xxx"` → 直接取 `xxx`
   - 如果是字段名且存在于 `字段名 -> 值` 映射 → 用真实值替换
   - 其他表达式 → 变成 `${expr:变量名}` 形式

2. **`String.format`**
   - 把 `%s/%d` 简化为 `${...}`

3. **`StringBuilder.append("prefix")...`**
   - 只做弱推断：找到第一个 append 的字符串字面量，输出 `prefix${...}`

4. **直接在 redis 调用里使用字面量 key**
   - 例如 `redisService.get("a:b:c")` 这种，会直接提取 `"a:b:c"`

最终对同一个类可能得到多个 key pattern，会用 ` / ` 拼在一起输出。

### 11.4 TTL（过期时间）提取

脚本另外扫描字段名包含 `EXPIRE` 的 `@Value("${...}")`，把解析出来的 TTL 展示到表格里。

当前输出里的真实例子：

- `UmsAdminCacheServiceImpl`
  - key：`mall:ums:admin:${expr:username} / mall:ums:resourceList:${expr:adminId}`
  - TTL：`86400`

---

## 12. 对象存储扫描逻辑（OSS / MinIO）

脚本在 Neo4j 中找：

- 类里声明了 `OSSClient` 或 `MinioClient` 类型字段

如果找到，就：

1. 先输出“运维配置”（从配置文件读取）：
   - `aliyun.oss.endpoint / bucketName / dir.prefix`
   - `minio.endpoint / bucketName`
2. 再输出“使用组件表格”：
   - 存储类型（阿里云 OSS / MinIO）
   - 使用组件（类名）
   - 组件用途（`SE_What`）

当前输出里能看到：

- OSS Endpoint：`oss-cn-shenzhen.aliyuncs.com`
- MinIO Endpoint：`http://localhost:9000`
- 使用组件：`OssServiceImpl`

---
