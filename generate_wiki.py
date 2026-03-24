"""
Wiki生成脚本

根据输入的Neo4j节点ID，自动判断节点类型并调用对应的workflow生成wiki文档。

用法:
    python generate_wiki.py <nodeId>              # 生成单个节点的wiki
    python generate_wiki.py <nodeId1> <nodeId2>   # 生成多个节点的wiki
    python generate_wiki.py --all                  # 生成所有Block的wiki（root + 中间层 + 叶子）

示例:
    python generate_wiki.py 318
    python generate_wiki.py 318 327 335
    python generate_wiki.py --all
"""

import os
import sys
import json
import asyncio
import argparse
import time
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BLOCK_NAMES_PATH = os.path.join(PROJECT_ROOT, "graph", "block_new_names.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")


def load_block_names() -> Dict[str, str]:
    """加载Block名称映射"""
    if os.path.exists(BLOCK_NAMES_PATH):
        with open(BLOCK_NAMES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


async def detect_node_type(neo4j: Neo4jInterface, node_id: int) -> Dict[str, Any]:
    """
    检测节点类型，返回节点信息和分类结果。

    返回:
        {
            "node_id": int,
            "name": str,
            "labels": list,
            "type": "root_block" | "intermediate_block" | "hybrid_block" | "leaf_block" | "non_block",
            "has_child_blocks": bool,
            "has_direct_files": bool
        }
    """
    # 查询节点基本信息
    query_info = """
    MATCH (n)
    WHERE n.nodeId = $node_id
    RETURN n.name AS name, n.nodeId AS nodeId,
           n.module_explaination AS module_explaination,
           labels(n) AS labels
    """
    result = await neo4j.execute_query(query_info, {"node_id": node_id})
    if not result:
        return {"node_id": node_id, "type": "not_found"}

    record = result[0]
    labels = record.get("labels", [])
    name = record.get("name", "")

    # 非Block节点
    if "Block" not in labels:
        return {
            "node_id": node_id,
            "name": name,
            "labels": labels,
            "type": "non_block"
        }

    # 查询是否有子Block和直接File
    query_children = """
    MATCH (b:Block {nodeId: $node_id})
    OPTIONAL MATCH (b)-[:f2c]->(child:Block)
    OPTIONAL MATCH (b)-[:f2c]->(f:File)
    RETURN count(DISTINCT child) AS child_block_count,
           count(DISTINCT f) AS direct_file_count
    """
    children_result = await neo4j.execute_query(query_children, {"node_id": node_id})
    child_block_count = children_result[0]["child_block_count"]
    direct_file_count = children_result[0]["direct_file_count"]

    if name == "root":
        node_type = "root_block"
    elif direct_file_count > 0 and child_block_count > 0:
        node_type = "hybrid_block"
    elif direct_file_count > 0:
        node_type = "leaf_block"
    elif child_block_count > 0:
        node_type = "intermediate_block"
    else:
        node_type = "leaf_block"  # 无子节点也无文件，当作叶子处理

    return {
        "node_id": node_id,
        "name": name,
        "labels": labels,
        "type": node_type,
        "has_child_blocks": child_block_count > 0,
        "has_direct_files": direct_file_count > 0,
        "module_explaination": record.get("module_explaination")
    }


async def generate_root_wiki(llm: LLMInterface, neo4j: Neo4jInterface) -> Dict:
    """生成root Block的wiki"""
    from workflows.root_doc_workflow import root_doc_workflow

    print("[INFO] 调用 root_doc_workflow...")
    app = root_doc_workflow(llm, neo4j)
    result = await app.ainvoke(
        {},
        config={"configurable": {"thread_id": "gen-root-doc"}}
    )

    output = result.get("final_output", {})
    output_path = os.path.join(OUTPUT_DIR, "root_doc.json")
    print(f"[INFO] Root文档已保存: {output_path}")
    return output


async def generate_intermediate_wiki(
    llm: LLMInterface,
    neo4j: Neo4jInterface,
    node_info: Dict
) -> Dict:
    """生成中间层Block的wiki"""
    from chains.common_chains import ChainFactory
    from chains.prompts.internal_block_prompt import (
        INTERNAL_BLOCK_OVERVIEW_PROMPT,
        INTERNAL_BLOCK_CHILDREN_PROMPT
    )

    block_names = load_block_names()
    node_id = node_info["node_id"]
    block_name = block_names.get(str(node_id), node_info["name"])

    print(f"[INFO] 生成中间层Block文档: {block_name} ({node_id})")

    # 获取子Block列表
    query = """
    MATCH (parent:Block {nodeId: $block_id})-[:f2c]->(child:Block)
    RETURN child.nodeId AS nodeId,
           child.name AS name,
           child.module_explaination AS module_explaination
    ORDER BY child.name
    """
    children = await neo4j.execute_query(query, {"block_id": node_id})

    if not children:
        print(f"[WARN] {block_name} 没有子Block节点")
        return {"wiki": [], "source_id_list": []}

    # 准备子模块信息
    child_modules_info = []
    child_node_ids = []
    for idx, child in enumerate(children, 1):
        child_name = block_names.get(str(child["nodeId"]), child["name"])
        child_node_ids.append(child["nodeId"])
        child_modules_info.append(
            f"{idx}. 模块名称: {child_name}\n"
            f"   模块ID: {child['nodeId']}\n"
            f"   功能说明: {child['module_explaination'] or '暂无说明'}"
        )

    child_modules_str = "\n\n".join(child_modules_info)

    # 创建LLM链
    overview_chain = ChainFactory.create_generic_chain(llm, INTERNAL_BLOCK_OVERVIEW_PROMPT)
    children_chain = ChainFactory.create_generic_chain(llm, INTERNAL_BLOCK_CHILDREN_PROMPT)

    # 并发生成两个章节
    overview_content, children_content = await asyncio.gather(
        overview_chain.ainvoke({
            "block_name": block_name,
            "block_explaination": node_info.get("module_explaination") or "暂无说明",
            "child_modules_info": child_modules_str
        }),
        children_chain.ainvoke({
            "child_modules": child_modules_str
        })
    )

    children_data = json.loads(children_content)

    wiki_output = {
        "wiki": [
            {
                "markdown": overview_content,
                "neo4j_id": {"1": [node_id] + child_node_ids}
            },
            {
                "markdown": children_data["markdown"],
                "neo4j_id": children_data["mapping"]
            }
        ],
        "source_id_list": []
    }

    # 保存文件
    output_path = os.path.join(OUTPUT_DIR, f"{block_name}.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(wiki_output, f, ensure_ascii=False, indent=4)
    print(f"[INFO] 中间层Block文档已保存: {output_path}")

    return wiki_output


async def generate_leaf_wiki(
    llm: LLMInterface,
    neo4j: Neo4jInterface,
    node_info: Dict,
    skeleton: bool = False
) -> Dict:
    """生成叶子Block的wiki"""
    from workflows.block_module_workflow import block_module_workflow

    block_names = load_block_names()
    node_id = node_info["node_id"]
    block_name = block_names.get(str(node_id), node_info["name"])
    block_path = os.path.join(OUTPUT_DIR, block_name)

    print(f"[INFO] 生成叶子Block文档: {block_name} ({node_id})")

    id_name_path = {
        "block_id": node_id,
        "block_name": block_name,
        "block_path": block_path
    }

    app = block_module_workflow(llm, neo4j, id_name_path, skeleton=skeleton)
    result = await app.ainvoke(
        {},
        config={"configurable": {"thread_id": f"gen-leaf-{node_id}"}}
    )

    # 打印UML token统计
    uml_stats = result.get("uml_token_stats")
    if uml_stats:
        print(f"[TOKEN-UML] Block {block_name}: "
              f"调用{uml_stats['call_count']}次, "
              f"输入{uml_stats['total_input_tokens']:,}tokens, "
              f"输出{uml_stats['total_output_tokens']:,}tokens, "
              f"合计{uml_stats['total_tokens']:,}tokens")

    output_path = block_path + ".json"
    print(f"[INFO] 叶子Block文档已保存: {output_path}")

    # 读取生成的文件返回
    output = {}
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            output = json.load(f)
    # 附带UML token统计供上层汇总
    if uml_stats:
        output["uml_token_stats"] = uml_stats
    return output


async def generate_hybrid_wiki(
    llm: LLMInterface,
    neo4j: Neo4jInterface,
    node_info: Dict,
    skeleton: bool = False
) -> Dict:
    """生成混合型Block的wiki（同时有直连File和子Block）"""
    from workflows.hybrid_block_workflow import hybrid_block_workflow

    block_names = load_block_names()
    node_id = node_info["node_id"]
    block_name = block_names.get(str(node_id), node_info["name"])
    block_path = os.path.join(OUTPUT_DIR, block_name)

    print(f"[INFO] 生成混合型Block文档: {block_name} ({node_id})")

    id_name_path = {
        "block_id": node_id,
        "block_name": block_name,
        "block_path": block_path
    }

    app = hybrid_block_workflow(llm, neo4j, id_name_path, skeleton=skeleton)
    result = await app.ainvoke(
        {},
        config={"configurable": {"thread_id": f"gen-hybrid-{node_id}"}}
    )

    # 打印UML token统计
    uml_stats = result.get("uml_token_stats")
    if uml_stats:
        print(f"[TOKEN-UML] Block {block_name}: "
              f"调用{uml_stats['call_count']}次, "
              f"输入{uml_stats['total_input_tokens']:,}tokens, "
              f"输出{uml_stats['total_output_tokens']:,}tokens, "
              f"合计{uml_stats['total_tokens']:,}tokens")

    output_path = block_path + ".json"
    print(f"[INFO] 混合型Block文档已保存: {output_path}")

    output = {}
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            output = json.load(f)
    if uml_stats:
        output["uml_token_stats"] = uml_stats
    return output


async def generate_wiki_for_node(
    llm: LLMInterface,
    neo4j: Neo4jInterface,
    node_id: int,
    skeleton: bool = False
) -> Optional[Dict]:
    """根据节点ID自动判断类型并生成wiki"""
    node_info = await detect_node_type(neo4j, node_id)

    node_type = node_info["type"]

    if node_type == "not_found":
        print(f"[ERR] 节点 {node_id} 在Neo4j中不存在")
        return None

    if node_type == "non_block":
        print(f"[ERR] 节点 {node_id} 不是Block类型 (labels: {node_info['labels']})，当前只支持Block节点生成wiki")
        return None

    print(f"[INFO] 节点 {node_id} ({node_info['name']}) -> 类型: {node_type}")

    if node_type == "root_block":
        return await generate_root_wiki(llm, neo4j)
    elif node_type == "intermediate_block":
        return await generate_intermediate_wiki(llm, neo4j, node_info)
    elif node_type == "hybrid_block":
        return await generate_hybrid_wiki(llm, neo4j, node_info, skeleton=skeleton)
    elif node_type == "leaf_block":
        return await generate_leaf_wiki(llm, neo4j, node_info, skeleton=skeleton)


async def generate_all(llm: LLMInterface, neo4j: Neo4jInterface, skeleton: bool = False):
    """生成所有Block的wiki（root + 中间层 + 叶子）"""
    # 1. 获取所有Block节点
    query = """
    MATCH (b:Block)
    RETURN b.nodeId AS nodeId, b.name AS name
    """
    all_blocks = await neo4j.execute_query(query)
    print(f"[INFO] 共找到 {len(all_blocks)} 个Block节点")

    # 2. 先生成root文档
    print("\n=== 阶段1: 生成Root文档 ===")
    await generate_root_wiki(llm, neo4j)

    # 3. 检测所有非root Block的类型
    print("\n=== 阶段2: 检测Block类型 ===")
    intermediate_ids = []
    hybrid_ids = []
    leaf_ids = []

    for block in all_blocks:
        if block["name"] == "root":
            continue
        info = await detect_node_type(neo4j, block["nodeId"])
        if info["type"] == "intermediate_block":
            intermediate_ids.append(block["nodeId"])
        elif info["type"] == "hybrid_block":
            hybrid_ids.append(block["nodeId"])
        elif info["type"] == "leaf_block":
            leaf_ids.append(block["nodeId"])

    print(f"[INFO] 中间层Block: {len(intermediate_ids)} 个, 混合型Block: {len(hybrid_ids)} 个, 叶子Block: {len(leaf_ids)} 个")

    # 4. 生成中间层文档
    print("\n=== 阶段3: 生成中间层Block文档 ===")
    max_concurrent = int(os.environ.get("MAX_CONCURRENT_BLOCKS", "10"))
    semaphore = asyncio.Semaphore(max_concurrent)

    async def gen_with_semaphore(node_id, gen_func, **kwargs):
        async with semaphore:
            try:
                info = await detect_node_type(neo4j, node_id)
                return await gen_func(llm, neo4j, info, **kwargs)
            except Exception as e:
                print(f"[ERR] 节点 {node_id} 生成失败: {e}")
                return None

    tasks = [gen_with_semaphore(nid, generate_intermediate_wiki) for nid in intermediate_ids]
    await asyncio.gather(*tasks)

    # 5. 生成混合型文档
    print("\n=== 阶段4: 生成混合型Block文档 ===")
    tasks = [gen_with_semaphore(nid, generate_hybrid_wiki, skeleton=skeleton) for nid in hybrid_ids]
    await asyncio.gather(*tasks)

    # 6. 生成叶子文档
    print("\n=== 阶段5: 生成叶子Block文档 ===")
    tasks = [gen_with_semaphore(nid, generate_leaf_wiki, skeleton=skeleton) for nid in leaf_ids]
    await asyncio.gather(*tasks)

    print("\n=== 全部生成完成 ===")


async def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="根据Neo4j节点ID生成Wiki文档")
    parser.add_argument("node_ids", nargs="*", type=int, help="要生成wiki的节点ID列表")
    parser.add_argument("--all", action="store_true", help="生成所有Block的wiki")
    parser.add_argument("--model", default="gpt-4.1", help="LLM模型名称 (默认: gpt-4.1)")
    parser.add_argument("--provider", default="openai", help="LLM提供商: openai/claude/google (默认: openai)")
    parser.add_argument("--skeleton", action="store_true", help="精简UML源码输入，只保留类签名和字段，去掉方法体（减少60-80%%token）")
    args = parser.parse_args()

    if not args.all and not args.node_ids:
        parser.print_help()
        print("\n[ERR] 请提供节点ID或使用 --all 参数")
        sys.exit(1)

    # 初始化连接
    llm = LLMInterface(model_name=args.model, provider=args.provider)
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )

    if not await neo4j.test_connection():
        print("[ERR] Neo4j 连接失败，请检查 .env 配置")
        sys.exit(1)
    print("[INFO] Neo4j 连接成功")

    start_time = time.time()
    uml_total = {"call_count": 0, "total_input_tokens": 0, "total_output_tokens": 0, "total_tokens": 0}

    def accumulate_uml_stats(result):
        if result and result.get("uml_token_stats"):
            s = result["uml_token_stats"]
            for k in uml_total:
                uml_total[k] += s.get(k, 0)

    try:
        if args.skeleton:
            print("[INFO] 已启用源码精简模式（--skeleton）")

        if args.all:
            await generate_all(llm, neo4j, skeleton=args.skeleton)
        else:
            for node_id in args.node_ids:
                print(f"\n{'='*50}")
                result = await generate_wiki_for_node(llm, neo4j, node_id, skeleton=args.skeleton)
                if result:
                    wiki_count = len(result.get("wiki", []))
                    source_count = len(result.get("source_id_list", []))
                    print(f"[INFO] 生成完成: {wiki_count} 个章节, {source_count} 个源码定位")
                    accumulate_uml_stats(result)
    finally:
        neo4j.close()

    elapsed = time.time() - start_time
    print(f"\n[INFO] 总耗时: {elapsed:.1f}s")

    # 输出UML图生成token用量统计
    if uml_total["call_count"] > 0:
        print(f"\n{'='*50}")
        print(f"[TOKEN-UML] LLM调用次数: {uml_total['call_count']}")
        print(f"[TOKEN-UML] 输入token数: {uml_total['total_input_tokens']:,}")
        print(f"[TOKEN-UML] 输出token数: {uml_total['total_output_tokens']:,}")
        print(f"[TOKEN-UML] 总token数:   {uml_total['total_tokens']:,}")


if __name__ == "__main__":
    asyncio.run(main())
