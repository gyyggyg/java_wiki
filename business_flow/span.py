"""
Step 3 — 业务流 span 计算

读取  business_flow/business_flows_merged.json
输出  business_flow/business_flows_with_span.json

对每个 flow 的 entry_methods 做 CALLS 边的 BFS 展开，
按文件路径白名单分桶为 "core"（主业务包）和 "support"（公共工具），
得到该 flow 真正触达的所有 class 集合。

运行:
    python business_flow/span.py
"""

import asyncio
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from interfaces.neo4j_interface import Neo4jInterface


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BF_DIR = os.path.join(PROJECT_ROOT, "business_flow")
INPUT_PATH = os.path.join(BF_DIR, "business_flows.json")
OUTPUT_PATH = os.path.join(BF_DIR, "business_flows_with_span.json")
LOG_DIR = os.path.join(BF_DIR, "logs")


# =====================================================================
# 可配置项
# =====================================================================

# 从入口方法往下追 CALLS 边的最大深度
MAX_DEPTH = int(os.environ.get("BF_SPAN_MAX_DEPTH", "4"))

# 单个 flow 最多保留多少 class（超出按 depth 近的优先保留）
MAX_CLASSES_PER_FLOW = int(os.environ.get("BF_SPAN_MAX_CLASSES", "200"))

# =============================================================
# File 路径分桶配置：启发式默认 + 可选显式覆盖
# =============================================================
#
# 默认走"启发式"，对任何 Java 多模块项目都开箱即用：
#   - File.name 第一级目录属于 JDK/常见第三方（java/javax/org/com/...）→ external 丢弃
#   - 第一级目录名里含 common/utils/shared/base 等关键字 → support
#   - 其余都当 core（项目自身代码）
#
# 如果启发式分错了（比如你的业务包叫 com.yourcompany.xxx 但根目录就是 `com/`），
# 设下面任一环境变量切到显式白名单模式：
#   - BF_SPAN_CORE_PREFIXES       逗号分隔前缀，匹中的归 core
#   - BF_SPAN_SUPPORT_PREFIXES    同上，匹中的归 support
#   - BF_SPAN_EXTERNAL_PREFIXES   额外的 external 黑名单（启发式模式下生效）
# 设置了 CORE 或 SUPPORT 任一时即进入"纯白名单模式"：没命中的一律 external。
# =============================================================

def _split_env_prefixes(env_var: str) -> List[str]:
    raw = os.environ.get(env_var, "")
    return [p.strip() for p in raw.split(",") if p.strip()]


CORE_PATH_PREFIXES = _split_env_prefixes("BF_SPAN_CORE_PREFIXES")
SUPPORT_PATH_PREFIXES = _split_env_prefixes("BF_SPAN_SUPPORT_PREFIXES")
EXTERNAL_EXTRA_PREFIXES = _split_env_prefixes("BF_SPAN_EXTERNAL_PREFIXES")

# 纯白名单模式：只要用户显式设了 CORE 或 SUPPORT，就关闭启发式，按传统前缀匹配
WHITELIST_MODE = bool(CORE_PATH_PREFIXES or SUPPORT_PATH_PREFIXES)

# 启发式模式下的内置"第一级目录是框架/JDK/第三方"黑名单（按小写比较）
_BUILTIN_EXTERNAL_TOP_DIRS = {
    "java", "javax", "jdk", "sun",              # JDK
    "org", "io", "net",                         # spring / apache / reactor / netty / okhttp 等 open source 根
    "com", "cn",                                # 典型的第三方（google / fasterxml / alibaba / hutool 等）
    "lombok", "springfox", "oshi",              # 常见注解/工具库
    "kotlin", "scala", "groovy",                # 非 Java JVM 语言
}

# 启发式模式下："第一级目录名包含这些关键字" → support
_SUPPORT_KEYWORDS = ("common", "utils", "util", "shared", "base")

# 并发 flow 数（Neo4j 查询并发）
MAX_CONCURRENT = int(os.environ.get("BF_SPAN_CONCURRENCY", "4"))


