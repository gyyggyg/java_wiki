import os
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
from chains.prompts.type_chart_prompt import PROJECT_MODULE_PROMPT
from collections import deque
from time import sleep

# ====================== 1. 状态定义 ======================
from typing_extensions import TypedDict

class TrueState(TypedDict, total=False):
    graphman: list
    high_blocks: list
    father_blocks: list
    output: Dict

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

async def get_high_directory(neo4j_interface: Neo4jInterface):
    root_block = await get_root_block(neo4j_interface)
    if not root_block:
        return []
    first_layer_blocks = await get_child_blocks(neo4j_interface, root_block["nodeId"])
    high_directory = []
    query = """
    MATCH (d:Directory)
    WHERE d.name = $dir_name
    RETURN d.nodeId AS nodeId, d.name AS name
    """
    for block in first_layer_blocks:
        item = (block['nodeId'], block['name'])
        q = deque([item])
        while q:
            target = q.popleft()
            result = await neo4j_interface.execute_query(query, {"dir_name":target[1]})
            if result:
                high_directory.append(result[0]['nodeId'])
                print(f"高层目录节点: {target[1]} ({result[0]['nodeId']})")
            else:
                child_blocks = await get_child_blocks(neo4j_interface, target[0])
                for child in child_blocks:
                    q.append((child['nodeId'], child['name']))
    return high_directory

async def get_depth_ratio(neo4j_interface: Neo4jInterface, high_directory: List[str]) -> Dict[str, int]:
    ratio_map = {}

    # 查询：计算每个Directory对应Block的当前深度和到最深叶子的总深度
    query = """
    UNWIND $dir_ids AS dir_id
    MATCH (d:Directory {nodeId: dir_id})
    MATCH (root:Block {name: 'root'})
    MATCH path1 = (root)-[:f2c*]->(b:Block {name: d.name})
    WITH d, b, length(path1) AS currentDepth
    OPTIONAL MATCH path2 = (b)-[:f2c*]->(leaf:Block)
    WHERE NOT (leaf)-[:f2c]->(:Block)
    WITH b, currentDepth,
         CASE WHEN max(length(path2)) IS NULL THEN 0 ELSE max(length(path2)) END AS maxSubDepth
    WITH b, currentDepth, currentDepth + maxSubDepth AS totalDepth
    RETURN b.nodeId AS blockId,
           b.name AS name,
           currentDepth,
           totalDepth,
           CASE WHEN totalDepth = 0 THEN 0.0
                ELSE toFloat(currentDepth) / totalDepth
           END AS ratio
    """
    results = await neo4j_interface.execute_query(query, {"dir_ids": high_directory})

    for record in results:
        ratio_map[record['blockId']] = {
            'name': record['name'],
            'currentDepth': record['currentDepth'],
            'totalDepth': record['totalDepth'],
            'ratio': record['ratio']
        }

    return ratio_map

async def expand_by_depth_threshold(neo4j_interface: Neo4jInterface, ratio_map,depth_threshold) -> Dict[str, Dict[str, Any]]:
    target_list = []
    for block_id, data in list(ratio_map.items()):
        if data['ratio'] < depth_threshold:
            k = data['totalDepth']*depth_threshold - data['currentDepth']
            q = deque([block_id])
            for i in range(int(k)):
                lens = len(q)
                for i in range(lens):
                    tar = q.popleft()
                    childs = await get_child_blocks(neo4j_interface, tar)
                    if childs:
                        for child in childs:
                            q.append(child['nodeId'])
            target_list.extend(list(q))
        else:
            target_list.append(block_id)
    return target_list

