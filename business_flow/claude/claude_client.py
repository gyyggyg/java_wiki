"""Claude CLI 封装 —— subprocess 调用 + JSON 提取 + schema 校验 + 重试"""

import asyncio
import json
import logging
import os
import re
import shutil
import sys
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("business_flow.claude.client")

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "sonnet")
CLAUDE_TIMEOUT = int(os.environ.get("BF_CLAUDE_TIMEOUT", "240"))
CLAUDE_MAX_RETRIES = int(os.environ.get("BF_CLAUDE_MAX_RETRIES", "3"))


def _find_claude_cli() -> str:
    path = shutil.which("claude")
    if path:
        return path
    if sys.platform == "win32":
        npm_path = os.path.join(os.environ.get("APPDATA", ""), "npm", "claude.cmd")
        if os.path.isfile(npm_path):
            return npm_path
    raise FileNotFoundError("未找到 claude CLI，请先安装 Claude Code")


async def _invoke_once(
    user_prompt: str, system_prompt: str, timeout: int, label: str,
    resume_session_id: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """调一次 claude CLI，返回 (原始 stdout, session_id)。

    resume_session_id 非空时追加 `--resume <id>` 以复用上一次会话（含 prompt 缓存 + 上下文）。
    """
    claude_bin = _find_claude_cli()
    env = os.environ.copy()
    if sys.platform == "win32" and "CLAUDE_CODE_GIT_BASH_PATH" not in env:
        git_bash = shutil.which("bash")
        if git_bash:
            env["CLAUDE_CODE_GIT_BASH_PATH"] = git_bash

    cmd = [
        claude_bin, "-p",
        "--system-prompt", system_prompt,
        "--model", CLAUDE_MODEL,
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
    ]
    if resume_session_id:
        cmd.extend(["--resume", resume_session_id])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(input=user_prompt.encode("utf-8")),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"claude CLI 超时 ({timeout}s) —— {label}")

    out = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
    err = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
    rc = proc.returncode

    logger.debug(f"[{label}] rc={rc} resume={bool(resume_session_id)}")
    logger.debug(f"[{label}] stdout (前 2000 字符):\n{out[:2000]}")
    if err.strip():
        logger.debug(f"[{label}] stderr (前 500 字符):\n{err[:500]}")

    if rc != 0:
        raise RuntimeError(f"claude CLI 失败 (rc={rc}): {err[:200]}")
    if not out.strip():
        raise RuntimeError(f"claude CLI 无输出")

    # 从 envelope 抽取 session_id（非破坏性：out 原样返回给下游 JSON 提取器）
    sid: Optional[str] = None
    try:
        env_obj = json.loads(out)
        if isinstance(env_obj, dict):
            sid = env_obj.get("session_id") or None
    except json.JSONDecodeError:
        pass
    return out, sid


def _repair_unescaped_quotes(json_str: str) -> str:
    """修复 JSON value 里未转义的 ASCII 双引号（LLM 常见错误）"""
    pat = re.compile(r'^(\s*"[^"]+"\s*:\s*")(.*?)("\s*[,}]?\s*)$')
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
    """对形如 {"key": "值里含未转义的 \"双引号\""} 的单字段 JSON 做激进修复：
    定位首个 `"key": "` 与最后一个 `"}` 之间的所有未转义 ASCII 双引号并转义。
    仅在常规修复失败后使用。
    """
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
    # 只转义未被反斜杠转义过的 "
    fixed = re.sub(r'(?<!\\)"', r'\\"', value_body)
    return s[:head_end] + fixed + s[tail_start:]


def _unwrap_cli_envelope(raw_output: str) -> str:
    """Claude CLI 返回一个 JSON envelope `{"type":"result","result":"..."}`，
    这里解包拿到真实的 result 字符串。无 envelope 或非 JSON 时直接原样返回。
    """
    if not raw_output:
        return ""
    try:
        env = json.loads(raw_output)
        if isinstance(env, dict) and "result" in env:
            return env["result"] if isinstance(env["result"], str) else str(env["result"])
    except json.JSONDecodeError:
        pass
    return raw_output


def _strip_code_fence(s: str, allow_langs: str = "json|markdown|md") -> str:
    """剥离 ```lang\n ... \n``` 围栏。若没有围栏直接返回原串。"""
    s = s.strip()
    m = re.search(rf"```(?:{allow_langs})?\s*\n?(.*?)\n?```", s, re.DOTALL)
    return m.group(1).strip() if m else s


