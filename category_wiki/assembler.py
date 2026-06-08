"""组装最终 JSON：包一层顶级 SectionNode、打 id、填 neo4j_source"""

import logging
from typing import Any, Dict, List

from category_wiki.schema import SectionNode, TextNode, ChartNode
from category_wiki.id_generator import SectionIdGenerator
from category_wiki.source_resolver import (
    resolve_sources,
    collect_all_node_ids,
    fill_neo4j_source_recursively,
)

logger = logging.getLogger("category_wiki.assembler")


def _assign_ids(node, gen: SectionIdGenerator):
    """为节点打 id。顶级先打，子节点按 DFS 顺序"""
    if hasattr(node, "id"):
        node.id = gen.next()
    content = getattr(node, "content", None)
    if isinstance(content, list):
        for sub in content:
            if hasattr(sub, "id") or hasattr(sub, "content"):
                _assign_ids(sub, gen)


async def assemble_wiki(scope: Dict[str, Any], section_nodes: List[SectionNode], neo4j) -> dict:
    """把若干 SectionNode 组装为最终 JSON。

    Args:
        scope: build_scope_for_category 的输出
        section_nodes: 已构建好的章节节点列表（§1, §2, §3, §6）
        neo4j: Neo4jInterface

    Returns:
        {"markdown_content": [root_section_dict]}
    """
    category_path = scope["category_path"]

    # 1. 包一层顶级标题
    top_title = f"# {category_path.split('/')[-1]}"
    root = SectionNode(
        title=top_title,
        content=list(section_nodes),
        neo4j_id={},  # 顶级不记 neo4j_id
    )

    # 2. 收集整棵树的所有 nodeId，批量查 name 属性
    all_ids = collect_all_node_ids(root)
    logger.info(f"[assemble] 收集到 {len(all_ids)} 个 nodeId，准备批量解析 name")
    sources_map = await resolve_sources(neo4j, all_ids)

    # 3. 把 neo4j_source 填充到每个节点
    fill_neo4j_source_recursively(root, sources_map)

    # 4. DFS 打 S1/S2/... id
    gen = SectionIdGenerator()
    _assign_ids(root, gen)

    # 5. 序列化
    return {
        "markdown_content": [root.to_dict()],
        # 顶层 source_id 保持和总揽.json 一致（可空列表）
        "source_id": [],
        # 附加元信息（可选）
        "_category_path": category_path,
        "_description": scope.get("description", ""),
        "_page_count": len(scope.get("pages", [])),
    }
