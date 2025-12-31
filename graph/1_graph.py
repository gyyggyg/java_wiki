import os
import sys
import json
import asyncio
from typing import Any, Dict
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from interfaces.llm_interface import LLMInterface          # 你自己的封装
from interfaces.neo4j_interface import Neo4jInterface
from chains.prompts.fin_prompt import INDIVIDUL_PROMPT
from chains.prompts.mapping_prompt import GENERATE_JSON_PROMPT   # 提示词模板
from chains.common_chains import ChainFactory            # 简易链工厂
from interfaces.data_master import get_file_content

# ====================== 1. 状态定义 ======================
from typing_extensions import TypedDict

class TrueState(TypedDict, total=False):
    graphman: str       

def in_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface):
    in_chain = ChainFactory.create_generic_chain(llm_interface, INDIVIDUL_PROMPT)
    test_chain = ChainFactory.create_generic_chain(llm_interface, GENERATE_JSON_PROMPT)
    async def generate_in(state: TrueState) -> TrueState:
        # path = "D:/langgraph/java_wiki/mall/mall"
        # file_path_list = ["mall-mbg/src/main/resources/com/macro/mall/mapper/OmsOrderMapper.xml", "mall-portal/src/main/resources/dao/PortalOrderDao.xml"]
        # file_content = get_file_content(path, file_path_list)
        node_id_list = [345, 344]

        # ---- Cypher 查询 ----
        query1 = """
        MATCH (n)
        WHERE n.nodeId = $node_id
        RETURN n.name AS name,
            n.source_code AS source_code,
            n.semantic_explanation AS sema
        """
        query2 = """
        MATCH (n)-[:CALLS]->(m2:Method)
        WHERE n.nodeId = $node_id
        RETURN m2.name AS m2_name,
            m2.semantic_explanation AS sema
        """
        query3 = """
        MATCH (n)-[:USES]->(n0)
        WHERE n.nodeId = $node_id
        RETURN n0.name AS n0_name,
            n0.semantic_explanation AS sema
        """
        query4 = """
        MATCH (n)-[:RETURNS]->(n0)
        WHERE n.nodeId = $node_id
        RETURN n0.name AS n0_name,
            n0.semantic_explanation AS sema
        """

        # 并发执行
        result1, result2, result3, result4 = await asyncio.gather(
            neo4j_interface.execute_query(query1, {"node_id": node_id}),
            neo4j_interface.execute_query(query2, {"node_id": node_id}),
            neo4j_interface.execute_query(query3, {"node_id": node_id}),
            neo4j_interface.execute_query(query4, {"node_id": node_id}),
        )

        node_information = []
        if result1:
            code = result1[0]
            node_information.append(
                f"\n下面是与函数 {code['name']} 相关的类的介绍，"
                f"其源码为 {code['source_code']}，"
                f"语义解释为 {code['sema']}"
            )

        if result2:
            for record in result2:
                node_information.append(
                    f"\n{code['name']} 调用函数 {record['m2_name']} 的解释为 "
                    f"{json.loads(record['sema'])['What']}"
                )

        if result3:
            for record in result3:
                node_information.append(
                    f"\n{code['name']} 使用类型 {record['n0_name']} 的解释为 "
                    f"{json.loads(record['sema'])['What']}"
                )

        if result4:
            for record in result4:
                node_information.append(
                    f"\n{code['name']} 返回类型 {record['n0_name']} 的解释为 "
                    f"{json.loads(record['sema'])['What']}"
                )

        all_in = "\n".join(node_information)
        all_in = f"{all_in}\n{file_content}"

        chain = ChainFactory.create_generic_chain(llm_interface, INDIVIDUL_PROMPT)
        resultt = await chain.ainvoke({"all_in": all_in})

        out_path = os.path.join(os.path.dirname(__file__), "out1.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(resultt)

        return {"graphman": "1"}


    graph = StateGraph(TrueState)
    graph.add_node("generate_in", generate_in)
    graph.set_entry_point("generate_in")
    graph.add_edge("generate_in", END)

    app = graph.compile(checkpointer=MemorySaver())
    return app

# ====================== 4. 独立运行入口 ======================
async def main():
    load_dotenv()
    print("=== 独立运行对外提供接口说明文档生成应用 ===")

    llm = LLMInterface(model_name="gpt-4.1-2025-04-14", provider="openai")
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    if not await neo4j.test_connection():
        print("[ERR] Neo4j 连接失败")
        return

    app = in_app(llm, neo4j)
    await app.ainvoke(
        {}, 
        config={"configurable": {"thread_id": "standalone-api"}}
    )
    neo4j.close()

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())