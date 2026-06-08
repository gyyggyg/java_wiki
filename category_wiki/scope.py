"""分类范围解析 —— 方案 A：读每个 page 的 .json，收集 nodeId

从 new_wiki_index.json 拿到某个 category 的 pages 清单，
对每个 page 打开其 wiki JSON 文件，抽出全部 nodeId，
再根据 Neo4j 的节点 label 拆分为 class_ids / method_ids 等。
"""

import json
import os
import logging
from typing import Dict, List, Set, Tuple

logger = logging.getLogger("category_wiki.scope")


def load_new_wiki_index(path: str) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"new_wiki_index 不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_category(new_wiki_index: dict, category_path: str) -> dict:
    for c in new_wiki_index.get("categories", []):
        if c.get("path") == category_path:
            return c
    raise KeyError(f"未在 new_wiki_index 中找到 category: {category_path}")


def collect_node_ids_from_wiki_file(wiki_json_path: str) -> Set[str]:
    """从一个 wiki JSON 文件中收集所有出现过的 nodeId（字符串形式）"""
    all_ids: Set[str] = set()
    if not os.path.isfile(wiki_json_path):
        logger.warning(f"wiki 文件不存在: {wiki_json_path}")
        return all_ids

    try:
        with open(wiki_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"读取 {wiki_json_path} 失败: {e}")
        return all_ids

    # 1. 顶层 source_id 列表（新 schema 里是 list of {source_id, name, lines}）
    top_source_id = data.get("source_id")
    if isinstance(top_source_id, list):
        for item in top_source_id:
            if isinstance(item, dict):
                sid = item.get("source_id")
                if sid is not None:
                    all_ids.add(str(sid))

    # 2. 也兼容老 schema 的顶层 source_id_list
    top_source_id_list = data.get("source_id_list")
    if isinstance(top_source_id_list, list):
        for item in top_source_id_list:
            if isinstance(item, dict):
                sid = item.get("source_id")
                if sid is not None:
                    all_ids.add(str(sid))

    # 3. 递归扫描整棵 markdown_content（或 wiki）树的 neo4j_id
    def _walk(node):
        if isinstance(node, dict):
            nid = node.get("neo4j_id")
            if isinstance(nid, dict):
                for v in nid.values():
                    if isinstance(v, list):
                        for x in v:
                            if x:
                                all_ids.add(str(x))
                    elif v:
                        all_ids.add(str(v))
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    _walk(data)
    return all_ids


async def partition_by_label(neo4j, node_ids: List[str]) -> Dict[str, List[str]]:
    """把一堆 nodeId 按 Neo4j 节点 label 分桶。

    返回: {
        "class_ids", "method_ids", "field_ids",
        "interface_ids", "enum_ids", "annotation_ids", "record_ids",
        "file_ids", "package_ids", "directory_ids", "block_ids",
        "other_ids"
    }
    """
    buckets = {
        "class_ids": [],
        "method_ids": [],
        "field_ids": [],
        "interface_ids": [],
        "enum_ids": [],
        "annotation_ids": [],
        "record_ids": [],
        "file_ids": [],
        "package_ids": [],
        "directory_ids": [],
        "block_ids": [],
        "other_ids": [],
    }
    if not node_ids:
        return buckets

    ids_int = []
    for s in node_ids:
        try:
            ids_int.append(int(s))
        except (TypeError, ValueError):
            continue

    query = """
    MATCH (n) WHERE n.nodeId IN $ids
    RETURN n.nodeId AS nodeId, labels(n) AS labels
    """
    rows = await neo4j.execute_query(query, {"ids": ids_int})

    for r in rows:
        nid = str(r["nodeId"])
        labels = r.get("labels") or []
        if "Class" in labels:
            buckets["class_ids"].append(nid)
        elif "Interface" in labels:
            buckets["interface_ids"].append(nid)
        elif "Enum" in labels:
            buckets["enum_ids"].append(nid)
        elif "Annotation" in labels:
            buckets["annotation_ids"].append(nid)
        elif "Record" in labels:
            buckets["record_ids"].append(nid)
        elif "Method" in labels:
            buckets["method_ids"].append(nid)
        elif "Field" in labels:
            buckets["field_ids"].append(nid)
        elif "File" in labels:
            buckets["file_ids"].append(nid)
        elif "Package" in labels:
            buckets["package_ids"].append(nid)
        elif "Directory" in labels:
            buckets["directory_ids"].append(nid)
        elif "Block" in labels:
            buckets["block_ids"].append(nid)
        else:
            buckets["other_ids"].append(nid)
    return buckets


# ============ 向下展开：容器节点 → Class/Interface/Enum ============

MAX_DIR_INCLUDE_DEPTH = 8  # Directory 可能有多层嵌套
MAX_F2C_DEPTH = 10         # Block 树可能比较深


