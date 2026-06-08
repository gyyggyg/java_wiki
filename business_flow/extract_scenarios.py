"""端到端业务场景抽取（MVP）

读 business_flows_with_span.json 和 Neo4j，按每个 Controller 入口方法
让 LLM 读真源码拆出独立业务场景，输出 business_scenarios.json。

MVP 简化（后续阶段扩展）：
- BFS 深度 3（阶段 2 扩到 4）
- allow-list = 全部 26 flow 的 core_class_ids 并集（只过滤 JDK/工具类）
- 不做图验证（阶段 3）
- 不做跨入口去重（阶段 4）

用法:
    python business_flow/extract_scenarios.py --flow 奖品兑换流
    python business_flow/extract_scenarios.py --flow 奖品兑换流 --entry exchange
    python business_flow/extract_scenarios.py --all --concurrency 5    # 全 26 flow
"""
import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from business_flow.llm_client import set_default_llm, invoke_llm_strict


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BF_DIR = os.path.join(PROJECT_ROOT, "business_flow")
INPUT_PATH = os.path.join(BF_DIR, "business_flows_with_span.json")
OUTPUT_PATH = os.path.join(BF_DIR, "business_scenarios.json")
LOG_DIR = os.path.join(BF_DIR, "logs")

BFS_DEPTH = 3
MAX_CONTEXT_CHARS = 40000  # ~10-13k tokens，对任意模型都安全


def setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"extract_scenarios_{ts}.log")
    logger = logging.getLogger("business_flow.extract_scenarios")
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
    logger.info(f"日志文件: {log_file}")
    return logger


# ============================================================
# 阶段 1：上下文组装（BFS + allow-list 过滤 + 按层分组）
# ============================================================

async def bfs_reachable_methods(
    neo4j, entry_id: int, max_depth: int,
) -> Dict[int, int]:
    """BFS CALLS，返回 {method_id: min_depth}（含入口自身，depth=0）。

    **关键**：CALLS 边只能追到"声明类型"的方法 —— 例如源码里 `iService.foo()`
    若 iService 声明为接口 IService，CALLS 会指向 IService.foo（接口方法节点，没有
    source_code）。必须在 BFS 里做接口→实现穿透：遇到 CALLS 指向 Interface 方法时，
    同时把所有 IMPLEMENTS 该接口的实现类里同名方法加进 frontier。
    """
    visited: Dict[int, int] = {entry_id: 0}
    frontier: List[int] = [entry_id]
    for d in range(1, max_depth + 1):
        if not frontier:
            break
        rows = await neo4j.execute_query("""
            MATCH (m:Method) WHERE m.nodeId IN $ids
            MATCH (m)-[:CALLS]->(called:Method)
            OPTIONAL MATCH (owner)-[:DECLARES]->(called)
              WHERE owner:Class OR owner:Interface
            // 当 called 是 Interface 方法时，找所有实现类的同名方法
            OPTIONAL MATCH (impl:Class)-[:IMPLEMENTS]->(owner)
              WHERE owner:Interface
            OPTIONAL MATCH (impl)-[:DECLARES]->(impl_m:Method)
              WHERE impl_m.name = called.name
            RETURN DISTINCT called.nodeId AS called_id,
                   labels(owner)[0] AS owner_label,
                   collect(DISTINCT impl_m.nodeId) AS impl_ids
        """, {"ids": frontier})
        next_frontier: List[int] = []
        for r in rows:
            cid = r["called_id"]
            if cid is not None and cid not in visited:
                visited[cid] = d
                next_frontier.append(cid)
            # 接口方法穿透：把所有实现类的同名方法也加入可达集
            for impl_id in r.get("impl_ids") or []:
                if impl_id is not None and impl_id not in visited:
                    visited[impl_id] = d
                    next_frontier.append(impl_id)
        frontier = next_frontier
    return visited


async def fetch_methods_with_class(neo4j, method_ids: List[int]) -> List[Dict]:
    """一次拉每个 method 的 source_code + 所属类信息"""
    if not method_ids:
        return []
    return await neo4j.execute_query("""
        MATCH (m:Method) WHERE m.nodeId IN $ids
        OPTIONAL MATCH (cls)-[:DECLARES]->(m)
        WHERE cls:Class OR cls:Interface OR cls:Enum
        RETURN m.nodeId AS method_id,
               m.name AS method_name,
               coalesce(m.source_code, '') AS source_code,
               cls.nodeId AS class_id,
               cls.name AS class_name,
               labels(cls)[0] AS class_label
    """, {"ids": method_ids})


