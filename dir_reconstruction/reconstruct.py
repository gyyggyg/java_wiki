"""
wiki_index.json 重聚类脚本

读取 output/wiki_result/.index/wiki_index.json（405 条 wiki 页面），
用 Claude CLI 每次分类 10 条，把每条分到 categories.py 中定义的目标分类树。

用法:
    python dir_reconstruction/reconstruct.py                   # 全量跑，按 batch=10 处理
    python dir_reconstruction/reconstruct.py --batch 20         # 每次 20 条
    python dir_reconstruction/reconstruct.py --resume           # 从已有进度继续（默认就会 resume）
    python dir_reconstruction/reconstruct.py --dry-run          # 只打印要发送的 batch，不实际调 claude
    python dir_reconstruction/reconstruct.py --max-batches 3    # 最多跑 3 个 batch（用于调试）

输出文件（均在 dir_reconstruction/output/）：
    progress.json              —— 增量保存的每条 wiki → 分类结果（resume 时读它）
    failures.json              —— 记录失败的 batch（超时/schema 错等）
    new_wiki_index.json        —— 最终产物：按新分类重组后的 wiki_index
    category_stats.txt         —— 各分类下的 wiki 数量统计
"""

import os
import sys
import json
import re
import asyncio
import argparse
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from categories import CATEGORY_TREE, VALID_PATHS, render_category_tree_for_prompt
from prompts import SYSTEM_PROMPT, build_user_prompt


# ================================================================
# 路径常量
# ================================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECON_DIR = os.path.join(PROJECT_ROOT, "dir_reconstruction")

# 源 wiki_index.json 的默认位置
# 可通过 --source CLI 参数或 WIKI_INDEX_PATH 环境变量覆盖
DEFAULT_SOURCE_INDEX = os.environ.get(
    "WIKI_INDEX_PATH",
    "/Users/uinas/code/java_wiki/output/wiki_result/.index/wiki_index.json",
)

OUTPUT_DIR = os.path.join(RECON_DIR, "output")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "progress.json")
FAILURES_FILE = os.path.join(OUTPUT_DIR, "failures.json")
NEW_INDEX_FILE = os.path.join(OUTPUT_DIR, "new_wiki_index.json")
STATS_FILE = os.path.join(OUTPUT_DIR, "category_stats.txt")
LOG_DIR = os.path.join(RECON_DIR, "logs")


# ================================================================
# 日志
# ================================================================

def setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"reconstruct_{ts}.log")

    logger = logging.getLogger("reconstruct")
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


# ================================================================
# Claude CLI 封装
# ================================================================

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "sonnet")
CLAUDE_TIMEOUT = int(os.environ.get("DIR_RECONSTRUCTION_TIMEOUT", "180"))


def _find_claude_cli() -> str:
    path = shutil.which("claude")
    if path:
        return path
    if sys.platform == "win32":
        npm_path = os.path.join(os.environ.get("APPDATA", ""), "npm", "claude.cmd")
        if os.path.isfile(npm_path):
            return npm_path
    raise FileNotFoundError("未找到 claude CLI，请确认已安装 Claude Code 并添加到 PATH")


async def invoke_claude(user_prompt: str, system_prompt: str, timeout: int, label: str, logger: logging.Logger) -> str:
    """调用 claude CLI，返回原始输出字符串"""
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
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(input=user_prompt.encode("utf-8")),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"claude CLI 调用超时（{timeout}秒），任务：{label}")

    stdout_str = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
    stderr_str = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
    rc = proc.returncode

    logger.debug(f"[{label}] returncode={rc}")
    logger.debug(f"[{label}] stdout (first 2000 chars):\n{stdout_str[:2000]}")
    if stderr_str.strip():
        logger.debug(f"[{label}] stderr (first 500 chars):\n{stderr_str[:500]}")

    if rc != 0:
        raise RuntimeError(f"claude CLI 调用失败 (code={rc}): {stderr_str[:200]}")
    if not stdout_str.strip():
        raise RuntimeError(f"claude CLI 无输出, returncode={rc}")
    return stdout_str


