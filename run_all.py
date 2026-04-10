"""
全局启动脚本 — 按顺序执行全部 Wiki 生成工作流

执行顺序：
  1. 模块取名（module_name）→ 生成 graph/block_new_names.json
  2. Root 文档（root_doc_workflow）→ 生成 output/root_doc.meta.json
       · 如配置了 SOURCE_ROOT_PATH，会由 Claude CLI 补充扩展章节（技术栈/分层/核心类/业务流程/数据模型）
  3. 中间层 Block（internal_block_workflow）→ 生成中间层文档 + file_leaves.json + file_block_leaves.json
  4. 叶子 Block + 混合 Block（并发执行）→ 读取步骤3输出的列表，生成各 Block 的 Wiki 文档
  5. API 文档（StrictApiDocGenerator）→ 扫描Controller生成API接口文档（与步骤4并发）
  6. 后端集成清单（BackendInterfaceGenerator）→ 扫描MQ/DB/Cache/OSS依赖生成.meta.json（与步骤4/5并发）
  7. RabbitMQ 消息流分析（analyzer_v3.RabbitMQAnalyzer）→ 生成消息流转.meta.json（与步骤4/5/6并发）
  8. [可选，默认关闭] Block 级可选章节（optional_sections_workflow）
       → 追加状态机/消息队列等可选章节到各 Block Wiki
       · 依赖 step4 的产物（串行在并发块之后）
       · 需要 SOURCE_ROOT_PATH + 本地 claude CLI
       · 默认关闭：会对所有 Block 做 LLM 扫描 + Claude CLI 生成，代价较高
       · 需要显式 --run-optional 启用

用法:
    python run_all.py                          # 默认配置（跑 step1~7；step8 不跑）
    python run_all.py --model gpt-4.1          # 指定模型
    python run_all.py --no-skeleton            # 关闭源码精简模式
    python run_all.py --skip-name              # 跳过取名步骤（已有 block_new_names.json）
    python run_all.py --skip-root              # 跳过 root 文档生成
    python run_all.py --skip-internal          # 跳过中间层生成
    python run_all.py --skip-api               # 跳过 API 文档生成
    python run_all.py --skip-backend           # 跳过后端集成清单生成
    python run_all.py --skip-rabbitmq          # 跳过 RabbitMQ 消息流分析
    python run_all.py --run-optional           # 启用步骤8（Block 级可选章节，开销大）
    python run_all.py --only-leaves            # 只执行叶子+混合 Block 生成（需已有 file_leaves.json）

可选环境变量（.env）:
    SOURCE_ROOT_PATH       Java 源码根目录；启用后 step2 生成扩展章节，--run-optional 时 step8 需要
    CLAUDE_MODEL           Claude CLI 使用的模型，默认 "sonnet"
    AGENT_TIMEOUT          Claude CLI 单次调用超时（秒），默认 300/600
    AGENT_MAX_RETRIES      Claude CLI 调用失败重试次数，默认 2
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
API_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "API说明文档")
BACKEND_INTERFACES_PATH = os.path.join(OUTPUT_DIR, "后端接口清单.meta.json")
RABBITMQ_REPORT_PATH = os.path.join(OUTPUT_DIR, "RabbitMQ消息流分析.meta.json")


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
    logger.info("[步骤 2] Root 文档生成")
    logger.info("=" * 60)

    from workflows.root_doc_workflow import root_doc_workflow

    # 读取源码根目录：若配置则启用 Root 文档的扩展章节（tech_stack / layered_architecture /
    # key_entities / core_flows / data_model），由 Claude CLI 实际读源码生成
    source_root = os.environ.get("SOURCE_ROOT_PATH", "")
    if source_root:
        logger.info(f"启用 Root 扩展章节（Claude CLI 读源码）: SOURCE_ROOT_PATH={source_root}")
    else:
        logger.info("未配置 SOURCE_ROOT_PATH，跳过 Root 扩展章节（仅生成 1-3 章基础内容）")

    app = root_doc_workflow(llm, neo4j, source_root=source_root)
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


# ====================== 步骤 5: API 文档 ======================
async def step5_api_docs(logger: logging.Logger):
    """
    调用 Api_and_Rabbitmq/generate_api_docs.py 的 StrictApiDocGenerator 生成 API 接口文档。
    该生成器是同步的，使用 asyncio.to_thread 运行以避免阻塞事件循环。
    """
    logger.info("=" * 60)
    logger.info("[步骤 5] API 文档生成")
    logger.info("=" * 60)

    # StrictApiDocGenerator 在模块级读取 NEO4J_* 和 LLM_* 环境变量，
    # 这里先把 run_all 使用的 WIKI_NEO4J_* / OPENAI_API_KEY / BASE_URL 映射到它期望的名字，
    # 以便模块导入时使用正确的连接配置
    os.environ.setdefault("NEO4J_URI", os.environ.get("WIKI_NEO4J_URI", ""))
    os.environ.setdefault("NEO4J_USER", os.environ.get("WIKI_NEO4J_USER", ""))
    os.environ.setdefault("NEO4J_PASSWORD", os.environ.get("WIKI_NEO4J_PASSWORD", ""))
    # generate_api_docs.py 期望 LLM_API_KEY / LLM_BASE_URL，而 .env 里用的是 OPENAI_API_KEY / BASE_URL
    os.environ.setdefault("LLM_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
    os.environ.setdefault("LLM_BASE_URL", os.environ.get("BASE_URL", "https://api.zhec.moe/v1"))
    if not os.environ.get("LLM_API_KEY"):
        logger.warning("[步骤5] 未检测到 LLM_API_KEY / OPENAI_API_KEY，生成的 API 文档将不包含 LLM 增强内容")

    # 延迟导入，确保上面的环境变量在模块加载前已生效
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "Api_and_Rabbitmq"))
    from generate_api_docs import StrictApiDocGenerator  # type: ignore

    os.makedirs(API_OUTPUT_DIR, exist_ok=True)

    def _run():
        generator = StrictApiDocGenerator(
            os.environ["WIKI_NEO4J_URI"],
            os.environ["WIKI_NEO4J_USER"],
            os.environ["WIKI_NEO4J_PASSWORD"],
        )
        try:
            generator.generate_all(output_dir=API_OUTPUT_DIR)
        finally:
            generator.close()

    try:
        await asyncio.to_thread(_run)
        logger.info(f"API 文档生成完成 → {API_OUTPUT_DIR}")
    except Exception as e:
        logger.error(f"API 文档生成失败: {e}", exc_info=True)


# ====================== 步骤 6: 后端集成清单 ======================
async def step6_backend_interfaces(logger: logging.Logger):
    """
    调用 Api_and_Rabbitmq/generate_backend_interfaces.py 的 BackendInterfaceGenerator，
    扫描 RabbitMQ/定时任务/ES/Mongo/Redis/OSS 依赖，生成 Markdown 报告。
    该生成器是同步的，不调 LLM，使用 asyncio.to_thread 运行。
    """
    logger.info("=" * 60)
    logger.info("[步骤 6] 后端集成清单生成")
    logger.info("=" * 60)

    # 与 step5 相同，同步 WIKI_NEO4J_* → NEO4J_*
    os.environ.setdefault("NEO4J_URI", os.environ.get("WIKI_NEO4J_URI", ""))
    os.environ.setdefault("NEO4J_USER", os.environ.get("WIKI_NEO4J_USER", ""))
    os.environ.setdefault("NEO4J_PASSWORD", os.environ.get("WIKI_NEO4J_PASSWORD", ""))

    sys.path.insert(0, os.path.join(PROJECT_ROOT, "Api_and_Rabbitmq"))
    from generate_backend_interfaces import BackendInterfaceGenerator  # type: ignore

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    def _run():
        generator = BackendInterfaceGenerator(
            os.environ["WIKI_NEO4J_URI"],
            os.environ["WIKI_NEO4J_USER"],
            os.environ["WIKI_NEO4J_PASSWORD"],
        )
        try:
            generator.generate_report(output_file=BACKEND_INTERFACES_PATH)
        finally:
            generator.close()

    try:
        await asyncio.to_thread(_run)
        logger.info(f"后端集成清单生成完成 → {BACKEND_INTERFACES_PATH}")
    except Exception as e:
        logger.error(f"后端集成清单生成失败: {e}", exc_info=True)


# ====================== 步骤 7: RabbitMQ 消息流分析 ======================
async def step7_rabbitmq_docs(logger: logging.Logger):
    """
    调用 Api_and_Rabbitmq/rabbitmq_analyzer/analyzer_v3.py 的 RabbitMQAnalyzer，
    生成 RabbitMQ 消息流转 .meta.json 报告。
    analyzer_v3 使用 LLM 做结构化提取 + 确定性匹配 + Mermaid 流程图，
    输出天然符合 wiki .meta.json 格式。
    """
    logger.info("=" * 60)
    logger.info("[步骤 7] RabbitMQ 消息流分析")
    logger.info("=" * 60)

    # analyzer_v3 在模块级读取 NEO4J_*、LLM_*、PROJECT_ROOT 环境变量
    os.environ.setdefault("NEO4J_URI", os.environ.get("WIKI_NEO4J_URI", ""))
    os.environ.setdefault("NEO4J_USER", os.environ.get("WIKI_NEO4J_USER", ""))
    os.environ.setdefault("NEO4J_PASSWORD", os.environ.get("WIKI_NEO4J_PASSWORD", ""))
    # 与 generate_api_docs.py 的 ROOT_PREFIX 保持一致
    os.environ.setdefault("PROJECT_ROOT", os.environ.get("ROOT_PREFIX", "mall"))

    # 校验 LLM 凭证（v3 默认使用 OPENAI_API_KEY）
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key or api_key == "your_openai_api_key_here":
        logger.warning("未检测到有效的 OPENAI_API_KEY，跳过步骤7（RabbitMQ 消息流分析）")
        return

    # 把 rabbitmq_analyzer 目录加入 sys.path —— analyzer_v3 内部用相对 import `from llm_interface import LLMInterface`
    analyzer_dir = os.path.join(PROJECT_ROOT, "Api_and_Rabbitmq", "rabbitmq_analyzer")
    if analyzer_dir not in sys.path:
        sys.path.insert(0, analyzer_dir)

    try:
        from analyzer_v3 import RabbitMQAnalyzer  # type: ignore
    except Exception as e:
        logger.error(f"导入 analyzer_v3 失败: {e}", exc_info=True)
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        analyzer = RabbitMQAnalyzer()
        await analyzer.run(output_path=RABBITMQ_REPORT_PATH)
        logger.info(f"RabbitMQ 消息流分析完成 → {RABBITMQ_REPORT_PATH}")
    except Exception as e:
        logger.error(f"RabbitMQ 消息流分析失败: {e}", exc_info=True)


# ====================== 步骤 8: Block 级可选章节 ======================
async def step8_optional_sections(
    llm: LLMInterface,
    neo4j: Neo4jInterface,
    logger: logging.Logger,
):
    """
    扫描 step4 生成的所有 Block Wiki，为符合条件的 Block 追加可选章节
    （状态机、消息队列等），由 Claude CLI 自主读源码生成。
    依赖：
      - step4 必须先完成（本步骤读 output/ 下的 .meta.json）
      - SOURCE_ROOT_PATH 环境变量（Java 源码根）
      - 本地已安装 claude CLI
    """
    logger.info("=" * 60)
    logger.info("[步骤 8] Block 级可选章节生成")
    logger.info("=" * 60)

    source_root = os.environ.get("SOURCE_ROOT_PATH", "")
    if not source_root:
        logger.warning("未配置 SOURCE_ROOT_PATH，跳过步骤 8（Block 级可选章节）")
        return

    # 校验 claude CLI 是否可用
    import shutil
    if not shutil.which("claude"):
        logger.warning("未找到 claude CLI，跳过步骤 8（请先安装 Claude Code）")
        return

    from workflows.optional_sections_workflow import optional_sections_workflow

    app = optional_sections_workflow(
        neo4j_interface=neo4j,
        llm_interface=llm,
        wiki_path=OUTPUT_DIR,
        source_root=source_root,
    )

    try:
        result = await app.ainvoke(
            {
                "target_block": None,    # None = 处理所有 block
                "target_section": None,  # None = 处理所有可选章节类型
            },
            config={"configurable": {"thread_id": "optional-sections-generation"}}
        )
        final = result.get("final_output", {})
        generated_count = len(final.get("generated_results", []))
        logger.info(f"Block 级可选章节生成完成：共追加 {generated_count} 个章节")
    except Exception as e:
        logger.error(f"步骤 8 失败: {e}", exc_info=True)


# ====================== 主函数 ======================
async def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="全局启动脚本 — 按顺序执行全部 Wiki 生成工作流")
    parser.add_argument("--model", default=None, help="LLM模型名称（默认读取 .env 中的 LLM_MODEL）")
    parser.add_argument("--provider", default=None, help="LLM提供商: openai/claude/google（默认读取 .env 中的 LLM_PROVIDER）")
    parser.add_argument(
        "--skeleton",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="精简UML源码输入（减少token）。默认开启，使用 --no-skeleton 关闭"
    )
    parser.add_argument("--skip-name", action="store_true", help="跳过步骤1（模块取名），使用已有的 block_new_names.json")
    parser.add_argument("--skip-root", action="store_true", help="跳过步骤2（Root文档生成）")
    parser.add_argument("--skip-internal", action="store_true", help="跳过步骤3（中间层Block生成）")
    parser.add_argument("--skip-api", action="store_true", help="跳过步骤5（API文档生成）")
    parser.add_argument("--skip-backend", action="store_true", help="跳过步骤6（后端集成清单生成）")
    parser.add_argument("--skip-rabbitmq", action="store_true", help="跳过步骤7（RabbitMQ 消息流分析）")
    parser.add_argument("--run-optional", action="store_true",
                        help="启用步骤8（Block 级可选章节，状态机/MQ 等）。默认关闭，因为会对所有 Block 做 LLM 扫描 + Claude CLI 内容生成，代价较高")
    parser.add_argument("--only-leaves", action="store_true", help="只执行步骤4（需已有 file_leaves.json 和 file_block_leaves.json）")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logger = setup_logger()

    # 记录启动参数
    logger.info(f"启动参数: model={args.model}, provider={args.provider}, skeleton={args.skeleton}")
    logger.info(f"跳过选项: skip_name={args.skip_name}, skip_root={args.skip_root}, "
                f"skip_internal={args.skip_internal}, skip_api={args.skip_api}, "
                f"skip_backend={args.skip_backend}, skip_rabbitmq={args.skip_rabbitmq}, "
                f"run_optional={args.run_optional}, only_leaves={args.only_leaves}")

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
        logger.info("已启用源码精简模式（默认开启，使用 --no-skeleton 关闭）")
    else:
        logger.info("已关闭源码精简模式（--no-skeleton）")

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

        # 步骤 4 + 5 + 6 + 7：并发执行（Block 文档、API 文档、后端集成清单、RabbitMQ 消息流相互独立）
        parallel_tasks = []

        # 步骤 4: 叶子 + 混合 Block
        step4_start = time.time()
        parallel_tasks.append(
            step4_leaf_and_hybrid(llm, neo4j, logger, skeleton=args.skeleton, max_concurrent=max_concurrent)
        )

        # 步骤 5: API 文档（与步骤4并发）
        run_api = not args.skip_api and not args.only_leaves
        step5_start = time.time()
        if run_api:
            parallel_tasks.append(step5_api_docs(logger))
        else:
            logger.info("跳过步骤5（API文档）")

        # 步骤 6: 后端集成清单（与步骤4/5并发）
        run_backend = not args.skip_backend and not args.only_leaves
        step6_start = time.time()
        if run_backend:
            parallel_tasks.append(step6_backend_interfaces(logger))
        else:
            logger.info("跳过步骤6（后端集成清单）")

        # 步骤 7: RabbitMQ 消息流分析（与步骤4/5/6并发）
        run_rabbitmq = not args.skip_rabbitmq and not args.only_leaves
        step7_start = time.time()
        if run_rabbitmq:
            parallel_tasks.append(step7_rabbitmq_docs(logger))
        else:
            logger.info("跳过步骤7（RabbitMQ 消息流分析）")

        await asyncio.gather(*parallel_tasks)

        step_times["步骤4-叶子+混合Block"] = time.time() - step4_start
        logger.info(f"步骤4耗时: {step_times['步骤4-叶子+混合Block']:.1f}s")
        if run_api:
            step_times["步骤5-API文档"] = time.time() - step5_start
            logger.info(f"步骤5耗时: {step_times['步骤5-API文档']:.1f}s")
        if run_backend:
            step_times["步骤6-后端集成清单"] = time.time() - step6_start
            logger.info(f"步骤6耗时: {step_times['步骤6-后端集成清单']:.1f}s")
        if run_rabbitmq:
            step_times["步骤7-RabbitMQ消息流"] = time.time() - step7_start
            logger.info(f"步骤7耗时: {step_times['步骤7-RabbitMQ消息流']:.1f}s")

        # 步骤 8: Block 级可选章节（默认跳过，需要 --run-optional 显式启用）
        #   - 依赖 step4 的产物（必须串行在 gather 之后）
        #   - 会对所有 Block 做 LLM 扫描 + Claude CLI 内容生成，代价较高
        #   - 需要 SOURCE_ROOT_PATH 和本地 claude CLI
        run_optional = args.run_optional and not args.only_leaves
        if run_optional:
            step8_start = time.time()
            await step8_optional_sections(llm, neo4j, logger)
            step_times["步骤8-Block可选章节"] = time.time() - step8_start
            logger.info(f"步骤8耗时: {step_times['步骤8-Block可选章节']:.1f}s")
        else:
            logger.info("跳过步骤8（Block 级可选章节）—— 如需启用请加 --run-optional")

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
