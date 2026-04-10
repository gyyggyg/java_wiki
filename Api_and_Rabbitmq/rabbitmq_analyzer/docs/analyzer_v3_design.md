# RabbitMQ Flow Analyzer v3 设计文档

## 概述

`analyzer_v3.py` 是一个 RabbitMQ 消息流转链路分析工具，用于自动分析 Spring AMQP 项目中的消息流。

核心设计采用 **"锚点 + LLM"** 的混合架构：

```
确定性查询 → LLM 提取 → 确定性匹配
```

---

## 核心问题

分析目标：**Producer → Exchange → Queue → Consumer** 的完整消息链路

### 难点分析

| 维度 | 确定性 | 不确定性 |
|-----|-------|---------|
| 组件存在性 | 用了 `@RabbitListener` 就是消费者 | - |
| 组件内容 | - | 队列名可能是字符串、枚举... |
| 链路匹配 | Exchange 绑定 Queue 是 RabbitMQ 固定概念 | - |

**关键洞察**：不确定性只存在于"代码写法"这一层，组件的存在性和链路匹配逻辑都是确定的。

---

## 设计思路

### 核心理念

> **用确定性逻辑框住问题边界，用 LLM 处理边界内的模糊细节**

- **规则**负责：找节点、查关系、匹配链路（骨架）
- **LLM**负责：把模糊的表达式解析成确定的值（血肉）

### 三段式架构

```
┌─────────────────────────────────────────────────────────┐
│  Step 1: 确定性查询                                      │
│  ─────────────────                                      │
│  输入: 代码图数据库 (Neo4j)                               │
│  依据: Spring AMQP 标准注解                              │
│  输出: 组件列表（消费者、生产者、配置...）                   │
│  特点: 不漏、不错                                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Step 2: LLM 提取                                        │
│  ─────────────────                                       │
│  输入: 组件源码 + SE_* 语义信息                           │
│  任务: 理解代码，提取结构化信息                            │
│  输出: {queue_name: "xxx", exchange: "yyy", ...}         │
│  特点: 能处理多种写法，有容错能力                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Step 3: 确定性匹配                                      │
│  ─────────────────                                      │
│  输入: 提取后的结构化信息                                 │
│  依据: RabbitMQ 概念（Exchange→Binding→Queue）           │
│  输出: 完整链路                                          │
│  特点: 逻辑可控、可解释                                   │
└─────────────────────────────────────────────────────────┘
```

---

## 详细设计

### Step 1: 确定性查询（锚点）

基于 **Spring AMQP 标准注解**，通过 Neo4j 图数据库查询代码中的组件：

| 组件类型 | 查询依据（锚点） |
|---------|-----------------|
| 消费者 | `@RabbitListener` / `@RabbitHandler` |
| 生产者 | `AmqpTemplate` / `RabbitTemplate` 字段 |
| 队列配置 | `@Bean` + 返回类型 `Queue` |
| 交换机配置 | `@Bean` + 返回类型 `Exchange` |
| 绑定配置 | `@Bean` + 返回类型 `Binding` |

**锚点的作用**：
- **不会漏** — 标准注解是强约束，用了就能查到
- **不会错** — 不依赖 LLM 判断"这是不是消费者"

还会预先查询 MQ 相关枚举常量（如 `QueueEnum`），用于后续解析枚举引用。

### Step 2: LLM 提取

使用 **通用 Prompt** 让 LLM 从各类代码中提取结构化 JSON：

| 组件类型 | 提取内容 |
|---------|---------|
| 消费者 | 监听的队列名、绑定信息 |
| 生产者 | 发送的交换机、路由键 |
| 队列配置 | 队列名、死信配置、TTL |
| 交换机配置 | 交换机名、类型 |
| 绑定配置 | 队列/交换机/路由键关系 |

**LLM 处理的是"模糊地带"**——同样是队列名，可能有多种写法：

```java
// 硬编码
queues = "mall.order.cancel"

// 枚举引用
queues = QueueEnum.ORDER.getName()
```

#### 值解析逻辑

提取后通过 `_resolve_value()` 统一解析：