def build_entry_context(
    entry_class: str,
    entry_method_name: str,
    rows: List[Dict],
    depth_map: Dict[int, int],
    allow_class_ids: Set[str],
    max_chars: int,
    logger: logging.Logger,
    label: str,
) -> Tuple[str, Dict[str, Any]]:
    """按 allow-list 过滤后，按 (depth, class) 聚合渲染为 LLM context"""
    kept = []
    filtered_out = 0
    for r in rows:
        cid = r.get("class_id")
        if cid is not None and str(cid) in allow_class_ids:
            r["depth"] = depth_map.get(r["method_id"], 99)
            kept.append(r)
        else:
            filtered_out += 1

    # 按类聚合
    by_class: Dict[str, Dict[str, Any]] = {}
    for r in kept:
        cname = r.get("class_name") or "<unknown>"
        by_class.setdefault(cname, {
            "class_label": r.get("class_label"),
            "min_depth": r["depth"],
            "methods": [],
        })
        by_class[cname]["methods"].append(r)
        if r["depth"] < by_class[cname]["min_depth"]:
            by_class[cname]["min_depth"] = r["depth"]

    # 入口类最先，其余按 min_depth 排序
    class_order = sorted(
        by_class.keys(),
        key=lambda c: (0 if c == entry_class else by_class[c]["min_depth"] + 1, c),
    )

    rendered_parts: List[str] = []
    chars_used = 0
    classes_included = 0
    for cname in class_order:
        cinfo = by_class[cname]
        tag = "⭐ ENTRY CLASS" if cname == entry_class \
            else f"{cinfo['class_label']}, depth={cinfo['min_depth']}"
        header = f"\n///// {cname}  ({tag}) /////"
        body_parts = [header]
        # 同一类内把入口方法排最前
        methods = sorted(
            cinfo["methods"],
            key=lambda m: (0 if (cname == entry_class and m["method_name"] == entry_method_name)
                           else 1, m["depth"], m["method_name"] or ""),
        )
        for m in methods:
            src = (m.get("source_code") or "").strip()
            if not src:
                continue
            is_entry = (cname == entry_class and m["method_name"] == entry_method_name)
            prefix = "### ENTRY METHOD ###\n" if is_entry else ""
            body_parts.append(f"{prefix}{src}\n")
        rendered = "\n".join(body_parts)
        if chars_used + len(rendered) > max_chars and classes_included > 0:
            break
        rendered_parts.append(rendered)
        chars_used += len(rendered)
        classes_included += 1

    context = "\n".join(rendered_parts)
    classes_truncated = len(class_order) - classes_included
    stats = {
        "classes_included": classes_included,
        "classes_truncated": classes_truncated,
        "methods_in_allow_list": len(kept),
        "methods_filtered_out": filtered_out,
        "chars_used": chars_used,
    }
    logger.info(
        f"[{label}] context: {classes_included}类/{len(kept)}方法/{chars_used}chars"
        + (f"（截 {classes_truncated} 类）" if classes_truncated else "")
        + f"，过滤掉 {filtered_out} 个非核心方法"
    )
    return context, stats


# ============================================================
# 阶段 2：LLM 调用
# ============================================================

