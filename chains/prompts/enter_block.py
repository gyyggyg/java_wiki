
from typing import Any, Dict
import sys
import os
import time
import asyncio
import json
from collections import defaultdict, deque
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph, END
from interfaces.simple_validate_mermaid import SimpleMermaidValidator
from langgraph.checkpoint.memory import MemorySaver
from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from typing_extensions import TypedDict
from typing import Annotated
from chains.prompts.select_block_file import (
    SELECT_BLOCK_PROMPT, SELECT_FILE_PROMPT, FETCH_BLOCK1_PROMPT, FETCH_BLOCK2_PROMPT,
    JUDGE_BLOOK_PROMPT, JUDGE_BLOCK_LEVEL_PROMPT
)
from chains.common_chains import ChainFactory
from dotenv import load_dotenv
class NodeState(TypedDict, total=False):
    selected_blocks: list[str]
    selected_files: list[str]
    choice : int


def Node_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface, query: str, file_list: list[int]):
    select_block_chain = ChainFactory.create_generic_chain(llm_interface, SELECT_BLOCK_PROMPT)
    select_file_chain = ChainFactory.create_generic_chain(llm_interface, SELECT_FILE_PROMPT)
    fetch_block1_chain = ChainFactory.create_generic_chain(llm_interface, FETCH_BLOCK1_PROMPT)
    fetch_block2_chain = ChainFactory.create_generic_chain(llm_interface, FETCH_BLOCK2_PROMPT)
    async def decision_making(state: NodeState) -> NodeState:
        if file_list:
            return {"choice": 1}
        else:
            return {"choice": 0}

    async def fetch_block(state: NodeState) -> NodeState:
        neo4j_query="""
        MATCH (n:Block)-[:f2c]->(n0)-[:f2c]->(n1)
        WHERE n.name = 'root'
        RETURN n.semantic_explanation AS n_sema, n.nodeId AS n_nodeId, n.name AS n_name, n.child_blocks AS n_child,
        n0.semantic_explanation AS n0_sema, n0.nodeId AS n0_nodeId, n0.name AS n0_name, n0.child_blocks AS n0_child,
        n1.semantic_explanation AS n1_sema, n1.nodeId AS n1_nodeId, n1.name AS n1_name, n1.child_blocks AS n1_child
        """
        result = await neo4j_interface.execute_query(neo4j_query)
        relation_1 = ["father_id : child_id_list\n"]
        info_1 = []
        child_dict = {}
        block_info = {}
        child_dict[result[0]["n_nodeId"]] = result[0]["n_child"]
        block_info[result[0]["n_nodeId"]] = f"name:{result[0]['n_name']}, semantic_explanation:{result[0]['n_sema']}"
        for record in result:
            if record["n0_nodeId"] and record["n0_nodeId"] not in child_dict:
                child_dict[record["n0_nodeId"]] = record["n0_child"]
            if record["n0_nodeId"] and record["n0_nodeId"] not in block_info:
                block_info[record["n0_nodeId"]] = f"name:{record['n0_name']}, semantic_explanation:{record['n0_sema']}"
            if record["n1_nodeId"] and record["n1_nodeId"] not in block_info:
                block_info[record["n1_nodeId"]] = f"name:{record['n1_name']}, semantic_explanation:{record['n1_sema']}"           
        for key, value in child_dict.items():
            relation_1.append(f"{key}:{value}\n")
        for key, value in block_info.items():
            info_1.append(f"id:{key},{value}\n")
        high_father = await fetch_block1_chain.ainvoke({"query": query, "relation": "\n".join(relation_1), "all_information": "\n".join(info_1)})
        print(high_father)
        chosen_list = json.loads(high_father)["node_id"]
        query0 = """
        MATCH (n) 
        WHERE n.nodeId = $node_id 
        RETURN n.name AS name, n.semantic_explanation AS semantic_explanation, coalesce(n.child_blocks, []) as child_blocks, labels(n) AS labels
        """
        returns_block = []
        returns_file = []
        high_father_list = []
        for node_id in chosen_list:
            nodeId = int(node_id)
            result = await neo4j_interface.execute_query(query0, {"node_id": nodeId})
            if result[0]["labels"] == ["File"]:
                returns_file.append(nodeId)
            else:
                high_father_list.append(nodeId)
        for nodeId in high_father_list:
            info_2 = []
            relation_2 = []
            relation_2.append(f"下面是以id为{nodeId}顶点的树的信息：\n")
            result = await neo4j_interface.execute_query(query0, {"node_id": nodeId})
            child_blocks = result[0]["child_blocks"]
            relation_2.append(f"id为{nodeId}的节点可以划分为子节点{child_blocks}\n")
            info_2.append(f"id:{nodeId}, name:{result[0]['name']}, semantic_explanation:{result[0]['semantic_explanation']}\n")
            queue = deque([])
            for item in child_blocks:
                queue.append(int(json.loads(item)["nodeId"]))
            while queue:
                current = queue.popleft()
                result = await neo4j_interface.execute_query(query0, {"node_id": int(current)})
                if result[0]["labels"] == ["Block"]:
                    child_blocks = result[0]["child_blocks"]
                    relation_2.append(f"id为{current}的节点可以划分为子节点{child_blocks}\n")
                    info_2.append(f"id:{current}, name:{result[0]['name']}, semantic_explanation:{result[0]['semantic_explanation']}\n")
                    for item in child_blocks:
                        queue.append(int(json.loads(item)["nodeId"]))
            resultt = await fetch_block2_chain.ainvoke({"query": query, "relation": "\n".join(relation_2), "all_information": "\n".join(info_2)})
            returns_block.extend(json.loads(resultt)["block_id"])
        print("returns_file:",returns_file)
        print("returns_block:",returns_block)
        return {"selected_blocks" : returns_block, "selected_files" : returns_file}


    # async def select_block(state: NodeState) -> NodeState:
    #     neo4j_query1="""
    #     MATCH p = (a:File {nodeId: $file_id})<-[:f2c*]-(d:Block {name: 'root'})
    #     RETURN
    #     [n IN nodes(p) | {
    #         name: n.name,
    #         nodeId: n.nodeId,
    #         semantic_explanation: n.semantic_explanation
    #     }] AS pathNodes
    #     ORDER BY length(p)
    #     """
    #     all_info = []
    #     relations = []
    #     node_sema = defaultdict(str)
    #     for file_id in file_list:
    #         record = await neo4j_interface.execute_query(neo4j_query1, {"file_id": file_id})
    #         result = record[0]['pathNodes']
    #         chains = ""
    #         for node in result:
    #             if node["name"] != "root":
    #                 chains += f"{node['nodeId']}<-[:f2c]-"
    #             else:
    #                 chains += f"root\n"
    #             if node["nodeId"] not in node_sema:
    #                 node_sema[node["nodeId"]] = f"name: {node['name']}, semantic_explanation: {node['semantic_explanation']}"
    #         relations.append(chains)
    #     for node_id, info in node_sema.items():
    #         all_info.append(f"nodeId: {node_id}, {info}")
    #     all_info = "\n".join(all_info)
    #     selected_blocks = await select_block_chain.ainvoke({"query": query, "relation": "\n".join(relations), "all_information": all_info})
    #     print(json.loads(selected_blocks))
    #     return {"selected_blocks": json.loads(selected_blocks).get("block_id", [])}
    
    # async def select_file(state: NodeState) -> NodeState:
    #     neo4j_query2="""
    #     MATCH (n:Block {nodeId: $block_id})-[:f2c*]->(m:File)
    #     RETURN m.name AS name, m.nodeId AS nodeId, m.module_explaination AS module_explaination
    #     """
    #     files = []
    #     reasons = []
    #     for block_id in state["selected_blocks"]:
    #         all_info = []
    #         result = await neo4j_interface.execute_query(neo4j_query2, {"block_id": block_id})
    #         for record in result:
    #             all_info.append(f"nodeId: {record['nodeId']}, name: {record['name']}, module_explaination: {record['module_explaination']}")
    #         all_information = "\n".join(all_info)
    #         selected_files_node = await select_file_chain.ainvoke({"query": query, "all_information": all_information})
    #         files.extend(json.loads(selected_files_node).get("file_id", []))
    #         reasons.append(json.loads(selected_files_node).get("reason", []))
    #     print(files,len(files))
    #     print(reasons)
    #     return {"selected_files": list(files)}

    # =============================================================================
    # 从下往上搜索的辅助函数
    # =============================================================================

    async def get_module_info(id: int) -> str:
        query = """
        MATCH (n)
        WHERE n.nodeId = $id
        RETURN n.name AS name, n.module_explaination as module_explanation
        """
        #module_explaination
        result = await neo4j_interface.execute_query(query, {"id": id})
        return f"name:{result[0]['name']}, module_explanation:{result[0]['module_explanation']}"

    async def judge_level(block_list: list[int])-> list[int]:
        parent_query = """
        UNWIND $child_ids AS child_id
        MATCH (child:Block {nodeId: child_id})
        OPTIONAL MATCH (child)<-[:f2c]-(parent:Block)
        OPTIONAL MATCH (parent)-[:f2c]->(sibling)
        RETURN
            child.nodeId AS child_id,
            child.name AS child_name,
            parent.nodeId AS parent_id,
            parent.name AS parent_name,
            parent.module_explaination AS parent_module_explanation,
            collect(DISTINCT {
                nodeId: sibling.nodeId,
                module_explanation: sibling.module_explaination
            }) AS siblings
        """
        #module_explaination
        records = await neo4j_interface.execute_query(parent_query, {"child_ids": block_list})
        parent_groups = defaultdict(lambda: {
            'parent_info': {},
            'children_in_layer': [],
            'siblings_info': []
        })
        new_block_list = []
        for rec in records:
            parent_id = rec['parent_id']
            if not parent_id:
                new_block_list.append(rec['child_id'])
                continue
            if not parent_groups[parent_id]['parent_info']:
                parent_groups[parent_id]['parent_info'] = {
                    'nodeId': parent_id,
                    'name': rec['parent_name'],
                    'semantic': rec['parent_module_explanation']
                }
            parent_groups[parent_id]['children_in_layer'].append(rec['child_id'])
            for sib in rec['siblings']:
                if sib.get('nodeId') and sib not in parent_groups[parent_id]['siblings_info']:
                    parent_groups[parent_id]['siblings_info'].append(sib)
        judge_level_chain = ChainFactory.create_generic_chain(llm_interface, JUDGE_BLOCK_LEVEL_PROMPT)
        coros = [
            judge_level_chain.ainvoke({
                "query": query,
                "parent_info": g['parent_info'],
                "select_blocks_info": g['children_in_layer'],
                "all_child_blocks_info": g['siblings_info']
            })
                for _, g in parent_groups.items()
            ]
        results = await asyncio.gather(*coros)
        for (parent_id, _), result in zip(parent_groups.items(), results):
            parsed_result = json.loads(result)
            print(parent_id, parsed_result)
            if parsed_result['judgement'] == 'parent':
                new_block_list.append(parent_id)
            elif parsed_result['judgement'] == 'now':
                new_block_list.extend(parent_groups[parent_id]['children_in_layer'])
            else:
                print(parsed_result)
        print("new_block_list:", new_block_list)
        return new_block_list

    async def select_from_bottom_up(state: NodeState) -> NodeState:
        file_parent_query = """
        UNWIND $file_ids AS file_id
        MATCH (f:File {nodeId: file_id})<-[:f2c]-(b:Block)
        OPTIONAL MATCH (b)-[:f2c*]->(sibling:File)
        RETURN
            f.nodeId AS file_id,
            f.name AS file_name,
            f.module_explaination AS module_explanation,
            b.nodeId AS parent_id,
            b.name AS parent_name,
            b.module_explaination AS parent_module_explanation,
            collect(DISTINCT {
                nodeId: sibling.nodeId,
                name: sibling.name,
                module_explanation: sibling.module_explaination
            }) AS siblings
        """
        #module_explaination
        records = await neo4j_interface.execute_query(file_parent_query, {"file_ids": file_list})
        block_groups = defaultdict(lambda: {'block_info': {}, 'files_info': []})
        selected_blocks = []

        for rec in records:
            # File挂在普通Block下
            block_id = rec['parent_id']
            if not block_groups[block_id]['block_info']:
                block_groups[block_id]['block_info'] = {
                    'nodeId': block_id,
                    'name': rec['parent_name'],
                    'module_explanation': rec['parent_module_explanation']
                }
            for sib in rec['siblings']:
                if sib not in block_groups[block_id]['files_info']:
                    block_groups[block_id]['files_info'].append(sib)
        block_ids = list(block_groups.keys())
        tasks = []
        judge_block_chain = ChainFactory.create_generic_chain(llm_interface, JUDGE_BLOOK_PROMPT)
        for block_id in block_ids:
            tasks.append(judge_block_chain.ainvoke({
                "query": query,
                "block_info": f"block_nodeId:{block_id}, name:{block_groups[block_id]['block_info']['name']}, module_explanation:{block_groups[block_id]['block_info']['module_explanation']}",
                "files_info": block_groups[block_id]['files_info']
            }))
        results = await asyncio.gather(*tasks)
        print(results)        
        for (block_id, _), result in zip(block_groups.items(), results):
            parsed_result = json.loads(result)
            if parsed_result["relevant"]=="true":
                selected_blocks.append(block_id)
            elif parsed_result["relevant"]=="false":
                continue
        while True:
            new_block_list = await judge_level(selected_blocks)
            if sorted(new_block_list) == sorted(selected_blocks):
                break
            selected_blocks = new_block_list
        print("最终选中的blocks:", selected_blocks)
        return {"selected_blocks": selected_blocks}

    # 定义条件路由函数
    def route_decision(state: NodeState) -> str:
        """根据 choice 的值决定下一个节点"""
        # choice == 1 表示有file_list，使用从下往上搜索
        # choice == 0 表示没有file_list，使用从上往下搜索
        if state["choice"] == 1:
            return "select_from_bottom_up"  # 使用新的从下往上搜索
        else:
            return "fetch_block"  # 使用原来的从上往下搜索

    # 构建状态图
    graph = StateGraph(NodeState)

    # 添加节点
    graph.add_node("decision_making", decision_making)  # 决策节点
    graph.add_node("fetch_block", fetch_block)  # 从上往下搜索（保留）
    graph.add_node("select_from_bottom_up", select_from_bottom_up)  # 从下往上搜索（新）

    # 注意：select_block 和 select_file 已被 select_from_bottom_up 替代，不再需要

    # 设置入口点
    graph.set_entry_point("decision_making")

    # 添加条件边：根据decision_making的结果路由
    graph.add_conditional_edges("decision_making", route_decision)

    # 添加边：两条路径都直接结束
    graph.add_edge("fetch_block", END)  # 从上往下搜索完成后结束
    graph.add_edge("select_from_bottom_up", END)  # 从下往上搜索完成后结束

    # 编译图
    app = graph.compile(checkpointer=MemorySaver())
    return app
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    
    async def main():
        print("=== 独立运行对外提供接口说明文档生成应用 ===")
        llm = LLMInterface(model_name="gpt-4.1-2025-04-14", provider="openai")
        uri = os.environ.get("WIKI_NEO4J_URI")
        user = os.environ.get("WIKI_NEO4J_USER")
        password = os.environ.get("WIKI_NEO4J_PASSWORD")
        neo4j = Neo4jInterface(uri, user, password)
        query =  "代码中与订单提交有关的逻辑有哪些？"
        file_list =   [568, 386, 378, 530, 206, 145, 245, 505, 558, 432, 260, 272, 183, 543] 
        # file_list = []
        if not await neo4j.test_connection():
            print("Neo4j连接失败")
            return
        app = Node_app(llm, neo4j, query, file_list)
        result = await app.ainvoke(
            {}, 
            config={"configurable": {"thread_id": "standalone-api"}}
        )
        neo4j.close()
    
    asyncio.run(main())
