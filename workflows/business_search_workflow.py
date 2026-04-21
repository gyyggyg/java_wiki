"""
业务流抽取工作流

通过本地 Claude CLI 扫描 SOURCE_ROOT_PATH 源码，识别业务流，
用 neo4j_mcp 验证入口方法真实性并取回 nodeId，
最终产出 output/business_flows.json。
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from typing_extensions import TypedDict

from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from graph.business_search_agent import run_business_search_agent

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ====================== 日志配置 ======================
_log_dir = os.path.join(PROJECT_ROOT, "internal_result")
os.makedirs(_log_dir, exist_ok=True)
_log_path = os.path.join(_log_dir, f"business_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logger = logging.getLogger("business_search")
logger.setLevel(logging.DEBUG)
_fh = logging.FileHandler(_log_path, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
logger.addHandler(_fh)
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(_ch)
logger.propagate = False


# ====================== 状态定义 ======================
class BizFlowState(TypedDict, total=False):
    source_root: str
    extra_hint: str
    flows_result: Dict
    output_path: str


# ====================== 工作流 ======================
def business_search_workflow(source_root: str, extra_hint: str = ""):
    mcp_config = os.path.join(PROJECT_ROOT, "mcp_config.json")
    timeout = int(os.environ.get("BUSINESS_AGENT_TIMEOUT", "1800"))

    async def extract_flows(state: BizFlowState) -> BizFlowState:
        sr = state.get("source_root") or source_root
        hint = state.get("extra_hint") or extra_hint
        if not sr or not os.path.isdir(sr):
            raise RuntimeError(f"source_root 无效: {sr}")
        logger.info("=" * 60)
        logger.info(f"[节点] extract_flows 启动")
        logger.info(f"  源码根目录: {sr}")
        logger.info(f"  超时设置  : {timeout}s")
        logger.info(f"  MCP 配置  : {mcp_config} (exists={os.path.isfile(mcp_config)})")
        if hint:
            logger.info(f"  额外提示  : {hint}")
        logger.info("=" * 60)
        t0 = datetime.now()
        result = await run_business_search_agent(
            source_root=sr,
            timeout=timeout,
            mcp_config=mcp_config,
            extra_hint=hint,
        )
        elapsed = (datetime.now() - t0).total_seconds()
        flows = result.get("flows", []) if isinstance(result, dict) else []
        logger.info("=" * 60)
        logger.info(f"[节点] extract_flows 完成: 共 {len(flows)} 个业务流, 耗时 {elapsed:.1f}s")
        logger.info("=" * 60)
        return {"flows_result": result}

    async def save_output(state: BizFlowState) -> BizFlowState:
        result = state.get("flows_result") or {"flows": []}
        flows = result.get("flows", []) if isinstance(result, dict) else []

        # 业务流分类摘要
        by_kind: Dict[str, int] = {}
        verified_count = 0
        unverified_count = 0
        for f in flows:
            by_kind[f.get("kind", "未知")] = by_kind.get(f.get("kind", "未知"), 0) + 1
            for em in f.get("entry_methods", []):
                if em.get("node_id"):
                    verified_count += 1
                else:
                    unverified_count += 1

        logger.info(f"[节点] save_output: 写入 {len(flows)} 个业务流")
        logger.info(f"  按 kind 分布: {by_kind}")
        logger.info(f"  入口方法: 已验证 {verified_count} / 未验证 {unverified_count}")
        logger.info("  ---- 业务流清单 ----")
        for i, f in enumerate(flows, 1):
            ems = f.get("entry_methods", [])
            sample = ", ".join(
                f"{em.get('class','?')}.{em.get('method','?')}"
                for em in ems[:3]
            )
            more = f" (+{len(ems)-3}个)" if len(ems) > 3 else ""
            logger.info(f"  {i:02d}. [{f.get('kind','?')}] {f.get('name','?')} "
                        f"— {len(ems)} 入口: {sample}{more}")
            if f.get("description"):
                logger.info(f"      说明: {f.get('description')}")

        out_dir = os.path.join(PROJECT_ROOT, "output")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "business_flows.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"[节点] save_output 完成 → {out_path}")
        return {"output_path": out_path}

    graph = StateGraph(BizFlowState)
    graph.add_node("extract_flows", extract_flows)
    graph.add_node("save_output", save_output)
    graph.set_entry_point("extract_flows")
    graph.add_edge("extract_flows", "save_output")
    graph.add_edge("save_output", END)
    return graph.compile(checkpointer=MemorySaver())


# ====================== 独立运行入口 ======================
async def main():
    load_dotenv()
    print("=== 独立运行业务流抽取工作流 ===")

    source_root = os.environ.get("SOURCE_ROOT_PATH", "").strip()
    if not source_root or not os.path.isdir(source_root):
        print(f"[ERR] SOURCE_ROOT_PATH 无效: {source_root}")
        return

    print(f"[INFO] SOURCE_ROOT_PATH: {source_root}")
    print(f"[INFO] 日志文件: {_log_path}")

    app = business_search_workflow(source_root=source_root)
    result = await app.ainvoke(
        {"source_root": source_root},
        config={"configurable": {"thread_id": "business-flow-extract"}},
    )

    flows = result.get("flows_result", {}).get("flows", [])
    print(f"[INFO] 抽取完成，共 {len(flows)} 个业务流")
    print(f"[INFO] 输出文件: {result.get('output_path')}")


if __name__ == "__main__":
    asyncio.run(main())
