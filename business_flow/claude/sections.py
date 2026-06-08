"""6 个章节构建器 —— Claude CLI 版

§1 业务概述 / §2 对外接口清单 / §3 关键协作时序图
§4 涉及的核心实体与数据结构 / §5 核心业务流程图 / §6 组件索引
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from business_flow.claude.schema import SectionNode, TextNode, ChartNode
from business_flow.claude.neo4j_fetch import (
    fetch_class_briefs,
    fetch_classes_with_fields,
    search_classes_by_names,
)
from business_flow.claude.claude_client import invoke_claude_strict, invoke_claude_markdown
from business_flow.claude.mermaid_validator import invoke_claude_with_mermaid_check
from business_flow.claude.prompts import (
    OVERVIEW_SYSTEM, build_overview_user_prompt,
    ENTRYPOINTS_SYSTEM, build_entrypoints_user_prompt,
    SEQUENCE_SYSTEM, build_sequence_user_prompt,
    DATA_MODEL_SYSTEM, build_data_model_user_prompt, build_data_model_retry_user_prompt,
    CONTROL_FLOW_PLAN_SYSTEM, build_control_flow_plan_user_prompt,
    DIAGRAM_DESCRIPTION_SYSTEM, build_diagram_description_user_prompt,
    SOURCE_ID_SYSTEM, build_source_id_user_prompt,
    CFG_SYSTEM, build_cfg_user_prompt,
    CFG_ID_VALIDATE_SYSTEM, build_cfg_id_validate_user_prompt,
    STATE_MACHINE_SYSTEM, build_state_machine_user_prompt,
)
from business_flow.claude.branch_analyzer import analyze_entry_methods, format_branch_hint
from business_flow.claude.state_field_detector import (
    detect_state_field_candidates, format_candidates_for_prompt,
)
from business_flow.claude.class_context import build_class_context_text
from business_flow.claude.line_mapping import (
    generate_source_id, find_class_or_method_range, tag_code_lines,
    apply_offset_to_lines, fetch_method_source, fetch_file_source_for_classes,
    normalize_mapping_value,
)
import json as _json

logger = logging.getLogger("business_flow.claude.sections")


def _dedup(seq: List[str]) -> List[str]:
    seen, out = set(), []
    for s in seq:
        s = str(s) if s is not None else ""
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


_BACKTICK_RE = __import__("re").compile(r"`([^`\n]+)`")


def _collect_referenced_ids(
    markdown: str,
    class_rows: Optional[List[Dict]] = None,
    entry_methods: Optional[List[Dict]] = None,
) -> Dict[str, List[str]]:
    """从 markdown 里抽出被反引号包裹的类/方法引用，映射到 neo4j nodeId。

    识别：
    - `ClassName`          → class_ids
    - `ClassName.method`   / `ClassName.method()`  → method_ids（含重载）
    - 含包路径形如 `a.b.ClassName` → 取最后一段匹配类索引
    - 单个 `method()` 无类前缀 → 不处理（歧义）

    类索引自动兼容 class_id / nodeId / class_name / name 两套键名。
    """
    if not markdown:
        return {"classes": [], "methods": []}

    # 类名 → class_id 索引
    class_index: Dict[str, str] = {}
    for r in (class_rows or []):
        name = (r.get("name") or r.get("class_name") or "").strip()
        cid = r.get("class_id") or r.get("nodeId")
        if name and cid is not None:
            class_index[name] = str(cid)

    # (class, method) → [node_id,...] 索引（含重载）
    from collections import defaultdict
    method_index: Dict[tuple, List[str]] = defaultdict(list)
    for e in (entry_methods or []):
        cls = (e.get("class") or "").strip()
        mth = (e.get("method") or "").strip()
        nid = e.get("node_id")
        if cls and mth and nid is not None:
            method_index[(cls, mth)].append(str(nid))

    class_hits: set = set()
    method_hits: set = set()

    for raw in _BACKTICK_RE.findall(markdown):
        token = raw.strip().rstrip("()")
        if not token:
            continue
        if "." in token:
            cls_part, _, tail = token.rpartition(".")
            cls_part = cls_part.strip()
            tail = tail.strip()
            key = (cls_part, tail)
            if key in method_index:
                method_hits.update(method_index[key])
                if cls_part in class_index:
                    class_hits.add(class_index[cls_part])
                continue
            # 不是方法：可能是带包路径的类或嵌套类
            if token in class_index:
                class_hits.add(class_index[token])
            elif tail in class_index:
                class_hits.add(class_index[tail])
        else:
            if token in class_index:
                class_hits.add(class_index[token])

    return {
        "classes": sorted(class_hits),
        "methods": sorted(method_hits),
    }


# ===========================================================
# 辅助格式化
# ===========================================================

def _format_entry_methods_list(entry_methods: List[Dict]) -> str:
    if not entry_methods:
        return "(无)"
    lines = []
    for e in entry_methods:
        lines.append(f"- {e.get('class','?')}.{e.get('method','?')}  (method_id={e.get('node_id','?')})")
    return "\n".join(lines)


def _format_entry_methods_detail(entry_methods: List[Dict], all_class_rows: List[Dict]) -> str:
    cls_index = {r.get("name"): r for r in all_class_rows}
    lines = []
    for e in entry_methods:
        cls = e.get("class", "?")
        method = e.get("method", "?")
        nid = e.get("node_id", "?")
        cls_row = cls_index.get(cls) or {}
        cls_id = cls_row.get("class_id", "?")
        se = (cls_row.get("se_what") or "").replace("\n", " ")[:100]
        lines.append(f"- class={cls} (class_id={cls_id})  method={method}  method_id={nid}  class_SE_What={se}")
    return "\n".join(lines)


def _format_class_briefs(rows: List[Dict], limit: int = 30) -> str:
    if not rows:
        return "(该业务流下未找到带有语义解释的类)"
    lines = []
    for r in rows[:limit]:
        name = r.get("name") or "?"
        what = (r.get("se_what") or "").replace("\n", " ")[:200]
        why = (r.get("se_why") or "").replace("\n", " ")[:150]
        lines.append(f"- **{name}**\n    - What: {what}\n    - Why: {why}")
    if len(rows) > limit:
        lines.append(f"- ...（另外 {len(rows) - limit} 个类省略）")
    return "\n".join(lines)


# ===========================================================
# §1 业务概述
# ===========================================================

async def build_overview_section(flow: Dict, scope: Dict, neo4j) -> SectionNode:
    logger.info(f"[s1] 生成概述: {flow['name']}")
    core_class_ids = scope.get("class_ids", []) + scope.get("interface_ids", []) \
                     + scope.get("enum_ids", []) + scope.get("record_ids", [])
    briefs = await fetch_class_briefs(neo4j, core_class_ids)

    user = build_overview_user_prompt(
        flow_name=flow["name"],
        flow_kind=flow.get("kind", "?"),
        flow_description=flow.get("description", ""),
        entry_methods=_format_entry_methods_list(flow.get("entry_methods", [])),
        class_briefs=_format_class_briefs(briefs),
    )
    md, _ = await invoke_claude_markdown(
        system_prompt=OVERVIEW_SYSTEM,
        user_prompt=user,
        label=f"s1-{flow['name']}",
    )
    refs = _collect_referenced_ids(md, class_rows=briefs,
                                    entry_methods=flow.get("entry_methods"))
    merged = _dedup(refs["classes"] + refs["methods"])
    if merged:
        nid = {"1": merged}
    else:
        logger.warning(f"[s1] {flow['name']} 概述未匹配到任何类/方法引用，退回全量 scope")
        nid = {"1": _dedup(core_class_ids)}
    logger.info(
        f"[s1] {flow['name']} 概述引用提取: "
        f"{len(refs['classes'])} 个类 / {len(refs['methods'])} 个方法"
    )
    text = TextNode(content={"markdown": md}, neo4j_id=nid)
    return SectionNode(
        title="## 1. 业务概述",
        content=[text],
        neo4j_id={},
    )


# ===========================================================
# §2 触发入口
# ===========================================================

async def build_entrypoints_section(flow: Dict, scope: Dict,
                                    class_context_text: str,
                                    all_class_rows: List[Dict]) -> SectionNode:
    logger.info(f"[s2] 生成触发入口: {flow['name']}")
    entries = flow.get("entry_methods", [])
    if not entries:
        text = TextNode(content={"markdown": "_该业务流未定义入口方法。_"})
        return SectionNode(title="## 2. 触发入口", content=[text], neo4j_id={})

    user = build_entrypoints_user_prompt(
        flow_name=flow["name"],
        flow_kind=flow.get("kind", "?"),
        entry_methods_detail=_format_entry_methods_detail(entries, all_class_rows),
        class_contexts=class_context_text,
    )
    md, _ = await invoke_claude_markdown(
        system_prompt=ENTRYPOINTS_SYSTEM,
        user_prompt=user,
        label=f"s2-{flow['name']}",
    )

    refs = _collect_referenced_ids(md, class_rows=all_class_rows, entry_methods=entries)
    merged = _dedup(refs["classes"] + refs["methods"])
    if merged:
        nid = {"3": merged}
    else:
        # 兜底：LLM 偶尔漏写某接口时，用全量 entries 补齐
        entry_method_ids = _dedup([str(e.get("node_id", "")) for e in entries])
        entry_class_names = {e.get("class") for e in entries}
        entry_class_ids = _dedup([
            str(r["class_id"]) for r in all_class_rows
            if r.get("name") in entry_class_names and r.get("class_id") is not None
        ])
        logger.warning(f"[s2] {flow['name']} 接口清单未匹配到任何引用，退回全量 entries")
        nid = {"3": _dedup(entry_method_ids + entry_class_ids)}
    logger.info(
        f"[s2] {flow['name']} 接口清单引用提取: "
        f"{len(refs['classes'])} 个类 / {len(refs['methods'])} 个方法（输入 {len(entries)} 个入口）"
    )

    text = TextNode(content={"markdown": md}, neo4j_id=nid)
    return SectionNode(
        title="## 3. 对外接口清单",
        content=[text],
        neo4j_id={},
    )


# ===========================================================
# §3 端到端时序图
# ===========================================================

_DESC_HEADING_RE = __import__("re").compile(r"^(#{1,3})(\s+\S)", flags=__import__("re").MULTILINE)


def _demote_top_headings(md: str) -> str:
    """把 description 里 LLM 偷偷出的 # / ## / ### 统一降级为 ####，避免破坏外层章节层级。"""
    if not md:
        return md
    return _DESC_HEADING_RE.sub(lambda m: "####" + m.group(2), md)


