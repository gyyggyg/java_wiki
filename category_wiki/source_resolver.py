"""批量把 nodeId 解析为 Neo4j 节点的 name 属性（用于 neo4j_source 字段）"""

import logging
from typing import Dict, List

logger = logging.getLogger("category_wiki.source_resolver")


async def resolve_sources(neo4j, node_ids: List[str]) -> Dict[str, str]:
    """给一批 nodeId，一次查出它们的 name 属性。

    Args:
        neo4j: Neo4jInterface
        node_ids: list of nodeId (int or str)

    Returns:
        {str(nodeId): name_string}
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
    RETURN n.nodeId AS nodeId, n.name AS name
    """
    rows = await neo4j.execute_query(query, {"ids": list(set(ids_int))})
    out = {}
    for r in rows:
        out[str(r["nodeId"])] = r.get("name") or ""
    return out


def collect_all_node_ids(node) -> List[str]:
    """递归提取一棵 schema 节点树中所有 neo4j_id 的 nodeId 字符串集合"""
    seen = []
    _collect(node, seen)
    # 去重保持顺序
    seen_set = set()
    result = []
    for s in seen:
        if s and s not in seen_set:
            seen_set.add(s)
            result.append(s)
    return result


def _collect(node, acc: List[str]):
    nid = getattr(node, "neo4j_id", None)
    if isinstance(nid, dict):
        for v in nid.values():
            if isinstance(v, list):
                for x in v:
                    if x:
                        acc.append(str(x))
            elif v:
                acc.append(str(v))
    content = getattr(node, "content", None)
    if isinstance(content, list):
        for sub in content:
            if hasattr(sub, "neo4j_id") or hasattr(sub, "content"):
                _collect(sub, acc)


def fill_neo4j_source_recursively(node, sources_map: Dict[str, str]):
    """给整棵 schema 树打上 neo4j_source"""
    nid = getattr(node, "neo4j_id", None)
    if isinstance(nid, dict):
        new_source = {}
        for k, v in nid.items():
            if isinstance(v, list):
                new_source[k] = [sources_map.get(str(x), "") for x in v]
            else:
                new_source[k] = sources_map.get(str(v), "") if v else ""
        node.neo4j_source = new_source

    content = getattr(node, "content", None)
    if isinstance(content, list):
        for sub in content:
            if hasattr(sub, "neo4j_id") or hasattr(sub, "content"):
                fill_neo4j_source_recursively(sub, sources_map)
