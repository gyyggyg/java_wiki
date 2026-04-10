"""
RabbitMQ Flow Analyzer v2 - 基于图谱语义的消息链路分析工具

设计思路：
1. 查全量组件：通过 Neo4j 查询所有 Consumer/Producer/Config/Enum
2. 复用语义：直接使用图谱中已有的 SE_What/SE_Why/SE_How 属性
3. 确定性解析：用正则解析枚举值和配置，不依赖 LLM
4. LLM 只做组装：综合所有信息，构建消息流转链路描述

与 v1 的区别：
- 不再对每个组件调用 LLM 分析
- 充分利用图谱已有的语义信息
- 报告格式更清晰，无内部产物（置信度等）
"""

import os
import re
import json
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from neo4j import GraphDatabase


# ============================================================================
# 配置
# ============================================================================

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7689")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "c8a3974ba62qcc2")

# LLM 配置（仅用于链路组装）
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4.1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class Consumer:
    """消息消费者"""
    class_name: str
    method_name: str
    queue_name: str  # 解析后的实际队列名
    payload_type: str
    se_what: str
    se_why: str
    se_how: str


@dataclass
class Producer:
    """消息生产者"""
    class_name: str
    exchange: str  # 解析后的实际交换机名
    routing_key: str  # 解析后的实际路由键
    se_what: str
    callers: List[Dict] = field(default_factory=list)  # 调用方信息


@dataclass
class QueueConfig:
    """队列配置"""
    bean_name: str
    queue_name: str  # 解析后的实际队列名
    dlx_exchange: Optional[str] = None  # 死信交换机
    dlx_routing_key: Optional[str] = None  # 死信路由键
    se_what: str = ""


@dataclass
class ExchangeConfig:
    """交换机配置"""
    bean_name: str
    exchange_name: str  # 解析后的实际交换机名
    exchange_type: str = "direct"
    se_what: str = ""


@dataclass
class BindingConfig:
    """绑定配置"""
    bean_name: str
    queue_name: str
    exchange_name: str
    routing_key: str
    se_what: str = ""


@dataclass
class EnumConstant:
    """枚举常量"""
    enum_class: str
    constant_name: str
    exchange: str
    queue: str
    routing_key: str
    se_what: str = ""


# ============================================================================
# 核心分析器
# ============================================================================