async def _generate_diagram_description(
    chart_kind: str,
    resume_session_id: Optional[str],
    label: str,
) -> str:
    """图定稿后，用 --resume 复用绘图 session，生成一段详细说明。

    resume_session_id 缺失时返回空串（不会阻断主流程）。
    返回的 markdown 会统一降级其中任何 H1~H3 标题，防止越级污染外层目录。
    """
    if not resume_session_id:
        logger.warning(f"[{label}] 无 session_id，跳过 description 生成")
        return ""
    try:
        md, _ = await invoke_claude_markdown(
            system_prompt=DIAGRAM_DESCRIPTION_SYSTEM,
            user_prompt=build_diagram_description_user_prompt(chart_kind),
            label=label,
            resume_session_id=resume_session_id,
        )
    except Exception as e:
        logger.warning(f"[{label}] description 生成失败: {type(e).__name__}: {e}")
        return ""
    return _demote_top_headings(md)


async def _add_class_line_mapping(
    clean_mapping: Dict[str, str],
    neo4j,
) -> tuple:
    """把 {NodeID: class_id} 映射转换为 {NodeID: source_id}，并产出 source_id_list 条目。

    对 clean_mapping 里出现的每个 class_id：
    - 从 Neo4j 拉该类所在文件的源码 + 类源码
    - 用 find_class_or_method_range 算出类声明在文件中的行范围
    - 生成一个 8 位 source_id 指向该行范围
    - source_id_list 条目 dedupe 按 class_id（同一类多节点共用一个 source_id）

    返回 (new_mapping {NodeID: source_id}, source_id_entries [{source_id, name, lines}])
    """
    if not clean_mapping:
        return clean_mapping, []

    class_ids = list({str(v) for v in clean_mapping.values() if v})
    info_map = await fetch_file_source_for_classes(neo4j, class_ids)

    class_id_to_sid: Dict[str, Dict[str, Any]] = {}
    for cid in class_ids:
        info = info_map.get(cid)
        if not info:
            logger.warning(f"[line_mapping] class_id={cid} 未查到文件信息")
            continue
        class_name = info.get("class_name") or ""
        class_source = info.get("class_source") or ""
        file_source = info.get("file_source") or ""
        file_name = info.get("file_name") or ""
        if not file_source or not class_name:
            logger.warning(
                f"[line_mapping] class_id={cid} 缺文件源码或类名 "
                f"(file_source={bool(file_source)}, class_name={bool(class_name)})"
            )
            continue
        line_ranges = find_class_or_method_range(file_source, class_source, class_name)
        if not line_ranges:
            logger.warning(f"[line_mapping] class_id={cid} name={class_name} 定位行号失败")
            continue
        sid = generate_source_id()
        class_id_to_sid[cid] = {
            "source_id": sid,
            "name": file_name,
            "lines": line_ranges,
        }

    new_mapping: Dict[str, str] = {}
    seen_sids: set = set()
    entries: List[Dict[str, Any]] = []
    for node, cid in clean_mapping.items():
        entry = class_id_to_sid.get(str(cid))
        if not entry:
            continue  # 没拿到行号的节点：直接从 mapping 里移除
        new_mapping[node] = entry["source_id"]
        if entry["source_id"] not in seen_sids:
            seen_sids.add(entry["source_id"])
            entries.append(entry)
    return new_mapping, entries


def _sanitize_mapping(mapping: Any, valid_class_ids: set) -> Dict[str, str]:
    if not isinstance(mapping, dict):
        return {}
    clean = {}
    for k, v in mapping.items():
        if not k or not v:
            continue
        if isinstance(v, list):
            v = v[0] if v else ""
        s = str(v)
        if s in valid_class_ids:
            clean[str(k)] = s
        else:
            logger.warning(f"[s3] mapping '{k}' 对应 class_id '{s}' 不在 scope，剔除")
    return clean


