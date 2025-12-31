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
        node_id_list = [536, 574, 467, 367, 245]

        # ---- Cypher 查询 ----
        query1 = """
        MATCH (n)
        WHERE n.nodeId = $node_id
        RETURN n.name AS name,
            n.source_code AS source_code,
            n.semantic_explanation AS sema
        """
        all_info = []

        # 并发执行
        for id in node_id_list:
            result = await neo4j_interface.execute_query(query1, {"node_id": id})
            im = f"name: {result[0]['name']}, source_code: {result[0]['source_code']}, semantic_explanation: {result[0]['sema']}"
            all_info.append(im)
        target =  "用户申请退货后，后台如何处理退货和退款，请只为我提供详细的控制流图"
        related_context = "\n".join(all_info)

        resultt = await test_chain.ainvoke({"target": target, "related_context": related_context})
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