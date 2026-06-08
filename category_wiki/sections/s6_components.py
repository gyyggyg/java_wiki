"""§6. 组件索引 —— 不需要 LLM，直接从 new_wiki_index.json 的 pages 抽取"""

import logging
from typing import Any, Dict, List

from category_wiki.schema import SectionNode, TextNode
from category_wiki.sections._base import format_neo4j_id_list

logger = logging.getLogger("category_wiki.s6")


async def build_components_section(scope: Dict[str, Any], llm, neo4j) -> SectionNode:
    """直接用 page path / summary / classes 组成一份索引清单"""
    logger.info(f"[s6] 生成 {scope['category_path']} 组件索引")
    pages = scope.get("pages", [])
    if not pages:
        text = TextNode(content={"markdown": "_该分类下无聚合页面。_"})
        return SectionNode(title="## 6. 组件索引", content=[text], neo4j_id={})

    # 子小节：每个 page 一个 §6.N 条目
    sub_sections: List[Any] = []

    # 顶层说明
    intro = TextNode(content={
        "markdown": (
            f"本分类聚合了 **{len(pages)} 篇** wiki 页面。下表列出每个页面对应的核心类/接口，"
            f"可跳转到已有的 Block wiki 查看详情。\n"
        )
    })
    sub_sections.append(intro)

    # 汇总为一份 markdown 表格
    lines = ["| # | 页面 | 核心类/接口 | 简述 |", "|---|---|---|---|"]
    per_section_neo4j: Dict[str, List[str]] = {}

    for idx, p in enumerate(pages, 1):
        page_path = p.get("path", "")
        page_name = page_path.rsplit("/", 1)[-1].replace(".json", "")
        classes = p.get("classes", []) or []
        summary = (p.get("summary") or "").replace("\n", " ")[:120]
        class_str = ", ".join(f"`{c}`" for c in classes[:5])
        if len(classes) > 5:
            class_str += f" 等 {len(classes)} 个"
        lines.append(
            f"| {idx} | [{page_name}]({page_path}) | {class_str or '-'} | {summary} |"
        )

    table = TextNode(content={"markdown": "\n".join(lines)})
    sub_sections.append(table)

    section = SectionNode(
        title="## 6. 组件索引",
        content=sub_sections,
        # 这章的 neo4j_id 用整个 scope 的所有 class_ids 作为一个聚合
        neo4j_id={"6": format_neo4j_id_list(scope.get("class_ids", []))},
    )
    return section
