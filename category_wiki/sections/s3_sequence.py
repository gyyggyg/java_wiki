"""§3. 端到端时序图 —— 新版策略:
给 LLM 送所有类的源码 + SE_What, 由 LLM 自己识别入口 + 推断调用链 + 生成 Mermaid。
不再查 CALLS 边。
"""

import logging
from typing import Any, Dict, List

from chains.common_chains import ChainFactory

from category_wiki.schema import SectionNode, TextNode, ChartNode
from category_wiki.prompts import SEQUENCE_PROMPT
from category_wiki.sections._base import invoke_llm_strict

logger = logging.getLogger("category_wiki.s3")


def _sanitize_mapping(mapping: Any, valid_class_ids: set) -> Dict[str, str]:
    """规整 LLM 返回的 mapping: 过滤非法 class_id，value 统一为 str"""
    if not isinstance(mapping, dict):
        return {}
    clean = {}
    for k, v in mapping.items():
        if not k or not v:
            continue
        if isinstance(v, list):
            v = v[0] if v else ""
        s = str(v)
        if s in valid_class_ids:
            clean[str(k)] = s
        else:
            logger.warning(f"[s3] mapping 中 '{k}' 对应 class_id '{s}' 不在 scope 内，已剔除")
    return clean


async def build_sequence_section(scope: Dict[str, Any], llm,
                                 class_context_text: str,
                                 all_class_rows: List[Dict]) -> SectionNode:
    """返回 §3 章节节点。

    Args:
        scope: build_scope_for_category 的输出
        llm: LLMInterface
        class_context_text: 已组装好的类上下文 markdown
        all_class_rows: 所有类的原始 row（用于 valid class_id 校验）
    """
    logger.info(f"[s3] 生成 {scope['category_path']} 时序图 (new strategy)")

    if not all_class_rows:
        text = TextNode(content={"markdown": "_该分类下未获取到任何类，无法分析调用链。_"})
        return SectionNode(title="## 3. 端到端时序图", content=[text], neo4j_id={})

    chain = ChainFactory.create_generic_chain(llm, SEQUENCE_PROMPT)
    result = await invoke_llm_strict(
        chain,
        {
            "category_path": scope["category_path"],
            "class_contexts": class_context_text,
        },
        required_keys=["mermaid", "mapping"],
    )

    mermaid_text = (result.get("mermaid") or "").strip()
    raw_mapping = result.get("mapping") or {}

    valid_class_ids = {str(r["class_id"]) for r in all_class_rows if r.get("class_id") is not None}
    clean_mapping = _sanitize_mapping(raw_mapping, valid_class_ids)

    chart = ChartNode(
        content={"mermaid": mermaid_text, "mapping": clean_mapping},
        neo4j_id=dict(clean_mapping),  # 每个 participant → class_id
    )

    text_intro = TextNode(
        content={"markdown": f"下图由 LLM 基于 `{scope['category_path']}` 下所有类的源码推断出的端到端调用链。"}
    )

    section = SectionNode(
        title="## 3. 端到端时序图",
        content=[text_intro, chart],
        neo4j_id={"3": list(clean_mapping.values())},
    )
    logger.info(f"[s3] sequenceDiagram 含 {len(clean_mapping)} 个 participant")
    return section