async def build_sequence_section(flow: Dict, scope: Dict,
                                 class_context_text: str,
                                 all_class_rows: List[Dict],
                                 neo4j=None) -> SectionNode:
    logger.info(f"[s3] 生成时序图: {flow['name']}")
    entries = flow.get("entry_methods", [])
    if not entries or not all_class_rows:
        text = TextNode(content={"markdown": "_缺少入口方法或类源码，无法生成时序图。_"})
        return SectionNode(title="## 3. 端到端时序图", content=[text], neo4j_id={})

    user = build_sequence_user_prompt(
        flow_name=flow["name"],
        flow_kind=flow.get("kind", "?"),
        entry_methods_detail=_format_entry_methods_detail(entries, all_class_rows),
        class_contexts=class_context_text,
    )
    result, sid = await invoke_claude_with_mermaid_check(
        system_prompt=SEQUENCE_SYSTEM,
        user_prompt=user,
        required_keys=["mermaid", "mapping"],
        label=f"s3-{flow['name']}",
    )

    mermaid_text = (result.get("mermaid") or "").strip()
    valid_class_ids = {str(r["class_id"]) for r in all_class_rows if r.get("class_id") is not None}
    clean_mapping = _sanitize_mapping(result.get("mapping"), valid_class_ids)

    # 把 class_id 映射替换成 source_id，生成 source_id_list 条目
    source_entries: List[Dict[str, Any]] = []
    if neo4j is not None and clean_mapping:
        new_mapping, source_entries = await _add_class_line_mapping(clean_mapping, neo4j)
        logger.info(
            f"[s3] {flow['name']} 时序图行号映射: "
            f"{len(clean_mapping)} 个节点 → {len(new_mapping)} 个定位成功, "
            f"{len(source_entries)} 条 source_id"
        )
        clean_mapping = new_mapping

    chart = ChartNode(
        content={"mermaid": mermaid_text, "mapping": clean_mapping},
        neo4j_id=dict(clean_mapping),
        source_id=source_entries,
    )
    intro = TextNode(
        content={"markdown": f"下图展示 **{flow['name']}** 的关键协作路径。"}
    )
    section_content: List[Any] = [intro, chart]

    # 图定稿后 --resume 生成详细说明
    description = await _generate_diagram_description(
        chart_kind="sequence",
        resume_session_id=sid,
        label=f"s3-{flow['name']}-desc",
    )
    if description:
        desc_refs = _collect_referenced_ids(
            description, class_rows=all_class_rows, entry_methods=flow.get("entry_methods"),
        )
        merged = _dedup(desc_refs["classes"] + desc_refs["methods"])
        section_content.append(TextNode(
            content={"markdown": "### 时序说明\n\n" + description},
            neo4j_id={"4": merged} if merged else {},
        ))

    return SectionNode(
        title="## 4. 关键协作时序图",
        content=section_content,
        neo4j_id={"4": list(clean_mapping.values())},
    )


# ===========================================================
# §4 涉及的核心实体与数据结构
# ===========================================================

def _format_classes_with_fields(rows: List[Dict], max_fields_per_class: int = 20) -> str:
    """把 fetch_classes_with_fields 的结果格式化为 prompt 可读文本"""
    if not rows:
        return "(该业务流下没有带字段的数据类)"
    lines = []
    for r in rows:
        class_name = r.get("class_name") or "?"
        class_id = r.get("class_id") or "?"
        mods = (r.get("modifiers") or "").replace("\n", " ")[:120]
        se = (r.get("se_what") or "").replace("\n", " ")[:150]
        file_name = r.get("file_name") or "-"
        fields = r.get("fields") or []
        lines.append(f"### {class_name} (class_id={class_id})")
        lines.append(f"- file: `{file_name}`")
        if mods:
            lines.append(f"- 类注解: {mods}")
        if se:
            lines.append(f"- SE_What: {se}")
        lines.append(f"- 字段（{len(fields)} 个）:")
        for fld in fields[:max_fields_per_class]:
            fname = fld.get("field_name") or "?"
            ftype = fld.get("field_type") or "?"
            fmods = (fld.get("field_modifiers") or "").replace("\n", " ")[:100]
            target_name = fld.get("target_class_name") or ""
            target_id = fld.get("target_class_id")
            ref_info = f" → {target_name}(class_id={target_id})" if target_name else ""
            anno_hint = ""
            if fmods:
                # 只保留前缀的 @注解
                import re as _re
                anns = _re.findall(r"@\w+(?:\([^)]*\))?", fmods)
                if anns:
                    anno_hint = " " + " ".join(anns[:3])
            lines.append(f"    - {ftype} {fname}{anno_hint}{ref_info}")
        if len(fields) > max_fields_per_class:
            lines.append(f"    - ...（另外 {len(fields) - max_fields_per_class} 个字段省略）")
        lines.append("")
    return "\n".join(lines)


def _extract_external_names(result: Dict) -> List[str]:
    """从 data_model 的 LLM 返回值中提取需要回查 Neo4j 的类名。

    - status=missing_data：从 missing_classes 取
    - status=complete：从 external_refs 取（被引用但不在 scope 的类）
    """
    status = str(result.get("status") or "complete").strip().lower()
    key = "missing_classes" if status == "missing_data" else "external_refs"
    items = result.get(key) or []
    return _dedup([
        str(m.get("suspected_name") or "").strip()
        for m in items if isinstance(m, dict) and m.get("suspected_name")
    ])



def _format_missing_data_markdown(flow_name: str, missing_classes: List[Dict], notes: str) -> str:
    """将 Claude 返回的 missing_data 组装为告警 markdown"""
    lines: List[str] = []
    if notes:
        lines.append(notes)
        lines.append("")
    lines.append("> ⚠️ **数据不足**：当前 scope 缺少绘制 ER 图所需的关键实体，已跳过本章节的图表生成。")
    lines.append("")
    if missing_classes:
        lines.append("**需要补充的类**：")
        lines.append("")
        lines.append("| 疑似类名 | 推断依据 |")
        lines.append("|---|---|")
        for m in missing_classes:
            name = str(m.get("suspected_name") or "?").strip()
            ev = str(m.get("evidence") or "").strip().replace("\n", " ")
            lines.append(f"| `{name}` | {ev} |")
        lines.append("")
    lines.append(f"补齐上述类后，可重新生成 **{flow_name}** 的数据结构章节。")
    return "\n".join(lines)


