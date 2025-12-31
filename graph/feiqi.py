
from typing import Any, Dict
import sys
import os
import time
import asyncio
import json
from collections import defaultdict, deque
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph, END
from interfaces.simple_validate_mermaid import SimpleMermaidValidator
from langgraph.checkpoint.memory import MemorySaver
from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from typing_extensions import TypedDict
from typing import Annotated
from chains.prompts.select_block_file import (
    SELECT_BLOCK_PROMPT, SELECT_FILE_PROMPT, FETCH_BLOCK1_PROMPT, FETCH_BLOCK2_PROMPT,
    JUDGE_ROOT_FILE_PROMPT, JUDGE_FILES_IN_BLOCK_PROMPT,
    JUDGE_SIBLING_BLOCKS_PROMPT
)
from chains.common_chains import ChainFactory
from dotenv import load_dotenv
class NodeState(TypedDict, total=False):
    selected_blocks: list[str]
    selected_files: list[str]
    choice : int


def Node_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface, query: str, file_list: list[int]):
    select_block_chain = ChainFactory.create_generic_chain(llm_interface, SELECT_BLOCK_PROMPT)
    select_file_chain = ChainFactory.create_generic_chain(llm_interface, SELECT_FILE_PROMPT)
    fetch_block1_chain = ChainFactory.create_generic_chain(llm_interface, FETCH_BLOCK1_PROMPT)
    fetch_block2_chain = ChainFactory.create_generic_chain(llm_interface, FETCH_BLOCK2_PROMPT)
    async def decision_making(state: NodeState) -> NodeState:
        if file_list:
            return {"choice": 1}
        else:
            return {"choice": 0}

    async def fetch_block(state: NodeState) -> NodeState:
        neo4j_query="""
        MATCH (n:Block)-[:f2c]->(n0)-[:f2c]->(n1)
        WHERE n.name = 'root'
        RETURN n.semantic_explanation AS n_sema, n.nodeId AS n_nodeId, n.name AS n_name, n.child_blocks AS n_child,
        n0.semantic_explanation AS n0_sema, n0.nodeId AS n0_nodeId, n0.name AS n0_name, n0.child_blocks AS n0_child,
        n1.semantic_explanation AS n1_sema, n1.nodeId AS n1_nodeId, n1.name AS n1_name, n1.child_blocks AS n1_child
        """
        result = await neo4j_interface.execute_query(neo4j_query)
        relation_1 = ["father_id : child_id_list\n"]
        info_1 = []
        child_dict = {}
        block_info = {}
        child_dict[result[0]["n_nodeId"]] = result[0]["n_child"]
        block_info[result[0]["n_nodeId"]] = f"name:{result[0]['n_name']}, semantic_explanation:{result[0]['n_sema']}"
        for record in result:
            if record["n0_nodeId"] and record["n0_nodeId"] not in child_dict:
                child_dict[record["n0_nodeId"]] = record["n0_child"]
            if record["n0_nodeId"] and record["n0_nodeId"] not in block_info:
                block_info[record["n0_nodeId"]] = f"name:{record['n0_name']}, semantic_explanation:{record['n0_sema']}"
            if record["n1_nodeId"] and record["n1_nodeId"] not in block_info:
                block_info[record["n1_nodeId"]] = f"name:{record['n1_name']}, semantic_explanation:{record['n1_sema']}"           
        for key, value in child_dict.items():
            relation_1.append(f"{key}:{value}\n")
        for key, value in block_info.items():
            info_1.append(f"id:{key},{value}\n")
        high_father = await fetch_block1_chain.ainvoke({"query": query, "relation": "\n".join(relation_1), "all_information": "\n".join(info_1)})
        print(high_father)
        chosen_list = json.loads(high_father)["node_id"]
        query0 = """
        MATCH (n) 
        WHERE n.nodeId = $node_id 
        RETURN n.name AS name, n.semantic_explanation AS semantic_explanation, coalesce(n.child_blocks, []) as child_blocks, labels(n) AS labels
        """
        returns_block = []
        returns_file = []
        high_father_list = []
        for node_id in chosen_list:
            nodeId = int(node_id)
            result = await neo4j_interface.execute_query(query0, {"node_id": nodeId})
            if result[0]["labels"] == ["File"]:
                returns_file.append(nodeId)
            else:
                high_father_list.append(nodeId)
        for nodeId in high_father_list:
            info_2 = []
            relation_2 = []
            relation_2.append(f"下面是以id为{nodeId}顶点的树的信息：\n")
            result = await neo4j_interface.execute_query(query0, {"node_id": nodeId})
            child_blocks = result[0]["child_blocks"]
            relation_2.append(f"id为{nodeId}的节点可以划分为子节点{child_blocks}\n")
            info_2.append(f"id:{nodeId}, name:{result[0]['name']}, semantic_explanation:{result[0]['semantic_explanation']}\n")
            queue = deque([])
            for item in child_blocks:
                queue.append(int(json.loads(item)["nodeId"]))
            while queue:
                current = queue.popleft()
                result = await neo4j_interface.execute_query(query0, {"node_id": int(current)})
                if result[0]["labels"] == ["Block"]:
                    child_blocks = result[0]["child_blocks"]
                    relation_2.append(f"id为{current}的节点可以划分为子节点{child_blocks}\n")
                    info_2.append(f"id:{current}, name:{result[0]['name']}, semantic_explanation:{result[0]['semantic_explanation']}\n")
                    for item in child_blocks:
                        queue.append(int(json.loads(item)["nodeId"]))
            resultt = await fetch_block2_chain.ainvoke({"query": query, "relation": "\n".join(relation_2), "all_information": "\n".join(info_2)})
            returns_block.extend(json.loads(resultt)["block_id"])
        print("returns_file:",returns_file)
        print("returns_block:",returns_block)
        return {"selected_blocks" : returns_block, "selected_files" : returns_file}


    # async def select_block(state: NodeState) -> NodeState:
    #     neo4j_query1="""
    #     MATCH p = (a:File {nodeId: $file_id})<-[:f2c*]-(d:Block {name: 'root'})
    #     RETURN
    #     [n IN nodes(p) | {
    #         name: n.name,
    #         nodeId: n.nodeId,
    #         semantic_explanation: n.semantic_explanation
    #     }] AS pathNodes
    #     ORDER BY length(p)
    #     """
    #     all_info = []
    #     relations = []
    #     node_sema = defaultdict(str)
    #     for file_id in file_list:
    #         record = await neo4j_interface.execute_query(neo4j_query1, {"file_id": file_id})
    #         result = record[0]['pathNodes']
    #         chains = ""
    #         for node in result:
    #             if node["name"] != "root":
    #                 chains += f"{node['nodeId']}<-[:f2c]-"
    #             else:
    #                 chains += f"root\n"
    #             if node["nodeId"] not in node_sema:
    #                 node_sema[node["nodeId"]] = f"name: {node['name']}, semantic_explanation: {node['semantic_explanation']}"
    #         relations.append(chains)
    #     for node_id, info in node_sema.items():
    #         all_info.append(f"nodeId: {node_id}, {info}")
    #     all_info = "\n".join(all_info)
    #     selected_blocks = await select_block_chain.ainvoke({"query": query, "relation": "\n".join(relations), "all_information": all_info})
    #     print(json.loads(selected_blocks))
    #     return {"selected_blocks": json.loads(selected_blocks).get("block_id", [])}
    
    # async def select_file(state: NodeState) -> NodeState:
    #     neo4j_query2="""
    #     MATCH (n:Block {nodeId: $block_id})-[:f2c*]->(m:File)
    #     RETURN m.name AS name, m.nodeId AS nodeId, m.module_explaination AS module_explaination
    #     """
    #     files = []
    #     reasons = []
    #     for block_id in state["selected_blocks"]:
    #         all_info = []
    #         result = await neo4j_interface.execute_query(neo4j_query2, {"block_id": block_id})
    #         for record in result:
    #             all_info.append(f"nodeId: {record['nodeId']}, name: {record['name']}, module_explaination: {record['module_explaination']}")
    #         all_information = "\n".join(all_info)
    #         selected_files_node = await select_file_chain.ainvoke({"query": query, "all_information": all_information})
    #         files.extend(json.loads(selected_files_node).get("file_id", []))
    #         reasons.append(json.loads(selected_files_node).get("reason", []))
    #     print(files,len(files))
    #     print(reasons)
    #     return {"selected_files": list(files)}

    # =============================================================================
    # 从下往上搜索的辅助函数
    # =============================================================================

    async def get_block_semantic(block_id: int) -> str:
        """
        获取Block的语义解释

        参数:
            block_id: Block的nodeId

        返回:
            Block的semantic_explanation字符串
        """
        # 查询Block的语义解释
        query = """
        MATCH (b:Block {nodeId: $block_id})
        RETURN b.semantic_explanation AS semantic_explanation
        """
        result = await neo4j_interface.execute_query(query, {"block_id": block_id})
        return result[0]['semantic_explanation'] if result else ""

    async def query_all_files_under_block(block_id: int) -> list:
        """
        递归查询Block下所有File节点

        参数:
            block_id: Block的nodeId

        返回:
            File信息列表，每个元素包含 {nodeId, name, module_explaination}
        """
        # 使用递归关系 [:f2c*] 查询Block下所有File
        query = """
        MATCH (b:Block {nodeId: $block_id})-[:f2c*]->(f:File)
        RETURN DISTINCT
            f.nodeId AS file_id,
            f.name AS file_name,
            f.module_explaination AS module_explaination
        ORDER BY f.nodeId
        """
        result = await neo4j_interface.execute_query(query, {"block_id": block_id})

        # 转换为统一格式
        files = []
        for record in result:
            files.append({
                'nodeId': record['file_id'],
                'name': record['file_name'],
                'module_explaination': record['module_explaination']
            })
        return files

    async def judge_root_file(file_record: dict) -> dict:
        """
        判断root直连File的相关性

        参数:
            file_record: File记录，包含 {file_id, file_name, module_explaination}

        返回:
            {relevant: bool, reason: str}
        """
        # 创建root file判断的chain
        judge_root_file_chain = ChainFactory.create_generic_chain(llm_interface, JUDGE_ROOT_FILE_PROMPT)

        # 调用LLM判断
        result = await judge_root_file_chain.ainvoke({
            "query": query,
            "file_info": f"file_id: {file_record['file_id']}, file_name: {file_record['file_name']}, module_explaination: {file_record.get('module_explaination', '')}",
        })

        # 解析JSON结果
        return json.loads(result)

    async def judge_files_in_block(block_id: int, block_info: dict) -> dict:
        """
        判断Block下所有File的相关性（Layer 0使用）

        参数:
            block_id: Block的nodeId
            block_info: Block信息，包含 {parent_info: {semantic: ...}, files: [...]}

        返回:
        """
        # 创建判断chain
        judge_files_chain = ChainFactory.create_generic_chain(llm_interface, JUDGE_FILES_IN_BLOCK_PROMPT)

        # 格式化files信息
        files_info = []
        for file in block_info['files']:
            files_info.append(f"file_id: {file['nodeId']}, file_name: {file['name']}, module_explaination: {file.get('module_explaination', 'N/A')}")

        # 调用LLM判断
        result = await judge_files_chain.ainvoke({
            "query": query,
            "block_info": f"block_id: {block_id}, block_name: {block_info['name']}, block_semantic: {block_info['semantic']}",
            "files_info": "\n".join(files_info)
        })

        # 解析结果并添加block语义信息
        parsed_result = json.loads(result)
        return parsed_result

    async def judge_sibling_blocks(parent_info: dict, known_children: list, siblings: list) -> dict:
        """
        判断兄弟Block的相关性（Layer N使用）

        参数:
            parent_info: 父Block信息 {nodeId, name, semantic}
            known_children: 已知相关的子Block列表 [{nodeId, semantic_explanation}, ...]
            siblings: 兄弟Block列表 [{nodeId, semantic_explanation}, ...]

        返回:
            {relevant_siblings: [{nodeId, reason}, ...]}
        """
        # 创建判断chain
        judge_sibling_chain = ChainFactory.create_generic_chain(llm_interface, JUDGE_SIBLING_BLOCKS_PROMPT)

        # 格式化已知子Block信息

        # 格式化兄弟Block信息
        sibling_lines = []
        for sib in siblings:
            sibling_lines.append(
                f"- Block ID: {sib['nodeId']}, name: {sib['name']}, semantic: {sib.get('semantic_explanation', 'N/A')}"
            )
        sibling_blocks_info = "\n".join(sibling_lines) if sibling_lines else "无"

        # 调用LLM判断
        result = await judge_sibling_chain.ainvoke({
            "query": query,
            "parent_info": f"parent_info: nodeId: {parent_info['nodeId']}, name: {parent_info['name']}, semantic: {parent_info.get('semantic', '')}",
            "known_children_info": known_children,
            "sibling_blocks_info": sibling_blocks_info
        })

        # 解析结果
        return json.loads(result)

    # async def judge_files_with_context(block_id: int, sibling_info: dict, all_files: list, selected_files: list) -> dict:
    #     """
    #     判断新Block下File的相关性（带上下文）

    #     参数:
    #         block_id: Block的nodeId
    #         sibling_info: Block信息 {nodeId, reason, semantic_explanation}
    #         all_files: Block下所有File列表
    #         selected_files: 已选File的nodeId列表

    #     返回:
    #         {files: [{nodeId, relevant, reason}, ...]}
    #     """
    #     # 创建判断chain
    #     judge_files_context_chain = ChainFactory.create_generic_chain(llm_interface, JUDGE_FILES_WITH_CONTEXT_PROMPT)

    #     # 格式化已选File信息（简化版，只显示ID）
    #     if selected_files:
    #         selected_files_info = f"已选文件ID: {', '.join(map(str, selected_files))}"
    #     else:
    #         selected_files_info = "暂无已选文件"

    #     # 格式化当前Block下的File信息
    #     files_info_lines = []
    #     for file in all_files:
    #         files_info_lines.append(
    #             f"- File ID: {file['nodeId']}, File Name: {file['name']}, "
    #             f"Module Explanation: {file.get('module_explaination', 'N/A')}"
    #         )
    #     files_info = "\n".join(files_info_lines)

    #     # 调用LLM判断
    #     result = await judge_files_context_chain.ainvoke({
    #         "query": query,
    #         "block_id": block_id,
    #         "block_semantic": sibling_info.get('semantic_explanation', ''),
    #         "selection_reason": sibling_info.get('reason', '该Block被判断为相关'),
    #         "selected_files_info": selected_files_info,
    #         "files_info": files_info
    #     })

    #     # 解析结果
    #     return json.loads(result)

    async def process_parent_group(parent_id: int, group_info: dict) -> dict:
        """
        处理单个父Block分组（Layer N的核心逻辑）

        参数:
            parent_id: 父Block的nodeId
            group_info: 分组信息 {parent_info, children_in_layer, siblings}
            selected_files: 全局已选File列表

        返回:
            {should_continue: bool, new_files: [file_id, ...]}
        """
        parent_info = group_info['parent_info']
        children = group_info['children_in_layer']
        siblings = group_info['siblings']

        # 检查终止条件1：父节点是root
        if parent_info['name'] == 'root':
            print(f"[Layer N] 父Block {parent_id} 是root，终止向上")
            return {'should_continue': False, 'new_files': []}

        # 过滤有效的兄弟Block（排除nodeId为None的）
        valid_siblings = [s for s in siblings if s.get('nodeId')]

        # 检查终止条件2：没有兄弟（独生子）
        if not valid_siblings:
            print(f"[Layer N] 父Block {parent_id} 下只有已选子Block，无其他兄弟，终止向上")
            return {'should_continue': False, 'new_files': []}

        # 判断兄弟Block相关性
        print(f"[Layer N] 判断父Block {parent_id} 的 {len(valid_siblings)} 个兄弟Block")
        sibling_result = await judge_sibling_blocks(parent_info, children, valid_siblings)
        relevant_siblings = sibling_result.get('relevant_siblings', [])

        # 如果兄弟都不相关
        if not relevant_siblings:
            print(f"[Layer N] 所有兄弟Block都不相关")
            # 检查是否是独生子（只有一个子Block被选中）
            if len(children) == 1:
                print(f"[Layer N] 且只有1个子Block被选中，满足终止条件")
                return {'should_continue': False, 'new_files': []}
            else:
                print(f"[Layer N] 有{len(children)}个子Block被选中，仍然终止")
                return {'should_continue': False, 'new_files': []}

        # 有相关的兄弟Block，处理每个相关兄弟
        print(f"[Layer N] 找到 {len(relevant_siblings)} 个相关兄弟Block")
        new_files = []

        for sibling in relevant_siblings:
            sibling_id = sibling['nodeId']
            print(f"[Layer N]   处理兄弟Block {sibling_id}")

            # 查询该兄弟Block下所有File
            all_files = await query_all_files_under_block(sibling_id)

            if all_files:
                print(f"[Layer N]     该Block下有 {len(all_files)} 个File")
                # 判断File相关性
                sibling_self_info = await get_block_semantic(sibling_id)
                sibling_info = {"files":all_files, "semantic":sibling_self_info}

                file_result = await judge_files_in_block(sibling_id, sibling_info)

                # 收集相关File
                if json.loads(file_result).get('relevant_files', ""):
                    for file in json.loads(file_result).get('relevant_files', []):
                        new_files.append(file['id'])
                else:


        return {'should_continue': True, 'new_files': list(set(new_files))}

    # =============================================================================
    # 从下往上搜索的主函数
    # =============================================================================

    async def select_from_bottom_up(state: NodeState) -> NodeState:
        """
        从下往上逐层筛选相关File和Block（替换原来的select_block和select_file）

        参数:
            state: NodeState（未使用，保持接口一致）

        返回:
            {selected_files: [file_id, ...], selected_blocks: [block_id, ...]}
        """
        print("\n" + "="*80)
        print("开始从下往上搜索")
        print("="*80)

        selected_files = []  # 所有相关的File
        selected_blocks = []  # 需要整体返回的Block

        # ========== Layer 0: 处理初始File ==========
        print("\n=== Layer 0: 处理初始File ===")

        # 1. 批量查询每个File的父Block
