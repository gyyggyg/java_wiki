"""
RabbitMQ Flow Analyzer - 通用的消息链路分析工具

核心思路：
1. 锚点发现：通过 Cypher 查询找到 Consumer/Producer/Config
2. LLM 分析：让 LLM 理解代码语义，提取关键信息
3. 迭代探索：根据 LLM 的分析结果，继续在图中探索相关节点
4. 链路组装：综合所有信息，构建完整的消息流转链路

设计目标：通用性 - 同一套逻辑在不同 SpringBoot 项目中都能工作
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from neo4j import GraphDatabase
from llm_interface import LLMInterface


# ============================================================================
# 配置
# ============================================================================

# Neo4j 配置
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7689")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "c8a3974ba62qcc2")

# LLM 配置
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4.1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your_openai_api_key_here")


# ============================================================================
# 数据结构/
# ============================================================================

class AnchorType(Enum):
    CONSUMER = "consumer"
    PRODUCER = "producer"
    CONFIG = "config"
    ENUM_CONSTANT = "enum_constant"


@dataclass
class Anchor:
    """锚点：代码中与消息队列相关的关键节点"""
    node_id: int
    anchor_type: AnchorType
    name: str
    class_name: str
    source_code: str
    se_what: Optional[str] = None
    se_why: Optional[str] = None
    class_source: Optional[str] = None  # 类级别的源码
    class_modifiers: Optional[str] = None  # 类级别的修饰符/注解
    neighbors: List[Dict] = field(default_factory=list)
    extracted_info: Dict = field(default_factory=dict)


@dataclass
class MessageFlow:
    """消息流转链路"""
    producer: Optional[Anchor] = None
    consumer: Optional[Anchor] = None
    path: List[Dict] = field(default_factory=list)
    confidence: str = "unknown"
    reasoning: str = ""


# ============================================================================
# Prompt 模板
# ============================================================================

PROMPTS = {
    "consumer": """你是一个 Java RabbitMQ 代码分析专家。

## 任务
分析以下 RabbitMQ 消息消费者代码，提取队列监听信息。

## 输入
类名：{class_name}
方法名：{method_name}

方法源码：
```java
{source_code}
```

类级别注解（重要！@RabbitListener 通常在这里定义）：
```
{class_modifiers}
```

类级别源码：
```java
{class_source}
```

语义描述：{se_what}

## 分析要求
请识别这个消费者监听的队列。**注意**：
- @RabbitListener 通常在**类级别注解**中定义（此时方法上只有 @RabbitHandler）
- 请优先检查"类级别注解"字段中的 @RabbitListener
- @RabbitListener 也可能在方法级别定义

可能的队列标识形式：
1. 硬编码字符串：如 queues = "order.cancel"
2. 枚举/常量引用：如 queues = QueueEnum.ORDER_CANCEL.getName()
3. 配置文件占位符：如 queues = "${{mq.order.queue}}"
4. SpEL 表达式：如 queues = "#{{queueConfig.orderQueue}}"
5. @QueueBinding 绑定形式

## 输出要求
返回 JSON 格式：
```json
{{
    "queue_identifier": "队列的标识符（字符串值、枚举引用或表达式）",
    "identifier_type": "string|enum|config|spel|binding|unknown",
    "enum_class": "如果是枚举引用，枚举类名（否则为 null）",
    "enum_constant": "如果是枚举引用，常量名（否则为 null）",
    "needs_lookup": true/false,
    "lookup_hint": "如果需要进一步查找，提示查找什么（否则为 null）"
}}
```""",

    "producer": """你是一个 Java RabbitMQ 代码分析专家。

## 任务
分析以下 RabbitMQ 消息生产者代码，提取消息发送目标信息。

## 输入
类名：{class_name}
源码：
```java
{source_code}
```

语义描述：{se_what}

## 分析要求
请识别这个生产者发送消息的目标，可能的情况包括：
1. 发送到队列：rabbitTemplate.convertAndSend(queueName, message)
2. 发送到交换机：rabbitTemplate.convertAndSend(exchange, routingKey, message)
3. 目标可能是字符串、枚举引用或变量

请找出所有 convertAndSend / send 等发送方法的调用，并分析其参数。

## 输出要求
返回 JSON 格式：
```json
{{
    "send_calls": [
        {{
            "method": "convertAndSend",
            "target_type": "queue|exchange",
            "target_identifier": "目标标识符",
            "identifier_type": "string|enum|variable|unknown",
            "enum_class": "如果是枚举，类名（否则为 null）",
            "enum_constant": "如果是枚举，常量名（否则为 null）",
            "routing_key": "路由键（如果有）"
        }}
    ],
    "needs_lookup": true/false,
    "lookup_hints": ["需要进一步查找的内容"]
}}
```""",

    "config": """你是一个 Java RabbitMQ 代码分析专家。

## 任务
分析以下 RabbitMQ 配置代码（@Bean 方法），提取队列/交换机/绑定的配置信息。

## 输入
类名：{class_name}
方法名：{method_name}
返回类型：{return_type}
源码：
```java
{source_code}
```

语义描述：{se_what}

## 分析要求
请识别这个 @Bean 配置了什么：
1. 是 Queue、Exchange 还是 Binding
2. 名称来源（字符串、枚举引用等）
3. 是否配置了死信队列（x-dead-letter-exchange, x-dead-letter-routing-key）
4. 是否配置了 TTL（x-message-ttl）
5. 其他重要参数

