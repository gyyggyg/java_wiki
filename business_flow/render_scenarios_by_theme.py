"""按业务主题分文件渲染场景 wiki（单归属 / Option A）

根据 theme_mapping.json 把 business_scenarios.json 的 313 个场景按**入口所在 domain 的主题**
分到 ~11 个 theme 文件里，每个 theme 文件内部分两节：
  §1 主题内场景 —— 只涉及本主题内 domain 的场景
  §2 跨主题协作场景 —— 触达其它主题的场景，按涉及的外部主题再分子节

同时产出 `_index.meta.json` 作为总索引。

单归属：每个场景恰好出现在一个 theme 文件里（按 entry._domain 的 theme），在 header 显式标注 ✕ 跨到的外部主题。

用法:
    python business_flow/render_scenarios_by_theme.py
    python business_flow/render_scenarios_by_theme.py --out-dir business_flow/output/themes
"""
import argparse
import asyncio
import json
import logging
import os
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from interfaces.neo4j_interface import Neo4jInterface
from interfaces.llm_interface import LLMInterface
from business_flow.llm_client import (
    set_default_llm, invoke_llm_strict, invoke_llm_markdown,
)
from business_flow.line_mapping import (
    generate_source_id, find_class_or_method_range,
    fetch_file_source_for_classes,
)
from business_flow.render_scenarios_meta import (
    flatten_scenarios, collect_referenced_class_names,
    resolve_classes_to_nodes, fetch_entity_class_ids,
    build_entity_aware_ownership, enrich_ownership_via_sibling_prefix,
    compute_involved_domains, load_span_flows,
    render_state_diagram,
    render_writes_by_domain_md, render_entry_notes_md,
)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BF_DIR = os.path.join(PROJECT_ROOT, "business_flow")
INPUT_PATH = os.path.join(BF_DIR, "business_scenarios.json")
THEME_MAPPING_PATH = os.path.join(BF_DIR, "theme_mapping.json")
OUTPUT_DIR = os.path.join(BF_DIR, "output", "themes")
SPAN_PATH = os.path.join(BF_DIR, "business_flows_with_span.json")
LOG_DIR = os.path.join(BF_DIR, "logs")


def setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"render_by_theme_{ts}.log")
    logger = logging.getLogger("business_flow.render_by_theme")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    return logger


# ============================================================
# 加载 theme mapping + 场景标注
# ============================================================

