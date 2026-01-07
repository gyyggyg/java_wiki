import os
import sys
import json
import asyncio
import re
import uuid
from typing import Any, Dict, List
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from interfaces.llm_interface import LLMInterface          # 你自己的封装
from interfaces.neo4j_interface import Neo4jInterface
from chains.common_chains import ChainFactory            # 简易链工厂
from interfaces.data_master import get_file_content

# ====================== 1. 辅助函数 ======================
def generate_uuid_4digits() -> str:
    """生成4位唯一ID"""
    return str(uuid.uuid4().int)[:4]

def find_code_line_range(full_code: str, target_code: str, name: str) -> List[str]:
    """
    在完整代码中查找目标代码的行号范围

    Args:
        full_code: 完整文件的源代码
        target_code: 要查找的类或函数代码片段
        name: 类或函数的名称

    Returns:
        行号范围列表，如 ["25-54"]
    """
    # 将代码按行分割
    full_lines = full_code.split('\n')
    target_lines = target_code.strip().split('\n')

    # 跳过目标代码开头的注解行，找到实际的声明行
    first_non_annotation_idx = 0
    for idx, line in enumerate(target_lines):
        if not line.strip().startswith('@'):
            first_non_annotation_idx = idx
            break

    first_line = target_lines[first_non_annotation_idx].strip()

    # 在完整代码中查找起始行
    start_line = None
    for i, line in enumerate(full_lines, 1):
        if first_line in line.strip():
            # 验证后续几行是否匹配
            match = True
            for j in range(min(3, len(target_lines) - first_non_annotation_idx)):
                if i + j - 1 < len(full_lines):
                    target_idx = first_non_annotation_idx + j
                    if target_idx < len(target_lines) and target_lines[target_idx].strip():
                        if target_lines[target_idx].strip() not in full_lines[i + j - 1]:
                            match = False
                            break
            if match:
                start_line = i
                break

    if start_line is None:
        return []

    # 计算结束行（起始行 + 目标代码行数 - 1）
    end_line = start_line + len(target_lines) - first_non_annotation_idx - 1

    return [f"{start_line}-{end_line}"]

def find_class_or_method_range(full_code: str, code_snippet: str, name: str) -> List[str]:
    """
    使用正则表达式匹配类或方法的行号范围

    Args:
        full_code: 完整文件的源代码
        code_snippet: 类或方法的代码片段
        name: 类或方法的名称

    Returns:
        行号范围列表，如 ["28-54"]
    """
    lines = full_code.split('\n')

    # 尝试匹配类定义
    class_pattern = rf'(public\s+)?class\s+{re.escape(name)}\s*\{{'
    # 尝试匹配方法定义（支持泛型、数组等复杂返回类型）
    method_pattern = rf'(public|private|protected)?\s*[\w\<\>\[\]\,\s\.]+\s+{re.escape(name)}\s*\([^)]*\)\s*\{{'

    start_line = None
    is_class = False

    # 查找起始行
    for i, line in enumerate(lines, 1):
        if re.search(class_pattern, line):
            start_line = i
            is_class = True
            break
        elif re.search(method_pattern, line):
            start_line = i
            break

    # 如果没找到，使用简单的字符串匹配
    if start_line is None:
        return find_code_line_range(full_code, code_snippet, name)

    # 查找匹配的结束大括号
    brace_count = 0
    end_line = None
    in_string = False

    for i in range(start_line - 1, len(lines)):
        line = lines[i]
        for char_idx, char in enumerate(line):
            if char == '"' and (char_idx == 0 or line[char_idx-1] != '\\'):
                in_string = not in_string
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_line = i + 1
                        break
        if end_line:
            break

    if end_line is None:
        # 如果没找到结束，使用代码片段的行数估算
        snippet_lines = code_snippet.strip().split('\n')
        end_line = start_line + len(snippet_lines) - 1

    return [f"{start_line}-{end_line}"]

# ====================== 2. 状态定义 ======================
from typing_extensions import TypedDict

class TrueState(TypedDict, total=False):
    graphman: str

def in_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface):
    async def generate_in(state: TrueState) -> TrueState:
        query = """
        MATCH (n)
        WHERE n.nodeId in [67,590,3735]
        RETURN n.nodeId AS nodeId, n.name AS name, n.source_code AS source_code
        """
        records = await neo4j_interface.execute_query(query)

        # 找出完整文件代码（通常是包含完整路径的记录）
        full_file_record = None
        class_method_records = []

        for record in records:
            name = record.get('n.name') or record.get('name')
            # 判断是否为完整文件（包含路径的通常是文件）
            if '/' in name or '\\' in name or '.java' in name:
                full_file_record = record
            else:
                class_method_records.append(record)

        if not full_file_record:
            print("未找到完整文件代码")
            return {"graphman": "0"}

        full_code = full_file_record.get('n.source_code') or full_file_record.get('source_code')

        # ---- 处理类和方法，匹配行号 ----
        output_data = []

        for record in class_method_records:
            name = record.get('n.name') or record.get('name')
            source_code = record.get('n.source_code') or record.get('source_code')
            node_id = record.get('n.nodeId') or record.get('nodeId')

            # 使用正则匹配查找行号范围
            line_ranges = find_class_or_method_range(full_code, source_code, name)

            # 生成4位UUID
            source_id = generate_uuid_4digits()

            # 构建输出格式
            output_item = {
                "source_id": source_id,
                "name": name,
                "lines": line_ranges
            }
            output_data.append(output_item)

            print(f"处理: {name} -> 行号: {line_ranges}, ID: {source_id}")

        # ---- 输出为 JSON 文件 ----
        out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "yanglidata.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

        print(f"输出完成，共处理 {len(output_data)} 个项目，保存至: {out_path}")
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