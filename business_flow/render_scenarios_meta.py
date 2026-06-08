"""把 business_scenarios.json 渲染为跨模块端到端业务场景的 meta.json

**只渲染真正跨模块的场景**（call_path 触达 ≥2 个业务域的），不覆盖 per-flow wiki
已经讲过的单域内容。

判据：
  1. 加载 business_flows_with_span.json，算出每个类的 primary_owner domain
     （被 > max_shared 个 flow 当 core 的类视为公共类，不计算 owner）
  2. 每个场景的 involved_domains = call_path 中所有类（含 entry）非公共 primary_owner 的集合
  3. len(involved_domains) >= 2 → 跨模块，保留

输入: business_flow/business_scenarios.json 或通过 --input 指定
输出: business_flow/output/_cross_domain_scenarios.meta.json

运行:
    python business_flow/render_scenarios_meta.py
    python business_flow/render_scenarios_meta.py --input business_flow/business_scenarios_lottery.json
    python business_flow/render_scenarios_meta.py --no-cross-domain-only   # 调试：不做过滤
    python business_flow/render_scenarios_meta.py --max-shared 5            # 放宽公共类阈值
"""
import argparse
import asyncio
import json
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from interfaces.neo4j_interface import Neo4jInterface
from business_flow.overview_generator import (
    extract_flow_facts, build_primary_class_ownership,
)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BF_DIR = os.path.join(PROJECT_ROOT, "business_flow")
INPUT_PATH = os.path.join(BF_DIR, "business_scenarios.json")
OUTPUT_DIR = os.path.join(BF_DIR, "output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "_cross_domain_scenarios.meta.json")
SPAN_PATH = os.path.join(BF_DIR, "business_flows_with_span.json")
LOG_DIR = os.path.join(BF_DIR, "logs")

# domain 参与方 box 的配色（低饱和度，只是视觉分组）
_DOMAIN_BOX_COLORS = [
    "rgb(220,240,255)", "rgb(255,240,220)", "rgb(240,255,220)",
    "rgb(255,220,240)", "rgb(220,255,245)", "rgb(245,220,255)",
    "rgb(230,230,230)", "rgb(255,250,200)", "rgb(210,240,210)",
]


def setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"render_scenarios_{ts}.log")
    logger = logging.getLogger("business_flow.render_scenarios")
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
# 数据加载 + domain ownership
# ============================================================

def load_span_flows(span_path: str) -> List[Dict]:
    if not os.path.isfile(span_path):
        raise FileNotFoundError(span_path)
    with open(span_path, encoding="utf-8") as f:
        return json.load(f).get("flows", [])


def build_domain_ownership(span_flows: List[Dict], max_shared: int,
                             logger: logging.Logger) -> Dict[str, str]:
    """(legacy) class_id → primary_domain。纯复用 overview_generator，
    会把业务核心实体（@TableName）误当公共类剔除。保留仅作对照用。"""
    flow_facts = [extract_flow_facts(f) for f in span_flows]
    return build_primary_class_ownership(flow_facts, max_shared, logger)


async def fetch_entity_class_ids(neo4j) -> Set[str]:
    """查 Neo4j 里所有带 @TableName 注解的 Class，视为业务核心实体。"""
    rows = await neo4j.execute_query("""
        MATCH (c:Class)-[:ANNOTATED_BY]->(a:Annotation {name: 'TableName'})
        RETURN DISTINCT c.nodeId AS nodeId
    """)
    return {str(r["nodeId"]) for r in rows}


