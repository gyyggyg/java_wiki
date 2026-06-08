"""Mermaid 语法校验 + 语法错误自动重试

调用 `scripts/validate_mermaid.mjs` 子进程（node + jsdom + mermaid.parse），
在 Claude 返回含 mermaid 的结果后做一轮纯语法校验；若失败则把错误反馈
追加到 user prompt 上再调一次 Claude，最多重试 `max_retries` 次。
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Tuple

from business_flow.claude.claude_client import invoke_claude_strict

logger = logging.getLogger("business_flow.claude.mermaid")

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VALIDATOR_SCRIPT = os.path.join(_PROJECT_ROOT, "scripts", "validate_mermaid.mjs")

VALIDATOR_TIMEOUT = int(os.environ.get("BF_MERMAID_VALIDATE_TIMEOUT", "30"))
MERMAID_MAX_FIX_ATTEMPTS = int(os.environ.get("BF_MERMAID_MAX_FIX_ATTEMPTS", "3"))


async def validate_mermaid(mermaid_text: str, timeout: int = VALIDATOR_TIMEOUT) -> Tuple[bool, str]:
    """调 node 子进程校验 mermaid 源码。返回 (is_valid, error_message)。

    `mermaid_text` 应为纯 mermaid 源码（不含 ``` 围栏）。
    校验脚本缺失时返回 (True, "...") 放行，避免环境问题阻塞生成。
    """
    text = (mermaid_text or "").strip()
    if not text:
        return False, "empty mermaid source"
    if not os.path.isfile(VALIDATOR_SCRIPT):
        logger.warning(f"validator 脚本不存在: {VALIDATOR_SCRIPT}，跳过校验")
        return True, "validator missing"

    try:
        proc = await asyncio.create_subprocess_exec(
            "node", VALIDATOR_SCRIPT, "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        logger.warning("未找到 node 可执行文件，跳过 mermaid 校验")
        return True, "node missing"

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(text.encode("utf-8")),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        return False, f"校验超时 ({timeout}s)"

    if proc.returncode == 0:
        return True, ""
    err = (stderr or b"").decode("utf-8", errors="replace").strip()
    if not err:
        err = (stdout or b"").decode("utf-8", errors="replace").strip() or "unknown parse error"
    return False, err


def _build_short_fix_prompt(err_msg: str) -> str:
    """--resume 语境下的修复提示（极简，Claude 已知上次输出和原请求）"""
    return (
        "你刚返回的 mermaid 语法校验未通过，错误信息：\n\n"
        f"```\n{err_msg[:800]}\n```\n\n"
        "请仅修正 mermaid 语法，重新输出**完整 JSON**；其它字段（mapping / notes / status 等）"
        "保持与上次一致，不要重新推导或改动业务内容。"
    )


async def invoke_claude_with_mermaid_check(
    system_prompt: str,
    user_prompt: str,
    required_keys: List[str],
    label: str,
    max_retries: int = MERMAID_MAX_FIX_ATTEMPTS,
    resume_session_id: Optional[str] = None,
) -> Tuple[Dict, Optional[str]]:
    """调 Claude 生成含 mermaid 的 JSON；若 mermaid 语法错误则 `--resume` 复用会话重试。

    - 若结果里无 `mermaid` 字段（如 missing_data 分支），直接返回不校验
    - 修复轮使用 `--resume <sid>` + 极简错误提示，复用 prompt 缓存和上下文
    - 最多重试 `max_retries` 次；耗尽仍失败则返回最后一次结果并记 warning
    """
    current_user = user_prompt
    current_sid = resume_session_id
    last_result: Dict = {}
    last_sid: Optional[str] = None

    for attempt in range(max_retries + 1):
        attempt_label = label if attempt == 0 else f"{label}-mermaidfix{attempt}"
        result, sid = await invoke_claude_strict(
            system_prompt=system_prompt,
            user_prompt=current_user,
            required_keys=required_keys,
            label=attempt_label,
            resume_session_id=current_sid,
        )
        last_result, last_sid = result, sid

        mermaid_text = (result.get("mermaid") or "").strip()
        if not mermaid_text:
            return result, sid

        ok, err = await validate_mermaid(mermaid_text)
        if ok:
            if attempt > 0:
                logger.info(f"[{label}] mermaid 语法校验在第 {attempt + 1} 轮通过 (resume={bool(current_sid)})")
            return result, sid

        logger.warning(
            f"[{label}] mermaid 校验失败(尝试 {attempt + 1}/{max_retries + 1}): "
            f"{err.splitlines()[0][:200] if err else '?'}"
        )

        if attempt >= max_retries:
            logger.warning(f"[{label}] mermaid 修复重试耗尽，输出可能含语法错误的图")
            return result, sid

        # 下一轮：resume 到刚才的 session，发极简修复指令
        current_user = _build_short_fix_prompt(err)
        current_sid = sid

    return last_result, last_sid
