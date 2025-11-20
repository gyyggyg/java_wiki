
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
from interfaces.message_service import MessageService
from typing_extensions import TypedDict
from typing import Annotated
from chains.prompts.select_api_prompt import SELECT_BLOCK_PROMPT, SELECT_FILE_PROMPT
from chains.common_chains import ChainFactory
from dotenv import load_dotenv
class NodeState(TypedDict, total=False):
    selected_blocks: list[str]
    selected_files: list[str]


def Node_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface, query: str, file_list: list[int]):
    select_block_chain = ChainFactory.create_generic_chain(llm_interface, SELECT_BLOCK_PROMPT)
    select_file_chain = ChainFactory.create_generic_chain(llm_interface, SELECT_FILE_PROMPT)

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
                    chains += f"node['name']<-[:f2c]-"
                else:
                    chains += f"root\n"
                if node["nodeId"] not in node_sema:
                    node_sema[node["nodeId"]] = f"name: {node['name']}, semantic_explanation: {node['semantic_explanation']}"
            relations.append(chains)
        for node_id, info in node_sema.items():
            all_info.append(f"nodeId: {node_id}, {info}")
        all_info = "\n".join(all_info)
        selected_blocks = await select_block_chain.ainvoke({"query": query, "relation": "\n".join(relations), "all_information": all_info})
        return {"selected_blocks": selected_blocks.get("block_id", [])}
    
    async def select_file(state: NodeState) -> NodeState:
        neo4j_query2="""
        MATCH (n:Block {nodeId: $block_id})-[:f2c*](m:File)
        RETURN m.name AS name, m.nodeId AS nodeId, m.module_explaination AS module_explaination
        """
        all_info = []
        files = []
        for block_id in state["selected_blocks"]:
            result = await neo4j_interface.execute_query(neo4j_query2, {"block_id": block_id})
            for record in result:
                all_info.append(f"nodeId: {record['nodeId']}, name: {record['name']}, module_explaination: {record['module_explaination']}")
        all_information = "\n".join(all_info)
        selected_files_node = await select_file_chain.ainvoke({"query": query, "all_information": all_information})
        files = set(file_list | selected_files_node.get("file_id", []))
        return {"selected_files": list(files)}
    
    graph = StateGraph(NodeState)
    graph.add_node("select_block", select_block)
    graph.add_node("select_file", select_file)
    graph.set_entry_point("select_block")
    graph.add_edge("select_block", "select_file")
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
        query = "test query"
        file_list = []
        if not await neo4j.test_connection():
            print("Neo4j连接失败")
            return
        app = Node_app(llm, neo4j, query)
        result = await app.ainvoke(
            {}, 
            config={"configurable": {"thread_id": "standalone-api"}}
        )
        neo4j.close()
    
    asyncio.run(main())
