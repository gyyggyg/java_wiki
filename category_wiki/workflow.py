"""单个分类的 wiki 生成编排器 —— 并发跑 §1/§2/§3/§6，然后交给 assembler

新策略（2026-04）:
  §2 和 §3 共享同一份 "类上下文" 输入（所有 Class/Interface/Enum 的 source_code + SE_What），
  由 LLM 独立判断入口和调用链，不再用 Cypher 预扫描 @RestController/@Scheduled/CALLS 边。
"""

import asyncio
import logging
from typing import Any, Dict

from category_wiki.scope import build_scope_for_category
from category_wiki.neo4j_queries import fetch_classes_full_context
from category_wiki.class_context import build_class_context_text
from category_wiki.sections.s1_overview import build_overview_section
from category_wiki.sections.s2_entrypoints import build_entrypoints_section
from category_wiki.sections.s3_sequence import build_sequence_section
from category_wiki.sections.s6_components import build_components_section
from category_wiki.assembler import assemble_wiki

logger = logging.getLogger("category_wiki.workflow")


async def generate_wiki_for_category(
    new_wiki_index: dict,
    category_path: str,
    wiki_root: str,
    llm,
    neo4j,
) -> dict:
    """为单个分类生成业务流 wiki。

    Returns:
        {"markdown_content": [...], ...}
    """
    logger.info(f"========== 开始处理分类: {category_path} ==========")

    # 1. 构建 scope（读 page .json → 收集 nodeId → 展开容器到 Class/Interface/Enum）
    scope = await build_scope_for_category(new_wiki_index, category_path, wiki_root, neo4j)

    if not scope.get("class_ids") and not scope.get("interface_ids") and not scope.get("enum_ids"):
        logger.warning(f"[{category_path}] scope 下没有任何 Class/Interface/Enum 节点，跳过")
        return None

    # 2. 拉取所有类的完整上下文（source_code + SE_What），§2 §3 共用
    all_class_like = (
        scope.get("class_ids", [])
        + scope.get("interface_ids", [])
        + scope.get("enum_ids", [])
        + scope.get("record_ids", [])
    )
    all_class_rows = await fetch_classes_full_context(neo4j, all_class_like)
    logger.info(
        f"[{category_path}] fetch_classes_full_context: 请求 {len(all_class_like)} 个 id → "
        f"命中 {len(all_class_rows)} 条类数据"
    )

    ctx_info = build_class_context_text(all_class_rows)
    logger.info(
        f"[{category_path}] class_context: mode={ctx_info['mode']}, "
        f"chars={ctx_info['char_count']}, classes={ctx_info['class_count']}, "
        f"dropped={ctx_info['dropped_count']}"
    )
    class_context_text = ctx_info["text"]

    # 3. 并发跑 4 个章节
    results = await asyncio.gather(
        build_overview_section(scope, llm, neo4j),
        build_entrypoints_section(scope, llm, class_context_text, all_class_rows),
        build_sequence_section(scope, llm, class_context_text, all_class_rows),
        build_components_section(scope, llm, neo4j),
        return_exceptions=True,
    )
    section_nodes = []
    for name, r in zip(["s1", "s2", "s3", "s6"], results):
        if isinstance(r, Exception):
            logger.error(f"[{category_path}] {name} 失败: {type(r).__name__}: {r}", exc_info=r)
            from category_wiki.schema import SectionNode, TextNode
            placeholder = SectionNode(
                title=f"## {name.upper()} ({name} 生成失败)",
                content=[TextNode(content={"markdown": f"_生成失败: {type(r).__name__}: {r}_"})],
            )
            section_nodes.append(placeholder)
        else:
            section_nodes.append(r)

    # 4. assembler 打 id + 填 neo4j_source
    doc = await assemble_wiki(scope, section_nodes, neo4j)
    return doc
