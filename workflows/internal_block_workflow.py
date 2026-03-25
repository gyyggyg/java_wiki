import os
import sys
import json
import asyncio
from typing import Any, Dict, List
from collections import deque
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from chains.common_chains import ChainFactory
from chains.prompts.internal_block_prompt import (
    INTERNAL_BLOCK_OVERVIEW_PROMPT,
    INTERNAL_BLOCK_CHILDREN_PROMPT
)
from interfaces.data_master import get_file

# 项目根目录（java_wiki）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ====================== 1. 状态定义 ======================
class InternalBlockState(TypedDict, total=False):
    # 输入
    root_id: str
    # 遍历结果
    intermediate_blocks: List[Dict]  # 需要生成文档的中间层Block列表（子节点全是Block）
    file_leaves: Dict[str, str]  # {nodeId: folder_path} - 纯File叶子Block
    file_block_leaves: Dict[str, str]  # {nodeId: folder_path} - Block+File混合叶子Block
    # 生成结果
    generated_docs: List[Dict]  # [{block_id, doc_path, wiki}, ...] - 生成的文档
    # 最终输出
    final_output: Dict

# ====================== 2. 辅助函数 ======================

async def get_root_block(neo4j_interface: Neo4jInterface) -> Dict[str, Any]:
    """获取root Block节点"""
    query = """
    MATCH (n:Block)
    WHERE n.name = 'root'
    RETURN n.nodeId AS nodeId, n.name AS name
    LIMIT 1
    """
    result = await neo4j_interface.execute_query(query)
    return result[0] if result else None


async def get_child_blocks(
    neo4j_interface: Neo4jInterface,
    block_node_id: str
) -> List[Dict[str, Any]]:
    """获取Block的直接子Block节点"""
    query = """
    MATCH (parent:Block)-[:f2c]->(child:Block)
    WHERE parent.nodeId = $block_id
    RETURN child.nodeId AS nodeId,
           child.name AS name,
           child.module_explaination AS module_explaination
    ORDER BY child.name
    """
    return await neo4j_interface.execute_query(query, {"block_id": block_node_id})


async def check_direct_files(
    neo4j_interface: Neo4jInterface,
    block_node_id: str
) -> int:
    """检查Block是否直接连接File节点"""
    query = """
    MATCH (b:Block)-[:f2c]->(f:File)
    WHERE b.nodeId = $block_id
    RETURN count(f) AS file_count
    """
    result = await neo4j_interface.execute_query(query, {"block_id": block_node_id})
    return result[0]["file_count"] if result else 0


async def get_block_info(
    neo4j_interface: Neo4jInterface,
    block_node_id: str
) -> Dict[str, Any]:
    """获取Block的详细信息"""
    query = """
    MATCH (b:Block)
    WHERE b.nodeId = $block_id
    RETURN b.nodeId AS nodeId,
           b.name AS name,
           b.module_explaination AS module_explaination
    """
    result = await neo4j_interface.execute_query(query, {"block_id": block_node_id})
    return result[0] if result else None