async def build_data_model_section(flow: Dict, scope: Dict, neo4j) -> SectionNode:
    """§2. 数据结构以及架构概览

    Claude 返回两种 status：
    - complete     → 正常输出 ER 图 + 简短文字说明
    - missing_data → 跳过图表生成，输出缺失类清单告警
    """
    logger.info(f"[s2-datamodel] 生成数据结构与架构概览: {flow['name']}")

    # 只查 Class 类型，DTO/Entity 都是 Class；Interface/Enum 无字段不处理
    class_ids = scope.get("class_ids", [])
    rows = await fetch_classes_with_fields(neo4j, class_ids, min_fields=2, max_classes=30)
    logger.info(f"[s2-datamodel] {flow['name']} 有字段的类 {len(rows)} 个")

    if not rows:
        text = TextNode(content={"markdown": "_该业务流下未发现带字段的数据类。_"})
        return SectionNode(
            title="## 2. 数据结构以及架构概览",
            content=[text],
            neo4j_id={},
        )

    user = build_data_model_user_prompt(
        flow_name=flow["name"],
        flow_kind=flow.get("kind", "?"),
        classes_with_fields=_format_classes_with_fields(rows),
    )
    # 只要求 status 字段；后续按 status / external_refs 分支校验
    result, sid = await invoke_claude_with_mermaid_check(
        system_prompt=DATA_MODEL_SYSTEM,
        user_prompt=user,
        required_keys=["status"],
        label=f"s2-datamodel-{flow['name']}",
    )

    # ====== 按需回查 Neo4j 补类并 --resume 重试一次 ======
    # 触发条件：status=missing_data（核心实体缺失），或 status=complete 但 external_refs 非空
    external_names = _extract_external_names(result)
    if external_names:
        logger.info(
            f"[s2-datamodel] {flow['name']} 首轮存在未覆盖实体 {len(external_names)} 个: {external_names}"
        )
        extra_rows = await search_classes_by_names(neo4j, external_names)
        found_names = [r.get("name") for r in extra_rows]
        found_ids = _dedup([str(r.get("class_id")) for r in extra_rows if r.get("class_id") is not None])
        not_found = [n for n in external_names if n not in found_names]
        logger.info(
            f"[s2-datamodel] {flow['name']} 回查命中 {len(found_ids)} 个 "
            f"(已找到: {found_names}; 未找到: {not_found})"
        )

        if found_ids:
            # 只为补查到的新类查字段（不重新查原 scope；Claude 已在 session 里见过）
            new_field_rows = await fetch_classes_with_fields(
                neo4j, found_ids, min_fields=1, max_classes=40,
            )
            logger.info(
                f"[s2-datamodel] {flow['name']} 补查到 {len(new_field_rows)} 个新类带字段 "
                f"(resume sid={'yes' if sid else 'no'})"
            )

            # 精简的 retry prompt：只包含新补查到的类字段
            user2 = build_data_model_retry_user_prompt(
                additional_classes_with_fields=_format_classes_with_fields(new_field_rows),
            )
            result2, sid2 = await invoke_claude_with_mermaid_check(
                system_prompt=DATA_MODEL_SYSTEM,
                user_prompt=user2,
                required_keys=["status"],
                label=f"s2-datamodel-retry-{flow['name']}",
                resume_session_id=sid,
            )
            # 不管第二轮是 complete 还是 missing_data，都以它为最终结果
            result = result2
            sid = sid2  # 重试的 session_id 才是"最终图"的来源
            # 把新类合进 rows 供后续 mapping 校验和实体说明使用
            existing_cids = {str(r.get("class_id")) for r in rows}
            rows = list(rows) + [
                r for r in new_field_rows if str(r.get("class_id")) not in existing_cids
            ]
            logger.info(
                f"[s2-datamodel] {flow['name']} 重试完成，最终 status={result.get('status')}"
            )

    status = str(result.get("status") or "complete").strip().lower()

    # ====== 情况 B：数据不足（重试后依然不足 / 压根没回查到）======
    if status == "missing_data":
        missing_classes = result.get("missing_classes") or []
        notes = (result.get("notes") or "").strip()
        flow["_missing_classes"] = [
            {
                "suspected_name": str(m.get("suspected_name") or "").strip(),
                "evidence": str(m.get("evidence") or "").strip(),
            }
            for m in missing_classes
            if m.get("suspected_name")
        ]
        flow["_missing_data_notes"] = notes
        md = _format_missing_data_markdown(flow["name"], missing_classes, notes)
        return SectionNode(
            title="## 2. 数据结构以及架构概览",
            content=[TextNode(content={"markdown": md})],
            neo4j_id={},
        )

    # ====== 情况 A：数据充足 ======
    mermaid_text = (result.get("mermaid") or "").strip()
    valid_class_ids = {str(r["class_id"]) for r in rows if r.get("class_id") is not None}
    clean_mapping = _sanitize_mapping(result.get("mapping"), valid_class_ids)

    # 保留原始 {EntityName: class_id} 映射，用于章节 neo4j_id 返回
    # （clean_mapping 之后会被替换为 {EntityName: source_id}）
    class_id_mapping = dict(clean_mapping)

    # 替换为 source_id 映射并产出 source_id_list 条目
    source_entries: List[Dict[str, Any]] = []
    if clean_mapping:
        new_mapping, source_entries = await _add_class_line_mapping(clean_mapping, neo4j)
        logger.info(
            f"[s2-datamodel] {flow['name']} ER 图行号映射: "
            f"{len(clean_mapping)} 个实体 → {len(new_mapping)} 个定位成功, "
            f"{len(source_entries)} 条 source_id"
        )
        clean_mapping = new_mapping

    content: List[Any] = []
    if mermaid_text:
        chart = ChartNode(
            content={"mermaid": mermaid_text, "mapping": clean_mapping},
            neo4j_id=dict(clean_mapping),
            source_id=source_entries,
        )
        content.append(chart)

    # 图定稿后 --resume 生成详细说明
    if mermaid_text:
        description = await _generate_diagram_description(
            chart_kind="er",
            resume_session_id=sid,
            label=f"s2-datamodel-{flow['name']}-desc",
        )
        if description:
            desc_refs = _collect_referenced_ids(description, class_rows=rows)
            merged = _dedup(desc_refs["classes"] + desc_refs["methods"])
            content.append(TextNode(
                content={"markdown": "### 数据模型说明\n\n" + description},
                neo4j_id={"2": merged} if merged else {},
            ))

    if not content:
        content.append(TextNode(content={"markdown": "_ER 图生成失败。_"}))

    return SectionNode(
        title="## 2. 数据结构以及架构概览",
        content=content,
        neo4j_id={"2": list(class_id_mapping.values())} if class_id_mapping else {},
    )


# ===========================================================
# §5 核心业务流程图（控制流）
# ===========================================================

def _filter_rows_by_names(all_class_rows: List[Dict], names: List[str]) -> List[Dict]:
    """按类名白名单过滤 all_class_rows"""
    name_set = {n for n in (str(x).strip() for x in names or []) if n}
    if not name_set:
        return []
    return [r for r in all_class_rows if (r.get("name") or "") in name_set]


def _partition_skipped(skipped: List[Dict]) -> tuple:
    """按 kind 把 skipped 数组分成 (controllers, services)。
    未指定 kind 的按 controller 处理（向下兼容老数据）。
    """
    controllers: List[Dict] = []
    services: List[Dict] = []
    for s in skipped or []:
        if not isinstance(s, dict):
            continue
        kind = (s.get("kind") or "").strip().lower()
        if kind == "service":
            services.append(s)
        else:
            controllers.append(s)
    return controllers, services


def _format_skipped_controller_block(items: List[Dict]) -> str:
    """直通 Controller 接口：每项 3 行（标题 + 用途 + 实现）。"""
    if not items:
        return ""
    lines: List[str] = [
        "#### 直通查询接口",
        "",
        f"以下 {len(items)} 个接口为无分支逻辑的直接查询/转发，故不单独绘制控制流图；"
        "它们按输入参数直接调用对应数据访问层并返回结果。",
        "",
    ]
    for s in items:
        entry = s.get("entry", "?")
        purpose = (s.get("purpose") or "").strip()
        impl = (s.get("implementation") or "").strip()
        lines.append(f"- **`{entry}`**")
        if purpose:
            lines.append(f"    - 用途：{purpose}")
        if impl:
            lines.append(f"    - 实现：{impl}")
        if not purpose and not impl:
            fallback = (s.get("description") or s.get("reason") or "").strip()
            if fallback:
                lines.append(f"    - {fallback}")
    return "\n".join(lines)


def _format_skipped_service_block(items: List[Dict],
                                   planned_entry_to_idx: Dict[str, int]) -> str:
    """简单 Service：每项标注调用者（含 Controller 在 §5.X 的编号）。"""
    if not items:
        return ""
    lines: List[str] = [
        "#### 简单 Service 实现",
        "",
        f"以下 {len(items)} 个 Service 方法被前述控制流图里的 `[[...]]` 黑盒节点调用，"
        "本身实现薄（单行转发或少量字段赋值），不单独画 CFG，这里列出其用途与实现以便查阅。",
        "",
    ]
    for s in items:
        entry = s.get("entry", "?")
        purpose = (s.get("purpose") or "").strip()
        impl = (s.get("implementation") or "").strip()
        called_by = s.get("called_by") or []
        lines.append(f"- **`{entry}`**")
        if called_by:
            parts: List[str] = []
            for em in called_by:
                em_clean = str(em).strip()
                parent_idx = planned_entry_to_idx.get(em_clean)
                if parent_idx is not None:
                    parts.append(f"[5.{parent_idx}] `{em_clean}`")
                else:
                    parts.append(f"`{em_clean}`")
            lines.append(f"    - 被调用自：{'、'.join(parts)}")
        if purpose:
            lines.append(f"    - 用途：{purpose}")
        if impl:
            lines.append(f"    - 实现：{impl}")
    return "\n".join(lines)


