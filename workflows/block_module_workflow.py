import os
import sys
import json
import asyncio
from typing import Any, Dict, List
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gy.interfaces.data_master import get_file
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from chains.common_chains import ChainFactory
from chains.prompts.block_doc_prompt import BLOCK_OVERVIEW_PROMPT, MODULE_CHART_PROMPT, BLOCK_RELATIONSHIP_PROMPT
from graph.module_target import module_app
from graph.four_chart import chart_app
from time import sleep

# ====================== 1. 状态定义 ======================
class BlockState(TypedDict, total=False):
    section1_summary: Dict
    section2_core_components: Dict
    section3_architecture_diagram: Dict
    section4_main_control_flow: list
    section5_module_relation: Dict
    section6_data_uml: Dict
    source_id_list: List

new_names = json.loads(get_file(r"E:\\github_clone\\java_wiki\\gy\\graph\\block_new_names.json"))

# ====================== 2. 工作流定义 ======================
def block_module_workflow(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface, id_name_path: Dict):
    generate_summary_chain = ChainFactory.create_generic_chain(llm_interface, BLOCK_OVERVIEW_PROMPT)
    generate_module_chart_chain = ChainFactory.create_generic_chain(llm_interface, MODULE_CHART_PROMPT)
    generate_relationship_chain = ChainFactory.create_generic_chain(llm_interface, BLOCK_RELATIONSHIP_PROMPT)

    name = id_name_path["block_name"]
    write_path = id_name_path["block_path"] + ".json"
    nodeId = int(id_name_path["block_id"])
    async def generate_summary(state: BlockState) -> BlockState:
        query = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c*]->(f:File)
        RETURN b.module_explaination AS block_explanation, f.module_explaination AS file_explanation, f.name AS file_name
        """
        result = await neo4j_interface.execute_query(query, {"nodeId": nodeId})

        # 初始化变量，避免作用域问题
        block_explanation = "暂无说明"
        file_info = []

        # 处理查询结果
        if result:
            # block_explanation对所有记录都相同，取第一条即可
            block_explanation = result[0].get("block_explanation", "暂无说明")
            # 收集所有文件信息
            for record in result:
                file_name = record.get("file_name", "未知文件")
                file_exp = record.get("file_explanation", "暂无说明")
                file_info.append(f"{file_name}: {file_exp}")

        section1_content = await generate_summary_chain.ainvoke({
            "block_name": name,
            "block_explaination": block_explanation,
            "file_info": "\n".join(file_info)
        })
        print("1 done")
        return {"section1_summary": {"markdown": section1_content, "neo4j_id": {"1": nodeId}}}
    
    async def generate_core_components(state: BlockState) -> BlockState:
        query = """
        MATCH (b:Block)-[:f2c*]->(f:File)-[:DECLARES]->(com)
        WHERE b.nodeId = $nodeId
        OPTIONAL MATCH (f)<-[:CONTAINS]-(p:Package)
        RETURN labels(com) AS com_labels, com.name AS com_name, com.SE_How AS how, com.SE_What AS what, com.SE_When AS when, 
        f.name AS file_name, p.name AS package_name, com.nodeId AS com_nodeId, f.nodeId AS file_nodeId, p.nodeId AS package_nodeId
        """
        content = ["## 2. 核心组件介绍\n"]
        result = await neo4j_interface.execute_query(query, {"nodeId": nodeId})
        neo4j_id = {}
        for i, record in enumerate(result, 1):
            com_name = record.get("com_name")
            file_name = record.get("file_name", "未知文件")
            package_name = record.get("package_name", "未知包")
            what = record.get("what", "暂无说明")
            how = record.get("how", "")
            when = json.loads(record.get("when"))["summary"]
            com_labels = record.get("com_labels")[0]
            com_nodeId = record.get("com_nodeId")
            file_nodeId = record.get("file_nodeId")
            package_nodeId = record.get("package_nodeId")
            content.append(f"### 2.{i} {com_name}({com_labels})\n")
            content.append(f"{com_name}属于文件{file_name}, 该文件属于包{package_name}\n")
            content.append(f"- **主要职责**\n  - {what}\n")
            content.append(f"- **实现方式**\n  - {how}\n")
            content.append(f"- **使用时机**\n  - {when}\n" )
            neo4j_id[f"2.{i}"] = [com_nodeId, file_nodeId, package_nodeId]
        return {"section2_core_components": {"markdown": "\n".join(content), "neo4j_id": neo4j_id}}
    
    async def generate_architecture_diagram(state: BlockState) -> BlockState:
        query_relationship = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->()-[r*1..5]->(c)<-[:DECLARES]-(f2:File)
        WHERE NONE(rel IN r WHERE type(rel) IN ['CONTAINS', 'DIR_INCLUDES', 'f2c']) AND (f2:File)<-[:f2c*]-(b) AND f1 <> f2
        RETURN f1.nodeId AS from_fileId, f1.name AS from_fileName,
               f2.nodeId AS to_fileId, f2.name AS to_fileName
        """
        result = await neo4j_interface.execute_query(query_relationship, {"nodeId": nodeId})
        rel = {}
        id_name = {}
        for record in result:
            id_name[record["from_fileId"]] = record["from_fileName"]
            id_name[record["to_fileId"]] = record["to_fileName"]
            if record["from_fileId"] not in rel:
                rel[record["from_fileId"]] = []
            rel[record["from_fileId"]].append(record["to_fileId"]) 
        relationship = set()
        for key, values in rel.items():
            for value in values:
                relationship.add(f"{id_name[key]} 指向 {id_name[value]}")
        print(relationship)

        query_paths = """
        MATCH (root:Block)
        WHERE root.nodeId = $nodeId
        MATCH path = (root)-[:f2c*]->(target:File)
        WITH nodes(path) AS path_nodes
        UNWIND range(0, size(path_nodes)-2) AS i
        WITH path_nodes[i] AS parent, path_nodes[i+1] AS child
        RETURN DISTINCT parent.nodeId AS parent_id, parent.name AS parent_name,
               child.nodeId AS child_id, child.name AS child_name
        """
        path_results = await neo4j_interface.execute_query(query_paths, {"nodeId": nodeId})

        # 构建父子关系字典和收集所有节点ID
        f2c = {}
        id_name_map = {}
        # explanations = []
        path = {}


        for record in path_results:
            parent_id = record['parent_id']
            parent_name = record['parent_name']
            id_name_map[parent_id] = parent_name
            child_name = record['child_name']
            child_id = record['child_id']
            id_name_map[child_id] = child_name
            if child_name.startswith(parent_name) and child_name != parent_name:
                suffix = child_name[len(parent_name):].lstrip("/")
                path[child_id] = f"../{suffix}" if suffix else "../"
            else:
                path[child_id] = child_name

            if parent_id not in f2c:
                f2c[parent_id] = []
            if child_id not in f2c[parent_id]:
                f2c[parent_id].append(child_id)


        # 构建嵌套树结构
        def build_tree(node_id) -> dict:
            children = f2c.get(node_id, [])
            return {
                "name": new_names.get(str(node_id)),
                "id": node_id,
                "path": path.get(node_id),
                "children": [build_tree(child) for child in children]
            }

        tree_structure = build_tree(nodeId)
        project_information = tree_structure.get("children", [])
        # if explanation_results:
        #     for record in explanation_results:
        #         explanations.append(f"{record['block_name']}: {record['explanation']}")

        mermaid_result = await generate_module_chart_chain.ainvoke({
            "project_information": project_information,
            "relationship": "\n".join(relationship)
        })    
        print(mermaid_result)
        markedown_content = "## 3. 模块内架构图\n```mermaid\n" + json.loads(mermaid_result)["mermaid"] +"```"
        return {"section3_architecture_diagram": {"markdown": markedown_content, "neo4j_id": json.loads(mermaid_result)['mapping']}}
    
    async def main_control_flow(state: BlockState) -> BlockState:
        query = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c*]->(f:File)-[:DECLARES]->(c)-[:DECLARES*]->(m:Method)
        RETURN c.name AS class_name, m.name AS method_name, m.nodeId AS method_nodeId, m.layer_num AS layer_num
        ORDER BY layer_num DESC
        LIMIT 1
        """
        result = await neo4j_interface.execute_query(query, {"nodeId": nodeId})
        section4_main_control_flow = [{"markdown":"## 4. 关键控制流分析\n", "neo4j_id":{}}]
        source_id_list = state.get("source_id_list", [])
        for idx, method in enumerate(result, 1):
            content = []
            class_name = method.get("class_name", "未知类")
            method_name = method.get("method_name", "未知方法")
            method_nodeId = method.get("method_nodeId")
            content.append(f"### 4.{idx} {class_name}.{method_name} 控制流分析\n")
            # 调用四图生成控制流图
            app = chart_app(llm_interface, neo4j_interface, node_list=[method_nodeId], type="cfg")
            result = await app.ainvoke(
                {}, 
                config={"configurable": {"thread_id":f"{class_name}.{method_name}standalone-api"}}
            )
            module_data = result["output"]
            content.append(module_data)
            mapping = result["mapping"]
            source_id_list.extend(result["id_list"])
            section4_main_control_flow.append({"mermaid":"".join(content), "mapping": mapping})
        return {"section4_main_control_flow": section4_main_control_flow, "source_id_list": source_id_list}
    
    async def module_relation(state: BlockState) -> BlockState:
        query_calls = """
        MATCH (b1:Block{nodeId: $nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->(c1)-[r*1..5]->(c2)<-[:DECLARES]-(f2:File)<-[:f2c*]-(b2:Block)
        WHERE NONE(rel IN r WHERE type(rel) IN ['CONTAINS', 'DIR_INCLUDES', 'f2c']) AND f1 <> f2 AND b1.name <> 'root' AND b2.name <> 'root'
        MATCH p = shortestPath((f2)<-[:f2c*1..]-(b2:Block))
        WHERE b1 <> b2 AND NOT EXISTS ((b2:Block)<-[:f2c*]-(:Block)-[:f2c]->(:File))
        RETURN c1.name AS from_component, c1.nodeId AS from_componentId, c1.SE_What AS from_what,
                c2.name AS to_component, c2.nodeId AS to_componentId, c2.SE_What AS to_what,
                b2.name AS to_block, b2.nodeId AS to_blockId
        """
        query_called = """
        MATCH (b1:Block{nodeId: $nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->(c1)<-[r*1..5]-(c2)<-[:DECLARES]-(f2:File)<-[:f2c*]-(b2:Block)
        WHERE NONE(rel IN r WHERE type(rel) IN ['CONTAINS', 'DIR_INCLUDES', 'f2c']) AND f1 <> f2 AND b1.name <> 'root' AND b2.name <> 'root'
        MATCH p = shortestPath((f2)<-[:f2c*1..]-(b2:Block))
        WHERE b1 <> b2 AND NOT EXISTS ((b2:Block)<-[:f2c*]-(:Block)-[:f2c]->(:File))
        RETURN c2.name AS from_component, c2.nodeId AS from_componentId, c2.SE_What AS from_what,
                c1.name AS to_component, c1.nodeId AS to_componentId, c1.SE_What AS to_what,
                b2.name AS from_block, b2.nodeId AS from_blockId
        """
        result1, result2 = await asyncio.gather(
            neo4j_interface.execute_query(query_calls, {"nodeId": nodeId}),
            neo4j_interface.execute_query(query_called, {"nodeId": nodeId})
        )
        sema = {}
        relationship = set(f"下面是{name}模块和其他模块之间的关系，接下来我们用'该模块'指代{name}模块。\n")
        for record in result1:
            from_component = record.get("from_component", "未知组件")
            from_what = record.get("from_what", "暂无说明")
            to_component = record.get("to_component", "未知组件")
            to_what = record.get("to_what", "暂无说明")
            to_block_id = record.get("to_blockId")
            to_block = new_names[str(to_block_id)]
            sema["from_component"] = from_what
            sema["to_component"] = to_what
            relationship.add(f"该模块中的组件 {from_component}调用了id为{to_block_id}模块 {to_block} 中的组件 {to_component}\n")
        for record in result2:
            from_component = record.get("from_component", "未知组件")
            from_what = record.get("from_what", "暂无说明")
            to_component = record.get("to_component", "未知组件")
            to_what = record.get("to_what", "暂无说明")
            from_block_id = record.get("from_blockId")
            from_block = new_names[str(from_block_id)]
            sema["from_component"] = from_what
            sema["to_component"] = to_what
            relationship.add(f"id为{from_block_id}模块 {from_block} 中的组件 {from_component}调用了该模块中的组件 {to_component}\n")
        for key, values in sema.items():
            relationship.add(f"{key}: {values}\n")
        print(relationship)
        markdown_result = await generate_relationship_chain.ainvoke({"cross_module_calls": "\n".join(relationship)})
        section5_module_relation = {"markdown": json.loads(markdown_result)["markdown"], "neo4j_id": json.loads(markdown_result)["mapping"]}
        print(markdown_result)
        return {"section5_module_relation": section5_module_relation}
    
    async def data_uml(state: BlockState) -> BlockState:
        query = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c*]->(f:File)-[:DECLARES]->(c:Class|Interface)
        RETURN c.name AS class_name
        """
        source_id_list = state.get("source_id_list", [])
        result = await neo4j_interface.execute_query(query, {"nodeId": nodeId})
        id_list = ["Class&Interface"]
        for record in result:
            id_list.append(record.get("class_name"))
        app = chart_app(llm_interface, neo4j_interface, node_list=id_list, type="uml")
        result = await app.ainvoke(
            {}, 
            config={"configurable": {"thread_id":f"{name}standalone-uml"}}
        )
        module_data = result["output"]
        mapping = result["mapping"]
        source_id_list.extend(result["id_list"])
        section6_data_uml_mermaid= "### 6. 模块数据结构\n" + module_data
        section6_data_uml = {"mermaid": section6_data_uml_mermaid, "mapping": mapping}
        return {"section6_data_uml": section6_data_uml, "source_id_list": source_id_list}

    async def generate_final_output(state: BlockState) -> BlockState:
        print(f"[final_output] state keys: {list(state.keys())}")
        content = {"wiki":[
            state.get("section1_summary", {"markdown": ""}),
            state.get("section2_core_components", {"markdown": ""}),
            state.get("section3_architecture_diagram", {"markdown": ""})
        ]}
        content["wiki"].extend(state.get("section4_main_control_flow", []))
        content["wiki"].append(state.get("section5_module_relation", {"markdown": ""}))
        content["wiki"].append(state.get("section6_data_uml", {"mermaid": ""}))
        content["source_id_list"] = state.get("source_id_list", [])
        os.makedirs(os.path.dirname(write_path), exist_ok=True)
        with open(write_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=4)
        print("final output done")
        return {}
    def should_generate_output(state: BlockState) -> str:
      """检查所有章节是否都已生成完成"""
      required_keys = [
          "section1_summary",
          "section2_core_components",
          "section3_architecture_diagram",
          "section4_main_control_flow",
          "section5_module_relation",
          "section6_data_uml"
      ]
      if all(key in state and state[key] for key in required_keys):
          return "generate_final_output"
      return "wait"  # 或者返回 END 让其他分支继续
    

    # 构建状态图
    graph = StateGraph(BlockState)
    graph.add_node("generate_summary", generate_summary)
    graph.add_node("generate_core_components", generate_core_components)
    graph.add_node("generate_architecture_diagram", generate_architecture_diagram)
    graph.add_node("main_control_flow", main_control_flow)
    graph.add_node("module_relation", module_relation)
    graph.add_node("data_uml", data_uml)
    graph.add_node("generate_final_output", generate_final_output)
    # 设置流程
    graph.set_entry_point("generate_summary")
    graph.add_edge("generate_summary", "generate_core_components")
    graph.add_edge("generate_summary", "generate_architecture_diagram")
    graph.add_edge("generate_summary", "main_control_flow")
    graph.add_edge("generate_summary", "module_relation")
    graph.add_edge("main_control_flow", "data_uml")
    graph.add_conditional_edges(
        "generate_core_components",
        should_generate_output,
        {"generate_final_output": "generate_final_output", "wait": END}
    )
    graph.add_conditional_edges(
        "generate_architecture_diagram",
        should_generate_output,
        {"generate_final_output": "generate_final_output", "wait": END}
    )
    graph.add_conditional_edges(
        "module_relation",
        should_generate_output,
        {"generate_final_output": "generate_final_output", "wait": END}
    )
    graph.add_conditional_edges(
        "data_uml",
        should_generate_output,
        {"generate_final_output": "generate_final_output", "wait": END}
    )

    graph.add_edge("generate_final_output", END)


    app = graph.compile(checkpointer=MemorySaver())
    return app

# ====================== 3. 独立运行入口 ======================
async def main():
    load_dotenv()
    print("=== 独立运行叶子Block文档生成工作流 ===")

    llm = LLMInterface(model_name="gpt-4.1", provider="openai")
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )

    if not await neo4j.test_connection():
        print("[ERR] Neo4j 连接失败")
        return

    print("[INFO] Neo4j 连接成功")

    # 读取叶子Block映射
    block_target = json.loads(get_file(r"gy\output\leaf_blocks_mapping.json"))

    # ============ 单个Block测试模式 ============
    # 取第一个block进行测试
    first_block_id, first_block_path = list(block_target.items())[2]
    first_block_name = new_names.get(str(first_block_id), f"Block_{first_block_id}")

    print(f"[INFO] 测试模式: 只处理第一个Block")
    print(f"[INFO] Block ID: {first_block_id}, Name: {first_block_name}")

    try:
        id_name_path = {
            "block_id": first_block_id,
            "block_name": first_block_name,
            "block_path": first_block_path
        }

        app = block_module_workflow(llm, neo4j, id_name_path)
        result = await app.ainvoke(
            {},
            config={"configurable": {"thread_id": f"block-{first_block_id}"}}
        )
        print(f"[INFO] 测试完成: {first_block_name}")
    except Exception as e:
        print(f"[ERR] 测试失败: {first_block_name} - {str(e)}")
        import traceback
        traceback.print_exc()

    # ============ 以下是原并发逻辑（已注释） ============
    # # 准备所有需要处理的Block
    # blocks_to_process = []
    # for block_id, block_path in block_target.items():
    #     block_name = new_names.get(str(block_id), f"Block_{block_id}")
    #     blocks_to_process.append({
    #         "block_id": block_id,
    #         "block_name": block_name,
    #         "block_path": block_path
    #     })

    # print(f"[INFO] 共有 {len(blocks_to_process)} 个叶子Block需要生成文档")

    # # 从环境变量读取最大并发数
    # max_concurrent = int(os.environ.get("MAX_CONCURRENT_BLOCKS", "10"))
    # print(f"[INFO] 最大并发数: {max_concurrent}")

    # # 创建信号量控制并发
    # semaphore = asyncio.Semaphore(max_concurrent)

    # async def process_single_block(block_info: Dict, index: int):
    #     """
    #     处理单个Block的文档生成
    #     """
    #     async with semaphore:
    #         block_id = block_info["block_id"]
    #         block_name = block_info["block_name"]
    #         block_path = block_info["block_path"]

    #         print(f"  [{index}/{len(blocks_to_process)}] 开始生成: {block_name} ({block_id})")

    #         try:
    #             # 创建workflow实例
    #             id_name_path = {
    #                 "block_id": block_id,
    #                 "block_name": block_name,
    #                 "block_path": block_path
    #             }

    #             app = block_module_workflow(llm, neo4j, id_name_path)

    #             # 执行workflow
    #             result = await app.ainvoke(
    #                 {},
    #                 config={"configurable": {"thread_id": f"block-{block_id}"}}
    #             )

    #             print(f"  [{index}/{len(blocks_to_process)}] 完成: {block_name}")
    #             return {
    #                 "block_id": block_id,
    #                 "block_name": block_name,
    #                 "success": True,
    #                 "result": result
    #             }

    #         except Exception as e:
    #             print(f"  [{index}/{len(blocks_to_process)}] 失败: {block_name} - {str(e)}")
    #             return {
    #                 "block_id": block_id,
    #                 "block_name": block_name,
    #                 "success": False,
    #                 "error": str(e)
    #             }

    # # 并发执行所有Block的文档生成
    # print(f"[INFO] 开始并发生成文档...")
    # tasks = [
    #     process_single_block(block, i + 1)
    #     for i, block in enumerate(blocks_to_process)
    # ]

    # results = await asyncio.gather(*tasks)

    # # 统计结果
    # success_count = sum(1 for r in results if r["success"])
    # fail_count = len(results) - success_count

    # print(f"\n[INFO] 文档生成完成:")
    # print(f"  - 成功: {success_count}/{len(blocks_to_process)}")
    # print(f"  - 失败: {fail_count}/{len(blocks_to_process)}")

    # if fail_count > 0:
    #     print(f"\n[WARN] 失败的Block:")
    #     for r in results:
    #         if not r["success"]:
    #             print(f"  - {r['block_name']} ({r['block_id']}): {r['error']}")

    neo4j.close()
    print("[INFO] 工作流执行完成")

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())

    

    

    