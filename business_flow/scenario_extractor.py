"""业务场景调用链抽取 + LLM 审核 + 图渲染（视角 B 的场景化版本）

思路：
- 阶段 1（程序）：从每个 Controller entry method 出发 BFS CALLS 边 ≤ max_depth 跳，
  按 class_ownership 把被调用方法归到各 flow，收集跨 flow 的 fan-out hops；
  保守去重（只合并 involved_flows 完全相同的链路，保留 hops 最多的那条）
- 阶段 2（LLM）：每条候选链独立调一次 LLM，判定是否保留 + 起业务名 + 给出**结构化修改指令**
  （标记冗余 hops / 补全缺失 hops）
- 阶段 3（渲染）：按 LLM 的 modifications 真正**删除/添加** hops，再画 sequenceDiagram

用法:
    python business_flow/scenario_extractor.py
    python business_flow/scenario_extractor.py --max-depth 3  # 查更深的调用链
    python business_flow/scenario_extractor.py --no-llm        # 跳过审核阶段（调试用）
    python business_flow/scenario_extractor.py --top 20        # 只渲染 top N 条场景
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from interfaces.neo4j_interface import Neo4jInterface
from interfaces.llm_interface import LLMInterface
from business_flow.llm_client import set_default_llm, invoke_llm_strict
from business_flow.overview_generator import (
    BF_DIR, INPUT_PATH, LOG_DIR,
    load_flows, filter_generated_flows, extract_flow_facts,
    build_primary_class_ownership,
)


def setup_logger() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"scenarios_{ts}.log")
    logger = logging.getLogger("business_flow.scenarios")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    logger.info(f"日志文件: {log_file}")
    return logger


# ============================================================
# 阶段 1：BFS 抽取跨 flow 调用链
# ============================================================

async def bfs_cross_flow_hops(
    neo4j,
    entry_method_id: int,
    entry_method_name: str,
    class_ownership: Dict[str, str],
    entry_flow: str,
    max_depth: int,
    max_steps: int,
) -> List[Dict[str, Any]]:
    """带 parent 追踪的 BFS：返回**真实链式**的跨 flow 调用 steps。

    每次 CALLS 边记录 (caller_flow, caller_method) → (called_flow, called_method)。
    只有当 caller_flow 和 called_flow 不同时才记为 "跨流 step"；否则该方法仍用于继续深入搜索。

    去重：(src_flow, dst_flow, dst_method) 只保留首次出现，避免同一链路被多次记录。
    """
    # method_id → {flow, method_name}（flow 是该方法所属类的 primary owner，
    # 若为公共类则继承 caller 的 flow 以避免链路中断）
    method_meta: Dict[int, Dict[str, str]] = {
        entry_method_id: {"flow": entry_flow, "method_name": entry_method_name},
    }
    visited_methods: Set[int] = {entry_method_id}
    frontier: List[int] = [entry_method_id]
    steps: List[Dict[str, Any]] = []
    seen_keys: Set[Tuple[str, str, str]] = set()

    for depth in range(1, max_depth + 1):
        if not frontier or len(steps) >= max_steps:
            break
        query = """
        MATCH (m:Method) WHERE m.nodeId IN $ids
        MATCH (m)-[:CALLS]->(called:Method)
        OPTIONAL MATCH (c)-[:DECLARES]->(called)
        WHERE c:Class OR c:Interface
        RETURN m.nodeId AS caller_id,
               called.nodeId AS called_id,
               called.name AS called_method,
               c.nodeId AS called_class_id,
               c.name AS called_class
        """
        rows = await neo4j.execute_query(query, {"ids": frontier})
        next_frontier: List[int] = []
        for r in rows:
            called_id = r.get("called_id")
            if called_id is None or called_id in visited_methods:
                continue
            caller_id = r.get("caller_id")
            caller_meta = method_meta.get(caller_id)
            if not caller_meta:
                continue
            visited_methods.add(called_id)

            src_flow = caller_meta["flow"]
            src_method = caller_meta["method_name"]
            cid = r.get("called_class_id")
            dst_flow_strict = class_ownership.get(str(cid)) if cid else None
            # 公共类（dst_flow_strict=None）继承 src_flow 以不中断链路，
            # 这样继续往下的调用仍能被追踪
            effective_flow = dst_flow_strict or src_flow
            called_method = r.get("called_method") or ""

            # 记录 called 方法的 meta（用于下一层追踪）
            method_meta[called_id] = {
                "flow": effective_flow,
                "method_name": called_method,
            }
            next_frontier.append(called_id)

            # 只在发生"真实跨流"时记录 step
            if not dst_flow_strict or dst_flow_strict == src_flow:
                continue
            key = (src_flow, dst_flow_strict, called_method)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            steps.append({
                "src_flow": src_flow,
                "src_method": src_method,
                "dst_flow": dst_flow_strict,
                "dst_method": called_method,
                "dst_class": r.get("called_class") or "",
                "depth": depth,
            })
            if len(steps) >= max_steps:
                break

        frontier = next_frontier
    return steps


async def extract_all_chains(
    neo4j,
    flow_facts: List[Dict],
    class_ownership: Dict[str, str],
    max_depth: int,
    max_steps: int,
    logger: logging.Logger,
) -> List[Dict[str, Any]]:
    """对每个 flow 的每个 entry method 做 BFS，抽候选链路。"""
    chains: List[Dict[str, Any]] = []
    for f in flow_facts:
        for em in f["raw_entry_methods"]:
            nid = em.get("node_id")
            if nid is None:
                continue
            entry_method_full = f"{em.get('class', '')}.{em.get('method', '')}"
            hops = await bfs_cross_flow_hops(
                neo4j,
                entry_method_id=int(nid),
                entry_method_name=entry_method_full,
                class_ownership=class_ownership,
                entry_flow=f["name"],
                max_depth=max_depth,
                max_steps=max_steps,
            )
            # involved_flows 包含所有出现在链路里的 src + dst
            involved: Set[str] = {f["name"]}
            for h in hops:
                involved.add(h["src_flow"])
                involved.add(h["dst_flow"])
            if len(involved) < 2:
                continue
            chains.append({
                "entry_flow": f["name"],
                "entry_class": em.get("class", ""),
                "entry_method": em.get("method", ""),
                "entry_method_id": nid,
                "hops": hops,
                "involved_flows": sorted(involved),
            })
    logger.info(f"阶段 1 抽取候选链路 {len(chains)} 条")
    return chains


def filter_and_dedupe_chains(chains: List[Dict]) -> List[Dict]:
    """保守去重：按 (entry_flow, involved_flows) 组合合并，保留 hops 最多的那条。

    不跨 entry_flow 合并（不同入口代表不同业务场景，即使涉及 flow 集合相同）。
    """
    by_key: Dict[Tuple[str, frozenset], Dict] = {}
    for c in chains:
        key = (c["entry_flow"], frozenset(c["involved_flows"]))
        cur = by_key.get(key)
        if not cur or len(c["hops"]) > len(cur["hops"]):
            by_key[key] = c
    return list(by_key.values())


# ============================================================
# 阶段 2：LLM 审核（结构化输出 modifications）
# ============================================================

CHAIN_REVIEW_SYSTEM = """你是业务流程审阅专家。任务：审阅一条**自动抽取的跨业务流调用链**，输出严格 JSON。

