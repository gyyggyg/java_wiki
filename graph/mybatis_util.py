import os
import sys
import json
import asyncio
import re
import uuid
from typing import Any, Dict, List, TypedDict, Tuple
from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from interfaces.llm_interface import LLMInterface          # 你自己的封装
from interfaces.neo4j_interface import Neo4jInterface
from chains.common_chains import ChainFactory            # 简易链工厂
from interfaces.data_master import get_file_content
from chains.prompts.mybatis_prompt import MYBATIS_METHOD_PROMPT

# ====================== 1. 辅助函数 ======================

class MbState(TypedDict, total=False):
    graphman: str

def match_method_xml(method_name: str, xml_content: str) -> str:
    """
    从xml_content中提取出method_name对应的XML片段
    包含递归查找 <include refid> 引用的 <sql> 片段
    返回：主片段 + 所有依赖的 <sql> 片段
    """
    
    # 第1步：找到主方法对应的XML（保持原有逻辑不变）
    start_pattern = rf'<([a-zA-Z_][a-zA-Z0-9_]*)[^>]*?(?:\s|^)id=["\']{re.escape(method_name)}["\'][^>]*?>'
    
    start_match = re.search(start_pattern, xml_content, re.IGNORECASE)
    if not start_match:
        return ""
    
    tag_name = start_match.group(1)
    start_pos = start_match.start()
    pos = start_match.end()
    
    # 检查自闭合
    if xml_content[pos-2:pos].strip().endswith('/'):
        main_fragment = xml_content[start_pos:pos]
    else:
        # 栈计数找结束标签（原有逻辑）
        depth = 1
        tag_pattern = re.compile(r'<(/?)([a-zA-Z_][a-zA-Z0-9_]*)\b[^>]*?(/?)>', re.IGNORECASE)
        end_pos = pos
        
        while pos < len(xml_content):
            next_match = tag_pattern.search(xml_content, pos)
            if not next_match:
                break
            
            is_closing = next_match.group(1) == '/'
            current_tag = next_match.group(2)
            is_self_closing = next_match.group(3) == '/'
            
            if current_tag.lower() == tag_name.lower():
                if is_closing:
                    depth -= 1
                    if depth == 0:
                        end_pos = next_match.end()
                        break
                elif not is_self_closing:
                    depth += 1
            
            pos = next_match.end()
        
        main_fragment = xml_content[start_pos:end_pos]
    
    # 第2步：提取主片段中所有的 <include refid="...">
    include_pattern = r'<include\s+refid\s*=\s*["\']([^"\']+)["\']'
    refids = re.findall(include_pattern, main_fragment, re.IGNORECASE)
    
    # 第3步：递归查找每个 refid 对应的 <sql> 片段
    sql_fragments = []
    collected_sql_ids = set()  # 防止循环引用
    
    def find_sql_fragment(sql_id: str, xml: str) -> str:
        """查找单个 <sql id="..."> 片段"""
        if sql_id in collected_sql_ids:
            return ""  # 已收集过，跳过
        collected_sql_ids.add(sql_id)
        
        # 匹配 <sql id="sql_id">...</sql>
        sql_pattern = rf'<sql[^>]*?(?:\s|^)id=["\']{re.escape(sql_id)}["\'][^>]*?>'
        sql_match = re.search(sql_pattern, xml, re.IGNORECASE)
        
        if not sql_match:
            return ""
        
        sql_start = sql_match.start()
        sql_pos = sql_match.end()
        
        # 检查自闭合
        if xml[sql_pos-2:sql_pos].strip().endswith('/'):
            return xml[sql_start:sql_pos]
        
        # 栈计数找 </sql>
        depth = 1
        tag_pattern = re.compile(r'<(/?)([a-zA-Z_][a-zA-Z0-9_]*)\b[^>]*?(/?)>', re.IGNORECASE)
        
        while sql_pos < len(xml):
            m = tag_pattern.search(xml, sql_pos)
            if not m:
                break
            
            is_closing = m.group(1) == '/'
            current_tag = m.group(2)
            is_self_closing = m.group(3) == '/'
            
            if current_tag.lower() == 'sql':
                if is_closing:
                    depth -= 1
                    if depth == 0:
                        sql_fragment = xml[sql_start:m.end()]
                        
                        # 递归检查这个 <sql> 内部是否还有 <include>
                        inner_refids = re.findall(include_pattern, sql_fragment, re.IGNORECASE)
                        for inner_id in inner_refids:
                            inner_sql = find_sql_fragment(inner_id, xml)
                            if inner_sql:
                                sql_fragments.append(inner_sql)
                        
                        return sql_fragment
                elif not is_self_closing:
                    depth += 1
            
            sql_pos = m.end()
        
        return xml[sql_start:]
    
    # 收集所有依赖的 <sql>
    for refid in refids:
        sql_fragment = find_sql_fragment(refid, xml_content)
        if sql_fragment:
            sql_fragments.append(sql_fragment)
    
    # 第4步：组合结果
    result_parts = [main_fragment]
    result_parts.extend(sql_fragments)
    
    return '\n\n<!-- 依赖的 SQL 片段 -->\n'.join(result_parts) if sql_fragments else main_fragment

