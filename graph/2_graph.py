# 生成对外提供接口说明文档（对外提供服务的api/接口）用户角度的接口
from typing import Any, Dict
import sys
import os
import time
import asyncio
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph, END
from interfaces.simple_validate_mermaid import SimpleMermaidValidator
from langgraph.checkpoint.memory import MemorySaver
from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from interfaces.message_service import MessageService
from typing_extensions import TypedDict
from typing import Annotated
from chains.prompts.select_api_prompt import API_FILE_PROMPT, API_CLASS_PROMPT, API_1_PROMPT, API_2_PROMPT
from chains.common_chains import ChainFactory
from dotenv import load_dotenv
class APIState(TypedDict, total=False):
    selected_files: list[str]
    selected_nodes: list[str]
    readme_content: str = ""
    base: dict[int, str]


def SelectApi_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface, path: str):
    select_api_file_chain = ChainFactory.create_generic_chain(llm_interface, API_FILE_PROMPT)
    select_api_class_chain = ChainFactory.create_generic_chain(llm_interface, API_CLASS_PROMPT)
    generate_api_1_chain = ChainFactory.create_generic_chain(llm_interface, API_1_PROMPT)
    generate_api_2_chain = ChainFactory.create_generic_chain(llm_interface, API_2_PROMPT)

    async def fetch_files(state: APIState) -> APIState:
        files = []
        query = f"""
        MATCH (n:File)
        RETURN n.name AS name, n.nodeId AS nodeId, n.module_explaination AS module_explaination
        """
        result = await neo4j_interface.execute_query(query)
        for record in result:
            files.append(f"fileId: {record['nodeId']}, name: {record['name']}, module_explaination: {record['module_explaination']}")
        file_instruction = "\n".join(files)
        selected_files1, selected_files2 = await asyncio.gather(
            select_api_file_chain.ainvoke({"file_introduction": file_instruction}),
            select_api_file_chain.ainvoke({"file_introduction": file_instruction}),
        )
        selected_files_set = set(json.loads(selected_files1).get("file_id", [])) | set(json.loads(selected_files2).get("file_id", [])) 
        selected_files = list(selected_files_set)
        print(selected_files)
        return {"selected_files": selected_files}

    async def fetch_nodes(state: APIState) -> APIState:
        query1 = f"""
        MATCH (n:Enum)<-[:DECLARES]-(n0:File)
         WHERE 'public' IN split(replace(n.modifiers, '\n', ' '), ' ') AND n0.nodeId IN {state["selected_files"]}
        OPTIONAL MATCH (a:Annotation)-[:ANNOTATES]->(n)
        RETURN n.name AS name, n.nodeId AS nodeId, n.modifiers AS modifiers, n.semantic_explanation AS semantic_explanation,
               collect(a.source_code)  AS annotation_sources
        """
        query2 = f"""
        MATCH (n:Interface)<-[:DECLARES]-(n0:File)
         WHERE 'public' IN split(replace(n.modifiers, '\n', ' '), ' ') AND n0.nodeId IN {state["selected_files"]}
        OPTIONAL MATCH (a:Annotation)-[:ANNOTATES]->(n)
        RETURN n.name AS name, n.nodeId AS nodeId, n.modifiers AS modifiers, n.semantic_explanation AS semantic_explanation,
               collect(a.source_code)  AS annotation_sources
        """
        query3 = f"""
        MATCH (n:Class)<-[:DECLARES]-(n0:File)
         WHERE 'public' IN split(replace(n.modifiers, '\n', ' '), ' ') AND n0.nodeId IN {state["selected_files"]}
        OPTIONAL MATCH (a:Annotation)-[:ANNOTATES]->(n)
        RETURN n.name AS name, n.nodeId AS nodeId, n.modifiers AS modifiers, n.semantic_explanation AS semantic_explanation,
               collect(a.source_code)  AS annotation_sources
        """
        nodes = []
        result1 = await neo4j_interface.execute_query(query1)
        result2 = await neo4j_interface.execute_query(query2)
        result3 = await neo4j_interface.execute_query(query3)
        for record in result1:
            nodes.append(record['nodeId'])
        for record in result2:
            nodes.append(record['nodeId'])
        for record in result3:
            nodes.append(record['nodeId'])
        return {"selected_nodes": nodes}
        #     nodes.append(f"nodeId: {record['nodeId']}, name: {record['name']}, modifiers: {record['modifiers']}, semantic_explanation: {(record['semantic_explanation'])}, annotation_sources: {record['annotation_sources']}")
        # node_instruction = "\n".join(nodes)
        # selected_nodes = await select_api_class_chain.ainvoke({"node_introduction": node_instruction})
        # print(selected_nodes)
        # return {"selected_nodes": json.loads(selected_nodes).get("node_id", [])}
    
    async def generate_base(state: APIState) -> APIState:
        content = {}
        query = f"""
        MATCH (n)<-[:DECLARES]-(n0:File)<-[:CONTAINS]-(nn:Package)
        WHERE n.nodeId IN {state["selected_nodes"]}
        RETURN n.name AS name, n.nodeId AS nodeId,n.source_code AS source_code, n.semantic_explanation AS semantic_explanation, n0.name AS file_name, nn.name AS package_name
        """
        result = await neo4j_interface.execute_query(query)
        for record in result:
            content[record['nodeId']] = f"nodeId: {record['nodeId']}, name: {record['name']}, from_file:{record['file_name']}, package_name:{record['package_name']}, source_code: {record['source_code']}, semantic_explanation: {json.loads(record['semantic_explanation']).get('What', '')}"
        return {"base": content}
    
    async def save_doc(state: APIState) -> APIState:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        output_filename = os.path.join(base_dir, path)
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        validator = SimpleMermaidValidator()
        input_content = ["下面是可能包含与对外提供接口/API服务功能的类的介绍"]
        for i in range(len(state["selected_nodes"])):
            input_content.append(state["base"][state["selected_nodes"][i]])
        input_content = "\n".join(input_content)
        result1 = await generate_api_1_chain.ainvoke({"readme_content": "readme.md", "all_content": input_content})
        result2 = await generate_api_2_chain.ainvoke({"readme_content": "readme.md", "all_content": input_content, "exist_content": result1})
        result = result1 + result2 + f"\n来源文件id为 {state['selected_files']}"
        with open(path, "w", encoding="utf-8") as f:
            f.write(result)
        return {"output_filename": path}
    

    
    graph = StateGraph(APIState)
    graph.add_node("fetch_files", fetch_files)
    graph.add_node("fetch_nodes", fetch_nodes)
    graph.add_node("generate_base", generate_base)
    graph.add_node("save_doc", save_doc)
    graph.set_entry_point("fetch_files")
    graph.add_edge("fetch_files", "fetch_nodes")
    graph.add_edge("fetch_nodes", "generate_base")
    graph.add_edge("generate_base", "save_doc")

    
    # save_doc 节点是终点
    graph.add_edge("save_doc", END)

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
        path = os.environ.get("2_LOCATION")
        if not await neo4j.test_connection():
            print("Neo4j连接失败")
            return
        app = SelectApi_app(llm, neo4j, path)
        result = await app.ainvoke(
            {}, 
            config={"configurable": {"thread_id": "standalone-api"}}
        )
        neo4j.close()
    
    asyncio.run(main())
