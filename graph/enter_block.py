
from typing import Any, Dict
import sys
import os
import time
import asyncio
import json
from collections import defaultdict
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph, END
from interfaces.simple_validate_mermaid import SimpleMermaidValidator
from langgraph.checkpoint.memory import MemorySaver
from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from typing_extensions import TypedDict
from typing import Annotated
from chains.prompts.select_block_file import SELECT_BLOCK_PROMPT, SELECT_FILE_PROMPT
from chains.common_chains import ChainFactory
from dotenv import load_dotenv
class NodeState(TypedDict, total=False):
    selected_blocks: list[str]
    selected_files: list[str]
    choice : int


def Node_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface, query: str, file_list: list[int]):
    select_block_chain = ChainFactory.create_generic_chain(llm_interface, SELECT_BLOCK_PROMPT)
    select_file_chain = ChainFactory.create_generic_chain(llm_interface, SELECT_FILE_PROMPT)
    fetch_block1_chain = ChainFactory.create_generic_chain(llm_interface, SELECT_BLOCK_PROMPT)
    fetch_block2_chain = ChainFactory.create_generic_chain(llm_interface, SELECT_BLOCK_PROMPT)
    async def decision_making(state: NodeState) -> NodeState:
        if state["file_list"] :
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
        chosen_list = json.loads(high_father)["node_id"]
        query = """
        MATCH (n) 
        WHERE n.nodeId = $node_id 
        RETURN n.name AS name, n.semantic_explanation AS semantic_explanation, coalesce(n.child_blocks, []) as child_blocks, labels(n) AS labels
        """
        returns_block = []
        returns_file = []
        high_father_list = []
        info_2 = []
        relation_2 = []
        for node_id in chosen_list:
            nodeId = node_id if node_id.isdigit() else json.loads(node_id)
            result = await neo4j_interface.execute_query(query, {"node_id": nodeId})
            if result[0]["labels"] == ["File"]:
                returns_file.append(nodeId)
            else:
                high_father_list.append(nodeId)
        for nodeId in high_father_list:
            relation_2.append(f"下面是以id为{nodeId}顶点的树的信息：\n")
            result = await neo4j_interface.execute_query(query, {"node_id": nodeId})
            child_blocks = result[0]["child_blocks"]
            relation_2.append(f"id为{nodeId}的节点可以划分为子节点{child_blocks}\n")
            info_2.append(f"id:{nodeId}, name:{result[0]['name']}, semantic_explanation:{result[0]['semantic_explanation']}\n")
            queue = deque([])
            for item in child_blocks:
                queue.append(json.loads(item)["nodeId"])
            while queue:
                current = queue.popleft()
                result = await neo4j_interface.execute_query(query, {"node_id": current})
                if result[0]["labels"] == ["Block"]:
                    child_blocks = result[0]["child_blocks"]
                    relation_2.append(f"id为{current}的节点可以划分为子节点{child_blocks}\n")
                    info_2.append(f"id:{current}, name:{result[0]['name']}, semantic_explanation:{result[0]['semantic_explanation']}\n")
                    for item in child_blocks:
                        queue.append(json.loads(item)["nodeId"])
            resultt = await fetch_block2_chain.ainvoke({"query": query, "relation": "\n".join(relation_2), "all_information": "\n".join(info_2)})
            returns_block.extend(json.loads(resultt)["block_id"])
        return {"selected_blocks" : returns_block, "selected_files" : returns_file}


    async def select_block(state: NodeState) -> NodeState:
        neo4j_query1="""
        MATCH p = (a:File {nodeId: $file_id})<-[:f2c*]-(d:Block {name: 'root'})
        RETURN
        [n IN nodes(p) | {
            name: n.name,
            nodeId: n.nodeId,
            semantic_explanation: n.semantic_explanation
        }] AS pathNodes
        ORDER BY length(p)
        """
        all_info = []
        relations = []
        node_sema = defaultdict(str)
        for file_id in file_list:
            record = await neo4j_interface.execute_query(neo4j_query1, {"file_id": file_id})
            result = record[0]['pathNodes']
            chains = ""
            for node in result:
                if node["name"] != "root":
                    chains += f"{node['nodeId']}<-[:f2c]-"
                else:
                    chains += f"root\n"
                if node["nodeId"] not in node_sema:
                    node_sema[node["nodeId"]] = f"name: {node['name']}, semantic_explanation: {node['semantic_explanation']}"
            relations.append(chains)
        print(relations)
        for node_id, info in node_sema.items():
            all_info.append(f"nodeId: {node_id}, {info}")
        all_info = "\n".join(all_info)
        selected_blocks = await select_block_chain.ainvoke({"query": query, "relation": "\n".join(relations), "all_information": all_info})
        print(json.loads(selected_blocks))
        return {"selected_blocks": json.loads(selected_blocks).get("block_id", [])}
    
    async def select_file(state: NodeState) -> NodeState:
        neo4j_query2="""
        MATCH (n:Block {nodeId: $block_id})-[:f2c*]->(m:File)
        RETURN m.name AS name, m.nodeId AS nodeId, m.module_explaination AS module_explaination
        """
        all_info = []
        files = []
        for block_id in state["selected_blocks"]:
            result = await neo4j_interface.execute_query(neo4j_query2, {"block_id": block_id})
            for record in result:
                all_info.append(f"nodeId: {record['nodeId']}, name: {record['name']}, module_explaination: {record['module_explaination']}")
        all_information = "\n".join(all_info)
        out_path = os.path.join(os.path.dirname(__file__), "out2.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(all_information)
        selected_files_node = await select_file_chain.ainvoke({"query": query, "all_information": all_information})
        print(json.loads(selected_files_node))
        files = set(file_list) | set(json.loads(selected_files_node).get("file_id", []))
        print(files,len(files))
        return {"selected_files": list(files)}
    
    graph = StateGraph(NodeState)
    graph.add_node("decision_making", decision_making)
    graph.add_node("fetch_block", fetch_block)
    graph.add_node("select_block", select_block)
    graph.add_node("select_file", select_file)
    graph.add_edge("decision_making", "select_block", condition=lambda state: state["choice"] == 1)
    graph.add_edge("decision_making", "fetch_block", condition=lambda state: state["choice"] == 0)
    graph.set_entry_point("select_block")
    graph.add_edge("select_block", "select_file")
    graph.add_edge("fetch_block", END)
    graph.add_edge("select_file", END)
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
        query = "代码中与订单提交有关的逻辑有哪些？"
        file_list = [90, 91, 92, 93, 105, 111, 112, 121, 142, 143, 144, 145, 148, 171, 172, 173, 174, 203, 204, 205 , 206, 381, 383, 432, 494, 495, 496, 509, 510, 511, 525, 533, 535, 550, 551, 559, 566]
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
