import os
import re
from neo4j import GraphDatabase
from ruamel.yaml import YAML
from pathlib import Path

# Configuration
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7689")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "c8a3974ba62qcc2")

class ConfigParser:
    def __init__(self, root_dir="."):
        self.root_dir = Path(root_dir)
        self.config = {}
        self.yaml = YAML()
        self.profile_override = (
            os.environ.get("CONFIG_PROFILE")
            or os.environ.get("SPRING_PROFILES_ACTIVE")
        )
        self._load_configs()

    def _load_yaml_file(self, yaml_file):
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = self.yaml.load(f)
                if data:
                    self._flatten_and_merge(data)
                    return data
        except Exception as e:
            print(f"Failed to parse {yaml_file}: {e}")
        return None

    def _load_configs(self):
        print("Loading configuration files...")
        base_files = list(self.root_dir.rglob("application.yml"))

        for yaml_file in base_files:
            if "target" in str(yaml_file):
                continue
            data = self._load_yaml_file(yaml_file)

            profile = self.profile_override
            if not profile and isinstance(data, dict):
                profile = (
                    data.get("spring", {})
                        .get("profiles", {})
                        .get("active")
                )

            if profile:
                profile_file = yaml_file.with_name(f"application-{profile}.yml")
                if profile_file.exists():
                    self._load_yaml_file(profile_file)
            else:
                dev_file = yaml_file.with_name("application-dev.yml")
                if dev_file.exists():
                    self._load_yaml_file(dev_file)
                
    def _flatten_and_merge(self, data, prefix=""):
        if isinstance(data, dict):
            for k, v in data.items():
                new_key = f"{prefix}.{k}" if prefix else k
                self._flatten_and_merge(v, new_key)
        else:
            self.config[prefix] = str(data)

    def get(self, key, default=None):
        if not key: return default
        # Handle "${key}" format
        clean_key = key.strip("${}")
        return self.config.get(clean_key, default if default is not None else key)

