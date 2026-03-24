"""
混合型Block工作流

用于同时拥有直连File和子Block的Block节点。
章节结构：
  1. 模块概述 — LLM生成，综合直连File和子Block信息
  2. 核心组件与子模块介绍 — 直连File中的类/接口 + 子Block列表及功能说明
  3. 模块内架构图 — 下两层范围的依赖关系（LLM生成mermaid）
  4. 关键控制流 — 直连File中最关键方法的CFG（chart_app type=cfg）
  5. 模块关系 — 占位（TODO）
  6. 数据结构与模块关系UML — 直连File + 子Block的类，namespace分组标注归属（chart_app type=hybrid_uml）
"""

import os
import sys
import json
import asyncio
from typing import Any, Dict, List
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from interfaces.data_master import get_file
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from chains.common_chains import ChainFactory
from chains.prompts.block_doc_prompt import MODULE_CHART_PROMPT, BLOCK_RELATIONSHIP_PROMPT, HYBRID_BLOCK_OVERVIEW_PROMPT, ARCHITECTURE_DESC_PROMPT
from graph.four_chart import chart_app

new_names = json.loads(get_file(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "graph", "block_new_names.json"
)))


# ====================== 1. 状态定义 ======================
class HybridBlockState(TypedDict, total=False):
    section1_summary: Dict
    section2_components_and_children: Dict
    section3_architecture_diagram: Dict
    section4_main_control_flow: list
    section5_module_relation: Dict
    section6_data_uml: Dict
    source_id_list: List
    uml_token_stats: Dict