async def _generate_single_control_flow(
    flow: Dict,
    cf_spec: Dict,
    all_class_rows: List[Dict],
    neo4j,
) -> Dict:
    """为单个控制流跑 3-stage line-mapping 管线：
       A. SOURCE_ID 划分   → 功能片段 → UUID source_id
       B. CFG 绘制         → mermaid + mapping: {NodeID → source_id}
       C. CFG_ID 校验      → mapping: {NodeID → 行号范围}（方法内相对行号）
    然后叠加 offset（方法在文件中的起始行-1）转为文件级行号。

    返回 {title, entry_method, mermaid, mapping, source_id_entries, err}。
    """
    title = str(cf_spec.get("title") or "").strip() or "(未命名子流程)"
    entry_method = str(cf_spec.get("entry_method") or "").strip()
    needed = cf_spec.get("needed_classes") or []
    filtered_rows = _filter_rows_by_names(all_class_rows, needed)
    if not filtered_rows:
        return {"title": title, "entry_method": entry_method,
                "mermaid": "", "mapping": {}, "source_id_entries": [],
                "err": f"needed_classes {needed} 在 all_class_rows 里都找不到"}

    # ---- 查方法源码 + 文件源码 ----
    # planner 偶尔会在 entry_method 末尾带上 (ParamType) 用于区分重载，抽出来作为 hint
    import re as _re
    _hint_m = _re.search(r"\(([^)]+)\)\s*$", entry_method)
    param_hint = _hint_m.group(1).strip() if _hint_m else None
    entry_method_clean = _re.sub(r"\s*\([^)]*\)\s*$", "", entry_method).strip()

    try:
        cls_n, mth_n = entry_method_clean.split(".", 1)
    except ValueError:
        return {"title": title, "entry_method": entry_method,
                "mermaid": "", "mapping": {}, "source_id_entries": [],
                "err": f"entry_method 格式异常: {entry_method}"}
    mrow = await fetch_method_source(neo4j, cls_n, mth_n, param_hint=param_hint)
    if not mrow or not mrow.get("method_source"):
        return {"title": title, "entry_method": entry_method,
                "mermaid": "", "mapping": {}, "source_id_entries": [],
                "err": f"未查到 {cls_n}.{mth_n} 的源码（hint={param_hint!r}）"}
    method_source = mrow["method_source"]
    file_source = mrow.get("file_source") or ""
    file_name = mrow.get("file_name") or ""

    # offset = 方法在文件中的起始行 - 1
    method_range = find_class_or_method_range(file_source, method_source, mth_n) if file_source else []
    if method_range:
        try:
            base_start = int(method_range[0].split("-")[0])
        except (ValueError, IndexError):
            base_start = 1
    else:
        base_start = 1
        logger.warning(f"[s5] {entry_method} 无法定位文件行号，offset=0")
    offset = base_start - 1

    # 按行编号（跳过 @Anno 行，与 four_chart.py 一致）
    tag_code = tag_code_lines(method_source, strip_annotations=True)
    tagged_source_text = _json.dumps(tag_code, ensure_ascii=False, indent=2)

    # 相关类源码作为 explanation（帮助 LLM 理解跨类调用）
    ctx = build_class_context_text(filtered_rows, max_chars=40_000, prefer_full=True)
    explanation = (
        f"入口方法: {entry_method}\n"
        f"识别原因: {cf_spec.get('reason', '')}\n\n"
        f"相关类源码:\n{ctx['text']}"
    )

    # ==================== Stage A: source_id 划分 ====================
    try:
        src_parsed, _ = await invoke_claude_strict(
            system_prompt=SOURCE_ID_SYSTEM,
            user_prompt=build_source_id_user_prompt(tagged_source_text, explanation),
            required_keys=["lines"],
            label=f"s5-{flow['name']}-{title}-A",
        )
    except Exception as e:
        return {"title": title, "entry_method": entry_method,
                "mermaid": "", "mapping": {}, "source_id_entries": [],
                "err": f"Stage A 失败: {type(e).__name__}: {e}"}

    split_reason = str(src_parsed.get("reason") or "")
    id_list: List[Dict] = []   # 喂给 Stage B 的 [{source_id, lines}]
    id_list_map: Dict[str, List] = {}
    for item in src_parsed.get("lines", []) or []:
        if isinstance(item, str):
            item = [item]
        elif not isinstance(item, list):
            continue
        sid = generate_source_id()
        id_list.append({"source_id": sid, "lines": item})
        id_list_map[sid] = item

    if not id_list:
        return {"title": title, "entry_method": entry_method,
                "mermaid": "", "mapping": {}, "source_id_entries": [],
                "err": "Stage A 未返回任何功能片段"}

    # ==================== Stage B: mermaid + mapping (NodeID → source_id) ====================
    try:
        cfg_parsed, sid_B = await invoke_claude_with_mermaid_check(
            system_prompt=CFG_SYSTEM,
            user_prompt=build_cfg_user_prompt(
                tagged_source=tagged_source_text,
                explanation=explanation,
                source_id_list=id_list,
                code_block_reason=split_reason,
            ),
            required_keys=["mermaid", "mapping"],
            label=f"s5-{flow['name']}-{title}-B",
        )
    except Exception as e:
        return {"title": title, "entry_method": entry_method,
                "mermaid": "", "mapping": {}, "source_id_entries": [],
                "err": f"Stage B 失败: {type(e).__name__}: {e}"}

    mermaid_text = (cfg_parsed.get("mermaid") or "").strip()
    stage_b_mapping_raw = cfg_parsed.get("mapping") or {}
    # 规整 value 类型
    node_to_sid: Dict[str, str] = {}
    for node, v in stage_b_mapping_raw.items():
        nv = normalize_mapping_value(v)
        if not nv:
            continue
        if nv not in id_list_map:
            logger.warning(
                f"[s5] {title} node {node} 映射到 source_id={nv} 不在 Stage A 结果中，忽略"
            )
            continue
        node_to_sid[str(node)] = nv

    # 初步 cfg_lines_map（node → 方法局部行号），用于 Stage C 输入
    cfg_lines_map: Dict[str, List] = {n: id_list_map[s] for n, s in node_to_sid.items()}

    # ==================== Stage C: 校验行号 ====================
    try:
        val_parsed, _ = await invoke_claude_strict(
            system_prompt=CFG_ID_VALIDATE_SYSTEM,
            user_prompt=build_cfg_id_validate_user_prompt(
                tagged_source=tagged_source_text,
                mermaid=mermaid_text,
                current_mapping=cfg_lines_map,
                split_reason=split_reason,
            ),
            required_keys=["mapping"],
            label=f"s5-{flow['name']}-{title}-C",
        )
        refined_map = val_parsed.get("mapping") or {}
    except Exception as e:
        logger.warning(f"[s5] {title} Stage C 失败，退回 Stage B 行号: {e}")
        refined_map = cfg_lines_map

    # ==================== 叠加 offset、构造 source_id_entries ====================
    # 每个 Stage B node 都对应一个 Stage A 的 source_id；我们以 Stage B mapping 为准，
    # 但用 Stage C 校正后的行号覆盖该 source_id 的行范围（若可用）。
    final_lines_by_sid: Dict[str, List[str]] = {}
    for node, sid in node_to_sid.items():
        # 取 Stage C 的修正行号，若不存在则退回 Stage A 原 lines
        raw = refined_map.get(node)
        if raw is None:
            raw = id_list_map.get(sid, [])
        file_lines = apply_offset_to_lines(raw if isinstance(raw, list) else [raw], offset)
        if not file_lines:
            # 再退一步，用 Stage A 的原始行号
            file_lines = apply_offset_to_lines(id_list_map.get(sid, []), offset)
        # 同 source_id 多次出现：取第一个非空（节点共用同一 source_id）
        if sid not in final_lines_by_sid and file_lines:
            final_lines_by_sid[sid] = file_lines

    source_id_entries = [
        {"source_id": sid, "name": file_name, "lines": final_lines_by_sid[sid]}
        for sid in final_lines_by_sid
    ]

    logger.info(
        f"[s5] {flow['name']}/{title} 完成: "
        f"{len(id_list)} 片段, {len(node_to_sid)} 节点→source_id, "
        f"{len(source_id_entries)} 条行号定位"
    )

    # ==================== 后校验：产物质量把关 ====================
    quality_issues: List[str] = []
    if not mermaid_text or "flowchart" not in mermaid_text.lower():
        quality_issues.append("mermaid 为空或缺少 flowchart 头")
    # mermaid 节点数粗估：找出 `-->` 箭头数量，少于 2 视为过简
    if mermaid_text.count("-->") + mermaid_text.count("-.->") < 2:
        quality_issues.append(f"节点/箭头过少（箭头数 {mermaid_text.count('-->')}）")
    if not node_to_sid:
        quality_issues.append("mapping 为空，所有 NodeID→source_id 都丢了")
    if not source_id_entries:
        quality_issues.append("source_id_entries 为空，节点没有任何行号定位")
    if quality_issues:
        logger.warning(
            f"[s5] {flow['name']}/{title} 后校验发现问题: {quality_issues}"
        )

    # ==================== 图定稿后 --resume 生成详细说明 ====================
    description_text = await _generate_diagram_description(
        chart_kind="flowchart",
        resume_session_id=sid_B,
        label=f"s5-{flow['name']}-{title}-desc",
    )

    return {
        "title": title,
        "entry_method": entry_method,
        "mermaid": mermaid_text,
        "mapping": node_to_sid,  # {NodeID: source_id}
        "source_id_entries": source_id_entries,
        "description": description_text,
        "quality_issues": quality_issues,
        "err": "",
    }