.

        # 5. 汇总Layer 0结果
        current_layer_blocks = []

        for block_id, result in zip(block_ids, results):
            print(f"\nBlock {block_id}:")

            if not result.get('relevant_files'):
                print(f"  所有File都不相关，跳过该Block")
                continue

            # 添加相关File
            for file in result.get('relevant_files', []):
                selected_files.append(file['id'])

            # Block加入selected_blocks和下一层处理
            selected_blocks.append(block_id)
            current_layer_blocks.append(block_id)

        print(f"\nLayer 0 完成:")
        print(f"  selected_files: {len(selected_files)} 个")
        print(f"  selected_blocks: {len(selected_blocks)} 个")
        print(f"  下一层待处理Block: {len(current_layer_blocks)} 个")

        # ========== Layer N (N>=1): 逐层向上 ==========
        layer_num = 1

        while current_layer_blocks:

            # 1. 批量查询父Block和兄弟Block
            parent_query = """
            UNWIND $child_ids AS child_id
            MATCH (child:Block {nodeId: child_id})<-[:f2c]-(parent:Block)
            OPTIONAL MATCH (parent)-[:f2c]->(sibling:Block)
            WHERE sibling.nodeId <> child_id
            RETURN
                child.nodeId AS child_id,
                parent.nodeId AS parent_id,
                parent.name AS parent_name,
                parent.semantic_explanation AS parent_semantic,
                collect(DISTINCT {
                    nodeId: sibling.nodeId,
                    semantic_explanation: sibling.semantic_explanation
                }) AS siblings
            """

            records = await neo4j_interface.execute_query(parent_query, {"child_ids": current_layer_blocks})

            # 2. 按父Block分组
            parent_groups = defaultdict(lambda: {
                'parent_info': {},
                'children_in_layer': [],
                'siblings': []
            })

            for rec in records:
                parent_id = rec['parent_id']
                if not parent_groups[parent_id]['parent_info']:
                    parent_groups[parent_id]['parent_info'] = {
                        'nodeId': parent_id,
                        'name': rec['parent_name'],
                        'semantic': rec['parent_semantic']
                    }
                parent_groups[parent_id]['children_in_layer'].append(rec['child_id'])

                # 去重添加siblings
                for sib in rec['siblings']:
                    if sib.get('nodeId') and sib not in parent_groups[parent_id]['siblings']:
                        parent_groups[parent_id]['siblings'].append(sib)

            print(f"按父Block分组: {len(parent_groups)} 个分组")

            # 3. 处理每个父Block分组
            next_layer_blocks = []

            for parent_id, group_info in parent_groups.items():
                print(f"\n处理父Block {parent_id} (子Block: {group_info['children_in_layer']})")

                # 处理该分组
                result = await process_parent_group(parent_id, group_info)

                if result['should_continue']:
                    # 有相关兄弟，继续向上
                    next_layer_blocks.append(parent_id)
                    selected_files.extend(result['new_files'])

                    # 更新selected_blocks：用父Block替换子Block
                    for child_id in group_info['children_in_layer']:
                        if child_id in selected_blocks:
                            selected_blocks.remove(child_id)
                    selected_blocks.append(parent_id)

                    print(f"  → 用父Block {parent_id} 替换子Block {group_info['children_in_layer']}")

            # 4. 准备下一层
            current_layer_blocks = next_layer_blocks
            layer_num += 1

            print(f"\nLayer {layer_num-1} 完成:")
            print(f"  selected_files: {len(selected_files)} 个")
            print(f"  selected_blocks: {len(selected_blocks)} 个")
            print(f"  下一层待处理Block: {len(current_layer_blocks)} 个")

        # ========== 最终结果 ==========
        print(f"\n{'='*80}")
        print("从下往上搜索完成")
        print(f"{'='*80}")
        print(f"最终选中 {len(set(selected_files))} 个File (去重)")
        print(f"最终选中 {len(set(selected_blocks))} 个Block (去重)")

        return {
            "selected_files": list(set(selected_files)),  # 去重
            "selected_blocks": list(set(selected_blocks))  # 去重
        }

    # 定义条件路由函数
    def route_decision(state: NodeState) -> str:
        """根据 choice 的值决定下一个节点"""
        # choice == 1 表示有file_list，使用从下往上搜索
        # choice == 0 表示没有file_list，使用从上往下搜索
        if state["choice"] == 1:
            return "select_from_bottom_up"  # 使用新的从下往上搜索
        else:
            return "fetch_block"  # 使用原来的从上往下搜索

    # 构建状态图
    graph = StateGraph(NodeState)

    # 添加节点
    graph.add_node("decision_making", decision_making)  # 决策节点
    graph.add_node("fetch_block", fetch_block)  # 从上往下搜索（保留）
    graph.add_node("select_from_bottom_up", select_from_bottom_up)  # 从下往上搜索（新）

    # 注意：select_block 和 select_file 已被 select_from_bottom_up 替代，不再需要

    # 设置入口点
    graph.set_entry_point("decision_making")

    # 添加条件边：根据decision_making的结果路由
    graph.add_conditional_edges("decision_making", route_decision)

    # 添加边：两条路径都直接结束
    graph.add_edge("fetch_block", END)  # 从上往下搜索完成后结束
    graph.add_edge("select_from_bottom_up", END)  # 从下往上搜索完成后结束

    # 编译图
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
        query = "代码库中控制订单价格的逻辑有哪些？"
        # file_list = [271, 173, 571, 122, 204, 406, 551, 171, 408, 525, 206, 538, 315, 293, 174, 205, 383, 339, 203, 172, 524, 356, 219, 157, 213, 184, 416, 422, 91, 280, 333, 220, 564, 556, 552, 93, 384, 129, 549, 420, 92, 515, 185, 134, 407, 105, 421, 218, 462, 130, 510, 519, 564, 300, 566, 374, 567, 308, 102, 183, 464, 237, 301, 365, 161, 409, 454, 217, 467, 418, 461, 540]
        file_list = []
        if not await neo4j.test_connection():
            print("Neo4j连接失败")
            return
        app = Node_app(llm, neo4j, query, file_list)
        result = await app.ainvoke(
            {}, 
            config={"configurable": {"thread_id": "standalone-api"}}
        )
        neo4j.close()
    
    asyncio.run(main())
