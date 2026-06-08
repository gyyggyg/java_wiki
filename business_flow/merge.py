"""
业务流合并脚本

读取  business_flow/business_flows.json
输出  business_flow/business_flows_merged.json

运行:
    python business_flow/merge.py
"""

import asyncio
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from typing import Dict, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from merge_prompts import SYSTEM_PROMPT, build_user_prompt


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BF_DIR = os.path.join(PROJECT_ROOT, "business_flow")
INPUT_PATH = os.path.join(BF_DIR, "business_flows.json")
OUTPUT_PATH = os.path.join(BF_DIR, "business_flows_merged.json")
LOG_DIR = os.path.join(BF_DIR, "logs")

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "sonnet")
CLAUDE_TIMEOUT = int(os.environ.get("BUSINESS_FLOW_MERGE_TIMEOUT", "240"))


def setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"merge_{ts}.log")
    logger = logging.getLogger("business_flow.merge")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    logger.info(f"日志文件: {log_file}")
    return logger


# ============ Claude CLI 调用（和 dir_reconstruction 保持一致） ============
def _find_claude_cli() -> str:
    path = shutil.which("claude")
    if path:
        return path
    if sys.platform == "win32":
        npm_path = os.path.join(os.environ.get("APPDATA", ""), "npm", "claude.cmd")
        if os.path.isfile(npm_path):
            return npm_path
    raise FileNotFoundError("未找到 claude CLI，请先安装 Claude Code")


async def invoke_claude(user_prompt: str, system_prompt: str, timeout: int, logger: logging.Logger) -> str:
    claude_bin = _find_claude_cli()
    env = os.environ.copy()
    if sys.platform == "win32" and "CLAUDE_CODE_GIT_BASH_PATH" not in env:
        git_bash = shutil.which("bash")
        if git_bash:
            env["CLAUDE_CODE_GIT_BASH_PATH"] = git_bash

    proc = await asyncio.create_subprocess_exec(
        claude_bin, "-p",
        "--system-prompt", system_prompt,
        "--model", CLAUDE_MODEL,
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        out, err = await asyncio.wait_for(
            proc.communicate(input=user_prompt.encode("utf-8")), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"claude CLI 调用超时（{timeout}s）")

    stdout_s = out.decode("utf-8", errors="replace") if out else ""
    stderr_s = err.decode("utf-8", errors="replace") if err else ""
    logger.debug(f"claude stdout 前 2000 字符:\n{stdout_s[:2000]}")
    if stderr_s.strip():
        logger.debug(f"claude stderr 前 500 字符:\n{stderr_s[:500]}")
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI 失败 (code={proc.returncode}): {stderr_s[:200]}")
    if not stdout_s.strip():
        raise RuntimeError("claude CLI 无输出")
    return stdout_s


def _repair_unescaped_quotes_in_values(s: str) -> str:
    pat = re.compile(r'^(\s*"[^"]+"\s*:\s*")(.*?)("\s*[,}]?\s*)$')
    out = []
    for line in s.split("\n"):
        m = pat.match(line)
        if m:
            prefix, value, suffix = m.group(1), m.group(2), m.group(3)
            value = re.sub(r'(?<!\\)"', r'\\"', value)
            out.append(prefix + value + suffix)
        else:
            out.append(line)
    return "\n".join(out)


def extract_json_object(raw: str) -> dict:
    try:
        env = json.loads(raw)
        if isinstance(env, dict) and "result" in env:
            raw = env["result"]
    except json.JSONDecodeError:
        pass
    s = raw.strip()
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", s, re.DOTALL)
    if m:
        s = m.group(1).strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"输出中未找到 JSON 对象，原始前 300 字: {raw[:300]}")
    s = s[start:end + 1]
    try:
        return json.loads(s)
    except json.JSONDecodeError as e1:
        try:
            return json.loads(_repair_unescaped_quotes_in_values(s))
        except json.JSONDecodeError:
            raise e1


# ============ 校验 + 应用合并 ============