def load_theme_mapping(path: str) -> Tuple[Dict[str, str], List[Dict]]:
    """返回 (domain→theme_name, themes 列表)"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    themes = data.get("themes", [])
    domain_to_theme: Dict[str, str] = {}
    for t in themes:
        for d in t.get("domains", []):
            domain_to_theme[d] = t["name"]
    return domain_to_theme, themes


def annotate_themes(
    scenarios: List[Dict],
    class_to_node: Dict[str, Dict],
    ownership: Dict[str, str],
    domain_to_theme: Dict[str, str],
) -> None:
    """给每个场景打 _primary_theme / _involved_themes / _involved_domains"""
    for s in scenarios:
        doms = compute_involved_domains(s, class_to_node, ownership)
        s["_involved_domains"] = sorted(doms)
        themes_involved = {
            domain_to_theme[d] for d in doms if d in domain_to_theme
        }
        s["_involved_themes"] = sorted(themes_involved)
        s["_primary_theme"] = domain_to_theme.get(s["_domain"], "未分类")


def safe_filename(name: str) -> str:
    return re.sub(r'[/\\:*?"<>|]', "_", name)


# ============================================================
# 源码定位：给 class_to_node 的每一项加 source_id + lines
# ============================================================

async def enrich_class_to_node_with_source(
    neo4j,
    class_to_node: Dict[str, Dict],
    logger: logging.Logger,
) -> None:
    """对 class_to_node 中每个类：
    - 生成 8 位随机 source_id（项目级唯一）
    - 拉 Neo4j 里该类的 class_source + file_source，用 find_class_or_method_range 算 lines
    - 结果写回 info["source_id"] / info["lines"]（info["file_name"] 已有）
    """
    if not class_to_node:
        return
    class_ids = [info["nodeId"] for info in class_to_node.values() if info.get("nodeId")]
    file_sources = await fetch_file_source_for_classes(neo4j, class_ids)

    # nodeId → class_name 反向（可能多对一，取第一个）
    used_ids: Set[str] = set()
    resolved = 0
    for class_name, info in class_to_node.items():
        sid = generate_source_id(used_ids)
        info["source_id"] = sid

        node_id = str(info.get("nodeId") or "")
        fs = file_sources.get(node_id, {})
        full_code = fs.get("file_source") or ""
        class_code = fs.get("class_source") or ""
        if full_code and class_code:
            try:
                info["lines"] = find_class_or_method_range(full_code, class_code, class_name)
                if info["lines"]:
                    resolved += 1
            except Exception as e:
                logger.debug(f"lines 计算失败 {class_name}: {e}")
                info["lines"] = []
        else:
            info["lines"] = []
    logger.info(
        f"源码定位: {len(class_to_node)} 个类分配 source_id，"
        f"{resolved} 个算出 lines 范围（其余为空）"
    )


# ============================================================
# Mermaid 渲染：用 class_name 做 participant ID + mapping value = source_id
# （仿照现有 per-flow wiki 的格式）
# ============================================================

_DOMAIN_BOX_COLORS = [
    "rgb(220,240,255)", "rgb(255,240,220)", "rgb(240,255,220)",
    "rgb(255,220,240)", "rgb(220,255,245)", "rgb(245,220,255)",
    "rgb(230,230,230)", "rgb(255,250,200)", "rgb(210,240,210)",
]


def _escape_mermaid_text(s: str) -> str:
    if not s:
        return ""
    return s.replace("#", "＃").replace(";", "；").replace("<", "＜").replace(">", "＞")


_WRITE_METHOD_KW = {
    "insert": ["insert", "save", "add", "create", "batch"],
    "update": ["update", "modify", "edit", "set"],
    "delete": ["delete", "remove"],
    "send": ["send", "publish", "convertandsend"],
    "cache": ["put", "set", "setex", "hset"],
    "export": ["export"],
}


def _write_matches_method(write: Dict, method: str) -> bool:
    op = (write.get("op") or "").lower()
    m = (method or "").lower()
    for k, words in _WRITE_METHOD_KW.items():
        if op == k and any(w in m for w in words):
            return True
    return False


def _unique_participant_id(cls_name: str, used: Set[str]) -> str:
    """类名作 participant ID；极少数同名冲突时加序号后缀"""
    if cls_name not in used:
        used.add(cls_name)
        return cls_name
    i = 2
    while f"{cls_name}_{i}" in used:
        i += 1
    pid = f"{cls_name}_{i}"
    used.add(pid)
    return pid


def render_sequence_diagram_by_classname(
    scenario: Dict,
    class_to_node: Dict,
    ownership: Dict[str, str],
) -> Tuple[str, Dict[str, str]]:
    """按域 box 分组的 sequenceDiagram，participant ID = 类名，mapping value = source_id。
    返回 (mermaid 源码, mapping: class_name → source_id)。
    """
    entry_class = scenario["_entry_class"]
    entry_method = scenario["_entry_method"]
    kind = scenario.get("_kind", "")
    call_path = scenario.get("call_path") or []
    writes = scenario.get("writes") or []

    trigger_alias = {
        "用户端": "用户", "运营端": "运营",
        "大屏端": "大屏", "定时任务": "Quartz",
    }.get(kind, "触发方")

    # 收集参与类（按出现顺序）
    ordered_classes: List[str] = [entry_class]
    seen = {entry_class}
    for step in call_path:
        cls = (step.get("class") or "").strip()
        if cls and cls not in seen:
            seen.add(cls)
            ordered_classes.append(cls)

    # 按 primary_domain 分组
    def domain_of(cls: str) -> str:
        info = class_to_node.get(cls)
        if not info:
            return "—未解析—"
        return ownership.get(info["nodeId"]) or "公共/工具"

    class_domain: Dict[str, str] = {c: domain_of(c) for c in ordered_classes}
    domain_order: List[str] = []
    for c in ordered_classes:
        d = class_domain[c]
        if d not in domain_order:
            domain_order.append(d)
    domain_colors: Dict[str, str] = {}
    for i, d in enumerate(domain_order):
        if d == "公共/工具":
            domain_colors[d] = "rgb(240,240,240)"
        else:
            domain_colors[d] = _DOMAIN_BOX_COLORS[i % len(_DOMAIN_BOX_COLORS)]

    mapping: Dict[str, str] = {}
    used_pids: Set[str] = set()
    cls_to_pid: Dict[str, str] = {}
    lines = ["sequenceDiagram", "    autonumber", f"    participant U as {trigger_alias}"]

    for d in domain_order:
        classes_in_d = [c for c in ordered_classes if class_domain[c] == d]
        if not classes_in_d:
            continue
        color = domain_colors[d]
        lines.append(f'    box {color} {_escape_mermaid_text(d)}')
        for c in classes_in_d:
            pid = _unique_participant_id(c, used_pids)
            cls_to_pid[c] = pid
            lines.append(f'        participant {pid} as {_escape_mermaid_text(c)}')
            info = class_to_node.get(c)
            if info and info.get("source_id"):
                # 关键：mapping key = 类名（= pid），value = source_id
                mapping[pid] = info["source_id"]
        lines.append("    end")

    # 调用边
    entry_pid = cls_to_pid[entry_class]
    lines.append(f'    U ->> {entry_pid}: {_escape_mermaid_text(entry_method)}')

    # 跳过 call_path 中的 entry 自重复
    filtered = []
    skip_entry = True
    for step in call_path:
        cls = (step.get("class") or "").strip()
        mth = (step.get("method") or "").strip()
        if not cls or not mth:
            continue
        if skip_entry and cls == entry_class and mth == entry_method:
            skip_entry = False
            continue
        skip_entry = False
        filtered.append(step)

    caller_pid = entry_pid
    caller_domain = class_domain[entry_class]
    for step in filtered:
        cls = step["class"]
        mth = step["method"]
        role = (step.get("role") or "").lower()
        callee_pid = cls_to_pid.get(cls)
        if not callee_pid:
            continue
        callee_domain = class_domain[cls]
        is_cross = (callee_domain != caller_domain
                    and callee_domain != "公共/工具"
                    and caller_domain != "公共/工具")
        arrow = "->>+" if is_cross else "->>"
        lines.append(f'    {caller_pid} {arrow} {callee_pid}: {_escape_mermaid_text(mth)}')
        if role == "dao":
            for w in writes:
                if _write_matches_method(w, mth):
                    note = f"✍ {w.get('op','?')} {w.get('target','?')}"
                    lines.append(
                        f'    Note right of {callee_pid}: {_escape_mermaid_text(note)}'
                    )
                    break
            if is_cross:
                lines.append(f'    {callee_pid} -->>- {caller_pid}: ')
        if role != "dao":
            caller_pid = callee_pid
            caller_domain = callee_domain

    return "\n".join(lines), mapping


# ============================================================
# 图前/图后说明（模板 fallback，LLM 失败时用）
# ============================================================

def _dedup_classes_in_callpath(scenario: Dict) -> List[str]:
    """按出现顺序收集 scenario 涉及的类名（entry + call_path），去重"""
    classes = [scenario["_entry_class"]]
    seen = {scenario["_entry_class"]}
    for step in scenario.get("call_path") or []:
        c = (step.get("class") or "").strip()
        if c and c not in seen:
            seen.add(c)
            classes.append(c)
    return classes


def render_sequence_intro_md(scenario: Dict) -> str:
    """sequenceDiagram 前的"图说"行，说明这张图的用途"""
    entry = f"{scenario['_entry_class']}.{scenario['_entry_method']}"
    n_domains = len(scenario.get("_involved_domains", []))
    n_writes = len(scenario.get("writes") or [])
    kind = scenario.get("_kind", "")
    trigger_alias = {
        "用户端": "用户", "运营端": "运营",
        "大屏端": "大屏", "定时任务": "Quartz 定时",
    }.get(kind, "触发方")

    parts = [
        f"**图 · 调用时序**：当 {trigger_alias}调用 `{entry}` 时本场景展开的完整协作链路。",
    ]
    if n_domains >= 2:
        parts.append(
            f"跨 **{n_domains}** 个业务域（按域分 box 展示），带 ✍ 标记的节点表示 DAO 写入点。"
        )
    elif n_writes > 0:
        parts.append(f"共产生 **{n_writes}** 次 DAO 写入（图中 ✍ 标记）。")
    else:
        parts.append("本场景为纯查询流程，无写操作。")
    return "> " + " ".join(parts)


def render_sequence_analysis_md(
    scenario: Dict, class_to_node: Dict, ownership: Dict[str, str],
) -> str:
    """sequenceDiagram 后的"调用链路分析"段，按层说明"""
    call_path = scenario.get("call_path") or []
    writes = scenario.get("writes") or []

    # 按 role 分组
    by_role: Dict[str, List[Dict]] = defaultdict(list)
    for step in call_path:
        role = (step.get("role") or "other").lower()
        by_role[role].append(step)

    lines = ["**调用链路分析**：", ""]

    entry_class = scenario["_entry_class"]
    entry_method = scenario["_entry_method"]
    lines.append(f"- **入口层**：`{entry_class}.{entry_method}` 接收"
                 f"{'HTTP' if scenario.get('_kind') != '定时任务' else '定时触发'} "
                 f"请求后，进入业务编排。")

    svc_steps = by_role.get("service", []) + by_role.get("other", [])
    svc_classes = []
    seen = set()
    for s in svc_steps:
        c = s.get("class", "")
        if c and c != entry_class and c not in seen:
            svc_classes.append(c)
            seen.add(c)
    if svc_classes:
        if len(svc_classes) == 1:
            lines.append(f"- **业务编排**：由 `{svc_classes[0]}` 统一处理业务规则。")
        else:
            cls_list = "、".join(f"`{c}`" for c in svc_classes[:4])
            more = "" if len(svc_classes) <= 4 else f" 等 {len(svc_classes)} 个服务"
            lines.append(f"- **业务编排**：经 {cls_list}{more} 协作完成。")

    dao_steps = by_role.get("dao", [])
    if dao_steps:
        # 去重后按类-方法列出
        seen_dao = set()
        dao_items = []
        for s in dao_steps:
            key = (s.get("class", ""), s.get("method", ""))
            if key[0] and key[1] and key not in seen_dao:
                seen_dao.add(key)
                dao_items.append(key)
        if dao_items:
            readables = ", ".join(f"`{c}.{m}`" for c, m in dao_items[:5])
            more = "" if len(dao_items) <= 5 else f" 等 {len(dao_items)} 个 DAO 调用"
            lines.append(f"- **数据访问**：{readables}{more}。")

    if writes:
        lines.append(f"- **数据落库**（{len(writes)} 处写入）：")
        for w in writes:
            kind = w.get("kind", "?")
            op = w.get("op", "?")
            target = w.get("target", "?")
            suffix = "" if kind == "db" else f"（{kind}）"
            lines.append(f"  - `{target}` · {op}{suffix}")
    else:
        lines.append("- **数据落库**：无（读多写少场景）。")

    outer = [t for t in scenario.get("_involved_themes", [])
             if t and t != scenario.get("_primary_theme")]
    if outer:
        lines.append(
            f"- **跨主题衔接**：本场景从 `{scenario['_primary_theme']}` 主题触达 "
            + "、".join(f"`{t}`" for t in outer)
            + "，属于跨业务协作的典型例子。"
        )

    return "\n".join(lines)


def render_class_source_map_md(
    scenario: Dict, class_to_node: Dict,
) -> str:
    """列出参与类 → 源码文件路径，前端可点 nodeId 跳转"""
    classes = _dedup_classes_in_callpath(scenario)
    if not classes:
        return ""
    lines = ["**参与类 → 源码定位**：", ""]
    for c in classes:
        info = class_to_node.get(c)
        if info and info.get("file_name"):
            # 用 source_id 片段，前端 source_id_list 可以解析
            lines.append(f"- `{c}` → [{info['file_name']}](#source-{info['nodeId']})")
        else:
            lines.append(f"- `{c}` → *未在 Neo4j 图中解析到*")
    return "\n".join(lines)


def render_state_intro_md(scenario: Dict) -> str:
    """stateDiagram 前的"图说"行"""
    st = scenario.get("state_transitions") or []
    n = len(st)
    entities = sorted({t.get("entity", "?") for t in st if t.get("entity")})
    ent_str = "、".join(f"`{e}`" for e in entities[:3])
    return (
        f"> **图 · 状态变迁**：本场景触发后，"
        f"{ent_str} 共发生 **{n}** 处字段级状态变化，图示从『触发前』到『落库后』的转换。"
    )


def render_state_analysis_md(scenario: Dict) -> str:
    """stateDiagram 后的"变迁说明"段"""
    st = scenario.get("state_transitions") or []
    if not st:
        return ""
    lines = ["**变迁说明**：", ""]
    for t in st:
        entity = t.get("entity", "?")
        field = t.get("field", "?")
        f = t.get("from") or "（初始）"
        to = t.get("to") or "?"
        lines.append(f"- `{entity}.{field}`：`{f}` → `{to}`")
    return "\n".join(lines)


# ============================================================
# LLM：基于图源码+数据生成图前「用途」+ 图后「详细介绍」
# ============================================================

SEQUENCE_ANALYSIS_SYSTEM = """你是资深 Java 架构师，为跨模块业务流程写技术 wiki。