## 输入
- 入口方法：`EntryClass.entryMethod`（某 Controller 的 HTTP 入口）
- 入口所属业务流：entry_flow
- 该入口触发的**跨 flow 调用列表**（hops）：每条 `src_flow → dst_flow : methodName`
- 各涉及业务流的简短描述

## 判定任务
1. **keep**：判断这条链路是否代表一个**有业务意义的场景**
   - 有意义：用户/运营触发的完整业务动作，跨多个 flow 协作
   - 无意义：静态抽取的噪声（工具类/日志/框架回调碰巧跨类）、单纯的数据读取不涉及业务流转
2. **scenario_name**：3-10 字业务场景名，**从业务视角**起（如"用户兑换奖品"），禁止用类名方法名
3. **description**：30-60 字场景业务含义（谁在什么时候触发、做了什么）
4. **modifications**：结构化修改指令，对 hops 做**冗余删除**和**缺失补全**

## modifications 字段规范

### remove_hops（冗余删除）
某 hop 是纯技术性/工具性调用，不反映业务意图 → 标记删除

示例：
```
{"index": 2, "reason": "`getParentId` 是通用树形工具调用，不是业务流协作"}
```

### add_hops（缺失补全）
根据 scenario_name 和 entry_method 的业务语义，**明显应该存在但静态抽取未捕获**的跨 flow 调用 → 补上