async def build_control_flow_section(flow: Dict, scope: Dict,
                                     all_class_rows: List[Dict],
                                     neo4j) -> SectionNode:
    """§5. 核心业务流程图（两阶段 + 行号映射）：

    Stage 1 规划  —— Claude 读 entry_methods + 类骨架，识别 N 个值得画的控制流及各自需要的类
    Stage 2 并发生成 —— 每个控制流走 3-stage line-mapping 管线（SOURCE_ID / CFG / CFG_ID 校验），
                    最终每个 mermaid 节点映射到具体文件行号
    """
    logger.info(f"[s5] 生成业务流程图: {flow['name']}")
    entries = flow.get("entry_methods", [])
    if not entries or not all_class_rows:
        text = TextNode(content={"markdown": "_缺少入口方法或类源码，无法生成控制流图。_"})
        return SectionNode(title="## 5. 核心业务流程图", content=[text], neo4j_id={})

    # -------- Stage 0：入口方法静态 AST 分支分析（"直通查询"硬判据）--------
    branch_analysis = await analyze_entry_methods(neo4j, entries)
    passthrough_count = sum(1 for v in branch_analysis.values() if v.get("is_passthrough"))
    logger.info(
        f"[s5] {flow['name']} AST 分支分析: {len(branch_analysis)}/{len(entries)} 解析成功, "
        f"其中 {passthrough_count} 个判定为直通查询"
    )

    # -------- Stage 1：规划 --------
    skeleton_ctx = build_class_context_text(all_class_rows, max_chars=80_000, prefer_full=False)
    plan_user = build_control_flow_plan_user_prompt(
        flow_name=flow["name"],
        flow_kind=flow.get("kind", "?"),
        entry_methods_detail=_format_entry_methods_detail(entries, all_class_rows),
        class_skeletons=skeleton_ctx["text"],
        branch_hint=format_branch_hint(branch_analysis),
    )
    try:
        plan, _ = await invoke_claude_strict(
            system_prompt=CONTROL_FLOW_PLAN_SYSTEM,
            user_prompt=plan_user,
            required_keys=["control_flows"],
            label=f"s5-plan-{flow['name']}",
        )
    except Exception as e:
        logger.warning(f"[s5] {flow['name']} 规划阶段失败: {type(e).__name__}: {e}")
        return SectionNode(
            title="## 5. 核心业务流程图",
            content=[TextNode(content={"markdown": f"_规划阶段失败，未生成控制流图: {e}_"})],
            neo4j_id={},
        )

    planned = plan.get("control_flows") or []
    skipped = plan.get("skipped") or []
    raw_service_flows = plan.get("service_flows") or []
    # Service 子流程上限 3 个；过滤掉没有 called_by 或 entry_method 的脏数据
    service_flows: List[Dict] = []
    for sf in raw_service_flows[:3]:
        if not isinstance(sf, dict):
            continue
        if not sf.get("entry_method") or not sf.get("called_by"):
            continue
        service_flows.append(sf)
    logger.info(
        f"[s5] {flow['name']} 规划: {len(planned)} 个控制流, "
        f"{len(service_flows)} 个 Service 子流程, "
        f"跳过 {len(skipped)} 个入口"
    )

    # 按 kind 分组 skipped（含直通 Controller 和简单 Service），两分支都会用到
    skipped_controllers, skipped_services = _partition_skipped(skipped)

    if not planned:
        if skipped_controllers or skipped_services:
            parts: List[str] = [
                "### 5.1 其他入口与简单实现说明",
                "",
                "本业务流未识别出需要单独绘图的控制流；以下分组列出直通入口和相关的简单 Service 实现。",
                "",
            ]
            ctl_block = _format_skipped_controller_block(skipped_controllers)
            if ctl_block:
                parts.extend(["", ctl_block])
            svc_block = _format_skipped_service_block(skipped_services, planned_entry_to_idx={})
            if svc_block:
                parts.extend(["", svc_block])
            skip_md = "\n".join(parts)
            skip_refs = _collect_referenced_ids(
                skip_md, class_rows=all_class_rows, entry_methods=entries,
            )
            skip_merged = _dedup(skip_refs["classes"] + skip_refs["methods"])
            skip_nid = {"5.1": skip_merged} if skip_merged else {}
        else:
            skip_md = "_本业务流未识别出具有判断/分支/状态转移的控制流。_"
            skip_nid = {}
        return SectionNode(
            title="## 5. 核心业务流程图",
            content=[TextNode(content={"markdown": skip_md}, neo4j_id=skip_nid)],
            neo4j_id={},
        )

    # -------- Stage 2：并发生成所有控制流（Controller + Service）--------
    # 将 Controller 控制流 和 Service 子流程合成同一列表，统一走 _generate_single_control_flow
    all_flows: List[Dict[str, Any]] = []
    for cf in planned[:5]:
        all_flows.append({"spec": cf, "kind": "controller"})
    for sf in service_flows:
        all_flows.append({"spec": sf, "kind": "service"})

    gen_tasks = [
        _generate_single_control_flow(flow, f["spec"], all_class_rows, neo4j)
        for f in all_flows
    ]
    gen_results = await asyncio.gather(*gen_tasks, return_exceptions=True)

    # -------- 后校验 + 补救：失败的子流程尝试用"宽松 entry_method"重跑一次 --------
    async def _recover_sub_flow(cf: Dict, failed: Any) -> Any:
        """仅针对"未查到源码"这类可恢复失败，把 entry_method 里的 (ParamType) 完全剥掉
        并换个兜底的 entry_method 再跑一次。其它类型失败（LLM 报错等）直接返回原结果。
        """
        if isinstance(failed, Exception):
            return failed  # 异常类原样保留
        err = str(failed.get("err") or "")
        if not err:
            return failed  # 没错
        # 只补救 "未查到源码" 这一种情况
        if "未查到" not in err and "源码" not in err:
            return failed
        original_entry = str(cf.get("entry_method") or "")
        cleaned_entry = __import__("re").sub(r"\s*\([^)]*\)\s*$", "", original_entry).strip()
        if not cleaned_entry or cleaned_entry == original_entry:
            return failed  # 没有 (ParamType) 可剥
        cf_clean = dict(cf)
        cf_clean["entry_method"] = cleaned_entry
        logger.info(
            f"[s5] {flow['name']} 补救子流程 '{cf.get('title')}' "
            f"entry_method: {original_entry!r} → {cleaned_entry!r}"
        )
        try:
            return await _generate_single_control_flow(flow, cf_clean, all_class_rows, neo4j)
        except Exception as e:
            logger.warning(f"[s5] {flow['name']} 补救也失败: {type(e).__name__}: {e}")
            return failed

    recovered = []
    for f_meta, r in zip(all_flows, gen_results):
        if isinstance(r, Exception) or (isinstance(r, dict) and r.get("err")):
            r = await _recover_sub_flow(f_meta["spec"], r)
        recovered.append(r)
    gen_results = recovered

    # -------- 组装 SectionNode --------
    content: List[Any] = []
    neo4j_id_map: Dict[str, List[str]] = {}

    header_md = f"本章展示 **{flow['name']}** 识别出的 {len(planned)} 个核心业务决策流"
    if service_flows:
        header_md += f"以及 {len(service_flows)} 个 Service 子流程"
    header_md += "。"
    extras_total = len(skipped_controllers) + len(skipped_services)
    if extras_total:
        parts_desc: List[str] = []
        if skipped_controllers:
            parts_desc.append(f"{len(skipped_controllers)} 个直通入口")
        if skipped_services:
            parts_desc.append(f"{len(skipped_services)} 个简单 Service 实现")
        header_md += f"末尾节列出 {' 和 '.join(parts_desc)}。"
    content.append(TextNode(content={"markdown": header_md}))

    # 控制流从 5.1 起；skipped 说明移至末尾独立子节
    cf_start_idx = 1

    # 构建 entry_method → 5.X 索引，用于 Service 子流程和简单 Service 标注"被调用自"
    planned_entry_to_idx: Dict[str, int] = {}
    for loop_i, cf in enumerate(planned[:5]):
        em = str(cf.get("entry_method") or "").strip()
        if em:
            planned_entry_to_idx[em] = loop_i + cf_start_idx

    for loop_i, (f_meta, r) in enumerate(zip(all_flows, gen_results)):
        idx = loop_i + cf_start_idx
        spec = f_meta["spec"]
        is_service = f_meta["kind"] == "service"

        title = str(spec.get("title") or f"子流程 {idx}").strip()
        entry_method = str(spec.get("entry_method") or "").strip()
        # purpose 是面向读者的业务用途介绍；缺失时退回 reason（技术性自证）
        purpose = str(spec.get("purpose") or spec.get("reason") or "").strip()

        # 子节标题：Service 子流程加明显标识
        if is_service:
            sub_title_md = f"### 5.{idx} Service 子流程：{title}"
            if entry_method:
                sub_title_md += f"  `{entry_method}`"
            # 注明被哪些 Controller 入口调用
            called_by = spec.get("called_by") or []
            if called_by:
                parts: List[str] = []
                for em in called_by:
                    em_clean = str(em).strip()
                    parent_idx = planned_entry_to_idx.get(em_clean)
                    if parent_idx is not None:
                        parts.append(f"[5.{parent_idx}] `{em_clean}`")
                    else:
                        parts.append(f"`{em_clean}`")
                sub_title_md += f"\n\n**被调用自**：{'、'.join(parts)}"
        else:
            sub_title_md = f"### 5.{idx} {title}"
            if entry_method:
                sub_title_md += f"  `{entry_method}`"

        if purpose:
            sub_title_md += f"\n\n{purpose}"
        content.append(TextNode(content={"markdown": sub_title_md}))

        if isinstance(r, Exception):
            logger.warning(f"[s5] {flow['name']} 子流程 '{title}' 异常: {r}")
            content.append(TextNode(content={"markdown": f"_生成失败: {type(r).__name__}: {r}_"}))
            continue

        if r.get("err"):
            logger.warning(f"[s5] {flow['name']} 子流程 '{title}' 失败: {r['err']}")
            content.append(TextNode(content={"markdown": f"_生成失败: {r['err']}_"}))
            continue

        mermaid_text = r.get("mermaid") or ""
        clean_mapping = r.get("mapping") or {}        # {NodeID: source_id}
        source_entries = r.get("source_id_entries") or []
        if not mermaid_text:
            content.append(TextNode(content={"markdown": "_未返回 mermaid_"}))
            continue

        chart = ChartNode(
            content={"mermaid": mermaid_text, "mapping": clean_mapping},
            neo4j_id=dict(clean_mapping),
            source_id=source_entries,
        )
        content.append(chart)
        sub_description = (r.get("description") or "").strip()
        if sub_description:
            desc_refs = _collect_referenced_ids(
                sub_description, class_rows=all_class_rows, entry_methods=flow.get("entry_methods"),
            )
            merged = _dedup(desc_refs["classes"] + desc_refs["methods"])
            content.append(TextNode(
                content={"markdown": "#### 流程说明\n\n" + sub_description},
                neo4j_id={f"5.{idx}": merged} if merged else {},
            ))
        if clean_mapping:
            neo4j_id_map[f"5.{idx}"] = list(clean_mapping.values())

    # ---- 末尾追加"其他入口与简单实现说明"子节 ----
    if skipped_controllers or skipped_services:
        last_idx = len(all_flows) + cf_start_idx  # 控制流之后下一个编号
        sub_parts: List[str] = [
            f"### 5.{last_idx} 其他入口与简单实现说明",
            "",
        ]
        explain_bits: List[str] = []
        if skipped_controllers:
            explain_bits.append(f"{len(skipped_controllers)} 个无分支逻辑的直通入口")
        if skipped_services:
            explain_bits.append(
                f"{len(skipped_services)} 个被前述控制流 `[[...]]` 黑盒节点调用的简单 Service 方法"
            )
        sub_parts.append(
            "以下罗列未单独绘图的 "
            + " 和 ".join(explain_bits)
            + "，便于读者查阅其用途和实现要点。"
        )
        sub_parts.append("")
        ctl_block = _format_skipped_controller_block(skipped_controllers)
        if ctl_block:
            sub_parts.extend(["", ctl_block])
        svc_block = _format_skipped_service_block(skipped_services, planned_entry_to_idx)
        if svc_block:
            sub_parts.extend(["", svc_block])
        extras_md = "\n".join(sub_parts)
        extras_refs = _collect_referenced_ids(
            extras_md, class_rows=all_class_rows, entry_methods=entries,
        )
        extras_merged = _dedup(extras_refs["classes"] + extras_refs["methods"])
        content.append(TextNode(
            content={"markdown": extras_md},
            neo4j_id={f"5.{last_idx}": extras_merged} if extras_merged else {},
        ))

    return SectionNode(
        title="## 5. 核心业务流程图",
        content=content,
        neo4j_id=neo4j_id_map,
    )


