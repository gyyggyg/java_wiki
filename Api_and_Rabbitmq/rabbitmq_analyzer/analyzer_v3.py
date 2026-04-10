"""
RabbitMQ Flow Analyzer v3 - 通用的消息链路分析工具

设计思路：
1. 确定性查询：基于 Spring AMQP 标准注解查询组件
2. LLM 提取：用通用 prompt 让 LLM 理解不同写法的代码，输出结构化信息
3. 确定性匹配：基于 RabbitMQ 概念（Exchange→Queue→Consumer）匹配链路

通用性保证：
- 查询基于 Spring AMQP 标准（@RabbitListener, AmqpTemplate, @Bean 等）
- LLM prompt 不假设特定的代码风格
- 链路匹配基于 RabbitMQ 通用概念
"""

import os
import re
import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from neo4j import GraphDatabase
from llm_interface import LLMInterface


# ============================================================================
# 配置
# ============================================================================

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7689")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "c8a3974ba62qcc2")

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4.1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your_openai_api_key_here")

# 项目根目录（neo4j 图中路径不含根目录，需要拼接）
PROJECT_ROOT = os.environ.get("PROJECT_ROOT", "mall")


# ============================================================================
# 通用 Prompt 模板
# ============================================================================

PROMPTS = {
    "consumer": """你是一个 Java Spring AMQP 代码分析专家。

## 任务
分析以下 RabbitMQ 消费者代码，提取监听信息。

## 输入
类名：{class_name}
方法名：{method_name}

源码：
```java
{source_code}
```

类级别源码（可能包含类注解）：
```java
{class_source}
```

已有语义描述（供参考）：{se_what}

## 分析要求
请从代码中提取消费者监听的队列信息。队列可能以多种形式定义：
- 硬编码字符串：queues = "order.queue"
- 常量/枚举引用：queues = QueueConstants.ORDER
- 配置占位符：queues = "${{mq.queue.name}}"
- SpEL 表达式：queues = "#{{config.queueName}}"
- @QueueBinding 形式

请尽可能解析出实际的队列名称。如果是引用形式，请同时提供引用表达式和可能的实际值。

## 输出格式
返回 JSON：
```json
{{
    "queue_name": "解析出的队列名称，如果无法确定则为 null",
    "queue_expression": "原始表达式（如 QueueEnum.ORDER.getName()）",
    "binding_info": {{
        "exchange": "如果使用 @QueueBinding，交换机名称",
        "routing_key": "如果使用 @QueueBinding，路由键"
    }} | null
}}
```""",

    "producer": """你是一个 Java Spring AMQP 代码分析专家。

## 任务
分析以下 RabbitMQ 生产者代码，提取消息发送目标信息。

## 输入
类名：{class_name}

源码：
```java
{source_code}
```

已有语义描述（供参考）：{se_what}

## 分析要求
请从代码中提取消息发送的目标信息。关注以下方法调用：
- convertAndSend(exchange, routingKey, message)
- convertAndSend(routingKey, message)
- send(message)

目标可能以多种形式定义：
- 硬编码字符串
- 常量/枚举引用
- 成员变量
- 方法参数

请尽可能解析出实际的交换机名称和路由键。

## 输出格式
返回 JSON：
```json
{{
    "exchange": "交换机名称，如果无法确定则为 null",
    "exchange_expression": "原始表达式",
    "routing_key": "路由键，如果无法确定则为 null",
    "routing_key_expression": "原始表达式"
}}
```""",

    "queue_config": """你是一个 Java Spring AMQP 代码分析专家。

## 任务
分析以下 RabbitMQ 队列配置代码（@Bean 方法），提取队列配置信息。

## 输入
方法名：{method_name}

源码：
```java
{source_code}
```

已有语义描述（供参考）：{se_what}

## 分析要求
请从代码中提取：
1. 队列名称（可能是字符串、枚举引用等）
2. 是否配置了死信（x-dead-letter-exchange, x-dead-letter-routing-key）
3. 是否配置了 TTL（x-message-ttl）
4. 其他重要配置

## 输出格式
返回 JSON：
```json
{{
    "queue_name": "队列名称，如果无法确定则为 null",
    "queue_expression": "原始表达式",
    "is_durable": true/false,
    "dlx": {{
        "exchange": "死信交换机名称",
        "exchange_expression": "原始表达式",
        "routing_key": "死信路由键",
        "routing_key_expression": "原始表达式"
    }} | null,
    "ttl_ms": "TTL 毫秒数" | null
}}
```""",

    "exchange_config": """你是一个 Java Spring AMQP 代码分析专家。

## 任务
分析以下 RabbitMQ 交换机配置代码（@Bean 方法），提取交换机配置信息。

## 输入
方法名：{method_name}

源码：
```java
{source_code}
```

已有语义描述（供参考）：{se_what}

## 分析要求
请从代码中提取：
1. 交换机名称
2. 交换机类型（Direct, Topic, Fanout, Headers）
3. 是否持久化

## 输出格式
返回 JSON：
```json
{{
    "exchange_name": "交换机名称，如果无法确定则为 null",
    "exchange_expression": "原始表达式",
    "exchange_type": "direct|topic|fanout|headers",
    "is_durable": true/false
}}
```""",

    "binding_config": """你是一个 Java Spring AMQP 代码分析专家。

## 任务
分析以下 RabbitMQ 绑定配置代码（@Bean 方法），提取绑定关系信息。

## 输入
方法名：{method_name}

源码：
```java
{source_code}
```

已有语义描述（供参考）：{se_what}

## 分析要求
请从代码中提取：
1. 绑定的队列
2. 绑定的交换机
3. 路由键

注意：队列和交换机可能通过方法参数注入，参数名通常对应其他 @Bean 方法名。

## 输出格式
返回 JSON：
```json
{{
    "queue_name": "队列名称，如果无法确定则为 null",
    "queue_bean": "队列 Bean 名称（方法参数名）",
    "exchange_name": "交换机名称，如果无法确定则为 null",
    "exchange_bean": "交换机 Bean 名称（方法参数名）",
    "routing_key": "路由键，如果无法确定则为 null",
    "routing_key_expression": "原始表达式"
}}
```"""
}


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class Component:
    """基础组件"""
    class_name: str
    method_name: str
    source_code: str
    se_what: str
    extracted: Dict = field(default_factory=dict)
    neo4j_ids: List[int] = field(default_factory=list)  # 关联的 Neo4j 节点 nodeId
    source_path: str = ""  # 源文件路径（不含项目根目录）