async def _expand_files_to_classes(neo4j, file_ids: List[str]) -> List[Dict]:
    """File -[:DECLARES]-> Class/Interface/Enum/Record/Annotation"""
    if not file_ids:
        return []
    ids_int = [int(x) for x in file_ids if str(x).isdigit()]
    query = """
    MATCH (f:File) WHERE f.nodeId IN $ids
    MATCH (f)-[:DECLARES]->(c)
    WHERE c:Class OR c:Interface OR c:Enum OR c:Record OR c:Annotation
    RETURN DISTINCT c.nodeId AS nodeId, labels(c) AS labels, c.name AS name
    """
    return await neo4j.execute_query(query, {"ids": ids_int})


async def _expand_packages_to_classes(neo4j, package_ids: List[str]) -> List[Dict]:
    """Package -[:CONTAINS]-> File -[:DECLARES]-> Class/..."""
    if not package_ids:
        return []
    ids_int = [int(x) for x in package_ids if str(x).isdigit()]
    query = """
    MATCH (p:Package) WHERE p.nodeId IN $ids
    MATCH (p)-[:CONTAINS]->(f:File)-[:DECLARES]->(c)
    WHERE c:Class OR c:Interface OR c:Enum OR c:Record OR c:Annotation
    RETURN DISTINCT c.nodeId AS nodeId, labels(c) AS labels, c.name AS name
    """
    return await neo4j.execute_query(query, {"ids": ids_int})


async def _expand_directories_to_classes(neo4j, directory_ids: List[str]) -> List[Dict]:
    """Directory -[:DIR_INCLUDE*]-> File -[:DECLARES]-> Class/..."""
    if not directory_ids:
        return []
    ids_int = [int(x) for x in directory_ids if str(x).isdigit()]
    query = f"""
    MATCH (d:Directory) WHERE d.nodeId IN $ids
    MATCH (d)-[:DIR_INCLUDE*1..{MAX_DIR_INCLUDE_DEPTH}]->(f:File)
    MATCH (f)-[:DECLARES]->(c)
    WHERE c:Class OR c:Interface OR c:Enum OR c:Record OR c:Annotation
    RETURN DISTINCT c.nodeId AS nodeId, labels(c) AS labels, c.name AS name
    """
    return await neo4j.execute_query(query, {"ids": ids_int})


async def _expand_blocks_to_classes(neo4j, block_ids: List[str]) -> List[Dict]:
    """Block -[:f2c*]-> File -[:DECLARES]-> Class/..."""
    if not block_ids:
        return []
    ids_int = [int(x) for x in block_ids if str(x).isdigit()]
    query = f"""
    MATCH (b:Block) WHERE b.nodeId IN $ids
    MATCH (b)-[:f2c*1..{MAX_F2C_DEPTH}]->(f:File)
    MATCH (f)-[:DECLARES]->(c)
    WHERE c:Class OR c:Interface OR c:Enum OR c:Record OR c:Annotation
    RETURN DISTINCT c.nodeId AS nodeId, labels(c) AS labels, c.name AS name
    """
    return await neo4j.execute_query(query, {"ids": ids_int})


async def _promote_members_to_classes(neo4j, member_ids: List[str]) -> List[Dict]:
    """Method / Field → 反查其 declaring Class/Interface/Enum"""
    if not member_ids:
        return []
    ids_int = [int(x) for x in member_ids if str(x).isdigit()]
    query = """
    MATCH (m) WHERE m.nodeId IN $ids AND (m:Method OR m:Field)
    MATCH (parent)-[:DECLARES]->(m)
    WHERE parent:Class OR parent:Interface OR parent:Enum OR parent:Record
    RETURN DISTINCT parent.nodeId AS nodeId, labels(parent) AS labels, parent.name AS name
    """
    return await neo4j.execute_query(query, {"ids": ids_int})


