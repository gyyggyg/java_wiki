"""§2. 触发入口 —— 新版策略:
给 LLM 送所有类的源码 + SE_What, 由 LLM 独立识别所有类型的入口 (HTTP/Scheduled/MQ/Event/...)
"""

import logging
from typing import Any, Dict, List

from chains.common_chains import ChainFactory

from category_wiki.schema import SectionNode, TextNode
from category_wiki.prompts import ENTRYPOINTS_PROMPT
from category_wiki.sections._base import invoke_llm_strict, format_neo4j_id_list

logger = logging.getLogger("category_wiki.s2")


async def build_entrypoints_section(scope: Dict[str, Any], llm,
                                    class_context_text: str,
                                    all_class_rows: List[Dict]) -> SectionNode:
    """返回 §2 章节节点。

    Args:
        scope: build_scope_for_category 的输出
        llm: LLMInterface
        class_context_text: 已组装好的类上下文 markdown（含每个类的 class_id/SE_What/source）
        all_class_rows: 所有类的原始 row（用于 fallback 和 neo4j_id 收集）
    """
    logger.info(f"[s2] 生成 {scope['category_path']} 触发入口 (new strategy)")

    if not all_class_rows:
        text = TextNode(content={"markdown": "_该分类下未获取到任何类，无法分析入口。_"})
        return SectionNode(title="## 2. 触发入口", content=[text], neo4j_id={})

    chain = ChainFactory.create_generic_chain(llm, ENTRYPOINTS_PROMPT)
    result = await invoke_llm_strict(
        chain,
        {
            "category_path": scope["category_path"],
            "class_contexts": class_context_text,
        },
        required_keys=["markdown", "entry_class_ids"],
    )

    markdown = result.get("markdown", "").strip()
    entry_class_ids_raw = result.get("entry_class_ids") or []

    # 校验：entry_class_ids 里的每个 id 都必须在输入里出现过
    valid_class_ids = {str(r["class_id"]) for r in all_class_rows if r.get("class_id") is not None}
    entry_class_ids = []
    for cid in entry_class_ids_raw:
        s = str(cid)
        if s in valid_class_ids:
            entry_class_ids.append(s)
        else:
            logger.warning(f"[s2] LLM 返回的 entry_class_id '{cid}' 不在输入范围，忽略")

    entry_class_ids = format_neo4j_id_list(entry_class_ids)

    text = TextNode(content={"markdown": markdown})

    # 本章 neo4j_id 用 LLM 判定的入口类集合
    neo4j_id_map = {}
    if entry_class_ids:
        neo4j_id_map["2"] = entry_class_ids

    section = SectionNode(
        title="## 2. 触发入口",
        content=[text],
        neo4j_id=neo4j_id_map,
    )

    # 同时把入口类 id 存回 scope，供 §3 参考（§3 也会自己判一遍）
    scope["_entry_class_ids"] = entry_class_ids
    logger.info(f"[s2] LLM 识别到 {len(entry_class_ids)} 个入口类")
    return section
