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
from chains.prompts.type_chart_prompt import MODULE_NAME_PROMPT, MODULE_NAME_SHORTEN_PROMPT
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


def build_slim_tree(full_tree: dict, draft_names: dict, with_explanation: bool = True) -> dict:
    """
    用阶段一的草稿名替换树中的name。
    with_explanation=True 时保留 explanation（当前树用），
    with_explanation=False 时只保留 nodeId、name、children（其他树用）。
    """
    node_id = str(full_tree["nodeId"])
    result = {
        "nodeId": node_id,
        "name": draft_names.get(node_id, full_tree.get("old_name", "")),
        "children": [build_slim_tree(c, draft_names, with_explanation) for c in full_tree.get("children", [])]
    }
    if with_explanation:
        explanation = full_tree.get("explanation", "")
        if explanation:
            result["explanation"] = explanation
    return result


def collect_names_from_tree(slim_tree: dict) -> list:
    """
    从精简树中提取所有节点名称的扁平列表（纯字符串）。
    """
    result = [slim_tree["name"]]
    for child in slim_tree.get("children", []):
        result.extend(collect_names_from_tree(child))
    return result


async def get_block_newname(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface):
    """
    两阶段为每个Block树生成新的模块名称：
    阶段一：逐棵子树生成草稿名
    阶段二：逐树精简，输入 = 当前树(带explanation) + 其他树的名字列表
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

    # ====================== 阶段一：并发生成草稿名 ======================
    all_block_names = {}

    # 先并发构建所有Block树
    all_full_trees = await asyncio.gather(
        *[get_block_tree(neo4j_interface, hb) for hb in high_blocks]
    )
    print(f"[INFO] 已构建 {len(all_full_trees)} 棵Block树")

    # 并发调用LLM为每棵树生成草稿名
    async def generate_draft_name(idx, block_tree):
        print(f"[INFO] 【阶段一】生成第 {idx+1}/{len(all_full_trees)} 棵树草稿名...")
        name_result = await name_generate_chain.ainvoke({"module_information": block_tree, "pom_content": pom_content})
        print(f"[INFO] 第 {idx+1} 棵树草稿名完成")
        return json.loads(name_result)

    draft_results = await asyncio.gather(
        *[generate_draft_name(i, tree) for i, tree in enumerate(all_full_trees)]
    )
    for result in draft_results:
        all_block_names.update(result)

    print(f"\n[INFO] 阶段一完成，共生成 {len(all_block_names)} 个草稿名")

    # ====================== 阶段二：逐树精简 ======================
    print(f"\n[INFO] 【阶段二】开始逐树精简名称...")

    shorten_chain = ChainFactory.create_generic_chain(llm_interface, MODULE_NAME_SHORTEN_PROMPT)

    for idx, full_tree in enumerate(all_full_trees):
        print(f"\n[INFO] 【阶段二】精简第 {idx+1}/{len(all_full_trees)} 棵树...")

        # 当前树：带 explanation
        current_tree = build_slim_tree(full_tree, all_block_names, with_explanation=True)

        # 其他树：只提取 {nodeId, name} 扁平列表
        other_names = []
        for j, other_tree in enumerate(all_full_trees):
            if j != idx:
                other_slim = build_slim_tree(other_tree, all_block_names, with_explanation=False)
                other_names.extend(collect_names_from_tree(other_slim))

        shorten_result = await shorten_chain.ainvoke({
            "current_tree": json.dumps(current_tree, ensure_ascii=False),
            "other_names": json.dumps(other_names, ensure_ascii=False)
        })
        print(f"[INFO] 精简结果: {shorten_result}")
        shorten_result = json.loads(shorten_result)

        # 用精简结果覆盖草稿名（后续树能看到已精简的名字）
        all_block_names.update(shorten_result)

    print(f"\n[INFO] 阶段二完成")

    # 将最终名称写入本地文件
    out_path = os.path.join(os.path.dirname(__file__), "block_new_names.json")
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(all_block_names, f, ensure_ascii=False, indent=2)
        print(f"\n[SUCCESS] 已将 {len(all_block_names)} 个Block的新名称写入 {out_path}")
    except Exception as e:
        print(f"[ERR] 写入文件失败: {e}")

    # 生成可视化树结构文件
    watch_trees = [build_slim_tree(ft, all_block_names, with_explanation=False) for ft in all_full_trees]
    watch_path = os.path.join(os.path.dirname(__file__), "block_new_names_watch.json")
    try:
        with open(watch_path, 'w', encoding='utf-8') as f:
            json.dump(watch_trees, f, ensure_ascii=False, indent=2)
        print(f"[SUCCESS] 已将树结构写入 {watch_path}")
    except Exception as e:
        print(f"[ERR] 写入watch文件失败: {e}")

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