# =====================================================================
# 日志
# =====================================================================

def setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"span_{ts}.log")
    logger = logging.getLogger("business_flow.span")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    logger.info(f"日志文件: {log_file}")
    return logger


# =====================================================================
# 路径分桶
# =====================================================================

def classify_file(file_name: Optional[str]) -> str:
    """返回 'core' / 'support' / 'external'。

    两种模式：
    - 白名单模式（用户显式设了 CORE / SUPPORT 前缀）：按前缀 startswith 匹配，不中就 external。
    - 启发式模式（默认）：第一级目录查内置黑名单 → external；名字含关键字 → support；其余 core。
    """
    if not file_name:
        return "external"

    if WHITELIST_MODE:
        for p in CORE_PATH_PREFIXES:
            if file_name.startswith(p):
                return "core"
        for p in SUPPORT_PATH_PREFIXES:
            if file_name.startswith(p):
                return "support"
        return "external"

    # 启发式：先看 BF_SPAN_EXTERNAL_PREFIXES 显式追加的额外前缀
    for p in EXTERNAL_EXTRA_PREFIXES:
        if file_name.startswith(p):
            return "external"

    top = file_name.split("/", 1)[0].lower()
    if top in _BUILTIN_EXTERNAL_TOP_DIRS:
        return "external"

    if any(kw in top for kw in _SUPPORT_KEYWORDS):
        return "support"

    return "core"


# =====================================================================
# Neo4j 查询
# =====================================================================

async def fetch_flow_span(
    neo4j: Neo4jInterface,
    entry_method_ids: List[int],
    max_depth: int,
) -> List[Dict]:
    """
    从一组入口 Method nodeId 出发，CALLS*0..max_depth 追踪可达的方法，
    返回每条可达记录（包含类信息）。

    depth=0 时返回入口方法自己。

    Interface→Impl 解糖：
        Controller 通常 `@Autowired IService`，图里 CALLS 边指向 Interface.method；
        实际运行时是 Impl.method 在执行。这里把"看到的 Interface method"自动扩展到
        "所有 impl 类里同名的 method"，让 BFS 能正确穿透到实现层。

    做法：把 CALLS + (IMPLEMENTS 边反查 + Class DECLARES 同名 method) 合成一种
          逻辑边 `REACH`，再对 `REACH*0..max_depth` 做可达查询。
    """
    if not entry_method_ids:
        return []

    # 关键查询：用 UNION 把 CALLS 和 "interface-method → impl-method（同名）"两种
    # 逻辑边合并起来，然后以 depth 最近的方式聚合。
    # 我们用 apoc-free 的做法：分层 BFS，Python 侧循环 max_depth 次。
    visited_method_rows: Dict[str, Dict] = {}  # method_id -> row
    frontier = list(entry_method_ids)
    current_depth = 0

    while frontier and current_depth <= max_depth:
        # 对当前 frontier，查：它们自身 + 所有直接 CALLS 目标 + 若 frontier 包含 interface method 的话对应 impl method
        step_query = """
        MATCH (m:Method) WHERE m.nodeId IN $ids
        OPTIONAL MATCH (tc)-[:DECLARES]->(m)
        OPTIONAL MATCH (tf:File)-[:DECLARES]->(tc)
        RETURN DISTINCT
            m.nodeId AS method_id, m.name AS method_name,
            tc.nodeId AS class_id, tc.name AS class_name,
            labels(tc) AS class_labels, tf.name AS file_name
        """
        step_rows = await neo4j.execute_query(step_query, {"ids": frontier})
        for r in step_rows:
            mid = str(r["method_id"])
            if mid not in visited_method_rows:
                visited_method_rows[mid] = {**r, "depth": current_depth}

        if current_depth >= max_depth:
            break

        # 下一层 frontier = CALLS 目标 ∪ (frontier 里 interface 方法对应的 impl 同名方法)
        next_query = """
        MATCH (m:Method) WHERE m.nodeId IN $ids
        OPTIONAL MATCH (m)-[:CALLS]->(called:Method)
        OPTIONAL MATCH (mc)-[:DECLARES]->(m)
        OPTIONAL MATCH (impl:Class)-[:IMPLEMENTS]->(mc)
        OPTIONAL MATCH (impl)-[:DECLARES]->(impl_m:Method) WHERE impl_m.name = m.name
        WITH collect(DISTINCT called.nodeId) + collect(DISTINCT impl_m.nodeId) AS next_ids
        UNWIND next_ids AS nid
        WITH DISTINCT nid WHERE nid IS NOT NULL
        RETURN collect(nid) AS ids
        """
        next_rows = await neo4j.execute_query(next_query, {"ids": frontier})
        next_ids = next_rows[0]["ids"] if next_rows else []
        # 去掉已访问
        next_frontier = [int(nid) for nid in next_ids if str(nid) not in visited_method_rows]
        frontier = next_frontier
        current_depth += 1

    return list(visited_method_rows.values())


