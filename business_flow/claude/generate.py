"""
业务流 wiki 生成器 —— Claude CLI 版本

读取  business_flow/business_flows_with_span.json
输出  business_flow/claude/output/<flow名>.meta.json × N（flow 名末尾"流"字会被省略）

不依赖 OpenAI 兼容 API，全部走本地 `claude` CLI 子进程。

运行:
    python business_flow/claude/generate.py
    python business_flow/claude/generate.py --flow "支付宝支付"
    python business_flow/claude/generate.py --concurrency 2
    python business_flow/claude/generate.py --start 5 --end 10   # 只跑输入里第 5~10 个
    python business_flow/claude/generate.py --start 5            # 第 5 个到末尾
    python business_flow/claude/generate.py --end 3              # 前 3 个
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
load_dotenv()

from interfaces.neo4j_interface import Neo4jInterface

from business_flow.claude.schema import SectionNode, TextNode
from business_flow.claude.neo4j_fetch import fetch_classes_full_context
from business_flow.claude.class_context import build_class_context_text
from business_flow.claude.sections import (
    build_overview_section,
    build_entrypoints_section,
    build_sequence_section,
    build_data_model_section,
    build_control_flow_section,
    build_components_section,
    build_state_machine_section,
)
from business_flow.claude.assembler import assemble_wiki


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BF_DIR = os.path.join(PROJECT_ROOT, "business_flow")
CLAUDE_DIR = os.path.join(BF_DIR, "claude")
INPUT_PATH = os.path.join(BF_DIR, "business_flows_with_span.json")
OUTPUT_DIR = os.path.join(CLAUDE_DIR, "output")
LOG_DIR = os.path.join(CLAUDE_DIR, "logs")


def setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"generate_{ts}.log")
    logger = logging.getLogger("business_flow.claude")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                                      datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    logger.info(f"日志文件: {log_file}")
    return logger


def build_scope_from_flow(flow: dict) -> dict:
    span = flow.get("span", {})
    details = span.get("core_classes_detail", []) or []

    class_ids, interface_ids, enum_ids, record_ids = [], [], [], []
    for c in details:
        cid = c.get("class_id")
        if not cid:
            continue
        labels = c.get("labels") or []
        cid = str(cid)
        if "Class" in labels:
            class_ids.append(cid)
        elif "Interface" in labels:
            interface_ids.append(cid)
        elif "Enum" in labels:
            enum_ids.append(cid)
        elif "Record" in labels:
            record_ids.append(cid)
        else:
            class_ids.append(cid)

    return {
        "flow_name": flow.get("name", ""),
        "flow_kind": flow.get("kind", ""),
        "description": flow.get("description", ""),
        "class_ids": sorted(set(class_ids)),
        "interface_ids": sorted(set(interface_ids)),
        "enum_ids": sorted(set(enum_ids)),
        "record_ids": sorted(set(record_ids)),
    }


def flow_to_filename(flow_name: str) -> str:
    """把 flow 名字转为输出文件名。

    规则：
    - 去掉不适合做文件名的符号（/、空格、括号）
    - 末尾有「流」字则去掉（避免"xxx流.meta.json"冗余）
    - 最终格式：`<flow名>.meta.json`（不再加"业务流_"前缀）
    """
    safe = flow_name.replace("/", "_").replace(" ", "_").replace("(", "").replace(")", "")
    if safe.endswith("流") and len(safe) > 1:
        safe = safe[:-1]
    return f"{safe}.meta.json"


async def generate_wiki_for_flow(flow: dict, neo4j, logger: logging.Logger) -> dict:
    name = flow.get("name", "?")
    logger.info(f"========== 开始处理业务流: {name} ==========")

    scope = build_scope_from_flow(flow)
    all_class_like = scope["class_ids"] + scope["interface_ids"] + scope["enum_ids"] + scope["record_ids"]
    if not all_class_like:
        logger.warning(f"[{name}] scope 为空，跳过")
        return None

    all_class_rows = await fetch_classes_full_context(neo4j, all_class_like)
    logger.info(f"[{name}] fetched {len(all_class_rows)} 类的 source_code/SE_What")

    ctx_info = build_class_context_text(all_class_rows)
    logger.info(f"[{name}] class_context: mode={ctx_info['mode']}, chars={ctx_info['char_count']}, "
                f"classes={ctx_info['class_count']}, dropped={ctx_info['dropped_count']}")
    class_context_text = ctx_info["text"]

    # 并发跑 7 个章节（6 个调 Claude + 1 个纯模板）
    # 章节顺序:
    #   §1 业务概述         (overview)
    #   §2 数据结构以及架构概览 (data_model) —— ER 图 + 相关类源码
    #   §3 对外接口清单      (entrypoints)
    #   §4 关键协作时序图    (sequence)
    #   §5 核心业务流程图    (control_flow)
    #   §6 业务状态流转      (state_machine) —— stateDiagram-v2
    #   §7 组件索引          (components) —— 纯模板，无 LLM
    results = await asyncio.gather(
        build_overview_section(flow, scope, neo4j),                                     # §1
        build_data_model_section(flow, scope, neo4j),                                  # §2 架构概览（ER 图）
        build_entrypoints_section(flow, scope, class_context_text, all_class_rows),     # §3
        build_sequence_section(flow, scope, class_context_text, all_class_rows, neo4j), # §4
        build_control_flow_section(flow, scope, all_class_rows, neo4j),                 # §5
        build_state_machine_section(flow, scope, all_class_rows, neo4j),                # §6
        build_components_section(flow, scope, neo4j),                                   # §7
        return_exceptions=True,
    )
    section_nodes = []
    s6_skipped = False
    for sname, r in zip(["s1", "s2", "s3", "s4", "s5", "s6", "s7"], results):
        if isinstance(r, Exception):
            logger.error(f"[{name}] {sname} 失败: {type(r).__name__}: {r}", exc_info=r)
            section_nodes.append(SectionNode(
                title=f"## {sname.upper()} ({sname} 生成失败)",
                content=[TextNode(content={"markdown": f"_生成失败: {type(r).__name__}: {r}_"})],
            ))
        elif r is None:
            # 目前只有 §6 状态机 section 允许返回 None（无可画状态机时）
            logger.info(f"[{name}] {sname} 返回 None，跳过该章节")
            if sname == "s6":
                s6_skipped = True
        else:
            section_nodes.append(r)

    # §6 状态机被跳过时，把 §7 组件索引升级为 §6，保证编号连续
    if s6_skipped:
        for sec in section_nodes:
            if isinstance(sec, SectionNode) and sec.title.startswith("## 7."):
                sec.title = "## 6." + sec.title[len("## 7."):]
                # 同步更新 neo4j_id 的键，从 "7.xxx" 改 "6.xxx"
                new_nid = {}
                for k, v in (sec.neo4j_id or {}).items():
                    if k.startswith("7."):
                        new_nid["6." + k[2:]] = v
                    else:
                        new_nid[k] = v
                sec.neo4j_id = new_nid
                logger.info(f"[{name}] 因 §6 被跳过，组件索引章节从 §7 升为 §6")
                break

    doc = await assemble_wiki(flow, section_nodes, neo4j)
    return doc


async def main():
    parser = argparse.ArgumentParser(description="用 Claude CLI 为每个业务流生成 wiki")
    parser.add_argument("--flow", default=None, help="只生成指定名字的 flow（调试用）")
    parser.add_argument("--start", type=int, default=None,
                        help="按输入顺序从第 N 个 flow 开始（1-indexed，含），默认从头开始")
    parser.add_argument("--end", type=int, default=None,
                        help="按输入顺序到第 N 个 flow 结束（1-indexed，含），默认到末尾")
    parser.add_argument("--concurrency", type=int, default=1,
                        help="并发 flow 数（Claude CLI 是本地进程，建议 1-3）")
    args = parser.parse_args()

    if args.flow and (args.start is not None or args.end is not None):
        parser.error("--flow 和 --start/--end 不能同时使用")
    if args.start is not None and args.start < 1:
        parser.error(f"--start 必须 >= 1，实际收到 {args.start}")
    if args.end is not None and args.end < 1:
        parser.error(f"--end 必须 >= 1，实际收到 {args.end}")
    if (args.start is not None and args.end is not None
            and args.start > args.end):
        parser.error(f"--start ({args.start}) 不能大于 --end ({args.end})")

    logger = setup_logger()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 校验 claude CLI
    if not shutil.which("claude"):
        logger.error("未找到 claude CLI，请先安装 Claude Code")
        sys.exit(1)
    logger.info(f"使用 Claude CLI: {shutil.which('claude')}")

    if not os.path.isfile(INPUT_PATH):
        logger.error(f"输入文件不存在: {INPUT_PATH}")
        sys.exit(1)
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    flows = data.get("flows") or []
    logger.info(f"输入共 {len(flows)} 个 flow")

    if args.flow:
        flows = [f for f in flows if f.get("name") == args.flow]
        if not flows:
            logger.error(f"未找到 flow: {args.flow}")
            sys.exit(1)
        logger.info(f"只处理指定 flow: {args.flow}")
    elif args.start is not None or args.end is not None:
        total = len(flows)
        # 1-indexed → 0-indexed；end 含右端点（切片用 end_idx_excl）
        start_idx = (args.start or 1) - 1
        end_idx_excl = args.end if args.end is not None else total
        if start_idx >= total:
            logger.error(f"--start {args.start} 超过总数 {total}")
            sys.exit(1)
        if end_idx_excl > total:
            logger.warning(f"--end {args.end} 超过总数 {total}，截断到 {total}")
            end_idx_excl = total
        flows = flows[start_idx:end_idx_excl]
        flow_names = [f.get("name", "?") for f in flows]
        logger.info(
            f"按范围处理第 {start_idx + 1}-{end_idx_excl} 个 flow（共 {len(flows)} 个）: "
            f"{flow_names}"
        )

    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    if not await neo4j.test_connection():
        logger.error("Neo4j 连接失败")
        sys.exit(1)
    logger.info("Neo4j 连接成功")

    sem = asyncio.Semaphore(max(1, args.concurrency))
    results_summary: Dict[str, str] = {}

    async def run_one(flow):
        name = flow.get("name", "?")
        async with sem:
            try:
                doc = await generate_wiki_for_flow(flow, neo4j, logger)
                if doc is None:
                    results_summary[name] = "empty"
                    return
                out_path = os.path.join(OUTPUT_DIR, flow_to_filename(name))
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)
                logger.info(f"[{name}] 已保存 → {out_path}")
                results_summary[name] = "ok"
            except Exception as e:
                logger.error(f"[{name}] 失败: {type(e).__name__}: {e}", exc_info=True)
                results_summary[name] = f"error: {type(e).__name__}"

    try:
        await asyncio.gather(*[run_one(f) for f in flows])
    finally:
        neo4j.close()

    # 汇总各 flow 中 §2 数据模型章节识别出的缺失类
    missing_report_entries = []
    for flow in flows:
        missing = flow.get("_missing_classes") or []
        if not missing:
            continue
        missing_report_entries.append({
            "flow_name": flow.get("name", ""),
            "flow_kind": flow.get("kind", ""),
            "missing_classes": missing,
            "notes": flow.get("_missing_data_notes", ""),
        })
    if missing_report_entries:
        report_path = os.path.join(OUTPUT_DIR, "missing_classes_report.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        report = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total_flows_with_missing_data": len(missing_report_entries),
            "flows_with_missing_data": missing_report_entries,
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        total_missing = sum(len(e["missing_classes"]) for e in missing_report_entries)
        logger.info(f"缺失类报告已保存 → {report_path} "
                    f"({len(missing_report_entries)} 个 flow, 共 {total_missing} 个疑似缺失类)")

    logger.info("=" * 60)
    logger.info("汇总:")
    for n, s in results_summary.items():
        logger.info(f"  [{s:20s}] {n}")
    ok = sum(1 for v in results_summary.values() if v == "ok")
    logger.info(f"成功 {ok}/{len(flows)}")


if __name__ == "__main__":
    asyncio.run(main())