def build_entity_aware_ownership(
    span_flows: List[Dict],
    max_shared: int,
    entity_ids: Set[str],
    logger: logging.Logger,
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """增强版 ownership：
    - 非实体类沿用 overview_generator 的 `build_primary_class_ownership`
    - 被 max_shared 剔除的 @TableName 业务核心实体，用 **"同名前缀 sibling 类的 ownership 众数"**
      推断归属。例如 `WlxIntegral` 被剔除时，找 `WlxIntegralRecord` / `WlxIntegralMapper` /
      `WlxIntegralServiceImpl` 等 sibling 的 ownership，取出现最多的那个 flow 作为它的 primary owner。
      背后假设：**一个实体的归属 ≈ 围绕它的 Mapper/Service 的归属**，业务聚合通常一致。
    - sibling 匹配失败时，fallback 到 `depth 最浅 + flow_size 最小` 的原始启发式。
    """
    flow_facts = [extract_flow_facts(f) for f in span_flows]

    # 1. 先跑原算法得到基础归属（实体类里被 max_shared 剔除的不出现在这）
    base_ownership = build_primary_class_ownership(flow_facts, max_shared, logger)

    # 2. 用于 fallback 的 depth / flow_size 数据
    class_flow_depth: Dict[str, Dict[str, int]] = defaultdict(dict)
    for f in flow_facts:
        for cid, depth in f["class_id_to_depth"].items():
            class_flow_depth[cid][f["name"]] = depth
    flow_size: Dict[str, int] = {f["name"]: len(f["core_class_ids"]) for f in flow_facts}
    id_to_name: Dict[str, str] = {}
    for f in flow_facts:
        id_to_name.update(f["class_id_to_name"])

    # 3. 预建 name → cid 反向索引（用于 sibling 匹配时看整体 name 空间）
    name_to_owners: Dict[str, List[str]] = defaultdict(list)
    for cid, owner in base_ownership.items():
        name = id_to_name.get(cid, "")
        if name:
            name_to_owners[name].append(owner)

    # 4. 对每个未归属的 entity 做 sibling 匹配 / fallback
    added_by_sibling: List[Tuple[str, str, Dict[str, int]]] = []
    added_by_fallback: List[Tuple[str, str, int]] = []
    unresolved: List[str] = []

    for cid in entity_ids:
        if cid in base_ownership:
            continue
        entity_name = id_to_name.get(cid, "")
        if not entity_name:
            unresolved.append(cid)
            continue

        # sibling 匹配：找所有 name 以 entity_name 开头但不等于 entity_name 的已归属类
        sibling_owner_votes: Dict[str, int] = defaultdict(int)
        for other_name, owners in name_to_owners.items():
            if other_name == entity_name:
                continue
            if other_name.startswith(entity_name):
                for o in owners:
                    sibling_owner_votes[o] += 1

        if sibling_owner_votes:
            # 取票数最多的 flow；平票时选 flow_size 最小的
            primary = max(
                sibling_owner_votes.keys(),
                key=lambda f: (sibling_owner_votes[f], -flow_size.get(f, 99999)),
            )
            base_ownership[cid] = primary
            added_by_sibling.append((entity_name, primary, dict(sibling_owner_votes)))
            continue

        # fallback：原启发式
        depth_map = class_flow_depth.get(cid, {})
        if not depth_map:
            unresolved.append(entity_name)
            continue
        primary = min(
            depth_map.keys(),
            key=lambda fname: (depth_map[fname], flow_size.get(fname, 99999)),
        )
        base_ownership[cid] = primary
        added_by_fallback.append((entity_name, primary, len(depth_map)))

    logger.info(
        f"Entity-aware ownership: Neo4j 有 {len(entity_ids)} 个 @TableName 实体类，"
        f"原算法覆盖 {len([e for e in entity_ids if e in base_ownership]) - len(added_by_sibling) - len(added_by_fallback)}, "
        f"sibling 匹配新补 {len(added_by_sibling)}, fallback 补 {len(added_by_fallback)}, "
        f"未归属 {len(unresolved)}"
    )
    if added_by_sibling:
        logger.info("sibling 匹配补的实体（前 15）：")
        for name, primary, votes in added_by_sibling[:15]:
            votes_str = ", ".join(f"{f}:{c}" for f, c in
                                   sorted(votes.items(), key=lambda x: -x[1])[:3])
            logger.info(f"  {name:30s} → {primary}  (votes: {votes_str})")
    if added_by_fallback:
        logger.info("fallback 补的实体（前 10）：")
        for name, primary, n_shared in added_by_fallback[:10]:
            logger.info(f"  {name:30s} → {primary}  (fallback, 共享 {n_shared} flow)")
    if unresolved:
        logger.info(f"未归属: {unresolved[:10]}")
    return base_ownership, id_to_name


def enrich_ownership_via_sibling_prefix(
    ownership: Dict[str, str],
    id_to_name: Dict[str, str],
    class_to_node: Dict[str, Dict[str, Any]],
    logger: logging.Logger,
) -> Dict[str, str]:
    """对 scenarios 涉及但未归属的类（典型：Mapper Interface 被 span 排除在 core_class_ids 外），
    用去掉常见层后缀的前缀反查已归属类，取 owner 众数。

    例：`WlxIntegralMapper` → prefix=`WlxIntegral` → sibling `WlxIntegralRecordServiceImpl` /
    `WlxIntegralRecord` / `WlxIntegral` 都在积分任务流 → 归积分任务流。
    """
    SUFFIXES = ["ServiceImpl", "Service", "Mapper", "Dao", "Repository"]

    # name → owner 反向索引（仅来自已归属 cid）
    name_to_owner: Dict[str, str] = {}
    for cid, owner in ownership.items():
        nm = id_to_name.get(cid)
        if nm:
            name_to_owner[nm] = owner

    def derive_prefix(cls_name: str) -> str:
        for s in SUFFIXES:
            if cls_name.endswith(s) and len(cls_name) > len(s) + 3:
                return cls_name[:-len(s)]
        return cls_name

    added: List[Tuple[str, str, Dict[str, int]]] = []
    no_sibling: List[str] = []
    for cls_name, info in class_to_node.items():
        nid = info.get("nodeId")
        if not nid or nid in ownership:
            continue
        prefix = derive_prefix(cls_name)
        if len(prefix) < 5:
            continue
        votes: Dict[str, int] = defaultdict(int)
        for sib_name, sib_owner in name_to_owner.items():
            if sib_name == cls_name:
                continue
            if sib_name.startswith(prefix):
                votes[sib_owner] += 1
        if votes:
            # 取票数最多；平票选第一个（dict 序）
            primary = max(votes.items(), key=lambda x: x[1])[0]
            ownership[nid] = primary
            added.append((cls_name, primary, dict(votes)))
        else:
            no_sibling.append(cls_name)

    logger.info(
        f"Sibling-prefix 兜底: 新增 {len(added)} 个类的归属"
        f"（主要是 Interface Mapper），仍无 sibling: {len(no_sibling)}"
    )
    for name, owner, votes in added[:15]:
        top = dict(sorted(votes.items(), key=lambda x: -x[1])[:3])
        logger.info(f"  {name:35s} → {owner}  (votes: {top})")
    if no_sibling:
        logger.info(f"  仍无归属（前 5）: {no_sibling[:5]}")
    return ownership


def flatten_scenarios(data: Dict) -> List[Dict]:
    flat = []
    for entry in data.get("per_entry_scenarios", []):
        for i, s in enumerate(entry.get("scenarios", [])):
            flat.append({
                **s,
                "_domain": entry["domain"],
                "_kind": entry.get("kind", ""),
                "_entry_class": entry["entry_class"],
                "_entry_method": entry["entry_method"],
                "_entry_method_id": entry["entry_method_id"],
                "_entry_notes": entry.get("entry_notes", ""),
                "_intra_entry_index": i,
            })
    return flat


# ============================================================
# class_name → nodeId（Neo4j 解析）
# ============================================================

def collect_referenced_class_names(scenarios: List[Dict]) -> Set[str]:
    names: Set[str] = set()
    for s in scenarios:
        names.add(s["_entry_class"])
        for step in s.get("call_path") or []:
            n = (step.get("class") or "").strip()
            if n:
                names.add(n)
    return names


async def resolve_classes_to_nodes(
    neo4j, class_names: Set[str], logger: logging.Logger,
) -> Dict[str, Dict[str, Any]]:
    if not class_names:
        return {}
    rows = await neo4j.execute_query("""
        MATCH (c) WHERE c.name IN $names
          AND (c:Class OR c:Interface OR c:Enum OR c:Record)
        OPTIONAL MATCH (f:File)-[:DECLARES]->(c)
        RETURN c.name AS name, c.nodeId AS nodeId,
               labels(c)[0] AS label, f.name AS file_name
    """, {"names": list(class_names)})
    label_pri = {"Class": 0, "Record": 1, "Enum": 2, "Interface": 3}
    result: Dict[str, Dict[str, Any]] = {}
    collisions: Dict[str, List[str]] = defaultdict(list)
    for r in rows:
        name = r["name"]
        lp = label_pri.get(r["label"], 9)
        collisions[name].append(f"{r['label']}#{r['nodeId']}")
        existing = result.get(name)
        if not existing or label_pri.get(existing["label"], 9) > lp:
            result[name] = {
                "nodeId": str(r["nodeId"]),
                "label": r["label"],
                "file_name": r["file_name"] or "",
            }
    multi = [(n, c) for n, c in collisions.items() if len(c) > 1]
    if multi:
        logger.info(f"{len(multi)} 个类名有多候选，按 Class>Record>Enum>Interface 优先级选取")
    return result


# ============================================================
# 跨模块判据：involved_domains 计算
# ============================================================

def compute_involved_domains(
    scenario: Dict,
    class_to_node: Dict[str, Dict[str, Any]],
    ownership: Dict[str, str],
) -> Set[str]:
    """返回场景触达的 primary_domain 集合（不含公共类）"""
    domains: Set[str] = set()

    def add_class(cls_name: str):
        info = class_to_node.get(cls_name)
        if not info:
            return
        d = ownership.get(info["nodeId"])
        if d:
            domains.add(d)

    add_class(scenario["_entry_class"])
    for step in scenario.get("call_path") or []:
        cls = (step.get("class") or "").strip()
        if cls:
            add_class(cls)
    return domains


def annotate_and_filter_cross_domain(
    scenarios: List[Dict],
    class_to_node: Dict[str, Dict[str, Any]],
    ownership: Dict[str, str],
    cross_domain_only: bool,
    logger: logging.Logger,
) -> List[Dict]:
    """给每个场景标 _involved_domains，按 cross_domain_only 决定是否过滤"""
    kept: List[Dict] = []
    skipped_single: int = 0
    skipped_no_owner: int = 0
    for s in scenarios:
        doms = compute_involved_domains(s, class_to_node, ownership)
        s["_involved_domains"] = sorted(doms)
        if not cross_domain_only:
            kept.append(s)
            continue
        if len(doms) == 0:
            skipped_no_owner += 1
            continue
        if len(doms) < 2:
            skipped_single += 1
            continue
        kept.append(s)

    logger.info(
        f"跨模块过滤: {len(kept)} 保留 / "
        f"{skipped_single} 单域跳过 / {skipped_no_owner} 无 owner 跳过"
    )
    if kept:
        # 组合统计
        combos: Dict[Tuple[str, ...], int] = defaultdict(int)
        for s in kept:
            combos[tuple(s["_involved_domains"])] += 1
        top = sorted(combos.items(), key=lambda x: -x[1])[:10]
        logger.info(f"跨模块 domain 组合 Top 10:")
        for doms, cnt in top:
            logger.info(f"  {cnt:3d}  {' × '.join(doms)}")
    return kept


def sort_scenarios(scenarios: List[Dict], domain_order: List[str]) -> List[Dict]:
    conf_rank = {"high": 0, "medium": 1, "low": 2}
    dom_rank = {d: i for i, d in enumerate(domain_order)}
    return sorted(scenarios, key=lambda s: (
        len(s["_involved_domains"]),          # 跨越更多 domain 的排前面
        dom_rank.get(s["_domain"], 999),
        conf_rank.get(s.get("confidence", "low"), 3),
        s["_entry_class"],
        s["_intra_entry_index"],
    ), reverse=False)


# ============================================================
# Mermaid 渲染
# ============================================================

def _role_label(class_name: str) -> str:
    if class_name.endswith("Controller"):
        return "Controller"
    if class_name.endswith("ServiceImpl") or class_name.endswith("Service"):
        return "Service"
    if class_name.endswith("Mapper") or class_name.endswith("Dao") \
            or class_name.endswith("Repository"):
        return "DAO"
    return ""


def _short_pid(name: str, used: Dict[str, str]) -> str:
    if name in used:
        return used[name]
    alpha = re.findall(r"[A-Z]", name)
    pid_base = "".join(alpha[:4]) if alpha else "P"
    pid = pid_base
    i = 0
    while pid in used.values():
        i += 1
        pid = f"{pid_base}{i}"
    used[name] = pid
    return pid


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


def _escape_mermaid_text(s: str) -> str:
    if not s:
        return ""
    return s.replace("#", "＃").replace(";", "；").replace("<", "＜").replace(">", "＞")


def render_sequence_diagram_boxed(
    scenario: Dict,
    class_to_node: Dict[str, Dict[str, Any]],
    ownership: Dict[str, str],
) -> Tuple[str, Dict[str, str]]:
    """跨模块 sequenceDiagram：按 primary_domain 分 box，跨域调用用粗箭头标记"""
    entry_class = scenario["_entry_class"]
    entry_method = scenario["_entry_method"]
    kind = scenario.get("_kind", "")
    call_path = scenario.get("call_path") or []
    writes = scenario.get("writes") or []
    scenario_domain = scenario["_domain"]
    involved = scenario.get("_involved_domains", [])

    trigger_alias = {
        "用户端": "用户", "运营端": "运营",
        "大屏端": "大屏", "定时任务": "Quartz",
    }.get(kind, "触发方")

    # 1. 按出现顺序收集参与类
    ordered_classes: List[str] = [entry_class]
    seen = {entry_class}
    for step in call_path:
        cls = (step.get("class") or "").strip()
        if cls and cls not in seen:
            seen.add(cls)
            ordered_classes.append(cls)

    # 2. 按 primary_domain 把类分组；无 owner 的类放到 "公共/工具" 组
    def domain_of(cls: str) -> str:
        info = class_to_node.get(cls)
        if not info:
            return "—未解析—"
        return ownership.get(info["nodeId"]) or "公共/工具"

    class_domain: Dict[str, str] = {cls: domain_of(cls) for cls in ordered_classes}

    # 按涉及 domain 的出现顺序排（entry_class 所在 domain 优先）
    domain_order: List[str] = []
    for cls in ordered_classes:
        d = class_domain[cls]
        if d not in domain_order:
            domain_order.append(d)

    # 3. 颜色分配
    domain_colors: Dict[str, str] = {}
    for i, d in enumerate(domain_order):
        if d == "公共/工具":
            domain_colors[d] = "rgb(240,240,240)"
        else:
            domain_colors[d] = _DOMAIN_BOX_COLORS[i % len(_DOMAIN_BOX_COLORS)]

    # 4. 生成 participant 声明（按 box 分组）
    used: Dict[str, str] = {}
    mapping: Dict[str, str] = {}
    lines = ["sequenceDiagram", "    autonumber", f"    participant U as {trigger_alias}"]

    for d in domain_order:
        classes_in_d = [c for c in ordered_classes if class_domain[c] == d]
        if not classes_in_d:
            continue
        color = domain_colors[d]
        lines.append(f'    box {color} {_escape_mermaid_text(d)}')
        for cls in classes_in_d:
            pid = _short_pid(cls, used)
            role = _role_label(cls)
            label = _escape_mermaid_text(cls) + (f" ({role})" if role else "")
            lines.append(f'        participant {pid} as {label}')
            info = class_to_node.get(cls)
            if info:
                mapping[pid] = info["nodeId"]
        lines.append("    end")

    # 5. 画调用
    entry_pid = used[entry_class]
    lines.append(f'    U ->> {entry_pid}: {_escape_mermaid_text(entry_method)}')

    # 跳过 call_path[0] 如果是 entry 方法本身
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

    # caller tracking：Controller→Service 后，DAO 全由 Service 发起
    caller_pid = entry_pid
    caller_domain = class_domain[entry_class]
    for step in filtered:
        cls = step["class"]
        mth = step["method"]
        role = (step.get("role") or "").lower()
        callee_pid = used.get(cls)
        if not callee_pid:
            continue
        callee_domain = class_domain[cls]
        is_cross = callee_domain != caller_domain and \
                   callee_domain != "公共/工具" and caller_domain != "公共/工具"
        # 跨域调用用 `->>+`（粗箭头）吸引注意
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
            # 跨域 DAO 调用结束后立即 return（避免激活栈变黄）
            if is_cross:
                lines.append(f'    {callee_pid} -->>- {caller_pid}: ')
        if role != "dao":
            caller_pid = callee_pid
            caller_domain = callee_domain

    return "\n".join(lines), mapping


def render_state_diagram(scenario: Dict) -> Optional[str]:
    st = scenario.get("state_transitions") or []
    if not st:
        return None
    lines = ["stateDiagram-v2", "    direction LR"]
    state_ids: Dict[str, str] = {}

    def sid(label: str) -> str:
        if label in state_ids:
            return state_ids[label]
        pid = f"s{len(state_ids)}"
        state_ids[label] = pid
        return pid

    def fmt_label(s: str) -> str:
        return _escape_mermaid_text(s).replace(":", "=")

    decls: List[str] = []
    edges: List[str] = []
    for t in st:
        entity = t.get("entity", "") or "?"
        field = t.get("field", "") or "?"
        f = t.get("from") or "初始"
        to = t.get("to") or "?"
        from_label = fmt_label(f"{entity}.{field}={f}")
        to_label = fmt_label(f"{entity}.{field}={to}")
        from_id = sid(from_label)
        to_id = sid(to_label)
        decls.append(f'    {from_id}: {from_label}')
        decls.append(f'    {to_id}: {to_label}')
        edges.append(f'    {from_id} --> {to_id}')
    seen: Set[str] = set()
    for l in decls + edges:
        if l not in seen:
            seen.add(l)
            lines.append(l)
    return "\n".join(lines)


# ============================================================
# Markdown 生成
# ============================================================

CONF_BADGE = {
    "high": "🟢 **high**",
    "medium": "🟡 medium",
    "low": "🔴 low",
}


def render_overview_md(
    scenarios: List[Dict],
    total_before_filter: int,
    span_domains: List[str],
    ownership: Dict[str, str],
    max_shared: int,
) -> str:
    n_scenarios = len(scenarios)
    n_domains_covered = len({d for s in scenarios for d in s["_involved_domains"]})
    cross_counts = defaultdict(int)  # domain → 参与了多少个跨模块场景
    combo_counts: Dict[Tuple[str, ...], int] = defaultdict(int)
    for s in scenarios:
        for d in s["_involved_domains"]:
            cross_counts[d] += 1
        combo_counts[tuple(s["_involved_domains"])] += 1

    parts = [
        "# 跨模块端到端业务场景",
        "",
        f"本页只列出**真正跨多个业务域**的端到端业务场景 —— 即一次 HTTP 入口触发的调用链里，",
        f"会**触达 ≥2 个业务域**（如「用户兑换奖品」入口在奖品兑换流，但会触达积分任务流扣积分 + 站内消息流发通知）。",
        "",
        f"判据：用 `business_flows_with_span.json` 里每个域的 `core_class_ids`，算出每个类的 primary_owner domain",
        f"（共享 > **{max_shared}** 个 flow 的类视为公共工具类、不算 domain 触达）。",
        f"场景的 `call_path` 中涉及 ≥2 个 primary domain 即判定为跨模块。",
        "",
        f"## 概览",
        "",
        f"- 输入场景总数: **{total_before_filter}**",
        f"- **跨模块场景**: **{n_scenarios}** (占 {n_scenarios/max(total_before_filter,1)*100:.1f}%)",
        f"- 涉及 domain: **{n_domains_covered}** 个",
        "",
    ]

    # domain 参与度 Top 10
    if cross_counts:
        parts.append("## 跨模块参与度 Top 10")
        parts.append("")
        parts.append("| 业务域 | 参与跨模块场景数 |")
        parts.append("|---|---|")
        for d, cnt in sorted(cross_counts.items(), key=lambda x: -x[1])[:10]:
            parts.append(f"| `{d}` | {cnt} |")
        parts.append("")

    # Top 场景组合
    if combo_counts:
        parts.append("## 常见跨域组合 Top 10")
        parts.append("")
        parts.append("| 触达的 domain 组合 | 场景数 |")
        parts.append("|---|---|")
        for combo, cnt in sorted(combo_counts.items(), key=lambda x: -x[1])[:10]:
            parts.append(f"| {' ✕ '.join(f'`{d}`' for d in combo)} | {cnt} |")
        parts.append("")

    # 场景目录
    parts.append("## 场景目录")
    parts.append("")
    parts.append("> 按跨越的 domain 数量降序排列。")
    parts.append("")
    for s in scenarios:
        conf = CONF_BADGE.get(s.get("confidence", "low"), "")
        doms = " ✕ ".join(f"`{d}`" for d in s["_involved_domains"])
        parts.append(
            f'- 场景 {s["_display_idx"]}：**{s.get("scenario_name","?")}** — '
            f'{conf} — 跨 {len(s["_involved_domains"])} 域（{doms}）'
        )
    parts.append("")
    return "\n".join(parts)


def render_scenario_header_md(scenario: Dict, idx: int) -> str:
    conf = CONF_BADGE.get(
        scenario.get("confidence", "low"),
        scenario.get("confidence", "low"),
    )
    doms = " ✕ ".join(f"`{d}`" for d in scenario["_involved_domains"])
    return "\n".join([
        f'### 场景 {idx}：{scenario.get("scenario_name", "?")}',
        "",
        f'**入口** `{scenario["_entry_class"]}.{scenario["_entry_method"]}` '
        f'({scenario.get("_kind","")}) · '
        f'**触发** {scenario.get("trigger_condition","")} · '
        f'**置信度** {conf}',
        "",
        f'**触达域**（{len(scenario["_involved_domains"])} 个）：{doms}',
        "",
        scenario.get("description", ""),
    ])


def render_writes_by_domain_md(
    scenario: Dict,
    class_to_node: Dict[str, Dict[str, Any]],
    ownership: Dict[str, str],
) -> Optional[str]:
    """写操作按 primary_domain 分组展示"""
    writes = scenario.get("writes") or []
    if not writes:
        return None
    # 从 call_path 里找每个 write 对应的 DAO class；再查 owner
    call_path = scenario.get("call_path") or []
    dao_classes = [step.get("class", "") for step in call_path
                   if (step.get("role") or "").lower() == "dao"]

    def write_domain(w: Dict) -> str:
        target = (w.get("target") or "").lower()
        # 先按 target 字符串匹配 DAO class name
        for c in dao_classes:
            cl = c.lower()
            if target and (target in cl or cl.replace("mapper", "") in target):
                info = class_to_node.get(c)
                if info:
                    return ownership.get(info["nodeId"]) or "公共/工具"
        # 兜底：找第一个 DAO 的 domain
        for c in dao_classes:
            info = class_to_node.get(c)
            if info:
                return ownership.get(info["nodeId"]) or "公共/工具"
        return "—"

    by_domain: Dict[str, List[Dict]] = defaultdict(list)
    for w in writes:
        by_domain[write_domain(w)].append(w)

    parts = ["#### 写操作足迹"]
    parts.append("")
    parts.append("| 所属域 | 类型 | 目标 | 操作 |")
    parts.append("|---|---|---|---|")
    for d in sorted(by_domain.keys()):
        for w in by_domain[d]:
            parts.append(
                f"| `{d}` | {w.get('kind','?')} | `{w.get('target','?')}` | {w.get('op','?')} |"
            )
    return "\n".join(parts)


def render_entry_notes_md(scenario: Dict) -> Optional[str]:
    notes = (scenario.get("_entry_notes") or "").strip()
    if not notes:
        return None
    return "\n".join([
        "#### 审计备注",
        "",
        f"> {notes}",
    ])


# ============================================================
# 拼装 meta.json
# ============================================================

def build_wiki_entries(
    scenarios: List[Dict],
    class_to_node: Dict[str, Dict[str, Any]],
    ownership: Dict[str, str],
    total_before_filter: int,
    span_domains: List[str],
    max_shared: int,
) -> Tuple[List[Dict], List[Dict]]:
    for i, s in enumerate(scenarios, 1):
        s["_display_idx"] = i

    wiki: List[Dict] = []

    # 1. 概览
    wiki.append({
        "markdown": render_overview_md(
            scenarios, total_before_filter, span_domains, ownership, max_shared,
        ),
        "neo4j_id": {"0": []},
    })

    # 2. 每场景：header → seq → writes_by_domain → state → notes
    seen_entry_notes: Set[Tuple[str, int]] = set()
    for s in scenarios:
        idx = s["_display_idx"]
        nid = {}
        if s.get("_entry_method_id"):
            nid[str(idx)] = [str(s["_entry_method_id"])]
        wiki.append({"markdown": render_scenario_header_md(s, idx), "neo4j_id": nid})

        seq_src, seq_mapping = render_sequence_diagram_boxed(
            s, class_to_node, ownership,
        )
        wiki.append({
            "mermaid": f"```mermaid\n{seq_src}\n```",
            "mapping": seq_mapping,
        })

        writes_md = render_writes_by_domain_md(s, class_to_node, ownership)
        if writes_md:
            wiki.append({"markdown": writes_md, "neo4j_id": {}})

        state_src = render_state_diagram(s)
        if state_src:
            wiki.append({
                "mermaid": f"```mermaid\n{state_src}\n```",
                "mapping": {},
            })

        entry_key = (s["_domain"], s["_entry_method_id"])
        if entry_key not in seen_entry_notes:
            seen_entry_notes.add(entry_key)
            notes_md = render_entry_notes_md(s)
            if notes_md:
                wiki.append({"markdown": notes_md, "neo4j_id": {}})

    # source_id_list
    source_id_list: List[Dict] = []
    seen_ids: Set[str] = set()
    for name, info in class_to_node.items():
        nid = info.get("nodeId")
        if not nid or nid in seen_ids or not info.get("file_name"):
            continue
        seen_ids.add(nid)
        source_id_list.append({
            "source_id": nid,
            "name": info["file_name"],
            "lines": [],
        })

    return wiki, source_id_list


# ============================================================
# 主流程
# ============================================================

async def main():
    parser = argparse.ArgumentParser(description="渲染跨模块端到端场景为 meta.json")
    parser.add_argument("--input", default=INPUT_PATH,
                        help="business_scenarios 输入 JSON（可多个，用逗号分隔合并）")
    parser.add_argument("--out", default=OUTPUT_PATH)
    parser.add_argument("--cross-domain-only", dest="cross_domain_only",
                        action="store_true", default=True,
                        help="(默认) 只保留跨 ≥2 域的场景")
    parser.add_argument("--no-cross-domain-only", dest="cross_domain_only",
                        action="store_false",
                        help="不过滤，所有场景都输出（调试用）")
    parser.add_argument("--max-shared", type=int, default=3,
                        help="公共类阈值：被 > N 个 flow 当 core 的类视为公共工具（默认 3）")
    parser.add_argument("--span-path", default=SPAN_PATH,
                        help="business_flows_with_span.json 路径")
    args = parser.parse_args()

    logger = setup_logger()

    # 读输入（支持多文件合并）
    input_paths = [p.strip() for p in args.input.split(",") if p.strip()]
    merged: Dict[str, Any] = {"per_entry_scenarios": []}
    for p in input_paths:
        if not os.path.isfile(p):
            logger.error(f"输入文件不存在: {p}")
            sys.exit(1)
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        merged["per_entry_scenarios"].extend(data.get("per_entry_scenarios", []))
        logger.info(f"loaded {p}: {len(data.get('per_entry_scenarios', []))} entries")

    scenarios = flatten_scenarios(merged)
    total_before_filter = len(scenarios)
    logger.info(f"展平得到 {total_before_filter} 个场景")

    # 加载 span
    span_flows = load_span_flows(args.span_path)
    span_domains = [f["name"] for f in span_flows]

    # 连 Neo4j：1) 取 @TableName 实体类列表 2) 解析 class_name → nodeId
    class_names = collect_referenced_class_names(scenarios)
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
    finally:
        neo4j.close()
    logger.info(f"类解析: {len(class_to_node)}/{len(class_names)} 命中")

    # 算 ownership（entity-aware 版本：@TableName 实体绕过 max_shared 过滤）
    ownership, id_to_name = build_entity_aware_ownership(
        span_flows, args.max_shared, entity_ids, logger,
    )

    # 兜底：scenarios 里出现但 ownership 缺失的类（典型是 Mapper Interface），
    # 用 sibling-prefix 反查已归属类的 owner 众数
    ownership = enrich_ownership_via_sibling_prefix(
        ownership, id_to_name, class_to_node, logger,
    )

    # 过滤 + 排序
    scenarios = annotate_and_filter_cross_domain(
        scenarios, class_to_node, ownership, args.cross_domain_only, logger,
    )
    scenarios = sort_scenarios(scenarios, span_domains)
    # 跨越 domain 数量多的排前面
    scenarios.sort(key=lambda s: -len(s["_involved_domains"]))

    if not scenarios:
        logger.warning("过滤后无场景。如要调试可加 --no-cross-domain-only")
        sys.exit(0)

    wiki, source_id_list = build_wiki_entries(
        scenarios, class_to_node, ownership,
        total_before_filter, span_domains, args.max_shared,
    )

    meta = {"wiki": wiki, "source_id_list": source_id_list}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    logger.info(f"写入 {args.out}")
    logger.info(f"wiki entries: {len(wiki)} / source_id_list: {len(source_id_list)}")


if __name__ == "__main__":
    asyncio.run(main())
