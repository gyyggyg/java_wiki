"""
探索 Neo4j 图数据库中的 RabbitMQ 链路
"""

from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7689"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "c8a3974ba62qcc2"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def run_query(query, params=None):
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]

def print_results(title, results):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    if not results:
        print("  (无结果)")
        return
    for i, r in enumerate(results, 1):
        print(f"\n[{i}]")
        for k, v in r.items():
            # 截断过长的值
            v_str = str(v)
            if len(v_str) > 200:
                v_str = v_str[:200] + "..."
            print(f"  {k}: {v_str}")

# ============================================================================
# 1. 生产者侧探索
# ============================================================================

print("\n" + "#"*70)
print("# 生产者侧探索: CancelOrderSender")
print("#"*70)

# 1.1 CancelOrderSender 的所有出向关系
print_results(
    "CancelOrderSender 类的所有出向关系",
    run_query("""
        MATCH (c:Class {name: "CancelOrderSender"})-[r]->(n)
        RETURN type(r) as rel_type, labels(n) as node_labels, n.name as name
    """)
)

# 1.2 sendMessage 方法的所有出向关系
print_results(
    "sendMessage 方法的所有出向关系",
    run_query("""
        MATCH (c:Class {name: "CancelOrderSender"})-[:DECLARES]->(m:Method {name: "sendMessage"})
        MATCH (m)-[r]->(n)
        RETURN type(r) as rel_type, labels(n) as node_labels, n.name as name, n.source_code as source_code
    """)
)

# 1.3 sendMessage 引用的枚举常量详情
print_results(
    "sendMessage 引用的枚举常量",
    run_query("""
        MATCH (c:Class {name: "CancelOrderSender"})-[:DECLARES]->(m:Method {name: "sendMessage"})
        MATCH (m)-[:REFERENCES]->(ec:EnumConstant)
        RETURN ec.name as enum_constant, ec.source_code as source_code, ec.fully_qualified_name as fqn
    """)
)

# 1.4 枚举类 QueueEnum 的字段定义
print_results(
    "QueueEnum 枚举类的字段定义",
    run_query("""
        MATCH (e:Enum {name: "QueueEnum"})-[:DECLARES]->(f:Field)
        RETURN f.name as field_name, f.type as field_type, f.source_code as source_code
    """)
)

# 1.5 QueueEnum 的所有枚举常量
print_results(
    "QueueEnum 的所有枚举常量",
    run_query("""
        MATCH (e:Enum {name: "QueueEnum"})-[:DECLARES]->(ec:EnumConstant)
        RETURN ec.name as constant_name, ec.source_code as source_code
    """)
)

# ============================================================================
# 2. 消费者侧探索
# ============================================================================

print("\n" + "#"*70)
print("# 消费者侧探索")
print("#"*70)

# 2.1 查找所有带 @RabbitListener 或 @RabbitHandler 的类/方法
print_results(
    "RabbitMQ 消费者（@RabbitListener/@RabbitHandler）",
    run_query("""
        MATCH (c:Class)-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS '@RabbitHandler'
           OR m.modifiers CONTAINS '@RabbitListener'
           OR c.modifiers CONTAINS '@RabbitListener'
        RETURN c.name as class_name, c.modifiers as class_modifiers,
               m.name as method_name, m.modifiers as method_modifiers
    """)
)

# 2.2 消费者类的所有出向关系
print_results(
    "CancelOrderReceiver 类的所有出向关系",
    run_query("""
        MATCH (c:Class {name: "CancelOrderReceiver"})-[r]->(n)
        RETURN type(r) as rel_type, labels(n) as node_labels, n.name as name, n.source_code as source_code
    """)
)

# 2.3 查找注解节点
print_results(
    "CancelOrderReceiver 的注解",
    run_query("""
        MATCH (a:Annotation)-[:ANNOTATES]->(c:Class {name: "CancelOrderReceiver"})
        RETURN a.name as annotation_name, a.source_code as annotation_source
    """)
)

# 2.4 消费者类的 modifiers 属性（可能包含注解信息）
print_results(
    "CancelOrderReceiver 类的 modifiers",
    run_query("""
        MATCH (c:Class {name: "CancelOrderReceiver"})
        RETURN c.name as name, c.modifiers as modifiers, c.source_code as source_code
    """)
)

