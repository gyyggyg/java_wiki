"""§1. 业务概述"""

import json
import logging
from typing import Any, Dict

from chains.common_chains import ChainFactory

from category_wiki.schema import SectionNode, TextNode
from category_wiki.neo4j_queries import fetch_class_briefs
from category_wiki.prompts import OVERVIEW_PROMPT
from category_wiki.sections._base import invoke_llm_strict, format_neo4j_id_list

logger = logging.getLogger("category_wiki.s1")


def _format_class_briefs(rows) -> str:
    if not rows:
        return "(该分类下未找到带有语义解释的类/接口/枚举)"
    lines = []
    for r in rows[:30]:  # 只给 LLM 前 30 条，避免 prompt 过长
        name = r.get("name") or "?"
        what = (r.get("se_what") or "").replace("\n", " ")[:200]
        why = (r.get("se_why") or "").replace("\n", " ")[:150]
        lines.append(f"- **{name}**\n    - What: {what}\n    - Why: {why}")
    if len(rows) > 30:
        lines.append(f"- ...（另外 {len(rows) - 30} 个类/接口省略）")
    return "\n".join(lines)


def _format_pages_brief(pages) -> str:
    if not pages:
        return "(无)"
    lines = []
    for p in pages[:20]:
        path = p.get("path", "")
        summary = (p.get("summary") or "").replace("\n", " ")[:200]
        lines.append(f"- **{path.split('/')[-1]}**: {summary}")
    if len(pages) > 20:
        lines.append(f"- ...（另外 {len(pages) - 20} 页省略）")
    return "\n".join(lines)


async def build_overview_section(scope: Dict[str, Any], llm, neo4j) -> SectionNode:
    """返回 §1 章节节点：SectionNode(title='## 1. 业务概述', content=[TextNode])"""
    logger.info(f"[s1] 生成 {scope['category_path']} 概述")

    class_ids = scope.get("class_ids", []) + scope.get("interface_ids", []) + scope.get("enum_ids", [])
    briefs = await fetch_class_briefs(neo4j, class_ids)

    chain = ChainFactory.create_generic_chain(llm, OVERVIEW_PROMPT)
    result = await invoke_llm_strict(
        chain,
        {
            "category_path": scope["category_path"],
            "category_description": scope.get("description", ""),
            "class_briefs": _format_class_briefs(briefs),
            "pages_brief": _format_pages_brief(scope.get("pages", [])),
        },
        required_keys=["markdown"],
    )

    markdown = result["markdown"].strip()

    # neo4j_id 用于后续反查 neo4j_source
    # 概述章节的 nodeId 用 scope 里所有 class/interface/enum 的 id
    top_ids = format_neo4j_id_list(class_ids)

    text_node = TextNode(
        content={"markdown": markdown},
        neo4j_id={},  # text 本身不带 id
    )
    section = SectionNode(
        title="## 1. 业务概述",
        content=[text_node],
        neo4j_id={"1": top_ids},
    )
    return section
