"""LLM API 调用客户端 —— 业务流章节生成的 LLM 入口

提供两个高层调用 + 一个 session 复用机制：
- `invoke_llm_strict(system, user, required_keys)`：调 LLM + 强制返回含指定键的 JSON
- `invoke_llm_markdown(system, user)`：调 LLM + 返回裸 markdown 文本
- `resume_session_id`：上一次调用返回的 `List[BaseMessage]` 历史；
  再次调用时前置进消息列表，让模型"记住"上次生成的内容
  （常用场景：先让模型画 mermaid，再让它基于图补一段说明文字）

底层走 `LLMInterface.llm.ainvoke([messages])`（LangChain），
`set_default_llm()` 在进程启动时注入 LLMInterface 实例，之后 invoke_* 调用无需再传 llm 参数。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from langchain.schema import AIMessage, HumanMessage, SystemMessage, BaseMessage

from interfaces.llm_interface import LLMInterface

logger = logging.getLogger("business_flow.client")


# Session 实际是一串 LangChain 消息；调用方把它当"不透明句柄"存取即可。
Session = Optional[List[BaseMessage]]


# ---- 超时 / 重试参数 ----
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "180"))
LLM_MAX_RETRIES = int(os.environ.get("LLM_MAX_RETRIES", "3"))


# ---- 默认 LLM 注入：避免每个 invoke_* 调用都透传 llm 参数 ----
_default_llm: Optional[LLMInterface] = None


def set_default_llm(llm: LLMInterface) -> None:
    """在进程启动时由 generate.py 调用一次，之后所有 invoke_llm_* 调用默认使用该 llm。

    之后 sections.py 等模块里的 invoke_llm_* 调用无需再传 llm 参数。
    """
    global _default_llm
    _default_llm = llm


def _resolve_llm(llm: Optional[LLMInterface]) -> LLMInterface:
    if llm is not None:
        return llm
    if _default_llm is None:
        raise RuntimeError(
            "LLM 未初始化。请在启动时先调用 business_flow.llm_client.set_default_llm(...)。"
        )
    return _default_llm


# ============================================================
# JSON 抽取（含 3 层兜底修复：常规 loads / 未转义引号修复 / 单字段 JSON 激进修复）
# ============================================================

def _repair_unescaped_quotes(json_str: str) -> str:
    """对形如 {"k": "value with " inside"} 的未转义引号做宽容修复。"""
    pat = re.compile(r'^(\s*"[^"]+"\s*:\s*")(.*?)("\s*[,}]\s*)$', re.DOTALL)
    out = []
    for line in json_str.split("\n"):
        m = pat.match(line)
        if m:
            prefix, value, suffix = m.group(1), m.group(2), m.group(3)
            value = re.sub(r'(?<!\\)"', r'\\"', value)
            out.append(prefix + value + suffix)
        else:
            out.append(line)
    return "\n".join(out)


def _repair_single_field_json(s: str) -> Optional[str]:
    """针对 `{"key": "值里含未转义双引号"}` 单字段 JSON 的激进修复。"""
    m_head = re.match(r'^\s*\{\s*"[^"]+"\s*:\s*"', s, flags=re.DOTALL)
    if not m_head:
        return None
    m_tail = re.search(r'"\s*\}\s*$', s, flags=re.DOTALL)
    if not m_tail:
        return None
    head_end = m_head.end()
    tail_start = m_tail.start()
    if tail_start <= head_end:
        return None
    value_body = s[head_end:tail_start]
    fixed = re.sub(r'(?<!\\)"', r'\\"', value_body)
    return s[:head_end] + fixed + s[tail_start:]


def _strip_code_fence(s: str, allow_langs: str = "json|markdown|md") -> str:
    """剥离 ```lang\n ... \n``` 围栏。若没有围栏直接返回原串。"""
    s = s.strip()
    m = re.search(rf"```(?:{allow_langs})?\s*\n?(.*?)\n?```", s, re.DOTALL)
    return m.group(1).strip() if m else s


def extract_json_object(raw_output: str) -> Optional[dict]:
    """从 LLM 原始输出里抠出 JSON 对象：
    1) 去掉 ```json ... ``` 围栏
    2) 截外层 {...}
    3) json.loads，失败则尝试修复未转义引号
    """
    if not raw_output:
        return None
    s = _strip_code_fence(raw_output)
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        return None
    s = s[start:end + 1]
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_repair_unescaped_quotes(s))
    except json.JSONDecodeError:
        pass
    repaired = _repair_single_field_json(s)
    if repaired is not None:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return None
    return None


# ============================================================
# 核心：一次 LLM 调用，返回文本 + 更新后的 session（消息历史）
# ============================================================

async def _invoke_once(
    llm: Optional[LLMInterface],
    system_prompt: str,
    user_prompt: str,
    timeout: int,
    label: str,
    resume_session: Session = None,
) -> Tuple[str, Session]:
    """单次 LLM 调用。

    Args:
        llm: LLMInterface 实例
        system_prompt: 系统提示词
        user_prompt: 用户提示词
        timeout: 每次调用超时秒数
        label: 日志标签
        resume_session: 复用的历史消息列表；非空则忽略本次 system_prompt，沿用历史

    Returns:
        (assistant 文本, 更新后的完整消息历史)
    """
    llm_actual = _resolve_llm(llm)
    if resume_session:
        # 沿用历史会话，不重复塞 system prompt
        messages: List[BaseMessage] = list(resume_session) + [HumanMessage(content=user_prompt)]
    else:
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

    logger.debug(f"[{label}] 调 LLM，消息数={len(messages)} (resume={bool(resume_session)})")

    try:
        response = await asyncio.wait_for(llm_actual.llm.ainvoke(messages), timeout=timeout)
    except asyncio.TimeoutError as te:
        logger.warning(f"[{label}] LLM 调用超时（{timeout}s）")
        raise

    content = response.content if hasattr(response, "content") else str(response)
    if not isinstance(content, str):
        content = str(content)

    # 更新 session：加上本次 assistant 回复
    updated_session: Session = messages + [AIMessage(content=content)]
    logger.debug(f"[{label}] 返回长度={len(content)} chars")
    return content, updated_session