```python
def _resolve_value(self, *expressions):
    for expr in expressions:
        if not expr:
            continue

        expr_clean = expr.strip('"\'')

        # 方法调用 → 尝试解析枚举
        if '()' in expr:
            enum_value = self._resolve_enum_ref(expr)
            if enum_value:
                return enum_value

        # 简单字面量（可能包含点号）
        return expr_clean

    return None
```

### Step 3: 确定性匹配

基于 **RabbitMQ 通用概念** 匹配链路，支持多种场景：

#### 场景 1: 直接匹配

```
Producer → Exchange → Queue → Consumer
```

匹配条件：
- Exchange 名称匹配
- Queue 名称匹配
- Routing Key 匹配（根据 Exchange 类型）

#### 场景 2: TTL + 死信匹配（延迟消息）

```
Producer → Exchange → TTL Queue → DLX → Target Queue → Consumer
```

匹配条件：中间队列配置了死信交换机，死信目标队列是 Consumer 监听的队列

#### Exchange 类型处理

| Exchange 类型 | Routing Key 匹配规则 |
|--------------|---------------------|
| Direct | 精确匹配 |
| Topic | 支持 `*`（一个单词）和 `#`（任意）通配符 |
| Fanout | 忽略 Routing Key，总是匹配 |
| Headers | 宽松匹配（暂不支持 Headers 条件解析） |

```python
def _match_routing_key(self, exchange_type, producer_key, binding_key):
    if exchange_type == "fanout":
        return True  # Fanout 忽略路由键

    if exchange_type == "topic":
        return self._match_topic_pattern(producer_key, binding_key)

    return producer_key == binding_key  # Direct 精确匹配
```

### Step 4: 报告生成

输出 Markdown 报告，包含：
- 概览统计
- 消息流转链路（含 Mermaid 流程图）
- 触发入口（调用链）
- 各组件详情（消费者、生产者、队列、交换机、绑定）

---

## 架构优势

| 对比维度 | 纯 LLM 方案 | 纯规则方案 | 锚点 + LLM |
|---------|------------|-----------|-----------|
| 组件发现 | 可能漏掉组件 | 不会漏 | 不会漏 |
| 类型判断 | 可能误判 | 准确 | 准确 |
| 代码理解 | 能处理多种写法 | 规则脆弱易失效 | 能处理多种写法 |
| 匹配逻辑 | 不可控 | 可控 | 可控 |
| 可解释性 | 差 | 好 | 好 |

**本质**：把 LLM 的不确定性限制在"信息提取"这一步，前后两端（组件发现、链路匹配）都保持确定性。

---

## 数据结构

```python
@dataclass
class Consumer:
    class_name: str
    method_name: str
    queue_name: Optional[str]      # 监听的队列
    payload_type: str              # 消息载体类型
    se_why: str                    # 业务目的
    se_how: str                    # 处理逻辑

@dataclass
class Producer:
    class_name: str
    exchange: Optional[str]        # 目标交换机
    routing_key: Optional[str]     # 路由键
    callers: List[Dict]            # 调用方

@dataclass
class QueueConfig:
    queue_name: Optional[str]
    dlx_exchange: Optional[str]    # 死信交换机
    dlx_routing_key: Optional[str] # 死信路由键
    ttl_ms: Optional[int]          # TTL

@dataclass
class ExchangeConfig:
    exchange_name: Optional[str]
    exchange_type: str             # direct/topic/fanout/headers

@dataclass
class BindingConfig:
    queue_name: Optional[str]
    exchange_name: Optional[str]
    routing_key: Optional[str]
```

---

## 执行流程

```python
async def run(self):
    # Step 1: 确定性查询
    self.query_components()

    # Step 2: LLM 提取
    await self.extract_with_llm()

    # Step 3: 确定性匹配
    flows = self.match_flows()

    # Step 4: 生成报告
    self.generate_report(flows, output_path)
```

---

## 当前能力边界

### 已支持

- 硬编码字符串队列名/交换机名
- 枚举引用解析（如 `QueueEnum.ORDER.getName()`）
- Direct/Topic/Fanout Exchange 匹配
- TTL + 死信转发链路识别
- Mermaid 流程图生成

### 待完善

详见 [UNCERTAINTY_ISSUES.md](./UNCERTAINTY_ISSUES.md)：

- 外部配置中心（Nacos/Apollo）
- 条件性配置（@Profile）
- 运行时动态值
- 跨服务链路
- Headers Exchange 条件解析