def extract_json_object(raw_output: str) -> Optional[dict]:
    """从 Claude CLI 原始输出里抠出 JSON 对象：
    1) 解包 CLI envelope {"result": "..."}
    2) 去掉 ```json ... ``` 围栏
    3) 截外层 {...}
    4) json.loads，失败则尝试修复未转义引号
    """
    if not raw_output:
        return None
    raw_output = _unwrap_cli_envelope(raw_output)
    s = _strip_code_fence(raw_output)
    # 截外层 {...}
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
    # 最后兜底：针对 {"key":"value"} 单字段 JSON 的激进 " 转义
    repaired = _repair_single_field_json(s)
    if repaired is not None:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            return None
    return None


async def invoke_claude_strict(
    system_prompt: str,
    user_prompt: str,
    required_keys: List[str],
    label: str = "claude-call",
    max_retries: int = CLAUDE_MAX_RETRIES,
    timeout: int = CLAUDE_TIMEOUT,
    resume_session_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """调用 Claude CLI 并校验返回 dict 含指定键，失败则重试。

    Args:
        system_prompt: 系统 prompt
        user_prompt: 实际输入内容
        required_keys: 返回 dict 必须包含的键
        label: 日志标签
        max_retries: JSON 解析/字段校验失败时的重试次数
        timeout: 单次调用超时（秒）
        resume_session_id: 若提供，调用 CLI 时附 `--resume <id>` 以复用之前会话

    Returns:
        (解析后的 dict, session_id)
    """
    last_problem = "<no attempt>"
    for attempt in range(max_retries):
        try:
            raw, sid = await _invoke_once(
                user_prompt, system_prompt, timeout, f"{label}#{attempt+1}",
                resume_session_id=resume_session_id,
            )
        except Exception as e:
            last_problem = f"claude 调用抛出 {type(e).__name__}: {e}"
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

        return parsed, sid

    raise ValueError(f"Claude CLI 调用 {max_retries} 次均失败。最后一次: {last_problem}")


async def invoke_claude_markdown(
    system_prompt: str,
    user_prompt: str,
    label: str = "claude-call",
    max_retries: int = CLAUDE_MAX_RETRIES,
    timeout: int = CLAUDE_TIMEOUT,
    resume_session_id: Optional[str] = None,
    min_chars: int = 10,
) -> Tuple[str, Optional[str]]:
    """调用 Claude CLI 并直接返回 markdown 字符串（不经 JSON 解析）。

    适用于 prompt 输出本身就是纯 markdown 的场景（§1 概述、§3 接口清单、图后说明），
    避免 Claude 把 markdown 包进 JSON 字符串带来的转义失败和 token 浪费。

    处理：
    - 解包 Claude CLI envelope 拿到 result 字符串
    - 剥离 ```markdown / ```md 围栏（如果 LLM 多此一举包了围栏）
    - 兜底：如果 LLM 仍返回 JSON 形如 {"markdown": "..."}，自动抽取 markdown 字段

    失败条件：空串 或 长度不足 min_chars。

    Returns:
        (markdown 文本, session_id)
    """
    last_problem = "<no attempt>"
    for attempt in range(max_retries):
        try:
            raw, sid = await _invoke_once(
                user_prompt, system_prompt, timeout, f"{label}#{attempt+1}",
                resume_session_id=resume_session_id,
            )
        except Exception as e:
            last_problem = f"claude 调用抛出 {type(e).__name__}: {e}"
            logger.warning(f"[{label}] {last_problem}，重试 {attempt + 1}/{max_retries}")
            await asyncio.sleep(min(2 ** attempt, 8))
            continue

        text = _unwrap_cli_envelope(raw)
        text = _strip_code_fence(text).strip()

        # 兜底：Claude 偶尔忘了指令仍按 JSON 返回，尝试抽取任意字符串字段
        if text.startswith("{") and text.endswith("}"):
            parsed = extract_json_object(raw)
            if isinstance(parsed, dict):
                extracted: Optional[str] = None
                # 优先尝试常见键名
                for k in ("markdown", "description", "content", "text",
                          "overview", "body", "result", "output"):
                    v = parsed.get(k)
                    if isinstance(v, str) and v.strip():
                        extracted = v.strip()
                        logger.info(f"[{label}] LLM 返回了 JSON，已从字段 `{k}` 抽出 markdown")
                        break
                # 再兜：若 dict 只有 1 个字符串字段，直接取它（键名未知也能救）
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

        return text, sid

    raise ValueError(f"Claude CLI 调用 {max_retries} 次均失败。最后一次: {last_problem}")