## 输出要求
返回 JSON 格式：
```json
{{
    "bean_type": "queue|exchange|binding",
    "name_identifier": "名称标识符",
    "name_type": "string|enum|variable",
    "enum_class": "如果是枚举，类名（否则为 null）",
    "enum_constant": "如果是枚举，常量名（否则为 null）",
    "dlx_config": {{
        "exchange": "死信交换机（如果有）",
        "routing_key": "死信路由键（如果有）",
        "exchange_enum": "死信交换机的枚举引用（如果有）"
    }} | null,
    "ttl_ms": "TTL 毫秒数（如果有）" | null,
    "other_args": {{}},
    "needs_lookup": true/false,
    "lookup_hints": ["需要进一步查找的内容"]
}}
```""",

    "enum_constant": """你是一个 Java 代码分析专家。

## 任务
分析以下枚举常量的定义，提取消息队列相关的值。

## 输入
枚举类名：{enum_name}
常量名：{constant_name}
源码：
```java
{source_code}
```

语义描述：{se_what}

## 分析要求
这个枚举常量通常包含消息队列的配置信息，如：
- 队列名称
- 交换机名称
- 路由键

请从构造函数参数或字段中提取这些值。

## 输出要求
返回 JSON 格式：
```json
{{
    "queue_name": "队列名称（如果有）",
    "exchange_name": "交换机名称（如果有）",
    "routing_key": "路由键（如果有）",
    "other_values": {{}}
}}
```""",

    "assemble_flow": """你是一个 Java RabbitMQ 架构分析专家。

## 任务
根据以下收集到的信息，分析并构建完整的消息流转链路。

## 已发现的组件

### 生产者 (Producers)
{producers_json}

### 消费者 (Consumers)
{consumers_json}

### 配置 (@Bean Configs)
{configs_json}

### 枚举常量
{enums_json}

## 分析要求
1. 识别哪些 Producer 和 Consumer 是关联的
2. 分析消息的流转路径（可能是直接发送，也可能经过 TTL + DLX）
3. 标注关联的置信度