def match_method_interface(method_name: str, interface_code: str):
    """
    从Java接口源码中根据方法名提取完整方法签名和参数中的自定义类类型列表。
    返回: (方法签名字符串, 类类型列表)
    """
    escaped_name = re.escape(method_name)

    # 匹配: 返回类型 + 方法名 + 括号内参数（支持泛型嵌套） + 分号
    # 返回类型: [\w<>\[\],\s?]+ 支持泛型如 List<String>、int、void 等
    # 参数部分: 用括号平衡匹配，支持泛型中的 < > 嵌套
    pattern = rf'([\w<>\[\],\?\s]+?)\s+{escaped_name}\s*\('
    match = re.search(pattern, interface_code)
    if not match:
        return "", []

    return_type = match.group(1).strip()
    # 清理返回类型中可能混入的多余空白
    return_type = re.sub(r'\s+', ' ', return_type)

    # 从方法名后的 ( 开始，手动平衡括号找到匹配的 )
    paren_start = match.end() - 1  # 指向 (
    depth = 0
    pos = paren_start
    while pos < len(interface_code):
        ch = interface_code[pos]
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                break
        pos += 1

    params_with_parens = interface_code[paren_start:pos + 1]
    params_str = interface_code[paren_start + 1:pos]

    # 清理参数中的多余空白和换行
    params_clean = re.sub(r'\s+', ' ', params_with_parens)
    full_signature = f"{return_type} {method_name}{params_clean};"

    # 按逗号拆分参数（跳过泛型内的逗号）
    depth = 0
    param_parts = []
    current = []
    for ch in params_str:
        if ch == '<':
            depth += 1
            current.append(ch)
        elif ch == '>':
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0:
            param_parts.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        param_parts.append(''.join(current).strip())

    # 提取每个参数的实体类型
    # Java参数格式: [注解] 类型 变量名
    # 策略：有泛型则取泛型内部类型，无泛型则取类型本身
    class_types = []
    for param in param_parts:
        if not param:
            continue
        # 去掉注解 @Xxx(...) 或 @Xxx
        clean_param = re.sub(r'@\w+\s*(\([^)]*\))?\s*', '', param).strip()
        if not clean_param:
            continue
        # clean_param 格式: "List<PmsSkuStock> skuStockList" 或 "OmsOrder record"
        # 最后一个token是变量名，前面的都是类型
        tokens = clean_param.rsplit(None, 1)
        if len(tokens) < 2:
            continue
        type_part = tokens[0]  # 如 "List<PmsSkuStock>" 或 "OmsOrder"

        # 有泛型：提取 <> 内的类型（如 List<PmsSkuStock> → PmsSkuStock）
        generic_types = re.findall(r'<([^<>]+)>', type_part)
        if generic_types:
            for gt in generic_types:
                for t in gt.split(','):
                    t = t.strip()
                    if t and t not in class_types:
                        class_types.append(t)
        else:
            # 无泛型：直接取类型名本身（如 OmsOrder）
            if type_part not in class_types:
                class_types.append(type_part)

    return full_signature, class_types