def validate_plan(original_flows: List[dict], plan: dict, logger: logging.Logger) -> dict:
    name_to_flow = {f["name"]: f for f in original_flows}
    merges = plan.get("merges") or []
    keep_as_is = list(plan.get("keep_as_is") or [])
    clean_merges: List[dict] = []
    consumed = set()

    for m in merges:
        sources = [s for s in m.get("source_flow_names", []) if s]
        unknown = [s for s in sources if s not in name_to_flow]
        if unknown:
            logger.warning(f"引用了不存在的 flow，已忽略: {unknown}")
            sources = [s for s in sources if s in name_to_flow]
        sources = [s for s in sources if s not in consumed]
        if len(sources) < 2:
            logger.warning(f"合并组 source 不足 2 个 (target={m.get('target_name')}) → 源 flow 进 keep_as_is")
            for s in sources:
                if s not in keep_as_is:
                    keep_as_is.append(s)
            continue
        kinds = {name_to_flow[s].get("kind") for s in sources}
        if len(kinds) > 1:
            logger.warning(f"合并组 '{m.get('target_name')}' 跨 kind {kinds}，已拒绝")
            for s in sources:
                if s not in keep_as_is:
                    keep_as_is.append(s)
            continue
        target_kind = m.get("target_kind") or next(iter(kinds))
        if target_kind not in kinds:
            target_kind = next(iter(kinds))
        for s in sources:
            consumed.add(s)
        clean_merges.append({
            "target_name": m.get("target_name") or "未命名合并流",
            "target_kind": target_kind,
            "target_description": m.get("target_description", ""),
            "source_flow_names": sources,
            "reason": m.get("reason", ""),
        })

    clean_keep: List[str] = []
    for k in keep_as_is:
        if k in name_to_flow and k not in consumed and k not in clean_keep:
            clean_keep.append(k)
    leftover = [f["name"] for f in original_flows if f["name"] not in consumed and f["name"] not in clean_keep]
    if leftover:
        logger.warning(f"合并方案漏掉 {len(leftover)} 个 flow，自动进 keep_as_is: {leftover}")
        clean_keep.extend(leftover)

    return {"merges": clean_merges, "keep_as_is": clean_keep}


def apply_plan(original_flows: List[dict], plan: dict, logger: logging.Logger) -> List[dict]:
    name_to_flow = {f["name"]: f for f in original_flows}
    out: List[dict] = []

    for m in plan["merges"]:
        seen = set()
        entries: List[dict] = []
        for src in m["source_flow_names"]:
            for e in name_to_flow[src].get("entry_methods", []):
                key = e.get("node_id") or (e.get("class"), e.get("method"))
                if key in seen:
                    continue
                seen.add(key)
                entries.append(e)
        out.append({
            "name": m["target_name"],
            "kind": m["target_kind"],
            "description": m["target_description"],
            "entry_methods": entries,
            "_merged_from": m["source_flow_names"],
            "_merge_reason": m.get("reason", ""),
        })
        logger.info(f"[合并] {m['target_name']} ← {m['source_flow_names']} → {len(entries)} entries")

    for k in plan["keep_as_is"]:
        out.append(dict(name_to_flow[k]))

    return out


# ============ 主流程 ============
async def main():
    logger = setup_logger()

    if not os.path.isfile(INPUT_PATH):
        logger.error(f"输入文件不存在: {INPUT_PATH}")
        sys.exit(1)
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    flows = data.get("flows") or []
    logger.info(f"输入 {len(flows)} 个 flow")
    if not flows:
        logger.error("输入没有 flows")
        sys.exit(1)

    try:
        _find_claude_cli()
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    user_prompt = build_user_prompt(flows)
    logger.info(f"调用 Claude（model={CLAUDE_MODEL}, timeout={CLAUDE_TIMEOUT}s）")
    raw = await invoke_claude(user_prompt, SYSTEM_PROMPT, CLAUDE_TIMEOUT, logger)

    try:
        plan = extract_json_object(raw)
    except Exception as e:
        logger.error(f"解析 claude 返回失败: {e}")
        logger.error(f"原始前 500 字: {raw[:500]}")
        sys.exit(1)

    if not isinstance(plan, dict) or "merges" not in plan or "keep_as_is" not in plan:
        logger.error(f"方案格式不符: keys={list(plan.keys()) if isinstance(plan, dict) else type(plan)}")
        sys.exit(1)

    plan = validate_plan(flows, plan, logger)

    logger.info("=" * 60)
    logger.info(f"合并方案: {len(plan['merges'])} 组合并，{len(plan['keep_as_is'])} 个保留")
    for m in plan["merges"]:
        logger.info(f"  [合并] {m['target_name']}  kind={m['target_kind']}")
        logger.info(f"         ← {m['source_flow_names']}")
        logger.info(f"         reason={m['reason']}")
    logger.info("=" * 60)

    merged = apply_plan(flows, plan, logger)

    result = {
        "flows": merged,
        "_merge_plan": plan,
        "_original_flow_count": len(flows),
        "_merged_flow_count": len(merged),
    }

    logger.info(f"最终 flow 数: {len(merged)}（原 {len(flows)} → 减少 {len(flows) - len(merged)}）")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info(f"已写入: {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