# ============================================================================
# 3. 配置类探索
# ============================================================================

print("\n" + "#"*70)
print("# RabbitMQ 配置类探索")
print("#"*70)

# 3.1 RabbitMqConfig 类的所有方法
print_results(
    "RabbitMqConfig 的 @Bean 方法",
    run_query("""
        MATCH (c:Class {name: "RabbitMqConfig"})-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS '@Bean'
        RETURN m.name as method_name, m.return_type as return_type, m.source_code as source_code
    """)
)

# ============================================================================
# 4. 尝试通过图关系找到完整链路
# ============================================================================

print("\n" + "#"*70)
print("# 尝试通过图关系追踪链路")
print("#"*70)

# 4.1 从生产者到枚举的路径
print_results(
    "生产者 -> 枚举常量 -> 枚举类",
    run_query("""
        MATCH path = (c:Class {name: "CancelOrderSender"})-[:DECLARES]->(m:Method)-[:REFERENCES]->(ec:EnumConstant)<-[:DECLARES]-(e:Enum)
        RETURN c.name as producer, m.name as method, ec.name as enum_constant, e.name as enum_class
    """)
)

# 4.2 检查枚举常量和配置类之间是否有关系
print_results(
    "枚举常量被哪些节点引用",
    run_query("""
        MATCH (n)-[r]->(ec:EnumConstant {name: "QUEUE_TTL_ORDER_CANCEL"})
        RETURN labels(n) as from_labels, n.name as from_name, type(r) as rel_type
    """)
)

print_results(
    "枚举常量 QUEUE_ORDER_CANCEL 被哪些节点引用",
    run_query("""
        MATCH (n)-[r]->(ec:EnumConstant {name: "QUEUE_ORDER_CANCEL"})
        RETURN labels(n) as from_labels, n.name as from_name, type(r) as rel_type
    """)
)

# 4.3 检查队列配置方法引用了什么
print_results(
    "orderTtlQueue 方法的所有出向关系",
    run_query("""
        MATCH (c:Class {name: "RabbitMqConfig"})-[:DECLARES]->(m:Method {name: "orderTtlQueue"})
        MATCH (m)-[r]->(n)
        RETURN type(r) as rel_type, labels(n) as node_labels, n.name as name, n.source_code as source_code
    """)
)

# 4.4 绑定方法的引用
print_results(
    "orderTtlBinding 方法的所有出向关系",
    run_query("""
        MATCH (c:Class {name: "RabbitMqConfig"})-[:DECLARES]->(m:Method {name: "orderTtlBinding"})
        MATCH (m)-[r]->(n)
        RETURN type(r) as rel_type, labels(n) as node_labels, n.name as name, n.source_code as source_code
    """)
)

# ============================================================================
# 5. 深入探索：尝试构建完整链路
# ============================================================================

print("\n" + "#"*70)
print("# 深入探索：构建完整链路")
print("#"*70)

# 5.1 从生产者出发，找到它引用的枚举常量，获取 exchange/routeKey
print_results(
    "生产者 sendMessage 使用的字段（exchange/routeKey）",
    run_query("""
        MATCH (c:Class {name: "CancelOrderSender"})-[:DECLARES]->(m:Method {name: "sendMessage"})
        MATCH (m)-[:USES]->(f:Field)
        WHERE f.name IN ['exchange', 'routeKey', 'name']
        RETURN f.name as field_name, f.source_code as source_code
    """)
)

# 5.2 查看 sendMessage 引用的枚举常量属于哪个枚举，以及枚举的字段顺序
print_results(
    "枚举类 QueueEnum 的构造函数",
    run_query("""
        MATCH (e:Enum {name: "QueueEnum"})-[:DECLARES]->(m:Method)
        WHERE m.name = "QueueEnum" OR m.name CONTAINS "<init>"
        RETURN m.name as method_name, m.parameters as parameters, m.source_code as source_code
    """)
)

# 5.3 找到所有引用 QUEUE_TTL_ORDER_CANCEL 的配置方法
print_results(
    "引用 QUEUE_TTL_ORDER_CANCEL 的所有方法及其完整代码",
    run_query("""
        MATCH (m:Method)-[:REFERENCES]->(ec:EnumConstant {name: "QUEUE_TTL_ORDER_CANCEL"})
        RETURN m.name as method_name, m.source_code as source_code
    """)
)

