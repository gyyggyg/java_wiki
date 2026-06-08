"""业务流总览生成器 —— 跨流依赖视图（视角 B）

目标：展示 26 个业务流之间的调用依赖（"flow A 的代码调用了 flow B 的核心 Service"）。

思路：
1. 从 business_flows_with_span.json 读每个 flow 的 entry_methods + core_classes
2. 构建 class_id → owner_flow 归属映射（排除在多个 flow 里都出现的"共享工具类"）
3. 对每个 flow F，查 Neo4j 里 F 的 entry_methods 的下游 CALLS 边（1-2 跳），
   收集被调用方法所属的类 id
4. 若目标类的 owner 是另一个 flow G，则登记一条 F → G 的依赖边（附带调用次数作为权重）
5. 按权重阈值过滤后，输出 mermaid `graph LR` 视图

用法:
    python business_flow/overview_generator.py
    python business_flow/overview_generator.py --min-weight 3
    python business_flow/overview_generator.py --max-shared 2   # 类归属共享阈值（默认 3）
    python business_flow/overview_generator.py --no-llm          # 不调 LLM 写说明，纯图表
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from interfaces.neo4j_interface import Neo4jInterface
from interfaces.llm_interface import LLMInterface
from business_flow.llm_client import set_default_llm, invoke_llm_markdown

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BF_DIR = os.path.join(PROJECT_ROOT, "business_flow")
INPUT_PATH = os.path.join(BF_DIR, "business_flows_with_span.json")
OUTPUT_FLOW_DIR = os.path.join(BF_DIR, "claude", "output_flow")  # 已生成 meta 的目录
LOG_DIR = os.path.join(BF_DIR, "logs")


def setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"overview_{ts}.log")
    logger = logging.getLogger("business_flow.overview")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    logger.info(f"日志文件: {log_file}")
    return logger


# ============================================================
# 数据加载与归属推断
# ============================================================

def load_flows() -> List[Dict]:
    """读 business_flows_with_span.json 的 flows 列表。"""
    if not os.path.isfile(INPUT_PATH):
        raise FileNotFoundError(INPUT_PATH)
    with open(INPUT_PATH, encoding="utf-8") as f:
        return json.load(f).get("flows", [])


def filter_generated_flows(flows: List[Dict], logger: logging.Logger) -> List[Dict]:
    """只保留已在 output_flow/ 里生成 meta.json 的 flow；其余忽略。"""
    if not os.path.isdir(OUTPUT_FLOW_DIR):
        logger.warning(f"未找到 output_flow 目录: {OUTPUT_FLOW_DIR}，使用全部 flow")
        return flows

    generated_stems: Set[str] = {
        p.stem.replace(".meta", "")
        for p in Path(OUTPUT_FLOW_DIR).glob("*.meta.json")
    }

    def norm(name: str) -> str:
        # 生成文件时去掉末尾"流"字，这里做对应反推
        stem = name
        if stem.endswith("流"):
            stem = stem[:-1]
        return stem

    kept = [f for f in flows if norm(f.get("name", "")) in generated_stems]
    logger.info(
        f"flows 总数 {len(flows)}，已生成 meta 的 {len(kept)} 个 flow："
        f"{[f['name'] for f in kept]}"
    )
    return kept


def extract_flow_facts(flow: Dict) -> Dict:
    """抽每个 flow 的关键信息：entry_method_ids / core_class_ids / core_class_names / class_id_to_depth。"""
    entry_method_ids: Set[str] = {
        str(e["node_id"]) for e in flow.get("entry_methods", []) if e.get("node_id") is not None
    }
    core_classes = flow.get("span", {}).get("core_classes_detail", []) or []
    core_class_ids: Set[str] = {
        str(c["class_id"]) for c in core_classes if c.get("class_id") is not None
    }
    class_id_to_name: Dict[str, str] = {
        str(c["class_id"]): c.get("class_name", "")
        for c in core_classes
        if c.get("class_id") is not None
    }
    # depth：该类在本 flow 的"入链深度"（0=Controller 本身，1=被 Controller 调用的一跳，以此类推）
    class_id_to_depth: Dict[str, int] = {
        str(c["class_id"]): int(c.get("depth", 999))
        for c in core_classes
        if c.get("class_id") is not None
    }
    return {
        "name": flow["name"],
        "kind": flow.get("kind", ""),
        "entry_method_ids": entry_method_ids,
        "core_class_ids": core_class_ids,
        "class_id_to_name": class_id_to_name,
        "class_id_to_depth": class_id_to_depth,
    }


def build_primary_class_ownership(
    flow_facts: List[Dict],
    max_shared: int,
    logger: logging.Logger,
) -> Dict[str, str]:
    """给每个类选出**唯一的 primary owner flow**。

    规则（按优先级）：
    1. 若类被 > max_shared 个 flow 共享 → 视为公共类，**不归属**（从结果中剔除）
    2. 否则在共享的 flow 中选：
       a) depth 最浅的（depth=0 的 Controller > depth=1 的 Service > depth=2 的 Mapper...）
       b) depth 平手时，选 core_classes 总数最少的 flow（最"专精"的那个）

    Returns:
        class_id → primary_flow_name  （共享类不出现在结果中）
    """
    # 收集每个类在各 flow 里的 depth
    class_flow_depth: Dict[str, Dict[str, int]] = defaultdict(dict)
    for f in flow_facts:
        for cid, depth in f["class_id_to_depth"].items():
            class_flow_depth[cid][f["name"]] = depth

    flow_size: Dict[str, int] = {f["name"]: len(f["core_class_ids"]) for f in flow_facts}

    ownership: Dict[str, str] = {}
    public_classes: List[Tuple[str, int]] = []
    id_to_name: Dict[str, str] = {}
    for f in flow_facts:
        id_to_name.update(f["class_id_to_name"])

    for cid, depth_map in class_flow_depth.items():
        if len(depth_map) > max_shared:
            public_classes.append((cid, len(depth_map)))
            continue
        # 选 depth 最浅 + 平手选 flow_size 最小
        primary = min(
            depth_map.keys(),
            key=lambda f: (depth_map[f], flow_size.get(f, 99999)),
        )
        ownership[cid] = primary

    logger.info(
        f"类 primary 归属: 总 {len(class_flow_depth)} 个类，"
        f"{len(ownership)} 个有唯一 primary owner，"
        f"{len(public_classes)} 个公共类（共享 > {max_shared} flow）被剔除"
    )
    if public_classes[:10]:
        public_classes.sort(key=lambda x: -x[1])
        names = [(id_to_name.get(cid, cid), n) for cid, n in public_classes[:10]]
        logger.info(f"前 10 个公共类: {names}")
    return ownership


def build_class_ownership(
    flow_facts: List[Dict],
    max_shared: int,
    logger: logging.Logger,
) -> Dict[str, Set[str]]:
    """class_id → {flow_name, ...}；在 > max_shared 个 flow 里出现的类视为公共工具，**不归属任何 flow**。

    max_shared=3 表示：一个类若出现在 ≤3 个 flow 的 core_classes 里，仍归属这些 flow；
    出现在 4 个及以上则剔除归属（如 `AppUserController` 几乎每个 flow 都有）。
    """
    raw: Dict[str, Set[str]] = defaultdict(set)
    for f in flow_facts:
        for cid in f["core_class_ids"]:
            raw[cid].add(f["name"])

    ownership: Dict[str, Set[str]] = {}
    excluded: List[Tuple[str, int]] = []
    for cid, owners in raw.items():
        if len(owners) <= max_shared:
            ownership[cid] = owners
        else:
            excluded.append((cid, len(owners)))

    excluded.sort(key=lambda x: -x[1])
    logger.info(
        f"类归属构造: 总 {len(raw)} 个类，"
        f"{len(ownership)} 个有归属（共享 ≤ {max_shared} flow），"
        f"{len(excluded)} 个作为公共类被剔除归属"
    )
    if excluded[:10]:
        # 找类名打印便于核对
        id_to_name: Dict[str, str] = {}
        for f in flow_facts:
            id_to_name.update(f["class_id_to_name"])
        names = [(id_to_name.get(cid, cid), n) for cid, n in excluded[:10]]
        logger.info(f"共享度最高的前 10 个被剔除的类: {names}")
    return ownership


# ============================================================
# Neo4j 查询：每个 flow 的下游 CALLS 方法 → 目标类
# ============================================================

async def collect_downstream_class_ids(
    neo4j, entry_method_ids: List[str], max_depth: int,
) -> List[Tuple[str, str]]:
    """对 entry_method_ids 查下游 CALLS（1~max_depth 跳），返回 [(target_class_id, target_method_name), ...]。

    - 跳数 max_depth=1 时只看入口方法直接调用的方法
    - max_depth=2 时还包含 Service 方法内部的调用（覆盖 Controller → Service → OtherService 场景）
    - 用 IMPLEMENTS 展开 Service 接口到 ServiceImpl
    """
    if not entry_method_ids:
        return []
    ids_int = [int(x) for x in entry_method_ids if x.isdigit()]
    if not ids_int:
        return []

    # 变长路径：*1..N
    query = f"""
    MATCH (root:Method) WHERE root.nodeId IN $ids
    MATCH path = (root)-[:CALLS*1..{max_depth}]->(called:Method)
    MATCH (cc)-[:DECLARES]->(called)
    WHERE cc:Class OR cc:Interface
    RETURN DISTINCT cc.nodeId AS target_class_id, called.name AS method_name
    """
    rows = await neo4j.execute_query(query, {"ids": ids_int})
    return [
        (str(r["target_class_id"]), r["method_name"] or "")
        for r in rows
        if r.get("target_class_id") is not None
    ]


async def build_dependency_edges(
    neo4j,
    flow_facts: List[Dict],
    class_ownership: Dict[str, Set[str]],
    max_depth: int,
    logger: logging.Logger,
) -> Dict[Tuple[str, str], Dict]:
    """对每个 flow F，找它调用到的其他 flow G 的类，登记 F→G 依赖边。

    Returns:
        {(src_flow, dst_flow): {"weight": int, "samples": [method_name...]}}
    """
    edges: Dict[Tuple[str, str], Dict] = defaultdict(lambda: {"weight": 0, "samples": []})

    for f in flow_facts:
        f_name = f["name"]
        downstream = await collect_downstream_class_ids(
            neo4j, list(f["entry_method_ids"]), max_depth=max_depth,
        )
        local_edges: Dict[str, int] = defaultdict(int)
        method_samples: Dict[str, List[str]] = defaultdict(list)

        for target_cid, method_name in downstream:
            owners = class_ownership.get(target_cid)
            if not owners:
                continue
            # 去掉自己 flow（自己调自己不算跨流）
            others = owners - {f_name}
            for dst_flow in others:
                local_edges[dst_flow] += 1
                if method_name and method_name not in method_samples[dst_flow]:
                    method_samples[dst_flow].append(method_name)

        for dst_flow, weight in local_edges.items():
            key = (f_name, dst_flow)
            edges[key]["weight"] += weight
            # 取前 3 个方法作为标签
            for m in method_samples[dst_flow][:3]:
                if m not in edges[key]["samples"]:
                    edges[key]["samples"].append(m)

        logger.debug(
            f"{f_name}: 下游触达 {len(downstream)} 条，"
            f"跨流边 {len(local_edges)} 个："
            + ", ".join(f"{d}({w})" for d, w in local_edges.items())
        )

    logger.info(f"跨 flow 依赖边总数: {len(edges)}")
    return dict(edges)


# ============================================================
# Mermaid 渲染
# ============================================================

def compute_degrees(
    edges: Dict[Tuple[str, str], Dict],
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """返回 (in_degree, out_degree)，权重为边 weight 之和。"""
    in_deg: Dict[str, int] = defaultdict(int)
    out_deg: Dict[str, int] = defaultdict(int)
    for (src, dst), info in edges.items():
        out_deg[src] += info["weight"]
        in_deg[dst] += info["weight"]
    return dict(in_deg), dict(out_deg)


def identify_hubs(
    edges: Dict[Tuple[str, str], Dict],
    min_total_degree: int,
    max_hubs: int,
) -> List[str]:
    """按 in+out 总度识别出 hub flow（容易把全图搅乱的超级节点）。

    返回按总度降序排序的 flow 名列表，最多 max_hubs 个。
    """
    in_deg, out_deg = compute_degrees(edges)
    all_flows = set(in_deg) | set(out_deg)
    total = {f: in_deg.get(f, 0) + out_deg.get(f, 0) for f in all_flows}
    hubs = sorted(
        (f for f in all_flows if total[f] >= min_total_degree),
        key=lambda f: -total[f],
    )
    return hubs[:max_hubs]


def _render_edges_mermaid(
    title_hint: str,
    lines: List[str],
    active_flows: List[str],
    edge_list: List[Tuple[Tuple[str, str], Dict]],
    isolated: Optional[List[str]] = None,
) -> str:
    """把节点 + 边列表渲染成一份完整 mermaid graph LR 文本。"""
    fid_map: Dict[str, str] = {}
    def fid(name: str) -> str:
        if name not in fid_map:
            fid_map[name] = f"N{len(fid_map)}"
        return fid_map[name]

    lines.append("graph LR")
    for n in sorted(active_flows):
        lines.append(f'    {fid(n)}["{n}"]')
    if isolated:
        lines.append("")
        lines.append(f'    subgraph 独立["独立（与本图无依赖）"]')
        for n in sorted(isolated):
            lines.append(f'    {fid(n)}["{n}"]')
        lines.append("    end")
    lines.append("")
    for (src, dst), info in edge_list:
        weight = info["weight"]
        samples = info.get("samples") or []
        label = (
            f'|"{" / ".join(samples[:2])} ({weight})"|'
            if samples else f'|"{weight}"|'
        )
        lines.append(f"    {fid(src)} -->{label} {fid(dst)}")
    return "\n".join(lines)


def build_focus_subgraph(
    edges: Dict[Tuple[str, str], Dict],
    center_flow: str,
    min_weight: int,
) -> Tuple[str, int]:
    """为 center_flow 构造一张 1 跳邻居图（该节点的所有入边 + 出边）。

    Returns:
        (mermaid 源码, 这张图保留的边数)
    """
    kept_edges = [
        ((s, d), info)
        for (s, d), info in edges.items()
        if (s == center_flow or d == center_flow) and info["weight"] >= min_weight
    ]
    # 按权重降序
    kept_edges.sort(key=lambda x: -x[1]["weight"])
    active = {center_flow}
    for (s, d), _ in kept_edges:
        active.add(s); active.add(d)

    mermaid = _render_edges_mermaid(
        title_hint=center_flow,
        lines=[],
        active_flows=list(active),
        edge_list=kept_edges,
    )
    return mermaid, len(kept_edges)


def build_main_business_graph(
    flow_facts: List[Dict],
    edges: Dict[Tuple[str, str], Dict],
    hubs: Set[str],
    min_weight: int,
    top_n: int,
) -> Tuple[str, int]:
    """拆出"业务协作主图"：排除所有 hub flow 的边 + 按 top_n 限流。"""
    # 排除任一端点是 hub 的边
    non_hub_edges = [
        ((s, d), info)
        for (s, d), info in edges.items()
        if s not in hubs and d not in hubs and info["weight"] >= min_weight
    ]
    non_hub_edges.sort(key=lambda x: -x[1]["weight"])

    # top_n 出度限制
    count_by_src: Dict[str, int] = defaultdict(int)
    final_edges: List[Tuple[Tuple[str, str], Dict]] = []
    for (s, d), info in non_hub_edges:
        if count_by_src[s] >= top_n:
            continue
        count_by_src[s] += 1
        final_edges.append(((s, d), info))

    active_flows: Set[str] = set()
    for (s, d), _ in final_edges:
        active_flows.add(s); active_flows.add(d)

    # 非 hub 且没出现在边里 → 作为孤立节点
    non_hub_flows = {f["name"] for f in flow_facts if f["name"] not in hubs}
    isolated = non_hub_flows - active_flows

    mermaid = _render_edges_mermaid(
        title_hint="main",
        lines=[],
        active_flows=list(active_flows),
        edge_list=final_edges,
        isolated=list(isolated),
    )
    return mermaid, len(final_edges)


def build_mermaid_graph(
    flow_facts: List[Dict],
    edges: Dict[Tuple[str, str], Dict],
    min_weight: int,
    top_n: int,
) -> Tuple[str, List[Tuple[Tuple[str, str], Dict]]]:
    """输出 mermaid `graph LR`。只画 weight >= min_weight 的边；每个节点最多保留 top_n 条出边。"""
    # 过滤
    kept = [
        ((src, dst), info)
        for (src, dst), info in edges.items()
        if info["weight"] >= min_weight
    ]
    kept.sort(key=lambda x: -x[1]["weight"])

    # 每个 src 限制 top_n 条出边（避免密）
    count_by_src: Dict[str, int] = defaultdict(int)
    final_edges: List[Tuple[Tuple[str, str], Dict]] = []
    for (src, dst), info in kept:
        if count_by_src[src] >= top_n:
            continue
        count_by_src[src] += 1
        final_edges.append(((src, dst), info))

    # 找出出现在边里的所有 flow（有些可能没有任何跨流依赖，不画节点）
    active_flows: Set[str] = set()
    for (src, dst), _ in final_edges:
        active_flows.add(src)
        active_flows.add(dst)

    # 同时把没参与边的 flow 单独列出来作为"独立 flow"
    all_flow_names = {f["name"] for f in flow_facts}
    isolated = all_flow_names - active_flows

    # 节点 id 化（避免中文字符在 mermaid 里作为节点 id 报错）
    fid_map: Dict[str, str] = {}
    def fid(name: str) -> str:
        if name not in fid_map:
            fid_map[name] = f"F{len(fid_map)}"
        return fid_map[name]

    lines = ["graph LR"]

    # 节点声明
    for n in sorted(active_flows):
        lines.append(f'    {fid(n)}["{n}"]')
    if isolated:
        # 把独立节点放进 subgraph 以便一眼看出
        lines.append("")
        lines.append('    subgraph 独立["独立（无明显跨流依赖）"]')
        for n in sorted(isolated):
            lines.append(f'    {fid(n)}["{n}"]')
        lines.append("    end")

    lines.append("")
    # 边
    for (src, dst), info in final_edges:
        weight = info["weight"]
        samples = info.get("samples") or []
        if samples:
            sample_txt = " / ".join(samples[:2])
            label = f'|"{sample_txt} ({weight})"|'
        else:
            label = f'|"{weight}"|'
        lines.append(f"    {fid(src)} -->{label} {fid(dst)}")

    return "\n".join(lines), final_edges


# ============================================================
# LLM：给 overview 写一段中文说明
# ============================================================

OVERVIEW_SYSTEM = """你是技术文档撰写者。任务：为下列业务流跨流调用依赖图写一段 150-250 字的中文说明。