给定一张 sequenceDiagram 及其相关的场景数据（入口、调用链、写操作、状态变迁、分析备注），产出两段中文文字：

1. `purpose`：图前"图用途说明"，**1-2 句话，≤80 字**
   - 说明这张图展示什么业务动作 / 涉及哪些关键对象
   - 读者看图前能预期到它讲什么
   - 禁用套话："本图展示了"、"下图描述"等

2. `analysis`：图后"详细介绍"—— **对整张图逻辑的完整叙述**，markdown 段落文字（**不是 bullet list**）
   - 按图中的调用时序**串联**叙述业务逻辑：从触发方如何进入入口层 → Controller 做什么 → Service 怎么编排 → DAO 如何落库 → 最终的业务结果
   - 是**一整段连贯的流程说明**，读者读完能像看故事一样理解"这张图对应的业务逻辑是什么"
   - **要覆盖**：每一关键跳在业务上做了什么、为什么这样设计、分支如何决策、事务如何保证一致性、跨域如何衔接、并发/回滚风险
   - 长度 **200-350 字**，1-2 段即可
   - 具体类/方法名用反引号包起来（如 `WlxOrderMapper.insert`）
   - 主语明确（用"Service 层"、"OrderServiceImpl" 而非"它"）
   - **禁用套话**："本图展示了"、"综上所述"、"值得注意"、"由此可见"、"通过分析"、"不难发现"、"总体来说"等
   - 不要复述图里已画出的箭头（"C 调用 S，S 再调用 M"这种），要讲业务含义

**严格 JSON 输出（无围栏、无前言）**
{
  "purpose": "...",
  "analysis": "整段叙事文字..."
}
"""


STATE_ANALYSIS_SYSTEM = """你是资深 Java 架构师。给一张 stateDiagram-v2 和场景数据，产出：

1. `purpose`：图前"图用途说明"，≤60 字
   - 说明这张图展示什么实体的什么状态变化

2. `analysis`：图后"详细介绍"—— **对整张图状态逻辑的完整叙述**，markdown 段落文字（**不是 bullet list**）
   - 串联叙述：这个场景触发后，涉及的实体/字段**整体经历了怎样的状态演变**
   - 各字段间的业务关联（比如扣积分的同时记录流水，两者一起发生构成原子性）
   - 并发或一致性风险（同一实体同时被多个场景改？）
   - 失败时的回滚行为（@Transactional 如何影响这组状态变化）
   - 长度 **120-220 字**，连贯叙事，不要罗列
   - **禁用套话**："本图展示了"、"综上所述"、"值得注意"、"由此可见"、"总体来说"等

**严格 JSON 输出（无围栏）**
{
  "purpose": "...",
  "analysis": "整段叙事文字..."
}
"""


THEME_OVERVIEW_SYSTEM = """你是资深 Java 架构师，为一个跨模块业务场景 wiki 页面写**第一章 概述**。

输入：主题名字、主题描述、本主题下已经处理好的场景列表（每个含 name/trigger/description/关键写操作/跨域/上层 LLM 分析摘要）。

任务：写一段 **150-250 字** 的中文"概述"，让读者开卷就明白本页在讲什么。

**内容要点**
1. 本主题在项目中的业务定位（1-2 句）
2. 主题内场景的共性（都涉及某业务实体？都是用户/运营触发？都有积分扣减？等）
3. 跨主题协作的特征：如果多数场景跨到别的主题，点明这种跨域耦合的业务原因（例："奖品兑换需扣积分故必跨到积分主题"）
4. 本页读者能获得什么具体认知（例："了解退款链路如何跨 3 个域协作"）

**写作要求**
- **不要罗列数字**（数字在「统计信息」章节里已有）
- 不要写"本页包含 N 个场景"、"通过分析"、"本页旨在"等套话
- 用**业务语言**而非技术堆砌
- 段落式，不要 bullet 列表
- 中文

