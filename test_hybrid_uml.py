"""
混合型Block UML图生成测试脚本

单独测试hybrid_uml的生成，跳过其他章节，快速验证UML输出质量。

用法:
    python test_hybrid_uml.py <block_nodeId>
    python test_hybrid_uml.py <block_nodeId> --skeleton

示例:
    python test_hybrid_uml.py 18472
    python test_hybrid_uml.py 18472 --skeleton
"""

import os
import sys
import json
import asyncio
import argparse
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from graph.four_chart import chart_app

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BLOCK_NAMES_PATH = os.path.join(PROJECT_ROOT, "graph", "block_new_names.json")


def load_block_names():
    if os.path.exists(BLOCK_NAMES_PATH):
        with open(BLOCK_NAMES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


async def test_hybrid_uml(node_id: int, skeleton: bool = False):
    load_dotenv()
    new_names = load_block_names()

    neo4j = Neo4jInterface(
        os.getenv("WIKI_NEO4J_URI"),
        os.getenv("WIKI_NEO4J_USER"),
        os.getenv("WIKI_NEO4J_PASSWORD")
    )
    llm = LLMInterface()
    print(f"[INFO] Neo4j 连接成功")
    print(f"[INFO] 测试节点: {node_id}, skeleton={skeleton}")

    # 1. 查询直连File的类
    query_direct = """
    MATCH (b:Block {nodeId: $nodeId})-[:f2c]->(f:File)-[:DECLARES]->(c:Class|Interface)
    RETURN c.name AS class_name, '本模块' AS source_label
    """
    # 2. 查询子Block下的类
    query_child = """
    MATCH (b:Block {nodeId: $nodeId})-[:f2c]->(child:Block)-[:f2c*]->(f:File)-[:DECLARES]->(c:Class|Interface)
    RETURN c.name AS class_name, child.nodeId AS child_nodeId, child.name AS child_name
    """
    # 3. 查询Block基本信息
    query_block = """
    MATCH (b:Block {nodeId: $nodeId})
    RETURN b.name AS name, b.module_explaination AS explanation
    """

    block_result, direct_result, child_result = await asyncio.gather(
        neo4j.execute_query(query_block, {"nodeId": node_id}),
        neo4j.execute_query(query_direct, {"nodeId": node_id}),
        neo4j.execute_query(query_child, {"nodeId": node_id})
    )

    block_name = new_names.get(str(node_id), block_result[0]["name"] if block_result else f"Block_{node_id}")
    print(f"[INFO] Block名称: {block_name}")
    print(f"[INFO] 直连文件中的类: {len(direct_result)} 个")
    print(f"[INFO] 子模块中的类: {len(child_result)} 个")

    if not direct_result and not child_result:
        print("[WARN] 该Block下没有任何Class/Interface，无法生成UML")
        await neo4j.close()
        return

    # 构建 class_source_map 和 id_list
    id_list = ["Class&Interface"]
    class_source_map = {}
    seen = set()

    for record in direct_result:
        cname = record.get("class_name")
        if cname not in seen:
            id_list.append(cname)
            class_source_map[cname] = "__direct__"
            seen.add(cname)

    for record in child_result:
        cname = record.get("class_name")
        child_label = new_names.get(str(record["child_nodeId"]), record["child_name"])
        if cname not in seen:
            id_list.append(cname)
            class_source_map[cname] = child_label
            seen.add(cname)

    print(f"\n{'='*60}")
    print(f"共 {len(id_list)-1} 个类，分布在 {len(set(class_source_map.values()))} 个namespace中：")
    ns_summary = {}
    for cname, ns in class_source_map.items():
        if ns not in ns_summary:
            ns_summary[ns] = []
        ns_summary[ns].append(cname)
    for ns, classes in ns_summary.items():
        print(f"  [{ns}]: {', '.join(classes)}")
    print(f"{'='*60}\n")

    # 调用 chart_app 生成 hybrid_uml
    print("[INFO] 开始生成hybrid UML...")
    start_time = time.time()

    app = chart_app(llm, neo4j, node_list=id_list, type="hybrid_uml", skeleton=skeleton, class_source_map=class_source_map)
    result = await app.ainvoke(
        {},
        config={"configurable": {"thread_id": f"test-hybrid-uml-{node_id}"}}
    )

    elapsed = time.time() - start_time
    print(f"\n[INFO] 生成完成，耗时: {elapsed:.1f}s")

    # 输出结果
    output = result.get("output", "")
    mapping = result.get("mapping", {})
    id_list_result = result.get("id_list", [])
    token_stats = result.get("uml_token_stats")

    print(f"\n{'='*60}")
    print("UML输出:")
    print(f"{'='*60}")
    print(output)

    print(f"\n{'='*60}")
    print(f"Mapping ({len(mapping)} 项):")
    print(json.dumps(mapping, ensure_ascii=False, indent=2))

    if token_stats:
        print(f"\nToken统计:")
        print(f"  LLM调用次数: {token_stats.get('call_count', 'N/A')}")
        print(f"  输入token: {token_stats.get('total_input_tokens', 'N/A')}")
        print(f"  输出token: {token_stats.get('total_output_tokens', 'N/A')}")
        print(f"  总token: {token_stats.get('total_tokens', 'N/A')}")

    # 验证：检查输入中的类是否都出现在mapping中
    input_classes = set(id_list[1:])  # 去掉标志位
    mapped_classes = set(mapping.keys()) if isinstance(mapping, dict) else set()
    missing = input_classes - mapped_classes
    extra = mapped_classes - input_classes

    print(f"\n{'='*60}")
    print("覆盖率检查:")
    print(f"  输入类数: {len(input_classes)}")
    print(f"  映射类数: {len(mapped_classes)}")
    if missing:
        print(f"  [WARN] 缺失的类 ({len(missing)}): {', '.join(missing)}")
    if extra:
        print(f"  [WARN] 多出的类 ({len(extra)}): {', '.join(extra)}")
    if not missing and not extra:
        print(f"  [OK] 完全匹配！")
    print(f"{'='*60}")

    # 保存结果到文件
    output_path = os.path.join(PROJECT_ROOT, "graph", "test_hybrid_uml_result.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "node_id": node_id,
            "block_name": block_name,
            "skeleton": skeleton,
            "class_count": len(input_classes),
            "namespace_count": len(ns_summary),
            "mapping": mapping,
            "missing_classes": list(missing),
            "extra_classes": list(extra),
            "token_stats": token_stats,
            "elapsed_seconds": round(elapsed, 1),
            "mermaid_output": output,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n[INFO] 结果已保存: {output_path}")

    await neo4j.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="测试混合型Block的hybrid UML生成")
    parser.add_argument("node_id", type=int, help="Block的nodeId")
    parser.add_argument("--skeleton", action="store_true", help="启用源码精简模式")
    args = parser.parse_args()

    asyncio.run(test_hybrid_uml(args.node_id, skeleton=args.skeleton))