def _repair_unescaped_quotes_in_values(json_str: str) -> str:
    """尝试修复 JSON 字符串值中未转义的双引号。

    典型错误形态（LLM 忘记 escape 内层引号）：
        "reason": "该模块位于"奖励与交易映射"路径下"
    修复目标：
        "reason": "该模块位于\"奖励与交易映射\"路径下"

    工作原理：逐行扫描，对形如 `"key": "value..."` 的行，把 value 区间内的
    所有 `"` 转义为 `\"`，保留最外层的两个包裹引号。
    """
    # 匹配: 可选前导空白 + "key": " 然后到 行尾前的最后一个 "
    # 支持 value 末尾可选 , 或 }
    pattern = re.compile(r'^(\s*"[^"]+"\s*:\s*")(.*?)("\s*[,}]?\s*)$')
    fixed_lines = []
    for line in json_str.split("\n"):
        m = pattern.match(line)
        if m:
            prefix, value, suffix = m.group(1), m.group(2), m.group(3)
            # 把 value 中所有单独的 " 都变成 \"
            # 但不要把已经转义的 \" 再加 escape
            repaired_value = re.sub(r'(?<!\\)"', r'\\"', value)
            fixed_lines.append(prefix + repaired_value + suffix)
        else:
            fixed_lines.append(line)
    return "\n".join(fixed_lines)


def extract_json_object(raw_output: str) -> dict:
    """从 claude CLI 原始输出中提取 JSON 对象"""
    # 1. 先尝试解包 CLI envelope {"result": "..."}
    try:
        envelope = json.loads(raw_output)
        if isinstance(envelope, dict) and "result" in envelope:
            raw_output = envelope["result"]
    except json.JSONDecodeError:
        pass

    # 2. 去掉 markdown 围栏
    json_str = raw_output.strip()
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", json_str, re.DOTALL)
    if fence_match:
        json_str = fence_match.group(1).strip()

    # 3. 截取最外层 {...}
    start = json_str.find("{")
    end = json_str.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"输出中未找到 JSON 对象，原始（前 300 字符）：{raw_output[:300]}")
    json_str = json_str[start : end + 1]

    # 4. 尝试直接解析，失败则走修复路径
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as first_err:
        repaired = _repair_unescaped_quotes_in_values(json_str)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            # 再失败就抛原始错误（保留原始信息）
            raise first_err


# ================================================================
# 业务逻辑
# ================================================================