**输出：纯 markdown 段落文字，无围栏、无标题**
"""


def _format_call_path_for_llm(call_path: List[Dict]) -> str:
    if not call_path:
        return "(无)"
    lines = []
    for i, step in enumerate(call_path):
        cls = step.get("class", "?")
        mth = step.get("method", "?")
        role = step.get("role", "?")
        lines.append(f"  {i+1}. [{role}] `{cls}.{mth}`")
    return "\n".join(lines)


def _format_writes_for_llm(writes: List[Dict]) -> str:
    if not writes:
        return "(无写操作)"
    return "\n".join(
        f"  - {w.get('kind','?')} · {w.get('op','?')} · `{w.get('target','?')}`"
        for w in writes
    )


def _format_state_for_llm(transitions: List[Dict]) -> str:
    if not transitions:
        return "(无)"
    return "\n".join(
        f"  - `{t.get('entity','?')}.{t.get('field','?')}`: "
        f"`{t.get('from','?')}` → `{t.get('to','?')}`"
        for t in transitions
    )


def build_sequence_user_prompt(scenario: Dict, seq_src: str) -> str:
    outer = [t for t in scenario.get("_involved_themes", [])
             if t and t != scenario.get("_primary_theme")]
    return "\n".join([
        f"## 场景",
        f"- **名称**：{scenario.get('scenario_name','?')}",
        f"- **描述**：{scenario.get('description','')}",
        f"- **业务域**：`{scenario['_domain']}`（触发侧：{scenario.get('_kind','?')}）",
        f"- **所属主题**：`{scenario.get('_primary_theme','?')}`",
        f"- **触发条件**：{scenario.get('trigger_condition','')}",
        f"- **置信度**：{scenario.get('confidence','?')}",
        f"- **涉及业务域**：{', '.join(scenario.get('_involved_domains', [])) or '(仅本域)'}",
        f"- **跨到的外部主题**：{', '.join(outer) or '(无)'}",
        "",
        f"## 入口方法",
        f"`{scenario['_entry_class']}.{scenario['_entry_method']}` (method_id={scenario.get('_entry_method_id','?')})",
        "",
        f"## 调用链（call_path）",
        _format_call_path_for_llm(scenario.get("call_path") or []),
        "",
        f"## 写操作（writes）",
        _format_writes_for_llm(scenario.get("writes") or []),
        "",
        f"## 状态变迁（state_transitions）",
        _format_state_for_llm(scenario.get("state_transitions") or []),
        "",
        f"## 入口层 LLM 分析备注（上层抽取阶段的观察）",
        scenario.get("_entry_notes", "") or "(无)",
        "",
        f"## 待分析的 sequenceDiagram",
        f"```mermaid",
        seq_src,
        f"```",
        "",
        f"请产出严格 JSON：`purpose` + `analysis`。",
    ])


def build_state_user_prompt(scenario: Dict, state_src: str) -> str:
    return "\n".join([
        f"## 场景",
        f"- 名称：{scenario.get('scenario_name','?')}",
        f"- 描述：{scenario.get('description','')}",
        f"- 入口：`{scenario['_entry_class']}.{scenario['_entry_method']}`",
        "",
        f"## 状态变迁数据",
        _format_state_for_llm(scenario.get("state_transitions") or []),
        "",
        f"## 写操作（关联）",
        _format_writes_for_llm(scenario.get("writes") or []),
        "",
        f"## 待分析的 stateDiagram-v2",
        f"```mermaid",
        state_src,
        f"```",
        "",
        f"请产出严格 JSON：`purpose` + `analysis`。",
    ])


def build_theme_overview_user_prompt(
    theme: Dict,
    theme_scenarios: List[Dict],
    cross_theme_counts: Dict[str, int],
) -> str:
    parts = [
        f"## 主题",
        f"- 名称：{theme['name']}",
        f"- 描述：{theme.get('description','')}",
        "",
        f"## 主题下场景（{len(theme_scenarios)} 个，按 confidence 排序）",
    ]
    for i, s in enumerate(theme_scenarios[:30], 1):
        outer = [t for t in s.get("_involved_themes", [])
                 if t and t != s.get("_primary_theme")]
        writes_brief = ", ".join(
            f"{w.get('op','?')} `{w.get('target','?')}`"
            for w in (s.get("writes") or [])[:3]
        ) or "(无)"
        parts.append(
            f"{i}. **{s.get('scenario_name','?')}** "
            f"(域=`{s['_domain']}`, 触发侧={s.get('_kind','?')})"
        )
        parts.append(f"   描述：{s.get('description','')[:100]}")
        parts.append(f"   触发：{s.get('trigger_condition','')}")
        parts.append(f"   主要写操作：{writes_brief}")
        if outer:
            parts.append(f"   跨到主题：{', '.join(outer)}")
        # 如果场景已经有 LLM 生成的图后分析（seq_analysis），摘要一下前 120 字给 overview 参考
        seq_analysis = s.get("_seq_analysis", "")
        if seq_analysis:
            first_line = seq_analysis.strip().split("\n", 1)[0][:120]
            parts.append(f"   上层分析要点：{first_line}")
        parts.append("")
    if len(theme_scenarios) > 30:
        parts.append(f"... 另外 {len(theme_scenarios) - 30} 个场景略")
        parts.append("")
    if cross_theme_counts:
        parts.append(f"## 跨主题协作统计")
        for t, cnt in sorted(cross_theme_counts.items(), key=lambda x: -x[1]):
            parts.append(f"- `{t}`: {cnt} 个场景")
        parts.append("")
    parts.append("请按要求输出第一章概述的 markdown 段落。")
    return "\n".join(parts)


async def llm_sequence_analysis(
    scenario: Dict, seq_src: str, logger: logging.Logger,
) -> Tuple[Optional[str], Optional[str]]:
    label = f"seq-{scenario.get('_domain','?')}-{scenario.get('_entry_method','?')}-{scenario.get('_intra_entry_index',0)}"
    try:
        result, _ = await invoke_llm_strict(
            system_prompt=SEQUENCE_ANALYSIS_SYSTEM,
            user_prompt=build_sequence_user_prompt(scenario, seq_src),
            required_keys=["purpose", "analysis"],
            label=label,
        )
    except Exception as e:
        logger.warning(f"[{label}] sequence LLM 失败: {type(e).__name__}: {e}")
        return None, None
    return (result.get("purpose", "").strip(),
            result.get("analysis", "").strip())


async def llm_state_analysis(
    scenario: Dict, state_src: str, logger: logging.Logger,
) -> Tuple[Optional[str], Optional[str]]:
    label = f"state-{scenario.get('_domain','?')}-{scenario.get('_entry_method','?')}-{scenario.get('_intra_entry_index',0)}"
    try:
        result, _ = await invoke_llm_strict(
            system_prompt=STATE_ANALYSIS_SYSTEM,
            user_prompt=build_state_user_prompt(scenario, state_src),
            required_keys=["purpose", "analysis"],
            label=label,
        )
    except Exception as e:
        logger.warning(f"[{label}] state LLM 失败: {type(e).__name__}: {e}")
        return None, None
    return (result.get("purpose", "").strip(),
            result.get("analysis", "").strip())


async def llm_theme_overview(
    theme: Dict,
    theme_scenarios: List[Dict],
    cross_theme_counts: Dict[str, int],
    logger: logging.Logger,
) -> Optional[str]:
    label = f"overview-{theme['name']}"
    try:
        text, _ = await invoke_llm_markdown(
            system_prompt=THEME_OVERVIEW_SYSTEM,
            user_prompt=build_theme_overview_user_prompt(
                theme, theme_scenarios, cross_theme_counts,
            ),
            label=label,
        )
    except Exception as e:
        logger.warning(f"[{label}] overview LLM 失败: {type(e).__name__}: {e}")
        return None
    return text.strip()


async def precompute_scenario_analyses(
    scenarios: List[Dict],
    class_to_node: Dict,
    ownership: Dict[str, str],
    concurrency: int,
    logger: logging.Logger,
) -> None:
    """对每个场景：(1) 生成 mermaid 源码并存场景字段 (2) LLM 生成图前图后文本"""
    sem = asyncio.Semaphore(max(1, concurrency))

    async def process_one(s: Dict):
        # 1. 生成 sequence 源码（确定性）
        seq_src, seq_mapping = render_sequence_diagram_by_classname(s, class_to_node, ownership)
        s["_seq_src"] = seq_src
        s["_seq_mapping"] = seq_mapping

        # 2. 生成 state 源码（确定性）
        state_src = render_state_diagram(s)
        s["_state_src"] = state_src

        # 3. LLM：sequence 图前/图后
        async with sem:
            purpose, analysis = await llm_sequence_analysis(s, seq_src, logger)
        if purpose and analysis:
            s["_seq_purpose"] = purpose
            s["_seq_analysis"] = analysis

        # 4. LLM：state 图前/图后（如果有 state 图）
        if state_src:
            async with sem:
                purpose, analysis = await llm_state_analysis(s, state_src, logger)
            if purpose and analysis:
                s["_state_purpose"] = purpose
                s["_state_analysis"] = analysis

    total = len(scenarios)
    logger.info(f"开始 LLM 分析 {total} 个场景的图（并发 {concurrency}）...")
    await asyncio.gather(*[process_one(s) for s in scenarios])

    seq_ok = sum(1 for s in scenarios if s.get("_seq_analysis"))
    state_total = sum(1 for s in scenarios if s.get("_state_src"))
    state_ok = sum(1 for s in scenarios if s.get("_state_analysis"))
    logger.info(
        f"场景图分析完成: sequence {seq_ok}/{total} 成功, "
        f"state {state_ok}/{state_total} 成功"
    )


# ============================================================
# 渲染单个场景的 block（header + 图说 + seq + 分析 + 源码定位 + writes + state）
# ============================================================

def render_scenario_block(
    scenario: Dict, idx: int,
    class_to_node: Dict, ownership: Dict[str, str],
) -> List[Dict]:
    blocks: List[Dict] = []
    # 跨主题标签
    cross_tag = ""
    outer_themes = [
        t for t in scenario.get("_involved_themes", [])
        if t and t != scenario["_primary_theme"]
    ]
    if outer_themes:
        cross_tag = f' · **跨主题** ✕ {"、".join(f"`{t}`" for t in outer_themes)}'

    header_md = "\n".join([
        f'### 场景 {idx}：{scenario.get("scenario_name", "?")}',
        "",
        f'**入口** `{scenario["_entry_class"]}.{scenario["_entry_method"]}` '
        f'({scenario.get("_kind","")}) · '
        f'**域** `{scenario["_domain"]}` · '
        f'**触发** {scenario.get("trigger_condition","")}'
        f'{cross_tag}',
        "",
        scenario.get("description", ""),
    ])
    nid: Dict[str, List[str]] = {}
    if scenario.get("_entry_method_id"):
        nid[str(idx)] = [str(scenario["_entry_method_id"])]
    blocks.append({"markdown": header_md, "neo4j_id": nid})

    # —— 调用时序图 ——
    seq_src = scenario.get("_seq_src")
    seq_mapping = scenario.get("_seq_mapping")
    if seq_src is None:
        seq_src, seq_mapping = render_sequence_diagram_by_classname(
            scenario, class_to_node, ownership,
        )
    # 图前「用途」：优先用 LLM 产出，否则回落模板
    seq_purpose = scenario.get("_seq_purpose") or render_sequence_intro_md(scenario)
    blocks.append({
        "markdown": "#### 调用时序\n\n> " + seq_purpose.lstrip("> ").strip(),
        "neo4j_id": {},
    })
    blocks.append({
        "mermaid": f"```mermaid\n{seq_src}\n```",
        "mapping": seq_mapping or {},
    })
    # 图后「详细介绍」：优先 LLM，否则模板
    seq_analysis = scenario.get("_seq_analysis") or \
        render_sequence_analysis_md(scenario, class_to_node, ownership)
    blocks.append({"markdown": "**详细介绍**：\n\n" + seq_analysis, "neo4j_id": {}})

    # —— 写操作表 ——
    writes_md = render_writes_by_domain_md(scenario, class_to_node, ownership)
    if writes_md:
        blocks.append({"markdown": writes_md, "neo4j_id": {}})

    # —— 状态变迁图 ——
    state_src = scenario.get("_state_src")
    if state_src is None:
        state_src = render_state_diagram(scenario)
    if state_src:
        state_purpose = scenario.get("_state_purpose") or render_state_intro_md(scenario)
        blocks.append({
            "markdown": "#### 状态变迁\n\n> " + state_purpose.lstrip("> ").strip(),
            "neo4j_id": {},
        })
        blocks.append({
            "mermaid": f"```mermaid\n{state_src}\n```",
            "mapping": {},
        })
        state_analysis = scenario.get("_state_analysis") or render_state_analysis_md(scenario)
        if state_analysis:
            blocks.append({
                "markdown": "**详细介绍**：\n\n" + state_analysis,
                "neo4j_id": {},
            })

    return blocks


# ============================================================
# 主题页的整体组织
# ============================================================

def compute_cross_theme_counts(
    theme_name: str, cross_scenarios: List[Dict],
) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for s in cross_scenarios:
        for t in s.get("_involved_themes", []):
            if t and t != theme_name:
                counts[t] += 1
    return counts


def render_theme_overview_md(
    theme: Dict,
    theme_scenarios: List[Dict],
    cross_scenarios: List[Dict],
    llm_overview: Optional[str] = None,
) -> str:
    """渲染主题页顶部：# 标题 → 第一章 概述（LLM 或 fallback 模板）→ 统计信息章"""
    total = len(theme_scenarios)
    n_cross = len(cross_scenarios)
    n_within = total - n_cross
    domains = sorted({s["_domain"] for s in theme_scenarios})
    n_entries = len({
        (s["_domain"], s["_entry_method_id"]) for s in theme_scenarios
    })

    cross_theme_counts = compute_cross_theme_counts(theme["name"], cross_scenarios)

    parts = [f"# {theme['name']}", ""]
    if theme.get("description"):
        parts.append(f"> {theme['description']}")
        parts.append("")

    # —— 第一章 概述：优先 LLM，否则 fallback 到模板 ——
    parts.append("## 第一章 概述")
    parts.append("")
    if llm_overview:
        parts.append(llm_overview.strip())
        parts.append("")
    else:
        # fallback：模板拼接
        intro_sents: List[str] = []
        intro_sents.append(
            f"本页收集了 **{theme['name']}** 主题下识别出的 **{total}** 个业务场景"
            f"（跨 **{len(domains)}** 个业务域、**{n_entries}** 个入口）。"
        )
        if cross_theme_counts:
            top_cross = sorted(cross_theme_counts.items(), key=lambda x: -x[1])[:3]
            crossed_str = "、".join(f"**{t}**（{c}）" for t, c in top_cross)
            intro_sents.append(
                f"其中 **{n_cross}** 个场景跨主题协作，最频繁触达的外部主题是 {crossed_str}。"
            )
        intro_sents.append(
            "每个场景配有：调用时序图 + 图前用途说明 + 图后详细分析、"
            "参与类源码定位、写操作足迹、状态变迁图（有字段变化时）。"
        )
        for s in intro_sents:
            parts.append(s)
            parts.append("")

    # —— 统计信息章 ——
    parts.extend([
        "## 统计信息",
        "",
        f"- **覆盖域**（{len(domains)}）：{', '.join(f'`{d}`' for d in domains)}",
        f"- **入口方法**：{n_entries} 个",
        f"- **场景总数**：{total}（主题内 {n_within} / 跨主题 {n_cross}）",
        "",
    ])
    if cross_theme_counts:
        parts.append("### 跨主题协作分布")
        parts.append("")
        parts.append("| 协作主题 | 场景数 |")
        parts.append("|---|---|")
        for t, cnt in sorted(cross_theme_counts.items(), key=lambda x: -x[1]):
            parts.append(f"| `{t}` | {cnt} |")
        parts.append("")
    return "\n".join(parts)