常见场景：MQ 异步调用 / Spring 事件 / 反射 / 子线程提交 静态 CALLS 边抓不到

示例：
```
{
  "after_index": 0,
  "src_flow": "奖品兑换流",
  "src_method": "addOrderByPrizeId",
  "dst_flow": "站内消息流",
  "method_name": "sendMessage",
  "reason": "兑换成功后业务规则要求发推送（疑似 MQ 异步，静态抓不到）"
}
```

**字段规范**：
- `after_index`：插在原 hops 数组第几个之后（-1 = 插到最前）
- `src_method` **必填**：发起该补充调用的方法名（必须是链路里已出现的方法，通常是 `entry_method` 或某 hop 的 `dst_method`）
- `dst_flow` / `method_name`：目标 flow 和目标方法名

### 节制原则
- remove_hops：只标记明显无业务意义的；犹豫时保留
- add_hops：只在 **high confidence** 时补（你能说出具体业务理由）；不确定就不加
- 每项 **reason 必填**，说清楚依据

## 输出格式（严格 JSON，无围栏，无前言）
{
  "keep": true,
  "scenario_name": "用户兑换奖品",
  "description": "用户在 App 选择奖品下单，系统扣减积分并创建兑换订单，兑换成功后推送站内消息通知用户",
  "modifications": {
    "remove_hops": [
      {"index": 2, "reason": "..."}
    ],
    "add_hops": [
      {"after_index": 0, "src_flow": "...", "dst_flow": "...",
       "method_name": "...", "reason": "..."}
    ]
  },
  "review_notes": "对场景/修改的简短补充说明，≤ 50 字（可空串）"
}