# ===========================================================
# §6 组件索引（无 LLM）
# ===========================================================

def _classify_by_suffix(class_name: str) -> str:
    if not class_name:
        return "其它"
    if class_name.endswith("Controller"):
        return "Controller"
    if class_name.endswith("ServiceImpl"):
        return "ServiceImpl"
    if class_name.endswith("Service"):
        return "Service"
    if class_name.endswith("Mapper") or class_name.endswith("Dao"):
        return "Mapper/Dao"
    if "Example" in class_name or "Criteria" in class_name:
        return "QueryWrapper"
    if class_name.endswith("Dto") or class_name.endswith("Param") or class_name.endswith("Vo") \
            or class_name.endswith("Request") or class_name.endswith("Response"):
        return "DTO/VO"
    if class_name.endswith("Config") or class_name.endswith("Configuration"):
        return "Config"
    return "Entity/其它"


async def build_components_section(flow: Dict, scope: Dict, neo4j) -> SectionNode:
    logger.info(f"[s6] 生成组件索引: {flow['name']}")
    core = flow.get("span", {}).get("core_classes_detail", []) or []
    support = flow.get("span", {}).get("support_classes_detail", []) or []

    if not core and not support:
        text = TextNode(content={"markdown": "_该业务流 span 无类信息。_"})
        return SectionNode(title="## 7. 组件索引", content=[text], neo4j_id={})

    by_layer: Dict[str, List[Dict]] = {}
    for c in core:
        by_layer.setdefault(_classify_by_suffix(c.get("class_name") or ""), []).append(c)

    layer_order = ["Controller", "Service", "ServiceImpl", "Mapper/Dao",
                   "DTO/VO", "Config", "QueryWrapper", "Entity/其它"]

    sub_content: List[Any] = []
    intro = TextNode(content={
        "markdown": (
            f"本业务流共涉及 **{len(core)}** 个核心类 + **{len(support)}** 个公共工具类。"
            f"下表按架构分层组织。\n"
        )
    })
    sub_content.append(intro)

    table_lines = ["| 层 | 类名 | 文件 | 入链深度 |", "|---|---|---|---|"]
    neo4j_id_map: Dict[str, List[str]] = {}
    for layer in layer_order:
        cls_list = sorted(by_layer.get(layer, []), key=lambda x: x.get("class_name") or "")
        if not cls_list:
            continue
        layer_ids = []
        for c in cls_list:
            cid = c.get("class_id")
            cname = c.get("class_name")
            fname = c.get("file_name") or "-"
            depth = c.get("depth", "?")
            table_lines.append(f"| {layer} | `{cname}` | `{fname}` | d{depth} |")
            if cid:
                layer_ids.append(str(cid))
        if layer_ids:
            neo4j_id_map[f"7.{layer}"] = layer_ids

    sub_content.append(TextNode(content={"markdown": "\n".join(table_lines)}))

    if support:
        sup_lines = ["\n**公共工具类**\n", "| 类名 | 文件 |", "|---|---|"]
        sup_ids = []
        for c in sorted(support, key=lambda x: x.get("class_name") or ""):
            sup_lines.append(f"| `{c.get('class_name')}` | `{c.get('file_name', '-')}` |")
            if c.get("class_id"):
                sup_ids.append(str(c["class_id"]))
        sub_content.append(TextNode(content={"markdown": "\n".join(sup_lines)}))
        if sup_ids:
            neo4j_id_map["7.support"] = sup_ids

    return SectionNode(
        title="## 7. 组件索引",
        content=sub_content,
        neo4j_id=neo4j_id_map,
    )


