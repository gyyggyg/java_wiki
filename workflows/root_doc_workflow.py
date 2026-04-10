import os
import sys
import json
import re
import uuid
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from interfaces.data_master import get_file
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from chains.common_chains import ChainFactory
from chains.prompts.root_doc_prompt import PROJECT_INTRO_PROMPT, MODULE_ARCHITECTURE_PROMPT
from graph.module_target import module_app
from graph.root_doc_agent import (
    ROOT_CANDIDATE_SECTIONS,
    run_discover_agent,
    run_root_section_agent,
)
from interfaces.simple_validate_mermaid import SimpleMermaidValidator

# 项目根目录（java_wiki）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ====================== 日志配置 ======================
_log_dir = os.path.join(PROJECT_ROOT, "internal_result")
os.makedirs(_log_dir, exist_ok=True)
_log_path = os.path.join(_log_dir, f"root_doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logger = logging.getLogger("root_doc")
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

_mermaid_validator = SimpleMermaidValidator()

# ====================== 1. 状态定义 ======================
class RootDocState(TypedDict, total=False):
    # 模块信息
    modules_info: List[Dict]
    # neo4j全局统计文本（供discover和generate使用）
    neo4j_stats_text: str
    modules_info_text: str
    # 基础章节（OpenAI/LangChain生成）
    section1_intro: Dict
    section2_architecture: Dict
    section3_diagram: Dict
    # 扩展章节（Claude CLI生成）
    discovered_sections: List[Dict]    # discover阶段选中的章节规划
    extra_sections: List[Dict]         # generate阶段生成的章节内容
    # 最终输出
    final_output: Dict
    high_blocks: List

# ====================== 2. 工作流定义 ======================
def root_doc_workflow(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface,
                      source_root: str = ""):
    """
    构建Root文档生成工作流。

    完整流程：
      fetch_modules → generate_intro → generate_architecture → generate_diagram
                                                                    ↓
                                                            discover_sections
                                                                    ↓
                                                            generate_extra
                                                                    ↓
                                                                  merge

    Args:
        llm_interface: LLM接口（用于基础章节1-3）
        neo4j_interface: Neo4j接口
        source_root: Java源码根目录路径（用于Claude CLI搜索源码生成扩展章节4+）
    """
    intro_chain = ChainFactory.create_generic_chain(llm_interface, PROJECT_INTRO_PROMPT)
    architecture_chain = ChainFactory.create_generic_chain(llm_interface, MODULE_ARCHITECTURE_PROMPT)

    async def fetch_root_modules(state: RootDocState) -> RootDocState:
        """
        查询root Block的直接子Block信息
        """
        query = """
        MATCH (root:Block {name: 'root'})-[:f2c]->(child:Block)
        RETURN child.nodeId AS nodeId,
               child.name AS name,
               child.module_explaination AS module_explaination
        ORDER BY child.name
        """
        high_blocks = []
        result = await neo4j_interface.execute_query(query)

        modules_info = []
        new_names = json.loads(get_file(os.path.join(PROJECT_ROOT, "graph", "block_new_names.json")))

        for record in result:
            modules_info.append({
                "nodeId": record['nodeId'],
                "name": new_names.get(str(record['nodeId'])),
                "path": record['name'],
                "module_explaination": record['module_explaination'] or "暂无说明"
            })
            high_blocks.append(record['nodeId'])

        # 构建模块信息文本（供discover/generate使用）
        modules_info_text = "\n".join(
            f"- {m['name']}: {m['module_explaination']}" for m in modules_info
        )

        # 查询neo4j全局统计
        stats_query = """
        MATCH (n)
        WITH labels(n)[0] AS label, count(n) AS cnt
        RETURN label, cnt
        ORDER BY cnt DESC
        """
        stats_result = await neo4j_interface.execute_query(stats_query)
        stats_lines = ["节点类型统计:"]
        for r in stats_result:
            stats_lines.append(f"  - {r['label']}: {r['cnt']} 个")

        # 查询顶层Package
        pkg_query = """
        MATCH (p:Package)
        RETURN p.name AS name
        ORDER BY p.name
        LIMIT 30
        """
        pkg_result = await neo4j_interface.execute_query(pkg_query)
        if pkg_result:
            stats_lines.append("\n主要包(Package):")
            for r in pkg_result:
                stats_lines.append(f"  - {r['name']}")

        # 查询使用的Annotation类型
        anno_query = """
        MATCH (a:Annotation)
        RETURN DISTINCT a.name AS name
        ORDER BY a.name
        LIMIT 30
        """
        anno_result = await neo4j_interface.execute_query(anno_query)
        if anno_result:
            stats_lines.append("\n注解(Annotation)类型:")
            for r in anno_result:
                stats_lines.append(f"  - {r['name']}")

        # 查询被引用最多的Class（高入度）
        popular_query = """
        MATCH (c:Class)<-[r]-()
        WITH c, count(r) AS in_degree
        ORDER BY in_degree DESC
        LIMIT 15
        RETURN c.name AS name, in_degree
        """
        popular_result = await neo4j_interface.execute_query(popular_query)
        if popular_result:
            stats_lines.append("\n被引用最多的类(Top 15):")
            for r in popular_result:
                stats_lines.append(f"  - {r['name']} (被引用 {r['in_degree']} 次)")

        neo4j_stats_text = "\n".join(stats_lines)

        logger.info(f"获取到 {len(modules_info)} 个一级模块")
        return {
            "modules_info": modules_info,
            "high_blocks": high_blocks,
            "modules_info_text": modules_info_text,
            "neo4j_stats_text": neo4j_stats_text,
        }

    async def generate_intro(state: RootDocState) -> RootDocState:
        """
        章节1：项目介绍
        输入：modules_info（一级模块名称+功能说明）
        引擎：OpenAI LangChain（PROJECT_INTRO_PROMPT）
        输出：{"markdown": "## 1. 项目介绍\n...", "neo4j_id": {"1": [Block nodeId列表]}}
        """
        modules_info = state["modules_info"]
        modules_text = []
        for module in modules_info:
            modules_text.append(
                f"- 模块名称: {module['name']}\n"
                f"  功能说明: {module['module_explaination']}"
            )
        modules_info_str = "\n\n".join(modules_text)

        markdown_content = await intro_chain.ainvoke({"modules_info": modules_info_str})

        neo4j_id = {"1": [str(module['nodeId']) for module in modules_info]}

        logger.info("项目介绍章节生成完成")
        return {
            "section1_intro": {
                "markdown": markdown_content,
                "neo4j_id": neo4j_id
            }
        }

    async def generate_architecture(state: RootDocState) -> RootDocState:
        """
        章节2：项目模块架构
        输入：modules_info（名称+路径+nodeId+功能说明）
        引擎：OpenAI LangChain（MODULE_ARCHITECTURE_PROMPT，返回JSON）
        输出：{"markdown": "## 2. 项目模块架构\n### 2.1 ...", "neo4j_id": {"2.1": "nodeId", ...}}
        """
        modules_info = state["modules_info"]
        modules_text = []
        for module in modules_info:
            modules_text.append(
                f"- 模块名称: {module['name']}\n"
                f"  模块路径: {module['path']}\n"
                f"  模块ID: {module['nodeId']}\n"
                f"  功能说明: {module['module_explaination']}"
            )
        modules_info_str = "\n\n".join(modules_text)

        markdown_content = await architecture_chain.ainvoke({"modules_info": modules_info_str})

        logger.info("模块架构章节生成完成")
        return {
            "section2_architecture": {
                "markdown": json.loads(markdown_content)["markdown"],
                "neo4j_id": json.loads(markdown_content)["mapping"]
            }
        }

    async def generate_diagram(state: RootDocState) -> RootDocState:
        """
        章节3：项目架构图
        输入：无（内部调用module_app子工作流，自行查neo4j）
        引擎：OpenAI LangChain（module_target.py子工作流）
        输出：{"mermaid": "## 3. 项目架构图\n```mermaid\n...\n```", "neo4j_id": {mermaid节点ID: Block nodeId}}
        """
        logger.info("开始生成项目架构图...")

        module_workflow = module_app(llm_interface, neo4j_interface)
        result = await module_workflow.ainvoke(
            {},
            config={"configurable": {"thread_id": "root-doc-module"}}
        )
        module_data = result["output"]
        mermaid_data = module_data["mermaid"]
        neo4j_id = module_data["mapping"]

        mermaid_content = "## 3. 项目架构图\n\n"
        mermaid_content += "下图展示了项目的模块组织结构和依赖关系：\n\n"
        mermaid_content += "```mermaid\n"
        mermaid_content += mermaid_data
        mermaid_content += "\n```"

        logger.info("项目架构图生成完成")
        return {
            "section3_diagram": {"mermaid": mermaid_content, "neo4j_id": neo4j_id}
        }

    # ====================== 新增：扩展章节发现与生成 ======================

    async def discover_sections(state: RootDocState) -> RootDocState:
        """
        调用 Claude CLI 规划需要补充的扩展章节。
        基于已有章节摘要 + neo4j统计 + 源码快速探索来决定。
        """
        if not source_root:
            logger.warning("未配置 source_root，跳过扩展章节发现")
            return {"discovered_sections": []}

        # 从已生成的基础章节中动态构建摘要
        existing_summary = "已有章节：\n"
        if state.get("section1_intro"):
            existing_summary += "  1. 项目介绍（项目整体定位和目标）\n"
        if state.get("section2_architecture"):
            existing_summary += "  2. 项目模块架构（各一级模块的职责说明）\n"
        if state.get("section3_diagram"):
            existing_summary += "  3. 项目架构图（模块依赖关系mermaid图）\n"

        logger.info("开始规划扩展章节...")
        try:
            selected = await run_discover_agent(
                modules_info=state.get("modules_info_text", ""),
                neo4j_stats=state.get("neo4j_stats_text", ""),
                existing_sections_summary=existing_summary,
                source_root=source_root,
                timeout=int(os.environ.get("AGENT_TIMEOUT", "300")),
            )
            logger.info(f"规划完成：选中 {len(selected)} 个扩展章节")
            return {"discovered_sections": selected}
        except Exception as e:
            logger.error(f"扩展章节规划失败: {e}")
            return {"discovered_sections": []}

    async def generate_extra_sections(state: RootDocState) -> RootDocState:
        """
        并发调用 Claude CLI 为每个选中的扩展章节生成内容。
        """
        discovered = state.get("discovered_sections", [])
        if not discovered:
            logger.info("无需生成扩展章节")
            return {"extra_sections": []}

        # 基础章节固定为1-3，扩展章节从4开始
        base_section_num = 4

        max_concurrent = int(os.environ.get("MAX_CONCURRENT_BLOCKS", "3"))
        semaphore = asyncio.Semaphore(max_concurrent)
        max_retries = int(os.environ.get("AGENT_MAX_RETRIES", "2"))

        async def generate_single(item: Dict, index: int, section_number: int):
            async with semaphore:
                key = item["key"]
                # 在候选菜单中找到完整定义
                section_def = next(
                    (s for s in ROOT_CANDIDATE_SECTIONS if s["key"] == key), None
                )
                if not section_def:
                    logger.warning(f"未找到章节定义: {key}")
                    return None

                discovered_hints = item.get("discovered_hints", [])
                label = f"[{index}/{len(discovered)}] {section_def['title']}"

                for attempt in range(1, max_retries + 1):
                    logger.info(
                        f"  {label}: {'第' + str(attempt) + '次尝试' if attempt > 1 else '开始生成'}"
                    )
                    try:
                        result = await run_root_section_agent(
                            section_def=section_def,
                            modules_info=state.get("modules_info_text", ""),
                            neo4j_context=state.get("neo4j_stats_text", ""),
                            discovered_hints=discovered_hints,
                            section_number=section_number,
                            source_root=source_root,
                            timeout=int(os.environ.get("AGENT_TIMEOUT", "600")),
                        )

                        if not result.get("has_content"):
                            logger.info(f"  {label}: 无相关内容，跳过")
                            return None

                        logger.info(f"  {label}: 完成")
                        return {
                            "section_key": key,
                            "section_title": section_def["title"],
                            "section_number": section_number,
                            "content": result,
                        }
                    except Exception as e:
                        logger.warning(f"  {label}: 第{attempt}次失败 - {e}")
                        if attempt < max_retries:
                            await asyncio.sleep(5 * attempt)

                logger.error(f"  {label}: {max_retries}次尝试均失败，放弃")
                return None

        # 并发生成
        tasks = [
            generate_single(item, i + 1, base_section_num + i)
            for i, item in enumerate(discovered)
        ]
        results = await asyncio.gather(*tasks)
        extra_sections = [r for r in results if r is not None]

        # 重新编号：确保连续（有些可能失败被跳过）
        for i, section in enumerate(extra_sections):
            section["section_number"] = base_section_num + i

        logger.info(f"扩展章节生成完成: 成功 {len(extra_sections)}/{len(discovered)}")
        return {"extra_sections": extra_sections}

    async def merge_sections(state: RootDocState) -> RootDocState:
        """
        合并所有章节（基础 + 扩展）为最终JSON输出
        """
        wiki = []
        source_id_list = []
        existing_sids = set()

        def _gen_unique_sid() -> str:
            """生成8位唯一source_id"""
            for _ in range(100):
                sid = str(uuid.uuid4().int)[:8]
                if sid not in existing_sids:
                    existing_sids.add(sid)
                    return sid
            sid = str(uuid.uuid4().int)[:12]
            existing_sids.add(sid)
            return sid

        # ---- 基础章节（OpenAI/LangChain生成的1-3章） ----
        if state.get("section1_intro"):
            wiki.append(state["section1_intro"])
        if state.get("section2_architecture"):
            wiki.append(state["section2_architecture"])
        if state.get("section3_diagram"):
            wiki.append(state["section3_diagram"])

        # ---- 扩展章节（Claude CLI生成） ----
        extra_sections = state.get("extra_sections", [])
        for section_info in extra_sections:
            content = section_info["content"]
            section_number = section_info["section_number"]
            section_key = section_info["section_key"]

            markdown_text = content.get("markdown", "")

            # 从referenced_files查询neo4j nodeId
            raw_refs = content.get("referenced_files", [])
            file_paths = [
                r["path"] for r in raw_refs
                if isinstance(r, dict) and r.get("path")
            ]
            file_node_ids = await resolve_file_node_ids(neo4j_interface, file_paths)
            node_id_list = [str(v) for v in file_node_ids.values()] if file_node_ids else []

            # 如果没有解析到nodeId，使用一级模块的nodeId作为fallback
            if not node_id_list:
                node_id_list = [str(m['nodeId']) for m in state.get("modules_info", [])]

            # 构建neo4j_id映射
            sub_titles = re.findall(r'(?m)^###\s+([\d.]+)', markdown_text)
            if sub_titles:
                neo4j_id_map = {t: node_id_list for t in sub_titles}
            else:
                neo4j_id_map = {str(section_number): node_id_list}

            # markdown条目
            markdown_entry = {
                "markdown": markdown_text,
                "neo4j_id": neo4j_id_map,
            }
            wiki.append(markdown_entry)

            # mermaid条目（如果有）
            mermaid_text = content.get("mermaid")
            if mermaid_text:
                # 校验mermaid语法
                val = _mermaid_validator.validate_file(f"```mermaid\n{mermaid_text}\n```")
                if not val["result"]:
                    logger.warning(
                        f"  [mermaid校验] 章节{section_number} 语法错误: {val['errors']}"
                    )
                    # 跳过有语法错误的mermaid（可以后续接fix_mermaid，此处简化处理）
                    mermaid_text = None

            if mermaid_text:
                # 找最大子标题序号
                existing_sub_nums = [
                    int(t.split(".")[1])
                    for t in sub_titles
                    if "." in t and t.startswith(f"{section_number}.")
                ]
                next_sub = (max(existing_sub_nums) + 1) if existing_sub_nums else 1
                mermaid_sub = f"{section_number}.{next_sub}"
                mermaid_title = f"### {mermaid_sub} 架构图"

                # 处理mermaid_mapping → source_id_list + mapping
                mermaid_mapping_raw = content.get("mermaid_mapping")
                if mermaid_mapping_raw and isinstance(mermaid_mapping_raw, dict):
                    path_to_source_id = {}
                    new_source_entries = []
                    mapping_result = {}

                    for node_id, loc in mermaid_mapping_raw.items():
                        if not isinstance(loc, dict) or not loc.get("path"):
                            continue
                        fpath = loc["path"]
                        flines = loc.get("lines", [])
                        dedup_key = (fpath, tuple(sorted(flines)))

                        if dedup_key not in path_to_source_id:
                            sid = _gen_unique_sid()
                            path_to_source_id[dedup_key] = sid
                            new_source_entries.append({
                                "source_id": sid,
                                "name": fpath,
                                "lines": flines if flines else [],
                            })

                        mapping_result[node_id] = path_to_source_id[dedup_key]

                    if mapping_result:
                        mermaid_entry = {
                            "mermaid": f"{mermaid_title}\n\n```mermaid\n{mermaid_text}\n```",
                            "mapping": mapping_result,
                        }
                        source_id_list.extend(new_source_entries)
                    else:
                        mermaid_entry = {
                            "mermaid": f"{mermaid_title}\n\n```mermaid\n{mermaid_text}\n```",
                            "neo4j_id": {mermaid_sub: node_id_list},
                        }
                else:
                    mermaid_entry = {
                        "mermaid": f"{mermaid_title}\n\n```mermaid\n{mermaid_text}\n```",
                        "neo4j_id": {mermaid_sub: node_id_list},
                    }
                wiki.append(mermaid_entry)

            logger.info(f"  [OK] 合并扩展章节 {section_number}: {section_key}")

        output = {
            "wiki": wiki,
            "source_id_list": source_id_list,
        }

        # 保存输出文件
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "output", "总揽.meta.json"
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"Root文档生成完成，保存路径：{output_path}")
        return {"final_output": output}

    # ====================== 辅助函数 ======================

    async def resolve_file_node_ids(neo4j_if: Neo4jInterface, file_paths: List[str]) -> Dict[str, int]:
        """将文件相对路径映射到neo4j File节点的nodeId"""
        if not file_paths:
            return {}
        query = """
        MATCH (f:File)
        WHERE ANY(path IN $file_paths WHERE f.name CONTAINS path)
        RETURN f.name AS name, f.nodeId AS nodeId
        """
        try:
            results = await neo4j_if.execute_query(query, {"file_paths": file_paths})
            mapping = {}
            for r in results:
                for fp in file_paths:
                    if fp in str(r["name"]):
                        mapping[fp] = r["nodeId"]
            return mapping
        except Exception as e:
            logger.warning(f"查询File nodeId失败: {e}")
            return {}

    # ====================== 构建状态图 ======================
    graph = StateGraph(RootDocState)
    graph.add_node("fetch_modules", fetch_root_modules)
    graph.add_node("generate_intro", generate_intro)
    graph.add_node("generate_architecture", generate_architecture)
    graph.add_node("generate_diagram", generate_diagram)
    graph.add_node("discover_sections", discover_sections)
    graph.add_node("generate_extra", generate_extra_sections)
    graph.add_node("merge", merge_sections)

    # 完整流程：
    #   fetch_modules → generate_intro → generate_architecture → generate_diagram
    #                                                                 ↓
    #                                                         discover_sections
    #                                                                 ↓
    #                                                         generate_extra
    #                                                                 ↓
    #                                                               merge
    graph.set_entry_point("fetch_modules")
    graph.add_edge("fetch_modules", "generate_intro")
    graph.add_edge("generate_intro", "generate_architecture")
    graph.add_edge("generate_architecture", "generate_diagram")
    graph.add_edge("generate_diagram", "discover_sections")
    graph.add_edge("discover_sections", "generate_extra")
    graph.add_edge("generate_extra", "merge")
    graph.add_edge("merge", END)

    app = graph.compile(checkpointer=MemorySaver())
    return app

# ====================== 3. 独立运行入口 ======================
async def main():
    load_dotenv()
    print("=== 独立运行Root文档生成工作流 ===")

    source_root = os.environ.get("SOURCE_ROOT_PATH", "")
    if not source_root:
        print("[WARN] 未配置 SOURCE_ROOT_PATH，扩展章节将被跳过")

    llm = LLMInterface(model_name="gpt-4.1-2025-04-14", provider="openai")
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )

    if not await neo4j.test_connection():
        print("[ERR] Neo4j 连接失败")
        return

    print("[INFO] Neo4j 连接成功")
    print(f"[INFO] SOURCE_ROOT_PATH: {source_root}")
    print(f"[INFO] 日志文件: {_log_path}")

    app = root_doc_workflow(llm, neo4j, source_root=source_root)
    result = await app.ainvoke(
        {},
        config={"configurable": {"thread_id": "root-doc-generation"}}
    )

    neo4j.close()
    print("[INFO] 工作流执行完成")

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
