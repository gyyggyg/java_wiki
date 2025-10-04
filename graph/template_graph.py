from typing import Any, Dict

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from message_service import MessageService
 
from graph.concept_doc_graph import build_concept_doc_app
from graph.global_doc_graph import build_global_doc_app
from graph.system_arch_graph import build_system_arch_app
from graph.scripts_doc_graph import build_scripts_doc_app
from graph.block_doc_graph import build_block_doc_app
from graph.internal_block_doc_graph import build_internal_block_doc_app, collect_internal_blocks
from graph.catalog_doc_graph import build_catalog_doc_app
from typing_extensions import TypedDict
# from graph.recover import expand_files_back_to_file_blocks
class MasterState(TypedDict, total=False):
    run_id: str
    concept_output: str
    global_output: str
    system_arch_output: str
    scripts_output: str
    blocks_output: str
    recovered: bool


def build_master_app(llm: LLMInterface, neo4j: Neo4jInterface):
    concept_app = build_concept_doc_app(llm)
    global_app = build_global_doc_app(llm)
    system_arch_app = build_system_arch_app(llm, neo4j)
    scripts_app = build_scripts_doc_app(llm)
    block_app = build_block_doc_app(llm, neo4j)
    catalog_app = build_catalog_doc_app()
    # 统一的 Markdown 输出根目录，支持通过环境变量覆盖
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    md_root = os.getenv("MD_OUTPUT_ROOT", os.path.join(base_dir, "md_files"))

    async def run_concept(state: MasterState) -> MasterState:
        res = await concept_app.ainvoke({}, config={"configurable": {"thread_id": f"{state.get('run_id','run')}-concept"}})
        return {"concept_output": res.get("output_filename")}

    async def run_global(state: MasterState) -> MasterState:
        code_root = os.environ.get("SOURCE_CODE_ROOT")
        if not code_root:
            raise RuntimeError("缺少环境变量：SOURCE_CODE_ROOT")
        res = await global_app.ainvoke({"path": code_root}, config={"configurable": {"thread_id": f"{state.get('run_id','run')}-global"}})
        return {"global_output": res.get("output_filename")}

    async def run_system_arch(state: MasterState) -> MasterState:
        res = await system_arch_app.ainvoke({}, config={"configurable": {"thread_id": f"{state.get('run_id','run')}-sysarch"}})
        return {"system_arch_output": res.get("output_filename")}

    async def run_scripts(state: MasterState) -> MasterState:
        res = await scripts_app.ainvoke({}, config={"configurable": {"thread_id": f"{state.get('run_id','run')}-scripts"}})
        return {"scripts_output": res.get("output_filename")}

    async def run_all_blocks(state: MasterState) -> MasterState:
        # 生成倒数第二层（其直接子为叶子）的文档
        all_nodes = await neo4j.get_all_block_nodes()
        id_to_node = {str(n["nodeId"]): n for n in all_nodes}
        tasks = []
        index = 0
        for n in all_nodes:
            children = (n.get("child_blocks") or [])
            if not children:
                continue
            # 判断所有直接子是否为叶子：child_blocks == [] 且 contain_nodes 非空
            all_direct_children_are_leaves = True
            for item in children:
                try:
                    cid = str(__import__("json").loads(item)["nodeId"]) if isinstance(item, str) else str(item.get("nodeId"))
                except Exception:
                    all_direct_children_are_leaves = False
                    break
                cnode = id_to_node.get(cid)
                if not cnode:
                    all_direct_children_are_leaves = False
                    break
                c_child = (cnode.get("child_blocks") or [])
                c_contain = (cnode.get("contain_nodes") or [])
                if not (c_child == [] and c_contain):
                    all_direct_children_are_leaves = False
                    break
            if not all_direct_children_are_leaves:
                continue
            index += 1
            block_name = n["name"]
            id_list = children
            filename = _safe_filename(block_name) + f"-{n['nodeId']}"
            path = os.path.join(md_root, "sections", f"{filename}.md")
            init_state = {
                "block": block_name,
                "node_id": n["nodeId"],
                "id_list": id_list,
                "path": path,
                # 数值型 position：5.x -> 5*10000 + x*100
                "sidebar_position": str(5 * 10000 + index * 100),
            }
            tasks.append(
                block_app.ainvoke(
                    init_state,
                    config={"configurable": {"thread_id": f"{state.get('run_id','run')}-block-{index}"}},
                )
            )
        import asyncio as _asyncio
        if tasks:
            await _asyncio.gather(*tasks)
        return {"blocks_output": os.path.join(md_root, "sections")}

    async def run_catalog(state: MasterState) -> MasterState:
        res = await catalog_app.ainvoke({}, config={"configurable": {"thread_id": f"{state.get('run_id','run')}-catalog"}})
        return {"catalog_output": res.get("output_filename")}

    async def run_internal_blocks(state: MasterState) -> MasterState:
        # 生成“纯中间层”节点文档（全深度）
        internal_nodes = await collect_internal_blocks(neo4j)
        internal_app = build_internal_block_doc_app(llm, neo4j)
        tasks = []
        # 分深度并发生成
        from collections import defaultdict as _dd
        groups: dict[int, list[dict]] = _dd(list)
        for n in internal_nodes:
            d = n.get('depth', None)
            if d is None:
                continue
            groups[d].append(n)
        import asyncio as _asyncio
        for d in sorted(groups.keys()):
            group_nodes = sorted(groups[d], key=lambda x: (x.get('name') or "", x.get('nodeId')))
            tasks = []
            for index, n in enumerate(group_nodes, 1):
                filename = _safe_filename(n["name"]) + f"-{n['nodeId']}"
                subdir = f"depth-{d}"
                path = os.path.join(md_root, "sections", subdir, f"{filename}.md")
                def _encode_triplet(a: int, b: int, c: int) -> str:
                    return str(a * 10000 + b * 100 + c)

                init_state = {
                    "block_id": n["nodeId"],
                    "path": path,
                    "sidebar_position": _encode_triplet(6, int(d), int(index)),
                }
                tasks.append(
                    internal_app.ainvoke(
                        init_state,
                        config={"configurable": {"thread_id": f"{state.get('run_id','run')}-internal-d{d}-{index}"}},
                    )
                )
            if tasks:
                await _asyncio.gather(*tasks)
        return {}

    async def run_all_docs(state: MasterState) -> MasterState:
        import asyncio as _asyncio
        # 并行生成四个主文档
        concept_task = concept_app.ainvoke({}, config={"configurable": {"thread_id": f"{state.get('run_id','run')}-concept"}})
        code_root = os.environ.get("SOURCE_CODE_ROOT")
        if not code_root:
            raise RuntimeError("缺少环境变量：SOURCE_CODE_ROOT")
        global_task = global_app.ainvoke({"path": code_root}, config={"configurable": {"thread_id": f"{state.get('run_id','run')}-global"}})
        system_task = system_arch_app.ainvoke({}, config={"configurable": {"thread_id": f"{state.get('run_id','run')}-sysarch"}})
        scripts_task = scripts_app.ainvoke({}, config={"configurable": {"thread_id": f"{state.get('run_id','run')}-scripts"}})

        # 并行生成 internal 中间层文档
        internal_nodes = await collect_internal_blocks(neo4j)
        internal_app = build_internal_block_doc_app(llm, neo4j)
        internal_tasks = []
        # 按深度分组后并发
        from collections import defaultdict as _dd
        groups: dict[int, list[dict]] = _dd(list)
        for n in internal_nodes:
            d = n.get('depth', None)
            if d is None:
                continue
            groups[d].append(n)
        for d in sorted(groups.keys()):
            group_nodes = sorted(groups[d], key=lambda x: (x.get('name') or "", x.get('nodeId')))
            for index, n in enumerate(group_nodes, 1):
                filename = _safe_filename(n["name"]) + f"-{n['nodeId']}"
                subdir = f"depth-{d}"
                path = f"md_files/sections/{subdir}/{filename}.md"
                def _encode_triplet(a: int, b: int, c: int) -> str:
                    return str(a * 10000 + b * 100 + c)
                init_state = {
                    "block_id": n["nodeId"],
                    "path": path,
                    "sidebar_position": _encode_triplet(6, int(d), int(index)),
                }
                internal_tasks.append(
                    internal_app.ainvoke(
                        init_state,
                        config={"configurable": {"thread_id": f"{state.get('run_id','run')}-internal-d{d}-{index}"}},
                    )
                )

        await _asyncio.gather(concept_task, global_task, system_task, scripts_task, *internal_tasks)
        return {}

    # async def run_recover(state: MasterState) -> MasterState:
    #     # 运行 graph/recover.py 中的图结构恢复脚本（幂等）
    #     import asyncio as _asyncio
    #     await _asyncio.to_thread(expand_files_back_to_file_blocks, neo4j.driver)
    #     return {"recovered": True}

    graph = StateGraph(MasterState)
    graph.add_node("run_concept", run_concept)
    graph.add_node("run_global", run_global)
    graph.add_node("run_system_arch", run_system_arch)
    graph.add_node("run_scripts", run_scripts)
    graph.add_node("run_all_blocks", run_all_blocks)
    graph.add_node("run_internal_blocks", run_internal_blocks)
    graph.add_node("run_catalog", run_catalog)
    graph.add_node("run_all_docs", run_all_docs)

    # 先进行 Neo4j 图结构恢复，再并行生成主文档 + internal，中间层完成后再生成 block
    graph.set_entry_point("run_all_docs")
    graph.add_edge("run_all_docs", "run_all_blocks")
    graph.add_edge("run_all_blocks", "run_catalog")
    graph.add_edge("run_catalog", END)

    app = graph.compile(checkpointer=MemorySaver())
    return app