def load_source_pages(source_path: str) -> List[dict]:
    if not os.path.isfile(source_path):
        raise FileNotFoundError(f"源文件不存在: {source_path}")
    with open(source_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    pages = data.get("pages", [])
    if not isinstance(pages, list):
        raise ValueError("source JSON 的 pages 不是 list")
    return pages


def load_progress() -> Dict[str, dict]:
    """从 progress.json 加载已完成的分类 {path: {category, reason}}"""
    if not os.path.isfile(PROGRESS_FILE):
        return {}
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_progress(progress: Dict[str, dict]):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def save_failures(failures: List[dict]):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(FAILURES_FILE, "w", encoding="utf-8") as f:
        json.dump(failures, f, ensure_ascii=False, indent=2)


def slim_page_for_prompt(page: dict) -> dict:
    """把一条 wiki 压缩成只给 LLM 看关键字段，节省 token"""
    return {
        "path": page["path"],
        "summary": page.get("summary", "")[:500],  # 限长
        "classes": page.get("classes", [])[:15],   # 最多 15 个类
    }


def validate_batch_result(parsed: dict, batch: List[dict], logger: logging.Logger) -> List[dict]:
    """校验 LLM 返回的 assignments，过滤非法条目。

    返回：[{path, category, reason}] 通过校验的条目
    """
    if not isinstance(parsed, dict) or "assignments" not in parsed:
        raise ValueError(f"返回缺少 'assignments' 键: {list(parsed.keys()) if isinstance(parsed, dict) else type(parsed)}")

    assignments = parsed["assignments"]
    if not isinstance(assignments, list):
        raise ValueError(f"'assignments' 不是 list, 实际类型: {type(assignments)}")

    batch_paths = {p["path"] for p in batch}
    valid_assignments = []
    for a in assignments:
        if not isinstance(a, dict):
            logger.warning(f"跳过非 dict 的 assignment: {a}")
            continue
        p = a.get("path")
        c = a.get("category")
        if p not in batch_paths:
            logger.warning(f"跳过未知 path: {p}")
            continue
        if c not in VALID_PATHS:
            logger.warning(f"跳过非法 category: '{c}' (wiki path={p})")
            continue
        valid_assignments.append({
            "path": p,
            "category": c,
            "reason": a.get("reason", ""),
        })
    return valid_assignments


async def classify_batch(batch: List[dict], category_tree_text: str, batch_idx: int, logger: logging.Logger) -> List[dict]:
    """把一个 batch（10 条 wiki）送给 Claude 分类，返回 valid assignments 列表"""
    slim = [slim_page_for_prompt(p) for p in batch]
    user_prompt = build_user_prompt(slim, category_tree_text)

    label = f"batch-{batch_idx}"
    logger.info(f"[{label}] 发送 {len(batch)} 条 wiki 给 Claude CLI（模型={CLAUDE_MODEL}, 超时={CLAUDE_TIMEOUT}s）")
    raw = await invoke_claude(user_prompt, SYSTEM_PROMPT, CLAUDE_TIMEOUT, label, logger)
    parsed = extract_json_object(raw)
    return validate_batch_result(parsed, batch, logger)


# ================================================================
# 结果整理
# ================================================================

def build_new_index(progress: Dict[str, dict], source_pages: List[dict]) -> dict:
    """生成新的 wiki_index，按分类组织"""
    path_to_page = {p["path"]: p for p in source_pages}

    # { category_path: [page, page, ...] }
    by_category: Dict[str, List[dict]] = {c["path"]: [] for c in CATEGORY_TREE}
    unclassified: List[dict] = []

    for wiki_path, info in progress.items():
        page = path_to_page.get(wiki_path)
        if not page:
            continue
        cat = info.get("category")
        if cat in by_category:
            enriched = dict(page)
            enriched["_classify_reason"] = info.get("reason", "")
            by_category[cat].append(enriched)
        else:
            unclassified.append(page)

    return {
        "categories": [
            {
                "path": c["path"],
                "description": c["description"],
                "pages": by_category.get(c["path"], []),
                "count": len(by_category.get(c["path"], [])),
            }
            for c in CATEGORY_TREE
        ],
        "unclassified": unclassified,
        "total_classified": sum(len(v) for v in by_category.values()),
        "total_unclassified": len(unclassified),
    }


def write_stats(new_index: dict):
    lines = ["=== 分类统计 ==="]
    lines.append(f"已分类: {new_index['total_classified']}")
    lines.append(f"未分类: {new_index['total_unclassified']}")
    lines.append("")
    lines.append("各分类下的 wiki 数量:")
    for c in new_index["categories"]:
        depth = c["path"].count("/")
        indent = "  " * depth
        lines.append(f"{indent}{c['count']:4d}  {c['path']}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ================================================================
# 主流程
# ================================================================

async def main():
    parser = argparse.ArgumentParser(description="基于目标分类树用 Claude CLI 重聚类 wiki_index")
    parser.add_argument("--source", default=DEFAULT_SOURCE_INDEX,
                        help=f"源 wiki_index.json 路径（默认 {DEFAULT_SOURCE_INDEX}，也可用 WIKI_INDEX_PATH 环境变量）")
    parser.add_argument("--batch", type=int, default=10, help="每次送入 Claude 的条数 (默认 10)")
    parser.add_argument("--resume", action="store_true", default=True, help="从 progress.json 继续（默认行为）")
    parser.add_argument("--no-resume", dest="resume", action="store_false", help="忽略已有 progress.json，从零开始")
    parser.add_argument("--dry-run", action="store_true", help="只打印要发送的 batch，不实际调 claude")
    parser.add_argument("--max-batches", type=int, default=None, help="最多跑 N 个 batch 后停止（用于调试）")
    parser.add_argument("--concurrency", type=int, default=1, help="并发 batch 数（默认 1=串行；claude CLI 本地进程，不宜设太大）")
    args = parser.parse_args()

    logger = setup_logger()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    logger.info(f"参数: source={args.source}, batch={args.batch}, resume={args.resume}, "
                f"dry_run={args.dry_run}, max_batches={args.max_batches}, concurrency={args.concurrency}")

    # 1. 加载源数据
    source_pages = load_source_pages(args.source)
    logger.info(f"读取到 {len(source_pages)} 条 wiki 页面（源: {args.source}）")

    # 2. 加载已有进度
    progress = load_progress() if args.resume else {}
    logger.info(f"已存在进度: {len(progress)} 条分类结果")

    # 3. 找出还未分类的
    pending = [p for p in source_pages if p["path"] not in progress]
    logger.info(f"待分类: {len(pending)} 条")

    if not pending:
        logger.info("全部已分类，直接生成最终产物")
        _finalize(source_pages, progress, logger)
        return

    # 4. 校验 claude CLI
    if not args.dry_run:
        try:
            _find_claude_cli()
        except FileNotFoundError as e:
            logger.error(str(e))
            sys.exit(1)

    # 5. 准备 category_tree 文本（复用）
    category_tree_text = render_category_tree_for_prompt()

    # 6. 切 batch
    batches = [pending[i : i + args.batch] for i in range(0, len(pending), args.batch)]
    if args.max_batches is not None:
        batches = batches[: args.max_batches]
    logger.info(f"共 {len(batches)} 个 batch（batch_size={args.batch}）")

    if args.dry_run:
        logger.info("=== DRY-RUN: 仅打印第一个 batch 的 prompt ===")
        if not batches:
            logger.info("(无 batch 可打印)")
            return
        first_slim = [slim_page_for_prompt(p) for p in batches[0]]
        print(build_user_prompt(first_slim, category_tree_text))
        return

    # 7. 执行 batch（支持并发 + 增量保存）
    failures: List[dict] = []
    semaphore = asyncio.Semaphore(max(1, args.concurrency))

    # progress 是共享 dict，需要锁保护写入
    progress_lock = asyncio.Lock()

    async def run_one_batch(idx: int, batch: List[dict]):
        async with semaphore:
            try:
                assignments = await classify_batch(batch, category_tree_text, idx, logger)
                async with progress_lock:
                    for a in assignments:
                        progress[a["path"]] = {"category": a["category"], "reason": a["reason"]}
                    save_progress(progress)
                classified_in_batch = len(assignments)
                missing = [p["path"] for p in batch if p["path"] not in {a["path"] for a in assignments}]
                logger.info(f"[batch-{idx}] 完成: 分类成功 {classified_in_batch}/{len(batch)}"
                            + (f", 遗漏 {len(missing)}" if missing else ""))
                if missing:
                    logger.warning(f"[batch-{idx}] LLM 未返回结果的 wiki path: {missing}")
            except Exception as e:
                logger.error(f"[batch-{idx}] 失败: {type(e).__name__}: {e}", exc_info=True)
                failures.append({
                    "batch_idx": idx,
                    "error": f"{type(e).__name__}: {e}",
                    "wiki_paths": [p["path"] for p in batch],
                })
                save_failures(failures)

    tasks = [run_one_batch(i, b) for i, b in enumerate(batches)]
    await asyncio.gather(*tasks)

    # 8. 最终落地
    _finalize(source_pages, progress, logger)

    logger.info("=== 完成 ===")
    logger.info(f"成功分类 {len(progress)}/{len(source_pages)} 条")
    if failures:
        logger.warning(f"失败 batch 数: {len(failures)} (见 {FAILURES_FILE})")


def _finalize(source_pages: List[dict], progress: Dict[str, dict], logger: logging.Logger):
    """生成最终产物：new_wiki_index.json + category_stats.txt"""
    new_index = build_new_index(progress, source_pages)
    with open(NEW_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(new_index, f, ensure_ascii=False, indent=2)
    logger.info(f"已生成: {NEW_INDEX_FILE} ({new_index['total_classified']} 分类 / {new_index['total_unclassified']} 未分类)")
    write_stats(new_index)
    logger.info(f"已生成统计: {STATS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
