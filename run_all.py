"""
全局启动脚本 — 按顺序执行全部 Wiki 生成工作流

执行顺序：
  1. 模块取名（module_name）→ 生成 graph/block_new_names.json
  2. Root 文档（root_doc_workflow）→ 生成 output/root_doc.meta.json
  3. 中间层 Block（internal_block_workflow）→ 生成中间层文档 + file_leaves.json + file_block_leaves.json
  4. 叶子 Block + 混合 Block（并发执行）→ 读取步骤3输出的列表，生成各 Block 的 Wiki 文档

用法:
    python run_all.py                          # 默认配置
    python run_all.py --model gpt-4.1          # 指定模型
    python run_all.py --skeleton               # 精简 UML 源码输入
    python run_all.py --skip-name              # 跳过取名步骤（已有 block_new_names.json）
    python run_all.py --skip-root              # 跳过 root 文档生成
    python run_all.py --skip-internal          # 跳过中间层生成
    python run_all.py --only-leaves            # 只执行叶子+混合 Block 生成（需已有 file_leaves.json）
"""

import os
import sys
import json
import asyncio
import argparse
import time
import logging
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
INTERNAL_RESULT_DIR = os.path.join(PROJECT_ROOT, "internal_result")
BLOCK_NAMES_PATH = os.path.join(PROJECT_ROOT, "graph", "block_new_names.json")
FILE_LEAVES_PATH = os.path.join(INTERNAL_RESULT_DIR, "file_leaves.json")
FILE_BLOCK_LEAVES_PATH = os.path.join(INTERNAL_RESULT_DIR, "file_block_leaves.json")


# ====================== 日志配置 ======================
def setup_logger() -> logging.Logger:
    """配置日志：同时输出到控制台和文件"""
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"run_all_{timestamp}.log")

    logger = logging.getLogger("run_all")
    logger.setLevel(logging.DEBUG)

    # 文件 handler：记录 DEBUG 及以上级别
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # 控制台 handler：记录 INFO 及以上级别
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"日志文件: {log_file}")
    return logger