def build_theme_meta(
    theme: Dict,
    all_scenarios: List[Dict],
    class_to_node: Dict,
    ownership: Dict[str, str],
    llm_overview: Optional[str] = None,
) -> Optional[Dict]:
    theme_name = theme["name"]
    theme_scenarios = [
        s for s in all_scenarios if s["_primary_theme"] == theme_name
    ]
    if not theme_scenarios:
        return None

    within = [s for s in theme_scenarios if len(s.get("_involved_themes", [])) <= 1]
    cross = [s for s in theme_scenarios if len(s.get("_involved_themes", [])) >= 2]

    conf_rank = {"high": 0, "medium": 1, "low": 2}
    def sort_key(s: Dict):
        return (
            conf_rank.get(s.get("confidence", "low"), 3),
            s["_entry_class"], s["_entry_method"], s["_intra_entry_index"],
        )
    within.sort(key=sort_key)
    cross.sort(key=sort_key)

    wiki: List[Dict] = []
    wiki.append({
        "markdown": render_theme_overview_md(theme, theme_scenarios, cross, llm_overview),
        "neo4j_id": {},
    })

    seen_entry_notes: Set[Tuple[str, object]] = set()
    idx_counter = [0]

    def add_scenario(s: Dict) -> None:
        idx_counter[0] += 1
        for b in render_scenario_block(s, idx_counter[0], class_to_node, ownership):
            wiki.append(b)
        entry_key = (s["_domain"], s.get("_entry_method_id"))
        if entry_key not in seen_entry_notes:
            seen_entry_notes.add(entry_key)
            notes_md = render_entry_notes_md(s)
            if notes_md:
                wiki.append({"markdown": notes_md, "neo4j_id": {}})

    if within:
        wiki.append({
            "markdown": f"## 1. 主题内场景（{len(within)}）",
            "neo4j_id": {},
        })
        for s in within:
            add_scenario(s)

    if cross:
        wiki.append({
            "markdown": f"## 2. 跨主题协作场景（{len(cross)}）",
            "neo4j_id": {},
        })
        # 按跨到的外部主题组合再分子节
        by_outer: Dict[Tuple[str, ...], List[Dict]] = defaultdict(list)
        for s in cross:
            outer = tuple(sorted(
                t for t in s.get("_involved_themes", [])
                if t and t != theme_name
            ))
            by_outer[outer].append(s)
        sub_idx = 0
        for outer, items in sorted(by_outer.items(), key=lambda x: -len(x[1])):
            sub_idx += 1
            outer_str = " ✕ ".join(f"`{t}`" for t in outer) if outer else "无外部主题"
            wiki.append({
                "markdown": f"### 2.{sub_idx} → {outer_str}（{len(items)} 场景）",
                "neo4j_id": {},
            })
            for s in items:
                add_scenario(s)

    # source_id_list：本主题涉及的所有类
    referenced_classes: Set[str] = set()
    for s in theme_scenarios:
        referenced_classes.add(s["_entry_class"])
        for step in s.get("call_path") or []:
            c = (step.get("class") or "").strip()
            if c:
                referenced_classes.add(c)

    source_id_list: List[Dict] = []
    seen_sids: Set[str] = set()
    for name in sorted(referenced_classes):
        info = class_to_node.get(name)
        if not info or not info.get("file_name"):
            continue
        sid = info.get("source_id")
        if not sid or sid in seen_sids:
            continue
        seen_sids.add(sid)
        source_id_list.append({
            "source_id": sid,
            "name": info["file_name"],
            "lines": info.get("lines") or [],
        })

    return {"wiki": wiki, "source_id_list": source_id_list}