class BackendInterfaceGenerator:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.config = ConfigParser()
        self.enum_constants = {}  # 缓存枚举常量值
        self._load_enum_constants()

    def _load_enum_constants(self):
        """加载所有枚举常量值，解析构造函数参数"""
        print("Loading enum constants from Neo4j...")
        
        # 查询所有枚举常量
        query = """
        MATCH (e:Enum)-[:DECLARES]->(ec:EnumConstant)
        RETURN e.name as enum_name, ec.name as constant_name, ec.source_code as source_code
        """
        
        with self.driver.session() as session:
            results = [record.data() for record in session.run(query)]
        
        for r in results:
            enum_name = r['enum_name']
            constant_name = r['constant_name']
            source_code = r['source_code'] or ""
            
            if enum_name not in self.enum_constants:
                self.enum_constants[enum_name] = {}
            
            # 解析枚举常量的构造函数参数
            # 例如: QUEUE_ORDER_CANCEL("mall.order.direct", "mall.order.cancel", "mall.order.cancel")
            match = re.search(rf'{constant_name}\s*\(\s*(.+)\s*\)', source_code)
            if match:
                args_str = match.group(1)
                # 提取所有字符串参数
                args = re.findall(r'"([^"]*)"', args_str)
                self.enum_constants[enum_name][constant_name] = args
            else:
                self.enum_constants[enum_name][constant_name] = []
        
        print(f"   Loaded {len(self.enum_constants)} enums with {sum(len(v) for v in self.enum_constants.values())} constants")

    def _resolve_enum_value(self, code_expression, field_index=0):
        """解析枚举方法调用，返回实际值
        例如: QueueEnum.QUEUE_ORDER_CANCEL.getExchange() -> "mall.order.direct"
        """
        # 匹配: EnumName.CONSTANT_NAME.getXxx() 或 EnumName.CONSTANT_NAME.getXxx()
        match = re.search(r'(\w+)\.(\w+)\.(get\w+)\(\)', code_expression)
        if match:
            enum_name = match.group(1)
            constant_name = match.group(2)
            getter = match.group(3).lower()
            
            if enum_name in self.enum_constants and constant_name in self.enum_constants[enum_name]:
                values = self.enum_constants[enum_name][constant_name]
                # QueueEnum 特殊处理: exchange(0), name(1), routeKey(2)
                if enum_name == 'QueueEnum':
                    if 'exchange' in getter and len(values) > 0:
                        return values[0]
                    elif 'name' in getter and len(values) > 1:
                        return values[1]
                    elif 'routekey' in getter and len(values) > 2:
                        return values[2]
                # 默认返回第一个值
                if values:
                    return values[field_index]
        
        return code_expression  # 无法解析时返回原表达式

    def close(self):
        self.driver.close()

    def generate_report(self, output_file="backend_interfaces.md"):
        print(" Starting Backend Interface Documentation Generation...")
        
        sections = []
        
        # 1. Overview & Architecture
        print(" Generating Overview...")
        sections.append(self._generate_overview())
        
        # 2. RabbitMQ
        print(" Scanning RabbitMQ...")
        sections.append(self._scan_rabbitmq())
        
        # 3. Scheduled Tasks
        print(" Scanning Scheduled Tasks...")
        sections.append(self._scan_scheduled())
        
        # 4. Data Storage (ES & Mongo)
        print(" Scanning Data Storage (ES/Mongo)...")
        sections.append(self._scan_data_storage())
        
        # 5. Redis
        print(" Scanning Redis...")
        sections.append(self._scan_redis())
        
        # 6. Object Storage
        print(" Scanning Object Storage...")
        sections.append(self._scan_object_storage())

        from datetime import datetime
        final_content = "\n\n".join(sections).replace("{{GEN_TIME}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f" Report generated: {output_file}")

    def _clean_se(self, text, parse_json=True):
        """Clean Semantic Explanation text, optionally parsing JSON to Markdown list"""
        if not text or text == 'None':
            return "暂无描述"
        text = text.strip()
        # 尝试解析 JSON 格式的 SE_When 字段
        if parse_json and text.startswith('{') and text.endswith('}'):
            try:
                import json
                data = json.loads(text)
                if 'summary' in data:
                    lines = [data['summary']]
                    if 'examples' in data and isinstance(data['examples'], list):
                        for ex in data['examples']:
                            name = ex.get('name', '')
                            etype = ex.get('type', '')
                            desc = ex.get('description', '')
                            lines.append(f"  - `{name}` ({etype}): {desc}")
                    return "\n".join(lines)
            except:
                pass
        return text.replace("\n", " ")

    def _has_annotation(self, text, annotations):
        if not text:
            return False
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue
            for ann in annotations:
                if re.match(rf"@{ann}\b", stripped):
                    return True
        return False

    def _is_spring_bean(self, class_modifiers, class_source):
        annotations = ["Component", "Service", "Configuration", "Controller", "RestController", "Repository"]
        if class_modifiers and any(f"@{ann}" in class_modifiers for ann in annotations):
            return True
        return self._has_annotation(class_source or "", annotations)

    def _generate_overview(self):
        """Generate Overview Section with Metadata and Mermaid Diagram"""
        from datetime import datetime
        gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""# 后端系统接口清单

> **生成时间**: {gen_time}
> **脚本版本**: v2.1.0 (Enhanced)
> **数据源**: Neo4j Code Graph

## 1. 概览
本文档由脚本自动生成，基于 Neo4j 代码图谱深度分析。涵盖消息队列、定时任务、数据存储、缓存及对象存储等后端集成接口。

```mermaid
graph LR
    App[后端应用]
    
    subgraph 消息中间件
        MQ[RabbitMQ]
    end
    
    subgraph 数据存储
        ES[Elasticsearch]
        Mongo[MongoDB]
        Redis[Redis 缓存]
    end
    
    subgraph 对象存储
        OSS[阿里云 OSS]
        MinIO[MinIO]
    end
    
    App -->|发送/监听| MQ
    App -->|索引/搜索| ES
    App -->|文档读写| Mongo
    App -->|缓存热点| Redis
    App -->|文件上传| OSS
    App -->|文件上传| MinIO
```
"""

    def _scan_rabbitmq(self):
        """Scan RabbitMQ Consumers, Producers and Queue Configurations"""
        doc = ["## 2. 消息队列接口 (RabbitMQ)\n"]
        
        # 1. Consumers
        query_consumer = """
        MATCH (c:Class)-[:DECLARES]->(m:Method)
        WHERE (m.modifiers CONTAINS '@RabbitListener' OR c.modifiers CONTAINS '@RabbitListener' OR m.modifiers CONTAINS '@RabbitHandler')
        RETURN c.name as class_name, 
               c.SE_What as class_desc,
               m.name as method_name, 
               m.parameters as params,
               m.SE_What as method_desc,
               m.SE_How as method_logic,
               m.SE_Why as method_purpose,
               m.modifiers as modifiers,
               m.source_code as source_code,
               c.modifiers as class_modifiers,
               c.source_code as class_source
        """
        
        with self.driver.session() as session:
            consumers = [record.data() for record in session.run(query_consumer)]
            
        if consumers:
            for r in consumers:
                all_modifiers = (r.get('class_modifiers', '') + " " + r.get('modifiers', '') + " " + 
                                 r.get('class_source', '') + " " + r.get('source_code', ''))
                
                queue_match = re.search(r'queues\s*=\s*"([a-zA-Z0-9\._\-]+)"', all_modifiers)
                queue_name_raw = queue_match.group(1) if queue_match else "Unknown"
                queue_name = self.config.get(queue_name_raw)
                
                params = r['params'].strip("()")
                payload_type = params.split(" ")[0] if params else "Unknown"
                if "," in payload_type: payload_type = payload_type.split(",")[0]

                doc.append(f"### 消费者: `{r['class_name']}.{r['method_name']}`")
                doc.append(f"- **监听队列**: `{queue_name}`")
                doc.append(f"- **消息载体**: `{payload_type}`")
                if not self._is_spring_bean(r.get('class_modifiers', ''), r.get('class_source', '')):
                    doc.append("- **Status**: disabled (class is not a Spring bean)")
                doc.append(f"- **业务目的**: {self._clean_se(r.get('method_purpose') or r.get('method_desc'))}")
                doc.append(f"- **处理逻辑**: {self._clean_se(r['method_logic'])}")
                doc.append("")
        else:
            doc.append("*未发现 RabbitMQ 消费者*")
            
        # 2. Producers with Resolved Info
        doc.append("### 消息发送链路 (Producers)")
        query_sender = """
        MATCH (c:Class)-[:DECLARES]->(f:Field)
        WHERE f.type CONTAINS 'RabbitTemplate' OR f.type CONTAINS 'AmqpTemplate'
        RETURN c.name as class_name, c.SE_What as desc, c.modifiers as class_modifiers, c.source_code as class_source
        """
        with self.driver.session() as session:
            senders = [record.data() for record in session.run(query_sender)]
            
        if senders:
            mermaid_lines = ["```mermaid", "graph TD"]
            for s in senders:
                doc.append(f"#### 发送组件: `{s['class_name']}`")
                if not self._is_spring_bean(s.get('class_modifiers', ''), s.get('class_source', '')):
                    doc.append("> Status: disabled (class is not a Spring bean)")
                doc.append(f"> {self._clean_se(s['desc'])}\n")
                
                query_calls = f"""
                MATCH (senderClass:Class {{name: '{s['class_name']}'}})-[:DECLARES]->(sendMethod:Method)
                WHERE sendMethod.source_code CONTAINS 'convertAndSend'
                MATCH (caller:Method)-[:CALLS]->(sendMethod)
                MATCH (callerClass:Class)-[:DECLARES]->(caller)
                RETURN sendMethod.name as send_method, 
                       sendMethod.source_code as send_code,
                       callerClass.name as caller_class, 
                       caller.name as caller_method, 
                       caller.SE_What as caller_desc
                LIMIT 15
                """
                with self.driver.session() as session:
                    calls = [record.data() for record in session.run(query_calls)]
                
                if calls:
                    doc.append("| 触发业务方 | 触发方法 | 交换机 (Exchange) | 路由键 (Routing Key) | 业务场景 |")
                    doc.append("|---|---|---|---|---|")
                    for c in calls:
                        exch, rout = self._extract_mq_info(c['send_code'])
                        resolved_exch = self._resolve_enum_value(exch) if exch else self.config.get(exch, "Default")
                        resolved_rout = self._resolve_enum_value(rout) if rout else self.config.get(rout, "None")
                        
                        doc.append(f"| `{c['caller_class']}` | `{c['caller_method']}` | `{resolved_exch}` | `{resolved_rout}` | {self._clean_se(c['caller_desc'])} |")
                        mermaid_lines.append(f"    {c['caller_class']}.{c['caller_method']} -->|send| {resolved_exch}:{resolved_rout}")
                    
                    doc.append("\n**消息流向图**:")
                    # 添加延迟机制子图
                    mermaid_lines.insert(2, "    subgraph 延迟机制")
                    mermaid_lines.insert(3, "        TTL[TTL队列] -->|过期| DLX[死信交换机]")
                    mermaid_lines.insert(4, "        DLX --> Consumer[消费队列]")
                    mermaid_lines.insert(5, "    end")
                    doc.append("\n".join(mermaid_lines) + "\n```\n")
                else:
                    doc.append("*暂无明确的调用链信息*")
                doc.append("")
        else:
            doc.append("\n*未发现显式消息发送组件*")
            
        # 3. Internal Queue Details (DLX/DLQ)
        doc.append("### 队列与交换机详细配置")
        query_config = """
        MATCH (c:Class)-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS '@Bean'
          AND (
            m.return_type CONTAINS 'Queue' OR m.return_type CONTAINS 'Exchange' OR m.return_type CONTAINS 'Binding'
            OR m.source_code CONTAINS 'QueueBuilder' OR m.source_code CONTAINS 'ExchangeBuilder' OR m.source_code CONTAINS 'BindingBuilder'
          )
        RETURN c.name as class_name, m.name as method_name, m.source_code as code, m.SE_What as desc, m.return_type as return_type
        """
        with self.driver.session() as session:
            configs = [record.data() for record in session.run(query_config)]
            
        if configs:
            for cfg in configs:
                code = cfg['code']
                ret = cfg.get('return_type') or ""
                ctype = "Unknown"
                if "Binding" in ret:
                    ctype = "Binding"
                elif "Queue" in ret:
                    ctype = "Queue"
                elif "Exchange" in ret:
                    ctype = "Exchange (Direct)"
                elif "BindingBuilder" in code or " Binding " in code:
                    ctype = "Binding"
                elif "QueueBuilder" in code or "new Queue" in code:
                    ctype = "Queue"
                elif "ExchangeBuilder" in code or "DirectExchange" in code:
                    ctype = "Exchange (Direct)"
                elif "Binding" in code:
                    ctype = "Binding"
                
                # Extract extra info like DLX/DLK/TTL
                extra = []
                dlx_match = re.search(r'x-dead-letter-exchange",\s*([\w\.\(\)]+)', code)
                if dlx_match:
                    dlx_val = self._resolve_enum_value(dlx_match.group(1).split(',')[0].strip())
                    extra.append(f"DLX: {dlx_val}")
                
                dlr_match = re.search(r'x-dead-letter-routing-key",\s*([\w\.\(\)]+)', code)
                if dlr_match:
                    dlr_val = self._resolve_enum_value(dlr_match.group(1).split(',')[0].strip())
                    extra.append(f"DLK: {dlr_val}")
                
                ttl_match = re.search(r'x-message-ttl",\s*(\d+)', code)
                if ttl_match: extra.append(f"TTL: {ttl_match.group(1)}ms")
                
                # 卡片布局
                doc.append(f"\n#### 组件: `{cfg['method_name']}`")
                doc.append(f"- **类型**: {ctype}")
                if extra:
                    doc.append(f"- **配置**: {', '.join(extra)}")
                doc.append(f"- **业务背景**: {self._clean_se(cfg['desc'])}")
            doc.append("")
            
        return "\n".join(doc)

    def _extract_mq_info(self, source_code):
        """Extract exchange and routing key from convertAndSend call with enum support"""
        # Match: convertAndSend(exchange, routingKey, message)
        match = re.search(r'convertAndSend\s*\(\s*([^,]+),\s*([^,]+)', source_code)
        if match:
            exch = match.group(1).strip()
            rout = match.group(2).strip()
            # Clean up literals
            exch = exch.strip('"').strip("'")
            rout = rout.strip('"').strip("'")
            return exch, rout
        return None, None

    def _scan_scheduled(self):
        """Scan Scheduled Tasks"""
        query = """
        MATCH (c:Class)-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS '@Scheduled'
        RETURN c.name as class_name, 
               m.name as method_name, 
               m.modifiers as modifiers,
               m.source_code as source_code,
               m.SE_What as desc,
               m.SE_How as logic,
               c.modifiers as class_modifiers,
               c.source_code as class_source
        """
        doc = ["## 3. 定时任务接口\n"]
        
        with self.driver.session() as session:
            tasks = [record.data() for record in session.run(query)]
            
        if not tasks:
            doc.append("*未发现定时任务*")
            return "\n".join(doc)
            
        disabled = []
        for t in tasks:
            cron_match = re.search(r'cron\s*=\s*"([^"]+)"', t['source_code'])
            cron_exp = cron_match.group(1) if cron_match else "FixedRate/Delay"
            is_bean = self._is_spring_bean(t.get('class_modifiers', ''), t.get('class_source', ''))
            
            doc.append(f"### Task: `{t['method_name']}`")
            doc.append(f"- **Class**: `{t['class_name']}`")
            doc.append(f"- **Schedule**: `{cron_exp}`")
            if not is_bean:
                doc.append("- **Status**: disabled (class is not a Spring bean)")
                disabled.append(f"{t['class_name']}.{t['method_name']}")
            doc.append(f"- **任务描述**: {self._clean_se(t['desc'])}")
            doc.append(f"- **执行逻辑**: {self._clean_se(t['logic'])}")
            doc.append("")
            
        if disabled:
            doc.append("**Note**: The tasks above are detected by annotation, but their classes are not Spring beans. They will not run unless the class is registered.")
        
        return "\n".join(doc)

    def _scan_data_storage(self):
        """Scan Elasticsearch and MongoDB with enhanced Setting and Index extraction"""
        doc_header = ["## 4. 数据存储接口\n"]
        doc_es = ["### 4.1 Elasticsearch 索引\n"]
        doc_mongo = ["### 4.2 MongoDB 集合\n"]
        
        # Scanning Classes with @Document
        query = """
        MATCH (c:Class)
        WHERE c.modifiers CONTAINS '@Document'
        RETURN c.name as class_name, 
               c.modifiers as modifiers,
               c.source_code as source_code,
               c.SE_What as desc,
               c.SE_Why as purpose,
               c.SE_When as usage
        """
        
        with self.driver.session() as session:
            models = [record.data() for record in session.run(query)]
            
        for m in models:
            mods = m['modifiers']
            src = m['source_code']
            all_txt = mods + " " + src
            
            # Identify ES vs Mongo
            if 'indexName' in mods or 'indexName' in src:
                # ES
                index_match = re.search(r'indexName\s*=\s*"([^"]+)"', all_txt)
                index_name = index_match.group(1) if index_match else "Unknown"
                
                doc_es.append(f"### 索引: `{index_name}`")
                doc_es.append(f"- **映射类**: `{m['class_name']}`")
                
                # Extract Shards/Replicas
                shards_match = re.search(r'shards\s*=\s*(\d+)', all_txt)
                replicas_match = re.search(r'replicas\s*=\s*(\d+)', all_txt)
                if shards_match or replicas_match:
                    s = shards_match.group(1) if shards_match else "-"
                    r = replicas_match.group(1) if replicas_match else "-"
                    doc_es.append(f"- **分片配置**: 分片={s}, 副本={r}")

                doc_es.append(f"- **用途**: {self._clean_se(m['desc'])}")
                doc_es.append(f"- **设计意图**: {self._clean_se(m['purpose'])}")
                doc_es.append(f"- **使用场景**: {self._clean_se(m['usage'])}")
                
                # Fetch Fields
                fields = self._get_class_fields(m['class_name'])
                if fields:
                    doc_es.append("\n**字段结构**:")
                    doc_es.append("| 字段名 | 类型 | ES配置 |")
                    doc_es.append("|---|---|---|")
                    for f in fields:
                        es_conf = "-"
                        if "@Field" in f['modifiers']:
                            analyzer = re.search(r'analyzer\s*=\s*"([^"]+)"', f['modifiers'])
                            ftype = re.search(r'type\s*=\s*FieldType\.([A-Z][a-z]+)', f['modifiers'])
                            info = []
                            if ftype: info.append(f"Type={ftype.group(1)}")
                            if analyzer: info.append(f"Analyzer={analyzer.group(1)}")
                            if info: es_conf = ", ".join(info)
                        elif "@Id" in f['modifiers']:
                            es_conf = "ID"
                            
                        doc_es.append(f"| `{f['name']}` | `{f['type']}` | {es_conf} |")
                doc_es.append("")
                
            else:
                # Mongo
                coll_match = re.search(r'collection\s*=\s*"([^"]+)"', all_txt)
                coll_name = coll_match.group(1) if coll_match else m['class_name'][0].lower() + m['class_name'][1:]
                
                doc_mongo.append(f"### 集合: `{coll_name}`")
                doc_mongo.append(f"- **映射类**: `{m['class_name']}`")
                doc_mongo.append(f"- **用途**: {self._clean_se(m['desc'])}")
                
                # Fetch Fields and Identify Indexes
                fields = self._get_class_fields(m['class_name'])
                indexed_fields = [f['name'] for f in fields if "@Indexed" in f['modifiers']]
                if indexed_fields:
                    doc_mongo.append(f"- **索引字段**: `{', '.join(indexed_fields)}`")

                doc_mongo.append(f"- **设计意图**: {self._clean_se(m['purpose'])}")
                doc_mongo.append(f"- **使用场景**: {self._clean_se(m['usage'])}")
                
                if fields:
                    doc_mongo.append("\n**文档结构**:")
                    doc_mongo.append("| 字段名 | 类型 | 说明 |")
                    doc_mongo.append("|---|---|---|")
                    for f in fields:
                        doc_mongo.append(f"| `{f['name']}` | `{f['type']}` | {self._clean_se(f.get('SE_What', ''))} |")
                doc_mongo.append("")
                
        return "\n".join(doc_header) + "\n" + "\n".join(doc_es) + "\n\n" + "\n".join(doc_mongo)

    def _get_class_fields(self, class_name):
        query = f"""
        MATCH (c:Class {{name: '{class_name}'}})-[:DECLARES]->(f:Field)
        RETURN f.name as name, f.type as type, f.modifiers as modifiers, f.SE_What as SE_What
        """
        with self.driver.session() as session:
            return [record.data() for record in session.run(query)]

    def _scan_redis(self):
        """Scan Redis Keys and Configuration with pattern extraction from source code"""
        doc = ["## 5. Redis 缓存接口\n"]
        
        # 1. 查找所有带有 Redis 相关 @Value 的类及其方法源码
        query = """
        MATCH (c:Class)-[:DECLARES]->(f:Field)
        WHERE f.modifiers CONTAINS '@Value' 
          AND (f.name CONTAINS 'REDIS' OR f.name CONTAINS 'key')
          AND NOT f.name CONTAINS 'DATABASE' 
          AND NOT f.name CONTAINS 'HOST'
          AND NOT f.name CONTAINS 'PORT'
          AND NOT f.name CONTAINS 'PASSWORD'
        WITH c, collect({name: f.name, mods: f.modifiers}) as fields
        MATCH (c)-[:DECLARES]->(m:Method)
        WHERE m.source_code CONTAINS 'redis' OR m.source_code CONTAINS 'Redis'
        RETURN c.name as class_name, 
               c.SE_What as class_desc,
               fields,
               collect({method: m.name, code: m.source_code}) as methods
        """
        
        query_ttl = """
        MATCH (c:Class)-[:DECLARES]->(f:Field)
        WHERE f.modifiers CONTAINS '@Value' AND f.name CONTAINS 'EXPIRE'
        RETURN c.name as class_name, f.name as field_name, f.modifiers as modifiers
        """
        
        with self.driver.session() as session:
            results = [record.data() for record in session.run(query)]
            ttls = [record.data() for record in session.run(query_ttl)]

        if not results:
            doc.append("*未发现明确定义的 Redis Key*")
            return "\n".join(doc)
            
        doc.append("| 业务组件 | 缓存项说明 | Key 模式 (代码提取) | TTL 配置 |")
        doc.append("|---|---|---|---|")
        
        # 预解析全局配置映射，确保所有类共享常量
        field_to_val = {}
        query_all_fields = """
        MATCH (f:Field) 
        WHERE f.modifiers CONTAINS '@Value' AND (f.name CONTAINS 'REDIS' OR f.name CONTAINS 'key')
        RETURN f.name as name, f.modifiers as mods
        """
        with self.driver.session() as session:
            all_fields = [record.data() for record in session.run(query_all_fields)]
            for f in all_fields:
                key_config = self._extract_value_key(f['mods'])
                field_to_val[f['name']] = self.config.get(key_config)

        for r in results:
            comp = r['class_name']
            comp_desc = self._clean_se(r['class_desc'])
            
            # 找到该类的 TTL
            comp_ttls = [t for t in ttls if t['class_name'] == comp]
            ttl_vals = []
            for t in comp_ttls:
                ttl_key = self._extract_value_key(t['modifiers'])
                ttl_val = self.config.get(ttl_key)
                if ttl_val: ttl_vals.append(ttl_val)
            ttl_str = ", ".join(ttl_vals) or "-"

            # 增强的 Key 模式提取
            patterns = self._extract_redis_keys_enhanced(r['methods'], field_to_val)
            
            key_pattern = " / ".join(patterns) if patterns else "提取失败"
            doc.append(f"| `{comp}` | {comp_desc} | `{key_pattern}` | {ttl_str} |")
                
        return "\n".join(doc)

    def _extract_redis_keys_enhanced(self, methods, field_to_val):
        """Enhanced extraction covering String.format, StringBuilder and multiple patterns"""
        patterns = set()
        for m in methods:
            code = m['code']
            
            # Pattern 1: String key = ... + ...
            match_concat = re.search(r'String\s+key\s*=\s*([^;]+);', code)
            if match_concat:
                raw_parts = [p.strip() for p in match_concat.group(1).split('+')]
                resolved = []
                for part in raw_parts:
                    if part.startswith('"') and part.endswith('"'):
                        resolved.append(part.strip('"'))
                    elif part in field_to_val:
                        resolved.append(str(field_to_val[part]))
                    else:
                        clean_var = part.split('.')[-1].replace('()', '')
                        if clean_var.startswith('get') and len(clean_var) > 3:
                            clean_var = clean_var[3].lower() + clean_var[4:]
                        resolved.append(f"${{expr:{clean_var}}}")
                patterns.add("".join(resolved))

            # Pattern 2: String.format (only when building key)
            match_fmt = re.search(r'String\s+key\s*=\s*String\.format\s*\(\s*([^,]+),\s*([^)]+)', code)
            if match_fmt:
                fmt_raw = match_fmt.group(1).strip()
                if fmt_raw in field_to_val:
                    fmt_str = str(field_to_val[fmt_raw])
                else:
                    fmt_str = fmt_raw.strip('"')
                # Simple %s to variable mapping (not exhaustive but handles common cases)
                patterns.add(fmt_str.replace('%s', '${...}').replace('%d', '${...}'))

            # Pattern 3: StringBuilder
            if 'StringBuilder' in code and '.append(' in code:
                # Heuristic: Find first string literal in appends
                sb_match = re.search(r'\.append\s*\(\s*"([^"]+)"\s*\)', code)
                if sb_match:
                    patterns.add(sb_match.group(1) + "${...}")

            # Pattern 4: Direct redis call literals
            direct_matches = re.findall(r'redis\w+\.\w+\(\s*"([^"]+:[^"]*)"', code)
            for dm in direct_matches:
                patterns.add(dm)
                
        return sorted(list(patterns))
        
    def _extract_value_key(self, modifiers):
        """Extract 'redis.key.admin' from '@Value("${redis.key.admin}")'"""
        match = re.search(r'\$\{([^}]+)\}', modifiers)
        return match.group(1) if match else modifiers.replace('"', '').strip() # Return full string if no ${}

    def _extract_last_part(self, properties_key):
        """Extract 'admin' from 'redis.key.admin'"""
        if "." in properties_key:
            return properties_key.split(".")[-1]
        return properties_key

    def _scan_object_storage(self):
        """Scan OSS and MinIO usage"""
        doc = ["## 6. 对象存储接口\n"]
        
        query = """
        MATCH (c:Class)-[:DECLARES]->(f:Field)
        WHERE f.type CONTAINS 'OSSClient' OR f.type CONTAINS 'MinioClient'
        RETURN c.name as class_name, c.SE_What as desc, c.modifiers as class_modifiers, c.source_code as class_source, f.type as client_type
        """
        
        with self.driver.session() as session:
            clients = [record.data() for record in session.run(query)]
            
        if not clients:
            doc.append("*未发现对象存储客户端*")
            return "\n".join(doc)
            
        # Add Operation Config
        oss_endpoint = self.config.get("aliyun.oss.endpoint", "Unknown")
        oss_bucket = self.config.get("aliyun.oss.bucketName", "Unknown")
        oss_prefix = self.config.get("aliyun.oss.dir.prefix", "Unknown")
        minio_endpoint = self.config.get("minio.endpoint", "Unknown")
        minio_bucket = self.config.get("minio.bucketName", "Unknown")
        
        doc.append("### 运维配置")
        if oss_endpoint != "Unknown":
            doc.append(f"- **Aliyun OSS Endpoint**: `{oss_endpoint}`")
            doc.append(f"- **Aliyun OSS Bucket**: `{oss_bucket}`")
            doc.append(f"- **Aliyun OSS Prefix**: `{oss_prefix}`")
        if minio_endpoint != "Unknown":
            doc.append(f"- **MinIO Endpoint**: `{minio_endpoint}`")
            doc.append(f"- **MinIO Bucket**: `{minio_bucket}`")
        doc.append("")
            
        doc.append("| 存储类型 | 使用组件 | 组件用途 |")
        doc.append("|---|---|---|")
        
        for c in clients:
            type_name = "阿里云 OSS" if "OSSClient" in c['client_type'] else "MinIO"
            doc.append(f"| {type_name} | `{c['class_name']}` | {self._clean_se(c['desc'])} |")
            
        return "\n".join(doc)

if __name__ == "__main__":
    generator = BackendInterfaceGenerator(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        generator.generate_report()
    finally:
        generator.close()