async def expand_to_class_entities(neo4j, buckets: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """把所有容器节点（File/Package/Directory/Block）向下展开为 Class/Interface/Enum/...

    Method/Field 向上追到 declaring Class。

    返回：{"class_ids": [...], "interface_ids": [...], "enum_ids": [...],
           "record_ids": [...], "annotation_ids": [...],
           "expansion_stats": {...}}
    """
    import asyncio

    # 5 路并发展开
    files_rows, pkgs_rows, dirs_rows, blocks_rows, members_rows = await asyncio.gather(
        _expand_files_to_classes(neo4j, buckets.get("file_ids", [])),
        _expand_packages_to_classes(neo4j, buckets.get("package_ids", [])),
        _expand_directories_to_classes(neo4j, buckets.get("directory_ids", [])),
        _expand_blocks_to_classes(neo4j, buckets.get("block_ids", [])),
        _promote_members_to_classes(neo4j, buckets.get("method_ids", []) + buckets.get("field_ids", [])),
    )

    # 合并 + 按 label 分桶
    expanded = {
        "class_ids": set(buckets.get("class_ids", [])),
        "interface_ids": set(buckets.get("interface_ids", [])),
        "enum_ids": set(buckets.get("enum_ids", [])),
        "record_ids": set(buckets.get("record_ids", [])),
        "annotation_ids": set(buckets.get("annotation_ids", [])),
    }

    def _absorb(rows):
        for r in rows:
            labels = r.get("labels") or []
            nid = str(r["nodeId"])
            if "Class" in labels:
                expanded["class_ids"].add(nid)
            elif "Interface" in labels:
                expanded["interface_ids"].add(nid)
            elif "Enum" in labels:
                expanded["enum_ids"].add(nid)
            elif "Record" in labels:
                expanded["record_ids"].add(nid)
            elif "Annotation" in labels:
                expanded["annotation_ids"].add(nid)

    for rows in (files_rows, pkgs_rows, dirs_rows, blocks_rows, members_rows):
        _absorb(rows)

    stats = {
        "from_file": len(files_rows),
        "from_package": len(pkgs_rows),
        "from_directory": len(dirs_rows),
        "from_block": len(blocks_rows),
        "from_member": len(members_rows),
    }

    return {
        "class_ids": sorted(expanded["class_ids"]),
        "interface_ids": sorted(expanded["interface_ids"]),
        "enum_ids": sorted(expanded["enum_ids"]),
        "record_ids": sorted(expanded["record_ids"]),
        "annotation_ids": sorted(expanded["annotation_ids"]),
        "expansion_stats": stats,
    }


async def build_scope_for_category(
    new_wiki_index: dict,
    category_path: str,
    wiki_root: str,
    neo4j,
) -> Dict:
    """
    为某个分类聚合 in_scope_nodeids 并按 label 分桶。

    处理流程:
        1. 从每个 page 的 wiki JSON 收集 nodeId (source_id + 树内 neo4j_id)
        2. partition_by_label 按节点类型分桶
        3. 对容器节点 (File/Package/Directory/Block) 向下展开到 Class/Interface/Enum
        4. 对 Method/Field 向上追到 declaring Class

    Returns:
        {
            "category_path": str,
            "description": str,
            "pages": [原始 page dicts],
            "all_ids": [str, ...],  # 原始收集的全部 nodeId（按 label 未分类前）

            # 按 label 分桶（原始）
            "class_ids": [...],      # 展开合并后的完整 Class 集合（包含展开而来的）
            "interface_ids": [...],
            "enum_ids": [...],
            "record_ids": [...],
            "annotation_ids": [...],

            # 原始从页面收集到的成员和容器节点（未展开）
            "method_ids": [...],
            "field_ids": [...],
            "file_ids": [...],
            "package_ids": [...],
            "directory_ids": [...],
            "block_ids": [...],
            "other_ids": [...],

            "expansion_stats": {...},  # 展开统计
        }
    """
    cat = find_category(new_wiki_index, category_path)
    pages = cat.get("pages", [])

    all_ids: Set[str] = set()
    for p in pages:
        rel_path = p.get("path")
        if not rel_path:
            continue
        full = os.path.join(wiki_root, rel_path)
        ids = collect_node_ids_from_wiki_file(full)
        all_ids.update(ids)

    # Step 1: 分桶
    buckets = await partition_by_label(neo4j, list(all_ids))

    # Step 2: 容器节点向下展开 + 成员节点向上追
    expanded = await expand_to_class_entities(neo4j, buckets)

    before = len(buckets.get("class_ids", [])) + len(buckets.get("interface_ids", [])) + len(buckets.get("enum_ids", []))
    after = len(expanded["class_ids"]) + len(expanded["interface_ids"]) + len(expanded["enum_ids"])

    logger.info(
        f"[scope] {category_path}: {len(pages)} pages, {len(all_ids)} nodeIds, "
        f"raw bucket = (Class={len(buckets['class_ids'])}, Interface={len(buckets['interface_ids'])}, "
        f"Enum={len(buckets['enum_ids'])}, Method={len(buckets['method_ids'])}, Field={len(buckets['field_ids'])}, "
        f"File={len(buckets['file_ids'])}, Package={len(buckets['package_ids'])}, "
        f"Dir={len(buckets['directory_ids'])}, Block={len(buckets['block_ids'])}), "
        f"expanded Class/Interface/Enum: {before} -> {after}, stats={expanded['expansion_stats']}"
    )

    scope = {
        "category_path": category_path,
        "description": cat.get("description", ""),
        "pages": pages,
        "all_ids": sorted(all_ids),
        # 展开后的 Class/Interface/Enum/Record/Annotation（这些送给 §1/§2 用）
        "class_ids": expanded["class_ids"],
        "interface_ids": expanded["interface_ids"],
        "enum_ids": expanded["enum_ids"],
        "record_ids": expanded["record_ids"],
        "annotation_ids": expanded["annotation_ids"],
        # 原始捕获的成员/容器节点（留作参考，§2 的 Controller 仍从 class_ids 查起）
        "method_ids": buckets.get("method_ids", []),
        "field_ids": buckets.get("field_ids", []),
        "file_ids": buckets.get("file_ids", []),
        "package_ids": buckets.get("package_ids", []),
        "directory_ids": buckets.get("directory_ids", []),
        "block_ids": buckets.get("block_ids", []),
        "other_ids": buckets.get("other_ids", []),
        "expansion_stats": expanded["expansion_stats"],
    }
    return scope
