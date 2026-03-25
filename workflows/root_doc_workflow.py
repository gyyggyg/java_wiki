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
from chains.prompts.root_doc_prompt import PROJECT_INTRO_PROMPT, MODULE_ARCHITECTURE_PROMPT
from graph.module_target import module_app

# 项目根目录（java_wiki）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ====================== 1. 状态定义 ======================
class RootDocState(TypedDict, total=False):
    # 模块信息
    modules_info: List[Dict]
    # 各章节内容
    section1_intro: Dict
    section2_architecture: Dict
    section3_diagram: Dict
    # 最终输出
    final_output: Dict
    high_blocks: List

# ====================== 2. 工作流定义 ======================
def root_doc_workflow(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface):
    # 创建LLM链
    intro_chain = ChainFactory.create_generic_chain(llm_interface, PROJECT_INTRO_PROMPT)
    architecture_chain = ChainFactory.create_generic_chain(llm_interface, MODULE_ARCHITECTURE_PROMPT)

    async def fetch_root_modules(state: RootDocState) -> RootDocState:
        """
        查询root Block的直接子Block信息
        """
        query = """
        MATCH (root:Block {name: 'root'})-[:f2c]->(child:Block)
        RETURN child.nodeId AS nodeId,
               child.name AS name,
               child.module_explaination AS module_explaination
        ORDER BY child.name
        """
        high_blocks = []
        result = await neo4j_interface.execute_query(query)

        modules_info = []
        new_names = json.loads(get_file(os.path.join(PROJECT_ROOT, "graph", "block_new_names.json")))

        for record in result:
            modules_info.append({
                "nodeId": record['nodeId'],
                "name": new_names.get(str(record['nodeId'])),
                "path": record['name'],
                "module_explaination": record['module_explaination'] or "暂无说明"
            })
            high_blocks.append(record['nodeId'])

        print(f"[INFO] 获取到 {len(modules_info)} 个一级模块")
        return {"modules_info": modules_info, "high_blocks": high_blocks}

    async def generate_intro(state: RootDocState) -> RootDocState:
        """
        生成项目介绍章节
        """
        modules_info = state["modules_info"]

        # 格式化模块信息
        modules_text = []
        for module in modules_info:
            modules_text.append(
                f"- 模块名称: {module['name']}\n"
                f"  功能说明: {module['module_explaination']}"
            )

        modules_info_str = "\n\n".join(modules_text)

        # 调用LLM生成内容
        markdown_content = await intro_chain.ainvoke({
            "modules_info": modules_info_str
        })

        # 收集所有引用的节点ID
        neo4j_id = {
            "1": [str(module['nodeId']) for module in modules_info]
        }

        print(f"[INFO] 项目介绍章节生成完成")
        return {
            "section1_intro": {
                "markdown": markdown_content,
                "neo4j_id": neo4j_id
            }
        }

    async def generate_architecture(state: RootDocState) -> RootDocState:
        """
        生成项目模块架构章节
        """
        modules_info = state["modules_info"]

        # 格式化模块信息
        modules_text = []
        for module in modules_info:
            modules_text.append(
                f"- 模块名称: {module['name']}\n"
                f"  模块路径: {module['path']}\n"
                f"  模块ID: {module['nodeId']}\n"
                f"  功能说明: {module['module_explaination']}"
            )

        modules_info_str = "\n\n".join(modules_text)

        # 调用LLM生成内容
        markdown_content = await architecture_chain.ainvoke({
            "modules_info": modules_info_str
        })

        # 收集所有引用的节点ID

        print(f"[INFO] 模块架构章节生成完成")
        return {
            "section2_architecture": {
                "markdown": json.loads(markdown_content)["markdown"],
                "neo4j_id": json.loads(markdown_content)["mapping"]
            }
        }

    async def generate_diagram(state: RootDocState) -> RootDocState:
        """
        生成项目架构图（调用module_target.py的功能）
        """
        print(f"[INFO] 开始生成项目架构图...")

        # 调用module_target.py的module_app
        module_workflow = module_app(llm_interface, neo4j_interface)
        result = await module_workflow.ainvoke(
            {},
            config={"configurable": {"thread_id": "root-doc-module"}}
        )
        module_data = result["output"]
        mermaid_data = module_data["mermaid"]
        neo4j_id = module_data["mapping"]

        # 添加标题和说明
        mermaid_content = "## 3. 项目架构图\n\n"
        mermaid_content += "下图展示了项目的模块组织结构和依赖关系：\n\n"
        mermaid_content += "```mermaid\n"
        mermaid_content += mermaid_data
        mermaid_content += "\n```"

        print(f"[INFO] 项目架构图生成完成")
        return {
            "section3_diagram": {"mermaid": mermaid_content, "neo4j_id": neo4j_id}
        }

    async def merge_sections(state: RootDocState) -> RootDocState:
        """
        合并所有章节为最终JSON输出
        """
        wiki = []

        # 添加项目介绍章节
        if "section1_intro" in state:
            wiki.append(state["section1_intro"])

        # 添加模块架构章节
        if "section2_architecture" in state:
            wiki.append(state["section2_architecture"])

        # 添加架构图章节
        if "section3_diagram" in state:
            wiki.append(state["section3_diagram"])

        output = {
            "wiki": wiki,
            "source_id_list": []  # root文档不需要源码定位
        }

        # 保存输出文件
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "output", "root_doc.meta.json"
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"[INFO] Root文档生成完成，保存路径：{output_path}")
        return {"final_output": output}

    # 构建状态图
    graph = StateGraph(RootDocState)
    graph.add_node("fetch_modules", fetch_root_modules)
    graph.add_node("generate_intro", generate_intro)
    graph.add_node("generate_architecture", generate_architecture)
    graph.add_node("generate_diagram", generate_diagram)
    graph.add_node("merge", merge_sections)

    # 设置流程
    graph.set_entry_point("fetch_modules")
    graph.add_edge("fetch_modules", "generate_intro")
    graph.add_edge("generate_intro", "generate_architecture")
    graph.add_edge("generate_architecture", "generate_diagram")
    graph.add_edge("generate_diagram", "merge")
    graph.add_edge("merge", END)

    app = graph.compile(checkpointer=MemorySaver())
    return app

# ====================== 3. 独立运行入口 ======================
async def main():
    load_dotenv()
    print("=== 独立运行Root文档生成工作流 ===")

    llm = LLMInterface(model_name="gpt-4.1-2025-04-14", provider="openai")
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )

    if not await neo4j.test_connection():
        print("[ERR] Neo4j 连接失败")
        return

    print("[INFO] Neo4j 连接成功")

    app = root_doc_workflow(llm, neo4j)
    result = await app.ainvoke(
        {},
        config={"configurable": {"thread_id": "root-doc-generation"}}
    )

    neo4j.close()
    print("[INFO] 工作流执行完成")

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