## 如果 keep=false
无需填 scenario_name / description / modifications，可以全部空值。
输出仍为严格 JSON。
"""


def build_chain_review_user_prompt(
    chain: Dict, flow_descriptions: Dict[str, str],
) -> str:
    lines: List[str] = []
    lines.append(f"## 入口方法")
    lines.append(f"- 业务流：`{chain['entry_flow']}`")
    lines.append(f"- 入口类/方法：`{chain['entry_class']}.{chain['entry_method']}`")
    lines.append("")
    lines.append(f"## 静态抽取的跨 flow 调用链 ({len(chain['hops'])} 条 hop，按调用顺序)")
    lines.append("")
    lines.append("每条 hop 的格式：`<调用方 flow>.<调用方法>` → `<被调方 flow>.<被调方法>`  (深度)")
    lines.append("")
    for i, h in enumerate(chain["hops"]):
        src_m = h.get("src_method") or "?"
        lines.append(
            f"- **hop[{i}]** (d={h['depth']}): "
            f"`{h['src_flow']}.{src_m}` → `{h['dst_flow']}.{h['dst_method']}`"
        )
    lines.append("")
    lines.append(f"## 涉及业务流描述")
    for fn in chain["involved_flows"]:
        desc = flow_descriptions.get(fn, "（无描述）")
        lines.append(f"- `{fn}`: {desc}")
    lines.append("")
    lines.append("请严格输出 JSON。")
    return "\n".join(lines)


async def review_chain(
    chain: Dict,
    flow_descriptions: Dict[str, str],
    logger: logging.Logger,
) -> Optional[Dict]:
    """对一条链路调 LLM，返回 review 结构体。失败时返回 None。"""
    label = f"scenario-{chain['entry_flow']}-{chain['entry_method']}"
    try:
        result, _ = await invoke_llm_strict(
            system_prompt=CHAIN_REVIEW_SYSTEM,
            user_prompt=build_chain_review_user_prompt(chain, flow_descriptions),
            required_keys=["keep"],
            label=label,
        )
    except Exception as e:
        logger.warning(f"[{label}] LLM 审核失败: {type(e).__name__}: {e}")
        return None
    return result


# ============================================================
# 阶段 3：应用 LLM 的 modifications + 渲染 sequenceDiagram
# ============================================================

def apply_modifications(
    hops: List[Dict], modifications: Dict,
) -> Tuple[List[Dict], List[str]]:
    """按 LLM 指令修改 hops，返回 (新 hops, 修改说明文字列表)。

    处理顺序：先删除（倒序处理避免索引偏移），再插入（按 after_index 升序处理）。
    synthetic=True 标记 LLM 新增的 hop，用于渲染时加视觉区分。
    """
    notes: List[str] = []
    new_hops = [dict(h) for h in hops]  # 深拷贝

    remove_items = sorted(
        modifications.get("remove_hops") or [],
        key=lambda x: -int(x.get("index", -1)),
    )
    for item in remove_items:
        idx = int(item.get("index", -1))
        if 0 <= idx < len(new_hops):
            removed = new_hops.pop(idx)
            notes.append(
                f"🗑 删除 `{removed['dst_flow']}.{removed['dst_method']}` — "
                f"{item.get('reason', '')}"
            )

    add_items = sorted(
        modifications.get("add_hops") or [],
        key=lambda x: int(x.get("after_index", -1)),
    )
    # 逆序处理：插入时靠 after_index 从高到低，避免插入位置互相影响
    for item in sorted(add_items, key=lambda x: -int(x.get("after_index", -1))):
        after = int(item.get("after_index", -1))
        # src_method 优先用 LLM 提供的；否则从上下文推断：
        # - after_index >= 0: 承接 hops[after] 的 dst_method（即插入点之前一跳的目标方法）
        # - after_index == -1: 插到最开头，src_method 从入口推断（留空由渲染兜底）
        src_method_hint = item.get("src_method") or item.get("src_method_name") or ""
        if not src_method_hint and after >= 0 and after < len(hops):
            src_method_hint = hops[after].get("dst_method", "")
        new_hop = {
            "src_flow": item.get("src_flow", ""),
            "src_method": src_method_hint,
            "dst_flow": item.get("dst_flow", ""),
            "dst_method": item.get("method_name", ""),
            "dst_class": "",
            "depth": 1,
            "synthetic": True,
        }
        insert_at = max(0, min(after + 1, len(new_hops)))
        new_hops.insert(insert_at, new_hop)
        notes.append(
            f"➕ 补充 `{new_hop['src_flow']} → {new_hop['dst_flow']}.{new_hop['dst_method']}` — "
            f"{item.get('reason', '')}"
        )

    return new_hops, notes


_NODE_ID_RE = re.compile(r"[^\w]")


def _safe_participant_id(name: str, id_map: Dict[str, str]) -> str:
    """mermaid sequenceDiagram 的 participant id 必须是标识符；给中文 flow 名建 F0/F1 映射"""
    if name in id_map:
        return id_map[name]
    pid = f"F{len(id_map)}"
    id_map[name] = pid
    return pid


def render_chain_as_flowchart(
    chain: Dict,
    review: Optional[Dict],
    applied_hops: List[Dict],
) -> str:
    """画 flowchart LR：每个 flow 一个 subgraph，方法为节点，边是调用关系。

    与 sequenceDiagram 相比更紧凑：
    - 同 flow 内多次出现的方法合并为同一节点（key = (flow, method_name)）
    - fan-out 的并行分支用箭头分叉，视觉上一目了然
    - synthetic（LLM 补充的跳）用虚线 `-.->` 区分
    """
    lines: List[str] = ["flowchart LR"]

    # 收集 (flow, method) → node_id；同时按 flow 分组
    method_to_node: Dict[Tuple[str, str], str] = {}
    flow_methods: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    def get_or_create(flow: str, method: str) -> str:
        key = (flow, method)
        if key not in method_to_node:
            nid = f"M{len(method_to_node)}"
            method_to_node[key] = nid
            flow_methods[flow].append((nid, method))
        return method_to_node[key]

    # 先注册入口方法自身（在它所属 flow 的 subgraph 内）
    entry_nid = get_or_create(chain["entry_flow"], chain["entry_method"])
    entry_method_name = chain["entry_method"]
    entry_flow_name = chain["entry_flow"]
    for h in applied_hops:
        # src_method 可能因 LLM 新增 hop 未提供而为空，兜底回入口方法
        sm = h.get("src_method") or entry_method_name
        sf = h.get("src_flow") or entry_flow_name
        get_or_create(sf, sm)
        # 渲染时直接用这个兜底值
        h["_render_src_flow"] = sf
        h["_render_src_method"] = sm
        get_or_create(h["dst_flow"], h["dst_method"])

    # Start 节点（外部触发方）
    entry_label = f'{chain["entry_class"]}.{chain["entry_method"]}'
    lines.append(f'    Start(["{entry_label}"])')

    # 每个 flow 一个 subgraph
    flow_ids: Dict[str, str] = {}
    for flow, items in flow_methods.items():
        fid = f"F{len(flow_ids)}"
        flow_ids[flow] = fid
        # mermaid subgraph 语法：subgraph ID [Label]
        lines.append(f'    subgraph {fid} ["{flow}"]')
        for nid, method in items:
            lines.append(f'        {nid}["{method}"]')
        lines.append("    end")

    # 找"根节点"：作为 src 出现但没有任何 hop 指向它的节点（链路起点）
    src_nids: Set[str] = {
        method_to_node[(h["_render_src_flow"], h["_render_src_method"])]
        for h in applied_hops
    }
    dst_nids: Set[str] = {
        method_to_node[(h["dst_flow"], h["dst_method"])] for h in applied_hops
    }
    roots = (src_nids - dst_nids)
    roots.add(entry_nid)  # entry 本身永远作为一个根

    # Start → 每个根节点
    for root in sorted(roots):
        lines.append(f"    Start --> {root}")

    # 画每条 hop
    for h in applied_hops:
        src_nid = method_to_node[(h["_render_src_flow"], h["_render_src_method"])]
        dst_nid = method_to_node[(h["dst_flow"], h["dst_method"])]
        if h.get("synthetic"):
            lines.append(f'    {src_nid} -.->|"[补]"| {dst_nid}')
        else:
            lines.append(f"    {src_nid} --> {dst_nid}")

    return "\n".join(lines)


def render_chain_as_sequence(
    chain: Dict,
    review: Optional[Dict],
    applied_hops: List[Dict],
) -> str:
    """画 sequenceDiagram。synthetic hop 用虚线 -) 表示（表示异步/补充）。"""
    id_map: Dict[str, str] = {}
    entry_flow_name = chain["entry_flow"]
    # 所有参与方（入口 flow + hop 目标 flow + 补充跳的 src 也可能新增）
    all_flows: List[str] = [entry_flow_name]
    for h in applied_hops:
        sf = h.get("src_flow") or entry_flow_name
        if sf not in all_flows:
            all_flows.append(sf)
        if h["dst_flow"] not in all_flows:
            all_flows.append(h["dst_flow"])

    lines = ["sequenceDiagram"]
    lines.append("    participant U as 触发方")
    for f in all_flows:
        lines.append(f'    participant {_safe_participant_id(f, id_map)} as {f}')

    # 入口触发
    entry_pid = _safe_participant_id(chain["entry_flow"], id_map)
    lines.append(f'    U ->> {entry_pid}: {chain["entry_class"]}.{chain["entry_method"]}')

    # 每条 hop
    for h in applied_hops:
        sf = h.get("src_flow") or entry_flow_name
        src_pid = _safe_participant_id(sf, id_map)
        dst_pid = _safe_participant_id(h["dst_flow"], id_map)
        arrow = "-)" if h.get("synthetic") else "->>"
        tag = " [补] " if h.get("synthetic") else " "
        lines.append(f"    {src_pid} {arrow} {dst_pid}:{tag}{h['dst_method']}")

    return "\n".join(lines)


# ============================================================
# 组装 meta.json
# ============================================================

def assemble_scenarios_meta(
    reviewed: List[Tuple[Dict, Optional[Dict], List[Dict], List[str]]],
    total_candidates: int,
    render_fn=None,
) -> Dict:
    """reviewed: [(chain, review, applied_hops, notes)]

    render_fn: 渲染函数，接 (chain, review, applied_hops) → mermaid 源码字符串。
        默认用 flowchart；传 render_chain_as_sequence 可切回时序图。
    """
    render_fn = render_fn or render_chain_as_flowchart
    wiki: List[Dict] = []
    kept = [r for r in reviewed if r[1] and r[1].get("keep")]

    intro = (
        f"## 业务场景调用链总览\n\n"
        f"本章以**业务场景**为维度展示跨 flow 调用链：每张图对应一次由 Controller 入口触发、"
        f"跨多个业务流协作完成的业务动作。\n\n"
        f"**生成流程**：\n"
        f"1. 程序从 Neo4j 的 `CALLS` 图抽取所有跨 flow 调用候选（{total_candidates} 条）\n"
        f"2. LLM 审核每条，剔除噪声、去重相似链路、补全静态抽不到的异步/事件调用\n"
        f"3. 对每个保留场景画一张 `sequenceDiagram`\n\n"
        f"最终保留 **{len(kept)}** 个业务场景。\n\n"
        f"**图例约定**：实线 `->>` 为静态可追的调用；"
        f"虚线 `-)` 标 `[补]` 为 LLM 补充的疑似异步/事件调用。"
    )
    wiki.append({"markdown": intro, "neo4j_id": {}})

    for idx, (chain, review, applied_hops, notes) in enumerate(kept, start=1):
        if not review:
            continue
        scenario_name = review.get("scenario_name", "").strip() or f"场景 {idx}"
        desc = review.get("description", "").strip() or ""
        entry_method = f"{chain['entry_class']}.{chain['entry_method']}"
        flows_list = "、".join(f"`{f}`" for f in chain["involved_flows"])

        header_md = (
            f"### 场景 {idx}：{scenario_name}\n\n"
            f"**入口**：`{entry_method}`  "
            f"**涉及业务流**：{flows_list}\n\n"
            f"{desc}"
        )
        wiki.append({"markdown": header_md, "neo4j_id": {}})

        mermaid_src = render_fn(chain, review, applied_hops)
        wiki.append({
            "mermaid": f"```mermaid\n{mermaid_src}\n```",
            "mapping": {},
        })

        if notes or review.get("review_notes"):
            parts = ["#### 审核备注", ""]
            if notes:
                parts.extend(notes)
                parts.append("")
            rn = (review.get("review_notes") or "").strip()
            if rn:
                parts.append(f"**其它**：{rn}")
            wiki.append({"markdown": "\n".join(parts), "neo4j_id": {}})

    return {"wiki": wiki, "source_id_list": []}


# ============================================================
# 主流程
# ============================================================

def _extract_flow_facts_with_entries(flow: Dict) -> Dict:
    """在 overview_generator.extract_flow_facts 基础上，多带 raw_entry_methods 便于后续 BFS。"""
    base = extract_flow_facts(flow)
    base["raw_entry_methods"] = flow.get("entry_methods", []) or []
    return base


async def main():
    parser = argparse.ArgumentParser(description="业务场景调用链抽取 + LLM 审核")
    parser.add_argument("--max-depth", type=int, default=3,
                        help="BFS 最大深度（默认 3，覆盖 Controller→Service→SubService 的 3 层链路）")
    parser.add_argument("--max-steps", type=int, default=15,
                        help="单条链路最多保留几个跨流 step（默认 15，避免链路爆炸）")
    parser.add_argument("--max-shared", type=int, default=3,
                        help="类归属共享阈值（默认 3）")
    parser.add_argument("--no-llm", action="store_true",
                        help="跳过阶段 2 LLM 审核，直接渲染原始链（调试用）")
    parser.add_argument("--format", choices=["flowchart", "seq"], default="flowchart",
                        help="图格式：flowchart（默认，按 flow 分 subgraph 更紧凑）"
                             "或 seq（sequenceDiagram，时序视角）")
    parser.add_argument("--top", type=int, default=50,
                        help="LLM 审核前最多保留几条候选（默认 50，足以覆盖全部）")
    parser.add_argument("--concurrency", type=int, default=5,
                        help="LLM 审核的并发数（默认 5）")
    parser.add_argument("--out", default=None, help="输出路径")
    args = parser.parse_args()

    logger = setup_logger()

    # 加载数据
    all_flows = load_flows()
    flows = filter_generated_flows(all_flows, logger)
    if not flows:
        logger.error("无已生成 meta 的 flow，退出")
        sys.exit(1)

    flow_facts = [_extract_flow_facts_with_entries(f) for f in flows]
    flow_descriptions = {
        f["name"]: (f.get("description") or "").strip()[:200]
        for f in flows
    }
    ownership = build_primary_class_ownership(flow_facts, args.max_shared, logger)

    # Neo4j 连
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    if not await neo4j.test_connection():
        logger.error("Neo4j 连接失败")
        sys.exit(1)
    logger.info("Neo4j 连接成功")

    # 阶段 1
    try:
        raw_chains = await extract_all_chains(
            neo4j, flow_facts, ownership, args.max_depth, args.max_steps, logger,
        )
    finally:
        neo4j.close()
    chains = filter_and_dedupe_chains(raw_chains)
    logger.info(f"阶段 1 保守去重后: {len(chains)} 条")
    if not chains:
        logger.warning("没有候选链路，退出")
        sys.exit(0)

    # 截断到 top N（按 hops 数降序）
    chains.sort(key=lambda c: -len(c["hops"]))
    chains = chains[:args.top]
    logger.info(f"截断到 top {len(chains)}")

    # 阶段 2：LLM 审核
    reviewed: List[Tuple[Dict, Optional[Dict], List[Dict], List[str]]] = []
    if args.no_llm:
        logger.info("--no-llm 模式：跳过 LLM 审核，所有链路按原始结构渲染")
        for c in chains:
            reviewed.append((c, {
                "keep": True,
                "scenario_name": f"{c['entry_flow']} · {c['entry_method']}",
                "description": "（未经 LLM 审核）",
                "modifications": {"remove_hops": [], "add_hops": []},
                "review_notes": "",
            }, list(c["hops"]), []))
    else:
        llm = LLMInterface()
        set_default_llm(llm)
        logger.info(
            f"使用 LLM: provider={llm.provider} "
            f"model={llm.model_kwargs.get('model_name') or llm.model_kwargs.get('model')}"
        )
        sem = asyncio.Semaphore(args.concurrency)

        async def _review_one(c: Dict) -> Tuple[Dict, Optional[Dict], List[Dict], List[str]]:
            async with sem:
                review = await review_chain(c, flow_descriptions, logger)
            if not review:
                return (c, None, list(c["hops"]), [])
            mods = review.get("modifications") or {}
            applied, notes = apply_modifications(c["hops"], mods)
            return (c, review, applied, notes)

        logger.info(f"并发 {args.concurrency} 跑 LLM 审核 {len(chains)} 条链路...")
        results = await asyncio.gather(*[_review_one(c) for c in chains])
        reviewed = list(results)
        kept_count = sum(1 for r in reviewed if r[1] and r[1].get("keep"))
        logger.info(f"LLM 审核完成：{kept_count}/{len(reviewed)} 条保留")

    # 阶段 3 + 输出
    render_fn = (
        render_chain_as_flowchart if args.format == "flowchart"
        else render_chain_as_sequence
    )
    meta = assemble_scenarios_meta(
        reviewed, total_candidates=len(chains), render_fn=render_fn,
    )
    out_path = args.out or os.path.join(
        BF_DIR, "output_flow", "_scenarios.meta.json",
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存 → {out_path}")

    # 终端打印保留场景数
    kept = [r for r in reviewed if r[1] and r[1].get("keep")]
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"保留 {len(kept)} 个业务场景：")
    for i, (chain, review, _, _) in enumerate(kept, 1):
        name = review.get("scenario_name", "").strip() if review else ""
        entry = f"{chain['entry_class']}.{chain['entry_method']}"
        print(f"  {i}. [{name}] {entry}  涉及: {' → '.join(chain['involved_flows'])}")


if __name__ == "__main__":
    asyncio.run(main())
