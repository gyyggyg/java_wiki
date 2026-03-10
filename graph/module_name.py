import os
import re
import sys
import json
import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from chains.common_chains import ChainFactory
from interfaces.data_master import get_file
from interfaces.simple_validate_mermaid import SimpleMermaidValidator
from chains.prompts.type_chart_prompt import MODULE_NAME_PROMPT
from collections import deque, defaultdict
from time import sleep

# ====================== 1. 状态定义 ======================
from typing_extensions import TypedDict

class TrueState(TypedDict, total=False):
    graphman: list
    high_blocks: list
    father_blocks: list

# ====================== 辅助函数 ==============================


async def get_child_blocks(
    neo4j_interface: Neo4jInterface,
    block_node_id: str
) -> List[Dict[str, Any]]:
    """
    获取 Block 的直接子 Block 节点
    """
    query = """
    MATCH (parent:Block)-[:f2c]->(child:Block)
    WHERE parent.nodeId = $block_id
    RETURN child.nodeId AS nodeId, child.name AS name
    ORDER BY child.name
    """
    return await neo4j_interface.execute_query(query, {"block_id": block_node_id})


async def get_root_block(neo4j_interface: Neo4jInterface) -> Optional[Dict[str, Any]]:
    """
    获取根 Block 节点（name='root' 的 Block 节点）
    """
    query = """
    MATCH (n:Block)
    WHERE n.name = 'root'
    RETURN n.nodeId AS nodeId, n.name AS name
    LIMIT 1
    """
    result = await neo4j_interface.execute_query(query)
    return result[0] if result else None

async def get_block_tree(neo4j_interface: Neo4jInterface, high_block) -> dict:
    """
    递归构建Block树的JSON结构
    """
    node_id = high_block["nodeId"]

    # 获取当前节点的explanation（如果有）
    query = """
    MATCH (b:Block)
    WHERE b.nodeId = $node_id
    RETURN b.nodeId AS nodeId, b.name AS name, b.module_explaination AS explanation
    """
    result = await neo4j_interface.execute_query(query, {"node_id": node_id})

    if not result:
        return {"nodeId": node_id, "explanation": "", "children": []}

    current_node = result[0]
    old_name = current_node.get("name", "")
    explanation = current_node.get("explanation", "")

    # 递归获取所有子节点
    children_blocks = await get_child_blocks(neo4j_interface, node_id)
    children = []
    for child in children_blocks:
        child_tree = await get_block_tree(neo4j_interface, child)
        children.append(child_tree)

    return {
        "nodeId": node_id,
        "old_name": old_name,
        "explanation": explanation,
        "children": children
    } 

async def get_block_newname(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface):
    """
    为每个Block树生成新的模块名称
    """
    path = os.environ.get("POM_PATHS", "pom.xml")
    pom_content = get_file(path)
    name_generate_chain = ChainFactory.create_generic_chain(llm_interface, MODULE_NAME_PROMPT)
    root = await get_root_block(neo4j_interface)

    if not root:
        print("[ERR] 未找到root节点")
        return

    # 获取root下的一层Block（高层Block）
    high_blocks = await get_child_blocks(neo4j_interface, root['nodeId'])

    if not high_blocks:
        print("[WARN] root节点下没有子Block")
        return

    print(f"[INFO] 找到 {len(high_blocks)} 个高层Block节点")

    # 存储所有Block的新名称
    all_block_names = {}

    # 遍历每个高层Block，构建其树结构
    for idx, high_block in enumerate(high_blocks):
        print(f"\n[INFO] 处理第 {idx+1}/{len(high_blocks)} 个Block树: {high_block['name']}")

        # 获取该Block树的完整JSON结构
        block_tree = await get_block_tree(neo4j_interface, high_block)
        name_result = await name_generate_chain.ainvoke({"module_information": block_tree, "pom_content": pom_content})
        print(f"[INFO] 生成的新名称结果: {name_result}")
        name_result =  json.loads(name_result)
        all_block_names.update(name_result)

    # 将新名称写入本地文件
    out_path = os.path.join(os.path.dirname(__file__), "block_new_names.json")
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(all_block_names, f, ensure_ascii=False, indent=2)
        print(f"\n[SUCCESS] 已将 {len(all_block_names)} 个Block的新名称写入 {out_path}")
    except Exception as e:
        print(f"[ERR] 写入文件失败: {e}")

    return all_block_names



# ====================== 4. 独立运行入口 ======================
async def main():
    load_dotenv()
    print("=== 独立运行模块命名生成应用 ===")

    llm = LLMInterface(model_name="gpt-4.1", provider="openai")
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    if not await neo4j.test_connection():
        print("[ERR] Neo4j 连接失败")
        return

    # 调用主函数生成Block新名称
    result = await get_block_newname(llm, neo4j)

    if result:
        print(f"\n[INFO] 共生成 {len(result)} 个Block的新名称")
        print("\n[INFO] 部分结果预览:")
        for idx, (block_id, new_name) in enumerate(list(result.items())[:5]):
            print(f"  {block_id} -> {new_name}")
        if len(result) > 5:
            print(f"  ... 还有 {len(result) - 5} 个")

    neo4j.close()

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())