SCENARIO_EXTRACT_SYSTEM = """你是资深业务架构师。任务：读完一个 HTTP 入口方法及其传递调用的 Java 源码，识别该入口支持的**独立业务场景**。

## 什么是"独立场景"
- 入口或其内部方法有**业务语义的分支**（if/else/switch/try-catch/早返回），不同分支走不同的**写操作**或**下游调用**
- 不算业务分支：参数校验 / 权限校验 / 日志审计 / 异常包装 / 返回码设置
- 纯列表/详情/导出查询通常是 1 个场景，不要硬拆
- 多个分支只差"分页参数"也是同一场景

## 输出每个场景的字段
- `scenario_name`: 3-10 字动词性业务名（例："兑换实物奖品"、"取消已付款订单"）
  - ❌ 不要用方法名（"exchange"）、域名（"奖品兑换流"）、层级名（"用户端接口"）
- `trigger_condition`: 触发该分支的**业务条件**，≤20 字
  - ✅ 好："库存不足"、"订单已支付"、"用户无抽奖次数"、"无业务分支"
  - ❌ 坏："访问/list接口"、"调用GET /dict"、"调用add接口"（这些是 HTTP 细节，不是业务条件）
  - 无业务分支时直接写 "无业务分支"，不要编造
- `description`: 这个场景在做什么，≤50 字（业务视角）
- `call_path`: 有序调用列表 `[{class, method, role}]`，只放**业务性调用**（忽略 getter/setter/工具类/日志）
  - role ∈ "entry" | "service" | "dao" | "external"
- `writes`: 写操作列表 `[{kind, target, op}]`
  - kind ∈ "db" | "mq" | "event" | "cache" | "file"
  - target: 表名（从 @TableName 或实体类名推断）/ queue 名 / event 类名 / 文件名
  - op ∈ "insert" | "update" | "delete" | "send" | "cache" | "export"
  - **Excel / CSV / 文件导出** 用 `{kind: "file", op: "export", target: "<文件业务名>.xlsx"}`
    **不是 `{kind: "db", op: "insert"}`** —— 导出是文件生成，不是 DB 写
- `state_transitions`: 状态字段变迁 `[{entity, field, from, to}]`（可空）
- `confidence`: "high" | "medium" | "low"

## 硬约束
1. **忠实源码**：call_path 只能放源码里**真看到**的调用，不要补"应该有"的调用
2. **Mapper 写方法命名规律**：insert* / update* / delete* / batch* / remove* 开头 = DB 写
3. **纯查询 Mapper**（select* 开头）不算 writes
4. 源码简单（<20 行且无业务分支）→ 输出 1 个场景就够，trigger_condition 写 "无业务分支"
5. **ExcelUtil.exportExcel / EasyExcel 相关调用** = 文件导出，用 `{kind: "file", op: "export"}`，禁止标为 DB 写

## 严格 JSON 输出（无围栏、无前言）
{
  "scenarios": [
    {
      "scenario_name": "...",
      "trigger_condition": "...",
      "description": "...",
      "call_path": [{"class": "...", "method": "...", "role": "..."}],
      "writes": [{"kind": "...", "target": "...", "op": "..."}],
      "state_transitions": [],
      "confidence": "high"
    }
  ],
  "entry_notes": "整体补充，可空字符串"
}
"""


def build_user_prompt(
    flow: Dict,
    entry_class: str,
    entry_method_name: str,
    entry_method_id: int,
    context: str,
) -> str:
    return "\n".join([
        f"## 业务域背景",
        f"- 域名称：`{flow['name']}`",
        f"- 域类型：`{flow.get('kind', '?')}`",
        f"- 域说明：{flow.get('description', '')}",
        "",
        f"## 要分析的入口",
        f"- 入口类：`{entry_class}`",
        f"- 入口方法：`{entry_method_name}` (method_id={entry_method_id})",
        "",
        "## 源码（入口方法 + 传递可达的业务类方法，已过滤掉 JDK/工具类）",
        "",
        context,
        "",
        "---",
        "请识别独立业务场景并按 JSON 格式输出（不要围栏、不要前言）。",
    ])


async def extract_scenarios_for_entry(
    flow: Dict,
    entry: Dict,
    neo4j,
    allow_class_ids: Set[str],
    logger: logging.Logger,
) -> Optional[Dict]:
    entry_class = entry["class"]
    entry_method_name = entry["method"]
    entry_method_id = int(entry["node_id"])
    label = f"{flow['name']}/{entry_class}.{entry_method_name}"

    depth_map = await bfs_reachable_methods(neo4j, entry_method_id, BFS_DEPTH)
    logger.info(f"[{label}] BFS 可达 {len(depth_map)} 方法（深度≤{BFS_DEPTH}）")

    rows = await fetch_methods_with_class(neo4j, list(depth_map.keys()))
    context, ctx_stats = build_entry_context(
        entry_class, entry_method_name, rows, depth_map,
        allow_class_ids, MAX_CONTEXT_CHARS, logger, label,
    )
    if not context.strip():
        logger.warning(f"[{label}] context 为空，跳过")
        return None

    user_prompt = build_user_prompt(
        flow, entry_class, entry_method_name, entry_method_id, context,
    )

    try:
        result, _ = await invoke_llm_strict(
            system_prompt=SCENARIO_EXTRACT_SYSTEM,
            user_prompt=user_prompt,
            required_keys=["scenarios"],
            label=label,
        )
    except Exception as e:
        logger.error(f"[{label}] LLM 失败: {type(e).__name__}: {e}")
        return None

    scenarios = result.get("scenarios") or []
    logger.info(f"[{label}] 抽出 {len(scenarios)} 个场景:")
    for s in scenarios:
        logger.info(f"  - [{s.get('confidence','?')}] {s.get('scenario_name','?')}"
                    f" —— {s.get('trigger_condition','')}")

    return {
        "entry_method_id": entry_method_id,
        "entry_class": entry_class,
        "entry_method": entry_method_name,
        "domain": flow["name"],
        "kind": flow.get("kind", ""),
        "extraction_stats": ctx_stats,
        "scenarios": scenarios,
        "entry_notes": result.get("entry_notes", ""),
    }