def module_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface):
    draw_module_chain = ChainFactory.create_generic_chain(llm_interface, PROJECT_MODULE_PROMPT)

    async def generate_in(state: TrueState) -> TrueState:
        """
        生成模块架构图
        """
        depth_threshold = float(os.environ.get("EXPAND_THRESHOLD", "0.5"))
        high_blocks = await get_high_directory(neo4j_interface)
        ratio_map = await get_depth_ratio(neo4j_interface, high_blocks)
        target_list = await expand_by_depth_threshold(neo4j_interface, ratio_map, depth_threshold)
        print(f"最终展开的模块节点 {target_list}")
        return {"graphman": target_list}


    async def draw_module(state: TrueState) -> TrueState:
        """
        生成模块架构图
        """
        path = os.environ.get("POM_PATHS", "pom.xml")
        pom_content = get_file(path)
        new_names = json.loads(get_file(r"E:\\github_clone\\java_wiki\\gy\\graph\\block_new_names.json"))
        target_list = state['graphman']

        # 获取从root到target_list中所有节点的路径
        query_paths = """
        MATCH (root:Block)
        WHERE root.name = 'root'
        UNWIND $target_ids AS target_id
        MATCH path = (root)-[:f2c*]->(target:Block {nodeId: target_id})
        WITH nodes(path) AS path_nodes
        UNWIND range(0, size(path_nodes)-2) AS i
        WITH path_nodes[i] AS parent, path_nodes[i+1] AS child
        RETURN DISTINCT parent.nodeId AS parent_id, parent.name AS parent_name,
               child.nodeId AS child_id, child.name AS child_name
        """
        # query_explanation = """
        # UNWIND $target_ids AS target_id
        # MATCH (b:Block {nodeId: target_id})
        # RETURN b.name AS block_name, b.module_explaination AS explanation
        # """

        # path_results = await asyncio.gather(
        #     neo4j_interface.execute_query(query_paths, {"target_ids": target_list})
        #     # neo4j_interface.execute_query(query_explanation, {"target_ids": target_list})
        # )
        path_results = await neo4j_interface.execute_query(query_paths, {"target_ids": target_list})
        root = await get_root_block(neo4j_interface)
        root_id = root['nodeId'] if root else None

        # 构建父子关系字典和收集所有节点ID
        f2c = {}
        id_name_map = {}
        # explanations = []
        path = {}


        for record in path_results:
            parent_id = record['parent_id']
            parent_name = record['parent_name']
            id_name_map[parent_id] = parent_name
            child_name = record['child_name']
            child_id = record['child_id']
            id_name_map[child_id] = child_name
            if child_name.startswith(parent_name) and child_name != parent_name:
                suffix = child_name[len(parent_name):].lstrip("/")
                path[child_id] = f"../{suffix}" if suffix else "../"
            else:
                path[child_id] = child_name

            if parent_id not in f2c:
                f2c[parent_id] = []
            if child_id not in f2c[parent_id]:
                f2c[parent_id].append(child_id)


        # 构建嵌套树结构
        def build_tree(node_id) -> dict:
            children = f2c.get(node_id, [])
            return {
                "name": new_names.get(str(node_id)),
                "id": node_id,
                "path": path.get(node_id),
                "children": [build_tree(child) for child in children]
            }

        tree_structure = build_tree(root_id)
        project_information = tree_structure.get("children", [])
        # if explanation_results:
        #     for record in explanation_results:
        #         explanations.append(f"{record['block_name']}: {record['explanation']}")

        mermaid_result = await draw_module_chain.ainvoke({
            "project_information": project_information,
            "pom_content": pom_content
            # "module_explanation": "\n".join(explanations)
        })
        # module_result = json.loads(mermaid_result)["mermaid"]
        # print(f"生成的模块架构图 mermaid 内容:\n{json.loads(mermaid_result)['mapping']}")
        # out_path = os.path.join(os.path.dirname(__file__), "module.md")
        # with open(out_path, "w", encoding="utf-8") as f:
        #     f.write("```mermaid\n")
        #     f.write("---\nconfig:\n  look: neo\n  theme: neutral\n  flowchart:\n    nodeSpacing: 60\n    rankSpacing: 100\n    curve: basis\n    htmlLabels: true\n    useMaxWidth: true\n---\n")
        #     f.write(module_result)
        #     f.write("\n```")
        # resultt = json.dumps({"mermaid": module_result, "mapping": {}, "neo4j_id": json.loads(mermaid_result)['mapping']}, ensure_ascii=False, indent=4)
        # out_path = os.path.join(os.path.dirname(__file__), "module.json")
        # with open(out_path, "w", encoding="utf-8") as f:
        #     f.write(resultt) 
        # print(f"模块架构图已生成，保存路径：{out_path}")
        return {"output": json.loads(mermaid_result)} 



    graph = StateGraph(TrueState)
    graph.add_node("generate_in", generate_in)
    graph.add_node("draw_module", draw_module)
    graph.set_entry_point("generate_in")
    graph.add_edge("generate_in", "draw_module")
    graph.add_edge("draw_module", END)

    app = graph.compile(checkpointer=MemorySaver())
    return app

# ====================== 4. 独立运行入口 ======================
async def main():
    load_dotenv()
    print("=== 独立运行模块架构树生成应用 ===")

    llm = LLMInterface(model_name="gpt-4.1-2025-04-14", provider="openai")
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    if not await neo4j.test_connection():
        print("[ERR] Neo4j 连接失败")
        return

    app = module_app(llm, neo4j)
    result = await app.ainvoke(
        {},
        config={"configurable": {"thread_id": "standalone-api"}}
    )
    neo4j.close()

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())