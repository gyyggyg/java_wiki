"""
批量生成混合型Block Wiki脚本

读取 h_block.json 中的节点ID和输出路径，批量调用 hybrid_block_workflow 生成文档。

用法:
    python generate_hybrid_batch.py                         # 使用默认配置
    python generate_hybrid_batch.py --model gpt-4.1         # 指定模型
    python generate_hybrid_batch.py --skeleton              # 精简源码模式
    python generate_hybrid_batch.py --ids 18468 18475       # 只生成指定ID
"""

import os
import sys
import json
import asyncio
import argparse
import time
from typing import Dict, List
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from workflows.hybrid_block_workflow import hybrid_block_workflow

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
H_BLOCK_PATH = os.path.join(PROJECT_ROOT, "h_block.json")


def load_h_block() -> Dict[str, str]:
    """加载 h_block.json，返回 {nodeId: output_path} 映射"""
    with open(H_BLOCK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


async def generate_one(
    llm: LLMInterface,
    neo4j: Neo4jInterface,
    node_id: int,
    block_path: str,
    skeleton: bool = False
) -> Dict:
    """生成单个混合型Block的wiki"""
    block_name = os.path.basename(block_path)
    # 混合型Block存入 目录/目录名.meta.json
    actual_path = os.path.join(block_path, block_name + ".meta")

    id_name_path = {
        "block_id": node_id,
        "block_name": block_name,
        "block_path": actual_path
    }

    print(f"[INFO] 开始生成混合型Block: {block_name} (ID: {node_id})")
    print(f"       输出路径: {actual_path}.json")

    app = hybrid_block_workflow(llm, neo4j, id_name_path, skeleton=skeleton)
    result = await app.ainvoke(
        {},
        config={"configurable": {"thread_id": f"gen-hybrid-{node_id}"}}
    )

    uml_stats = result.get("uml_token_stats")
    if uml_stats:
        print(f"[TOKEN-UML] Block {block_name}: "
              f"调用{uml_stats['call_count']}次, "
              f"输入{uml_stats['total_input_tokens']:,}tokens, "
              f"输出{uml_stats['total_output_tokens']:,}tokens, "
              f"合计{uml_stats['total_tokens']:,}tokens")

    output_path = actual_path + ".json"
    if os.path.exists(output_path):
        print(f"[INFO] 文档已保存: {output_path}")
    else:
        print(f"[WARN] 输出文件未找到: {output_path}")

    return result


async def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="批量生成混合型Block Wiki")
    parser.add_argument("--model", default="gpt-4.1", help="LLM模型名称 (默认: gpt-4.1)")
    parser.add_argument("--provider", default="openai", help="LLM提供商: openai/claude/google (默认: openai)")
    parser.add_argument("--skeleton", action="store_true", help="精简UML源码输入")
    parser.add_argument("--ids", nargs="*", type=int, help="只生成指定的节点ID（默认全部）")
    args = parser.parse_args()

    # 读取h_block.json
    h_block = load_h_block()
    print(f"[INFO] 从 h_block.json 读取到 {len(h_block)} 个混合型Block")

    # 筛选要生成的ID
    if args.ids:
        target_ids = {str(nid) for nid in args.ids}
        h_block = {k: v for k, v in h_block.items() if k in target_ids}
        not_found = target_ids - set(h_block.keys())
        if not_found:
            print(f"[WARN] 以下ID在h_block.json中不存在: {not_found}")
        print(f"[INFO] 筛选后将生成 {len(h_block)} 个Block")

    if not h_block:
        print("[INFO] 没有需要生成的Block，退出")
        return

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
    max_concurrent = int(os.environ.get("MAX_CONCURRENT_BLOCKS", "10"))
    semaphore = asyncio.Semaphore(max_concurrent)

    uml_total = {"call_count": 0, "total_input_tokens": 0, "total_output_tokens": 0, "total_tokens": 0}
    success_count = 0
    fail_count = 0

    async def gen_with_semaphore(node_id: int, block_path: str):
        nonlocal success_count, fail_count
        async with semaphore:
            try:
                result = await generate_one(llm, neo4j, node_id, block_path, skeleton=args.skeleton)
                uml_stats = result.get("uml_token_stats")
                if uml_stats:
                    for k in uml_total:
                        uml_total[k] += uml_stats.get(k, 0)
                success_count += 1
            except Exception as e:
                print(f"[ERR] Block {node_id} 生成失败: {e}")
                fail_count += 1

    try:
        tasks = [
            gen_with_semaphore(int(node_id), block_path)
            for node_id, block_path in h_block.items()
        ]
        await asyncio.gather(*tasks)
    finally:
        neo4j.close()

    elapsed = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"[INFO] 批量生成完成: 成功 {success_count} 个, 失败 {fail_count} 个")
    print(f"[INFO] 总耗时: {elapsed:.1f}s")

    if uml_total["call_count"] > 0:
        print(f"[TOKEN-UML] LLM调用次数: {uml_total['call_count']}")
        print(f"[TOKEN-UML] 输入token数: {uml_total['total_input_tokens']:,}")
        print(f"[TOKEN-UML] 输出token数: {uml_total['total_output_tokens']:,}")
        print(f"[TOKEN-UML] 总token数:   {uml_total['total_tokens']:,}")


if __name__ == "__main__":
    asyncio.run(main())
