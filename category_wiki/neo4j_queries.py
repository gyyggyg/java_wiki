"""所有 Cypher 查询集中定义。每个函数返回一个 list[dict]（execute_query 的输出）"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger("category_wiki.queries")


async def fetch_class_briefs(neo4j, class_ids: List[str]) -> List[Dict]:
    """§1 概述用：拿类/接口/枚举的名字 + SE_What/SE_Why/modifiers"""
    if not class_ids:
        return []
    ids_int = [int(x) for x in class_ids if str(x).isdigit()]
    query = """
    MATCH (c) WHERE c.nodeId IN $ids AND (c:Class OR c:Interface OR c:Enum)
    OPTIONAL MATCH (file:File)-[:DECLARES]->(c)
    RETURN c.nodeId AS nodeId, c.name AS name, labels(c) AS labels,
           c.modifiers AS modifiers,
           c.SE_What AS se_what,
           c.SE_Why AS se_why,
           file.name AS file_name
    ORDER BY c.name
    """
    return await neo4j.execute_query(query, {"ids": ids_int})


async def fetch_http_endpoints(neo4j, class_ids: List[str]) -> List[Dict]:
    """§2.1 HTTP 入口：@RestController / @Controller 下带 Mapping 的方法"""
    if not class_ids:
        return []
    ids_int = [int(x) for x in class_ids if str(x).isdigit()]
    query = """
    MATCH (c:Class)-[:DECLARES]->(m:Method)
    WHERE c.nodeId IN $ids
      AND (c.modifiers CONTAINS '@RestController' OR c.modifiers CONTAINS '@Controller')
      AND m.modifiers =~ '(?s).*@(Get|Post|Put|Delete|Request|Patch)Mapping.*'
    RETURN c.nodeId AS class_id, c.name AS class_name,
           c.modifiers AS class_modifiers,
           m.nodeId AS method_id, m.name AS method_name,
           m.modifiers AS method_modifiers,
           m.SE_What AS method_desc
    ORDER BY c.name, m.name
    """
    return await neo4j.execute_query(query, {"ids": ids_int})


async def fetch_scheduled_methods(neo4j, class_ids: List[str]) -> List[Dict]:
    """§2.2 定时任务：@Scheduled"""
    if not class_ids:
        return []
    ids_int = [int(x) for x in class_ids if str(x).isdigit()]
    query = """
    MATCH (c:Class)-[:DECLARES]->(m:Method)
    WHERE c.nodeId IN $ids AND m.modifiers CONTAINS '@Scheduled'
    RETURN c.nodeId AS class_id, c.name AS class_name,
           m.nodeId AS method_id, m.name AS method_name,
           m.modifiers AS method_modifiers,
           m.source_code AS source_code,
           m.SE_What AS method_desc
    ORDER BY c.name, m.name
    """
    return await neo4j.execute_query(query, {"ids": ids_int})


async def fetch_mq_listeners(neo4j, class_ids: List[str]) -> List[Dict]:
    """§2.3 MQ 消费者：@RabbitListener / @RabbitHandler"""
    if not class_ids:
        return []
    ids_int = [int(x) for x in class_ids if str(x).isdigit()]
    query = """
    MATCH (c:Class)-[:DECLARES]->(m:Method)
    WHERE c.nodeId IN $ids
      AND (m.modifiers CONTAINS '@RabbitListener' OR m.modifiers CONTAINS '@RabbitHandler'
           OR c.modifiers CONTAINS '@RabbitListener')
    RETURN c.nodeId AS class_id, c.name AS class_name,
           c.modifiers AS class_modifiers,
           m.nodeId AS method_id, m.name AS method_name,
           m.modifiers AS method_modifiers,
           m.SE_What AS method_desc
    ORDER BY c.name, m.name
    """
    return await neo4j.execute_query(query, {"ids": ids_int})


async def fetch_call_edges_from(neo4j, entry_method_ids: List[str], max_depth: int = 3,
                                max_edges: int = 80) -> List[Dict]:
    """§3 时序图用：从入口方法追踪 CALLS 链路

    返回每条调用边 (from_class.from_method -> to_class.to_method)，
    去重后用于生成 Mermaid sequenceDiagram。
    """
    if not entry_method_ids:
        return []
    ids_int = [int(x) for x in entry_method_ids if str(x).isdigit()]
    # 用 APOC 风格的展开查询 - 不假设 APOC 已装，用普通路径查询
    query = f"""
    MATCH (start:Method) WHERE start.nodeId IN $ids
    OPTIONAL MATCH (sc)-[:DECLARES]->(start)
    WITH start, sc
    MATCH path = (start)-[:CALLS*1..{max_depth}]->(target:Method)
    OPTIONAL MATCH (tc)-[:DECLARES]->(target)
    RETURN DISTINCT
           sc.nodeId AS start_class_id, sc.name AS start_class_name,
           start.nodeId AS start_method_id, start.name AS start_method_name,
           tc.nodeId AS target_class_id, tc.name AS target_class_name,
           target.nodeId AS target_method_id, target.name AS target_method_name,
           length(path) AS depth
    ORDER BY depth, start_class_name, target_class_name
    LIMIT $limit
    """
    return await neo4j.execute_query(query, {"ids": ids_int, "limit": max_edges})


async def fetch_call_edges_internal(neo4j, method_ids: List[str], max_edges: int = 80) -> List[Dict]:
    """§3 时序图补充：in-scope 方法之间的直接 CALLS 边（深度 1）

    覆盖入口查询之外的 service/dao 互调情况。
    """
    if not method_ids:
        return []
    ids_int = [int(x) for x in method_ids if str(x).isdigit()]
    query = """
    MATCH (from:Method)-[:CALLS]->(to:Method)
    WHERE from.nodeId IN $ids AND to.nodeId IN $ids
    OPTIONAL MATCH (fc)-[:DECLARES]->(from)
    OPTIONAL MATCH (tc)-[:DECLARES]->(to)
    RETURN DISTINCT
           fc.nodeId AS from_class_id, fc.name AS from_class_name,
           from.nodeId AS from_method_id, from.name AS from_method_name,
           tc.nodeId AS to_class_id, tc.name AS to_class_name,
           to.nodeId AS to_method_id, to.name AS to_method_name
    LIMIT $limit
    """
    return await neo4j.execute_query(query, {"ids": ids_int, "limit": max_edges})


async def fetch_method_ids_from_classes(neo4j, class_ids: List[str]) -> List[str]:
    """给一批 Class/Interface/Enum nodeId，返回其所有 Method nodeId。

    §3 内部调用边查询的必备前置：从 scope.class_ids 推导出完整的 in_scope method 集。
    """
    if not class_ids:
        return []
    ids_int = [int(x) for x in class_ids if str(x).isdigit()]
    query = """
    MATCH (c) WHERE c.nodeId IN $ids
      AND (c:Class OR c:Interface OR c:Enum OR c:Record)
    MATCH (c)-[:DECLARES]->(m:Method)
    RETURN DISTINCT m.nodeId AS nodeId
    """
    rows = await neo4j.execute_query(query, {"ids": ids_int})
    return [str(r["nodeId"]) for r in rows]


async def fetch_classes_full_context(neo4j, class_ids: List[str]) -> List[Dict]:
    """§2/§3 新策略用：给一批 Class/Interface/Enum/Record nodeId，
    返回每个类的 source_code + SE_What + 名字 + 标签 + 文件路径。

    这是"让 LLM 自己判断业务流"的核心信息源。
    """
    if not class_ids:
        return []
    ids_int = [int(x) for x in class_ids if str(x).isdigit()]
    query = """
    MATCH (c) WHERE c.nodeId IN $ids
      AND (c:Class OR c:Interface OR c:Enum OR c:Record)
    OPTIONAL MATCH (f:File)-[:DECLARES]->(c)
    RETURN c.nodeId AS class_id,
           c.name AS name,
           labels(c) AS labels,
           c.source_code AS source_code,
           c.SE_What AS se_what,
           f.name AS file_name
    ORDER BY c.name
    """
    return await neo4j.execute_query(query, {"ids": ids_int})
