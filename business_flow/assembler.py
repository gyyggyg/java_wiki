"""把 SectionNode 章节树扁平化为目标 .meta.json 格式:

{
  "wiki": [
    {"markdown": "...", "neo4j_id": {"1": [...]}},
    {"mermaid": "...", "mapping": {...}},
    ...
  ],
  "source_id_list": [
    {"source_id": "<nodeId>", "name": "<file_path>", "lines": []},
    ...
  ]
}

扁平化规则（按章节逐一应用）:
- 一个章节的 SectionNode.title 放在该章节第一个 entry 的 markdown 开头
- 章节级 neo4j_id 放在第一个 text entry 的 neo4j_id 里
- 遇到 ChartNode **一定独立成为一个 mermaid entry**:
  - 先 flush 前面累积的 text（包含章节标题和 intro）为 markdown entry
  - chart 的 `mermaid` 字段值严格等于 "```mermaid\\n<src>\\n```"（只有围栏包裹的图源码，不含标题/文字）
- 连续的 TextNode 之间用换行连接为一个 markdown entry
- ChartNode 之后的 text 开始新的 markdown entry
"""

import logging
from typing import Any, Dict, List, Tuple

from business_flow.schema import SectionNode, TextNode, ChartNode
from business_flow.neo4j_fetch import resolve_source_files

logger = logging.getLogger("business_flow.assembler")


def _collect_entry_node_ids(entry: Dict[str, Any]) -> List[str]:
    """从一个 wiki entry 里抽取所有 nodeId 字符串（遍历 neo4j_id/mapping）"""
    ids: List[str] = []

    def _walk(v):
        if isinstance(v, list):
            for x in v:
                _walk(x)
        elif isinstance(v, dict):
            for x in v.values():
                _walk(x)
        elif v is not None:
            ids.append(str(v))

    if "neo4j_id" in entry:
        _walk(entry["neo4j_id"])
    if "mapping" in entry:
        _walk(entry["mapping"])
    return ids


def _section_to_wiki_entries(section: SectionNode) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """把一个 SectionNode 扁平化为若干 wiki entries + 收集 chart 的 source_id 条目。

    返回 (wiki_entries, prebuilt_source_id_entries)。
    """
    title = section.title or ""
    section_neo4j_id = dict(section.neo4j_id or {})
    content = section.content or []

    entries: List[Dict[str, Any]] = []
    prebuilt_sid_entries: List[Dict[str, Any]] = []
    pending_text_parts: List[str] = [title] if title else []
    pending_neo4j_id: Dict[str, Any] = {}
    is_first_entry = True

    def flush_text():
        """把累积的 pending_text_parts 合并为一个 markdown entry"""
        nonlocal pending_text_parts, pending_neo4j_id, is_first_entry
        md = "\n\n".join(p for p in pending_text_parts if p and p.strip()).strip()
        if not md:
            pending_text_parts = []
            pending_neo4j_id = {}
            return
        nid = dict(pending_neo4j_id)
        if is_first_entry:
            # 首个 entry 合并章节级 neo4j_id
            for k, v in section_neo4j_id.items():
                if k not in nid:
                    nid[k] = v
            is_first_entry = False
        entries.append({"markdown": md, "neo4j_id": nid})
        pending_text_parts = []
        pending_neo4j_id = {}

    for node in content:
        if isinstance(node, TextNode):
            md = (node.content.get("markdown") or "").strip()
            if md:
                pending_text_parts.append(md)
            for k, v in (node.neo4j_id or {}).items():
                pending_neo4j_id[k] = v
        elif isinstance(node, ChartNode):
            mermaid_src = (node.content.get("mermaid") or "").strip()
            mapping = node.content.get("mapping") or {}
            # chart 总是独立成 entry；先把之前累积的 text flush
            if pending_text_parts:
                flush_text()
            entries.append({
                "mermaid": f"```mermaid\n{mermaid_src}\n```",
                "mapping": dict(mapping),
            })
            # 收集 chart 自带的 source_id 条目（带行号），assemble 时直接注入 source_id_list
            for sid_item in (node.source_id or []):
                if isinstance(sid_item, dict) and sid_item.get("source_id"):
                    prebuilt_sid_entries.append(dict(sid_item))
            is_first_entry = False
        else:
            # 不认识的节点类型，跳过
            logger.warning(f"未知节点类型，跳过: {type(node).__name__}")

    # 末尾剩余 text
    if pending_text_parts:
        flush_text()

    return entries, prebuilt_sid_entries


async def assemble_wiki(flow: Dict, section_nodes: List[SectionNode], neo4j) -> dict:
    """把所有 SectionNode 扁平化为目标 .meta.json 格式。

    source_id_list 的组装规则：
    - ChartNode 预计算的 source_id 条目（含具体行号）优先直接进 list；
    - 其余 nodeId（一般来自 markdown 的 neo4j_id，指 Class/Method 节点）仍通过 Neo4j
      解析出文件路径，lines 为空表示"整类/整方法"。
    - 两者按 source_id 去重；已预建的 source_id 不再做 Neo4j 兜底查询。
    """
    # 1. 扁平化所有章节 + 收集预建 source_id 条目
    wiki: List[Dict[str, Any]] = []
    prebuilt_entries: List[Dict[str, Any]] = []
    for section in section_nodes:
        entries, sids = _section_to_wiki_entries(section)
        wiki.extend(entries)
        prebuilt_entries.extend(sids)

    # 按 source_id 去重（同一 source_id 出现多次时保留 lines 非空的那条）
    prebuilt_by_sid: Dict[str, Dict[str, Any]] = {}
    for e in prebuilt_entries:
        sid = str(e.get("source_id") or "")
        if not sid:
            continue
        if sid not in prebuilt_by_sid or (not prebuilt_by_sid[sid].get("lines") and e.get("lines")):
            prebuilt_by_sid[sid] = {
                "source_id": sid,
                "name": e.get("name") or "",
                "lines": list(e.get("lines") or []),
            }
    prebuilt_sid_set = set(prebuilt_by_sid.keys())

    # 2. 收集所有 entry 里的 nodeId；已在 prebuilt 中的跳过 Neo4j 解析
    all_ids: List[str] = []
    for entry in wiki:
        all_ids.extend(_collect_entry_node_ids(entry))
    neo4j_ids = sorted({nid for nid in all_ids if nid and nid not in prebuilt_sid_set})

    logger.info(
        f"[assemble] {flow.get('name')}: {len(wiki)} 个 wiki entries, "
        f"{len(prebuilt_by_sid)} 条预建 source_id（chart 行号映射）, "
        f"{len(neo4j_ids)} 个待 Neo4j 解析的 nodeId"
    )

    file_info_map = await resolve_source_files(neo4j, neo4j_ids) if neo4j_ids else {}

    # 3. 合并 source_id_list
    source_id_list: List[Dict[str, Any]] = list(prebuilt_by_sid.values())
    seen: set = set(prebuilt_sid_set)
    for nid in neo4j_ids:
        if nid in seen:
            continue
        info = file_info_map.get(nid)
        if not info or not info.get("file_name"):
            continue
        seen.add(nid)
        source_id_list.append({
            "source_id": nid,
            "name": info["file_name"],
            "lines": [],  # markdown 里的类/方法引用不到具体行号
        })

    return {
        "wiki": wiki,
        "source_id_list": source_id_list,
    }