@dataclass
class Consumer(Component):
    """消息消费者"""
    queue_name: Optional[str] = None
    payload_type: str = "Unknown"
    se_why: str = ""
    se_how: str = ""


@dataclass
class Producer(Component):
    """消息生产者"""
    exchange: Optional[str] = None
    routing_key: Optional[str] = None
    callers: List[Dict] = field(default_factory=list)


@dataclass
class QueueConfig(Component):
    """队列配置"""
    queue_name: Optional[str] = None
    dlx_exchange: Optional[str] = None
    dlx_routing_key: Optional[str] = None
    ttl_ms: Optional[int] = None


@dataclass
class ExchangeConfig(Component):
    """交换机配置"""
    exchange_name: Optional[str] = None
    exchange_type: str = "direct"


@dataclass
class BindingConfig(Component):
    """绑定配置"""
    queue_name: Optional[str] = None
    queue_bean: Optional[str] = None
    exchange_name: Optional[str] = None
    exchange_bean: Optional[str] = None
    routing_key: Optional[str] = None


# ============================================================================
# 核心分析器
# ============================================================================

class RabbitMQAnalyzer:
    """RabbitMQ 消息流分析器 v3"""

    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.llm = LLMInterface(
            model_name=LLM_MODEL,
            provider=LLM_PROVIDER,
            temperature=0.1,
            api_key=OPENAI_API_KEY
        )

        # 组件存储
        self.consumers: List[Consumer] = []
        self.producers: List[Producer] = []
        self.queues: List[QueueConfig] = []
        self.exchanges: List[ExchangeConfig] = []
        self.bindings: List[BindingConfig] = []

        # 枚举值缓存（用于解析枚举引用）
        self.enum_values: Dict[str, Dict[str, str]] = {}  # key: "EnumClass.CONSTANT" -> {exchange, queue, routing_key}

    def close(self):
        self.driver.close()

    def run_query(self, query: str, params: Dict = None) -> List[Dict]:
        """执行 Cypher 查询"""
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    # ========================================================================
    # Step 1: 确定性查询（基于 Spring AMQP 标准）
    # ========================================================================

    def query_components(self):
        """查询所有 RabbitMQ 相关组件"""
        print("\n[Step 1] 确定性查询组件...")

        self._query_enum_constants()  # 先查枚举，后续解析需要
        self._query_consumers()
        self._query_producers()
        self._query_queue_configs()
        self._query_exchange_configs()
        self._query_binding_configs()

        print(f"  - 枚举常量: {len(self.enum_values)}")
        print(f"  - 消费者: {len(self.consumers)}")
        print(f"  - 生产者: {len(self.producers)}")
        print(f"  - 队列配置: {len(self.queues)}")
        print(f"  - 交换机配置: {len(self.exchanges)}")
        print(f"  - 绑定配置: {len(self.bindings)}")

    def _query_enum_constants(self):
        """查询消息队列相关枚举常量"""
        query = """
        MATCH (e:Enum)-[:DECLARES]->(ec:EnumConstant)
        WHERE e.name CONTAINS 'Queue' OR e.name CONTAINS 'MQ' OR e.name CONTAINS 'Message'
           OR ec.source_code CONTAINS 'exchange' OR ec.source_code CONTAINS 'queue'
        RETURN e.name as enum_class,
               ec.name as constant_name,
               ec.source_code as source_code
        """
        for r in self.run_query(query):
            source = r.get('source_code') or ''
            # 解析枚举构造函数参数
            match = re.search(r'\w+\s*\(\s*(.+)\s*\)', source)
            if match:
                args = re.findall(r'"([^"]*)"', match.group(1))
                if len(args) >= 3:
                    key = f"{r['enum_class']}.{r['constant_name']}"
                    self.enum_values[key] = {
                        'exchange': args[0],
                        'queue': args[1],
                        'routing_key': args[2]
                    }

    def _resolve_value(self, *expressions: Optional[str]) -> Optional[str]:
        """统一的值解析方法，依次尝试多个表达式

        解析顺序：
        1. 如果是简单字面量（不含方法调用），直接返回
        2. 尝试解析枚举引用
        3. 如果以上都不匹配，作为字面量返回
        """
        for expr in expressions:
            if not expr:
                continue

            # 去除可能的引号
            expr_clean = expr.strip('"\'')

            # 1. 检查是否需要解析枚举
            if '()' in expr:
                # 方法调用: getName()，尝试解析枚举
                enum_value = self._resolve_enum_ref(expr)
                if enum_value:
                    return enum_value

            # 2. 简单字面量（可能包含点号如 mall.order.cancel）
            return expr_clean

        return None

    def _resolve_enum_ref(self, ref: str) -> Optional[str]:
        """解析枚举引用，返回实际值

        例如: QueueEnum.QUEUE_ORDER_CANCEL.getExchange() -> mall.order.direct
        """
        if not ref:
            return None

        # 匹配: EnumClass.CONSTANT.getXxx()
        match = re.search(r'(\w+)\.(\w+)\.(get\w+)\(\)', ref)
        if match:
            enum_class = match.group(1)
            constant = match.group(2)
            getter = match.group(3).lower()

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

    def _query_consumers(self):
        """查询消费者 - 基于 @RabbitListener/@RabbitHandler"""
        query = """
        MATCH (f:File)-[:DECLARES]->(c:Class)-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS '@RabbitHandler'
           OR m.modifiers CONTAINS '@RabbitListener'
           OR c.modifiers CONTAINS '@RabbitListener'
        RETURN c.name as class_name,
               c.source_code as class_source,
               m.name as method_name,
               m.source_code as source_code,
               m.parameters as parameters,
               m.SE_What as se_what,
               m.SE_Why as se_why,
               m.SE_How as se_how,
               c.nodeId as class_id,
               m.nodeId as method_id,
               f.name as file_path
        """
        for r in self.run_query(query):
            # 提取消息载体类型
            params = r.get('parameters', '') or ''
            payload_type = "Unknown"
            if params.strip("()"):
                first_param = params.strip("()").split(",")[0].strip()
                parts = first_param.split()
                if parts:
                    payload_type = parts[0]

            neo4j_ids = [rid for rid in [r.get('class_id'), r.get('method_id')] if rid is not None]

            self.consumers.append(Consumer(
                class_name=r['class_name'],
                method_name=r['method_name'],
                source_code=(r.get('class_source') or '') + '\n' + (r.get('source_code') or ''),
                se_what=r.get('se_what') or '',
                se_why=r.get('se_why') or '',
                se_how=r.get('se_how') or '',
                payload_type=payload_type,
                neo4j_ids=neo4j_ids,
                source_path=r.get('file_path') or ''
            ))

    def _query_producers(self):
        """查询生产者 - 基于 AmqpTemplate/RabbitTemplate"""
        query = """
        MATCH (file:File)-[:DECLARES]->(c:Class)-[:DECLARES]->(f:Field)
        WHERE f.type CONTAINS 'AmqpTemplate' OR f.type CONTAINS 'RabbitTemplate'
        RETURN DISTINCT c.name as class_name,
               c.source_code as source_code,
               c.SE_What as se_what,
               c.nodeId as class_id,
               file.name as file_path
        """
        for r in self.run_query(query):
            neo4j_ids = [r['class_id']] if r.get('class_id') is not None else []
            self.producers.append(Producer(
                class_name=r['class_name'],
                method_name='',
                source_code=r.get('source_code') or '',
                se_what=r.get('se_what') or '',
                neo4j_ids=neo4j_ids,
                source_path=r.get('file_path') or ''
            ))

        # 查询调用方
        self._query_producer_callers()

    def _query_producer_callers(self):
        """查询生产者的调用方"""
        for producer in self.producers:
            query = """
            MATCH (c:Class {name: $class_name})-[:DECLARES]->(m:Method)
            WHERE m.source_code CONTAINS 'convertAndSend' OR m.source_code CONTAINS '.send('
            MATCH (caller:Method)-[:CALLS]->(m)
            MATCH (callerClass)-[:DECLARES]->(caller)
            OPTIONAL MATCH (callerFile:File)-[:DECLARES]->(callerClass)
            RETURN callerClass.name as caller_class,
                   caller.name as caller_method,
                   caller.SE_What as caller_desc,
                   caller.nodeId as caller_method_id,
                   callerClass.nodeId as caller_class_id,
                   callerFile.name as caller_file_path
            LIMIT 10
            """
            producer.callers = self.run_query(query, {"class_name": producer.class_name})

    def _query_queue_configs(self):
        """查询队列配置 - 基于 @Bean + Queue"""
        query = """
        MATCH (f:File)-[:DECLARES]->(c:Class)-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS '@Bean'
          AND (m.return_type CONTAINS 'Queue' AND NOT m.return_type CONTAINS 'Binding')
        RETURN m.name as method_name,
               m.source_code as source_code,
               m.SE_What as se_what,
               m.nodeId as method_id,
               c.nodeId as class_id,
               f.name as file_path
        """
        for r in self.run_query(query):
            neo4j_ids = [rid for rid in [r.get('class_id'), r.get('method_id')] if rid is not None]
            self.queues.append(QueueConfig(
                class_name='',
                method_name=r['method_name'],
                source_code=r.get('source_code') or '',
                se_what=r.get('se_what') or '',
                neo4j_ids=neo4j_ids,
                source_path=r.get('file_path') or ''
            ))

    def _query_exchange_configs(self):
        """查询交换机配置 - 基于 @Bean + Exchange"""
        query = """
        MATCH (f:File)-[:DECLARES]->(c:Class)-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS '@Bean'
          AND m.return_type CONTAINS 'Exchange'
        RETURN m.name as method_name,
               m.source_code as source_code,
               m.SE_What as se_what,
               m.nodeId as method_id,
               c.nodeId as class_id,
               f.name as file_path
        """
        for r in self.run_query(query):
            neo4j_ids = [rid for rid in [r.get('class_id'), r.get('method_id')] if rid is not None]
            self.exchanges.append(ExchangeConfig(
                class_name='',
                method_name=r['method_name'],
                source_code=r.get('source_code') or '',
                se_what=r.get('se_what') or '',
                neo4j_ids=neo4j_ids,
                source_path=r.get('file_path') or ''
            ))

    def _query_binding_configs(self):
        """查询绑定配置 - 基于 @Bean + Binding"""
        query = """
        MATCH (f:File)-[:DECLARES]->(c:Class)-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS '@Bean'
          AND m.return_type CONTAINS 'Binding'
        RETURN m.name as method_name,
               m.source_code as source_code,
               m.SE_What as se_what,
               m.nodeId as method_id,
               c.nodeId as class_id,
               f.name as file_path
        """
        for r in self.run_query(query):
            neo4j_ids = [rid for rid in [r.get('class_id'), r.get('method_id')] if rid is not None]
            self.bindings.append(BindingConfig(
                class_name='',
                method_name=r['method_name'],
                source_code=r.get('source_code') or '',
                se_what=r.get('se_what') or '',
                neo4j_ids=neo4j_ids,
                source_path=r.get('file_path') or ''
            ))

    # ========================================================================
    # Step 2: LLM 提取结构化信息
    # ========================================================================

    async def extract_with_llm(self):
        """使用 LLM 提取各组件的结构化信息"""
        print("\n[Step 2] LLM 提取结构化信息...")

        total = len(self.consumers) + len(self.producers) + len(self.queues) + \
                len(self.exchanges) + len(self.bindings)
        current = 0

        # 提取消费者信息
        for consumer in self.consumers:
            current += 1
            print(f"  [{current}/{total}] 分析消费者: {consumer.class_name}.{consumer.method_name}")
            result = await self._llm_extract(PROMPTS["consumer"], {
                "class_name": consumer.class_name,
                "method_name": consumer.method_name,
                "source_code": consumer.source_code,
                "class_source": "",
                "se_what": consumer.se_what
            })
            consumer.extracted = result
            # 统一解析：枚举引用 + 配置占位符
            consumer.queue_name = self._resolve_value(
                result.get("queue_name"),
                result.get("queue_expression")
            )

        # 提取生产者信息
        for producer in self.producers:
            current += 1
            print(f"  [{current}/{total}] 分析生产者: {producer.class_name}")
            result = await self._llm_extract(PROMPTS["producer"], {
                "class_name": producer.class_name,
                "source_code": producer.source_code,
                "se_what": producer.se_what
            })
            producer.extracted = result
            # 统一解析：枚举引用 + 配置占位符
            producer.exchange = self._resolve_value(
                result.get("exchange"),
                result.get("exchange_expression")
            )
            producer.routing_key = self._resolve_value(
                result.get("routing_key"),
                result.get("routing_key_expression")
            )

        # 提取队列配置
        for queue in self.queues:
            current += 1
            print(f"  [{current}/{total}] 分析队列配置: {queue.method_name}")
            result = await self._llm_extract(PROMPTS["queue_config"], {
                "method_name": queue.method_name,
                "source_code": queue.source_code,
                "se_what": queue.se_what
            })
            queue.extracted = result
            # 统一解析：枚举引用 + 配置占位符
            queue.queue_name = self._resolve_value(
                result.get("queue_name"),
                result.get("queue_expression")
            )
            if result.get("dlx"):
                queue.dlx_exchange = self._resolve_value(
                    result["dlx"].get("exchange"),
                    result["dlx"].get("exchange_expression")
                )
                queue.dlx_routing_key = self._resolve_value(
                    result["dlx"].get("routing_key"),
                    result["dlx"].get("routing_key_expression")
                )
            queue.ttl_ms = result.get("ttl_ms")

        # 提取交换机配置
        for exchange in self.exchanges:
            current += 1
            print(f"  [{current}/{total}] 分析交换机配置: {exchange.method_name}")
            result = await self._llm_extract(PROMPTS["exchange_config"], {
                "method_name": exchange.method_name,
                "source_code": exchange.source_code,
                "se_what": exchange.se_what
            })
            exchange.extracted = result
            # 统一解析：枚举引用 + 配置占位符
            exchange.exchange_name = self._resolve_value(
                result.get("exchange_name"),
                result.get("exchange_expression")
            )
            exchange.exchange_type = result.get("exchange_type", "direct")

        # 提取绑定配置
        for binding in self.bindings:
            current += 1
            print(f"  [{current}/{total}] 分析绑定配置: {binding.method_name}")
            result = await self._llm_extract(PROMPTS["binding_config"], {
                "method_name": binding.method_name,
                "source_code": binding.source_code,
                "se_what": binding.se_what
            })
            binding.extracted = result
            binding.queue_name = result.get("queue_name")
            binding.queue_bean = result.get("queue_bean")
            binding.exchange_name = result.get("exchange_name")
            binding.exchange_bean = result.get("exchange_bean")
            # 统一解析路由键：枚举引用 + 配置占位符
            binding.routing_key = self._resolve_value(
                result.get("routing_key"),
                result.get("routing_key_expression")
            )

        # 解析 Bean 引用
        self._resolve_bean_references()

    async def _llm_extract(self, prompt_template: str, params: Dict) -> Dict:
        """调用 LLM 提取信息"""
        user_prompt = prompt_template.format(**params)
        system_prompt = "你是一个专业的 Java Spring AMQP 代码分析助手。请严格按照要求的 JSON 格式输出，不要包含额外的解释。"

        try:
            result = await self.llm.structured_generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema={"type": "object"}
            )
            return result if isinstance(result, dict) else {}
        except Exception as e:
            print(f"    [Warning] LLM 提取失败: {type(e).__name__}: {e}")
            return {}

    def _resolve_bean_references(self):
        """解析绑定中的 Bean 引用"""
        # 建立 Bean 名称到实际值的映射
        queue_bean_map = {q.method_name: q.queue_name for q in self.queues if q.queue_name}
        exchange_bean_map = {e.method_name: e.exchange_name for e in self.exchanges if e.exchange_name}

        for binding in self.bindings:
            # 如果队列名为空但有 Bean 引用，尝试解析
            if not binding.queue_name and binding.queue_bean:
                binding.queue_name = queue_bean_map.get(binding.queue_bean)

            # 如果交换机名为空但有 Bean 引用，尝试解析
            if not binding.exchange_name and binding.exchange_bean:
                binding.exchange_name = exchange_bean_map.get(binding.exchange_bean)

    # ========================================================================
    # Step 3: 确定性链路匹配
    # ========================================================================

    def match_flows(self) -> List[Dict]:
        """基于 RabbitMQ 概念匹配消息流转链路"""
        print("\n[Step 3] 确定性链路匹配...")

        flows = []

        for producer in self.producers:
            for consumer in self.consumers:
                flow = self._try_match_flow(producer, consumer)
                if flow:
                    flows.append(flow)

        print(f"  - 发现 {len(flows)} 条消息流转链路")
        return flows

    def _try_match_flow(self, producer: Producer, consumer: Consumer) -> Optional[Dict]:
        """尝试匹配 Producer → Consumer 的链路"""

        # 场景 1: 直接匹配 - Producer 发到的交换机绑定的队列 == Consumer 监听的队列
        direct_flow = self._try_direct_match(producer, consumer)
        if direct_flow:
            return direct_flow

        # 场景 2: TTL + 死信 - Producer → TTL Queue → DLX → Target Queue → Consumer
        dlx_flow = self._try_dlx_match(producer, consumer)
        if dlx_flow:
            return dlx_flow

        return None

    def _try_direct_match(self, producer: Producer, consumer: Consumer) -> Optional[Dict]:
        """尝试直接匹配"""
        for binding in self.bindings:
            # 检查交换机匹配
            if binding.exchange_name != producer.exchange:
                continue

            # 检查队列匹配
            if binding.queue_name != consumer.queue_name:
                continue

            # 获取交换机类型
            exchange_type = self._get_exchange_type(binding.exchange_name)

            # 检查路由键匹配
            if not self._match_routing_key(
                exchange_type,
                producer.routing_key,
                binding.routing_key
            ):
                continue

            return {
                "type": "direct",
                "producer": producer,
                "consumer": consumer,
                "exchange_type": exchange_type,
                "steps": [
                    {"name": producer.class_name, "type": "producer", "action": "发送消息"},
                    {"name": producer.exchange, "type": "exchange"},
                    {"name": consumer.queue_name, "type": "queue"},
                    {"name": f"{consumer.class_name}.{consumer.method_name}", "type": "consumer", "action": "消费消息"}
                ]
            }
        return None

    def _get_exchange_type(self, exchange_name: str) -> str:
        """获取交换机类型"""
        for e in self.exchanges:
            if e.exchange_name == exchange_name:
                return e.exchange_type or "direct"
        return "direct"

    def _match_routing_key(self, exchange_type: str, producer_key: Optional[str], binding_key: Optional[str]) -> bool:
        """根据交换机类型匹配路由键

        - fanout: 忽略路由键，总是匹配
        - direct: 精确匹配
        - topic: 支持 * 和 # 通配符
        - headers: 暂不支持，返回 True（宽松匹配）
        """
        exchange_type = (exchange_type or "direct").lower()

        # Fanout 交换机：忽略路由键
        if exchange_type == "fanout":
            return True

        # Headers 交换机：暂不支持，宽松匹配
        if exchange_type == "headers":
            return True

        # 如果任一方没有路由键，宽松匹配
        if not producer_key or not binding_key:
            return True

        # Direct 交换机：精确匹配
        if exchange_type == "direct":
            return producer_key == binding_key

        # Topic 交换机：通配符匹配
        if exchange_type == "topic":
            return self._match_topic_pattern(producer_key, binding_key)

        return producer_key == binding_key

    def _match_topic_pattern(self, routing_key: str, pattern: str) -> bool:
        """Topic 交换机的通配符匹配

        - * 匹配一个单词
        - # 匹配零个或多个单词
        """
        import re

        # 将 pattern 转换为正则表达式
        # 先转义特殊字符，再处理通配符
        regex_pattern = re.escape(pattern)
        regex_pattern = regex_pattern.replace(r'\*', r'[^.]+')  # * -> 一个单词
        regex_pattern = regex_pattern.replace(r'\#', r'.*')     # # -> 任意
        regex_pattern = f'^{regex_pattern}$'

        try:
            return bool(re.match(regex_pattern, routing_key))
        except re.error:
            return False

    def _try_dlx_match(self, producer: Producer, consumer: Consumer) -> Optional[Dict]:
        """尝试 TTL + 死信匹配"""
        # 找 Producer 发送到的交换机绑定的队列
        for ttl_binding in self.bindings:
            if ttl_binding.exchange_name != producer.exchange:
                continue

            # 找到绑定的队列
            ttl_queue = self._find_queue_by_name(ttl_binding.queue_name)
            if not ttl_queue or not ttl_queue.dlx_exchange:
                continue

            # 检查死信目标是否连接到 Consumer
            for target_binding in self.bindings:
                if target_binding.exchange_name != ttl_queue.dlx_exchange:
                    continue
                if target_binding.routing_key and ttl_queue.dlx_routing_key:
                    if target_binding.routing_key != ttl_queue.dlx_routing_key:
                        continue
                if target_binding.queue_name == consumer.queue_name:
                    return {
                        "type": "ttl_dlx",
                        "producer": producer,
                        "consumer": consumer,
                        "ttl_queue": ttl_queue,
                        "steps": [
                            {"name": producer.class_name, "type": "producer", "action": "发送延迟消息"},
                            {"name": producer.exchange, "type": "exchange"},
                            {"name": ttl_queue.queue_name, "type": "ttl_queue"},
                            {"name": ttl_queue.dlx_exchange, "type": "dlx", "action": "TTL到期转发"},
                            {"name": consumer.queue_name, "type": "queue"},
                            {"name": f"{consumer.class_name}.{consumer.method_name}", "type": "consumer", "action": "消费消息"}
                        ]
                    }
        return None

    def _find_queue_by_name(self, name: str) -> Optional[QueueConfig]:
        """根据名称查找队列配置"""
        for q in self.queues:
            if q.queue_name == name:
                return q
        return None

    # ========================================================================
    # 报告生成（JSON wiki 格式）
    # ========================================================================

    def generate_report(self, flows: List[Dict], output_path: str):
        """生成 JSON wiki 格式报告"""
        if output_path.endswith(".md"):
            output_path = output_path[:-3] + ".json"

        print(f"\n[Step 4] 生成报告: {output_path}")

        wiki_entries = []
        source_id_map = {}  # source_id -> {source_id, name, lines}
        section_num = 0

        # --- 1. 报告头部 + 概览 ---
        section_num += 1
        header_md = f"## {section_num}. RabbitMQ 消息流分析报告\n\n"
        header_md += f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        header_md += "> 分析方式: Neo4j 查询 + LLM 结构化提取 + 确定性链路匹配\n\n"
        header_md += f"### {section_num}.1 概览\n\n"
        header_md += "| 组件类型 | 数量 |\n"
        header_md += "|---------|------|\n"
        header_md += f"| 消费者 | {len(self.consumers)} |\n"
        header_md += f"| 生产者 | {len(self.producers)} |\n"
        header_md += f"| 队列 | {len(self.queues)} |\n"
        header_md += f"| 交换机 | {len(self.exchanges)} |\n"
        header_md += f"| 绑定 | {len(self.bindings)} |\n"
        wiki_entries.append({
            "markdown": header_md,
            "neo4j_id": {},
            "source_id": []
        })

        # --- 2. 每条消息流转链路 ---
        for i, flow in enumerate(flows, 1):
            section_num += 1
            producer = flow['producer']
            consumer = flow['consumer']
            flow_type = flow['type']

            # neo4j_id: dict, key=子章节号, value=nodeId 列表
            neo4j_id_dict = {}
            # source_id: 扁平的 source_id 字符串列表
            flow_source_ids = []
            sub_num = 0

            # 生产者
            sub_num += 1
            neo4j_id_dict[f"{section_num}.{sub_num}"] = producer.neo4j_ids
            self._collect_source(producer, source_id_map, flow_source_ids)

            # 消费者
            sub_num += 1
            neo4j_id_dict[f"{section_num}.{sub_num}"] = consumer.neo4j_ids
            self._collect_source(consumer, source_id_map, flow_source_ids)

            # TTL 队列（如果有）
            ttl_queue = flow.get('ttl_queue')
            if ttl_queue:
                sub_num += 1
                neo4j_id_dict[f"{section_num}.{sub_num}"] = ttl_queue.neo4j_ids
                self._collect_source(ttl_queue, source_id_map, flow_source_ids)

            # 相关交换机/队列/绑定
            for exchange in self.exchanges:
                if exchange.exchange_name == producer.exchange:
                    sub_num += 1
                    neo4j_id_dict[f"{section_num}.{sub_num}"] = exchange.neo4j_ids
                    self._collect_source(exchange, source_id_map, flow_source_ids)
            for queue in self.queues:
                if queue.queue_name == consumer.queue_name:
                    sub_num += 1
                    neo4j_id_dict[f"{section_num}.{sub_num}"] = queue.neo4j_ids
                    self._collect_source(queue, source_id_map, flow_source_ids)
            for binding in self.bindings:
                if binding.exchange_name == producer.exchange or binding.queue_name == consumer.queue_name:
                    sub_num += 1
                    neo4j_id_dict[f"{section_num}.{sub_num}"] = binding.neo4j_ids
                    self._collect_source(binding, source_id_map, flow_source_ids)

            # caller 信息
            for caller in producer.callers:
                caller_file = caller.get('caller_file_path')
                if caller_file:
                    sid = str(caller.get('caller_class_id', ''))
                    if sid:
                        self._register_source(sid, caller_file, source_id_map)
                        if sid not in flow_source_ids:
                            flow_source_ids.append(sid)

            flow_source_ids = list(dict.fromkeys(flow_source_ids))

            # 生成 markdown 内容
            md = f"## {section_num}. 链路 {i}: {producer.class_name} → {consumer.class_name}\n\n"

            md += f"### {section_num}.1 生产者(Class)\n\n"
            md += f"{producer.class_name}属于文件{PROJECT_ROOT}/{producer.source_path}\n\n"
            if producer.se_what:
                md += f"- **功能说明**: {producer.se_what}\n"
            md += f"- **目标交换机**: `{producer.exchange or 'Unknown'}`\n"
            md += f"- **路由键**: `{producer.routing_key or 'Unknown'}`\n\n"

            md += f"### {section_num}.2 消费者(Method)\n\n"
            md += f"{consumer.class_name}.{consumer.method_name}属于文件{PROJECT_ROOT}/{consumer.source_path}\n\n"
            md += f"- **监听队列**: `{consumer.queue_name or 'Unknown'}`\n"
            md += f"- **消息类型**: `{consumer.payload_type}`\n"
            if consumer.se_why:
                md += f"- **业务目的**: {consumer.se_why}\n"
            if consumer.se_how:
                md += f"- **处理逻辑**: {consumer.se_how}\n"
            md += "\n"

            if flow_type == "ttl_dlx":
                md += "**流转机制**: TTL 延迟 + 死信转发\n\n"
            else:
                md += "**流转机制**: 直接发送\n\n"

            md += "**流转路径**:\n\n"
            for j, step in enumerate(flow['steps'], 1):
                action = step.get('action', '')
                if action:
                    md += f"{j}. `{step['name']}` {action}\n"
                else:
                    md += f"{j}. `{step['name']}`\n"
            md += "\n"

            if producer.callers:
                md += "**触发入口**:\n\n"
                md += "| 调用类 | 方法 | 说明 |\n"
                md += "|-------|------|------|\n"
                for caller in producer.callers:
                    desc = caller.get('caller_desc') or '-'
                    md += f"| `{caller['caller_class']}` | `{caller['caller_method']}` | {desc} |\n"
                md += "\n"

            wiki_entries.append({
                "markdown": md,
                "neo4j_id": neo4j_id_dict,
                "source_id": flow_source_ids
            })

            # Mermaid 图
            section_num += 1
            mermaid_md, mermaid_mapping = self._build_mermaid(section_num, i, flow)
            wiki_entries.append({
                "mermaid": mermaid_md,
                "mapping": mermaid_mapping
            })

        # --- 3. 组件详情 ---
        # 消费者详情
        section_num += 1
        consumer_md = f"## {section_num}. 组件详情 - 消费者\n\n"
        consumer_neo4j_dict = {}
        consumer_source_ids = []
        for ci, c in enumerate(self.consumers, 1):
            sub_key = f"{section_num}.{ci}"
            consumer_md += f"### {sub_key} `{c.class_name}.{c.method_name}`\n\n"
            consumer_md += f"{c.class_name}.{c.method_name}属于文件{PROJECT_ROOT}/{c.source_path}\n\n"
            consumer_md += f"- **监听队列**: `{c.queue_name or 'Unknown'}`\n"
            consumer_md += f"- **消息类型**: `{c.payload_type}`\n"
            if c.se_why:
                consumer_md += f"- **业务目的**: {c.se_why}\n"
            if c.se_how:
                consumer_md += f"- **处理逻辑**: {c.se_how}\n"
            consumer_md += "\n"
            consumer_neo4j_dict[sub_key] = c.neo4j_ids
            self._collect_source(c, source_id_map, consumer_source_ids)
        wiki_entries.append({
            "markdown": consumer_md,
            "neo4j_id": consumer_neo4j_dict,
            "source_id": list(dict.fromkeys(consumer_source_ids))
        })

        # 生产者详情
        section_num += 1
        producer_md = f"## {section_num}. 组件详情 - 生产者\n\n"
        producer_neo4j_dict = {}
        producer_source_ids = []
        for pi, p in enumerate(self.producers, 1):
            sub_key = f"{section_num}.{pi}"
            producer_md += f"### {sub_key} `{p.class_name}`\n\n"
            producer_md += f"{p.class_name}属于文件{PROJECT_ROOT}/{p.source_path}\n\n"
            producer_md += f"- **目标交换机**: `{p.exchange or 'Unknown'}`\n"
            producer_md += f"- **路由键**: `{p.routing_key or 'Unknown'}`\n"
            if p.se_what:
                producer_md += f"- **功能说明**: {p.se_what}\n"
            producer_md += "\n"
            producer_neo4j_dict[sub_key] = p.neo4j_ids
            self._collect_source(p, source_id_map, producer_source_ids)
        wiki_entries.append({
            "markdown": producer_md,
            "neo4j_id": producer_neo4j_dict,
            "source_id": list(dict.fromkeys(producer_source_ids))
        })

        # 队列配置
        section_num += 1
        queue_md = f"## {section_num}. 组件详情 - 队列配置\n\n"
        queue_md += "| 队列名称 | Bean 方法 | 死信交换机 | 死信路由键 |\n"
        queue_md += "|---------|----------|-----------|------------|\n"
        queue_neo4j_dict = {}
        queue_source_ids = []
        for qi, q in enumerate(self.queues, 1):
            queue_md += (f"| `{q.queue_name or 'Unknown'}` | `{q.method_name}` | "
                         f"`{q.dlx_exchange or '-'}` | `{q.dlx_routing_key or '-'}` |\n")
            queue_neo4j_dict[f"{section_num}.{qi}"] = q.neo4j_ids
            self._collect_source(q, source_id_map, queue_source_ids)
        queue_md += "\n"
        wiki_entries.append({
            "markdown": queue_md,
            "neo4j_id": queue_neo4j_dict,
            "source_id": list(dict.fromkeys(queue_source_ids))
        })

        # 交换机配置
        section_num += 1
        exchange_md = f"## {section_num}. 组件详情 - 交换机配置\n\n"
        exchange_md += "| 交换机名称 | Bean 方法 | 类型 |\n"
        exchange_md += "|-----------|----------|------|\n"
        exchange_neo4j_dict = {}
        exchange_source_ids = []
        for ei, e in enumerate(self.exchanges, 1):
            exchange_md += f"| `{e.exchange_name or 'Unknown'}` | `{e.method_name}` | {e.exchange_type} |\n"
            exchange_neo4j_dict[f"{section_num}.{ei}"] = e.neo4j_ids
            self._collect_source(e, source_id_map, exchange_source_ids)
        exchange_md += "\n"
        wiki_entries.append({
            "markdown": exchange_md,
            "neo4j_id": exchange_neo4j_dict,
            "source_id": list(dict.fromkeys(exchange_source_ids))
        })

        # 绑定关系
        section_num += 1
        binding_md = f"## {section_num}. 组件详情 - 绑定关系\n\n"
        binding_md += "| 队列 | 交换机 | 路由键 | Bean 方法 |\n"
        binding_md += "|------|--------|--------|----------|\n"
        binding_neo4j_dict = {}
        binding_source_ids = []
        for bi, b in enumerate(self.bindings, 1):
            binding_md += (f"| `{b.queue_name or 'Unknown'}` | `{b.exchange_name or 'Unknown'}` | "
                           f"`{b.routing_key or '-'}` | `{b.method_name}` |\n")
            binding_neo4j_dict[f"{section_num}.{bi}"] = b.neo4j_ids
            self._collect_source(b, source_id_map, binding_source_ids)
        binding_md += "\n"
        wiki_entries.append({
            "markdown": binding_md,
            "neo4j_id": binding_neo4j_dict,
            "source_id": list(dict.fromkeys(binding_source_ids))
        })

        # --- 组装最终 JSON ---
        result = {
            "wiki": wiki_entries,
            "source_id_list": list(source_id_map.values())
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"  报告已保存: {output_path}")

    def _collect_source(self, component: Component, source_id_map: Dict, source_id_list: List[str]):
        """收集组件的 source_id 到全局 map 和当前条目的 source_id 列表"""
        if not component.source_path or not component.neo4j_ids:
            return
        sid = str(component.neo4j_ids[0])
        self._register_source(sid, component.source_path, source_id_map)
        if sid not in source_id_list:
            source_id_list.append(sid)

    def _register_source(self, source_id: str, file_path: str, source_id_map: Dict):
        """注册一个 source_id 到全局 map
        file_path 来自 File 节点的 name 字段，需拼接 PROJECT_ROOT 作为根目录
        """
        if source_id not in source_id_map:
            source_id_map[source_id] = {
                "source_id": source_id,
                "name": f"{PROJECT_ROOT}/{file_path}",
                "lines": []
            }

    def _build_mermaid(self, section_num: int, flow_index: int, flow: Dict) -> tuple:
        """生成 Mermaid 流程图 markdown 和 mapping

        Returns:
            (mermaid_markdown, mapping_dict)
        """
        producer = flow['producer']
        consumer = flow['consumer']
        md = f"### {section_num}. 链路 {flow_index} 流程图: {producer.class_name} → {consumer.class_name}\n"
        md += "```mermaid\ngraph LR\n"

        mapping = {}
        steps = flow['steps']

        for i, step in enumerate(steps):
            name = step['name']
            stype = step['type']
            node_label = f"N{i}"

            # 将 mermaid 节点标签映射到 source_id（nodeId 字符串）
            if stype == 'producer' and producer.neo4j_ids:
                mapping[node_label] = str(producer.neo4j_ids[0])
            elif stype == 'consumer' and consumer.neo4j_ids:
                mapping[node_label] = str(consumer.neo4j_ids[0])
            else:
                matched_id = self._find_component_id(name, stype)
                if matched_id:
                    mapping[node_label] = matched_id

            if stype in ('exchange', 'dlx'):
                node = f"N{i}{{{{{name}}}}}"
            elif stype in ('queue', 'ttl_queue'):
                node = f"N{i}[({name})]"
            else:
                node = f"N{i}([{name}])"

            if i == 0:
                md += f"    {node}\n"

            if i < len(steps) - 1:
                next_step = steps[i + 1]
                next_name = next_step['name']
                next_type = next_step['type']

                if next_type in ('exchange', 'dlx'):
                    next_node = f"N{i+1}{{{{{next_name}}}}}"
                elif next_type in ('queue', 'ttl_queue'):
                    next_node = f"N{i+1}[({next_name})]"
                else:
                    next_node = f"N{i+1}([{next_name}])"

                action = next_step.get('action', '')
                if action:
                    md += f"    N{i} -->|{action}| {next_node}\n"
                else:
                    md += f"    N{i} --> {next_node}\n"

        md += "```\n"
        return md, mapping

    def _find_component_id(self, name: str, stype: str) -> Optional[str]:
        """根据名称和类型查找对应组件的 nodeId"""
        if stype in ('exchange', 'dlx'):
            for e in self.exchanges:
                if e.exchange_name == name and e.neo4j_ids:
                    return str(e.neo4j_ids[0])
        elif stype in ('queue', 'ttl_queue'):
            for q in self.queues:
                if q.queue_name == name and q.neo4j_ids:
                    return str(q.neo4j_ids[0])
        return None

    # ========================================================================
    # 主流程
    # ========================================================================

    async def run(self, output_path: str = "rabbitmq_flow_report_v3.json"):
        """执行完整分析流程"""
        print("=" * 60)
        print("RabbitMQ Flow Analyzer v3")
        print("=" * 60)

        try:
            # Step 1: 确定性查询
            self.query_components()

            if not self.consumers and not self.producers:
                print("\n[Warning] 未发现 RabbitMQ 组件!")
                return

            # Step 2: LLM 提取
            await self.extract_with_llm()

            # Step 3: 确定性匹配
            flows = self.match_flows()

            # Step 4: 生成报告
            self.generate_report(flows, output_path)

            print("\n" + "=" * 60)
            print("分析完成!")
            print("=" * 60)

        finally:
            self.close()


# ============================================================================
# 入口
# ============================================================================

async def main():
    analyzer = RabbitMQAnalyzer()
    await analyzer.run(output_path="rabbitmq_flow_report_v3.json")


if __name__ == "__main__":
    asyncio.run(main())
