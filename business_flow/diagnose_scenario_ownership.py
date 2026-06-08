"""诊断脚本：针对一个具体的业务场景（entry_method），列出它 call_path 里每个类的
Neo4j 解析情况 + primary domain 归属，快速定位跨模块识别失效的环节。

用法:
    # 默认诊断 addLotteryUser（已知应该跨 抽奖活动流 × 积分任务流）
    python business_flow/diagnose_scenario_ownership.py

    # 诊断其它场景
    python business_flow/diagnose_scenario_ownership.py --entry addOrderByPrizeId
    python business_flow/diagnose_scenario_ownership.py \\
        --input business_flow/business_scenarios_sample.json \\
        --entry writeOff

用处：render_scenarios_meta 跑完如果跨模块场景数量不符合预期，用这个脚本看
每个类的 nodeId 解析 / label / primary_owner 是否正确，快速定位是：
  - Neo4j 解析失败（类名不在图里）
  - ownership 没给它分配（比如 Interface 被 span 排除）
  - ownership 分错了 domain
"""
import argparse
import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from interfaces.neo4j_interface import Neo4jInterface
from business_flow.render_scenarios_meta import (
    load_span_flows, fetch_entity_class_ids,
    build_entity_aware_ownership, resolve_classes_to_nodes,
    enrich_ownership_via_sibling_prefix,
)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BF_DIR = os.path.join(PROJECT_ROOT, "business_flow")
DEFAULT_INPUT = os.path.join(BF_DIR, "business_scenarios_lottery.json")
SPAN_PATH = os.path.join(BF_DIR, "business_flows_with_span.json")


def find_scenario(data: dict, flow: str = None, entry: str = None) -> dict:
    for e in data.get("per_entry_scenarios", []):
        if flow and e.get("domain") != flow:
            continue
        if entry and e.get("entry_method") != entry and \
                f"{e.get('entry_class')}.{e.get('entry_method')}" != entry:
            continue
        return e
    return None


async def main():
    parser = argparse.ArgumentParser(description="诊断场景的 ownership 与跨模块识别")
    parser.add_argument("--input", default=DEFAULT_INPUT,
                        help="business_scenarios*.json 文件路径")
    parser.add_argument("--flow", default=None,
                        help="flow 名字（可选，用于在多 flow 合并文件里定位）")
    parser.add_argument("--entry", default="addLotteryUser",
                        help="entry_method 名（或 Class.method）；默认 addLotteryUser")
    parser.add_argument("--max-shared", type=int, default=3)
    args = parser.parse_args()

    # silence child loggers
    logging.basicConfig(level=logging.WARNING,
                        format="[%(levelname)s] %(name)s: %(message)s")
    logger = logging.getLogger("diagnose")

    # 读场景
    if not os.path.isfile(args.input):
        print(f"ERROR: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    target = find_scenario(data, args.flow, args.entry)
    if not target:
        print(f"ERROR: 未找到场景 flow={args.flow} entry={args.entry}", file=sys.stderr)
        # 列出所有可选
        print("\n可选的 (flow, entry):", file=sys.stderr)
        for e in data.get("per_entry_scenarios", []):
            print(f"  [{e.get('domain','?')}] {e.get('entry_class')}.{e.get('entry_method')}",
                  file=sys.stderr)
        sys.exit(1)

    entry_class = target["entry_class"]
    entry_method = target["entry_method"]
    domain = target["domain"]
    print(f"==== 诊断场景: {domain} / {entry_class}.{entry_method} ====")
    print(f"LLM 抽到的 scenarios:")
    for s in target["scenarios"]:
        print(f"  - [{s.get('confidence','?')}] {s.get('scenario_name','?')}")
        writes = s.get("writes") or []
        if writes:
            for w in writes:
                print(f"      write: {w.get('kind','?')} {w.get('op','?')} {w.get('target','?')}")

    # 收集 call_path 里所有类
    classes = [entry_class]
    for s in target["scenarios"]:
        for step in s.get("call_path", []):
            c = (step.get("class") or "").strip()
            if c and c not in classes:
                classes.append(c)
    print(f"\ncall_path 涉及 {len(classes)} 个类\n")

    # Neo4j：entity ids + 类解析
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    try:
        if not await neo4j.test_connection():
            print("ERROR: Neo4j 连接失败", file=sys.stderr)
            sys.exit(1)
        entity_ids = await fetch_entity_class_ids(neo4j)
        class_to_node = await resolve_classes_to_nodes(neo4j, set(classes), logger)
    finally:
        neo4j.close()

    # ownership (entity-aware + sibling-prefix 兜底)
    span_flows = load_span_flows(SPAN_PATH)
    ownership, id_to_name = build_entity_aware_ownership(
        span_flows, args.max_shared, entity_ids, logger,
    )
    ownership = enrich_ownership_via_sibling_prefix(
        ownership, id_to_name, class_to_node, logger,
    )

    # 表格
    print(f'{"类名":35s} {"nodeId":>10s} {"label":>12s} {"entity?":>8s} {"primary_domain":>25s}')
    print("-" * 95)
    involved: set = set()
    unresolved: list = []
    no_owner: list = []
    for c in classes:
        info = class_to_node.get(c)
        if not info:
            print(f"  {c:33s} {'—':>10s} {'UNRESOLVED':>12s} {'—':>8s} {'—':>25s}")
            unresolved.append(c)
            continue
        nid = info["nodeId"]
        label = info["label"]
        is_entity = "yes" if nid in entity_ids else "no"
        owner = ownership.get(nid, "—NO OWNER—")
        if owner == "—NO OWNER—":
            no_owner.append(c)
        else:
            involved.add(owner)
        print(f"  {c:33s} {nid:>10s} {label:>12s} {is_entity:>8s} {owner:>25s}")

    print()
    print(f"触达 domain（涉及 ≥1 个 owner 的类）: {sorted(involved)}")
    print(f"  → 跨模块判定: {'✓ 跨模块' if len(involved) >= 2 else '✗ 单域（或未识别）'}")
    if unresolved:
        print(f"  ⚠ 未解析的类 ({len(unresolved)}): {unresolved}")
    if no_owner:
        print(f"  ⚠ 解析到但无 owner 的类 ({len(no_owner)}): {no_owner}")

    # 提示：如果关键 Mapper 是 Interface 且没 owner
    interface_no_owner = [
        c for c in no_owner
        if class_to_node.get(c, {}).get("label") == "Interface"
    ]
    if interface_no_owner:
        print()
        print("💡 以下 Interface 类有 nodeId 但没 primary_owner，")
        print("   通常是因为 span.py 的 BFS 产出（core_class_ids）不收录 Interface。")
        print("   建议：在 ownership 里给 Interface 加 'sibling class 推断' 兜底规则：")
        print("   对形如 `XxxMapper` 的 Interface，取同名 Class（或 XxxServiceImpl）的 owner")
        for c in interface_no_owner:
            print(f"     - {c}")


if __name__ == "__main__":
    asyncio.run(main())
