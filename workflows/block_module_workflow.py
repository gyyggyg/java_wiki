import os
import sys
import json
import asyncio
from typing import Any, Dict, List
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from interfaces.data_master import get_file
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from chains.common_chains import ChainFactory
from chains.prompts.block_doc_prompt import BLOCK_OVERVIEW_PROMPT, MODULE_CHART_PROMPT, BLOCK_RELATIONSHIP_PROMPT
from graph.module_target import module_app
from graph.four_chart import chart_app, invoke_and_parse
from time import sleep
import logging

# 项目根目录（java_wiki）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 配置日志，只记录block生成结果
from datetime import datetime
_internal_result_dir = os.path.join(PROJECT_ROOT, "internal_result")
os.makedirs(_internal_result_dir, exist_ok=True)
_log_path = os.path.join(_internal_result_dir, f"block_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(level=logging.INFO)
block_logger = logging.getLogger("block_generation")
_file_handler = logging.FileHandler(_log_path, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
_file_handler.flush = _file_handler.stream.flush  # 每条日志立即写入磁盘
block_logger.addHandler(_file_handler)
block_logger.propagate = False

# ====================== 1. 状态定义 ======================
class BlockState(TypedDict, total=False):
    section1_summary: Dict
    section2_core_components: Dict
    section3_architecture_diagram: Dict
    section4_main_control_flow: list
    section5_module_relation: Dict
    section6_data_uml: Dict
    source_id_list: List

# 修改：将硬编码的Windows路径改为基于项目根目录的相对路径
new_names = json.loads(get_file(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "graph", "block_new_names.json")))

# ====================== 2. 工作流定义 ======================
def block_module_workflow(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface, id_name_path: Dict, skeleton: bool = False):
    generate_summary_chain = ChainFactory.create_generic_chain(llm_interface, BLOCK_OVERVIEW_PROMPT)
    generate_module_chart_chain = ChainFactory.create_generic_chain(llm_interface, MODULE_CHART_PROMPT)
    generate_relationship_chain = ChainFactory.create_generic_chain(llm_interface, BLOCK_RELATIONSHIP_PROMPT)

    name = id_name_path["block_name"]
    write_path = id_name_path["block_path"] + ".meta.json"
    # Windows长路径支持（超过260字符限制）
    if sys.platform == "win32" and not write_path.startswith("\\\\?\\"):
        write_path = "\\\\?\\" + os.path.abspath(write_path)
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
        query = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c*]->(f:File)
        OPTIONAL MATCH (f)<-[:CONTAINS]-(p:Package)
        RETURN f.name AS file_name, p.name AS package_name, f.SE_What AS file_explanation, f.nodeId AS file_nodeId, p.nodeId AS package_nodeId
        """
        table_lines = []
        table_lines.append("| 文件 | 所属包 | 文件功能 |")
        table_lines.append("| --- | --- | --- |")
        node_id = set()
        result = await neo4j_interface.execute_query(query, {"nodeId": nodeId})
        for record in result:
            file_name = record.get("file_name", "未知文件")
            package_name = record.get("package_name", "未知包")
            file_explanation = record.get("file_explanation", "暂无说明")
            file_nodeId = record.get("file_nodeId")
            package_nodeId = record.get("package_nodeId")
            table_lines.append(f"| {file_name} | {package_name} | {file_explanation} |")
            node_id.add(str(file_nodeId))
            node_id.add(str(package_nodeId))

        markedown_content = "## 3. 模块内架构\n" + "\n".join(table_lines)
        return {"section3_architecture_diagram": {"markdown": markedown_content, "neo4j_id": {"3": list(node_id)}}}
        # query_relationship = """
        # MATCH (b:Block {nodeId: $nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->()-[r*1..5]->(c)<-[:DECLARES]-(f2:File)
        # WHERE NONE(rel IN r WHERE type(rel) IN ['CONTAINS', 'DIR_INCLUDES', 'f2c']) AND (f2:File)<-[:f2c*]-(b) AND f1 <> f2
        # RETURN f1.nodeId AS from_fileId, f1.name AS from_fileName,
        #        f2.nodeId AS to_fileId, f2.name AS to_fileName
        # """
        # result = await neo4j_interface.execute_query(query_relationship, {"nodeId": nodeId})
        # rel = {}
        # id_name = {}
        # for record in result:
        #     id_name[record["from_fileId"]] = record["from_fileName"]
        #     id_name[record["to_fileId"]] = record["to_fileName"]
        #     if record["from_fileId"] not in rel:
        #         rel[record["from_fileId"]] = []
        #     rel[record["from_fileId"]].append(record["to_fileId"]) 
        # relationship = set()
        # for key, values in rel.items():
        #     for value in values:
        #         relationship.add(f"{id_name[key]} 指向 {id_name[value]}")
        # print(relationship)

        # query_paths = """
        # MATCH (root:Block)
        # WHERE root.nodeId = $nodeId
        # MATCH path = (root)-[:f2c*]->(target:File)
        # WITH nodes(path) AS path_nodes
        # UNWIND range(0, size(path_nodes)-2) AS i
        # WITH path_nodes[i] AS parent, path_nodes[i+1] AS child
        # RETURN DISTINCT parent.nodeId AS parent_id, parent.name AS parent_name,
        #        child.nodeId AS child_id, child.name AS child_name
        # """
        # path_results = await neo4j_interface.execute_query(query_paths, {"nodeId": nodeId})

        # # 构建父子关系字典和收集所有节点ID
        # f2c = {}
        # id_name_map = {}
        # # explanations = []
        # path = {}


        # for record in path_results:
        #     parent_id = record['parent_id']
        #     parent_name = record['parent_name']
        #     id_name_map[parent_id] = parent_name
        #     child_name = record['child_name']
        #     child_id = record['child_id']
        #     id_name_map[child_id] = child_name
        #     if child_name.startswith(parent_name) and child_name != parent_name:
        #         suffix = child_name[len(parent_name):].lstrip("/")
        #         path[child_id] = f"../{suffix}" if suffix else "../"
        #     else:
        #         path[child_id] = child_name

        #     if parent_id not in f2c:
        #         f2c[parent_id] = []
        #     if child_id not in f2c[parent_id]:
        #         f2c[parent_id].append(child_id)


        # # 构建嵌套树结构
        # def build_tree(node_id) -> dict:
        #     children = f2c.get(node_id, [])
        #     return {
        #         "name": new_names.get(str(node_id)),
        #         "id": node_id,
        #         "path": path.get(node_id),
        #         "children": [build_tree(child) for child in children]
        #     }

        # tree_structure = build_tree(nodeId)
        # project_information = tree_structure.get("children", [])
        # # if explanation_results:
        # #     for record in explanation_results:
        # #         explanations.append(f"{record['block_name']}: {record['explanation']}")

        # mermaid_result = await generate_module_chart_chain.ainvoke({
        #     "project_information": project_information,
        #     "relationship": "\n".join(relationship)
        # })    
        # print(mermaid_result)
        # markedown_content = "## 3. 模块内架构图\n```mermaid\n" + json.loads(mermaid_result)["mermaid"] +"```"
        # return {"section3_architecture_diagram": {"markdown": markedown_content, "neo4j_id": json.loads(mermaid_result)['mapping']}}
    
    async def main_control_flow(state: BlockState) -> BlockState:
        query = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c*]->(f:File)-[:DECLARES]->(c:Class)-[:DECLARES*]->(m:Method)
        RETURN c.name AS class_name, m.name AS method_name, m.nodeId AS method_nodeId, m.layer_num AS layer_num
        ORDER BY layer_num DESC
        LIMIT 3
        """
        result = await neo4j_interface.execute_query(query, {"nodeId": nodeId})
        section4_main_control_flow = [{"markdown":"## 4. 关键控制流分析\n", "neo4j_id":{"4" :[str(nodeId)]}}]
        source_id_list = state.get("source_id_list", [])

        async def generate_single_cfg(idx, method):
            class_name = method.get("class_name", "未知类")
            method_name = method.get("method_name", "未知方法")
            method_nodeId = method.get("method_nodeId")
            app = chart_app(llm_interface, neo4j_interface, node_list=[method_nodeId], type="cfg")
            cfg_result = await app.ainvoke(
                {},
                config={"configurable": {"thread_id":f"{class_name}.{method_name}standalone-api"}}
            )
            content = f"### 4.{idx} {class_name}.{method_name} 控制流分析\n" + cfg_result["output"]
            return {
                "idx": idx,
                "mermaid": content,
                "mapping": cfg_result["mapping"],
                "id_list": cfg_result["id_list"]
            }

        # 并发执行所有cfg生成
        tasks = [generate_single_cfg(idx, method) for idx, method in enumerate(result, 1)]
        cfg_results = await asyncio.gather(*tasks)

        # 按idx排序，确保标题顺序正确
        cfg_results.sort(key=lambda x: x["idx"])

        for cfg in cfg_results:
            section4_main_control_flow.append({"mermaid": cfg["mermaid"], "mapping": cfg["mapping"]})
            source_id_list.extend(cfg["id_list"])

        return {"section4_main_control_flow": section4_main_control_flow, "source_id_list": source_id_list}
    
    async def module_relation(state: BlockState) -> BlockState:
        query_calls = """
        MATCH (b1:Block{nodeId:$nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->(m1:Method)-[:CALLS]->(m2:Method)<-[:DECLARES]-(c2)<-[:DECLARES]-(f2:File)<-[:f2c*]-(b2:Block)
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'CALLS' AS rel_type, m1.name AS from_entity, m1.nodeId AS from_entityId, m1.SE_What AS from_what,
               m2.name AS to_entity, m2.nodeId AS to_entityId, m2.SE_What AS to_what,
               b2.name AS to_block, b2.nodeId AS to_blockId, null AS mid_entity, null AS mid_entityId

        UNION ALL

        MATCH (b1:Block{nodeId:$nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->(c1)-[:EXTENDS]->(c2)<-[:DECLARES]-(f2:File)<-[:f2c*]-(b2:Block)
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'EXTENDS' AS rel_type, c1.name AS from_entity, c1.nodeId AS from_entityId, c1.SE_What AS from_what,
               c2.name AS to_entity, c2.nodeId AS to_entityId, c2.SE_What AS to_what,
               b2.name AS to_block, b2.nodeId AS to_blockId, null AS mid_entity, null AS mid_entityId

        UNION ALL

        MATCH (b1:Block{nodeId:$nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->(c1)-[:IMPLEMENTS]->(i2:Interface)<-[:DECLARES]-(f2:File)<-[:f2c*]-(b2:Block)
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'IMPLEMENTS' AS rel_type, c1.name AS from_entity, c1.nodeId AS from_entityId, c1.SE_What AS from_what,
               i2.name AS to_entity, i2.nodeId AS to_entityId, i2.SE_What AS to_what,
               b2.name AS to_block, b2.nodeId AS to_blockId, null AS mid_entity, null AS mid_entityId

        UNION ALL

        MATCH (b1:Block{nodeId:$nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->(c1)-[:DECLARES]->(m:Method)-[:USES]->(c2)<-[:DECLARES]-(f2:File)<-[:f2c*]-(b2:Block)
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'USES_CLASS' AS rel_type, c1.name AS from_entity, c1.nodeId AS from_entityId, c1.SE_What AS from_what,
               c2.name AS to_entity, c2.nodeId AS to_entityId, c2.SE_What AS to_what,
               b2.name AS to_block, b2.nodeId AS to_blockId, m.name AS mid_entity, m.nodeId AS mid_entityId

        UNION ALL

        MATCH (b1:Block{nodeId:$nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->(c1)-[:DECLARES]->(m:Method)-[:USES]->(fd:Field)<-[:DECLARES]-(c2)<-[:DECLARES]-(f2:File)<-[:f2c*]-(b2:Block)
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'USES_FIELD' AS rel_type, c1.name AS from_entity, c1.nodeId AS from_entityId, c1.SE_What AS from_what,
               c2.name AS to_entity, c2.nodeId AS to_entityId, c2.SE_What AS to_what,
               b2.name AS to_block, b2.nodeId AS to_blockId, fd.name AS mid_entity, fd.nodeId AS mid_entityId

        UNION ALL

        MATCH (b1:Block{nodeId:$nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->(c1)-[:DECLARES]->(fd:Field)-[:HAS_TYPE]->(c2)<-[:DECLARES]-(f2:File)<-[:f2c*]-(b2:Block)
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'HAS_TYPE' AS rel_type, c1.name AS from_entity, c1.nodeId AS from_entityId, c1.SE_What AS from_what,
               c2.name AS to_entity, c2.nodeId AS to_entityId, c2.SE_What AS to_what,
               b2.name AS to_block, b2.nodeId AS to_blockId, fd.name AS mid_entity, fd.nodeId AS mid_entityId

        UNION ALL

        MATCH (b1:Block{nodeId:$nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->(c1)-[:DECLARES]->(m:Method)-[:RETURNS]->(c2)<-[:DECLARES]-(f2:File)<-[:f2c*]-(b2:Block)
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'RETURNS' AS rel_type, c1.name AS from_entity, c1.nodeId AS from_entityId, c1.SE_What AS from_what,
               c2.name AS to_entity, c2.nodeId AS to_entityId, c2.SE_What AS to_what,
               b2.name AS to_block, b2.nodeId AS to_blockId, m.name AS mid_entity, m.nodeId AS mid_entityId

        UNION ALL

        MATCH (b1:Block{nodeId:$nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->(c1)-[:DECLARES]->(inner1)-[:DECLARES]->(m1:Method)-[:CALLS]->(m2:Method)<-[:DECLARES]-(inner2)<-[:DECLARES]-(c2)<-[:DECLARES]-(f2:File)<-[:f2c*]-(b2:Block)
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'INNER_CALLS' AS rel_type, inner1.name AS from_entity, inner1.nodeId AS from_entityId, m1.SE_What AS from_what,
               inner2.name AS to_entity, inner2.nodeId AS to_entityId, m2.SE_What AS to_what,
               b2.name AS to_block, b2.nodeId AS to_blockId, m1.name AS mid_entity, m1.nodeId AS mid_entityId

        UNION ALL

        MATCH (b1:Block{nodeId:$nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->(c1)-[:DECLARES]->(target)<-[:ANNOTATES]-(anno:Annotation)<-[:DECLARES]-(f2:File)<-[:f2c*]-(b2:Block)
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2) AND (target:Method OR target:Field)
        RETURN 'ANNOTATES_MEMBER' AS rel_type, c1.name AS from_entity, c1.nodeId AS from_entityId, target.SE_What AS from_what,
               anno.name AS to_entity, anno.nodeId AS to_entityId, anno.SE_What AS to_what,
               b2.name AS to_block, b2.nodeId AS to_blockId, target.name AS mid_entity, target.nodeId AS mid_entityId

        UNION ALL

        MATCH (b1:Block{nodeId:$nodeId})-[:f2c*]->(f1:File)-[:DECLARES]->(c1)<-[:ANNOTATES]-(anno:Annotation)<-[:DECLARES]-(f2:File)<-[:f2c*]-(b2:Block)
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'ANNOTATES_CLASS' AS rel_type, c1.name AS from_entity, c1.nodeId AS from_entityId, c1.SE_What AS from_what,
               anno.name AS to_entity, anno.nodeId AS to_entityId, anno.SE_What AS to_what,
               b2.name AS to_block, b2.nodeId AS to_blockId, null AS mid_entity, null AS mid_entityId
        """
        query_called = """
        MATCH (b2:Block)-[:f2c*]->(f2:File)-[:DECLARES]->(m2:Method)-[:CALLS]->(m1:Method)<-[:DECLARES]-(c1)<-[:DECLARES]-(f1:File)<-[:f2c*]-(b1:Block{nodeId:$nodeId})
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'CALLS' AS rel_type, c1.name AS to_entity, c1.nodeId AS to_entityId, m1.SE_What AS to_what,
               m2.name AS from_entity, m2.nodeId AS from_entityId, m2.SE_What AS from_what,
               b2.name AS from_block, b2.nodeId AS from_blockId, null AS mid_entity, null AS mid_entityId

        UNION ALL

        MATCH (b2:Block)-[:f2c*]->(f2:File)-[:DECLARES]->(c2)-[:EXTENDS]->(c1)<-[:DECLARES]-(f1:File)<-[:f2c*]-(b1:Block{nodeId:$nodeId})
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'EXTENDS' AS rel_type, c1.name AS to_entity, c1.nodeId AS to_entityId, c1.SE_What AS to_what,
               c2.name AS from_entity, c2.nodeId AS from_entityId, c2.SE_What AS from_what,
               b2.name AS from_block, b2.nodeId AS from_blockId, null AS mid_entity, null AS mid_entityId

        UNION ALL

        MATCH (b2:Block)-[:f2c*]->(f2:File)-[:DECLARES]->(c2)-[:IMPLEMENTS]->(i1:Interface)<-[:DECLARES]-(f1:File)<-[:f2c*]-(b1:Block{nodeId:$nodeId})
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'IMPLEMENTS' AS rel_type, i1.name AS to_entity, i1.nodeId AS to_entityId, i1.SE_What AS to_what,
               c2.name AS from_entity, c2.nodeId AS from_entityId, c2.SE_What AS from_what,
               b2.name AS from_block, b2.nodeId AS from_blockId, null AS mid_entity, null AS mid_entityId

        UNION ALL

        MATCH (b2:Block)-[:f2c*]->(f2:File)-[:DECLARES]->(c2)-[:DECLARES]->(m:Method)-[:USES]->(c1)<-[:DECLARES]-(f1:File)<-[:f2c*]-(b1:Block{nodeId:$nodeId})
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'USES_CLASS' AS rel_type, c1.name AS to_entity, c1.nodeId AS to_entityId, c1.SE_What AS to_what,
               c2.name AS from_entity, c2.nodeId AS from_entityId, c2.SE_What AS from_what,
               b2.name AS from_block, b2.nodeId AS from_blockId, m.name AS mid_entity, m.nodeId AS mid_entityId

        UNION ALL

        MATCH (b2:Block)-[:f2c*]->(f2:File)-[:DECLARES]->(c2)-[:DECLARES]->(m:Method)-[:USES]->(fd:Field)<-[:DECLARES]-(c1)<-[:DECLARES]-(f1:File)<-[:f2c*]-(b1:Block{nodeId:$nodeId})
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'USES_FIELD' AS rel_type, c1.name AS to_entity, c1.nodeId AS to_entityId, fd.SE_What AS to_what,
               c2.name AS from_entity, c2.nodeId AS from_entityId, c2.SE_What AS from_what,
               b2.name AS from_block, b2.nodeId AS from_blockId, fd.name AS mid_entity, fd.nodeId AS mid_entityId

        UNION ALL

        MATCH (b2:Block)-[:f2c*]->(f2:File)-[:DECLARES]->(c2)-[:DECLARES]->(fd:Field)-[:HAS_TYPE]->(c1)<-[:DECLARES]-(f1:File)<-[:f2c*]-(b1:Block{nodeId:$nodeId})
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'HAS_TYPE' AS rel_type, c1.name AS to_entity, c1.nodeId AS to_entityId, c1.SE_What AS to_what,
               c2.name AS from_entity, c2.nodeId AS from_entityId, c2.SE_What AS from_what,
               b2.name AS from_block, b2.nodeId AS from_blockId, fd.name AS mid_entity, fd.nodeId AS mid_entityId

        UNION ALL

        MATCH (b2:Block)-[:f2c*]->(f2:File)-[:DECLARES]->(c2)-[:DECLARES]->(m:Method)-[:RETURNS]->(c1)<-[:DECLARES]-(f1:File)<-[:f2c*]-(b1:Block{nodeId:$nodeId})
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'RETURNS' AS rel_type, c1.name AS to_entity, c1.nodeId AS to_entityId, c1.SE_What AS to_what,
               c2.name AS from_entity, c2.nodeId AS from_entityId, c2.SE_What AS from_what,
               b2.name AS from_block, b2.nodeId AS from_blockId, m.name AS mid_entity, m.nodeId AS mid_entityId

        UNION ALL

        MATCH (b2:Block)-[:f2c*]->(f2:File)-[:DECLARES]->(c2)-[:DECLARES]->(inner2)-[:DECLARES]->(m2:Method)-[:CALLS]->(m1:Method)<-[:DECLARES]-(inner1)<-[:DECLARES]-(c1)<-[:DECLARES]-(f1:File)<-[:f2c*]-(b1:Block{nodeId:$nodeId})
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'INNER_CALLS' AS rel_type, inner1.name AS to_entity, inner1.nodeId AS to_entityId, m1.SE_What AS to_what,
               inner2.name AS from_entity, inner2.nodeId AS from_entityId, m2.SE_What AS from_what,
               b2.name AS from_block, b2.nodeId AS from_blockId, m2.name AS mid_entity, m2.nodeId AS mid_entityId

        UNION ALL

        MATCH (b2:Block)-[:f2c*]->(f2:File)-[:DECLARES]->(c2)-[:DECLARES]->(target)<-[:ANNOTATES]-(anno:Annotation)<-[:DECLARES]-(f1:File)<-[:f2c*]-(b1:Block{nodeId:$nodeId})
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2) AND (target:Method OR target:Field)
        RETURN 'ANNOTATES_MEMBER' AS rel_type, target.name AS to_entity, target.nodeId AS to_entityId, target.SE_What AS to_what,
               anno.name AS from_entity, anno.nodeId AS from_entityId, anno.SE_What AS from_what,
               b2.name AS from_block, b2.nodeId AS from_blockId, target.name AS mid_entity, target.nodeId AS mid_entityId

        UNION ALL

        MATCH (b2:Block)-[:f2c*]->(f2:File)-[:DECLARES]->(anno:Annotation)-[:ANNOTATES]->(c1)<-[:DECLARES]-(f1:File)<-[:f2c*]-(b1:Block{nodeId:$nodeId})
        WHERE b1<>b2 AND (b1)<-[:f2c]-(:Block)-[:f2c]->(b2)
        RETURN 'ANNOTATES_CLASS' AS rel_type, c1.name AS to_entity, c1.nodeId AS to_entityId, c1.SE_What AS to_what,
               anno.name AS from_entity, anno.nodeId AS from_entityId, anno.SE_What AS from_what,
               b2.name AS from_block, b2.nodeId AS from_blockId, null AS mid_entity, null AS mid_entityId
        """
        result1, result2 = await asyncio.gather(
            neo4j_interface.execute_query(query_calls, {"nodeId": nodeId}),
            neo4j_interface.execute_query(query_called, {"nodeId": nodeId})
        )

        def _block(r):
            bid = r.get("to_blockId")
            return f"模块 {new_names.get(str(bid), r.get('to_block', '未知'))}(id:{bid})"
        def _block_from(r):
            bid = r.get("from_blockId")
            return f"模块 {new_names.get(str(bid), r.get('from_block', '未知'))}(id:{bid})"

        # ---- 逐条描述模板（仅用于组内只有1条记录时） ----
        REL_DESC = {
            "CALLS":             lambda r: f"该模块中 {r['from_entity']} 调用了{_block(r)}中的方法 {r['to_entity']}",
            "INNER_CALLS":       lambda r: f"该模块内部类 {r['from_entity']} 的方法 {r['mid_entity']} 调用了{_block(r)}中内部类 {r['to_entity']} 的方法",
            "EXTENDS":           lambda r: f"该模块中 {r['from_entity']} 继承了{_block(r)}中的类 {r['to_entity']}",
            "IMPLEMENTS":        lambda r: f"该模块中 {r['from_entity']} 实现了{_block(r)}中的接口 {r['to_entity']}",
            "USES_CLASS":        lambda r: f"该模块中 {r['from_entity']} 的方法 {r['mid_entity']} 使用了{_block(r)}中的类 {r['to_entity']}",
            "USES_FIELD":        lambda r: f"该模块中 {r['from_entity']} 的方法通过字段 {r['mid_entity']} 依赖了{_block(r)}中的 {r['to_entity']}",
            "HAS_TYPE":          lambda r: f"该模块中 {r['from_entity']} 的字段 {r['mid_entity']} 类型引用了{_block(r)}中的 {r['to_entity']}",
            "RETURNS":           lambda r: f"该模块中 {r['from_entity']} 的方法 {r['mid_entity']} 返回类型为{_block(r)}中的 {r['to_entity']}",
            "ANNOTATES_MEMBER":  lambda r: f"{_block(r)}中的注解 {r['to_entity']} 作用于该模块 {r['from_entity']} 的成员 {r['mid_entity']}",
            "ANNOTATES_CLASS":   lambda r: f"{_block(r)}中的注解 {r['to_entity']} 作用于该模块中的 {r['from_entity']}",
        }
        REL_DESC_CALLED = {
            "CALLS":             lambda r: f"{_block_from(r)}中的方法 {r['from_entity']} 调用了该模块中 {r['to_entity']} 的方法",
            "INNER_CALLS":       lambda r: f"{_block_from(r)}中内部类 {r['from_entity']} 的方法 {r['mid_entity']} 调用了该模块内部类 {r['to_entity']} 的方法",
            "EXTENDS":           lambda r: f"{_block_from(r)}中的 {r['from_entity']} 继承了该模块中的类 {r['to_entity']}",
            "IMPLEMENTS":        lambda r: f"{_block_from(r)}中的 {r['from_entity']} 实现了该模块中的接口 {r['to_entity']}",
            "USES_CLASS":        lambda r: f"{_block_from(r)}中 {r['from_entity']} 的方法 {r['mid_entity']} 使用了该模块中的类 {r['to_entity']}",
            "USES_FIELD":        lambda r: f"{_block_from(r)}中 {r['from_entity']} 的方法通过字段 {r['mid_entity']} 依赖了该模块中的 {r['to_entity']}",
            "HAS_TYPE":          lambda r: f"{_block_from(r)}中 {r['from_entity']} 的字段 {r['mid_entity']} 类型引用了该模块中的 {r['to_entity']}",
            "RETURNS":           lambda r: f"{_block_from(r)}中 {r['from_entity']} 的方法 {r['mid_entity']} 返回类型为该模块中的 {r['to_entity']}",
            "ANNOTATES_MEMBER":  lambda r: f"该模块中的注解 {r['from_entity']} 作用于{_block_from(r)}中 {r['to_entity']} 的成员 {r['mid_entity']}",
            "ANNOTATES_CLASS":   lambda r: f"该模块中的注解 {r['from_entity']} 作用于{_block_from(r)}中的 {r['to_entity']}",
        }

        # ---- 分组头模板（组内 >= 2 条时使用） ----
        # result1 方向：该模块 → 其他模块
        GROUP_HEADER = {
            "CALLS":             lambda blk: f"该模块中以下方法调用了{blk}中的方法：",
            "INNER_CALLS":       lambda blk: f"该模块中以下内部类方法调用了{blk}中内部类的方法：",
            "EXTENDS":           lambda blk: f"该模块中以下类继承了{blk}中的类：",
            "IMPLEMENTS":        lambda blk: f"该模块中以下类实现了{blk}中的接口：",
            "USES_CLASS":        lambda blk: f"该模块中以下方法使用了{blk}中的类：",
            "USES_FIELD":        lambda blk: f"该模块中以下方法通过字段依赖了{blk}中的类：",
            "HAS_TYPE":          lambda blk: f"该模块中以下字段类型引用了{blk}中的类：",
            "RETURNS":           lambda blk: f"该模块中以下方法返回类型属于{blk}：",
            "ANNOTATES_MEMBER":  lambda blk: f"{blk}中的注解作用于该模块的以下成员：",
            "ANNOTATES_CLASS":   lambda blk: f"{blk}中的注解作用于该模块中的以下类：",
        }
        # result2 方向：其他模块 → 该模块
        GROUP_HEADER_CALLED = {
            "CALLS":             lambda blk: f"{blk}中以下方法调用了该模块中的方法：",
            "INNER_CALLS":       lambda blk: f"{blk}中以下内部类方法调用了该模块中内部类的方法：",
            "EXTENDS":           lambda blk: f"{blk}中以下类继承了该模块中的类：",
            "IMPLEMENTS":        lambda blk: f"{blk}中以下类实现了该模块中的接口：",
            "USES_CLASS":        lambda blk: f"{blk}中以下方法使用了该模块中的类：",
            "USES_FIELD":        lambda blk: f"{blk}中以下方法通过字段依赖了该模块中的类：",
            "HAS_TYPE":          lambda blk: f"{blk}中以下字段类型引用了该模块中的类：",
            "RETURNS":           lambda blk: f"{blk}中以下方法返回类型属于该模块：",
            "ANNOTATES_MEMBER":  lambda blk: f"该模块中的注解作用于{blk}的以下成员：",
            "ANNOTATES_CLASS":   lambda blk: f"该模块中的注解作用于{blk}中的以下类：",
        }

        # ---- 每行格式：from_entity.mid_entity → to_entity ----
        def _item_line(r):
            fe = r.get("from_entity", "")
            me = r.get("mid_entity")
            te = r.get("to_entity", "")
            rel = r.get("rel_type", "")
            if rel == "USES_FIELD":
                # c1.m → c2.fd  (mid_entity=fd, to_entity=c2, from_entity=c1)
                return f"  - {fe} → {te}.{me}" if me else f"  - {fe} → {te}"
            elif rel in ("ANNOTATES_MEMBER", "ANNOTATES_CLASS"):
                # anno → c1.target
                return f"  - {te} → {fe}.{me}" if me else f"  - {te} → {fe}"
            elif me:
                # c1.m → c2
                return f"  - {fe}.{me} → {te}"
            else:
                # m1 → m2 or c1 → c2
                return f"  - {fe} → {te}"

        def _item_line_called(r):
            fe = r.get("from_entity", "")
            me = r.get("mid_entity")
            te = r.get("to_entity", "")
            rel = r.get("rel_type", "")
            if rel == "USES_FIELD":
                return f"  - {fe} → {te}.{me}" if me else f"  - {fe} → {te}"
            elif rel in ("ANNOTATES_MEMBER", "ANNOTATES_CLASS"):
                return f"  - {fe} → {te}.{me}" if me else f"  - {fe} → {te}"
            elif me:
                return f"  - {fe}.{me} → {te}"
            else:
                return f"  - {fe} → {te}"

        # ---- 分组并生成 relationship 文本 ----
        from collections import defaultdict

        relationship = [f"下面是{name}模块和其他兄弟模块之间的关系，接下来我们用'该模块'指代{name}模块。\n"]
        se_what_map = {}

        # 收集 se_what_map
        for record in result1 + result2:
            if record.get("from_what"):
                se_what_map[record["from_entity"]] = record["from_what"]
            if record.get("to_what"):
                se_what_map[record["to_entity"]] = record["to_what"]

        # result1 分组：按 (rel_type, to_blockId) 分组
        groups1 = defaultdict(list)
        for record in result1:
            rel_type = record.get("rel_type", "UNKNOWN")
            block_id = record.get("to_blockId")
            groups1[(rel_type, block_id)].append(record)

        for (rel_type, block_id), records in groups1.items():
            if len(records) == 1:
                desc_fn = REL_DESC.get(rel_type)
                if desc_fn:
                    relationship.append(desc_fn(records[0]))
            else:
                blk_str = f"模块 {new_names.get(str(block_id), str(block_id))}(id:{block_id})"
                header_fn = GROUP_HEADER.get(rel_type)
                if header_fn:
                    lines = [header_fn(blk_str)]
                    for r in records:
                        lines.append(_item_line(r))
                    relationship.append("\n".join(lines))

        # result2 分组：按 (rel_type, from_blockId) 分组
        groups2 = defaultdict(list)
        for record in result2:
            rel_type = record.get("rel_type", "UNKNOWN")
            block_id = record.get("from_blockId")
            groups2[(rel_type, block_id)].append(record)

        for (rel_type, block_id), records in groups2.items():
            if len(records) == 1:
                desc_fn = REL_DESC_CALLED.get(rel_type)
                if desc_fn:
                    relationship.append(desc_fn(records[0]))
            else:
                blk_str = f"模块 {new_names.get(str(block_id), str(block_id))}(id:{block_id})"
                header_fn = GROUP_HEADER_CALLED.get(rel_type)
                if header_fn:
                    lines = [header_fn(blk_str)]
                    for r in records:
                        lines.append(_item_line_called(r))
                    relationship.append("\n".join(lines))

        # 附加语义说明
        if se_what_map:
            relationship.append("\n--- 组件语义说明 ---")
            for entity_name, what in se_what_map.items():
                relationship.append(f"  {entity_name}: {what}")


        parsed = await invoke_and_parse(generate_relationship_chain, {"cross_module_calls": "\n".join(relationship)})
        section5_module_relation = {"markdown": parsed["markdown"], "neo4j_id": parsed["mapping"]}
        return {"section5_module_relation": section5_module_relation}
    
    async def data_uml(state: BlockState) -> BlockState:
        query = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c*]->(f:File)-[:DECLARES]->(c:Class|Interface)
        RETURN c.name AS class_name, c.layer_num AS layer_num
        ORDER BY layer_num DESC
        LIMIT 7
        """
        source_id_list = state.get("source_id_list", [])
        result = await neo4j_interface.execute_query(query, {"nodeId": nodeId})
        id_list = ["Class&Interface"]
        for record in result:
            id_list.append(record.get("class_name"))
        app = chart_app(llm_interface, neo4j_interface, node_list=id_list, type="uml", skeleton=skeleton)
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
        # output = ""
        # output += state.get("section1_summary", {"markdown": ""}).get("markdown", "") + "\n"
        # output += state.get("section2_core_components", {"markdown": ""}).get("markdown", "") + "\n"
        # output += state.get("section3_architecture_diagram", {"markdown": ""}).get("markdown", "") + "\n"
        # main_control_flow = state.get("section4_main_control_flow", [])
        # for item in main_control_flow:
        #     output += item.get("mermaid", "") + "\n"
        # output += state.get("section5_module_relation", {"markdown": ""}).get("markdown", "") + "\n"
        # output += state.get("section6_data_uml", {"mermaid": ""}).get("mermaid", "") + "\n"
        os.makedirs(os.path.dirname(write_path), exist_ok=True)
        with open(write_path, "w", encoding="utf-8") as f:
            # f.write(output)
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


    app = graph.compile()
    return app

# ====================== 3. 独立运行入口 ======================
async def main():
    load_dotenv()
    print("=== 独立运行叶子Block文档生成工作流 ===")

    llm = LLMInterface()  # 模型/提供商从 .env 的 LLM_MODEL / LLM_PROVIDER 读取
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
    block_target = json.loads(get_file(os.path.join(PROJECT_ROOT, "internal_result", "file_leaves.json")))

    # # ============ 单个Block测试模式（已注释） ============
    # # 取第一个block进行测试
    # first_block_id, first_block_path = list(block_target.items())[40]

    # first_block_name = new_names.get(str(first_block_id), f"Block_{first_block_id}")

    # print(f"[INFO] 测试模式: 只处理第一个Block")
    # print(f"[INFO] Block ID: {first_block_id}, Name: {first_block_name}")

    # try:
    #     id_name_path = {
    #         "block_id": first_block_id,
    #         "block_name": first_block_name,
    #         "block_path": first_block_path
    #     }

    #     app = block_module_workflow(llm, neo4j, id_name_path)
    #     result = await app.ainvoke(
    #         {},
    #         config={"configurable": {"thread_id": f"block-{first_block_id}"}}
    #     )
    #     print(f"[INFO] 测试完成: {first_block_name}")
    # except Exception as e:
    #     print(f"[ERR] 测试失败: {first_block_name} - {str(e)}")
    #     import traceback
    #     traceback.print_exc()

    # ============ 并发逻辑 ============
    # 准备所有需要处理的Block
    blocks_to_process = []
    for block_id, block_path in block_target.items():
        block_name = new_names.get(str(block_id), f"Block_{block_id}")
        blocks_to_process.append({
            "block_id": block_id,
            "block_name": block_name,
            "block_path": block_path
        })

    print(f"[INFO] 共有 {len(blocks_to_process)} 个叶子Block需要生成文档")

    # 从环境变量读取最大并发数
    max_concurrent = int(os.environ.get("MAX_CONCURRENT_BLOCKS", "10"))
    print(f"[INFO] 最大并发数: {max_concurrent}")

    # 创建信号量控制并发
    semaphore = asyncio.Semaphore(max_concurrent)

    max_retries_per_block = 2

    async def process_single_block(block_info: Dict, index: int):
        """
        处理单个Block的文档生成，失败时自动重试最多max_retries_per_block次
        """
        async with semaphore:
            block_id = block_info["block_id"]
            block_name = block_info["block_name"]
            block_path = block_info["block_path"]

            print(f"  [{index}/{len(blocks_to_process)}] 开始生成: {block_name} ({block_id})")

            last_error = None
            for attempt in range(1, max_retries_per_block + 1):
                try:
                    id_name_path = {
                        "block_id": block_id,
                        "block_name": block_name,
                        "block_path": block_path
                    }

                    app = block_module_workflow(llm, neo4j, id_name_path)

                    result = await app.ainvoke(
                        {},
                        config={"configurable": {"thread_id": f"block-{block_id}-attempt{attempt}"}}
                    )

                    print(f"  [{index}/{len(blocks_to_process)}] 完成: {block_name}" + (f" (第{attempt}次尝试)" if attempt > 1 else ""))
                    block_logger.info(f"SUCCESS | {block_name} ({block_id}) | 第{attempt}次尝试")
                    return {
                        "block_id": block_id,
                        "block_name": block_name,
                        "success": True,
                        "result": result
                    }

                except Exception as e:
                    last_error = e
                    print(f"  [{index}/{len(blocks_to_process)}] 第{attempt}/{max_retries_per_block}次失败: {block_name} - {str(e)}")

            print(f"  [{index}/{len(blocks_to_process)}] 最终失败（{max_retries_per_block}次尝试后）: {block_name}")
            block_logger.info(f"FAILED  | {block_name} ({block_id}) | {str(last_error)}")
            return {
                "block_id": block_id,
                "block_name": block_name,
                "success": False,
                "error": str(last_error)
            }

    # 并发执行所有Block的文档生成
    print(f"[INFO] 开始并发生成文档...")
    tasks = [
        process_single_block(block, i + 1)
        for i, block in enumerate(blocks_to_process)
    ]

    results = await asyncio.gather(*tasks)

    # 统计结果
    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count

    print(f"\n[INFO] 文档生成完成:")
    print(f"  - 成功: {success_count}/{len(blocks_to_process)}")
    print(f"  - 失败: {fail_count}/{len(blocks_to_process)}")

    if fail_count > 0:
        print(f"\n[WARN] 失败的Block:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['block_name']} ({r['block_id']}): {r['error']}")

    neo4j.close()
    print("[INFO] 工作流执行完成")

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())

    

    

    