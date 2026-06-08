"""章节构建器基类 + 公共工具"""

import json
import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("category_wiki.sections")


# =====================================================================
# invoke_and_parse_strict: 复用 four_chart 里的思路
# （这里独立实现避免引入额外依赖）
# =====================================================================

MAX_JSON_RETRIES = 5


def _extract_first_json(text: str) -> Optional[dict]:
    """从 LLM 输出中提取第一个 JSON 对象。支持 ```json``` 围栏"""
    if not text:
        return None
    import re
    t = text.strip()
    fence = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", t, re.DOTALL)
    if fence:
        t = fence.group(1).strip()
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(t[start:end + 1])
    except json.JSONDecodeError:
        return None


async def invoke_llm_strict(chain, invoke_args: Dict[str, Any], required_keys: List[str],
                            max_retries: int = MAX_JSON_RETRIES) -> Dict[str, Any]:
    """调用 LLM chain，校验返回 dict 必含指定键"""
    last_problem = "<no attempt>"
    for attempt in range(max_retries):
        try:
            raw = await chain.ainvoke(invoke_args)
        except Exception as e:
            last_problem = f"chain 抛出 {type(e).__name__}: {e}"
            logger.warning(f"[LLM] {last_problem}，重试 {attempt + 1}/{max_retries}")
            await asyncio.sleep(min(2 ** attempt, 8))
            continue

        parsed = _extract_first_json(raw if isinstance(raw, str) else str(raw))
        if not isinstance(parsed, dict):
            last_problem = f"未能从输出提取 JSON 对象，原文前 200 字符：{str(raw)[:200]}"
            logger.warning(f"[LLM] {last_problem}")
            continue

        missing = [k for k in required_keys if k not in parsed]
        if missing:
            last_problem = f"缺键 {missing}，实际键 {list(parsed.keys())}"
            logger.warning(f"[LLM] {last_problem}")
            continue

        return parsed

    raise ValueError(f"LLM 调用 {max_retries} 次均失败。最后一次: {last_problem}")


# =====================================================================
# 简单工具
# =====================================================================

def format_neo4j_id_list(ids: List[str]) -> List[str]:
    """去重保持顺序，全部转 str"""
    seen = set()
    result = []
    for x in ids:
        s = str(x) if x is not None else ""
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result