def load_block_names() -> Dict[str, str]:
    if os.path.exists(BLOCK_NAMES_PATH):
        with open(BLOCK_NAMES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ====================== 步骤 1: 模块取名 ======================
async def step1_module_name(llm: LLMInterface, neo4j: Neo4jInterface, logger: logging.Logger):
    logger.info("=" * 60)
    logger.info("[步骤 1/4] 模块取名（module_name）")
    logger.info("=" * 60)

    from graph.module_name import get_block_newname

    result = await get_block_newname(llm, neo4j)
    if result:
        logger.info(f"共生成 {len(result)} 个Block的新名称，已保存至 {BLOCK_NAMES_PATH}")
        logger.debug(f"名称映射（前10项）: {dict(list(result.items())[:10])}")
    else:
        logger.warning("未生成任何名称")
    return result


# ====================== 步骤 2: Root 文档 ======================
async def step2_root_doc(llm: LLMInterface, neo4j: Neo4jInterface, logger: logging.Logger):
    logger.info("=" * 60)
    logger.info("[步骤 2/4] Root 文档生成")
    logger.info("=" * 60)

    from workflows.root_doc_workflow import root_doc_workflow

    app = root_doc_workflow(llm, neo4j)
    result = await app.ainvoke(
        {},
        config={"configurable": {"thread_id": "root-doc-generation"}}
    )
    logger.info("Root 文档生成完成 → output/root_doc.meta.json")
    return result


# ====================== 步骤 3: 中间层 Block ======================
async def step3_internal_blocks(llm: LLMInterface, neo4j: Neo4jInterface, logger: logging.Logger):
    logger.info("=" * 60)
    logger.info("[步骤 3/4] 中间层 Block 文档生成")
    logger.info("=" * 60)

    from workflows.internal_block_workflow import internal_block_workflow

    app = internal_block_workflow(llm, neo4j)
    result = await app.ainvoke(
        {},
        config={"configurable": {"thread_id": "internal-block-generation"}}
    )

    final = result.get("final_output", {})
    stats = final.get("stats", {})
    logger.info("中间层 Block 生成完成:")
    logger.info(f"  中间层Block: {stats.get('total_intermediate', 0)} 个")
    logger.info(f"  纯File叶子Block: {stats.get('total_file_leaves', 0)} 个")
    logger.info(f"  混合叶子Block: {stats.get('total_file_block_leaves', 0)} 个")

    # 记录叶子和混合 Block 的详细列表
    file_leaves = final.get("file_leaves", {})
    file_block_leaves = final.get("file_block_leaves", {})
    if file_leaves:
        logger.debug(f"叶子Block列表: {json.dumps(file_leaves, ensure_ascii=False)}")
    if file_block_leaves:
        logger.debug(f"混合Block列表: {json.dumps(file_block_leaves, ensure_ascii=False)}")

    return result


# ====================== 步骤 4: 叶子 + 混合 Block（并发） ======================
async def step4_leaf_and_hybrid(
    llm: LLMInterface,
    neo4j: Neo4jInterface,
    logger: logging.Logger,
    skeleton: bool = False,
    max_concurrent: int = 10
):
    logger.info("=" * 60)
    logger.info("[步骤 4/4] 叶子 Block + 混合 Block 并发生成")
    logger.info("=" * 60)

    from workflows.block_module_workflow import block_module_workflow
    from workflows.hybrid_block_workflow import hybrid_block_workflow

    block_names = load_block_names()

    # 读取 file_leaves.json（叶子 Block）
    leaf_blocks = {}
    if os.path.exists(FILE_LEAVES_PATH):
        with open(FILE_LEAVES_PATH, "r", encoding="utf-8") as f:
            leaf_blocks = json.load(f)
        logger.info(f"读取到 {len(leaf_blocks)} 个叶子Block（来自 {FILE_LEAVES_PATH}）")
    else:
        logger.warning(f"未找到 {FILE_LEAVES_PATH}，跳过叶子Block生成")

    # 读取 file_block_leaves.json（混合 Block）
    hybrid_blocks = {}
    if os.path.exists(FILE_BLOCK_LEAVES_PATH):
        with open(FILE_BLOCK_LEAVES_PATH, "r", encoding="utf-8") as f:
            hybrid_blocks = json.load(f)
        logger.info(f"读取到 {len(hybrid_blocks)} 个混合Block（来自 {FILE_BLOCK_LEAVES_PATH}）")
    else:
        logger.warning(f"未找到 {FILE_BLOCK_LEAVES_PATH}，跳过混合Block生成")

    if not leaf_blocks and not hybrid_blocks:
        logger.info("无需生成任何Block，跳过")
        return

    semaphore = asyncio.Semaphore(max_concurrent)
    success_count = 0
    fail_count = 0
    failed_blocks = []

    async def gen_leaf(node_id_str: str, folder_path: str):
        nonlocal success_count, fail_count
        node_id = int(node_id_str)
        block_name = block_names.get(node_id_str, os.path.basename(folder_path))
        async with semaphore:
            start = time.time()
            try:
                id_name_path = {
                    "block_id": node_id,
                    "block_name": block_name,
                    "block_path": folder_path
                }
                logger.info(f"[LEAF] 开始: {block_name} (ID: {node_id})")
                app = block_module_workflow(llm, neo4j, id_name_path, skeleton=skeleton)
                result = await app.ainvoke(
                    {},
                    config={"configurable": {"thread_id": f"gen-leaf-{node_id}"}}
                )
                elapsed = time.time() - start
                logger.info(f"[LEAF] 完成: {block_name} → {folder_path}.meta.json ({elapsed:.1f}s)")
                success_count += 1
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"[LEAF] 失败: {block_name} (ID: {node_id}) ({elapsed:.1f}s): {e}", exc_info=True)
                failed_blocks.append({"type": "leaf", "id": node_id, "name": block_name, "error": str(e)})
                fail_count += 1

    async def gen_hybrid(node_id_str: str, folder_path: str):
        nonlocal success_count, fail_count
        node_id = int(node_id_str)
        block_name = block_names.get(node_id_str, os.path.basename(folder_path))
        actual_path = os.path.join(folder_path, block_name + ".meta")
        async with semaphore:
            start = time.time()
            try:
                id_name_path = {
                    "block_id": node_id,
                    "block_name": block_name,
                    "block_path": actual_path
                }
                logger.info(f"[HYBRID] 开始: {block_name} (ID: {node_id})")
                app = hybrid_block_workflow(llm, neo4j, id_name_path, skeleton=skeleton)
                result = await app.ainvoke(
                    {},
                    config={"configurable": {"thread_id": f"gen-hybrid-{node_id}"}}
                )
                elapsed = time.time() - start
                logger.info(f"[HYBRID] 完成: {block_name} → {actual_path}.json ({elapsed:.1f}s)")
                success_count += 1
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"[HYBRID] 失败: {block_name} (ID: {node_id}) ({elapsed:.1f}s): {e}", exc_info=True)
                failed_blocks.append({"type": "hybrid", "id": node_id, "name": block_name, "error": str(e)})
                fail_count += 1

    # 叶子和混合 Block 并发执行
    tasks = []
    for node_id_str, folder_path in leaf_blocks.items():
        tasks.append(gen_leaf(node_id_str, folder_path))
    for node_id_str, folder_path in hybrid_blocks.items():
        tasks.append(gen_hybrid(node_id_str, folder_path))

    logger.info(f"共 {len(tasks)} 个任务（叶子 {len(leaf_blocks)} + 混合 {len(hybrid_blocks)}），最大并发 {max_concurrent}")
    await asyncio.gather(*tasks)

    logger.info(f"步骤4完成: 成功 {success_count} 个, 失败 {fail_count} 个")
    if failed_blocks:
        logger.warning(f"失败的Block列表:")
        for fb in failed_blocks:
            logger.warning(f"  [{fb['type']}] {fb['name']} (ID: {fb['id']}): {fb['error']}")