## 输出要求
返回 JSON 格式：
```json
{{
    "flows": [
        {{
            "producer_class": "生产者类名",
            "consumer_class": "消费者类名",
            "path_description": "消息路径描述",
            "path_steps": [
                {{"step": 1, "component": "xxx", "action": "xxx"}}
            ],
            "confidence": "high|medium|low",
            "reasoning": "判断依据"
        }}
    ],
    "unlinked_producers": ["未能关联到消费者的生产者"],
    "unlinked_consumers": ["未能关联到生产者的消费者"]
}}
```"""
}


# ============================================================================
# 核心类
# ============================================================================

class RabbitMQFlowAnalyzer:
    """RabbitMQ 消息流分析器"""

    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str,
                 llm_provider: str = "openai", llm_model: str = "gpt-4o-mini", api_key: str = None):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.llm = LLMInterface(model_name=llm_model, provider=llm_provider, temperature=0.1, api_key=api_key)

        # 存储发现的锚点和提取的信息
        self.consumers: List[Anchor] = []
        self.producers: List[Anchor] = []
        self.configs: List[Anchor] = []
        self.enum_constants: Dict[str, Anchor] = {}  # key: "EnumClass.CONSTANT"

        # 探索历史，避免重复
        self.explored_nodes: set = set()

    def close(self):
        self.driver.close()

    def run_query(self, query: str, params: Dict = None) -> List[Dict]:
        """执行 Cypher 查询"""
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    # ========================================================================
    # 调用链查询
    # ========================================================================

    def query_caller_chain(self, class_name: str, method_name: str) -> List[Dict]:
        """查询谁调用了指定方法（向上追溯）"""
        query = """
        MATCH (targetClass {name: $class_name})-[:DECLARES]->(targetMethod:Method {name: $method_name})
        WHERE targetClass:Class OR targetClass:Interface
        MATCH (caller:Method)-[:CALLS]->(targetMethod)
        MATCH (callerOwner)-[:DECLARES]->(caller)
        WHERE callerOwner:Class OR callerOwner:Interface
        RETURN callerOwner.name as caller_class, caller.name as caller_method,
               caller.SE_What as caller_desc
        LIMIT 10
        """
        return self.run_query(query, {"class_name": class_name, "method_name": method_name})

    def query_callee_chain(self, class_name: str, method_name: str) -> List[Dict]:
        """查询指定方法调用了谁（向下追溯）"""
        query = """
        MATCH (targetClass {name: $class_name})-[:DECLARES]->(targetMethod:Method {name: $method_name})
        WHERE targetClass:Class OR targetClass:Interface
        MATCH (targetMethod)-[:CALLS]->(callee:Method)
        MATCH (calleeOwner)-[:DECLARES]->(callee)
        WHERE (calleeOwner:Class OR calleeOwner:Interface)
          AND NOT callee.name STARTS WITH 'get' AND NOT callee.name STARTS WITH 'set'
        RETURN calleeOwner.name as callee_class, callee.name as callee_method,
               callee.SE_What as callee_desc
        LIMIT 10
        """
        return self.run_query(query, {"class_name": class_name, "method_name": method_name})

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _extract_message_payload_type(self, parameters: str) -> str:
        """从方法参数中提取消息载体类型

        Args:
            parameters: 方法参数字符串，如 "(Long orderId)" 或 "(String message, Channel channel)"

        Returns:
            第一个参数的类型，如 "Long"，若无法提取返回 "Unknown"
        """
        if not parameters:
            return "Unknown"
        # 移除首尾括号
        params = parameters.strip("()")
        if not params:
            return "Unknown"
        # 取第一个参数
        first_param = params.split(",")[0].strip()
        # 移除注解（如 @Payload）
        while first_param.startswith("@"):
            parts = first_param.split(None, 1)
            if len(parts) > 1:
                first_param = parts[1].strip()
            else:
                return "Unknown"
        # 提取类型（第一个词）
        parts = first_param.split()
        return parts[0] if parts else "Unknown"

    # ========================================================================
    # Step 1: 锚点发现
    # ========================================================================

    def discover_consumers(self) -> List[Anchor]:
        """发现消息消费者（@RabbitListener / @RabbitHandler）"""
        print("\n[Step 1.1] Discovering Consumers...")

        query = """
        MATCH (c:Class)-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS '@RabbitListener'
           OR m.modifiers CONTAINS '@RabbitHandler'
           OR c.modifiers CONTAINS '@RabbitListener'
        RETURN
            m.nodeId as node_id,
            c.name as class_name,
            m.name as method_name,
            m.source_code as source_code,
            c.source_code as class_source,
            c.modifiers as class_modifiers,
            m.SE_What as se_what,
            m.SE_Why as se_why,
            m.parameters as parameters,
            m.SE_How as se_how
        """
        results = self.run_query(query)

        anchors = []
        for r in results:
            anchor = Anchor(
                node_id=r['node_id'],
                anchor_type=AnchorType.CONSUMER,
                name=r['method_name'],
                class_name=r['class_name'],
                source_code=r['source_code'] or '',
                se_what=r.get('se_what'),
                se_why=r.get('se_why'),
                class_source=r.get('class_source', ''),
                class_modifiers=r.get('class_modifiers', '')
            )
            # 存储额外字段到 extracted_info
            anchor.extracted_info['parameters'] = r.get('parameters', '')
            anchor.extracted_info['se_how'] = r.get('se_how', '')
            anchor.extracted_info['payload_type'] = self._extract_message_payload_type(r.get('parameters', ''))
            anchors.append(anchor)
            print(f"  Found Consumer: {r['class_name']}.{r['method_name']}")

        self.consumers = anchors
        return anchors

    def discover_producers(self) -> List[Anchor]:
        """发现消息生产者（注入了 RabbitTemplate/AmqpTemplate 的类）"""
        print("\n[Step 1.2] Discovering Producers...")

        query = """
        MATCH (c:Class)-[:DECLARES]->(f:Field)
        WHERE f.type CONTAINS 'AmqpTemplate' OR f.type CONTAINS 'RabbitTemplate'
        RETURN
            c.nodeId as node_id,
            c.name as class_name,
            f.name as field_name,
            f.type as template_type,
            c.source_code as source_code,
            c.SE_What as se_what,
            c.SE_Why as se_why
        """
        results = self.run_query(query)

        anchors = []
        for r in results:
            anchor = Anchor(
                node_id=r['node_id'],
                anchor_type=AnchorType.PRODUCER,
                name=r['class_name'],
                class_name=r['class_name'],
                source_code=r['source_code'] or '',
                se_what=r.get('se_what'),
                se_why=r.get('se_why')
            )
            anchors.append(anchor)
            print(f"  Found Producer: {r['class_name']} (has {r['template_type']})")

        self.producers = anchors
        return anchors

    def discover_configs(self) -> List[Anchor]:
        """发现配置（@Bean 返回 Queue/Exchange/Binding）"""
        print("\n[Step 1.3] Discovering Configs...")

        query = """
        MATCH (c:Class)-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS '@Bean'
          AND (
            m.return_type CONTAINS 'Queue' OR
            m.return_type CONTAINS 'Exchange' OR
            m.return_type CONTAINS 'Binding' OR
            m.source_code CONTAINS 'QueueBuilder' OR
            m.source_code CONTAINS 'ExchangeBuilder'
          )
        RETURN
            m.nodeId as node_id,
            c.name as class_name,
            m.name as method_name,
            m.return_type as return_type,
            m.source_code as source_code,
            m.SE_What as se_what
        """
        results = self.run_query(query)

        anchors = []
        for r in results:
            anchor = Anchor(
                node_id=r['node_id'],
                anchor_type=AnchorType.CONFIG,
                name=r['method_name'],
                class_name=r['class_name'],
                source_code=r['source_code'] or '',
                se_what=r.get('se_what')
            )
            anchor.extracted_info['return_type'] = r.get('return_type', '')
            anchors.append(anchor)
            print(f"  Found Config: {r['class_name']}.{r['method_name']}() -> {r['return_type']}")

        self.configs = anchors
        return anchors

    # ========================================================================
    # Step 2: LLM 分析
    # ========================================================================

    async def analyze_anchor(self, anchor: Anchor) -> Dict:
        """使用 LLM 分析一个锚点，提取关键信息"""

        if anchor.anchor_type == AnchorType.CONSUMER:
            prompt_template = PROMPTS["consumer"]
            user_prompt = prompt_template.format(
                class_name=anchor.class_name,
                method_name=anchor.name,
                source_code=anchor.source_code,
                class_modifiers=anchor.class_modifiers or "(类注解不可用)",
                class_source=anchor.class_source or "(类源码不可用)",
                se_what=anchor.se_what or "无"
            )
        elif anchor.anchor_type == AnchorType.PRODUCER:
            prompt_template = PROMPTS["producer"]
            user_prompt = prompt_template.format(
                class_name=anchor.class_name,
                source_code=anchor.source_code,
                se_what=anchor.se_what or "无"
            )
        elif anchor.anchor_type == AnchorType.CONFIG:
            prompt_template = PROMPTS["config"]
            user_prompt = prompt_template.format(
                class_name=anchor.class_name,
                method_name=anchor.name,
                return_type=anchor.extracted_info.get('return_type', ''),
                source_code=anchor.source_code,
                se_what=anchor.se_what or "无"
            )
        elif anchor.anchor_type == AnchorType.ENUM_CONSTANT:
            prompt_template = PROMPTS["enum_constant"]
            user_prompt = prompt_template.format(
                enum_name=anchor.class_name,
                constant_name=anchor.name,
                source_code=anchor.source_code,
                se_what=anchor.se_what or "无"
            )
        else:
            return {}

        system_prompt = "你是一个专业的 Java 代码分析助手，擅长分析 RabbitMQ 消息队列相关的代码。请严格按照要求的 JSON 格式输出。"

        try:
            result = await self.llm.structured_generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema={"type": "object"}
            )
            anchor.extracted_info.update(result)
            return result
        except Exception as e:
            print(f"  [Warning] LLM analysis failed for {anchor.class_name}.{anchor.name}: {e}")
            return {}

    async def analyze_all_anchors(self):
        """分析所有锚点"""
        print("\n[Step 2] Analyzing anchors with LLM...")

        all_anchors = self.consumers + self.producers + self.configs

        for i, anchor in enumerate(all_anchors):
            print(f"  [{i+1}/{len(all_anchors)}] Analyzing {anchor.anchor_type.value}: {anchor.class_name}.{anchor.name}")
            await self.analyze_anchor(anchor)

            # 打印提取的关键信息
            if anchor.extracted_info:
                print(f"    Extracted: {json.dumps(anchor.extracted_info, ensure_ascii=False, indent=2)[:200]}...")

    # ========================================================================
    # Step 3: 迭代探索
    # ========================================================================

    def search_enum_by_value(self, value: str) -> List[Dict]:
        """根据字符串值搜索枚举常量"""
        query = """
        MATCH (e:Enum)-[:DECLARES]->(ec:EnumConstant)
        WHERE ec.source_code CONTAINS $value
        RETURN
            e.name as enum_name,
            ec.name as constant_name,
            ec.nodeId as node_id,
            ec.source_code as source_code,
            ec.SE_What as se_what
        """
        return self.run_query(query, {"value": value})

    def search_enum_by_name(self, enum_class: str, constant_name: str) -> List[Dict]:
        """根据枚举类名和常量名搜索"""
        query = """
        MATCH (e:Enum {name: $enum_class})-[:DECLARES]->(ec:EnumConstant {name: $constant_name})
        RETURN
            e.name as enum_name,
            ec.name as constant_name,
            ec.nodeId as node_id,
            ec.source_code as source_code,
            ec.SE_What as se_what
        """
        return self.run_query(query, {"enum_class": enum_class, "constant_name": constant_name})

    def search_enum_usages(self, enum_class: str, constant_name: str) -> List[Dict]:
        """搜索枚举常量的使用位置"""
        full_ref = f"{enum_class}.{constant_name}"
        query = """
        MATCH (n)
        WHERE n.source_code CONTAINS $full_ref
        RETURN
            labels(n) as types,
            n.nodeId as node_id,
            n.name as name,
            n.source_code as source_code
        LIMIT 20
        """
        return self.run_query(query, {"full_ref": full_ref})

    async def explore_from_anchor(self, anchor: Anchor, depth: int = 0, max_depth: int = 3):
        """从一个锚点出发，迭代探索相关节点"""
        if depth >= max_depth:
            return

        if anchor.node_id in self.explored_nodes:
            return
        self.explored_nodes.add(anchor.node_id)

        info = anchor.extracted_info

        # 根据提取的信息决定下一步探索
        if info.get('needs_lookup'):
            hints = info.get('lookup_hints', []) or [info.get('lookup_hint')]

            for hint in hints:
                if not hint:
                    continue
                print(f"    [Explore] Following hint: {hint}")

        # 如果发现了枚举引用，查找枚举定义
        enum_class = info.get('enum_class')
        enum_constant = info.get('enum_constant')

        if enum_class and enum_constant:
            key = f"{enum_class}.{enum_constant}"
            if key not in self.enum_constants:
                print(f"    [Explore] Looking up enum: {key}")
                results = self.search_enum_by_name(enum_class, enum_constant)

                for r in results:
                    enum_anchor = Anchor(
                        node_id=r['node_id'],
                        anchor_type=AnchorType.ENUM_CONSTANT,
                        name=r['constant_name'],
                        class_name=r['enum_name'],
                        source_code=r['source_code'] or '',
                        se_what=r.get('se_what')
                    )

                    # 分析枚举常量
                    await self.analyze_anchor(enum_anchor)
                    self.enum_constants[key] = enum_anchor
                    print(f"      Found enum definition: {key}")

        # 如果是 Consumer 且有硬编码字符串，搜索枚举定义
        if anchor.anchor_type == AnchorType.CONSUMER:
            queue_id = info.get('queue_identifier')
            id_type = info.get('identifier_type')

            if id_type == 'string' and queue_id:
                print(f"    [Explore] Searching enum for value: {queue_id}")
                results = self.search_enum_by_value(queue_id)

                for r in results:
                    key = f"{r['enum_name']}.{r['constant_name']}"
                    if key not in self.enum_constants:
                        enum_anchor = Anchor(
                            node_id=r['node_id'],
                            anchor_type=AnchorType.ENUM_CONSTANT,
                            name=r['constant_name'],
                            class_name=r['enum_name'],
                            source_code=r['source_code'] or '',
                            se_what=r.get('se_what')
                        )
                        await self.analyze_anchor(enum_anchor)
                        self.enum_constants[key] = enum_anchor
                        print(f"      Found related enum: {key}")

        # 如果是 Config 且有 DLX 配置，追踪 DLX 目标
        if anchor.anchor_type == AnchorType.CONFIG:
            dlx = info.get('dlx_config')
            if dlx and dlx.get('exchange_enum'):
                # 解析枚举引用 (如 "QueueEnum.QUEUE_ORDER_CANCEL")
                enum_ref = dlx['exchange_enum']
                if '.' in enum_ref:
                    parts = enum_ref.replace('.getExchange()', '').replace('.getRouteKey()', '').split('.')
                    if len(parts) >= 2:
                        dlx_enum_class = parts[0]
                        dlx_enum_const = parts[1]
                        key = f"{dlx_enum_class}.{dlx_enum_const}"

                        if key not in self.enum_constants:
                            print(f"    [Explore] Tracing DLX target: {key}")
                            results = self.search_enum_by_name(dlx_enum_class, dlx_enum_const)

                            for r in results:
                                enum_anchor = Anchor(
                                    node_id=r['node_id'],
                                    anchor_type=AnchorType.ENUM_CONSTANT,
                                    name=r['constant_name'],
                                    class_name=r['enum_name'],
                                    source_code=r['source_code'] or '',
                                    se_what=r.get('se_what')
                                )
                                await self.analyze_anchor(enum_anchor)
                                self.enum_constants[key] = enum_anchor
                                print(f"      Found DLX target enum: {key}")

    async def explore_all(self):
        """从所有锚点出发进行探索"""
        print("\n[Step 3] Exploring related nodes...")

        all_anchors = self.consumers + self.producers + self.configs

        for anchor in all_anchors:
            print(f"  Exploring from: {anchor.class_name}.{anchor.name}")
            await self.explore_from_anchor(anchor)

    # ========================================================================
    # Step 5: 链路组装
    # ========================================================================

    async def assemble_flows(self) -> List[MessageFlow]:
        """综合所有信息，构建消息流转链路"""
        print("\n[Step 5] Assembling message flows with LLM...")

        # 准备数据给 LLM
        producers_data = [
            {
                "class": p.class_name,
                "extracted": p.extracted_info
            }
            for p in self.producers
        ]

        consumers_data = [
            {
                "class": c.class_name,
                "method": c.name,
                "extracted": c.extracted_info
            }
            for c in self.consumers
        ]

        configs_data = [
            {
                "class": c.class_name,
                "method": c.name,
                "extracted": c.extracted_info
            }
            for c in self.configs
        ]

        enums_data = [
            {
                "enum": key,
                "extracted": e.extracted_info
            }
            for key, e in self.enum_constants.items()
        ]

        user_prompt = PROMPTS["assemble_flow"].format(
            producers_json=json.dumps(producers_data, ensure_ascii=False, indent=2),
            consumers_json=json.dumps(consumers_data, ensure_ascii=False, indent=2),
            configs_json=json.dumps(configs_data, ensure_ascii=False, indent=2),
            enums_json=json.dumps(enums_data, ensure_ascii=False, indent=2)
        )

        system_prompt = "你是一个专业的消息队列架构分析专家。请根据提供的组件信息，分析并构建完整的消息流转链路。"

        try:
            result = await self.llm.structured_generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema={"type": "object"}
            )

            print(f"  LLM assembled {len(result.get('flows', []))} flows")
            return result
        except Exception as e:
            print(f"  [Error] Flow assembly failed: {e}")
            return {"flows": [], "error": str(e)}

    # ========================================================================
    # 报告生成
    # ========================================================================

    def _resolve_enum_value(self, enum_ref: str, field: str = 'queue_name') -> str:
        """解析枚举引用为实际值

        Args:
            enum_ref: 枚举引用，如 "QueueEnum.QUEUE_ORDER_CANCEL.getName()"
            field: 要提取的字段 ('queue_name', 'exchange', 'routing_key')

        Returns:
            解析后的实际值，如果无法解析则返回原始引用
        """
        if not enum_ref or not isinstance(enum_ref, str):
            return enum_ref

        # 提取枚举常量 key，移除方法调用后缀
        key = enum_ref
        for suffix in ['.getExchange()', '.getRouteKey()', '.getName()', '.getValue()']:
            key = key.replace(suffix, '')

        # 在 enum_constants 中查找
        if key in self.enum_constants:
            info = self.enum_constants[key].extracted_info
            if field == 'exchange':
                return info.get('exchange_name', enum_ref)
            elif field == 'routing_key':
                return info.get('routing_key', enum_ref)
            else:
                return info.get('queue_name', enum_ref)

        return enum_ref

    def _filter_internal_fields(self, info: Dict) -> Dict:
        """过滤内部处理字段，保留对用户有意义的信息

        Args:
            info: 原始的 extracted_info 字典

        Returns:
            过滤后的字典
        """
        exclude_fields = {'needs_lookup', 'lookup_hints', 'lookup_hint', 'identifier_type'}
        return {k: v for k, v in info.items() if k not in exclude_fields}

    def _generate_name_resolution_table(self) -> str:
        """生成枚举常量名称解析表

        Returns:
            Markdown 格式的表格字符串
        """
        if not self.enum_constants:
            return ""

        lines = ["## 枚举常量解析表\n"]
        lines.append("| 枚举常量 | 队列名称 | 交换机名称 | 路由键 |")
        lines.append("|----------|----------|------------|--------|")

        for key, anchor in self.enum_constants.items():
            info = anchor.extracted_info
            queue = info.get('queue_name', '-')
            exchange = info.get('exchange_name', '-')
            routing_key = info.get('routing_key', '-')
            lines.append(f"| `{key}` | {queue} | {exchange} | {routing_key} |")

        lines.append("")
        return "\n".join(lines)

    def _generate_producers_table(self) -> str:
        """生成 Producers 表格"""
        if not self.producers:
            return "未发现生产者。\n"

        lines = ["| 类名 | 目标（交换机/队列） | 路由键 | 枚举引用 |"]
        lines.append("|------|---------------------|--------|----------|")

        for p in self.producers:
            info = p.extracted_info
            class_name = p.class_name

            # 从 send_calls 数组中提取信息
            send_calls = info.get('send_calls', [])
            if send_calls:
                for call in send_calls:
                    target = call.get('target_identifier', '-')
                    routing_key = call.get('routing_key', '-')

                    # 构建枚举引用描述
                    enum_ref = '-'
                    enum_class = call.get('enum_class')
                    enum_const = call.get('enum_constant')
                    if enum_class and enum_const:
                        enum_ref = f"`{enum_class}.{enum_const}`"
                        # 尝试解析实际值
                        full_key = f"{enum_class}.{enum_const}"
                        if full_key in self.enum_constants:
                            resolved = self.enum_constants[full_key].extracted_info
                            if call.get('target_type') == 'exchange':
                                target = resolved.get('exchange_name', target)
                            routing_key = resolved.get('routing_key', routing_key)

                    lines.append(f"| `{class_name}` | {target} | {routing_key} | {enum_ref} |")
            else:
                lines.append(f"| `{class_name}` | - | - | - |")

        lines.append("")
        return "\n".join(lines)

    def _generate_consumers_table(self) -> str:
        """生成 Consumers 表格"""
        if not self.consumers:
            return "未发现消费者。\n"

        lines = ["| 类名.方法 | 队列标识符 | 解析后队列名 | 枚举引用 |"]
        lines.append("|-----------|------------|--------------|----------|")

        for c in self.consumers:
            info = c.extracted_info
            full_name = f"{c.class_name}.{c.name}"

            # 从 LLM 返回的字段提取
            queue_identifier = info.get('queue_identifier', '-')
            identifier_type = info.get('identifier_type', 'unknown')

            # 构建枚举引用描述并解析实际值
            enum_ref = '-'
            resolved_queue = queue_identifier
            enum_class = info.get('enum_class')
            enum_const = info.get('enum_constant')

            if enum_class and enum_const:
                enum_ref = f"`{enum_class}.{enum_const}`"
                full_key = f"{enum_class}.{enum_const}"
                if full_key in self.enum_constants:
                    resolved = self.enum_constants[full_key].extracted_info
                    resolved_queue = resolved.get('queue_name', queue_identifier)

            lines.append(f"| `{full_name}` | {queue_identifier} | {resolved_queue} | {enum_ref} |")

        lines.append("")
        return "\n".join(lines)

    def _generate_configs_table(self) -> str:
        """生成 Configs 表格"""
        if not self.configs:
            return "未发现配置 Bean。\n"

        lines = ["| Bean 方法 | 类型 | 名称标识符 | 解析后名称 | 死信配置 | TTL |"]
        lines.append("|-----------|------|------------|------------|----------|-----|")

        for c in self.configs:
            info = c.extracted_info
            bean_method = f"{c.class_name}.{c.name}"
            bean_type = info.get('bean_type', '-')

            # 名称标识符
            name_identifier = info.get('name_identifier', '-')
            resolved_name = name_identifier

            # 尝试解析枚举引用
            enum_class = info.get('enum_class')
            enum_const = info.get('enum_constant')
            if enum_class and enum_const:
                full_key = f"{enum_class}.{enum_const}"
                if full_key in self.enum_constants:
                    resolved = self.enum_constants[full_key].extracted_info
                    if bean_type == 'queue':
                        resolved_name = resolved.get('queue_name', name_identifier)
                    elif bean_type == 'exchange':
                        resolved_name = resolved.get('exchange_name', name_identifier)
                    else:
                        resolved_name = resolved.get('queue_name', resolved.get('exchange_name', name_identifier))

            # 死信配置
            dlx_config = info.get('dlx_config')
            dlx_str = '-'
            if dlx_config and isinstance(dlx_config, dict):
                dlx_ex = dlx_config.get('exchange', '')
                dlx_rk = dlx_config.get('routing_key', '')

                # 解析枚举引用
                if dlx_ex and isinstance(dlx_ex, str):
                    dlx_ex = self._resolve_enum_value(dlx_ex, 'exchange')
                if dlx_rk and isinstance(dlx_rk, str):
                    dlx_rk = self._resolve_enum_value(dlx_rk, 'routing_key')

                if dlx_ex or dlx_rk:
                    dlx_str = f"{dlx_ex} / {dlx_rk}"

            # TTL
            ttl = info.get('ttl_ms', '-')
            ttl_str = f"{ttl}ms" if ttl and ttl != '-' else '-'

            lines.append(f"| `{bean_method}` | {bean_type} | {name_identifier} | {resolved_name} | {dlx_str} | {ttl_str} |")

        lines.append("")
        return "\n".join(lines)

    def _generate_consumer_cards(self) -> str:
        """生成消费者卡片式布局"""
        if not self.consumers:
            return "未发现消费者。\n"

        lines = []
        for c in self.consumers:
            info = c.extracted_info

            # 队列信息
            queue_identifier = info.get('queue_identifier', '-')
            enum_class = info.get('enum_class')
            enum_const = info.get('enum_constant')
            resolved_queue = queue_identifier
            if enum_class and enum_const:
                full_key = f"{enum_class}.{enum_const}"
                if full_key in self.enum_constants:
                    resolved = self.enum_constants[full_key].extracted_info
                    resolved_queue = resolved.get('queue_name', queue_identifier)

            # 消息载体类型
            payload_type = info.get('payload_type', 'Unknown')

            # 业务语义
            se_why = c.se_why or "暂无业务目的描述"
            se_how = info.get('se_how', '') or "暂无处理逻辑描述"

            # 卡片头
            lines.append(f"### 消费者: `{c.class_name}.{c.name}`\n")
            lines.append(f"- **监听队列**: `{resolved_queue}`")
            lines.append(f"- **消息载体**: `{payload_type}`")
            lines.append(f"- **业务目的**: {se_why}")
            lines.append(f"- **处理逻辑**: {se_how}")
            lines.append("")

            # 调用的业务方法
            callees = info.get('callees', [])
            if callees:
                lines.append("**调用的业务方法**:\n")
                lines.append("| 目标类 | 方法 | 说明 |")
                lines.append("|--------|------|------|")
                for callee in callees:
                    callee_class = callee.get('callee_class', '-')
                    callee_method = callee.get('callee_method', '-')
                    callee_desc = callee.get('callee_desc', '-') or '-'
                    lines.append(f"| {callee_class} | {callee_method} | {callee_desc} |")
                lines.append("")

            lines.append("---\n")

        return "\n".join(lines)

    def _generate_producer_cards(self) -> str:
        """生成生产者卡片式布局"""
        if not self.producers:
            return "未发现生产者。\n"

        lines = []
        for p in self.producers:
            info = p.extracted_info

            # 业务描述
            se_what = p.se_what or "暂无功能描述"

            # 卡片头
            lines.append(f"### 发送组件: `{p.class_name}`\n")
            lines.append(f"> {se_what}\n")

            # 从 send_calls 提取目标信息
            send_calls = info.get('send_calls', [])
            if send_calls:
                for call in send_calls:
                    target = call.get('target_identifier', '-')
                    routing_key = call.get('routing_key', '-')

                    # 解析枚举引用
                    enum_class = call.get('enum_class')
                    enum_const = call.get('enum_constant')
                    if enum_class and enum_const:
                        full_key = f"{enum_class}.{enum_const}"
                        if full_key in self.enum_constants:
                            resolved = self.enum_constants[full_key].extracted_info
                            if call.get('target_type') == 'exchange':
                                target = resolved.get('exchange_name', target)
                            routing_key = resolved.get('routing_key', routing_key)

                    lines.append(f"- **目标交换机**: `{target}`")
                    lines.append(f"- **路由键**: `{routing_key}`")
            else:
                lines.append("- **目标**: 未识别到发送调用")

            lines.append("")

            # 触发业务方
            callers = info.get('callers', [])
            if callers:
                lines.append("**触发业务方**:\n")
                lines.append("| 业务类 | 方法 | 业务场景 |")
                lines.append("|--------|------|----------|")
                for caller in callers:
                    caller_class = caller.get('caller_class', '-')
                    caller_method = caller.get('caller_method', '-')
                    caller_desc = caller.get('caller_desc', '-') or '-'
                    lines.append(f"| {caller_class} | {caller_method} | {caller_desc} |")
                lines.append("")

            lines.append("---\n")

        return "\n".join(lines)

    def generate_report(self, flows_result: Dict, output_path: str):
        """生成 Markdown 报告"""
        print(f"\n[Step 6] Generating report: {output_path}")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# RabbitMQ 消息流分析报告\n\n")
            f.write("> 由 `rabbitmq_flow_analyzer.py` 基于 LLM 分析生成\n\n")

            # 概览
            f.write("## 概览\n\n")
            f.write(f"- **生产者数量**: {len(self.producers)}\n")
            f.write(f"- **消费者数量**: {len(self.consumers)}\n")
            f.write(f"- **配置 Bean 数量**: {len(self.configs)}\n")
            f.write(f"- **枚举常量数量**: {len(self.enum_constants)}\n\n")

            # 名称解析表（枚举常量）
            name_resolution_table = self._generate_name_resolution_table()
            if name_resolution_table:
                f.write(name_resolution_table)
                f.write("\n")

            # 消息流
            flows = flows_result.get('flows', [])
            if flows:
                f.write("## 消息流转链路\n\n")

                for i, flow in enumerate(flows, 1):
                    f.write(f"### 链路 {i}: {flow.get('producer_class', '?')} → {flow.get('consumer_class', '?')}\n\n")
                    f.write(f"**置信度**: {flow.get('confidence', 'unknown')}\n\n")
                    f.write(f"**流转路径**: {flow.get('path_description', '无')}\n\n")

                    # Mermaid 图
                    steps = flow.get('path_steps', [])
                    if steps and len(steps) >= 2:
                        f.write("```mermaid\ngraph LR\n")
                        for j, step in enumerate(steps):
                            component = step.get('component', '?')
                            action = step.get('action', '')
                            # 根据组件类型选择节点形状
                            if 'Sender' in component or 'Producer' in component:
                                node_def = f"S{j}([{component}])"
                            elif 'Receiver' in component or 'Consumer' in component or 'Listener' in component:
                                node_def = f"S{j}([{component}])"
                            elif 'Exchange' in component.lower() or 'exchange' in component:
                                node_def = f"S{j}{{{{{component}}}}}"
                            elif 'Queue' in component.lower() or 'queue' in component or component.startswith('mall.'):
                                node_def = f"S{j}[({component})]"
                            else:
                                node_def = f"S{j}[{component}]"

                            if j == 0:
                                f.write(f"    {node_def}\n")

                            if j < len(steps) - 1:
                                next_step = steps[j + 1]
                                next_component = next_step.get('component', '?')
                                next_action = next_step.get('action', '')
                                # 下一个节点的形状
                                if 'Sender' in next_component or 'Producer' in next_component:
                                    next_node = f"S{j+1}([{next_component}])"
                                elif 'Receiver' in next_component or 'Consumer' in next_component or 'Listener' in next_component:
                                    next_node = f"S{j+1}([{next_component}])"
                                elif 'Exchange' in next_component.lower() or 'exchange' in next_component:
                                    next_node = f"S{j+1}{{{{{next_component}}}}}"
                                elif 'Queue' in next_component.lower() or 'queue' in next_component or next_component.startswith('mall.'):
                                    next_node = f"S{j+1}[({next_component})]"
                                else:
                                    next_node = f"S{j+1}[{next_component}]"

                                # 添加边标签
                                if action:
                                    f.write(f"    S{j} -->|{action}| {next_node}\n")
                                else:
                                    f.write(f"    S{j} --> {next_node}\n")
                        f.write("```\n\n")
                    elif steps and len(steps) == 1:
                        # 只有一个步骤时显示简单图
                        component = steps[0].get('component', '?')
                        f.write("```mermaid\ngraph LR\n")
                        f.write(f"    S0([{component}])\n")
                        f.write("```\n\n")
                    else:
                        # 没有步骤时，基于 producer 和 consumer 生成简单图
                        producer = flow.get('producer_class', '?')
                        consumer = flow.get('consumer_class', '?')
                        f.write("```mermaid\ngraph LR\n")
                        f.write(f"    P([{producer}]) -->|消息| C([{consumer}])\n")
                        f.write("```\n\n")

                    f.write(f"**分析依据**: {flow.get('reasoning', '无')}\n\n")
                    f.write("---\n\n")

            # 未关联的组件
            unlinked_producers = flows_result.get('unlinked_producers', [])
            unlinked_consumers = flows_result.get('unlinked_consumers', [])

            if unlinked_producers or unlinked_consumers:
                f.write("## 未关联组件\n\n")

                if unlinked_producers:
                    f.write("### 未关联的生产者\n")
                    for p in unlinked_producers:
                        f.write(f"- {p}\n")
                    f.write("\n")

                if unlinked_consumers:
                    f.write("### 未关联的消费者\n")
                    for c in unlinked_consumers:
                        f.write(f"- {c}\n")
                    f.write("\n")

            # 组件详情（卡片式布局）
            f.write("## 组件详情\n\n")

            # 消费者卡片
            f.write(self._generate_consumer_cards())

            # 生产者卡片
            f.write(self._generate_producer_cards())

            # 配置 Bean（保留表格形式）
            f.write("## 配置 Bean\n\n")
            f.write(self._generate_configs_table())

            # 枚举常量原始数据（折叠）
            if self.enum_constants:
                f.write("<details>\n<summary>点击展开枚举详情</summary>\n\n")
                for key, e in self.enum_constants.items():
                    filtered_info = self._filter_internal_fields(e.extracted_info)
                    f.write(f"#### {key}\n")
                    f.write(f"```json\n{json.dumps(filtered_info, ensure_ascii=False, indent=2)}\n```\n\n")
                f.write("</details>\n\n")

        print(f"  Report saved to: {output_path}")

    # ========================================================================
    # Step 4: 调用链查询
    # ========================================================================

    def query_call_chains(self):
        """查询所有组件的调用链"""
        print("\n[Step 4] Querying call chains...")

        # 为消费者查询下游调用
        for consumer in self.consumers:
            callees = self.query_callee_chain(consumer.class_name, consumer.name)
            consumer.extracted_info['callees'] = callees
            if callees:
                print(f"  Consumer {consumer.class_name}.{consumer.name} calls {len(callees)} methods")

        # 为生产者查询上游调用者
        for producer in self.producers:
            # 找到包含 convertAndSend 的方法
            query = """
            MATCH (c:Class {name: $class_name})-[:DECLARES]->(m:Method)
            WHERE m.source_code CONTAINS 'convertAndSend'
            RETURN m.name as method_name
            """
            send_methods = self.run_query(query, {"class_name": producer.class_name})

            all_callers = []
            for sm in send_methods:
                callers = self.query_caller_chain(producer.class_name, sm['method_name'])
                all_callers.extend(callers)
            producer.extracted_info['callers'] = all_callers
            if all_callers:
                print(f"  Producer {producer.class_name} is called by {len(all_callers)} methods")

    # ========================================================================
    # 主流程
    # ========================================================================

    async def run(self, output_path: str = "rabbitmq_flow_report.md"):
        """执行完整的分析流程"""
        print("=" * 60)
        print("RabbitMQ Flow Analyzer")
        print("=" * 60)

        try:
            # Step 1: 锚点发现
            self.discover_consumers()
            self.discover_producers()
            self.discover_configs()

            if not self.consumers and not self.producers:
                print("\n[Warning] No RabbitMQ components found!")
                return

            # Step 2: LLM 分析
            await self.analyze_all_anchors()

            # Step 3: 迭代探索
            await self.explore_all()

            # Step 4: 调用链查询
            self.query_call_chains()

            # Step 5: 链路组装
            flows_result = await self.assemble_flows()

            # Step 6: 生成报告
            self.generate_report(flows_result, output_path)

            print("\n" + "=" * 60)
            print("Analysis Complete!")
            print("=" * 60)

        finally:
            self.close()


# ============================================================================
# 入口
# ============================================================================

async def main():
    if not OPENAI_API_KEY and LLM_PROVIDER == "openai":
        print("[Error] OPENAI_API_KEY environment variable is not set!")
        print("Please set it before running the script:")
        print("  export OPENAI_API_KEY=your_api_key")
        print("  # or on Windows:")
        print("  set OPENAI_API_KEY=your_api_key")
        return

    analyzer = RabbitMQFlowAnalyzer(
        neo4j_uri=NEO4J_URI,
        neo4j_user=NEO4J_USER,
        neo4j_password=NEO4J_PASSWORD,
        llm_provider=LLM_PROVIDER,
        llm_model=LLM_MODEL,
        api_key=OPENAI_API_KEY
    )

    await analyzer.run(output_path="rabbitmq_flow_report.md")


if __name__ == "__main__":
    asyncio.run(main())
