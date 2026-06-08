"""只重新生成已有 wiki meta.json 的 §5 核心业务流程图章节。

用途：迭代调试 §5 prompt / 逻辑时，不想为其他 5 个章节重复付费。
本脚本读取已有的 .meta.json，仅替换 §5 相关条目和 source_id_list，其他章节原样保留。

用法：
    # 按业务流名（默认读 output/<name-去流>.meta.json，输出覆盖）
    python business_flow/claude/regenerate_section5.py --flow "稿件资讯流"
    python business_flow/claude/regenerate_section5.py --flow "稿件资讯"  # 去"流"也行，脚本自动补

    # 指定输入/输出路径
    python business_flow/claude/regenerate_section5.py \
        --meta business_flow/claude/output/稿件资讯.meta.json \
        --out  /tmp/new.meta.json

    # 创建 .bak 备份再覆盖
    python business_flow/claude/regenerate_section5.py --flow "稿件资讯流" --backup
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from dotenv import load_dotenv
load_dotenv()

from interfaces.neo4j_interface import Neo4jInterface
from business_flow.claude.neo4j_fetch import fetch_classes_full_context, resolve_source_files
from business_flow.claude.sections import build_control_flow_section
from business_flow.claude.assembler import _section_to_wiki_entries, _collect_entry_node_ids
from business_flow.claude.generate import build_scope_from_flow, flow_to_filename


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BF_DIR = os.path.join(PROJECT_ROOT, "business_flow")
CLAUDE_DIR = os.path.join(BF_DIR, "claude")
INPUT_PATH = os.path.join(BF_DIR, "business_flows_with_span.json")
OUTPUT_DIR = os.path.join(CLAUDE_DIR, "output")
LOG_DIR = os.path.join(CLAUDE_DIR, "logs")


def setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"regen_s5_{ts}.log")
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


def find_section5_range(wiki: List[Dict[str, Any]]) -> Tuple[int, int]:
    """定位 §5 在 wiki 条目里的 [start, end) 区间。

    规则：
    - start = 第一个 markdown 以 `## 5.` 开头的条目索引
    - end   = start 之后，第一个 markdown 以 `## ` 开头且不以 `## 5.` 开头的条目索引；否则 len(wiki)
    - ChartNode entries（有 mermaid 无 markdown）夹在 §5 中间时不破坏 §5 连续性（它们继承上一段文字的章节归属）

    返回 (start, end)；未找到则 (len(wiki), len(wiki))。
    """
    start = None
    for i, entry in enumerate(wiki):
        md = entry.get("markdown", "") or ""
        if md.startswith("## 5."):
            start = i
            break
    if start is None:
        return len(wiki), len(wiki)

    end = len(wiki)
    for i in range(start + 1, len(wiki)):
        md = wiki[i].get("markdown", "") or ""
        if md.startswith("## ") and not md.startswith("## 5."):
            end = i
            break
    return start, end


async def rebuild_source_id_list(
    final_wiki: List[Dict[str, Any]],
    new_s5_prebuilt_sids: List[Dict[str, Any]],
    existing_source_id_list: List[Dict[str, Any]],
    neo4j,
    logger: logging.Logger,
) -> List[Dict[str, Any]]:
    """基于最终 wiki + 新 §5 的 chart 预建 source_id + 既有 source_id_list，重建 source_id_list。

    策略（从高到低优先级）：
    1. 新 §5 的 prebuilt（带准确行号）
    2. 既有 source_id_list（保留 §1~§4/§6 的 chart prebuilt + 通用 nodeId）
    3. Neo4j 查询（只对 wiki 引用但前两档都不覆盖的纯 nodeId）
    """
    # 构造查询字典
    new_s5_prebuilt_map: Dict[str, Dict[str, Any]] = {}
    for e in new_s5_prebuilt_sids:
        sid = str(e.get("source_id") or "")
        if not sid:
            continue
        if sid not in new_s5_prebuilt_map or (not new_s5_prebuilt_map[sid].get("lines") and e.get("lines")):
            new_s5_prebuilt_map[sid] = {
                "source_id": sid,
                "name": e.get("name") or "",
                "lines": list(e.get("lines") or []),
            }

    existing_map: Dict[str, Dict[str, Any]] = {
        str(e.get("source_id") or ""): e
        for e in existing_source_id_list
        if e.get("source_id")
    }

    # 收集最终 wiki 里实际被引用的 source_ids
    referenced: List[str] = []
    for entry in final_wiki:
        referenced.extend(_collect_entry_node_ids(entry))
    referenced = [r for r in referenced if r]

    # 组装
    seen: set = set()
    final_list: List[Dict[str, Any]] = []
    need_neo4j: List[str] = []

    for sid in referenced:
        if sid in seen:
            continue
        if sid in new_s5_prebuilt_map:
            final_list.append(new_s5_prebuilt_map[sid])
            seen.add(sid)
        elif sid in existing_map:
            final_list.append(dict(existing_map[sid]))
            seen.add(sid)
        elif sid.isdigit():
            need_neo4j.append(sid)
        # 非数字 sid 且前两档都找不到 → 孤立条目，丢弃

    # Neo4j 兜底：对 markdown 里出现的类/方法 nodeId 解析文件路径
    if need_neo4j:
        file_info_map = await resolve_source_files(neo4j, need_neo4j)
        for sid in need_neo4j:
            info = file_info_map.get(sid)
            if not info or not info.get("file_name"):
                continue
            if sid in seen:
                continue
            final_list.append({
                "source_id": sid,
                "name": info["file_name"],
                "lines": [],
            })
            seen.add(sid)

    logger.info(
        f"[rebuild] source_id_list: {len(final_list)} 条（新 §5 prebuilt={len(new_s5_prebuilt_map)}, "
        f"既有复用={len([r for r in referenced if r in existing_map and r not in new_s5_prebuilt_map])}, "
        f"Neo4j 新解析={len(need_neo4j)}）"
    )
    return final_list


async def regenerate_section5(
    flow: Dict[str, Any],
    existing_meta: Dict[str, Any],
    neo4j,
    logger: logging.Logger,
) -> Dict[str, Any]:
    name = flow.get("name", "?")
    logger.info(f"========== 开始重新生成 §5: {name} ==========")

    # 1. 构造 scope + class_rows（与 generate.py 一致）
    scope = build_scope_from_flow(flow)
    all_class_like = (
        scope["class_ids"] + scope["interface_ids"] + scope["enum_ids"] + scope["record_ids"]
    )
    if not all_class_like:
        raise ValueError(f"{name} scope 为空，无法生成 §5")

    all_class_rows = await fetch_classes_full_context(neo4j, all_class_like)
    logger.info(f"[{name}] fetched {len(all_class_rows)} 类的 source_code/SE_What")

    # 2. 生成新 §5
    new_s5_section = await build_control_flow_section(flow, scope, all_class_rows, neo4j)

    # 3. 把新 §5 扁平化成 wiki entries + prebuilt source_id 条目
    new_s5_entries, new_s5_prebuilt_sids = _section_to_wiki_entries(new_s5_section)
    logger.info(
        f"[{name}] 新 §5: {len(new_s5_entries)} 条 wiki entries, "
        f"{len(new_s5_prebuilt_sids)} 条 prebuilt source_id"
    )

    # 4. 找到旧 §5 在 existing_meta.wiki 里的区间并替换
    existing_wiki = existing_meta.get("wiki", []) or []
    s5_start, s5_end = find_section5_range(existing_wiki)
    if s5_start == s5_end:
        logger.warning(f"[{name}] 未在既有 meta 里找到 §5 条目，将追加到末尾")
        final_wiki = list(existing_wiki) + list(new_s5_entries)
    else:
        logger.info(f"[{name}] 旧 §5 区间: [{s5_start}, {s5_end}) 共 {s5_end - s5_start} 条")
        final_wiki = list(existing_wiki[:s5_start]) + list(new_s5_entries) + list(existing_wiki[s5_end:])

    # 5. 重建 source_id_list
    existing_sid_list = existing_meta.get("source_id_list", []) or []
    final_sid_list = await rebuild_source_id_list(
        final_wiki=final_wiki,
        new_s5_prebuilt_sids=new_s5_prebuilt_sids,
        existing_source_id_list=existing_sid_list,
        neo4j=neo4j,
        logger=logger,
    )

    return {
        "wiki": final_wiki,
        "source_id_list": final_sid_list,
    }


def load_flow(flow_name: str) -> Dict[str, Any]:
    """按名字查找 flow。支持模糊匹配：如果精确匹配失败，自动尝试加回末尾「流」字。

    这样 `--flow "奖品兑换"` 能匹配到 `奖品兑换流`（与输出文件名去"流"的约定对齐）。
    """
    if not os.path.isfile(INPUT_PATH):
        raise FileNotFoundError(f"输入文件不存在: {INPUT_PATH}")
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    flows = data.get("flows") or []
    for f in flows:
        if f.get("name") == flow_name:
            return f
    # 兜底：尝试补一个"流"字再匹配
    for f in flows:
        if f.get("name") == flow_name + "流":
            return f
    raise ValueError(f"未在 business_flows_with_span.json 里找到 flow: {flow_name}")


def infer_flow_name_from_meta_path(meta_path: str) -> Optional[str]:
    """从 `XXX.meta.json` 文件名反推出 flow 名字 XXX（不含扩展名）。

    注意：文件名里 flow 末尾的「流」字已被 `flow_to_filename` 去掉，
    这里直接返回去后的短名，由 `load_flow` 兜底补回「流」字。

    兼容老格式 `业务流_XXX.meta.json`：若带老前缀，自动剥离。
    """
    basename = os.path.basename(meta_path)
    if not basename.endswith(".meta.json"):
        return None
    stem = basename[:-len(".meta.json")]
    # 兼容老前缀
    old_prefix = "业务流_"
    if stem.startswith(old_prefix):
        stem = stem[len(old_prefix):]
    return stem or None


async def main():
    parser = argparse.ArgumentParser(description="只重新生成已有 wiki meta.json 的 §5 章节")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--flow", help="业务流名字（从默认 output 目录推断 meta 路径）")
    group.add_argument("--meta", help="既有 meta.json 的路径（会自动从文件名反推 flow 名）")
    parser.add_argument("--out", help="输出路径（默认覆盖输入）")
    parser.add_argument("--backup", action="store_true", help="覆盖前先创建 .bak 备份")
    args = parser.parse_args()

    logger = setup_logger()

    if not shutil.which("claude"):
        logger.error("未找到 claude CLI")
        sys.exit(1)
    logger.info(f"使用 Claude CLI: {shutil.which('claude')}")

    # 1. 定位输入 meta + flow 名
    if args.meta:
        meta_path = os.path.abspath(args.meta)
        flow_name = infer_flow_name_from_meta_path(meta_path)
        if not flow_name:
            logger.error(f"无法从 {meta_path} 的文件名反推 flow 名（应形如 业务流_XXX.meta.json）")
            sys.exit(1)
    else:
        flow_name = args.flow
        meta_path = os.path.join(OUTPUT_DIR, flow_to_filename(flow_name))

    if not os.path.isfile(meta_path):
        logger.error(f"meta 文件不存在: {meta_path}")
        sys.exit(1)

    out_path = os.path.abspath(args.out) if args.out else meta_path
    logger.info(f"flow = {flow_name}")
    logger.info(f"输入 meta = {meta_path}")
    logger.info(f"输出     = {out_path}")

    # 2. 载入 flow 定义 + 既有 meta
    try:
        flow = load_flow(flow_name)
    except Exception as e:
        logger.error(f"{e}")
        sys.exit(1)
    with open(meta_path, "r", encoding="utf-8") as f:
        existing_meta = json.load(f)

    # 3. 连 Neo4j 并跑
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    if not await neo4j.test_connection():
        logger.error("Neo4j 连接失败")
        sys.exit(1)
    logger.info("Neo4j 连接成功")

    try:
        new_meta = await regenerate_section5(flow, existing_meta, neo4j, logger)
    finally:
        neo4j.close()

    # 4. 备份 + 写出
    if args.backup and out_path == meta_path:
        bak_path = meta_path + ".bak"
        shutil.copy2(meta_path, bak_path)
        logger.info(f"已备份原文件到 {bak_path}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(new_meta, f, ensure_ascii=False, indent=2)
    logger.info(f"[{flow_name}] 已保存 → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
