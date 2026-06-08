"""
CLI 入口：基于 new_wiki_index.json 的聚类结果，为「业务领域 (wlx)」下 7 个子分类
生成业务流 wiki（章节 §1 概述 / §2 触发入口 / §3 时序图 / §6 组件索引）。

每个分类产出一个 JSON 文件，结构对齐 `output/wiki_result/总揽.json`：
    {"markdown_content": [SectionNode], "source_id": []}

用法:
    python category_wiki/generate.py
    python category_wiki/generate.py --dry-run                    # 只打印将要处理的分类
    python category_wiki/generate.py --category "业务领域 (wlx)/打卡系统"   # 只跑指定分类
    python category_wiki/generate.py --concurrency 2              # 分类间并发（默认 1）
    python category_wiki/generate.py --wiki-root /path/to/wiki_result  # 覆盖默认路径
"""

import os
import sys
import json
import asyncio
import argparse
import logging
from datetime import datetime
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface

from category_wiki.scope import load_new_wiki_index
from category_wiki.workflow import generate_wiki_for_category


# ============ 路径配置 ============
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CW_DIR = os.path.join(PROJECT_ROOT, "category_wiki")
DEFAULT_NEW_INDEX = os.path.join(PROJECT_ROOT, "dir_reconstruction", "output", "new_wiki_index.json")
DEFAULT_WIKI_ROOT = os.path.join(PROJECT_ROOT, "output", "wiki_result")
OUTPUT_DIR = os.path.join(CW_DIR, "output")
LOG_DIR = os.path.join(CW_DIR, "logs")

# 本 MVP 固定处理「业务领域 (wlx)」的 7 个子分类
WLX_SUB_CATEGORIES = [
    "业务领域 (wlx)/社区与网格管理",
    "业务领域 (wlx)/打卡系统",
    "业务领域 (wlx)/积分与抽奖引擎",
    "业务领域 (wlx)/活动与圈子平台",
    "业务领域 (wlx)/上报与通讯系统",
    "业务领域 (wlx)/App API 层",
    "业务领域 (wlx)/分析与统计",
]


def setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"generate_{ts}.log")
    logger = logging.getLogger("category_wiki")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    logger.info(f"日志文件: {log_file}")
    return logger


def category_to_filename(category_path: str) -> str:
    """把 "业务领域 (wlx)/打卡系统" → "业务领域_wlx_打卡系统.json" """
    safe = (category_path
            .replace("/", "_")
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", ""))
    return f"{safe}.json"


async def main():
    parser = argparse.ArgumentParser(description="按 wlx 分类生成业务流 wiki")
    parser.add_argument("--new-index", default=DEFAULT_NEW_INDEX,
                        help=f"new_wiki_index.json 路径（默认 {DEFAULT_NEW_INDEX}）")
    parser.add_argument("--wiki-root", default=DEFAULT_WIKI_ROOT,
                        help=f"wiki .json 页面的根目录（默认 {DEFAULT_WIKI_ROOT}）")
    parser.add_argument("--category", default=None,
                        help="只跑指定分类（完整 path，如 '业务领域 (wlx)/打卡系统'）")
    parser.add_argument("--concurrency", type=int, default=1,
                        help="分类间并发数（默认 1；Neo4j/LLM 会有压力不建议太大）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印会处理的分类清单，不实际生成")
    args = parser.parse_args()

    logger = setup_logger()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logger.info(f"参数: new_index={args.new_index}, wiki_root={args.wiki_root}, "
                f"category={args.category}, concurrency={args.concurrency}, dry_run={args.dry_run}")

    # 1. 加载 new_wiki_index.json
    new_wiki_index = load_new_wiki_index(args.new_index)
    all_categories = [c["path"] for c in new_wiki_index.get("categories", [])]

    # 2. 确定要处理的分类
    if args.category:
        if args.category not in all_categories:
            logger.error(f"指定的分类 '{args.category}' 未在 new_wiki_index 中找到")
            logger.info(f"可选分类（部分）: {all_categories[:10]}")
            sys.exit(1)
        targets = [args.category]
    else:
        targets = [c for c in WLX_SUB_CATEGORIES if c in all_categories]
        missing = [c for c in WLX_SUB_CATEGORIES if c not in all_categories]
        if missing:
            logger.warning(f"以下预设分类在 new_wiki_index 中未找到（将跳过）: {missing}")

    if not targets:
        logger.error("没有任何分类待处理")
        sys.exit(1)

    logger.info(f"将处理 {len(targets)} 个分类：")
    for t in targets:
        cat = next(c for c in new_wiki_index["categories"] if c["path"] == t)
        logger.info(f"  - {t} ({cat['count']} pages)")

    if args.dry_run:
        logger.info("(dry-run) 退出")
        return

    # 3. 初始化 LLM + Neo4j
    llm = LLMInterface()  # 模型/提供商从 .env 读取
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    if not await neo4j.test_connection():
        logger.error("Neo4j 连接失败，请检查 .env 配置")
        sys.exit(1)
    logger.info("Neo4j 连接成功")

    # 4. 并发执行
    semaphore = asyncio.Semaphore(max(1, args.concurrency))
    results = {}

    async def run_one(category_path: str):
        async with semaphore:
            try:
                doc = await generate_wiki_for_category(
                    new_wiki_index, category_path, args.wiki_root, llm, neo4j
                )
                if doc is None:
                    logger.warning(f"[{category_path}] 生成结果为空，跳过落盘")
                    results[category_path] = "empty"
                    return
                out_path = os.path.join(OUTPUT_DIR, category_to_filename(category_path))
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)
                logger.info(f"[{category_path}] 已保存 → {out_path}")
                results[category_path] = "ok"
            except Exception as e:
                logger.error(f"[{category_path}] 失败: {type(e).__name__}: {e}", exc_info=True)
                results[category_path] = f"error: {type(e).__name__}"

    try:
        await asyncio.gather(*[run_one(t) for t in targets])
    finally:
        neo4j.close()

    # 5. 汇总
    logger.info("=" * 60)
    logger.info("汇总：")
    for t, s in results.items():
        logger.info(f"  [{s:20s}] {t}")
    ok = sum(1 for v in results.values() if v == "ok")
    logger.info(f"成功 {ok}/{len(targets)}")


if __name__ == "__main__":
    asyncio.run(main())