# ============================================================
# 索引页
# ============================================================

def _flow_to_filename(flow_name: str) -> str:
    """和 generate.py / generate_wiki.py 保持一致的命名约定"""
    safe = flow_name.replace("/", "_").replace(" ", "_") \
                    .replace("(", "").replace(")", "")
    if safe.endswith("流") and len(safe) > 1:
        safe = safe[:-1]
    return f"{safe}.meta.json"


def _find_next_top_section_number(wiki_entries: List[Dict]) -> int:
    """扫 wiki entry 的 markdown，返回 max (## N. ...) + 1；找不到则返回 1"""
    max_num = 0
    for entry in wiki_entries:
        md = entry.get("markdown", "")
        m = re.match(r"^## (\d+)\. ", md)
        if m:
            n = int(m.group(1))
            if n > max_num:
                max_num = n
    return max_num + 1


def _find_cross_domain_section_index(wiki_entries: List[Dict]) -> int:
    """定位「## N. 跨模块业务流」章节的起始 entry 索引；找不到返回 -1"""
    pat = re.compile(r"^## (\d+\.\s*)?跨模块业务流")
    for i, entry in enumerate(wiki_entries):
        if pat.match(entry.get("markdown", "")):
            return i
    return -1


def build_cross_domain_section_blocks(
    domain: str,
    scenarios: List[Dict],
    section_num: int,
    class_to_node: Dict,
    ownership: Dict[str, str],
) -> List[Dict]:
    """为某 domain 的跨模块场景构造章节 blocks（不写文件，只返回 list）"""
    blocks: List[Dict] = []

    # —— 章节 intro ——
    domain_counts: Dict[str, int] = defaultdict(int)
    for s in scenarios:
        for d in s.get("_involved_domains", []):
            if d and d != domain:
                domain_counts[d] += 1

    intro_lines = [
        f"## {section_num}. 跨模块业务流",
        "",
        f"本模块的入口方法触发的跨模块业务流共 **{len(scenarios)}** 个，"
        f"涉及下列其他模块（按出现次数降序）：",
        "",
    ]
    for d, cnt in sorted(domain_counts.items(), key=lambda x: -x[1]):
        intro_lines.append(f"- `{d}`：{cnt} 个场景")
    intro_lines.append("")
    blocks.append({"markdown": "\n".join(intro_lines), "neo4j_id": {}})

    # —— 每个场景 ——
    conf_rank = {"high": 0, "medium": 1, "low": 2}
    sorted_scenarios = sorted(scenarios, key=lambda s: (
        conf_rank.get(s.get("confidence", "low"), 3),
        s["_entry_class"], s["_entry_method"], s["_intra_entry_index"],
    ))

    seen_entry_notes: Set[Tuple[str, object]] = set()
    idx_counter = [0]

    for s in sorted_scenarios:
        idx_counter[0] += 1
        blocks.extend(render_scenario_block(
            s, idx_counter[0], class_to_node, ownership,
        ))
        key = (s["_domain"], s.get("_entry_method_id"))
        if key not in seen_entry_notes:
            seen_entry_notes.add(key)
            notes_md = render_entry_notes_md(s)
            if notes_md:
                blocks.append({"markdown": notes_md, "neo4j_id": {}})

    return blocks


def _find_components_section_index(wiki_entries: List[Dict]) -> int:
    """定位「## N. 组件索引」章节的起始 entry 索引；找不到返回 -1"""
    pat = re.compile(r"^## (\d+\.\s*)?组件索引")
    for i, entry in enumerate(wiki_entries):
        if pat.match(entry.get("markdown", "")):
            return i
    return -1


def _extract_section_number(entry: Dict) -> Optional[int]:
    md = entry.get("markdown", "")
    m = re.match(r"^## (\d+)\. ", md)
    return int(m.group(1)) if m else None


def _renumber_section_in_entry(entry: Dict, old_num: int, new_num: int) -> None:
    """把 entry 的 markdown 章节号 old_num 换成 new_num，并同步 neo4j_id 的键"""
    md = entry.get("markdown", "")
    old_prefix = f"## {old_num}."
    if md.startswith(old_prefix):
        entry["markdown"] = f"## {new_num}." + md[len(old_prefix):]
    # 同步 neo4j_id 的键
    nid = entry.get("neo4j_id")
    if nid:
        new_nid: Dict[str, object] = {}
        old_str = str(old_num)
        new_str = str(new_num)
        for k, v in nid.items():
            if k == old_str:
                new_nid[new_str] = v
            elif k.startswith(f"{old_str}."):
                new_nid[new_str + k[len(old_str):]] = v
            else:
                new_nid[k] = v
        entry["neo4j_id"] = new_nid