# ====================== 3. 工作流定义 ======================
def internal_block_workflow(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface):
    # 创建LLM链
    overview_chain = ChainFactory.create_generic_chain(llm_interface, INTERNAL_BLOCK_OVERVIEW_PROMPT)
    children_chain = ChainFactory.create_generic_chain(llm_interface, INTERNAL_BLOCK_CHILDREN_PROMPT)

    # 加载Block名称映射
    block_names = json.loads(get_file(os.path.join(PROJECT_ROOT, "graph", "block_new_names.json")))

    async def traverse_tree(state: InternalBlockState) -> InternalBlockState:
        """
        阶段1：先一次性遍历整棵Block树，预先计算所有路径
        三路分类：
        - 子节点全是Block → 中间层，生成文档
        - 子节点全是File → file_leaves
        - 子节点有Block也有File → file_block_leaves
        """
        root = await get_root_block(neo4j_interface)
        if not root:
            print("[ERROR] 未找到root Block节点")
            return {"intermediate_blocks": [], "file_leaves": {}, "file_block_leaves": {}}

        root_id = root["nodeId"]
        print(f"[INFO] 找到root Block: {root_id}")
        print(f"[INFO] 开始遍历整棵Block树...")

        intermediate_blocks = []  # 中间层Block列表（子节点全是Block）
        file_leaves = {}  # 纯File叶子Block
        file_block_leaves = {}  # Block+File混合叶子Block

        async def traverse_recursive(block_id: str, block_name: str, folder_path: str):
            """
            递归遍历Block树
            """
            file_count = await check_direct_files(neo4j_interface, block_id)
            children = await get_child_blocks(neo4j_interface, block_id)

            has_files = file_count > 0
            has_blocks = len(children) > 0

            print(f"  [DEBUG] {block_name} ({block_id}): files={file_count}, blocks={len(children)}")

            if has_files and not has_blocks:
                # 纯File叶子Block
                file_leaves[block_id] = folder_path
                print(f"    → [FILE_LEAF] 写入file_leaves.json")
            elif has_files and has_blocks:
                # Block+File混合叶子Block
                file_block_leaves[block_id] = folder_path
                print(f"    → [FILE_BLOCK_LEAF] 写入file_block_leaves.json，继续递归子Block")
                # 继续递归处理子Block
                for child in children:
                    child_id = child["nodeId"]
                    child_name = block_names.get(str(child_id), child["name"])
                    child_folder_path = os.path.join(folder_path, child_name)
                    await traverse_recursive(child_id, child_name, child_folder_path)
            elif has_blocks:
                # 纯Block中间层，生成wiki json
                intermediate_blocks.append({
                    "block_id": block_id,
                    "block_name": block_name,
                    "folder_path": folder_path,
                    "children": children
                })
                print(f"    → [INTERMEDIATE] 生成wiki json，继续递归子Block")

                for child in children:
                    child_id = child["nodeId"]
                    child_name = block_names.get(str(child_id), child["name"])
                    child_folder_path = os.path.join(folder_path, child_name)
                    await traverse_recursive(child_id, child_name, child_folder_path)
            else:
                print(f"    → [WARN] 没有子节点，跳过")

        # 从root的子节点开始遍历
        root_children = await get_child_blocks(neo4j_interface, root_id)
        print(f"[INFO] root有 {len(root_children)} 个子Block")

        # 构建输出基础路径（相对于项目根目录）
        base_output_path = "output"

        for child in root_children:
            block_id = child["nodeId"]
            block_name = block_names.get(str(block_id), child["name"])
            folder_path = os.path.join(base_output_path, block_name)
            await traverse_recursive(block_id, block_name, folder_path)

        print(f"[INFO] 树遍历完成:")
        print(f"  - 中间层Block（纯Block子节点，生成文档）: {len(intermediate_blocks)} 个")
        print(f"  - 纯File叶子Block: {len(file_leaves)} 个")
        print(f"  - Block+File混合叶子Block: {len(file_block_leaves)} 个")

        return {
            "root_id": root_id,
            "intermediate_blocks": intermediate_blocks,
            "file_leaves": file_leaves,
            "file_block_leaves": file_block_leaves,
            "generated_docs": []
        }

    async def generate_docs_concurrent(state: InternalBlockState) -> InternalBlockState:
        """
        阶段2：并发生成所有中间层Block的文档
        使用信号量控制最大并发数
        """
        intermediate_blocks = state["intermediate_blocks"]

        if not intermediate_blocks:
            print("[INFO] 没有需要生成文档的中间层Block")
            return {"generated_docs": []}

        # 从环境变量读取最大并发数，默认10
        max_concurrent = int(os.environ.get("MAX_CONCURRENT_BLOCKS", "10"))
        print(f"[INFO] 开始并发生成文档，最大并发数: {max_concurrent}")
        print(f"[INFO] 共需生成 {len(intermediate_blocks)} 个文档")

        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)
        generated_docs = []

        async def generate_single_doc(block_info: Dict, index: int):
            """
            生成单个Block的文档（带信号量控制）
            """
            async with semaphore:
                block_id = block_info["block_id"]
                block_name = block_info["block_name"]
                folder_path = block_info["folder_path"]
                children = block_info["children"]

                print(f"  [{index}/{len(intermediate_blocks)}] 开始生成: {block_name} ({block_id})")

                try:
                    # 获取Block详细信息
                    block_detail = await get_block_info(neo4j_interface, block_id)

                    # 准备子模块信息（用于第一章节的详细信息）
                    child_modules_info = []
                    child_node_ids = []  # 收集所有子节点的nodeId

                    for idx, child in enumerate(children, 1):
                        child_name = block_names.get(str(child["nodeId"]), child["name"])
                        child_node_ids.append(child["nodeId"])
                        child_modules_info.append(
                            f"{idx}. 模块名称: {child_name}\n"
                            f"   模块ID: {child['nodeId']}\n"
                            f"   功能说明: {child['module_explaination'] or '暂无说明'}"
                        )
                    child_modules_info_str = "\n\n".join(child_modules_info)

                    # 准备子模块信息（用于第二章节）
                    child_modules_text = []
                    for idx, child in enumerate(children, 1):
                        child_name = block_names.get(str(child["nodeId"]), child["name"])
                        child_modules_text.append(
                            f"{idx}. 模块名称: {child_name}\n"
                            f"   模块ID: {child['nodeId']}\n"
                            f"   功能说明: {child['module_explaination'] or '暂无说明'}"
                        )
                    child_modules_str = "\n\n".join(child_modules_text)

                    # 并发调用两个LLM生成章节
                    overview_task = overview_chain.ainvoke({
                        "block_name": block_name,
                        "block_explaination": block_detail["module_explaination"] or "暂无说明",
                        "child_modules_info": child_modules_info_str
                    })

                    children_task = children_chain.ainvoke({
                        "child_modules": child_modules_str
                    })

                    # 等待两个任务完成
                    overview_content, children_content = await asyncio.gather(
                        overview_task,
                        children_task
                    )

                    # 解析章节二的JSON输出
                    children_data = json.loads(children_content)

                    # 构建wiki数组
                    # 第一章节的neo4j_id包含当前Block和所有子Block的nodeId
                    wiki = [
                        {
                            "markdown": overview_content,
                            "neo4j_id": {"1": [block_id] + child_node_ids}
                        },
                        {
                            "markdown": children_data["markdown"],
                            "neo4j_id": children_data["mapping"]
                        }
                    ]

                    # 保存文档路径（folder_path是相对路径，需转为绝对路径写文件）
                    doc_filename = f"{block_name}.md"
                    doc_path = os.path.join(PROJECT_ROOT, folder_path, doc_filename)

                    doc_result = {
                        "block_id": block_id,
                        "block_name": block_name,
                        "doc_path": doc_path,
                        "wiki": wiki
                    }

                    print(f"  [{index}/{len(intermediate_blocks)}] 完成: {block_name}")
                    return doc_result

                except Exception as e:
                    print(f"  [{index}/{len(intermediate_blocks)}] 失败: {block_name} - {str(e)}")
                    return None

        # 并发执行所有文档生成任务
        tasks = [
            generate_single_doc(block, i + 1)
            for i, block in enumerate(intermediate_blocks)
        ]

        results = await asyncio.gather(*tasks)

        # 过滤掉失败的任务
        generated_docs = [doc for doc in results if doc is not None]

        print(f"[INFO] 文档生成完成: 成功 {len(generated_docs)}/{len(intermediate_blocks)}")

        return {"generated_docs": generated_docs}

    async def save_results(state: InternalBlockState) -> InternalBlockState:
        """
        保存处理结果到文件
        """
        file_leaves = state["file_leaves"]
        file_block_leaves = state["file_block_leaves"]
        generated_docs = state["generated_docs"]

        internal_result_path = os.path.join(PROJECT_ROOT, "internal_result")
        os.makedirs(internal_result_path, exist_ok=True)

        # 1. 保存纯File叶子Block映射
        file_leaves_path = os.path.join(internal_result_path, "file_leaves.json")
        with open(file_leaves_path, "w", encoding="utf-8") as f:
            json.dump(file_leaves, f, ensure_ascii=False, indent=2)
        print(f"[INFO] 纯File叶子Block映射已保存: {file_leaves_path}")

        # 2. 保存Block+File混合叶子Block映射
        file_block_leaves_path = os.path.join(internal_result_path, "file_block_leaves.json")
        with open(file_block_leaves_path, "w", encoding="utf-8") as f:
            json.dump(file_block_leaves, f, ensure_ascii=False, indent=2)
        print(f"[INFO] Block+File混合叶子Block映射已保存: {file_block_leaves_path}")

        # 3. 保存每个生成的文档
        for doc in generated_docs:
            doc_path = doc["doc_path"]

            # 保存为JSON格式（遵循CLAUDE.md规范）
            output_data = {
                "wiki": doc["wiki"],
                "source_id_list": []  # 中间层Block文档不需要源码定位
            }

            json_path = doc_path.replace(".md", ".meta.json")

            # Windows长路径支持：添加\\?\前缀
            if os.name == 'nt' and not json_path.startswith('\\\\?\\'):
                json_path = '\\\\?\\' + os.path.abspath(json_path)
                dir_path = os.path.dirname(json_path)
            else:
                dir_path = os.path.dirname(json_path)

            # 确保目录存在
            os.makedirs(dir_path, exist_ok=True)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            print(f"[INFO] 文档已保存: {json_path}")

        final_output = {
            "file_leaves": file_leaves,
            "file_block_leaves": file_block_leaves,
            "generated_docs_count": len(generated_docs),
            "summary": {
                "total_file_leaves": len(file_leaves),
                "total_file_block_leaves": len(file_block_leaves),
                "total_intermediate_docs": len(generated_docs)
            }
        }

        return {"final_output": final_output}

    # 构建状态图
    graph = StateGraph(InternalBlockState)
    graph.add_node("traverse", traverse_tree)
    graph.add_node("generate", generate_docs_concurrent)
    graph.add_node("save", save_results)

    # 设置流程
    graph.set_entry_point("traverse")
    graph.add_edge("traverse", "generate")
    graph.add_edge("generate", "save")
    graph.add_edge("save", END)

    app = graph.compile(checkpointer=MemorySaver())
    return app

# ====================== 4. 独立运行入口 ======================
async def main():
    load_dotenv()
    print("=== 独立运行内部Block文档生成工作流 ===")

    llm = LLMInterface(model_name="gpt-4.1-mini", provider="openai")
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )

    if not await neo4j.test_connection():
        print("[ERR] Neo4j 连接失败")
        return

    print("[INFO] Neo4j 连接成功")

    app = internal_block_workflow(llm, neo4j)
    result = await app.ainvoke(
        {},
        config={"configurable": {"thread_id": "internal-block-generation"}}
    )

    print("\n=== 执行结果 ===")
    print(json.dumps(result["final_output"], ensure_ascii=False, indent=2))

    neo4j.close()
    print("[INFO] 工作流执行完成")

if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())