"""业务流 wiki 需要的 Neo4j 查询（独立于 category_wiki）"""

import logging
from typing import Dict, List

logger = logging.getLogger("business_flow.neo4j_fetch")


async def fetch_classes_full_context(neo4j, class_ids: List[str]) -> List[Dict]:
    """给一批 Class/Interface/Enum/Record nodeId，
    返回每个类的 source_code + SE_What + 名字 + 标签 + 文件路径。
    这是 §2/§3 的核心信息源。"""
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


async def fetch_class_briefs(neo4j, class_ids: List[str]) -> List[Dict]:
    """§1 概述用：拿类/接口/枚举的 SE_What/SE_Why/modifiers"""
    if not class_ids:
        return []
    ids_int = [int(x) for x in class_ids if str(x).isdigit()]
    query = """
    MATCH (c) WHERE c.nodeId IN $ids
      AND (c:Class OR c:Interface OR c:Enum OR c:Record)
    OPTIONAL MATCH (file:File)-[:DECLARES]->(c)
    RETURN c.nodeId AS nodeId, c.name AS name, labels(c) AS labels,
           c.modifiers AS modifiers,
           c.SE_What AS se_what, c.SE_Why AS se_why,
           file.name AS file_name
    ORDER BY c.name
    """
    return await neo4j.execute_query(query, {"ids": ids_int})


async def fetch_classes_with_fields(neo4j, class_ids: List[str], min_fields: int = 2,
                                     max_classes: int = 30) -> List[Dict]:
    """§4 数据结构用：拿指定类的字段清单 + 字段的 HAS_TYPE 引用关系。

    返回按字段数量降序排列的类清单，每个类含 fields 列表。
    只返回字段数 >= min_fields 的类，避免工具类污染。
    """
    if not class_ids:
        return []
    ids_int = [int(x) for x in class_ids if str(x).isdigit()]
    query = """
    MATCH (c:Class) WHERE c.nodeId IN $ids
    MATCH (c)-[:DECLARES]->(f:Field)
    OPTIONAL MATCH (f)-[:HAS_TYPE]->(t)
    WHERE t:Class OR t:Interface OR t:Enum
    WITH c, f, t
    ORDER BY f.name
    WITH c,
         collect({
             field_name: f.name,
             field_type: f.type,
             field_modifiers: f.modifiers,
             target_class_id: t.nodeId,
             target_class_name: t.name
         }) AS fields
    WHERE size(fields) >= $min_fields
    OPTIONAL MATCH (file:File)-[:DECLARES]->(c)
    RETURN c.nodeId AS class_id,
           c.name AS class_name,
           c.modifiers AS modifiers,
           c.SE_What AS se_what,
           file.name AS file_name,
           fields
    ORDER BY size(fields) DESC
    LIMIT $limit
    """
    return await neo4j.execute_query(query, {
        "ids": ids_int,
        "min_fields": min_fields,
        "limit": max_classes,
    })


async def search_classes_by_names(neo4j, names: List[str]) -> List[Dict]:
    """按类名精确匹配，查找 Class/Interface/Enum/Record。

    用于 §2 数据模型首次输出 missing_data 时，按 `suspected_name` 回查 Neo4j
    补全 scope。返回与 fetch_classes_full_context 同形 row。
    """
    if not names:
        return []
    clean = sorted({str(n).strip() for n in names if n and str(n).strip()})
    if not clean:
        return []
    query = """
    MATCH (c) WHERE c.name IN $names
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
    return await neo4j.execute_query(query, {"names": clean})


async def resolve_source_files(neo4j, node_ids: List[str]) -> Dict[str, Dict[str, str]]:
    """批量把 nodeId 解析成 {name, file_name}（用于构造 source_id_list）。

    支持 Class/Interface/Enum/Method/Field 等任意节点：
    - 类类型直接取 File-[:DECLARES]->Class 的 file
    - 成员节点（Method/Field）取其 declaring class 的 file
    """
    if not node_ids:
        return {}
    ids_int = []
    for s in node_ids:
        try:
            ids_int.append(int(s))
        except (TypeError, ValueError):
            continue
    if not ids_int:
        return {}
    query = """
    MATCH (n) WHERE n.nodeId IN $ids
    OPTIONAL MATCH (f:File)-[:DECLARES]->(n)
    OPTIONAL MATCH (n)<-[:DECLARES]-(parent)<-[:DECLARES]-(f2:File)
      WHERE n:Method OR n:Field
    RETURN n.nodeId AS nodeId,
           n.name AS name,
           coalesce(f.name, f2.name) AS file_name,
           labels(n) AS labels
    """
    rows = await neo4j.execute_query(query, {"ids": list(set(ids_int))})
    out = {}
    for r in rows:
        nid = str(r["nodeId"])
        out[nid] = {
            "name": r.get("name") or "",
            "file_name": r.get("file_name") or "",
            "labels": r.get("labels") or [],
        }
    return out


async def resolve_sources(neo4j, node_ids: List[str]) -> Dict[str, str]:
    """批量把 nodeId 解析成 name（用于 neo4j_source 字段）"""
    if not node_ids:
        return {}
    ids_int = []
    for s in node_ids:
        try:
            ids_int.append(int(s))
        except (TypeError, ValueError):
            continue
    if not ids_int:
        return {}
    query = """
    MATCH (n) WHERE n.nodeId IN $ids
    RETURN n.nodeId AS nodeId, n.name AS name
    """
    rows = await neo4j.execute_query(query, {"ids": list(set(ids_int))})
    return {str(r["nodeId"]): r.get("name") or "" for r in rows}