# ============================================================
# 高层 API：invoke_llm_strict 强制返回 JSON，invoke_llm_markdown 返回裸文本
# ============================================================

async def invoke_llm_strict(
    system_prompt: str,
    user_prompt: str,
    required_keys: List[str],
    label: str = "llm-call",
    max_retries: int = LLM_MAX_RETRIES,
    timeout: int = LLM_TIMEOUT,
    resume_session_id: Session = None,
    llm: Optional[LLMInterface] = None,
) -> Tuple[Dict[str, Any], Session]:
    """调用 LLM 并校验返回 dict 含指定键，失败则重试。

    Args:
        llm: LLMInterface 实例（由调用方预先构造）
        system_prompt: 系统 prompt
        user_prompt: 用户 prompt
        required_keys: 返回 dict 必须包含的键
        label: 日志标签
        max_retries: JSON 解析/字段校验失败时的重试次数
        timeout: 单次调用超时（秒）
        resume_session_id: 非空则复用上一次返回的消息历史（让模型"记住"之前的对话）

    Returns:
        (解析后的 dict, 更新后的 session 历史)
    """
    last_problem = "<no attempt>"
    for attempt in range(max_retries):
        try:
            raw, sess = await _invoke_once(
                llm, system_prompt, user_prompt, timeout,
                f"{label}#{attempt+1}", resume_session=resume_session_id,
            )
        except Exception as e:
            last_problem = f"llm 调用抛出 {type(e).__name__}: {e}"
            logger.warning(f"[{label}] {last_problem}，重试 {attempt + 1}/{max_retries}")
            await asyncio.sleep(min(2 ** attempt, 8))
            continue

        parsed = extract_json_object(raw)
        if not isinstance(parsed, dict):
            last_problem = f"未能从输出提取 JSON 对象，原始前 200 字: {raw[:200]}"
            logger.warning(f"[{label}] {last_problem}")
            continue

        missing = [k for k in required_keys if k not in parsed]
        if missing:
            last_problem = f"缺键 {missing}，实际键 {list(parsed.keys())}"
            logger.warning(f"[{label}] {last_problem}")
            continue

        return parsed, sess

    raise ValueError(f"LLM 调用 {max_retries} 次均失败。最后一次: {last_problem}")


async def invoke_llm_markdown(
    system_prompt: str,
    user_prompt: str,
    label: str = "llm-call",
    max_retries: int = LLM_MAX_RETRIES,
    timeout: int = LLM_TIMEOUT,
    resume_session_id: Session = None,
    min_chars: int = 10,
    llm: Optional[LLMInterface] = None,
) -> Tuple[str, Session]:
    """调用 LLM 并直接返回 markdown 字符串（不经 JSON 解析）。

    适用于 prompt 输出本身就是纯 markdown 的场景（§1 概述 / §3 接口清单 / 图后说明），
    避免 LLM 把 markdown 包进 JSON 字符串带来的转义失败和 token 浪费。

    处理：
    - 剥离 ```markdown / ```md 围栏（如果 LLM 多此一举包了围栏）
    - 兜底：如果 LLM 仍返回 JSON 形如 {"markdown": "..."}，自动抽取 markdown 字段

    失败条件：空串 或 长度 < min_chars。
    """
    last_problem = "<no attempt>"
    for attempt in range(max_retries):
        try:
            raw, sess = await _invoke_once(
                llm, system_prompt, user_prompt, timeout,
                f"{label}#{attempt+1}", resume_session=resume_session_id,
            )
        except Exception as e:
            last_problem = f"llm 调用抛出 {type(e).__name__}: {e}"
            logger.warning(f"[{label}] {last_problem}，重试 {attempt + 1}/{max_retries}")
            await asyncio.sleep(min(2 ** attempt, 8))
            continue

        text = _strip_code_fence(raw).strip()

        # 兜底：LLM 偶尔忘了指令仍按 JSON 返回，尝试抽取任意字符串字段
        if text.startswith("{") and text.endswith("}"):
            parsed = extract_json_object(raw)
            if isinstance(parsed, dict):
                extracted: Optional[str] = None
                for k in ("markdown", "description", "content", "text",
                          "overview", "body", "result", "output"):
                    v = parsed.get(k)
                    if isinstance(v, str) and v.strip():
                        extracted = v.strip()
                        logger.info(f"[{label}] LLM 返回了 JSON，已从字段 `{k}` 抽出 markdown")
                        break
                if extracted is None:
                    str_fields = {k: v for k, v in parsed.items()
                                  if isinstance(v, str) and v.strip()}
                    if len(str_fields) == 1:
                        k, v = next(iter(str_fields.items()))
                        extracted = v.strip()
                        logger.info(
                            f"[{label}] LLM 返回单字段 JSON，按键 `{k}` 抽出 markdown"
                        )
                if extracted is not None:
                    text = extracted

        if len(text) < min_chars:
            last_problem = f"返回内容过短（{len(text)} < {min_chars} chars）: {text!r}"
            logger.warning(f"[{label}] {last_problem}")
            continue

        return text, sess

    raise ValueError(f"LLM 调用 {max_retries} 次均失败。最后一次: {last_problem}")
