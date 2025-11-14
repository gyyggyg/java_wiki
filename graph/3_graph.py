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
from typing_extensions import TypedDict
from typing import Annotated
from chains.prompts.fin_prompt import UML_PROMPT, CONTENT_PROMPT
from chains.common_chains import ChainFactory
from dotenv import load_dotenv
class newState(TypedDict, total=False):
    graph4: str
    content: str


def Uml_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface):
    uml_chain = ChainFactory.create_generic_chain(llm_interface, UML_PROMPT)
    content_chain = ChainFactory.create_generic_chain(llm_interface, CONTENT_PROMPT)

    async def generate_uml(state: newState) -> newState:
        file_id = []
        class_name = ["AlipayController", "AlipayService", "AlipayServiceImpl", "OmsPortalOrderService", "OmsPortalOrderServiceImpl", "OmsOrderMapper", "PortalOrderDao"]
        query0 = """
        MATCH (n)
        WHERE n.name = $name
        RETURN n.source_code AS n_code, n.file_id AS file_id
        """
        query1 = """
        MATCH (n)-[:IMPLEMENTS]->(n0)
        WHERE n.name = $name
        RETURN n0.name AS n0_name, n0.source_code AS n0_code, n0.file_id AS file_id
        """
        query2 = """
        MATCH (n)-[:EXTENDS]->(n0)
        WHERE n.name = $name
        RETURN n0.name AS n0_name, n0.source_code AS n0_code, n0.file_id AS file_id
        """
        query3 = """
        MATCH (n)-[:DECLARES*1..]->(m1:Method)-[:CALLS]->(m2:Method)<-[:DECLARES*1..]-(n0)
        WHERE n.name = $name AND n<>n0
        RETURN m1.name AS m1_name, m2.name AS m2_name, n0.name AS n0_name, n0.source_code AS n0_code, n0.file_id AS file_id
        """
        query4 = """
        MATCH (n)-[:DECLARES*1..]->(m1:Method)-[:USES]->(n0:Class)
        WHERE n.name = $name AND n<>n0
        RETURN m1.name AS m1_name, n0.name AS n0_name, n0.source_code AS n0_code, n0.file_id AS file_id
        """
        query5 = """
        MATCH (n)-[:DECLARES*1..]->(m1:Method)-[:RETURNS]->(n0:Class)
        WHERE n.name = $name AND n<>n0
        RETURN m1.name AS m1_name, n0.name AS n0_name, n0.source_code AS n0_code, n0.file_id AS file_id
        """
        node_information = []
        for name in class_name:
            result, result1, result2, result3, result4, result5 = await asyncio.gather(
                neo4j_interface.execute_query(query0, {"name": name}),
                neo4j_interface.execute_query(query1, {"name": name}),
                neo4j_interface.execute_query(query2, {"name": name}),
                neo4j_interface.execute_query(query3, {"name": name}),
                neo4j_interface.execute_query(query4, {"name": name}),
                neo4j_interface.execute_query(query5, {"name": name}),
            )
            code = result[0]
            node_information.append(f"\n下面是与类 {name} 相关的类的介绍，类 {name} 的源码为 {code['n_code']}")
            file_id.append(code['file_id'])
            if result1:
                print(f"{name} 实现了", len(result1))
                for record in result1:
                    node_information.append(f"\n类 {name} 实现了 {record['n0_name']}，{record['n0_name']} 的源码为 {record['n0_code']}")
                    file_id.append(record['file_id'])
            if result2:
                print(f"{name} 继承了", len(result2))
                for record in result2:
                    node_information.append(f"\n类 {name} 继承了 {record['n0_name']}，{record['n0_name']} 的源码为 {record['n0_code']}")
                    file_id.append(record['file_id'])
            if result3:
                code_dict = {}
                rel_dict = {}
                for record in result3:
                    if record['n0_name'] not in code_dict:
                        code_dict[record['n0_name']] = record['n0_code']
                        rel_dict[record['n0_name']] = [record['m2_name']]
                        file_id.append(record['file_id'])
                    else:
                        rel_dict[record['n0_name']].append(record['m2_name'])
                print(f"{name} 调用了", len(code_dict))
                for key, value in rel_dict.items():
                    node_information.append(f"\n类 {name} 调用了 {key} 的函数 {value}")
                    node_information.append(f"\n类 {key} 源码为 {code_dict[key]}")
            if result4:
                code_dict = {}
                rel_dict = {}
                for record in result4:
                    if record['n0_name'] not in code_dict:
                        code_dict[record['n0_name']] = record['n0_code']
                        rel_dict[record['n0_name']] = [record['m1_name']]
                        file_id.append(record['file_id'])
                    else:
                        rel_dict[record['n0_name']].append(record['m1_name'])
                print(f"{name} 使用了", len(code_dict))
                for key, value in rel_dict.items():
                    node_information.append(f"\n类 {name} 使用了类型 {key} 的函数为 {value}")
            if result5:
                code_dict = {}
                rel_dict = {}
                for record in result5:
                    if record['n0_name'] not in code_dict:
                        code_dict[record['n0_name']] = record['n0_code']
                        rel_dict[record['n0_name']] = [record['m1_name']]
                        file_id.append(record['file_id'])
                    else:
                        rel_dict[record['n0_name']].append(record['m1_name'])
                print(f"{name} 返回了", len(code_dict))
                for key, value in rel_dict.items():
                    node_information.append(f"\n类 {name} 返回类型为 {key} 的函数为 {value}")
        node_information = "\n".join(node_information)
        file_id = list(set(file_id))
        resultt = await uml_chain.ainvoke({"node_information": node_information})
        resultt = resultt + f"\n来源文件id为 {file_id}"
        path = os.path.join(os.path.dirname(__file__), "out.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(resultt)
        return {"graph4": "1"}
    
    async def generate_content(state: newState) -> newState:
        name = "OmsPortalOrderServiceImpl"
        content = []
        query0 = """
        MATCH (n:Class)<-[:DECLARES]-(n1:File)<-[:CONTAINS]-(n2:Package)
        WHERE n.name = $name
        RETURN n.source_code AS n_code, n.semantic_explanation AS semantic_explanation, n1.name AS file_name, n2.name AS package_name, n.file_id AS file_id
        """
        query1 = """
        MATCH (n:Class)-[:IMPLEMENTS]->(n0)
        WHERE n.name = $name
        RETURN n0.name AS n0_name, n0.source_code AS n0_code
        """
        query2 = """
        MATCH (n:Class)-[:EXTENDS]->(n0)
        WHERE n.name = $name
        RETURN n0.name AS n0_name, n0.source_code AS n0_code
        """
        query3 = """
        MATCH (n:Class)-[:DECLARES*1..]->(m1:Method)-[:CALLS]->(m2:Method)
        WHERE n.name = $name
        RETURN m1.name AS m1_name, m2.name AS m2_name, m2.semantic_explanation AS m2_semantic_explanation
        """
        query4 = """
        MATCH (n:Class)-[:DECLARES*1..]->(m1:Method)-[:USES]->(n0)
        WHERE n.name = $name AND n<>n0
        RETURN m1.name AS m1_name, n0.name AS n0_name, n0.semantic_explanation AS n0_semantic_explanation
        """
        query5 = """
        MATCH (n:Class)-[:DECLARES*1..]->(m1:Method)-[:RETURNS]->(n0)
        WHERE n.name = $name AND n<>n0
        RETURN m1.name AS m1_name, n0.name AS n0_name, n0.semantic_explanation AS n0_semantic_explanation
        """
        result, result1, result2, result3, result4, result5 = await asyncio.gather(
                neo4j_interface.execute_query(query0, {"name": name}),
                neo4j_interface.execute_query(query1, {"name": name}),
                neo4j_interface.execute_query(query2, {"name": name}),
                neo4j_interface.execute_query(query3, {"name": name}),
                neo4j_interface.execute_query(query4, {"name": name}),
                neo4j_interface.execute_query(query5, {"name": name}),
            )
        content = []
        content.append(f"\n下面是与类 {name} 相关的类的介绍")
        record = result[0]
        content.append(
            f"类 {name}，所属文件为 {record['file_name']}，"
            f"所属包为 {record['package_name']}，"
            f"的源码为 {record['n_code']}，"
            f"语义解释为 {record['semantic_explanation']}"
        )
        file_id = record['file_id']
        if result1:
            for record in result1:
                content.append(
                    f"\n类 {name} 实现了 {record['n0_name']}，"
                    f"{record['n0_name']} 的源码为 {record['n0_code']}"
                )
        if result2:
            for record in result2:
                content.append(
                    f"\n类 {name} 继承了 {record['n0_name']}，"
                    f"{record['n0_name']} 的源码为 {record['n0_code']}"
                )
        if result3:
            sema_dic = {}
            for record in result3:
                if record['m2_name'] not in sema_dic:
                    sema_dic[record['m2_name']] = json.loads(record['m2_semantic_explanation'])['What']
            content.append(f"\n类 {name} 里调用到的函数的解释如下 {sema_dic}")
        if result4:
            sema_dic = {}
            for record in result4:
                if record['n0_name'] not in sema_dic:
                    sema_dic[record['n0_name']] = json.loads(record['n0_semantic_explanation'])['What']
            content.append(f"\n类 {name} 里函数使用到的类型的解释如下 {sema_dic}")
        if result5:
            sema_dic = {}
            for record in result5:
                if record['n0_name'] not in sema_dic:
                    sema_dic[record['n0_name']] = json.loads(record['n0_semantic_explanation'])['What']
            content.append(f"\n类 {name} 里函数返回时使用的类型的解释如下 {sema_dic}")
        content = "\n".join(content)
        resultt = await content_chain.ainvoke({"class_information": content})
        resultt = resultt + f"\n所属文件id为 {file_id}"
        path = os.path.join(os.path.dirname(__file__), "out2.md")
        print(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(resultt)
        return {"content": "2"}
    
    graph = StateGraph(newState)
    graph.add_node("generate_uml", generate_uml)
    graph.add_node("generate_content", generate_content)
    graph.set_entry_point("generate_uml")
    graph.add_edge("generate_uml", "generate_content")

    # save_doc 节点是终点
    graph.add_edge("generate_content", END)

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
        if not await neo4j.test_connection():
            print("Neo4j连接失败")
            return
        app = Uml_app(llm, neo4j)
        result = await app.ainvoke(
            {}, 
            config={"configurable": {"thread_id": "standalone-api"}}
        )
        neo4j.close()
    
    asyncio.run(main())
