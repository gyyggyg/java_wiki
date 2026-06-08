"""扫描 meta.json 里的所有 mermaid 块 → 用 validate_mermaid.mjs 校验 → 失败的用 Claude CLI 自动修复

流程:
  1. 递归扫描 --input-dir 下所有 *.meta.json
  2. 对每个文件的 wiki 数组，找出所有含 "mermaid" 的 entry
  3. 抽取 mermaid 源码（去 ```mermaid ... ``` 围栏），用 node 校验器验证
  4. 校验失败的：
     - `--no-fix`：只报错不修
     - 默认：调用 Claude CLI 修复；修好后再校验，通过才写回
     - 单张图最多重试 --max-retries 次（默认 3）

用法:
    python business_flow/validate_fix_mermaids.py
    python business_flow/validate_fix_mermaids.py --no-fix                       # 只校验不修
    python business_flow/validate_fix_mermaids.py --input-dir /other/path
    python business_flow/validate_fix_mermaids.py --concurrency 4 --max-retries 5
    python business_flow/validate_fix_mermaids.py --model opus

环境变量:
    CLAUDE_MODEL                  claude CLI 模型（默认 sonnet）
    BF_MERMAID_VALIDATE_TIMEOUT   单次 validator 子进程超时（默认 30s）
    BF_MERMAID_FIX_TIMEOUT        单次 claude 子进程超时（默认 300s）
"""
import argparse
import asyncio
import json
import os
import re
import shutil
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(PROJECT_ROOT, "business_flow", "output", "themes")
DEFAULT_VALIDATOR = os.path.join(PROJECT_ROOT, "scripts", "validate_mermaid.mjs")

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "sonnet")
VALIDATE_TIMEOUT = int(os.environ.get("BF_MERMAID_VALIDATE_TIMEOUT", "30"))
CLAUDE_TIMEOUT = int(os.environ.get("BF_MERMAID_FIX_TIMEOUT", "300"))


# 匹配 ```mermaid\n<src>\n``` 围栏
_FENCE_RE = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)


def extract_mermaid_source(text: str) -> str:
    """从 wiki entry 的 mermaid 字段取纯源码（去掉 ```mermaid ... ``` 围栏）"""
    if not text:
        return ""
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    # 没有围栏 → 原样返回（容错）
    return text.strip()


def wrap_mermaid_source(src: str) -> str:
    """加回 ```mermaid ... ``` 围栏"""
    src = (src or "").strip()
    return f"```mermaid\n{src}\n```"


# ============================================================
# Mermaid 语法校验（node subprocess）
# ============================================================

_SEQ_OPEN_KWS = ("alt ", "opt ", "loop ", "par ", "rect ", "critical ", "break ")


def _strip_seq_box_for_validation(src: str) -> str:
    """剥掉 sequenceDiagram 的 `box ... end` 包装，仅用于校验。

    原因：mermaid+jsdom 组合在 server-side 解析 sequenceDiagram 的 `box` 语法
    时会误报 "Option is not defined"（已知 false positive）。`box` 只是视觉分组，
    不影响语法逻辑。去掉后校验结果才准确；写回原文件时不做这个修改。

    用栈精确匹配 `box` 与它对应的 `end`（绕开 alt/opt/loop/par/rect/critical/break 等其它块）。
    """
    if not src or "sequenceDiagram" not in src.split("\n", 1)[0] + "\n" + (src.split("\n", 2)[1] if "\n" in src else ""):
        # 非 sequenceDiagram 直接返回
        if not any(l.strip().startswith("sequenceDiagram") for l in src.split("\n")[:5]):
            return src

    lines = src.split("\n")
    out: List[str] = []
    stack: List[str] = []  # 每项 "box" 或 "other"
    for ln in lines:
        s = ln.strip()
        if s.startswith("box ") or s == "box":
            stack.append("box")
            continue  # 丢弃 box 开启行
        if any(s.startswith(kw) for kw in _SEQ_OPEN_KWS):
            stack.append("other")
            out.append(ln)
            continue
        if s == "end":
            if stack:
                kind = stack.pop()
                if kind == "box":
                    continue  # 丢弃这个配对的 end
            out.append(ln)
            continue
        out.append(ln)
    return "\n".join(out)