# ====================== 2. 工作流定义 ======================
def hybrid_block_workflow(
    llm_interface: LLMInterface,
    neo4j_interface: Neo4jInterface,
    id_name_path: Dict,
    skeleton: bool = False
):
    generate_summary_chain = ChainFactory.create_generic_chain(llm_interface, HYBRID_BLOCK_OVERVIEW_PROMPT)
    generate_module_chart_chain = ChainFactory.create_generic_chain(llm_interface, MODULE_CHART_PROMPT)
    generate_relationship_chain = ChainFactory.create_generic_chain(llm_interface, BLOCK_RELATIONSHIP_PROMPT)
    generate_arch_desc_chain = ChainFactory.create_generic_chain(llm_interface, ARCHITECTURE_DESC_PROMPT)

    name = id_name_path["block_name"]
    write_path = id_name_path["block_path"] + ".json"
    nodeId = int(id_name_path["block_id"])

    # ---- 章节1: 模块概述 ----
    async def generate_summary(state: HybridBlockState) -> HybridBlockState:
        # 查询直连File（不穿透子Block）
        query_direct_files = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c]->(f:File)
        RETURN b.module_explaination AS block_explanation,
               f.module_explaination AS file_explanation,
               f.name AS file_name
        """
        # 查询子Block信息
        query_child_blocks = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c]->(child:Block)
        RETURN child.name AS child_name,
               child.nodeId AS child_nodeId,
               child.module_explaination AS child_explanation
        ORDER BY child.name
        """
        file_result, child_result = await asyncio.gather(
            neo4j_interface.execute_query(query_direct_files, {"nodeId": nodeId}),
            neo4j_interface.execute_query(query_child_blocks, {"nodeId": nodeId})
        )

        block_explanation = "暂无说明"
        direct_files = []
        if file_result:
            block_explanation = file_result[0].get("block_explanation", "暂无说明")
            for record in file_result:
                file_name = record.get("file_name", "未知文件")
                file_exp = record.get("file_explanation", "暂无说明")
                direct_files.append(f"{file_name}: {file_exp}")

        child_modules = []
        for record in child_result:
            child_name = new_names.get(str(record["child_nodeId"]), record["child_name"])
            child_exp = record.get("child_explanation") or "暂无说明"
            child_modules.append(f"{child_name}: {child_exp}")

        section1_content = await generate_summary_chain.ainvoke({
            "block_name": name,
            "block_explaination": block_explanation,
            "direct_files": "\n".join(direct_files),
            "child_modules": "\n".join(child_modules)
        })
        print("[hybrid] section1 done")
        return {"section1_summary": {"markdown": section1_content, "neo4j_id": {"1": nodeId}}}

    # ---- 章节2: 核心组件与子模块介绍 ----
    async def generate_components_and_children(state: HybridBlockState) -> HybridBlockState:
        # 查询直连File中的组件
        query_components = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c]->(f:File)-[:DECLARES]->(com)
        OPTIONAL MATCH (f)<-[:CONTAINS]-(p:Package)
        RETURN labels(com) AS com_labels, com.name AS com_name,
               com.SE_How AS how, com.SE_What AS what, com.SE_When AS when,
               f.name AS file_name, p.name AS package_name,
               com.nodeId AS com_nodeId, f.nodeId AS file_nodeId, p.nodeId AS package_nodeId
        """
        # 查询子Block
        query_children = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c]->(child:Block)
        RETURN child.nodeId AS nodeId,
               child.name AS name,
               child.module_explaination AS module_explaination
        ORDER BY child.name
        """
        comp_result, child_result = await asyncio.gather(
            neo4j_interface.execute_query(query_components, {"nodeId": nodeId}),
            neo4j_interface.execute_query(query_children, {"nodeId": nodeId})
        )

        content = ["## 2. 核心组件与子模块介绍\n"]
        neo4j_id = {}
        idx = 1

        # 2.1 核心组件部分
        if comp_result:
            content.append("### 2.1 核心组件\n")
            for record in comp_result:
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
                content.append(f"#### 2.1.{idx} {com_name}({com_labels})\n")
                content.append(f"{com_name}属于文件{file_name}, 该文件属于包{package_name}\n")
                content.append(f"- **主要职责**\n  - {what}\n")
                content.append(f"- **实现方式**\n  - {how}\n")
                content.append(f"- **使用时机**\n  - {when}\n")
                neo4j_id[f"2.1.{idx}"] = [com_nodeId, file_nodeId, package_nodeId]
                idx += 1

        # 2.2 子模块部分
        if child_result:
            content.append("### 2.2 子模块简要介绍\n")
            content.append("> 点击子模块标题可跳转至对应子模块的详细wiki说明\n")
            for child_idx, child in enumerate(child_result, 1):
                child_name = new_names.get(str(child["nodeId"]), child["name"])
                child_exp = child.get("module_explaination") or "暂无说明"
                content.append(f"#### 2.2.{child_idx} {child_name}\n")
                content.append(f"{child_exp}\n")
                neo4j_id[f"2.2.{child_idx}"] = [child["nodeId"]]

        print("[hybrid] section2 done")
        return {"section2_components_and_children": {"markdown": "\n".join(content), "neo4j_id": neo4j_id}}

    # ---- 章节3: 模块内架构图（下两层：直连File + 子Block及其下的File和Block） ----
    async def generate_architecture_diagram(state: HybridBlockState) -> HybridBlockState:
        # 查询两层范围内所有File之间的依赖关系
        query_relationship = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c*1..2]->(f1:File)-[:DECLARES]->()-[r*1..5]->(c)<-[:DECLARES]-(f2:File)<-[:f2c*1..2]-(b)
        WHERE NONE(rel IN r WHERE type(rel) IN ['CONTAINS', 'DIR_INCLUDES', 'f2c']) AND f1 <> f2
        RETURN f1.nodeId AS from_fileId, f1.name AS from_fileName,
               f2.nodeId AS to_fileId, f2.name AS to_fileName
        """
        result = await neo4j_interface.execute_query(query_relationship, {"nodeId": nodeId})
        rel = {}
        id_name_map = {}
        for record in result:
            id_name_map[record["from_fileId"]] = record["from_fileName"]
            id_name_map[record["to_fileId"]] = record["to_fileName"]
            if record["from_fileId"] not in rel:
                rel[record["from_fileId"]] = []
            rel[record["from_fileId"]].append(record["to_fileId"])
        relationship = set()
        for key, values in rel.items():
            for value in values:
                relationship.add(f"{id_name_map[key]} 指向 {id_name_map[value]}")

        # 构建两层树结构（包含直连File、子Block、子Block下的File和Block）
        query_paths = """
        MATCH (root:Block {nodeId: $nodeId})
        MATCH path = (root)-[:f2c*1..2]->(target)
        WHERE target:File OR target:Block
        WITH nodes(path) AS path_nodes
        UNWIND range(0, size(path_nodes)-2) AS i
        WITH path_nodes[i] AS parent, path_nodes[i+1] AS child
        RETURN DISTINCT parent.nodeId AS parent_id, parent.name AS parent_name,
               child.nodeId AS child_id, child.name AS child_name
        """
        path_results = await neo4j_interface.execute_query(query_paths, {"nodeId": nodeId})

        f2c_map = {}
        node_name_map = {}
        for record in path_results:
            parent_id = record['parent_id']
            child_id = record['child_id']
            node_name_map[parent_id] = record['parent_name']
            node_name_map[child_id] = record['child_name']
            if parent_id not in f2c_map:
                f2c_map[parent_id] = []
            if child_id not in [c for c in f2c_map[parent_id]]:
                f2c_map[parent_id].append(child_id)

        def build_tree(nid) -> dict:
            raw_name = node_name_map.get(nid, str(nid))
            display_name = new_names.get(str(nid), raw_name)
            return {
                "name": display_name,
                "id": nid,
                "path": raw_name,
                "children": [build_tree(cid) for cid in f2c_map.get(nid, [])]
            }

        tree = build_tree(nodeId)
        project_information = tree.get("children", [])

        mermaid_result = await generate_module_chart_chain.ainvoke({
            "project_information": project_information,
            "relationship": "\n".join(relationship)
        })
        parsed = json.loads(mermaid_result)
        rel_text = "\n".join(relationship)
        arch_desc = await generate_arch_desc_chain.ainvoke({
            "chart_mermaid": parsed["mermaid"],
            "project_information": json.dumps(project_information, ensure_ascii=False, indent=2),
            "relationship": rel_text
        })
        markdown_content = "## 3. 模块内文件架构图\n```mermaid\n" + parsed["mermaid"] + "```\n" + arch_desc + "\n"
        print("[hybrid] section3 done")
        return {"section3_architecture_diagram": {"markdown": markdown_content, "neo4j_id": parsed["mapping"]}}

    # ---- 章节4: 关键控制流（仅直连File中的方法） ----
    async def main_control_flow(state: HybridBlockState) -> HybridBlockState:
        query = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c]->(f:File)-[:DECLARES]->(c)-[:DECLARES*]->(m:Method)
        RETURN c.name AS class_name, m.name AS method_name,
               m.nodeId AS method_nodeId, m.layer_num AS layer_num
        ORDER BY layer_num DESC
        LIMIT 1
        """
        result = await neo4j_interface.execute_query(query, {"nodeId": nodeId})
        section4 = [{"markdown": "## 4. 关键控制流分析\n", "neo4j_id": {}}]
        source_id_list = state.get("source_id_list", [])
        for idx, method in enumerate(result, 1):
            content = []
            class_name = method.get("class_name", "未知类")
            method_name = method.get("method_name", "未知方法")
            method_nodeId = method.get("method_nodeId")
            content.append(f"### 4.{idx} {class_name}.{method_name} 控制流分析\n")
            app = chart_app(llm_interface, neo4j_interface, node_list=[method_nodeId], type="cfg")
            cfg_result = await app.ainvoke(
                {},
                config={"configurable": {"thread_id": f"{name}-{class_name}.{method_name}-cfg"}}
            )
            content.append(cfg_result["output"])
            mapping = cfg_result["mapping"]
            source_id_list.extend(cfg_result["id_list"])
            section4.append({"mermaid": "".join(content), "mapping": mapping})
        print("[hybrid] section4 done")
        return {"section4_main_control_flow": section4, "source_id_list": source_id_list}

    # ---- 章节5: 模块关系（与兄弟模块的依赖关系） ----
    async def module_relation(state: HybridBlockState) -> HybridBlockState:
        from collections import defaultdict

        # 正向：当前模块 → 兄弟模块
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

        # 反向：兄弟模块 → 当前模块
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

        if not result1 and not result2:
            print("[hybrid] section5 skipped (no cross-module relations)")
            return {"section5_module_relation": {
                "markdown": "## 5. 模块关系\n\n该模块与兄弟模块之间没有直接的代码依赖关系。\n",
                "neo4j_id": {}
            }}

        def _block(r):
            bid = r.get("to_blockId")
            return f"模块 {new_names.get(str(bid), r.get('to_block', '未知'))}(id:{bid})"
        def _block_from(r):
            bid = r.get("from_blockId")
            return f"模块 {new_names.get(str(bid), r.get('from_block', '未知'))}(id:{bid})"

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

        def _item_line(r):
            fe, me, te, rel = r.get("from_entity", ""), r.get("mid_entity"), r.get("to_entity", ""), r.get("rel_type", "")
            if rel == "USES_FIELD":
                return f"  - {fe} → {te}.{me}" if me else f"  - {fe} → {te}"
            elif rel in ("ANNOTATES_MEMBER", "ANNOTATES_CLASS"):
                return f"  - {te} → {fe}.{me}" if me else f"  - {te} → {fe}"
            elif me:
                return f"  - {fe}.{me} → {te}"
            else:
                return f"  - {fe} → {te}"

        def _item_line_called(r):
            fe, me, te, rel = r.get("from_entity", ""), r.get("mid_entity"), r.get("to_entity", ""), r.get("rel_type", "")
            if rel == "USES_FIELD":
                return f"  - {fe} → {te}.{me}" if me else f"  - {fe} → {te}"
            elif rel in ("ANNOTATES_MEMBER", "ANNOTATES_CLASS"):
                return f"  - {fe} → {te}.{me}" if me else f"  - {fe} → {te}"
            elif me:
                return f"  - {fe}.{me} → {te}"
            else:
                return f"  - {fe} → {te}"

        # 分组并生成关系文本
        relationship = [f"下面是{name}模块和其他兄弟模块之间的关系，接下来我们用'该模块'指代{name}模块。\n"]
        se_what_map = {}

        for record in result1 + result2:
            if record.get("from_what"):
                se_what_map[record["from_entity"]] = record["from_what"]
            if record.get("to_what"):
                se_what_map[record["to_entity"]] = record["to_what"]

        # result1 分组：按 (rel_type, to_blockId) 分组
        groups1 = defaultdict(list)
        for record in result1:
            groups1[(record.get("rel_type", "UNKNOWN"), record.get("to_blockId"))].append(record)

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
            groups2[(record.get("rel_type", "UNKNOWN"), record.get("from_blockId"))].append(record)

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

        print("[hybrid] section5 cross-module relations:")
        print("\n".join(relationship))

        markdown_result = await generate_relationship_chain.ainvoke({"cross_module_calls": "\n".join(relationship)})
        parsed = json.loads(markdown_result)
        section5_module_relation = {"markdown": parsed["markdown"], "neo4j_id": parsed["mapping"]}
        print("[hybrid] section5 done")
        return {"section5_module_relation": section5_module_relation}

    # ---- 章节6: 数据结构与模块关系UML（直连File + 子Block下的类，namespace分组） ----
    async def data_uml(state: HybridBlockState) -> HybridBlockState:
        # 查直连File的类
        query_direct = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c]->(f:File)-[:DECLARES]->(c:Class|Interface)
        RETURN c.name AS class_name, '本模块' AS source_label
        """
        # 查子Block下的类
        query_child = """
        MATCH (b:Block {nodeId: $nodeId})-[:f2c]->(child:Block)-[:f2c*]->(f:File)-[:DECLARES]->(c:Class|Interface)
        RETURN c.name AS class_name, child.nodeId AS child_nodeId, child.name AS child_name
        """
        source_id_list = state.get("source_id_list", [])
        direct_result, child_result = await asyncio.gather(
            neo4j_interface.execute_query(query_direct, {"nodeId": nodeId}),
            neo4j_interface.execute_query(query_child, {"nodeId": nodeId})
        )

        if not direct_result and not child_result:
            print("[hybrid] section6 skipped (no classes)")
            return {"section6_data_uml": {"mermaid": "## 6. 数据结构与模块关系\n\n> 该模块及子模块中无Class/Interface定义\n"}}

        # 构建 class_source_map 和 id_list
        id_list = ["Class&Interface"]
        class_source_map = {}
        seen = set()
        for record in direct_result:
            cname = record.get("class_name")
            if cname not in seen:
                id_list.append(cname)
                class_source_map[cname] = "__direct__"
                seen.add(cname)
        for record in child_result:
            cname = record.get("class_name")
            child_label = new_names.get(str(record["child_nodeId"]), record["child_name"])
            if cname not in seen:
                id_list.append(cname)
                class_source_map[cname] = child_label
                seen.add(cname)

        # 调试：将hybrid UML的输入写入文件
        debug_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "graph", "hybrid_uml_workflow_input.txt")
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(f"=== id_list ({len(id_list)-1} classes) ===\n")
            f.write(json.dumps(id_list, ensure_ascii=False, indent=2))
            f.write(f"\n\n=== class_source_map ===\n")
            f.write(json.dumps(class_source_map, ensure_ascii=False, indent=2))
        print(f"[DEBUG] hybrid UML workflow输入已写入 {debug_path}")

        app = chart_app(llm_interface, neo4j_interface, node_list=id_list, type="hybrid_uml", skeleton=skeleton, class_source_map=class_source_map)
        uml_result = await app.ainvoke(
            {},
            config={"configurable": {"thread_id": f"{name}-hybrid-uml"}}
        )
        module_data = uml_result["output"]
        mapping = uml_result["mapping"]
        source_id_list.extend(uml_result["id_list"])
        section6_mermaid = "## 6. 核心类与子模块类关系图\n" + module_data
        section6 = {"mermaid": section6_mermaid, "mapping": mapping}
        ret = {"section6_data_uml": section6, "source_id_list": source_id_list}
        if uml_result.get("uml_token_stats"):
            ret["uml_token_stats"] = uml_result["uml_token_stats"]
        print("[hybrid] section6 done")
        return ret

    # ---- 最终输出 ----
    async def generate_final_output(state: HybridBlockState) -> HybridBlockState:
        print(f"[hybrid][final_output] state keys: {list(state.keys())}")
        content = {"wiki": [
            state.get("section1_summary", {"markdown": ""}),
            state.get("section2_components_and_children", {"markdown": ""}),
            state.get("section3_architecture_diagram", {"markdown": ""}),
        ]}
        content["wiki"].extend(state.get("section4_main_control_flow", []))
        content["wiki"].append(state.get("section5_module_relation", {"markdown": ""}))
        content["wiki"].append(state.get("section6_data_uml", {"mermaid": ""}))
        content["source_id_list"] = state.get("source_id_list", [])
        os.makedirs(os.path.dirname(write_path), exist_ok=True)
        with open(write_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=4)
        print(f"[hybrid] final output saved: {write_path}")
        return {}

    def should_generate_output(state: HybridBlockState) -> str:
        required_keys = [
            "section1_summary",
            "section2_components_and_children",
            "section3_architecture_diagram",
            "section4_main_control_flow",
            "section5_module_relation",
            "section6_data_uml",
        ]
        if all(key in state and state[key] for key in required_keys):
            return "generate_final_output"
        return "wait"

    # ====================== 构建状态图 ======================
    graph = StateGraph(HybridBlockState)
    graph.add_node("generate_summary", generate_summary)
    graph.add_node("generate_components_and_children", generate_components_and_children)
    graph.add_node("generate_architecture_diagram", generate_architecture_diagram)
    graph.add_node("main_control_flow", main_control_flow)
    graph.add_node("module_relation", module_relation)
    graph.add_node("data_uml", data_uml)
    graph.add_node("generate_final_output", generate_final_output)

    # 流程：summary先执行，完成后2/3/4/5并发，4完成后触发6
    graph.set_entry_point("generate_summary")
    graph.add_edge("generate_summary", "generate_components_and_children")
    graph.add_edge("generate_summary", "generate_architecture_diagram")
    graph.add_edge("generate_summary", "main_control_flow")
    graph.add_edge("generate_summary", "module_relation")
    graph.add_edge("main_control_flow", "data_uml")

    # 所有分支完成后汇聚到final_output
    for node_name in [
        "generate_components_and_children",
        "generate_architecture_diagram",
        "module_relation",
        "data_uml",
    ]:
        graph.add_conditional_edges(
            node_name,
            should_generate_output,
            {"generate_final_output": "generate_final_output", "wait": END}
        )

    graph.add_edge("generate_final_output", END)
    app = graph.compile(checkpointer=MemorySaver())
    return app