class RabbitMQAnalyzer:
    """RabbitMQ 消息流分析器 v2"""

    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        # 存储组件
        self.consumers: List[Consumer] = []
        self.producers: List[Producer] = []
        self.queues: List[QueueConfig] = []
        self.exchanges: List[ExchangeConfig] = []
        self.bindings: List[BindingConfig] = []
        self.enums: Dict[str, EnumConstant] = {}  # key: "EnumClass.CONSTANT"

    def close(self):
        self.driver.close()

    def run_query(self, query: str, params: Dict = None) -> List[Dict]:
        """执行 Cypher 查询"""
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

    # ========================================================================
    # Step 1: 查询所有组件
    # ========================================================================

    def query_all_components(self):
        """查询所有 RabbitMQ 相关组件"""
        print("\n[Step 1] 查询所有组件...")

        self._query_enum_constants()
        self._query_consumers()
        self._query_producers()
        self._query_configs()

        print(f"  - 枚举常量: {len(self.enums)}")
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
               ec.source_code as source_code,
               ec.SE_What as se_what
        """
        results = self.run_query(query)

        for r in results:
            # 用正则解析枚举构造函数参数
            values = self._parse_enum_constructor(r['source_code'])
            if len(values) >= 3:
                key = f"{r['enum_class']}.{r['constant_name']}"
                self.enums[key] = EnumConstant(
                    enum_class=r['enum_class'],
                    constant_name=r['constant_name'],
                    exchange=values[0],
                    queue=values[1],
                    routing_key=values[2],
                    se_what=r.get('se_what') or ''
                )

    def _parse_enum_constructor(self, source_code: str) -> List[str]:
        """解析枚举构造函数参数，提取字符串值"""
        if not source_code:
            return []
        # 匹配: CONSTANT_NAME("value1", "value2", "value3")
        match = re.search(r'\w+\s*\(\s*(.+)\s*\)', source_code)
        if match:
            args_str = match.group(1)
            return re.findall(r'"([^"]*)"', args_str)
        return []

    def _query_consumers(self):
        """查询消息消费者"""
        query = """
        MATCH (c:Class)-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS '@RabbitHandler'
           OR c.modifiers CONTAINS '@RabbitListener'
        RETURN c.name as class_name,
               c.modifiers as class_modifiers,
               m.name as method_name,
               m.parameters as parameters,
               m.SE_What as se_what,
               m.SE_Why as se_why,
               m.SE_How as se_how
        """
        results = self.run_query(query)

        for r in results:
            # 提取队列名
            queue_name = self._extract_queue_from_listener(r.get('class_modifiers', ''))

            # 提取消息载体类型
            payload_type = self._extract_payload_type(r.get('parameters', ''))

            self.consumers.append(Consumer(
                class_name=r['class_name'],
                method_name=r['method_name'],
                queue_name=queue_name,
                payload_type=payload_type,
                se_what=r.get('se_what') or '',
                se_why=r.get('se_why') or '',
                se_how=r.get('se_how') or ''
            ))

    def _extract_queue_from_listener(self, modifiers: str) -> str:
        """从 @RabbitListener 注解提取队列名"""
        match = re.search(r'queues\s*=\s*"([^"]+)"', modifiers)
        return match.group(1) if match else "Unknown"

    def _extract_payload_type(self, parameters: str) -> str:
        """从方法参数提取消息载体类型"""
        if not parameters:
            return "Unknown"
        params = parameters.strip("()")
        if not params:
            return "Unknown"
        first_param = params.split(",")[0].strip()
        parts = first_param.split()
        return parts[0] if parts else "Unknown"

    def _query_producers(self):
        """查询消息生产者"""
        query = """
        MATCH (c:Class)-[:DECLARES]->(f:Field)
        WHERE f.type CONTAINS 'AmqpTemplate' OR f.type CONTAINS 'RabbitTemplate'
        MATCH (c)-[:DECLARES]->(m:Method)
        WHERE m.source_code CONTAINS 'convertAndSend'
        RETURN DISTINCT c.name as class_name,
               c.SE_What as se_what,
               m.source_code as source_code
        """
        results = self.run_query(query)

        for r in results:
            # 提取发送目标
            exchange, routing_key = self._extract_send_target(r.get('source_code', ''))

            # 解析枚举引用
            exchange = self._resolve_enum_ref(exchange, 'exchange')
            routing_key = self._resolve_enum_ref(routing_key, 'routing_key')

            self.producers.append(Producer(
                class_name=r['class_name'],
                exchange=exchange,
                routing_key=routing_key,
                se_what=r.get('se_what') or ''
            ))

        # 查询调用方
        self._query_producer_callers()

    def _extract_send_target(self, source_code: str) -> tuple:
        """从 convertAndSend 调用提取交换机和路由键"""
        match = re.search(r'convertAndSend\s*\(\s*([^,]+),\s*([^,]+)', source_code)
        if match:
            exchange = match.group(1).strip()
            routing_key = match.group(2).strip()
            return exchange, routing_key
        return "Unknown", "Unknown"

    def _resolve_enum_ref(self, ref: str, field: str) -> str:
        """解析枚举引用，返回实际值"""
        if not ref or ref == "Unknown":
            return ref

        # 匹配: QueueEnum.QUEUE_ORDER_CANCEL.getExchange()
        match = re.search(r'(\w+)\.(\w+)\.get\w+\(\)', ref)
        if match:
            enum_class = match.group(1)
            constant_name = match.group(2)
            key = f"{enum_class}.{constant_name}"

            if key in self.enums:
                enum = self.enums[key]
                if field == 'exchange':
                    return enum.exchange
                elif field == 'routing_key':
                    return enum.routing_key
                elif field == 'queue':
                    return enum.queue

        return ref

    def _query_producer_callers(self):
        """查询生产者的调用方"""
        for producer in self.producers:
            query = """
            MATCH (c:Class {name: $class_name})-[:DECLARES]->(m:Method)
            WHERE m.source_code CONTAINS 'convertAndSend'
            MATCH (caller:Method)-[:CALLS]->(m)
            MATCH (callerClass)-[:DECLARES]->(caller)
            RETURN callerClass.name as caller_class,
                   caller.name as caller_method,
                   caller.SE_What as caller_desc
            LIMIT 10
            """
            results = self.run_query(query, {"class_name": producer.class_name})
            producer.callers = results

    def _query_configs(self):
        """查询队列/交换机/绑定配置"""
        query = """
        MATCH (c:Class)-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS '@Bean'
          AND (m.return_type CONTAINS 'Queue'
               OR m.return_type CONTAINS 'Exchange'
               OR m.return_type CONTAINS 'Binding')
        RETURN m.name as bean_name,
               m.return_type as return_type,
               m.source_code as source_code,
               m.SE_What as se_what
        """
        results = self.run_query(query)

        for r in results:
            return_type = r.get('return_type', '')
            source_code = r.get('source_code', '')
            bean_name = r['bean_name']
            se_what = r.get('se_what') or ''

            if 'Queue' in return_type and 'Binding' not in return_type:
                self._parse_queue_config(bean_name, source_code, se_what)
            elif 'Exchange' in return_type:
                self._parse_exchange_config(bean_name, source_code, se_what)
            elif 'Binding' in return_type:
                self._parse_binding_config(bean_name, source_code, se_what)

    def _parse_queue_config(self, bean_name: str, source_code: str, se_what: str):
        """解析队列配置"""
        # 提取队列名
        queue_name = self._extract_name_from_source(source_code)
        queue_name = self._resolve_enum_ref(queue_name, 'queue')

        # 提取死信配置
        dlx_exchange = None
        dlx_routing_key = None

        # 匹配: "x-dead-letter-exchange", QueueEnum.XXX.getExchange()
        dlx_match = re.search(r'x-dead-letter-exchange"[,\s]*(\w+\.\w+\.get\w+\(\))', source_code)
        if dlx_match:
            dlx_exchange = self._resolve_enum_ref(dlx_match.group(1).strip(), 'exchange')

        # 匹配: "x-dead-letter-routing-key", QueueEnum.XXX.getRouteKey()
        dlk_match = re.search(r'x-dead-letter-routing-key"[,\s]*(\w+\.\w+\.get\w+\(\))', source_code)
        if dlk_match:
            dlx_routing_key = self._resolve_enum_ref(dlk_match.group(1).strip(), 'routing_key')

        self.queues.append(QueueConfig(
            bean_name=bean_name,
            queue_name=queue_name,
            dlx_exchange=dlx_exchange,
            dlx_routing_key=dlx_routing_key,
            se_what=se_what
        ))

    def _parse_exchange_config(self, bean_name: str, source_code: str, se_what: str):
        """解析交换机配置"""
        exchange_name = self._extract_name_from_source(source_code)
        exchange_name = self._resolve_enum_ref(exchange_name, 'exchange')

        exchange_type = "direct"
        if "Topic" in source_code:
            exchange_type = "topic"
        elif "Fanout" in source_code:
            exchange_type = "fanout"
        elif "Headers" in source_code:
            exchange_type = "headers"

        self.exchanges.append(ExchangeConfig(
            bean_name=bean_name,
            exchange_name=exchange_name,
            exchange_type=exchange_type,
            se_what=se_what
        ))

    def _parse_binding_config(self, bean_name: str, source_code: str, se_what: str):
        """解析绑定配置"""
        # 提取路由键: .with(QueueEnum.XXX.getRouteKey())
        routing_key = "Unknown"
        rk_match = re.search(r'\.with\s*\(\s*(\w+\.\w+\.get\w+\(\))\s*\)', source_code)
        if rk_match:
            routing_key = self._resolve_enum_ref(rk_match.group(1).strip(), 'routing_key')

        # 从方法参数名推断队列和交换机
        # 通常 Binding 方法会注入 Queue 和 Exchange 参数
        queue_name = "Unknown"
        exchange_name = "Unknown"

        # 匹配方法参数中的 Queue 和 Exchange
        # 例如: Binding orderBinding(DirectExchange orderDirect, Queue orderQueue)
        queue_param_match = re.search(r'Queue\s+(\w+)', source_code)
        exchange_param_match = re.search(r'(?:Direct)?Exchange\s+(\w+)', source_code)

        if queue_param_match:
            queue_bean = queue_param_match.group(1)
            queue_name = self._find_queue_by_bean(queue_bean)

        if exchange_param_match:
            exchange_bean = exchange_param_match.group(1)
            exchange_name = self._find_exchange_by_bean(exchange_bean)

        self.bindings.append(BindingConfig(
            bean_name=bean_name,
            queue_name=queue_name,
            exchange_name=exchange_name,
            routing_key=routing_key,
            se_what=se_what
        ))

    def _extract_name_from_source(self, source_code: str) -> str:
        """从源码提取名称（枚举引用或字符串）"""
        # 匹配枚举引用: QueueEnum.QUEUE_ORDER_CANCEL.getName()
        match = re.search(r'(\w+\.\w+\.get\w+\(\))', source_code)
        if match:
            return match.group(1)

        # 匹配字符串字面量
        match = re.search(r'"([^"]+)"', source_code)
        if match:
            return match.group(1)

        return "Unknown"

    def _find_queue_by_bean(self, bean_name: str) -> str:
        """根据 Bean 名称查找队列名"""
        for q in self.queues:
            if q.bean_name == bean_name:
                return q.queue_name
        return "Unknown"

    def _find_exchange_by_bean(self, bean_name: str) -> str:
        """根据 Bean 名称查找交换机名"""
        for e in self.exchanges:
            if e.bean_name == bean_name:
                return e.exchange_name
        return "Unknown"

    # ========================================================================
    # Step 2: 构建消息流转链路
    # ========================================================================

    def build_message_flows(self) -> List[Dict]:
        """构建消息流转链路"""
        print("\n[Step 2] 构建消息流转链路...")

        flows = []

        for producer in self.producers:
            for consumer in self.consumers:
                flow = self._try_build_flow(producer, consumer)
                if flow:
                    flows.append(flow)

        print(f"  - 发现 {len(flows)} 条消息流转链路")
        return flows

    def _try_build_flow(self, producer: Producer, consumer: Consumer) -> Optional[Dict]:
        """尝试构建从 Producer 到 Consumer 的流转链路"""

        # 直接匹配：Producer 的交换机绑定的队列 == Consumer 监听的队列
        for binding in self.bindings:
            if binding.exchange_name == producer.exchange and binding.queue_name == consumer.queue_name:
                return {
                    "type": "direct",
                    "producer": producer,
                    "consumer": consumer,
                    "path": [
                        {"component": producer.class_name, "action": "发送消息"},
                        {"component": producer.exchange, "type": "exchange"},
                        {"component": consumer.queue_name, "type": "queue"},
                        {"component": f"{consumer.class_name}.{consumer.method_name}", "action": "消费消息"}
                    ]
                }

        # TTL + 死信匹配：Producer → TTL Queue → DLX → Target Queue → Consumer
        for ttl_queue in self.queues:
            if ttl_queue.dlx_exchange:
                # 找到 Producer 发送到的 TTL 队列
                ttl_binding = self._find_binding_by_queue(ttl_queue.queue_name)
                if ttl_binding and ttl_binding.exchange_name == producer.exchange:
                    # 找到死信目标队列
                    target_binding = self._find_binding_by_exchange_and_key(
                        ttl_queue.dlx_exchange, ttl_queue.dlx_routing_key
                    )
                    if target_binding and target_binding.queue_name == consumer.queue_name:
                        return {
                            "type": "ttl_dlx",
                            "producer": producer,
                            "consumer": consumer,
                            "ttl_queue": ttl_queue,
                            "path": [
                                {"component": producer.class_name, "action": "发送延迟消息"},
                                {"component": producer.exchange, "type": "exchange"},
                                {"component": ttl_queue.queue_name, "type": "ttl_queue"},
                                {"component": ttl_queue.dlx_exchange, "type": "dlx", "action": "TTL到期转发"},
                                {"component": consumer.queue_name, "type": "queue"},
                                {"component": f"{consumer.class_name}.{consumer.method_name}", "action": "消费消息"}
                            ]
                        }

        return None

    def _find_binding_by_queue(self, queue_name: str) -> Optional[BindingConfig]:
        """根据队列名查找绑定配置"""
        for binding in self.bindings:
            if binding.queue_name == queue_name:
                return binding
        return None

    def _find_binding_by_exchange_and_key(self, exchange: str, routing_key: str) -> Optional[BindingConfig]:
        """根据交换机和路由键查找绑定配置"""
        for binding in self.bindings:
            if binding.exchange_name == exchange and binding.routing_key == routing_key:
                return binding
        return None

    # ========================================================================
    # Step 3: 生成报告
    # ========================================================================

    def generate_report(self, flows: List[Dict], output_path: str):
        """生成 Markdown 报告"""
        print(f"\n[Step 3] 生成报告: {output_path}")

        with open(output_path, "w", encoding="utf-8") as f:
            self._write_header(f)
            self._write_overview(f)
            self._write_flows(f, flows)
            self._write_components(f)
            self._write_enum_reference(f)

        print(f"  报告已保存: {output_path}")

    def _write_header(self, f):
        """写入报告头部"""
        f.write("# RabbitMQ 消息流分析报告\n\n")
        f.write("> 基于 Neo4j 代码图谱自动生成\n\n")

    def _write_overview(self, f):
        """写入概览"""
        f.write("## 概览\n\n")
        f.write(f"| 组件类型 | 数量 |\n")
        f.write(f"|---------|------|\n")
        f.write(f"| 消费者 | {len(self.consumers)} |\n")
        f.write(f"| 生产者 | {len(self.producers)} |\n")
        f.write(f"| 队列 | {len(self.queues)} |\n")
        f.write(f"| 交换机 | {len(self.exchanges)} |\n")
        f.write(f"| 绑定 | {len(self.bindings)} |\n\n")

    def _write_flows(self, f, flows: List[Dict]):
        """写入消息流转链路"""
        if not flows:
            f.write("## 消息流转链路\n\n*未发现完整的消息流转链路*\n\n")
            return

        f.write("## 消息流转链路\n\n")

        for i, flow in enumerate(flows, 1):
            producer = flow['producer']
            consumer = flow['consumer']
            flow_type = flow['type']

            f.write(f"### 链路 {i}: {producer.class_name} → {consumer.class_name}\n\n")

            # 业务描述
            if producer.se_what:
                f.write(f"**业务场景**: {producer.se_what}\n\n")

            # 流转路径描述
            if flow_type == "ttl_dlx":
                ttl_queue = flow['ttl_queue']
                f.write("**流转机制**: TTL 延迟 + 死信转发\n\n")
                f.write("**详细路径**:\n")
                f.write(f"1. `{producer.class_name}` 发送消息到交换机 `{producer.exchange}`\n")
                f.write(f"2. 消息路由到 TTL 队列 `{ttl_queue.queue_name}`\n")
                f.write(f"3. 消息过期后，通过死信机制转发到交换机 `{ttl_queue.dlx_exchange}`\n")
                f.write(f"4. 消息路由到目标队列 `{consumer.queue_name}`\n")
                f.write(f"5. `{consumer.class_name}.{consumer.method_name}` 消费消息\n\n")
            else:
                f.write("**流转机制**: 直接发送\n\n")
                f.write("**详细路径**:\n")
                f.write(f"1. `{producer.class_name}` 发送消息到交换机 `{producer.exchange}`\n")
                f.write(f"2. 消息路由到队列 `{consumer.queue_name}`\n")
                f.write(f"3. `{consumer.class_name}.{consumer.method_name}` 消费消息\n\n")

            # Mermaid 流程图
            self._write_flow_diagram(f, flow)

            # 触发入口
            if producer.callers:
                f.write("**触发入口**:\n\n")
                f.write("| 调用类 | 方法 | 说明 |\n")
                f.write("|-------|------|------|\n")
                for caller in producer.callers:
                    desc = caller.get('caller_desc', '-') or '-'
                    f.write(f"| `{caller['caller_class']}` | `{caller['caller_method']}` | {desc[:50]} |\n")
                f.write("\n")

            f.write("---\n\n")

    def _write_flow_diagram(self, f, flow: Dict):
        """写入 Mermaid 流程图"""
        f.write("```mermaid\n")
        f.write("graph LR\n")

        path = flow['path']
        for i, step in enumerate(path):
            component = step['component']
            comp_type = step.get('type', '')

            # 根据类型选择节点形状
            if comp_type == 'exchange' or comp_type == 'dlx':
                node = f"N{i}{{{{{component}}}}}"
            elif comp_type == 'queue' or comp_type == 'ttl_queue':
                node = f"N{i}[({component})]"
            else:
                node = f"N{i}([{component}])"

            if i == 0:
                f.write(f"    {node}\n")

            if i < len(path) - 1:
                next_step = path[i + 1]
                next_comp = next_step['component']
                next_type = next_step.get('type', '')

                if next_type == 'exchange' or next_type == 'dlx':
                    next_node = f"N{i+1}{{{{{next_comp}}}}}"
                elif next_type == 'queue' or next_type == 'ttl_queue':
                    next_node = f"N{i+1}[({next_comp})]"
                else:
                    next_node = f"N{i+1}([{next_comp}])"

                # 边标签（简短）
                action = next_step.get('action', '')
                if action:
                    f.write(f"    N{i} -->|{action}| {next_node}\n")
                else:
                    f.write(f"    N{i} --> {next_node}\n")

        f.write("```\n\n")

    def _write_components(self, f):
        """写入组件详情"""
        f.write("## 组件详情\n\n")

        # 消费者
        f.write("### 消费者\n\n")
        for consumer in self.consumers:
            f.write(f"#### `{consumer.class_name}.{consumer.method_name}`\n\n")
            f.write(f"- **监听队列**: `{consumer.queue_name}`\n")
            f.write(f"- **消息类型**: `{consumer.payload_type}`\n")
            if consumer.se_why:
                f.write(f"- **业务目的**: {consumer.se_why}\n")
            if consumer.se_how:
                f.write(f"- **处理逻辑**: {consumer.se_how[:200]}{'...' if len(consumer.se_how) > 200 else ''}\n")
            f.write("\n")

        # 生产者
        f.write("### 生产者\n\n")
        for producer in self.producers:
            f.write(f"#### `{producer.class_name}`\n\n")
            f.write(f"- **目标交换机**: `{producer.exchange}`\n")
            f.write(f"- **路由键**: `{producer.routing_key}`\n")
            if producer.se_what:
                f.write(f"- **功能说明**: {producer.se_what}\n")
            f.write("\n")

        # 队列配置
        f.write("### 队列配置\n\n")
        f.write("| 队列名称 | Bean 方法 | 死信交换机 | 死信路由键 | 说明 |\n")
        f.write("|---------|----------|-----------|-----------|------|\n")
        for q in self.queues:
            dlx = q.dlx_exchange or "-"
            dlk = q.dlx_routing_key or "-"
            desc = q.se_what[:30] + "..." if len(q.se_what) > 30 else q.se_what
            f.write(f"| `{q.queue_name}` | `{q.bean_name}` | `{dlx}` | `{dlk}` | {desc} |\n")
        f.write("\n")

        # 交换机配置
        f.write("### 交换机配置\n\n")
        f.write("| 交换机名称 | Bean 方法 | 类型 | 说明 |\n")
        f.write("|-----------|----------|------|------|\n")
        for e in self.exchanges:
            desc = e.se_what[:30] + "..." if len(e.se_what) > 30 else e.se_what
            f.write(f"| `{e.exchange_name}` | `{e.bean_name}` | {e.exchange_type} | {desc} |\n")
        f.write("\n")

        # 绑定配置
        f.write("### 绑定关系\n\n")
        f.write("| 队列 | 交换机 | 路由键 | Bean 方法 |\n")
        f.write("|------|--------|--------|----------|\n")
        for b in self.bindings:
            f.write(f"| `{b.queue_name}` | `{b.exchange_name}` | `{b.routing_key}` | `{b.bean_name}` |\n")
        f.write("\n")

    def _write_enum_reference(self, f):
        """写入枚举常量参考"""
        if not self.enums:
            return

        f.write("## 枚举常量参考\n\n")
        f.write("| 枚举常量 | 交换机 | 队列 | 路由键 |\n")
        f.write("|---------|--------|------|--------|\n")
        for key, enum in self.enums.items():
            f.write(f"| `{key}` | `{enum.exchange}` | `{enum.queue}` | `{enum.routing_key}` |\n")
        f.write("\n")

    # ========================================================================
    # 主流程
    # ========================================================================

    def run(self, output_path: str = "rabbitmq_flow_report_v2.md"):
        """执行分析"""
        print("=" * 60)
        print("RabbitMQ Flow Analyzer v2")
        print("=" * 60)

        try:
            # Step 1: 查询所有组件
            self.query_all_components()

            # Step 2: 构建消息流转链路
            flows = self.build_message_flows()

            # Step 3: 生成报告
            self.generate_report(flows, output_path)

            print("\n" + "=" * 60)
            print("分析完成!")
            print("=" * 60)

        finally:
            self.close()


# ============================================================================
# 入口
# ============================================================================

def main():
    analyzer = RabbitMQAnalyzer()
    analyzer.run(output_path="rabbitmq_flow_report_v2.md")


if __name__ == "__main__":
    main()
