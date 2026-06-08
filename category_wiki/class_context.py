"""构造"类上下文"文本，送给 §2 / §3 的 LLM。

输入: fetch_classes_full_context 的返回 (list of dict)
输出: 一段结构化 markdown，包含每个类的 class_id / name / SE_What / 源码（全量或精简）

策略：
1. 默认 full source_code（LLM 能看到方法体 → 能分析调用链）
2. 如果所有类合计的 source_code 超过阈值，降级到 skeleton（类声明 + 字段 + 方法签名）
3. 依然超阈值 → 按 annotation 相关性排序，先保留 Controller/Service/Component/Aspect 类，其它剪掉
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger("category_wiki.class_context")


DEFAULT_MAX_CHARS = 120_000   # ~ 40-50k tokens，gpt-5-mini 有 128k 上下文，留余量
PRIORITY_ANNOTATIONS = (
    "@RestController", "@Controller", "@Service", "@Component",
    "@Configuration", "@Aspect", "@RabbitListener", "@Scheduled",
    "@Repository",
)


def _has_priority_annotation(source_code: str) -> bool:
    if not source_code:
        return False
    # 扫描类声明前 800 字符即可（类注解必然在这段里）
    head = source_code[:800]
    return any(ann in head for ann in PRIORITY_ANNOTATIONS)


def _format_one(row: Dict, use_skeleton: bool) -> str:
    class_id = row.get("class_id")
    name = row.get("name") or "?"
    labels = row.get("labels") or []
    label_str = "/".join(l for l in labels if l in ("Class", "Interface", "Enum", "Record")) or "Entity"
    se_what = (row.get("se_what") or "").strip().replace("\n", " ")[:400]
    file_name = row.get("file_name") or "-"
    source = row.get("source_code") or ""

    if use_skeleton and source:
        try:
            from graph.four_chart import extract_class_summary
            source = extract_class_summary(source)
        except Exception:
            # 兜底：保留 source 首 800 字符
            source = source[:800] + ("\n// ... (truncated)" if len(source) > 800 else "")

    return (
        f"### {label_str} {name} (class_id={class_id})\n"
        f"- file: `{file_name}`\n"
        f"- SE_What: {se_what if se_what else '(无)'}\n"
        f"- 源码{'（骨架）' if use_skeleton else ''}:\n"
        f"```java\n{source}\n```\n"
    )


def _build(rows: List[Dict], use_skeleton: bool) -> str:
    parts = [_format_one(r, use_skeleton) for r in rows]
    return "\n".join(parts)


def build_class_context_text(
    rows: List[Dict],
    max_chars: int = DEFAULT_MAX_CHARS,
    prefer_full: bool = True,
) -> Dict:
    """构造给 LLM 的类上下文文本，并返回元信息。

    Returns:
        {
            "text": str,              # 最终送给 LLM 的 markdown
            "mode": "full" | "skeleton" | "skeleton_filtered",
            "char_count": int,
            "class_count": int,       # 实际包含的类数量
            "dropped_count": int,     # 被剪掉的类数量（仅 skeleton_filtered 下）
        }
    """
    if not rows:
        return {
            "text": "(该分类下未获取到任何类的源码)",
            "mode": "empty",
            "char_count": 0,
            "class_count": 0,
            "dropped_count": 0,
        }

    # 尝试 1: full source
    if prefer_full:
        full_text = _build(rows, use_skeleton=False)
        if len(full_text) <= max_chars:
            return {
                "text": full_text,
                "mode": "full",
                "char_count": len(full_text),
                "class_count": len(rows),
                "dropped_count": 0,
            }
        logger.info(
            f"[class_context] full 源码 {len(full_text)} 字符超过阈值 {max_chars}，降级到 skeleton"
        )

    # 尝试 2: skeleton 全量
    skeleton_text = _build(rows, use_skeleton=True)
    if len(skeleton_text) <= max_chars:
        return {
            "text": skeleton_text,
            "mode": "skeleton",
            "char_count": len(skeleton_text),
            "class_count": len(rows),
            "dropped_count": 0,
        }
    logger.info(
        f"[class_context] skeleton {len(skeleton_text)} 字符仍超过 {max_chars}，按注解优先级裁剪"
    )

    # 尝试 3: skeleton + 按注解优先级裁剪
    priority_rows = [r for r in rows if _has_priority_annotation(r.get("source_code") or "")]
    other_rows = [r for r in rows if r not in priority_rows]

    # 优先保留有关键注解的类；剩余配额给其它类按字母顺序
    kept = list(priority_rows)
    remaining_budget = max_chars - len(_build(kept, use_skeleton=True))
    for r in other_rows:
        chunk = _format_one(r, use_skeleton=True)
        if len(chunk) <= remaining_budget:
            kept.append(r)
            remaining_budget -= len(chunk)
        if remaining_budget <= 2000:
            break

    dropped = len(rows) - len(kept)
    text = _build(kept, use_skeleton=True)
    logger.info(
        f"[class_context] 裁剪后保留 {len(kept)}/{len(rows)} 个类，"
        f"{len(text)} 字符，丢弃 {dropped} 个"
    )
    return {
        "text": text,
        "mode": "skeleton_filtered",
        "char_count": len(text),
        "class_count": len(kept),
        "dropped_count": dropped,
    }