# ===========================================================
# §7 业务状态流转（state machine）
# ===========================================================

async def build_state_machine_section(flow: Dict, scope: Dict,
                                      all_class_rows: List[Dict],
                                      neo4j=None) -> Optional[SectionNode]:
    """§6. 业务状态流转

    流水线：
    1. 纯 Python 预处理：从 Entity 类源码里找候选状态字段 + 扫描引用片段
    2. 1 次 LLM 调用：让 Claude 从候选里挑 1-3 个真状态机并画 stateDiagram-v2
       （含 inline description，避免 --resume 跨图串味）

    返回 None 表示"本业务流没有值得画的状态机，整章应被跳过"
    （调用方据此把 §7 组件索引升级为 §6）。
    """
    logger.info(f"[s6] 生成业务状态流转: {flow['name']}")

    if not all_class_rows:
        logger.info(f"[s6] {flow['name']} 缺少类源码，跳过本章")
        return None

    # ------ Stage 0: 纯 Python 候选检测 ------
    candidates = detect_state_field_candidates(all_class_rows, min_usages=2, max_candidates=8)
    if not candidates:
        logger.info(f"[s6] {flow['name']} 未检测到候选状态字段，跳过本章")
        return None

    logger.info(
        f"[s7] {flow['name']} 候选状态字段 {len(candidates)} 个: "
        + ", ".join(f"{c['owner_class']}.{c['field_name']}({c['usage_count']})" for c in candidates[:5])
    )

    # ------ Stage 1: LLM 识别 + 绘图 ------
    user = build_state_machine_user_prompt(
        flow_name=flow["name"],
        flow_kind=flow.get("kind", "?"),
        candidates_text=format_candidates_for_prompt(candidates),
    )
    try:
        result, _ = await invoke_claude_with_mermaid_check(
            system_prompt=STATE_MACHINE_SYSTEM,
            user_prompt=user,
            required_keys=["state_machines"],
            label=f"s7-{flow['name']}",
        )
    except Exception as e:
        logger.warning(f"[s6] {flow['name']} LLM 调用失败: {type(e).__name__}: {e}，跳过本章")
        return None

    state_machines = result.get("state_machines") or []
    if not isinstance(state_machines, list):
        state_machines = []
    state_machines = state_machines[:3]  # 硬上限
    logger.info(f"[s6] {flow['name']} Claude 挑出 {len(state_machines)} 张状态机图")

    if not state_machines:
        logger.info(f"[s6] {flow['name']} Claude 判定候选均非真实状态机，跳过本章")
        return None

    # ------ Stage 2: 组装 + 每张图的 description ------
    content: List[Any] = []
    neo4j_id_map: Dict[str, List[str]] = {}

    # scope 里所有合法的 nodeId（用于过滤 mapping 里的脏值）
    valid_class_ids = {
        str(r["class_id"]) for r in all_class_rows if r.get("class_id") is not None
    }
    valid_method_ids = {
        str(e.get("node_id"))
        for e in (flow.get("entry_methods") or [])
        if e.get("node_id") is not None
    }
    valid_ids = valid_class_ids | valid_method_ids

    header_md = f"本章展示 **{flow['name']}** 涉及的 {len(state_machines)} 个核心数据对象状态机。"
    content.append(TextNode(content={"markdown": header_md}))

    for idx, sm in enumerate(state_machines, start=1):
        if not isinstance(sm, dict):
            continue
        field = str(sm.get("field") or "").strip()
        title = str(sm.get("title") or f"状态机 {idx}").strip()
        purpose = str(sm.get("purpose") or "").strip()
        mermaid_text = (sm.get("mermaid") or "").strip()
        raw_mapping = sm.get("mapping") or {}

        # 子节标题
        sub_title_md = f"### 6.{idx} {title}"
        if field:
            sub_title_md += f"  `{field}`"
        if purpose:
            sub_title_md += f"\n\n{purpose}"
        content.append(TextNode(content={"markdown": sub_title_md}))

        # 清理 mapping：只保留 scope 内的 class_id / method_id
        clean_mapping: Dict[str, str] = {}
        for k, v in (raw_mapping.items() if isinstance(raw_mapping, dict) else []):
            if not k or not v:
                continue
            sv = str(v) if not isinstance(v, list) else (str(v[0]) if v else "")
            if sv in valid_ids:
                clean_mapping[str(k)] = sv
            else:
                logger.debug(f"[s6] {flow['name']} mapping '{k}' -> '{sv}' 不在 scope，剔除")

        if not mermaid_text or not mermaid_text.lower().lstrip().startswith("statediagram"):
            logger.warning(f"[s6] {flow['name']} 6.{idx} mermaid 为空或非 stateDiagram，跳过")
            content.append(TextNode(content={"markdown": "_未生成有效状态机图_"}))
            continue

        chart = ChartNode(
            content={"mermaid": mermaid_text, "mapping": clean_mapping},
            neo4j_id=dict(clean_mapping),
        )
        content.append(chart)
        if clean_mapping:
            neo4j_id_map[f"6.{idx}"] = list(clean_mapping.values())

        # description 由 Stage 1 同时返回（inline），避免 --resume 跨图串味
        description = str(sm.get("description") or "").strip()
        if description:
            description = _demote_top_headings(description)
            desc_refs = _collect_referenced_ids(
                description, class_rows=all_class_rows, entry_methods=flow.get("entry_methods"),
            )
            merged = _dedup(desc_refs["classes"] + desc_refs["methods"])
            content.append(TextNode(
                content={"markdown": "#### 状态说明\n\n" + description},
                neo4j_id={f"6.{idx}": merged} if merged else {},
            ))

    return SectionNode(
        title="## 6. 业务状态流转",
        content=content,
        neo4j_id=neo4j_id_map,
    )