def match_characteristic_info(class_code: str) -> str:
    match = re.search(r'public|private|protected', class_code)
    first_brace = match.start() if match else -1

    # 提取大括号之后的内容
    after_brace = class_code[first_brace:]

    # 找到第一个函数的位置（public 或 private 开头，后面跟着返回类型和括号）
    # 匹配模式：访问修饰符 + 返回类型 + 方法名 + ()
    method_pattern = r'\s+(public|private|protected)\s+\w+(\s+[\w<>,\s]+)?\s+\w+\s*\('
    match = re.search(method_pattern, after_brace)

    if match:
        # 提取从开始到第一个函数之前的所有内容
        attributes_section = after_brace[:match.start()]
    else:
        attributes_section = after_brace
    return attributes_section.strip()


def mybatis_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface, method_id):
    method_chain = ChainFactory.create_generic_chain(llm_interface, MYBATIS_METHOD_PROMPT)
    async def method_flow(state: MbState) -> MbState:
        #从method_id获取interface和xml内容
        query_1 = """
        MATCH (m:Method)<-[:DECLARES*]-(i:Interface)<-[:DECLARES]-(f:File)
        WHERE m.nodeId = $method_id
        OPTIONAL MATCH (i)<-[:IMPLEMENTS]-(x:XML)
        RETURN m.name AS method_name, i.source_code AS interface_code, i.name AS interface_name, f.name AS file_name,
        m.SE_What AS method_what, i.SE_What AS interface_what, f.SE_What AS file_what, x.source_code AS xml_content
        """
        #查询承载的属性信息
        query_2 = """
        MATCH (c:Class {name: $class_name})
        RETURN c.source_code AS class_code
        """
        result_1 = await neo4j_interface.execute_query(query_1, {"method_id": method_id})
        record = result_1[0]
        method_name = record["method_name"]
        interface_code = record["interface_code"]
        xml_content = record["xml_content"]
        interface_what = record["interface_what"]
        file_what = record["file_what"]
        method_what = record["method_what"]
        file_name = record["file_name"]
        interface_name = record["interface_name"]
        method_xml = match_method_xml(method_name, xml_content)
        print(f"提取到的method_xml:\n{method_xml}\n")
        method_signature, generic_type = match_method_interface(method_name, interface_code)
        print(f"提取到的方法签名:\n{method_signature}\n")
        all_characteristic_info = ""
        for class_type in generic_type:
            result_2 = await neo4j_interface.execute_query(query_2, {"class_name": class_type})
            class_code = result_2[0]["class_code"] if result_2 else ""
            characteristic_info = match_characteristic_info(class_code)
            all_characteristic_info += characteristic_info + "\n"
        print(f"提取到的所有属性信息:\n{all_characteristic_info}\n")
        resultt = await method_chain.ainvoke({
            "xml_content": method_xml,
            "interface_code": method_signature,
            "characteristic_info": all_characteristic_info
        })
        table_lines = ["\n下面介绍该方法所属的文件、接口、方法的基本信息\n"]
        table_lines.append("| 文件 | 接口 | 方法 |")
        table_lines.append("| --- | --- | --- |")
        table_lines.append(f"| {file_name} | {interface_name} | {method_name} |")
        table_lines.append(f"| {file_what} | {interface_what} | {method_what} |")
        add_table = "\n".join(table_lines)
        md_content = json.loads(resultt)["markdown"] + "\n" + add_table
        mermaid_path = os.path.join(os.path.dirname(__file__), "xml_method.md")
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return {"graphman": "1"}
    async def file_target(state: MbState) -> MbState:
        return

    graph = StateGraph(MbState)
    graph.add_node("method_flow", method_flow)
    graph.add_node("file_target", file_target)
    graph.set_entry_point("method_flow")
    graph.add_edge("method_flow", "file_target")
    graph.add_edge("file_target", END)

    app = graph.compile(checkpointer=MemorySaver())
    return app

# ====================== 4. 独立运行入口 ======================
async def main():
    load_dotenv()
    print("=== 独立运行对外提供接口说明文档生成应用 ===")

    llm = LLMInterface()  # 模型/提供商从 .env 的 LLM_MODEL / LLM_PROVIDER 读取
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    if not await neo4j.test_connection():
        print("[ERR] Neo4j 连接失败")
        return
    method_id = 17149  # 替换为实际的方法节点ID
    app = mybatis_app(llm, neo4j, method_id)
    await app.ainvoke(
        {}, 
        config={"configurable": {"thread_id": "standalone-api"}}
    )
    neo4j.close()

if __name__ == "__main__":
    asyncio.run(main())