def _safe_filename(name: str) -> str:
    import re
    return re.sub(r'[\\/:"*?<>|]+', '_', name)


if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    # 优先加载 graph/.env；若不存在，再退回项目根目录 .env。兼容常见编码（UTF-8/UTF-16/GBK/BOM）
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        try:
            load_dotenv(env_path)
        except UnicodeDecodeError:
            for _enc in ["utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "gbk"]:
                try:
                    load_dotenv(env_path, encoding=_enc)
                    print(f"已使用编码 {_enc} 加载 graph/.env")
                    break
                except UnicodeDecodeError:
                    continue
    else:
        load_dotenv()
    
    async def main():
        # 配置 LLM
        provider = os.getenv("LLM_PROVIDER", "openai")
        model = os.getenv("LLM_MODEL", "gpt-4.1-mini")
        llm = LLMInterface(model_name=model, provider=provider)
        uri = os.environ.get("WIKI_NEO4J_URI")
        user = os.environ.get("WIKI_NEO4J_USER")
        password = os.environ.get("WIKI_NEO4J_PASSWORD")
        if not (uri and user and password):
            raise RuntimeError("缺少环境变量：WIKI_NEO4J_URI / WIKI_NEO4J_USER / WIKI_NEO4J_PASSWORD")
        neo4j = Neo4jInterface(uri=uri, user=user, password=password)
        
        if not await neo4j.test_connection():
            print("Neo4j连接失败")
            return
            
        # MQ 集成：在流程前后发送状态消息
        svc = MessageService({
            "bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "43.199.163.233:9092"),
            "client_id": os.getenv("KAFKA_CLIENT_ID", "py_kafka_producer"),
        })
        topic = os.getenv("KAFKA_TOPIC", "wiki.generate")

        app = build_master_app(llm, neo4j)
        try:
            start_time = time.perf_counter()
            svc.send_message(topic, {"spaceId": os.getenv("SPACE_ID", "123"), "event": "started", "data": {"progress": 0}}, None, None)
            result = await app.ainvoke({"run_id": "all-docs"}, config={"configurable": {"thread_id": "standalone-master"}})
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            svc.send_message(topic, {"spaceId": os.getenv("SPACE_ID", "123"), "event": "complete", "data": {"progress": 100, "duration_ms": duration_ms}}, None, None)
            print(f"流程总耗时: {duration_ms/1000:.2f} 秒")
        except Exception as e:
            try:
                duration_ms = int((time.perf_counter() - start_time) * 1000)
            except Exception:
                duration_ms = None
            payload = {"spaceId": os.getenv("SPACE_ID", "123"), "event": "failed", "data": {"error": str(e)}}
            if duration_ms is not None:
                payload["data"]["duration_ms"] = duration_ms
            svc.send_message(topic, payload , None, None)
            raise
        finally:
            svc.close()
            neo4j.close()
    
    asyncio.run(main())