# ====================== 主函数 ======================
async def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="全局启动脚本 — 按顺序执行全部 Wiki 生成工作流")
    parser.add_argument("--model", default="gpt-5-mini", help="LLM模型名称 (默认: gpt-5-mini)")
    parser.add_argument("--provider", default="openai", help="LLM提供商: openai/claude/google (默认: openai)")
    parser.add_argument("--skeleton", action="store_true", help="精简UML源码输入（减少token）")
    parser.add_argument("--skip-name", action="store_true", help="跳过步骤1（模块取名），使用已有的 block_new_names.json")
    parser.add_argument("--skip-root", action="store_true", help="跳过步骤2（Root文档生成）")
    parser.add_argument("--skip-internal", action="store_true", help="跳过步骤3（中间层Block生成）")
    parser.add_argument("--only-leaves", action="store_true", help="只执行步骤4（需已有 file_leaves.json 和 file_block_leaves.json）")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logger = setup_logger()

    # 记录启动参数
    logger.info(f"启动参数: model={args.model}, provider={args.provider}, skeleton={args.skeleton}")
    logger.info(f"跳过选项: skip_name={args.skip_name}, skip_root={args.skip_root}, "
                f"skip_internal={args.skip_internal}, only_leaves={args.only_leaves}")

    # 初始化连接
    llm = LLMInterface(model_name=args.model, provider=args.provider)
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )

    if not await neo4j.test_connection():
        logger.error("Neo4j 连接失败，请检查 .env 配置")
        sys.exit(1)
    logger.info("Neo4j 连接成功")

    if args.skeleton:
        logger.info("已启用源码精简模式（--skeleton）")

    total_start = time.time()
    max_concurrent = int(os.environ.get("MAX_CONCURRENT_BLOCKS", "10"))
    logger.info(f"最大并发数: {max_concurrent}")

    step_times = {}

    try:
        # 步骤 1: 模块取名
        if not args.only_leaves and not args.skip_name:
            step_start = time.time()
            await step1_module_name(llm, neo4j, logger)
            step_times["步骤1-模块取名"] = time.time() - step_start
            logger.info(f"步骤1耗时: {step_times['步骤1-模块取名']:.1f}s")
        else:
            if os.path.exists(BLOCK_NAMES_PATH):
                logger.info(f"跳过步骤1，使用已有 block_new_names.json（{len(load_block_names())} 个名称）")
            else:
                logger.error("跳过步骤1但 block_new_names.json 不存在，后续步骤可能失败")

        # 步骤 2: Root 文档
        if not args.only_leaves and not args.skip_root:
            step_start = time.time()
            await step2_root_doc(llm, neo4j, logger)
            step_times["步骤2-Root文档"] = time.time() - step_start
            logger.info(f"步骤2耗时: {step_times['步骤2-Root文档']:.1f}s")
        else:
            logger.info("跳过步骤2（Root文档）")

        # 步骤 3: 中间层 Block
        if not args.only_leaves and not args.skip_internal:
            step_start = time.time()
            await step3_internal_blocks(llm, neo4j, logger)
            step_times["步骤3-中间层Block"] = time.time() - step_start
            logger.info(f"步骤3耗时: {step_times['步骤3-中间层Block']:.1f}s")
        else:
            logger.info("跳过步骤3（中间层Block）")

        # 步骤 4 + 步骤 5：并发执行
        parallel_tasks = []

        # 步骤 4: 叶子 + 混合 Block
        step4_start = time.time()
        parallel_tasks.append(step4_leaf_and_hybrid(llm, neo4j, logger, skeleton=args.skeleton, max_concurrent=max_concurrent))

        # 步骤 5: 专项文档（与步骤4并发）
        run_extra = not args.skip_extra and not args.only_leaves
        step5_start = time.time()
        if run_extra:
            parallel_tasks.append(step5_extra_docs(logger))
        else:
            logger.info("跳过步骤5（专项文档）")

        await asyncio.gather(*parallel_tasks)

        step_times["步骤4-叶子+混合Block"] = time.time() - step4_start
        logger.info(f"步骤4耗时: {step_times['步骤4-叶子+混合Block']:.1f}s")
        if run_extra:
            step_times["步骤5-专项文档"] = time.time() - step5_start
            logger.info(f"步骤5耗时: {step_times['步骤5-专项文档']:.1f}s")

        # 步骤 5: 可选章节
        if not args.only_leaves and not args.skip_optional:
            step_start = time.time()
            await step5_optional_sections(llm, neo4j, logger)
            step_times["步骤5-可选章节"] = time.time() - step_start
            logger.info(f"步骤5耗时: {step_times['步骤5-可选章节']:.1f}s")
        else:
            logger.info("跳过步骤5（可选章节）")

    finally:
        neo4j.close()

    total_elapsed = time.time() - total_start

    # 最终汇总
    logger.info("=" * 60)
    logger.info("执行汇总")
    logger.info("=" * 60)
    for step_name, elapsed in step_times.items():
        logger.info(f"  {step_name}: {elapsed:.1f}s ({elapsed/60:.1f}min)")
    logger.info(f"  总耗时: {total_elapsed:.1f}s ({total_elapsed/60:.1f}min)")
    logger.info("全部完成！")


if __name__ == "__main__":
    asyncio.run(main())
