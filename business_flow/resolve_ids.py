"""
Step 2 — 业务流入口方法 node_id 解析

读取  output/business_flows.json  (业务流发现 workflow 的产出，entry_methods 只含 class+method+verified)
输出  business_flow/business_flows.json  (span.py 期望的输入格式，entry_methods 含 class+method+node_id)

按 (class_name, method_name) 在 Neo4j 里查 Method 节点的 nodeId 并填回。
默认把重载展开成多个同 class+method、不同 node_id 的 entry_method（保留所有功能面）。

运行:
    python business_flow/resolve_ids.py
    python business_flow/resolve_ids.py --verified-only
    python business_flow/resolve_ids.py --no-expand-overloads
    python business_flow/resolve_ids.py --input ... --output ...
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from interfaces.neo4j_interface import Neo4jInterface


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(PROJECT_ROOT, "output", "business_flows.json")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "business_flow", "business_flows.json")
LOG_DIR = os.path.join(PROJECT_ROOT, "business_flow", "logs")


def setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"resolve_ids_{ts}.log")
    logger = logging.getLogger("business_flow.resolve_ids")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    logger.info(f"日志文件: {log_file}")
    return logger


async def batch_resolve_node_ids(
    neo4j: Neo4jInterface,
    pairs: List[Dict[str, str]],
) -> Dict[Tuple[str, str], List[Dict]]:
    """批量查 (class_name, method_name) → [{node_id, class_id}, ...]。

    一次 UNWIND 查询完成所有 pair 的解析；重载的方法在同一 key 下返回多条。
    """
    if not pairs:
        return {}
    query = """
    UNWIND $pairs AS pair
    MATCH (c) WHERE c.name = pair.class_name
      AND (c:Class OR c:Interface OR c:Enum OR c:Record)
    MATCH (c)-[:DECLARES]->(m:Method) WHERE m.name = pair.method_name
    RETURN pair.class_name AS class_name,
           pair.method_name AS method_name,
           m.nodeId AS node_id,
           c.nodeId AS class_id,
           labels(c) AS class_labels
    """
    rows = await neo4j.execute_query(query, {"pairs": pairs})
    out: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
    for r in rows:
        nid = r.get("node_id")
        if nid is None:
            continue
        key = (r.get("class_name") or "", r.get("method_name") or "")
        out[key].append({
            "node_id": int(nid),
            "class_id": int(r["class_id"]) if r.get("class_id") is not None else None,
        })
    return dict(out)


def collect_pairs(flows: List[Dict], verified_only: bool) -> List[Dict[str, str]]:
    """从所有 flow 里收集唯一的 (class, method) 对"""
    seen = set()
    for f in flows:
        for e in f.get("entry_methods") or []:
            if verified_only and not e.get("verified"):
                continue
            cls = str(e.get("class") or "").strip()
            mth = str(e.get("method") or "").strip()
            if cls and mth:
                seen.add((cls, mth))
    return [{"class_name": c, "method_name": m} for c, m in sorted(seen)]


def enrich_flows(
    flows: List[Dict],
    resolved: Dict[Tuple[str, str], List[Dict]],
    verified_only: bool,
    expand_overloads: bool,
    logger: logging.Logger,
) -> List[Dict]:
    """给每个 flow 的 entry_methods 补 node_id。重载按 expand_overloads 决定是否展开。"""
    out_flows: List[Dict] = []
    stats = {
        "total_entries": 0,
        "resolved": 0,
        "overloaded": 0,
        "unresolved": 0,
        "filtered_unverified": 0,
    }
    for f in flows:
        flow_name = f.get("name", "?")
        new_entries: List[Dict] = []
        for e in f.get("entry_methods") or []:
            stats["total_entries"] += 1
            cls = str(e.get("class") or "").strip()
            mth = str(e.get("method") or "").strip()
            if verified_only and not e.get("verified"):
                stats["filtered_unverified"] += 1
                continue
            if not cls or not mth:
                stats["unresolved"] += 1
                logger.warning(f"[{flow_name}] 缺 class/method 字段: {e}")
                continue
            hits = resolved.get((cls, mth)) or []
            if not hits:
                stats["unresolved"] += 1
                logger.warning(f"[{flow_name}] Neo4j 查不到 {cls}.{mth}")
                continue
            if len(hits) > 1:
                stats["overloaded"] += 1
                logger.info(
                    f"[{flow_name}] {cls}.{mth} 有 {len(hits)} 个重载 "
                    f"(expand={expand_overloads})"
                )
            chosen = hits if expand_overloads else hits[:1]
            for h in chosen:
                new_entries.append({
                    "class": cls,
                    "method": mth,
                    "node_id": h["node_id"],
                })
                stats["resolved"] += 1
        out_flows.append({
            "name": f.get("name"),
            "kind": f.get("kind"),
            "description": f.get("description"),
            "entry_methods": new_entries,
        })
    logger.info(
        f"统计: 输入 entry 数={stats['total_entries']}, "
        f"解析成功={stats['resolved']}, 重载 pair 数={stats['overloaded']}, "
        f"未解析={stats['unresolved']}, verified 过滤={stats['filtered_unverified']}"
    )
    return out_flows


async def main():
    parser = argparse.ArgumentParser(
        description="把 output/business_flows.json 的 entry_methods 补上 node_id，"
                    "转换为 span.py 期望的格式"
    )
    parser.add_argument("--input", default=DEFAULT_INPUT,
                        help=f"输入文件 (默认 {DEFAULT_INPUT})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,
                        help=f"输出文件 (默认 {DEFAULT_OUTPUT})")
    parser.add_argument("--verified-only", action="store_true",
                        help="只保留 verified=true 的 entry_method，过滤 LLM 未校验的")
    parser.add_argument("--no-expand-overloads", action="store_true",
                        help="重载方法只保留第一个 node_id（默认展开成多个 entry）")
    args = parser.parse_args()

    logger = setup_logger()

    if not os.path.isfile(args.input):
        logger.error(f"输入文件不存在: {args.input}")
        sys.exit(1)
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)
    flows = data.get("flows") or []
    logger.info(f"输入 {len(flows)} 个 flow, 来源: {args.input}")

    if os.path.isfile(args.output):
        logger.warning(f"输出文件已存在，将覆盖: {args.output}")

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
        pairs = collect_pairs(flows, verified_only=args.verified_only)
        logger.info(f"待解析 {len(pairs)} 个唯一 (class, method) 对")
        resolved = await batch_resolve_node_ids(neo4j, pairs)
        logger.info(f"Neo4j 返回 {len(resolved)} 个 (class, method) 命中至少一条")

        enriched = enrich_flows(
            flows, resolved,
            verified_only=args.verified_only,
            expand_overloads=not args.no_expand_overloads,
            logger=logger,
        )
    finally:
        neo4j.close()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"flows": enriched}, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存 → {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