def append_cross_domain_to_flow_wiki(
    flow_wiki_path: str,
    domain: str,
    scenarios: List[Dict],
    class_to_node: Dict,
    ownership: Dict[str, str],
    logger: logging.Logger,
) -> int:
    """把跨模块业务流章节**插入到组件索引章节之前**，保证组件索引始终是最后一章。

    幂等：先移除已有的「跨模块业务流」章节，再插入新的。
    返回：该文件新增的 source_id 条目数。
    """
    with open(flow_wiki_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    wiki = data.get("wiki", [])
    source_id_list = data.get("source_id_list", [])

    # 幂等：定位并移除已有的跨模块章节（及其所有子 entries 直到下一个 "## N." 或结尾）
    existing_cd_idx = _find_cross_domain_section_index(wiki)
    if existing_cd_idx >= 0:
        end_idx = len(wiki)
        for j in range(existing_cd_idx + 1, len(wiki)):
            md_j = wiki[j].get("markdown", "")
            if re.match(r"^## \d+\. ", md_j):
                end_idx = j
                break
        del wiki[existing_cd_idx:end_idx]

    # 定位组件索引章节
    comp_idx = _find_components_section_index(wiki)
    if comp_idx >= 0:
        comp_num = _extract_section_number(wiki[comp_idx])
        if comp_num is None:
            comp_num = _find_next_top_section_number(wiki)
        # 跨模块章节占用当前 components 的编号；components 顺移 +1
        section_num = comp_num
        new_comp_num = comp_num + 1
        # 先把 components 重编号
        _renumber_section_in_entry(wiki[comp_idx], comp_num, new_comp_num)
        # 然后在 comp_idx 位置插入跨模块 blocks
        new_blocks = build_cross_domain_section_blocks(
            domain, scenarios, section_num, class_to_node, ownership,
        )
        wiki[comp_idx:comp_idx] = new_blocks
    else:
        # 找不到组件索引（文件被改动过），回退到末尾追加
        section_num = _find_next_top_section_number(wiki)
        new_blocks = build_cross_domain_section_blocks(
            domain, scenarios, section_num, class_to_node, ownership,
        )
        wiki.extend(new_blocks)

    # 合并 source_id_list
    existing_sids = {s.get("source_id") for s in source_id_list}
    added = 0
    # 本场景涉及的类
    for s in scenarios:
        classes = [s["_entry_class"]]
        for step in s.get("call_path") or []:
            c = (step.get("class") or "").strip()
            if c and c not in classes:
                classes.append(c)
        for cls_name in classes:
            info = class_to_node.get(cls_name)
            if not info or not info.get("file_name"):
                continue
            sid = info.get("source_id")
            if not sid or sid in existing_sids:
                continue
            existing_sids.add(sid)
            source_id_list.append({
                "source_id": sid,
                "name": info["file_name"],
                "lines": info.get("lines") or [],
            })
            added += 1

    data["wiki"] = wiki
    data["source_id_list"] = source_id_list
    with open(flow_wiki_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(
        f"  append {len(scenarios)} 场景 "
        f"(§{section_num}, 新增 {added} source_id) → "
        f"{os.path.basename(os.path.dirname(flow_wiki_path))}/{os.path.basename(flow_wiki_path)}"
    )
    return added


def distribute_scenarios_to_theme_flow_wikis(
    scenarios: List[Dict],
    themes: List[Dict],
    domain_to_theme: Dict[str, str],
    flows_out_dir: str,
    themes_out_dir: str,
    class_to_node: Dict,
    ownership: Dict[str, str],
    logger: logging.Logger,
) -> Tuple[Dict[str, Dict], List[str]]:
    """把跨模块场景分发到对应的 per-flow wiki 文件（在 themes/<theme>/<domain>.meta.json）。

    流程:
      1. 建 themes/<theme>/ 目录，把每个 domain 的 per-flow wiki 从 flows_out_dir 拷过来（覆盖式）
      2. 按 scenario._domain 分组所有跨模块场景
      3. 对每个有跨模块场景的 domain，append 到 themes/<theme>/<domain>.meta.json

    返回 (organized, unclassified_domains)：organized 用于索引构建
    """
    os.makedirs(themes_out_dir, exist_ok=True)
    organized: Dict[str, Dict] = {}

    # —— Step 1：按主题建子目录 + 拷贝 per-flow wiki ——
    for t in themes:
        theme_name = t["name"]
        theme_subdir = os.path.join(themes_out_dir, safe_filename(theme_name))
        os.makedirs(theme_subdir, exist_ok=True)
        info = {"description": t.get("description", ""), "flows": []}
        for domain in t.get("domains", []):
            flow_fname = _flow_to_filename(domain)
            src = os.path.join(flows_out_dir, flow_fname)
            dst = os.path.join(theme_subdir, flow_fname)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                info["flows"].append({
                    "domain": domain, "file": flow_fname,
                    "relpath": f"themes/{safe_filename(theme_name)}/{flow_fname}",
                    "cross_domain_count": 0,
                })
            else:
                info["flows"].append({
                    "domain": domain, "file": flow_fname,
                    "relpath": None, "missing": True,
                })
        organized[theme_name] = info

    # —— Step 2：按 domain 分组跨模块场景 ——
    scenarios_by_domain: Dict[str, List[Dict]] = defaultdict(list)
    for s in scenarios:
        scenarios_by_domain[s["_domain"]].append(s)

    # —— Step 3：把每个 domain 的场景追加到对应 per-flow wiki ——
    unclassified: List[str] = []
    for domain, domain_scenarios in scenarios_by_domain.items():
        theme_name = domain_to_theme.get(domain)
        if not theme_name:
            logger.warning(
                f"⚠ domain `{domain}` 不在 theme_mapping 中，"
                f"{len(domain_scenarios)} 个跨模块场景无处归属"
            )
            unclassified.append(domain)
            continue
        theme_subdir = os.path.join(themes_out_dir, safe_filename(theme_name))
        flow_fname = _flow_to_filename(domain)
        target = os.path.join(theme_subdir, flow_fname)
        if not os.path.isfile(target):
            logger.warning(f"⚠ flow wiki 不存在: {target}，跳过")
            continue
        append_cross_domain_to_flow_wiki(
            target, domain, domain_scenarios, class_to_node, ownership, logger,
        )
        # 更新 organized 计数
        for f in organized[theme_name]["flows"]:
            if f.get("domain") == domain:
                f["cross_domain_count"] = len(domain_scenarios)
                break

    return organized, unclassified


def build_index_meta_for_distributed(
    organized: Dict[str, Dict],
    unclassified_domains: List[str],
) -> Dict:
    """按 distributed 结构构建索引：每个主题下列 per-flow wiki 文件 + 跨模块场景数"""
    n_themes = len(organized)
    total_flows = sum(
        len([f for f in info["flows"] if not f.get("missing")])
        for info in organized.values()
    )
    total_cross = sum(
        sum(f.get("cross_domain_count", 0) for f in info["flows"])
        for info in organized.values()
    )

    lines = [
        "# 业务主题索引",
        "",
        f"- **{n_themes}** 个业务主题 / **{total_flows}** 个模块内流 wiki",
        f"- **{total_cross}** 个跨模块业务流已追加到对应 domain 的 wiki 末尾（「## N. 跨模块业务流」章节）",
        "",
    ]
    for theme_name, info in organized.items():
        lines.append(f"## {theme_name}")
        lines.append("")
        if info.get("description"):
            lines.append(f"> {info['description']}")
            lines.append("")
        for f in info.get("flows", []):
            if f.get("missing"):
                lines.append(f"- ⚠ `{f['domain']}`（源 wiki 未生成：{f['file']}）")
                continue
            cc = f.get("cross_domain_count", 0)
            tag = f" · **+{cc}** 跨模块业务流" if cc > 0 else ""
            lines.append(f"- [`{f['domain']}`]({f['relpath']}){tag}")
        lines.append("")

    if unclassified_domains:
        lines.append("## ⚠ 未归类 domain")
        lines.append("")
        for d in unclassified_domains:
            lines.append(f"- `{d}` 未在 theme_mapping.json 中出现")
        lines.append("")

    return {
        "wiki": [{"markdown": "\n".join(lines), "neo4j_id": {}}],
        "source_id_list": [],
    }


def build_index_meta(
    themes: List[Dict],
    theme_counts: Dict[str, int],
    total_scenarios: int,
    unclassified_count: int,
) -> Dict:
    lines = [
        "# 业务主题索引",
        "",
        f"本项目全部业务场景共 **{total_scenarios}** 个，按 **{len(themes)}** 个业务主题组织。",
        "",
        "## 主题列表",
        "",
        "| 主题 | 描述 | 场景数 | 覆盖域数 | 文件 |",
        "|---|---|---|---|---|",
    ]
    for t in themes:
        name = t["name"]
        fname = safe_filename(name) + ".meta.json"
        count = theme_counts.get(name, 0)
        n_doms = len(t.get("domains", []))
        desc = t.get("description", "")
        lines.append(
            f"| **{name}** | {desc} | {count} | {n_doms} | `themes/{fname}` |"
        )
    lines.append("")
    if unclassified_count:
        lines.append(f"> ⚠ 有 **{unclassified_count}** 个场景的入口 domain 不在任何主题里，未归类。")
        lines.append("")
    return {
        "wiki": [{"markdown": "\n".join(lines), "neo4j_id": {}}],
        "source_id_list": [],
    }


# ============================================================
# 主流程
# ============================================================

async def main():
    parser = argparse.ArgumentParser(
        description="把跨模块场景分发到各主题子目录下的 per-flow wiki（追加『跨模块业务流』章节）"
    )
    parser.add_argument("--input", default=INPUT_PATH,
                        help="business_scenarios.json 路径")
    parser.add_argument("--theme-mapping", default=THEME_MAPPING_PATH)
    parser.add_argument("--flows-dir", default=os.path.join(BF_DIR, "output"),
                        help="per-flow wiki 源目录（generate.py 产物目录）")
    parser.add_argument("--out-dir", default=OUTPUT_DIR,
                        help="themes/ 输出目录")
    parser.add_argument("--max-shared", type=int, default=3)
    parser.add_argument("--span-path", default=SPAN_PATH,
                        help="business_flows_with_span.json 路径")
    parser.add_argument("--cross-domain-only", action="store_true", default=False,
                        help="只渲染触达 ≥2 个 domain 的场景（默认开启 —— 单域场景的内容已在 per-flow wiki 的基础章节里）")
    parser.add_argument("--no-llm", action="store_true", default=False,
                        help="关闭 LLM，全部用模板生成（调试用，跑得快）")
    parser.add_argument("--llm-concurrency", type=int, default=5,
                        help="LLM 调用并发数（默认 5）")
    args = parser.parse_args()

    logger = setup_logger()

    if not os.path.isfile(args.theme_mapping):
        logger.error(f"theme_mapping.json 不存在: {args.theme_mapping}")
        logger.error("请先运行 `python business_flow/classify_themes.py` 产出。")
        sys.exit(1)

    # 加载
    with open(args.input, encoding="utf-8") as f:
        sdata = json.load(f)
    scenarios = flatten_scenarios(sdata)
    logger.info(f"展平 {len(scenarios)} 个场景")

    domain_to_theme, themes = load_theme_mapping(args.theme_mapping)
    logger.info(f"主题映射: {len(domain_to_theme)} domain → {len(themes)} theme")

    # Neo4j + ownership
    class_names = collect_referenced_class_names(scenarios)
    span_flows = load_span_flows(args.span_path)
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    try:
        if not await neo4j.test_connection():
            logger.error("Neo4j 连接失败")
            sys.exit(1)
        entity_ids = await fetch_entity_class_ids(neo4j)
        class_to_node = await resolve_classes_to_nodes(neo4j, class_names, logger)
        logger.info(f"类解析: {len(class_to_node)}/{len(class_names)} 命中")
        # 给每个类分配 source_id + 计算 lines 行号范围（从源码行匹配）
        await enrich_class_to_node_with_source(neo4j, class_to_node, logger)
    finally:
        neo4j.close()

    ownership, id_to_name = build_entity_aware_ownership(
        span_flows, args.max_shared, entity_ids, logger,
    )
    ownership = enrich_ownership_via_sibling_prefix(
        ownership, id_to_name, class_to_node, logger,
    )

    # 场景打 theme 标签
    annotate_themes(scenarios, class_to_node, ownership, domain_to_theme)

    # 可选：过滤非跨模块场景
    if args.cross_domain_only:
        before = len(scenarios)
        scenarios = [s for s in scenarios if len(s.get("_involved_domains", [])) >= 2]
        logger.info(f"--cross-domain-only 过滤: {before} → {len(scenarios)} 个跨模块场景")

    # ============================================================
    # 阶段 A：初始化 LLM + 对每个场景 LLM 生成图前「用途」+ 图后「详细介绍」
    # ============================================================
    if not args.no_llm:
        llm = LLMInterface()
        set_default_llm(llm)
        logger.info(
            f"LLM: provider={llm.provider} "
            f"model={llm.model_kwargs.get('model_name') or llm.model_kwargs.get('model')}"
        )
        await precompute_scenario_analyses(
            scenarios, class_to_node, ownership, args.llm_concurrency, logger,
        )
    else:
        logger.info("--no-llm 模式：跳过 LLM，全部用模板")

    # ============================================================
    # 阶段 B：分发场景到 themes/<theme>/<domain>.meta.json
    # ============================================================
    logger.info("")
    logger.info("分发跨模块场景到各主题子目录下的 per-flow wiki 文件...")
    organized, unclassified_domains = distribute_scenarios_to_theme_flow_wikis(
        scenarios=scenarios,
        themes=themes,
        domain_to_theme=domain_to_theme,
        flows_out_dir=args.flows_dir,
        themes_out_dir=args.out_dir,
        class_to_node=class_to_node,
        ownership=ownership,
        logger=logger,
    )

    # ============================================================
    # 阶段 C：构建索引 _index.meta.json
    # ============================================================
    index_meta = build_index_meta_for_distributed(organized, unclassified_domains)
    index_path = os.path.join(args.out_dir, "_index.meta.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_meta, f, ensure_ascii=False, indent=2)
    logger.info(f"总索引: {index_path}")

    # 汇总
    total_flow_files = sum(
        len([f for f in info["flows"] if not f.get("missing")])
        for info in organized.values()
    )
    total_with_cross = sum(
        len([f for f in info["flows"] if f.get("cross_domain_count", 0) > 0])
        for info in organized.values()
    )
    total_cross_scenarios = sum(
        sum(f.get("cross_domain_count", 0) for f in info["flows"])
        for info in organized.values()
    )
    logger.info("")
    logger.info("=== 汇总 ===")
    logger.info(
        f"{len(organized)} 个主题 / {total_flow_files} 个 per-flow wiki 文件 / "
        f"{total_with_cross} 个文件含跨模块场景 / 共 {total_cross_scenarios} 个跨模块场景"
    )
    if unclassified_domains:
        logger.warning(
            f"⚠ {len(unclassified_domains)} 个 domain 未归类（检查 theme_mapping.json）："
            f" {unclassified_domains}"
        )


if __name__ == "__main__":
    asyncio.run(main())