# =====================================================================
# 单个 flow 的 span 计算
# =====================================================================

async def compute_flow_span(neo4j: Neo4jInterface, flow: Dict, logger: logging.Logger) -> Dict:
    """给 flow 增加 span 字段。返回新的 flow dict（浅拷贝 + 新字段）"""
    name = flow.get("name", "?")
    entry_method_ids = []
    for e in flow.get("entry_methods", []):
        nid = e.get("node_id")
        if nid is None:
            continue
        try:
            entry_method_ids.append(int(nid))
        except (TypeError, ValueError):
            continue

    if not entry_method_ids:
        logger.warning(f"[{name}] 无有效 entry_method node_id，跳过")
        return {**flow, "span": {"core_class_ids": [], "support_class_ids": [],
                                 "span_method_ids": [], "stats": {}}}

    rows = await fetch_flow_span(neo4j, entry_method_ids, MAX_DEPTH)

    # 按 depth 聚合类和方法，分桶 core / support / external
    core_classes: Dict[str, Dict] = {}      # class_id -> {name, depth, file}
    support_classes: Dict[str, Dict] = {}
    external_classes: Dict[str, Dict] = {}
    method_by_id: Dict[str, Dict] = {}

    for r in rows:
        mid = r.get("method_id")
        if mid is not None:
            method_by_id.setdefault(str(mid), {
                "method_id": str(mid),
                "method_name": r.get("method_name"),
                "class_id": str(r["class_id"]) if r.get("class_id") is not None else None,
                "depth": r.get("depth", 0),
            })

        cid = r.get("class_id")
        if cid is None:
            continue
        bucket = classify_file(r.get("file_name"))
        target_dict = {
            "core": core_classes,
            "support": support_classes,
            "external": external_classes,
        }[bucket]
        key = str(cid)
        depth = r.get("depth", 0)
        if key not in target_dict or depth < target_dict[key]["depth"]:
            target_dict[key] = {
                "class_id": key,
                "class_name": r.get("class_name"),
                "labels": r.get("class_labels") or [],
                "file_name": r.get("file_name"),
                "depth": depth,
            }

    # 超出上限时按 depth 近的优先保留
    def trim(d: Dict[str, Dict], limit: int) -> Dict[str, Dict]:
        if len(d) <= limit:
            return d
        items = sorted(d.values(), key=lambda x: (x["depth"], x["class_name"] or ""))
        return {x["class_id"]: x for x in items[:limit]}

    core_classes = trim(core_classes, MAX_CLASSES_PER_FLOW)
    # support 上限放宽
    support_classes = trim(support_classes, MAX_CLASSES_PER_FLOW // 2)

    # 按 depth 统计
    depth_hist = defaultdict(int)
    for c in core_classes.values():
        depth_hist[c["depth"]] += 1

    span_method_ids = sorted({m["method_id"] for m in method_by_id.values()
                              if m.get("class_id") in core_classes or m.get("class_id") in support_classes})

    stats = {
        "entry_count": len(entry_method_ids),
        "core_classes": len(core_classes),
        "support_classes": len(support_classes),
        "external_classes_filtered": len(external_classes),
        "span_methods": len(span_method_ids),
        "max_depth_reached": max([c["depth"] for c in core_classes.values()] + [0]),
        "depth_histogram": dict(depth_hist),
    }

    logger.info(
        f"[{name}] entries={stats['entry_count']} "
        f"→ core={stats['core_classes']} / support={stats['support_classes']} "
        f"/ external_filtered={stats['external_classes_filtered']} "
        f"/ span_methods={stats['span_methods']}"
    )

    return {
        **flow,
        "span": {
            "core_class_ids": sorted(core_classes.keys()),
            "support_class_ids": sorted(support_classes.keys()),
            "span_method_ids": span_method_ids,
            "core_classes_detail": list(core_classes.values()),
            "support_classes_detail": list(support_classes.values()),
            "stats": stats,
        }
    }


# =====================================================================
# 主流程
# =====================================================================

async def main():
    logger = setup_logger()

    if not os.path.isfile(INPUT_PATH):
        logger.error(f"输入文件不存在: {INPUT_PATH}")
        sys.exit(1)
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    flows = data.get("flows") or []
    logger.info(f"输入 {len(flows)} 个 flow")
    logger.info(f"配置: MAX_DEPTH={MAX_DEPTH}, MAX_CLASSES_PER_FLOW={MAX_CLASSES_PER_FLOW}")
    if WHITELIST_MODE:
        logger.info(
            f"分桶模式=白名单  CORE_PREFIXES={CORE_PATH_PREFIXES}  "
            f"SUPPORT_PREFIXES={SUPPORT_PATH_PREFIXES}"
        )
    else:
        logger.info(
            f"分桶模式=启发式  (内置 external 根目录 {sorted(_BUILTIN_EXTERNAL_TOP_DIRS)}; "
            f"support 关键字 {list(_SUPPORT_KEYWORDS)}; "
            f"额外 external={EXTERNAL_EXTRA_PREFIXES or '无'}) —— "
            f"如需精细控制请设 BF_SPAN_CORE_PREFIXES / BF_SPAN_SUPPORT_PREFIXES"
        )

    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    if not await neo4j.test_connection():
        logger.error("Neo4j 连接失败")
        sys.exit(1)
    logger.info("Neo4j 连接成功")

    # 并发处理 flow
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def run_one(f):
        async with sem:
            try:
                return await compute_flow_span(neo4j, f, logger)
            except Exception as e:
                logger.error(f"[{f.get('name')}] span 计算失败: {type(e).__name__}: {e}", exc_info=True)
                return {**f, "span": {"core_class_ids": [], "support_class_ids": [],
                                      "span_method_ids": [], "stats": {"error": str(e)}}}

    enriched = await asyncio.gather(*[run_one(f) for f in flows])
    neo4j.close()

    # 汇总
    total_core = sum(len(f["span"]["core_class_ids"]) for f in enriched)
    total_support = sum(len(f["span"]["support_class_ids"]) for f in enriched)
    logger.info("=" * 60)
    logger.info("Span 汇总:")
    logger.info(f"  总 flow 数: {len(enriched)}")
    logger.info(f"  所有 flow 的 core 类总和: {total_core}")
    logger.info(f"  所有 flow 的 support 类总和: {total_support}")
    logger.info("  按 flow 展示:")
    for f in sorted(enriched, key=lambda x: -x["span"]["stats"].get("core_classes", 0)):
        s = f["span"]["stats"]
        logger.info(f"    {s.get('core_classes',0):3d} core + {s.get('support_classes',0):2d} support  "
                    f"[{f['kind']:6s}] {f['name']}")

    # 写出
    result = {
        "flows": enriched,
        "_config": {
            "max_depth": MAX_DEPTH,
            "max_classes_per_flow": MAX_CLASSES_PER_FLOW,
            "core_prefixes": CORE_PATH_PREFIXES,
            "support_prefixes": SUPPORT_PATH_PREFIXES,
        },
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"已写入: {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