async def validate_mermaid(src: str, validator: str,
                             timeout: int = VALIDATE_TIMEOUT) -> Tuple[bool, str]:
    """调 node scripts/validate_mermaid.mjs -  校验 mermaid 源码。返回 (is_valid, error_msg)

    送入校验器前会先 `_strip_seq_box_for_validation` 规避 mermaid+jsdom 的 box false positive。
    """
    if not src or not src.strip():
        return False, "empty source"
    if not os.path.isfile(validator):
        return True, "validator script missing (skip)"

    # 规避 mermaid+jsdom 对 `box` 语法的 false positive
    validation_src = _strip_seq_box_for_validation(src)

    try:
        proc = await asyncio.create_subprocess_exec(
            "node", validator, "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return True, "node executable not found (skip)"

    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(validation_src.encode("utf-8")),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        return False, f"validator timeout ({timeout}s)"

    if proc.returncode == 0:
        return True, ""
    err = (stderr or b"").decode("utf-8", errors="replace").strip()
    if not err:
        err = (stdout or b"").decode("utf-8", errors="replace").strip()
    return False, err or "unknown parse error"


# ============================================================
# Claude CLI 修复
# ============================================================

def _find_claude_cli() -> str:
    path = shutil.which("claude")
    if path:
        return path
    raise FileNotFoundError("未找到 claude CLI（请安装 Claude Code）")


def build_fix_prompt(bad_src: str, err_msg: str, context: str = "") -> str:
    return f"""你是一个 Mermaid 语法修复专家。下面这张 Mermaid 图未能通过语法校验，请只修正**语法错误**，**不要改变图的业务逻辑、节点、边、样式**。

## 上下文
{context or '(无)'}

## 校验器报告的错误
```
{err_msg[:1500]}
```

## 原始 Mermaid 源码
```
{bad_src}
```

## 严格要求
- 保持所有 participant / 节点 id 不变（上游 mapping 还在用）
- 保持 subgraph 分组结构不变
- 保持 style/class 指令不变
- 保持箭头上的标签文字（包括中文、emoji）
- 只改明显的语法问题（括号/引号/冒号/非法字符等）

## 输出格式（严格 JSON，无围栏、无前言）
{{
  "fixed_mermaid": "这里是修复后的 mermaid 源码，不包含 ``` 围栏"
}}
"""


def _extract_fixed_mermaid(text: str) -> Optional[str]:
    """从 Claude 输出里抽 {"fixed_mermaid": "..."} 的值"""
    if not text:
        return None
    t = text.strip()
    # 去可能的围栏
    t = re.sub(r"^```(?:json)?\s*\n?", "", t)
    t = re.sub(r"\n?```\s*$", "", t)
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1:
        return None
    blob = t[start:end + 1]
    try:
        obj = json.loads(blob)
    except json.JSONDecodeError:
        # 兜底：某些情况下 LLM 可能输出里 value 里有未转义换行，尝试修一次
        blob_fixed = re.sub(r'(?<!\\)\n', r'\\n', blob)
        try:
            obj = json.loads(blob_fixed)
        except json.JSONDecodeError:
            return None
    val = obj.get("fixed_mermaid") or obj.get("fixed") or ""
    return val.strip() if val else None


async def fix_with_claude(
    bad_src: str, err_msg: str, context: str,
    timeout: int = CLAUDE_TIMEOUT, model: str = CLAUDE_MODEL,
) -> Tuple[Optional[str], str]:
    """调 claude CLI 修复。返回 (修好的 mermaid 源码, 失败原因)。

    成功：(fixed_src, "")
    失败：(None, 具体原因)
    """
    claude_bin = _find_claude_cli()
    cmd = [
        claude_bin, "-p",
        "--model", model,
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
    ]
    prompt = build_fix_prompt(bad_src, err_msg, context)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(prompt.encode("utf-8")),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        return None, f"claude CLI 超时（{timeout}s）"

    if proc.returncode != 0:
        stderr_tail = (stderr_bytes or b"").decode("utf-8", errors="replace").strip()
        return None, (f"claude CLI rc={proc.returncode}: "
                      + (stderr_tail[:200] if stderr_tail else "(无 stderr)"))

    raw = stdout_bytes.decode("utf-8", errors="replace")
    if not raw.strip():
        return None, "claude CLI stdout 为空"

    # Claude CLI 用 --output-format json 时 stdout 是 envelope: {"result": "<string>", ...}
    content: str = raw
    try:
        envelope = json.loads(raw)
        if isinstance(envelope, dict):
            if envelope.get("is_error"):
                err_field = envelope.get("error") or envelope.get("subtype") or "unknown"
                return None, f"claude envelope is_error=true: {str(err_field)[:200]}"
            content = envelope.get("result") or envelope.get("content") or raw
    except json.JSONDecodeError:
        pass

    fixed = _extract_fixed_mermaid(content)
    if not fixed:
        preview = content[:160].replace("\n", "\\n")
        return None, f"JSON 抽取失败；content 头 160 字符：{preview}..."
    return fixed, ""


# ============================================================
# 单文件处理
# ============================================================

async def process_file(
    file_path: str,
    validator: str,
    fix: bool,
    max_retries: int,
    fix_sem: asyncio.Semaphore,
    model: str,
    log_prefix: str = "",
) -> Dict[str, int]:
    """处理一个 .meta.json 文件：扫 mermaid → 校验 → (可选)修复 → 写回

    返回 {total, ok, fixed, still_bad}
    """
    stats = {"total": 0, "ok": 0, "fixed": 0, "still_bad": 0}
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    wiki = data.get("wiki", [])
    modified = False

    for idx, entry in enumerate(wiki):
        if not isinstance(entry, dict) or "mermaid" not in entry:
            continue
        stats["total"] += 1
        raw_field = entry.get("mermaid", "")
        src = extract_mermaid_source(raw_field)

        ok, err = await validate_mermaid(src, validator)
        if ok:
            stats["ok"] += 1
            continue

        preview_err = (err.splitlines() or ["?"])[0][:140]
        print(f"{log_prefix} ✗ wiki[{idx}]: {preview_err}")

        if not fix:
            stats["still_bad"] += 1
            continue

        # 修复循环：最多 max_retries 次
        current_src = src
        current_err = err
        fixed_ok = False
        context = f"文件: {os.path.basename(file_path)} · wiki[{idx}]"
        for attempt in range(1, max_retries + 1):
            async with fix_sem:
                candidate, fail_reason = await fix_with_claude(
                    current_src, current_err, context,
                    timeout=CLAUDE_TIMEOUT, model=model,
                )
            if not candidate:
                print(f"{log_prefix}   · try {attempt}/{max_retries}: claude 未返回修复 "
                      f"({fail_reason})")
                continue
            ok2, err2 = await validate_mermaid(candidate, validator)
            if ok2:
                entry["mermaid"] = wrap_mermaid_source(candidate)
                stats["fixed"] += 1
                modified = True
                fixed_ok = True
                print(f"{log_prefix}   ✓ try {attempt}/{max_retries}: 修好")
                break
            current_src = candidate
            current_err = err2
            print(f"{log_prefix}   · try {attempt}/{max_retries}: 仍错 "
                  f"{(err2.splitlines() or ['?'])[0][:100]}")

        if not fixed_ok:
            stats["still_bad"] += 1

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return stats


# ============================================================
# 主流程
# ============================================================

async def main_async(args) -> int:
    input_dir = os.path.abspath(args.input_dir)
    validator = os.path.abspath(args.validator)

    if not os.path.isdir(input_dir):
        print(f"ERROR: 输入目录不存在: {input_dir}", file=sys.stderr)
        return 1
    if not os.path.isfile(validator):
        print(f"ERROR: 校验脚本不存在: {validator}", file=sys.stderr)
        return 1

    if args.fix:
        try:
            _find_claude_cli()
        except FileNotFoundError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

    # 收集 .meta.json
    targets: List[str] = []
    for root, _, files in os.walk(input_dir):
        for fn in files:
            if fn.endswith(".meta.json"):
                targets.append(os.path.join(root, fn))
    targets.sort()

    print(f"扫描目录: {input_dir}")
    print(f"校验脚本: {validator}")
    print(f"找到 {len(targets)} 个 .meta.json 文件")
    print(f"修复模式: {'开启（claude CLI 模型 = ' + args.model + '）' if args.fix else '关闭（仅校验）'}")
    print(f"并发 claude 修复数: {args.concurrency}")
    print(f"单图最大重试: {args.max_retries}")
    print()

    if not targets:
        print("无可处理文件")
        return 0

    fix_sem = asyncio.Semaphore(max(1, args.concurrency))
    t0 = datetime.now()

    grand = {"total": 0, "ok": 0, "fixed": 0, "still_bad": 0, "files_with_errors": 0}
    for i, path in enumerate(targets, 1):
        relpath = os.path.relpath(path, input_dir)
        prefix = f"[{i}/{len(targets)}] {relpath}"
        print(prefix)
        try:
            s = await process_file(
                path, validator, args.fix, args.max_retries, fix_sem,
                model=args.model, log_prefix="  ",
            )
        except Exception as e:
            print(f"  ! 处理失败: {type(e).__name__}: {e}")
            continue
        for k in ("total", "ok", "fixed", "still_bad"):
            grand[k] += s.get(k, 0)
        if s["still_bad"] > 0 or (not args.fix and s["total"] > s["ok"]):
            grand["files_with_errors"] += 1
        summary = f"  files: total={s['total']} ok={s['ok']}"
        if args.fix:
            summary += f" fixed={s['fixed']} bad={s['still_bad']}"
        else:
            summary += f" bad={s['total'] - s['ok']}"
        print(summary)
        print()

    elapsed = (datetime.now() - t0).total_seconds()
    print("=" * 60)
    print("汇总")
    print("=" * 60)
    print(f"扫描 mermaid 总数: {grand['total']}")
    print(f"  ✓ 一次通过:      {grand['ok']}")
    if args.fix:
        print(f"  🛠 修复成功:      {grand['fixed']}")
        print(f"  ✗ 无法修复:      {grand['still_bad']}")
    else:
        bad = grand["total"] - grand["ok"]
        print(f"  ✗ 未通过 (未修): {bad}")
    print(f"  文件含错误数:    {grand['files_with_errors']}")
    print(f"  总耗时:          {elapsed:.1f}s")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="批量校验 + Claude CLI 自动修复 mermaid",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input-dir", default=DEFAULT_DIR,
                        help=f"扫描目录（默认 {DEFAULT_DIR}）")
    parser.add_argument("--validator", default=DEFAULT_VALIDATOR,
                        help=f"validator 脚本（默认 {DEFAULT_VALIDATOR}）")
    parser.add_argument("--no-fix", dest="fix", action="store_false", default=True,
                        help="只校验不调 claude 修复")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="单张图的最大修复重试次数（默认 3）")
    parser.add_argument("--concurrency", type=int, default=2,
                        help="并发 claude 修复数（默认 2）")
    parser.add_argument("--model", default=CLAUDE_MODEL,
                        help=f"Claude 模型（默认 {CLAUDE_MODEL}）")
    args = parser.parse_args()

    try:
        code = asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n中断", file=sys.stderr)
        sys.exit(1)
    sys.exit(code)


if __name__ == "__main__":
    main()