# 5.4 找到所有引用 QUEUE_ORDER_CANCEL 的配置方法
print_results(
    "引用 QUEUE_ORDER_CANCEL 的所有方法及其完整代码",
    run_query("""
        MATCH (m:Method)-[:REFERENCES]->(ec:EnumConstant {name: "QUEUE_ORDER_CANCEL"})
        RETURN m.name as method_name, m.source_code as source_code
    """)
)

# 5.5 查看 orderTtlQueue 的完整源码（包含死信配置）
print_results(
    "orderTtlQueue 完整源码",
    run_query("""
        MATCH (c:Class {name: "RabbitMqConfig"})-[:DECLARES]->(m:Method {name: "orderTtlQueue"})
        RETURN m.source_code as source_code
    """)
)

# 5.6 检查是否有方法调用关系能连接配置
print_results(
    "orderTtlQueue 调用了哪些方法（包括 withArgument）",
    run_query("""
        MATCH (c:Class {name: "RabbitMqConfig"})-[:DECLARES]->(m:Method {name: "orderTtlQueue"})
        MATCH (m)-[:CALLS]->(called:Method)
        RETURN called.name as called_method, called.source_code as source_code
    """)
)

# 5.7 消费者的注解内容 - 尝试从 Annotation 节点获取
print_results(
    "RabbitListener 注解的详细信息",
    run_query("""
        MATCH (a:Annotation {name: "RabbitListener"})-[:ANNOTATES]->(c:Class {name: "CancelOrderReceiver"})
        RETURN a.source_code as annotation_source, a.name as annotation_name
    """)
)

# 5.8 检查是否有 Annotation 节点带有参数信息
print_results(
    "所有 Annotation 节点的属性",
    run_query("""
        MATCH (a:Annotation {name: "RabbitListener"})
        RETURN a.name, a.source_code, a.fully_qualified_name, keys(a) as all_keys
        LIMIT 5
    """)
)

# 5.9 尝试从消费者类的源码中提取队列名
print_results(
    "CancelOrderReceiver 完整源码",
    run_query("""
        MATCH (c:Class {name: "CancelOrderReceiver"})
        RETURN c.source_code as source_code
    """)
)

# 5.10 检查绑定方法的完整信息
print_results(
    "orderBinding 方法完整源码（绑定 orderQueue 到 orderDirect）",
    run_query("""
        MATCH (c:Class {name: "RabbitMqConfig"})-[:DECLARES]->(m:Method {name: "orderBinding"})
        RETURN m.source_code as source_code
    """)
)

# ============================================================================
# 6. 尝试用图路径找到生产者到消费者的连接
# ============================================================================

print("\n" + "#"*70)
print("# 尝试找到从生产者到消费者的图路径")
print("#"*70)

# 6.1 生产者 -> 枚举常量 -> 配置方法 的路径
print_results(
    "生产者和配置方法共同引用的枚举常量",
    run_query("""
        MATCH (producer:Method {name: "sendMessage"})-[:REFERENCES]->(ec:EnumConstant)
        MATCH (config:Method)-[:REFERENCES]->(ec)
        WHERE config.name <> "sendMessage"
        RETURN producer.name as producer_method, ec.name as enum_constant, config.name as config_method
    """)
)

# 6.2 TTL队列和普通队列之间的关联（通过枚举常量）
print_results(
    "orderTtlQueue 和 orderQueue 引用的枚举常量对比",
    run_query("""
        MATCH (ttlQueue:Method {name: "orderTtlQueue"})-[:REFERENCES]->(ec1:EnumConstant)
        MATCH (orderQueue:Method {name: "orderQueue"})-[:REFERENCES]->(ec2:EnumConstant)
        RETURN ttlQueue.name, collect(distinct ec1.name) as ttl_queue_refs,
               orderQueue.name, collect(distinct ec2.name) as order_queue_refs
    """)
)

# 6.3 检查 orderDirect 交换机的配置
print_results(
    "orderDirect 方法完整源码",
    run_query("""
        MATCH (c:Class {name: "RabbitMqConfig"})-[:DECLARES]->(m:Method {name: "orderDirect"})
        RETURN m.source_code as source_code
    """)
)

driver.close()
print("\n\n探索完成!")