# ============================================================
# 主流程
# ============================================================

def build_global_allow_list(flows: List[Dict]) -> Set[str]:
    """全部 flow 的 core_class_ids 并集 = 项目"业务类宇宙"，过滤掉 JDK/工具类"""
    allow: Set[str] = set()
    for f in flows:
        span = f.get("span") or {}
        for cid in (span.get("core_class_ids") or []):
            allow.add(str(cid))
    return allow


async def main():
    parser = argparse.ArgumentParser(description="端到端业务场景抽取（MVP）")
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--flow", default=None, help="处理指定 flow 名字")
    g.add_argument("--all", action="store_true", help="处理全部 26 flow")
    parser.add_argument("--entry", default=None,
                        help="只处理指定 entry（method 名，或 Class.method）")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--input", default=INPUT_PATH,
                        help="business_flows_with_span.json 路径")
    parser.add_argument("--out", default=OUTPUT_PATH)
    args = parser.parse_args()

    logger = setup_logger()

    # LLM
    llm = LLMInterface()
    set_default_llm(llm)
    logger.info(f"LLM: provider={llm.provider} "
                f"model={llm.model_kwargs.get('model_name') or llm.model_kwargs.get('model')}")

    # 加载 flows
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    all_flows: List[Dict] = data.get("flows", [])

    if args.all:
        target_flows = all_flows
    elif args.flow:
        target_flows = [f for f in all_flows if f["name"] == args.flow]
        if not target_flows:
            logger.error(f"未找到 flow: {args.flow}")
            sys.exit(1)
    else:
        # 默认：奖品兑换流（MVP 验证用）
        target_flows = [f for f in all_flows if f["name"] == "奖品兑换流"]
        if not target_flows:
            logger.error("默认 flow '奖品兑换流' 不存在，请用 --flow 指定")
            sys.exit(1)

    # 全局 allow-list
    allow_class_ids = build_global_allow_list(all_flows)
    logger.info(f"全局 allow-list: {len(allow_class_ids)} 个业务类")

    # 展开成 (flow, entry) 对
    tasks: List[Tuple[Dict, Dict]] = []
    for flow in target_flows:
        entries = flow.get("entry_methods", [])
        if args.entry:
            entries = [
                e for e in entries
                if e.get("method") == args.entry
                or f"{e.get('class')}.{e.get('method')}" == args.entry
            ]
        for e in entries:
            tasks.append((flow, e))
    logger.info(f"待处理 entries: {len(tasks)}")
    if not tasks:
        logger.error("无待处理入口")
        sys.exit(1)

    # Neo4j
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    if not await neo4j.test_connection():
        logger.error("Neo4j 连接失败")
        sys.exit(1)

    sem = asyncio.Semaphore(max(1, args.concurrency))

    async def run_one(flow: Dict, entry: Dict):
        async with sem:
            return await extract_scenarios_for_entry(
                flow, entry, neo4j, allow_class_ids, logger,
            )

    try:
        results = await asyncio.gather(
            *[run_one(f, e) for f, e in tasks],
            return_exceptions=True,
        )
    finally:
        neo4j.close()

    # 汇总
    per_entry: List[Dict] = []
    errors: List[str] = []
    for (flow, entry), r in zip(tasks, results):
        label = f"{flow['name']}/{entry['class']}.{entry['method']}"
        if isinstance(r, Exception):
            errors.append(f"{label}: {type(r).__name__}: {r}")
        elif r:
            per_entry.append(r)
    total_scenarios = sum(len(e["scenarios"]) for e in per_entry)
    logger.info(
        f"\n========== 汇总 ==========\n"
        f"  成功 entries: {len(per_entry)}/{len(tasks)}\n"
        f"  总场景数: {total_scenarios}\n"
        f"  失败数: {len(errors)}"
    )
    for err in errors[:10]:
        logger.error(f"  FAIL: {err}")

    out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_source": args.input,
        "mvp_scope": {
            "flows_processed": [f["name"] for f in target_flows],
            "entries_processed": len(per_entry),
            "total_scenarios": total_scenarios,
            "bfs_depth": BFS_DEPTH,
            "allow_list_size": len(allow_class_ids),
        },
        "per_entry_scenarios": per_entry,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    logger.info(f"写入 {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
