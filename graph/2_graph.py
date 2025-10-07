# 生成对外提供接口说明文档（对外提供服务的api/接口）用户角度的接口
from typing import Any, Dict
import sys
import os
import time
import asyncio
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph, END, Send
from langgraph.constants import Send
from interfaces.simple_validate_mermaid import SimpleMermaidValidator
from langgraph.checkpoint.memory import MemorySaver
from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from message_service import MessageService
from typing_extensions import TypedDict
from typing import Annotated
from chains.prompts.select_api_prompt import API_FILE_PROMPT, API_PROMPT
from chains.common_chains import ChainFactory
from dotenv import load_dotenv
class APIState(TypedDict, total=False):
    selected_nodes: list[int]
    readme_content: str = ""
    base: dict[int, str]
    extends: dict[int, str]
    returns: dict[int, str]
    uses: dict[int, str]
    calls: dict[int, str]
    counter:  Annotated[int, lambda x, y: x + y]

def SelectApi_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface, path: str):
    select_api_file_chain = ChainFactory.create_generic_chain(llm_interface, API_FILE_PROMPT)
    generate_api_chain = ChainFactory.create_generic_chain(llm_interface, API_PROMPT)

    async def fetch_nodes(state: APIState) -> APIState:
        query = f"""
        MATCH (n:{label})<-[:DECLARES]-(n0:File)
        WHERE 'public' in n.modifiers
        OPTIONAL MATCH (a:Annotation)-[:ANNOTATES]->(n)
        RETURN n.name AS name, n.nodeId AS nodeId, n.modifiers AS modifiers, n.semantic_explanation AS semantic_explanation,
               collect(a.source_code)  AS annotation_sources
        """
        records = []
        nodes = []
        result1 = await neo4j_interface.execute_query(query, {"label": "Enum"})
        result2 = await neo4j_interface.execute_query(query, {"label": "Interface"})
        result3 = await neo4j_interface.execute_query(query, {"label": "Class"})
        records.extend(result1)
        records.extend(result2)
        records.extend(result3)
        for record in records:
            nodes.append(f"nodeId: {record['nodeId']}, name: {record['name']}, modifiers: {record['modifiers']}, semantic_explanation: {record['semantic_explanation']}, annotation_sources: {record['annotation_sources']}")
        node_instruction = "\n".join(nodes)
        selected_nodes = await select_api_file_chain.ainvoke({"node_introduction": node_instruction})
        update = {
            "selected_nodes": selected_nodes.get("node_id", []),
            "counter": 0
        }
        return [Send("generate_base", update),
                Send("generate_extends", update),
                Send("generate_returns", update),
                Send("generate_uses", update),
                Send("generate_calls", update)]
    
    async def generate_base(state: APIState) -> APIState:
        content = {}
        query = f"""
        MATCH n
        WHERE n.nodeId IN {state["selected_nodes"]}
        OPTIONAL MATCH (a:Annotation)-[:ANNOTATES]->(n)
        RETURN n.name AS name, n.nodeId AS nodeId,n.source_code AS source_code, collect(a.source_code) AS annotation_sources
        """
        result = await neo4j_interface.execute_query(query)
        for record in result:
            content[record['nodeId']] = f"nodeId: {record['nodeId']}, name: {record['name']}, source_code: {record['source_code']}, annotation_sources: {record['annotation_sources']}"
        return {"base": content, "counter": 1}
    
    async def generate_extends(state: APIState) -> APIState:
        query = f"""
        MATCH n-[:EXTENDS]-> nf
        WHERE n.nodeId IN {state["selected_nodes"]}
        RETURN n.name AS name, n.nodeId AS nodeId,n.source_code AS source_code, nf.name AS nf_name, nf.semantic_explanation AS nf_semantic_explanation
        """
        content = {}
        result = await neo4j_interface.execute_query(query)
        for record in result:
            if record['nodeId'] in content:
                content[record['nodeId']] = content[record['nodeId']] + f"\n此类继承{record['nf_name']}, 其语义解释为{record['nf_semantic_explanation']}"
            else:
                content[record['nodeId']] = f"\n此类继承{record['nf_name']}, 其语义解释为{record['nf_semantic_explanation']}"
        return {"extends": content, "counter": 1}
    
    async def generate_returns(state: APIState) -> APIState:
        query = f"""
        MATCH n-[:DECLARES*1..]->(n1:Method)-[:RETURNS]->(n2)
        WHERE n.nodeId IN {state["selected_nodes"]}
        RETURN n1.name AS n1_name, n2.name AS n2_name, n2.semantic_explanation AS n2_sema, n.nodeId AS nodeId
        """
        content = {}
        result = await neo4j_interface.execute_query(query)
        for record in result:
            if record['nodeId'] in content:
                content[record['nodeId']] = content[record['nodeId']] + f"\n此类其中的Method{record['n1_name']}返回类型为{record['n2_name']}, 此类型其语义解释为{record['n2_sema']}"
            else:
                content[record['nodeId']] = f"\n此类其中的Method{record['n1_name']}返回类型为{record['n2_name']}, 此类型其语义解释为{record['n2_sema']}"
        return {"returns": content, "counter": 1}
    
    async def generate_uses(state: APIState) -> APIState:
        query = f"""
        MATCH n-[:DECLARES*1..]->(n1:Method)-[:USES]->(n2)
        WHERE n.nodeId IN {state["selected_nodes"]}
        RETURN n1.name AS n1_name, n2.name AS n2_name, n2.semantic_explanation AS n2_sema, n.nodeId AS nodeId
        """
        content = {}
        result = await neo4j_interface.execute_query(query)
        for record in result:
            if record['nodeId'] in content:
                content[record['nodeId']] = content[record['nodeId']] + f"\n此类其中的Method{record['n1_name']}使用类型为{record['n2_name']}, 此类型其语义解释为{record['n2_sema']["What"]}"
            else:
                content[record['nodeId']] = f"\n此类其中的Method{record['n1_name']}使用类型为{record['n2_name']}, 此类型其语义解释为{record['n2_sema']["What"]}"
        return {"uses": content, "counter": 1}

    async def generate_calls(state: APIState) -> APIState:
        query = f"""
        MATCH n-[:DECLARES*1..]->(n1:Method)-[:CALLS]->(n2)
        WHERE n.nodeId IN {state["selected_nodes"]}
        RETURN n1.name AS n1_name, n2.name AS n2_name, n2.semantic_explanation AS n2_sema, n.nodeId AS nodeId
        """
        content = {}
        result = await neo4j_interface.execute_query(query)
        for record in result:
            if record['nodeId'] in content:
                content[record['nodeId']] = content[record['nodeId']] + f"\n此类其中的Method{record['n1_name']}调用Method为{record['n2_name']}, 此Method其语义解释为{record['n2_sema']["What"]}\n"
            else:
                content[record['nodeId']] = f"\n此类其中的Method{record['n1_name']}调用Method为{record['n2_name']}, 此Method其语义解释为{record['n2_sema']["What"]}\n"
        return {"calls": content, "counter": 1}
    
    async def save_doc(state: APIState) -> APIState:
        validator = SimpleMermaidValidator()
        input_content = ["下面是可能包含与对外提供接口/API服务功能的类的介绍"]
        for i in range(len(state["selected_nodes"])):
            input_content.append(state["base"].get([state["selected_nodes"][i]], "")+state["extends"].get([state["selected_nodes"][i]], "")+state["returns"].get([state["selected_nodes"][i]], "")+state["uses"].get([state["selected_nodes"][i]], "")+state["calls"].get([state["selected_nodes"][i]], ""))
        input_content = "\n".join(input_content)
        result = await generate_api_chain.ainvoke({"readme_content": state["readme_content"], "all_content": input_content})
        result_validate = validator.validate_file(result)
        while not result_validate["result"]:
            error = result_validate["errors"]
            error_msg = f"注意: 如果需要生成mermaid语句, 在生成mermaid语句时需要规避的问题例如:{error}"
            new_content = state["readme_content"] + str(error_msg)
            result = await generate_api_chain.ainvoke({"readme_content": state["readme_content"], "all_content": input_content})
        with open(path, "w", encoding="utf-8") as f:
            f.write(result)
        return {"output_filename": path}
    
    def should_continue(state: APIState) -> str:
        if state.get("counter", 0) == 5:
            return "save_doc"
        else:
            return END
    
    graph = StateGraph(APIState)
    graph.add_node("fetch_nodes", fetch_nodes)
    graph.add_node("generate_base", generate_base)
    graph.add_node("generate_extends", generate_extends)
    graph.add_node("generate_returns", generate_returns)
    graph.add_node("generate_uses", generate_uses)
    graph.add_node("generate_calls", generate_calls)
    graph.add_node("save_doc", save_doc)
    graph.add_conditional_edges("generate_base", should_continue, {"save_doc": "save_doc", END: END})
    graph.add_conditional_edges("generate_extends", should_continue, {"save_doc": "save_doc", END: END})
    graph.add_conditional_edges("generate_returns", should_continue, {"save_doc": "save_doc", END: END})
    graph.add_conditional_edges("generate_uses", should_continue, {"save_doc": "save_doc", END: END})
    graph.add_conditional_edges("generate_calls", should_continue, {"save_doc": "save_doc", END: END})
    
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