## 要求
- 先概括"本项目的 26 个业务流之间的调用依赖关系如何"
- 指出 1-3 个"被高频调用的基础服务 flow"（入度大的节点，通常是积分、通知、用户等基础能力）
- 指出 1-3 个"高出度的整合型 flow"（出度大的节点，通常是业务主流程）
- 禁止长篇罗列；聚焦观察到的模式
- 所有 flow 名用反引号包裹
- 直接输出 markdown 正文，不要 JSON 包裹
"""


def build_overview_user_prompt(edges_kept: List[Tuple[Tuple[str, str], Dict]],
                                 total_flows: int) -> str:
    # 计算 in/out 度
    in_deg: Dict[str, int] = defaultdict(int)
    out_deg: Dict[str, int] = defaultdict(int)
    for (src, dst), info in edges_kept:
        out_deg[src] += info["weight"]
        in_deg[dst] += info["weight"]

    top_in = sorted(in_deg.items(), key=lambda x: -x[1])[:8]
    top_out = sorted(out_deg.items(), key=lambda x: -x[1])[:8]
    edge_samples = sorted(edges_kept, key=lambda x: -x[1]["weight"])[:15]

    lines = [f"## 项目 flow 总数：{total_flows}，画出的跨流依赖边：{len(edges_kept)}"]
    lines.append("")
    lines.append("## 被调用最频繁的 flow（入度 TOP）")
    for name, w in top_in:
        lines.append(f"- `{name}`: 入度 {w}")
    lines.append("")
    lines.append("## 调用其他 flow 最多的 flow（出度 TOP）")
    for name, w in top_out:
        lines.append(f"- `{name}`: 出度 {w}")
    lines.append("")
    lines.append("## 样例依赖边（TOP 15 按权重）")
    for (src, dst), info in edge_samples:
        methods = " / ".join(info["samples"][:2]) if info["samples"] else ""
        lines.append(f"- `{src}` → `{dst}` (权重 {info['weight']}; 样例方法: {methods})")

    return "\n".join(lines) + "\n\n请据此写一段 150-250 字的中文总览说明。"


# ============================================================
# 组装 meta.json（与 assembler 输出格式一致）
# ============================================================

def assemble_overview_meta(
    mermaid_src: str,
    narrative: Optional[str],
    flow_facts: List[Dict],
    edges: Dict[Tuple[str, str], Dict],
) -> Dict:
    """单图模式（--split 未开）的输出组装。"""
    wiki: List[Dict] = []
    header_md = "## 业务流跨流依赖总览\n\n"
    if narrative:
        header_md += narrative
    else:
        header_md += (
            "下图展示业务流之间的调用依赖关系。"
            "节点表示业务流，有向边 `A → B` 表示 A 的入口方法调用了 B 核心类里的方法，"
            "边标签为代表性方法名和调用点总数。"
        )
    wiki.append({"markdown": header_md, "neo4j_id": {}})
    wiki.append({
        "mermaid": f"```mermaid\n{mermaid_src}\n```",
        "mapping": {},
    })
    wiki.append({"markdown": _build_degree_table(flow_facts, edges), "neo4j_id": {}})
    return {"wiki": wiki, "source_id_list": []}


def _build_degree_table(
    flow_facts: List[Dict],
    edges: Dict[Tuple[str, str], Dict],
) -> str:
    in_deg, out_deg = compute_degrees(edges)
    lines = [
        "### 入度 / 出度统计",
        "",
        "| flow | 入度（被调用） | 出度（调用他人） |",
        "|---|---:|---:|",
    ]
    all_names = {f["name"] for f in flow_facts}
    for n in sorted(all_names):
        lines.append(f"| `{n}` | {in_deg.get(n, 0)} | {out_deg.get(n, 0)} |")
    return "\n".join(lines)


def assemble_split_meta(
    flow_facts: List[Dict],
    edges: Dict[Tuple[str, str], Dict],
    hubs: List[str],
    main_mermaid: str,
    main_edge_count: int,
    hub_subgraphs: List[Tuple[str, str, int]],  # (hub_name, mermaid, edge_count)
    narrative: Optional[str],
) -> Dict:
    """多图模式（--split）的输出组装：主图 + 每 hub 聚焦图 + 度数表。"""
    wiki: List[Dict] = []

    intro = "## 业务流跨流依赖总览\n\n"
    if narrative:
        intro += narrative + "\n\n"
    intro += (
        f"本项目共识别出 **{len(hubs)}** 个高流量"
        "**枢纽**（入+出度均很高），它们在单张图里会让结构混乱，"
        f"因此按「**主图** + **每枢纽聚焦图**」拆成 {1 + len(hubs)} 张：\n\n"
        "- **业务协作主图**：排除所有枢纽后的剩余 flow 之间的协作边\n"
    )
    for h in hubs:
        intro += f"- **{h}** 的 1 跳依赖详图\n"
    intro += (
        "\n边标签格式：`代表性方法名 (调用点总数)`。调用点总数是"
        "沿 Neo4j `CALLS` 边 1-2 跳内，发起方触达目标 flow 核心类的方法点计数。"
    )
    wiki.append({"markdown": intro, "neo4j_id": {}})

    # 业务协作主图
    wiki.append({
        "markdown": f"### 业务协作主图\n\n排除枢纽后，保留 {main_edge_count} 条边，"
                    "反映业务流之间**直接的业务协作**（而非通过数据/统计层中转）。",
        "neo4j_id": {},
    })
    wiki.append({
        "mermaid": f"```mermaid\n{main_mermaid}\n```",
        "mapping": {},
    })

    # 每个 hub 的聚焦图
    for hub_name, hub_mermaid, edge_count in hub_subgraphs:
        wiki.append({
            "markdown": f"### 枢纽聚焦：{hub_name}\n\n"
                        f"以 `{hub_name}` 为中心的 1 跳依赖，共 {edge_count} 条边。"
                        "上游箭头来自该枢纽的"
                        "调用发起者，下游箭头指向该枢纽依赖的其它 flow。",
            "neo4j_id": {},
        })
        wiki.append({
            "mermaid": f"```mermaid\n{hub_mermaid}\n```",
            "mapping": {},
        })

    # 度数统计表（同单图模式）
    wiki.append({"markdown": _build_degree_table(flow_facts, edges), "neo4j_id": {}})

    return {"wiki": wiki, "source_id_list": []}


# ============================================================
# 主流程
# ============================================================

async def main():
    parser = argparse.ArgumentParser(description="生成业务流跨流依赖图（视角 B）")
    parser.add_argument("--max-depth", type=int, default=2,
                        help="沿 CALLS 查下游的最大跳数（默认 2）")
    parser.add_argument("--max-shared", type=int, default=3,
                        help="类归属共享阈值：在 > 此值 个 flow 里共享的类剔除归属（默认 3）")
    parser.add_argument("--min-weight", type=int, default=2,
                        help="只画 weight >= 此值 的边（默认 2）")
    parser.add_argument("--top-n", type=int, default=4,
                        help="每个 flow 节点最多画出度 top_n 条边（默认 4）")
    parser.add_argument("--no-llm", action="store_true",
                        help="不调 LLM 写总览说明，使用模板文字")
    parser.add_argument("--split", action="store_true",
                        help="拆成多图：业务协作主图 + 每个枢纽的聚焦图（推荐；避免 hub 扰乱）")
    parser.add_argument("--hub-min-degree", type=int, default=30,
                        help="--split 模式下 hub 识别阈值：入+出度 >= 该值视为 hub（默认 30）")
    parser.add_argument("--hub-max-count", type=int, default=5,
                        help="--split 模式下最多保留几个 hub 聚焦图（默认 5，按总度降序）")
    parser.add_argument("--out", default=None,
                        help="输出路径（默认 business_flow/output_flow/_overview.meta.json）")
    args = parser.parse_args()

    logger = setup_logger()

    # 1. 数据加载
    all_flows = load_flows()
    flows = filter_generated_flows(all_flows, logger)
    if not flows:
        logger.error("没有找到任何已生成 meta 的 flow，退出")
        sys.exit(1)

    flow_facts = [extract_flow_facts(f) for f in flows]

    # 2. 类归属
    ownership = build_class_ownership(flow_facts, args.max_shared, logger)

    # 3. Neo4j 查依赖边
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    if not await neo4j.test_connection():
        logger.error("Neo4j 连接失败")
        sys.exit(1)
    logger.info("Neo4j 连接成功")

    try:
        edges = await build_dependency_edges(
            neo4j, flow_facts, ownership, args.max_depth, logger,
        )
    finally:
        neo4j.close()

    # 4. 生成 mermaid（按 --split 分支）
    if args.split:
        hubs = identify_hubs(edges, args.hub_min_degree, args.hub_max_count)
        logger.info(
            f"识别出 {len(hubs)} 个 hub（in+out 度 >= {args.hub_min_degree}）: {hubs}"
        )
        # 主图：排除所有 hub
        main_mermaid, main_edge_count = build_main_business_graph(
            flow_facts, edges, set(hubs), args.min_weight, args.top_n,
        )
        logger.info(f"业务协作主图保留 {main_edge_count} 条边")
        # 每个 hub 的聚焦图
        hub_subgraphs: List[Tuple[str, str, int]] = []
        for h in hubs:
            h_mermaid, h_edge_count = build_focus_subgraph(edges, h, args.min_weight)
            logger.info(f"枢纽 {h} 聚焦图保留 {h_edge_count} 条边")
            hub_subgraphs.append((h, h_mermaid, h_edge_count))

        # 单独用于 LLM 说明输入（把所有 kept edges 拼起来作为样例）
        kept_edges = [
            ((s, d), info)
            for (s, d), info in edges.items()
            if info["weight"] >= args.min_weight
        ]
    else:
        hubs = []
        mermaid_src, kept_edges = build_mermaid_graph(
            flow_facts, edges, args.min_weight, args.top_n,
        )
        logger.info(f"mermaid 最终保留 {len(kept_edges)} 条边")

    # 5. LLM 写说明（可选）
    narrative: Optional[str] = None
    if not args.no_llm and kept_edges:
        try:
            llm = LLMInterface()
            set_default_llm(llm)
            user_prompt = build_overview_user_prompt(kept_edges, len(flow_facts))
            narrative, _ = await invoke_llm_markdown(
                system_prompt=OVERVIEW_SYSTEM,
                user_prompt=user_prompt,
                label="overview",
            )
            logger.info(f"LLM 说明生成成功 ({len(narrative)} 字符)")
        except Exception as e:
            logger.warning(f"LLM 说明生成失败: {type(e).__name__}: {e}，将用模板文字")

    # 6. 组装 meta.json
    if args.split:
        meta = assemble_split_meta(
            flow_facts, edges, hubs,
            main_mermaid, main_edge_count, hub_subgraphs, narrative,
        )
    else:
        meta = assemble_overview_meta(mermaid_src, narrative, flow_facts, edges)

    out_path = args.out or os.path.join(
        BF_DIR, "output_flow", "_overview.meta.json",
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存 → {out_path}")

    # 7. 终端打印（便于直接复制粘贴）
    if args.split:
        print("\n━━━━━━━━━━━ 业务协作主图 ━━━━━━━━━━━")
        print(main_mermaid)
        for hub_name, hub_mermaid, _ in hub_subgraphs:
            print(f"\n━━━━━━━━━━━ 枢纽聚焦：{hub_name} ━━━━━━━━━━━")
            print(hub_mermaid)
    else:
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"mermaid 图（{len(kept_edges)} 条边）：")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(mermaid_src)


if __name__ == "__main__":
    asyncio.run(main())
