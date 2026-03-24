import os
import sys
import json
import asyncio
import re
import uuid
import time
from typing import Any, Dict, List, TypedDict
from dotenv import load_dotenv
from collections import defaultdict
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from interfaces.llm_interface import LLMInterface
from interfaces.neo4j_interface import Neo4jInterface
from chains.common_chains import ChainFactory   
from graph.id_generate import find_class_or_method_range
from interfaces.simple_validate_mermaid import SimpleMermaidValidator

# 便捷引用：清理classDiagram中类定义内部的空行
_sanitize_class_diagram = SimpleMermaidValidator.sanitize_class_diagram
from chains.prompts.type_chart_prompt import SOURCE_ID_PROMPT, CFG_PROMPT, UML_PROMPT, HYBRID_UML_PROMPT, HYBRID_UML_DESC_PROMPT, TIME_PROMPT, BLOCK_PROMPT, CFG_ID_PROMPT, MERMIAD_DESC_PROMPT


def generate_uuid_4digits() -> str:
    """生成4位唯一ID"""
    return str(uuid.uuid4().int)[:4]


def _strip_json_comments(text: str) -> str:
    """去除JSON文本中的行内 // 注释（不影响字符串内的 //）。"""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        in_string = False
        escape = False
        i = 0
        while i < len(line):
            ch = line[i]
            if escape:
                escape = False
                i += 1
                continue
            if ch == '\\' and in_string:
                escape = True
                i += 1
                continue
            if ch == '"':
                in_string = not in_string
                i += 1
                continue
            if not in_string and ch == '/' and i + 1 < len(line) and line[i + 1] == '/':
                line = line[:i].rstrip()
                break
            i += 1
        cleaned.append(line)
    return '\n'.join(cleaned)


def extract_json(text: str) -> dict:
    """从LLM输出中提取JSON对象，处理markdown代码块、多余文字和行内//注释。"""
    import re

    def _try_parse(s: str) -> dict | None:
        """尝试解析JSON，失败则去除//注释后重试。"""
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        try:
            return json.loads(_strip_json_comments(s))
        except json.JSONDecodeError:
            return None

    # 1. 直接解析
    result = _try_parse(text)
    if result is not None:
        return result

    # 2. 提取 ```json ... ``` 或 ``` ... ``` 中的内容
    patterns = [
        r'```json\s*\n?(.*?)\n?\s*```',
        r'```\s*\n?(.*?)\n?\s*```',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            result = _try_parse(match.group(1))
            if result is not None:
                return result

    # 3. 提取第一个 { 到最后一个 } 之间的内容
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass
    print(f"[WARN] 无法解析JSON，原始文本为:\n{text[:200]}...")
    return False


MAX_JSON_RETRIES = 10
MAX_MERMAID_RETRIES = 5

def sanitize_mermaid(mermaid_text: str) -> str:
    """清理mermaid文本中不支持的字符（如Java的$内部类分隔符）"""
    # 只替换类名中的$，不动箭头等语法符号
    mermaid_text = mermaid_text.replace("$", "_")
    return mermaid_text

async def invoke_and_parse(chain, invoke_args, max_retries=MAX_JSON_RETRIES):
    """调用LLM chain并解析JSON，解析失败时自动重试。"""
    for attempt in range(max_retries):
        result = await chain.ainvoke(invoke_args)
        parsed = extract_json(result)
        if parsed is not False:
            return parsed
        print(f"[WARN] JSON解析失败，正在重试 ({attempt + 1}/{max_retries})...")
    raise ValueError(f"经过{max_retries}次重试后仍无法从LLM输出中解析JSON")


def extract_class_summary(source_code: str) -> str:
    """从Java源码提取结构化摘要：类声明、字段列表、方法签名列表。

    输出格式紧凑，直接使用Java原始修饰符（public/private/static等）。
    示例输出：
        public class OrderService extends BaseService implements IOrderService
        fields: private OrderDao orderDao, private static Logger logger
        methods: public createOrder(CreateOrderRequest):Order, public static getInstance():OrderService
    """
    if not source_code:
        return source_code

    lines = source_code.split('\n')
    class_decl = ""
    is_enum = False
    enum_constants = []
    fields = []
    methods = []
    brace_depth = 0
    in_method = False
    method_brace_start = 0
    enum_section = True  # 枚举常量在字段/方法之前

    # 需要识别的修饰符
    all_mods = {'public', 'private', 'protected', 'static', 'final', 'abstract',
                'synchronized', 'default', 'native', 'volatile', 'transient'}
    # 需要保留在输出中的修饰符（对UML有意义的）
    keep_mods = {'public', 'private', 'protected', 'static', 'abstract'}

    for line in lines:
        stripped = line.strip()
        open_count = line.count('{')
        close_count = line.count('}')

        if in_method:
            brace_depth += open_count - close_count
            if brace_depth <= method_brace_start:
                in_method = False
            continue

        # 跳过注释、空行、import、package、注解
        if (not stripped or stripped.startswith('//') or stripped.startswith('*')
                or stripped.startswith('/*') or stripped.startswith('import ')
                or stripped.startswith('package ') or stripped.startswith('@')):
            brace_depth += open_count - close_count
            continue

        if brace_depth == 0:
            # 类/接口/枚举声明行
            for kw in ('class ', 'interface ', 'enum ', 'record '):
                if kw in stripped:
                    class_decl = stripped.rstrip('{').rstrip()
                    if kw == 'enum ':
                        is_enum = True
                    break
            brace_depth += open_count - close_count
            continue

        if brace_depth == 1:
            # 枚举常量处理
            if is_enum and enum_section:
                has_semicolon = ';' in stripped
                for const in stripped.rstrip(';').split(','):
                    const = const.strip()
                    if const:
                        const_name = const.split('(')[0].strip()
                        if const_name and const_name[0].isupper():
                            enum_constants.append(const_name)
                if has_semicolon:
                    enum_section = False
                brace_depth += open_count - close_count
                continue

            if '(' in stripped and not stripped.startswith('//'):
                # 方法签名
                sig_part = stripped.split('{')[0].rstrip().rstrip(';').rstrip()
                tokens = sig_part.split()

                # 收集修饰符前缀
                mod_prefix_parts = []
                for t in tokens:
                    if t in keep_mods:
                        mod_prefix_parts.append(t)
                    elif t not in all_mods:
                        break  # 遇到非修饰符token，停止
                mod_prefix = ' '.join(mod_prefix_parts)

                method_str = ""
                for i, tok in enumerate(tokens):
                    if '(' in tok:
                        ret_type = tokens[i-1] if i > 0 and tokens[i-1] not in all_mods else ""
                        method_part = ' '.join(tokens[i:])
                        if '(' in method_part and ')' in method_part:
                            name_part = method_part[:method_part.index('(')]
                            params_str = method_part[method_part.index('(')+1:method_part.rindex(')')]
                            param_types = []
                            for p in params_str.split(','):
                                p = p.strip()
                                if p:
                                    pt = p.split()
                                    if pt:
                                        param_types.append(pt[0])
                            params = ','.join(param_types)
                            if ret_type:
                                method_str = f"{mod_prefix} {name_part}({params}):{ret_type}" if mod_prefix else f"{name_part}({params}):{ret_type}"
                            else:
                                method_str = f"{mod_prefix} {name_part}({params})" if mod_prefix else f"{name_part}({params})"
                        break
                if method_str:
                    methods.append(method_str)

                # 跟踪方法体
                if open_count > close_count:
                    method_brace_start = brace_depth
                    brace_depth += open_count - close_count
                    in_method = True
                else:
                    brace_depth += open_count - close_count
            else:
                # 字段声明
                field_line = stripped.rstrip(';').rstrip()
                if field_line and not field_line.startswith('}'):
                    tokens = field_line.split()
                    # 收集修饰符
                    mod_parts = []
                    for t in tokens:
                        if t in keep_mods:
                            mod_parts.append(t)
                        elif t not in all_mods:
                            break
                    mod_str = ' '.join(mod_parts)
                    # 过滤掉所有修饰符，保留类型和名称
                    content_tokens = [t for t in tokens if t not in all_mods]
                    if len(content_tokens) >= 2:
                        field_name = content_tokens[1].split('=')[0]
                        field_entry = f"{mod_str} {content_tokens[0]} {field_name}" if mod_str else f"{content_tokens[0]} {field_name}"
                        fields.append(field_entry)
                    elif content_tokens:
                        field_entry = f"{mod_str} {' '.join(content_tokens)}" if mod_str else ' '.join(content_tokens)
                        fields.append(field_entry)
                brace_depth += open_count - close_count
        else:
            brace_depth += open_count - close_count

    # 组装输出
    parts = []
    if class_decl:
        parts.append(class_decl)
    if enum_constants:
        parts.append(f"enum_constants: {', '.join(enum_constants)}")
    if fields:
        parts.append(f"fields: {', '.join(fields)}")
    if methods:
        parts.append(f"methods: {', '.join(methods)}")
    return '\n'.join(parts) if parts else source_code


class ChartState(TypedDict, total=False):
    chart_type: str
    mermaid_content: str
    mermaid_source_info: str
    write_path: str
    additional_info: str
    output: str
    mapping : Dict
    id_list : List

def chart_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface, node_list: List , type: str, skeleton: bool = False, class_source_map: Dict = None) -> StateGraph:
    cfg_id_chain = ChainFactory.create_generic_chain(llm_interface, SOURCE_ID_PROMPT)
    cfg_chain = ChainFactory.create_generic_chain(llm_interface, CFG_PROMPT)
    cfg_id_validate_chain = ChainFactory.create_generic_chain(llm_interface, CFG_ID_PROMPT)
    uml_chain = ChainFactory.create_generic_chain(llm_interface, UML_PROMPT)
    hybrid_uml_chain = ChainFactory.create_generic_chain(llm_interface, HYBRID_UML_PROMPT)
    hybrid_uml_desc_chain = ChainFactory.create_generic_chain(llm_interface, HYBRID_UML_DESC_PROMPT)
    time_chain = ChainFactory.create_generic_chain(llm_interface, TIME_PROMPT)
    block_chain = ChainFactory.create_generic_chain(llm_interface, BLOCK_PROMPT)
    description_chain = ChainFactory.create_generic_chain(llm_interface, MERMIAD_DESC_PROMPT)
    validator = SimpleMermaidValidator()

    async def generate_cfg(state: ChartState) -> ChartState:
        node_id = node_list[0]
         # ---- Cypher 查询 ----
        query0 = """
        MATCH (f1:File)-[:DECLARES]->(n0)-[:DECLARES*]->(n)
        WHERE n.nodeId = $node_id 
        RETURN n.semantic_explanation as n_sema, n0.name AS n0_name, n.name as n_name, n0.semantic_explanation AS n0_sema, f1.name AS file_name, f1.semantic_explanation AS file_sema
        """
        query1 = """
        MATCH (n)<-[:DECLARES*]-(n0:File)
        WHERE n.nodeId = $node_id
        RETURN n.name AS name,
            n0.name AS file_name,
            n.source_code AS source_code,
            n.SE_How AS SE_How,
            n0.source_code AS file_code
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
        result0, result1, result2, result3, result4 = await asyncio.gather(
            neo4j_interface.execute_query(query0, {"node_id": node_id}),
            neo4j_interface.execute_query(query1, {"node_id": node_id}),
            neo4j_interface.execute_query(query2, {"node_id": node_id}),
            neo4j_interface.execute_query(query3, {"node_id": node_id}),
            neo4j_interface.execute_query(query4, {"node_id": node_id}),
        )
        node_information = []

        if result0:
            method_name = f"{result0[0]['n0_name']}.{result0[0]['n_name']}"
            method_use = json.loads(result0[0]['n_sema'])["What"]
            class_name = result0[0]['n0_name']
            class_use = json.loads(result0[0]['n0_sema'])["What"]
            file_use = json.loads(result0[0]['file_sema'])["What"]
            file_name = result0[0]['file_name']
            # print("key_target:",key_target)
                # 生成 markdown 表格
        table_lines = ["\n下面介绍该函数所属的文件、类、函数的基本信息\n"]
        table_lines.append("| 文件 | 类 | 函数 |")
        table_lines.append("| --- | --- | --- |")
        table_lines.append(f"| {file_name} | {class_name} | {method_name} |")
        table_lines.append(f"| {file_use} | {class_use} | {method_use} |")

        add_table = "\n".join(table_lines)
        if result1:
            code = result1[0]
            file_name = code['file_name']
            source_code = code['source_code']
            semantic_explanation = code['SE_How']
            node_information.append(
                f"函数 {code['name']} 语义解释为 {code['SE_How']}\n下面是与其相关的类的介绍"
            )
            base_lines = find_class_or_method_range(code['file_code'], code['source_code'], code['name'])
        else:
            raise ValueError(f"未找到nodeId={node_id}对应的方法源码，无法生成CFG")
        print("base_lines:", base_lines)
        if base_lines:
            base_start = int(base_lines[0].split('-')[0])
        else:
            base_start = 1
            print(f"[WARN] 无法定位方法 {code['name']} 在文件中的行号，默认从第1行开始")
        offset = base_start - 1
        code_lines = [line for line in source_code.split('\n') if not line.strip().startswith('@')]
        tag_code = {str(i+1): line for i, line in enumerate(code_lines)}

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
        source_id_parsed = await invoke_and_parse(cfg_id_chain, {"source_code": tag_code, "explanation": semantic_explanation})
        print("source_id:", source_id_parsed)
        reason = source_id_parsed["reason"]
        id_list = [] #[{'source_id': '2662', 'lines': ['1-2']}]
        id_list_map = {} #{'2662': ['1-2']}
        cfg_lines_map = {} #{'A1': ['1-2']}

        for item in source_id_parsed["lines"]:
            uu_id = generate_uuid_4digits()
            id_list.append({"source_id": uu_id, "lines": item})
            id_list_map[uu_id] = item

        cfg_parsed = await invoke_and_parse(cfg_chain, {"source_code": tag_code, "explanation": all_in, "source_id": id_list, "code_block": reason})
        cfg_parsed['mermaid'] = sanitize_mermaid(cfg_parsed['mermaid'])
        validate_result = validator.validate_file(f"```mermaid\n\n{cfg_parsed['mermaid']}\n\n```")
        for _retry in range(MAX_MERMAID_RETRIES):
            if validate_result["result"]:
                break
            print(validate_result)
            cfg_parsed = await invoke_and_parse(cfg_chain, {"source_code": tag_code, "explanation": all_in + f"之前存在错误的情况，需要规避{validate_result['errors']}", "source_id": id_list, "code_block": reason})
            cfg_parsed['mermaid'] = sanitize_mermaid(cfg_parsed['mermaid'])
            validate_result = validator.validate_file(f"```mermaid\n\n{cfg_parsed['mermaid']}\n\n```")

        cfg_map = cfg_parsed["mapping"] # {'A1': '2662'}
        for key,value in cfg_map.items():
            lines = id_list_map[value]
            cfg_lines_map[key] = lines
        print("old_id_result:", cfg_lines_map)
        new_id_parsed = await invoke_and_parse(cfg_id_validate_chain, {"source_code": tag_code, "mermaid": cfg_parsed["mermaid"], "reason": reason, "mapping": cfg_lines_map})
        print("new_id_result:", new_id_parsed["mapping"], new_id_parsed["reason"])
        new_map = new_id_parsed["mapping"] # {'A1': ['8-10'], 'B1': ['11-20','80']}
        new_id_list = []
        
        for key,value in new_map.items():
            uu_id = cfg_map[key]
            lines = []
            for item in value:
                if '-' in item:
                    start, end = item.split('-')
                    lines.append(f"{int(start) + offset}-{int(end) + offset}")
                else:
                    lines.append(str(int(item) + offset))
            new_id_list.append({"source_id": uu_id, "name": file_name, "lines": lines})
        # resultt = json.dumps({"mermaid": json.loads(cfg_result)["mermaid"], "mapping": json.loads(cfg_result)["mapping"], "id_list": new_id_list}, ensure_ascii=False, indent=4)
        # out_path = os.path.join(os.path.dirname(__file__), "cfg.json")
        # # with open(out_path, "w", encoding="utf-8") as f:
        # #     f.write(resultt)
        mermaid_path = os.path.join(os.path.dirname(__file__), "cfg_mermaid.md")
        mermaid_source_info = f"source_code: {source_code},\n code_explanation: {all_in}"
        return {"chart_type":"代码控制流图", "mermaid_content": cfg_parsed["mermaid"], "mermaid_source_info":  mermaid_source_info, "write_path": mermaid_path, 'additional_info': add_table, "mapping": cfg_parsed["mapping"], "id_list": new_id_list}

    async def generate_uml(state: ChartState) -> ChartState:
        simplify = extract_class_summary if skeleton else lambda x: x
        if node_list[0] == "Class&Interface":
            key_target = node_list[1:]
        else:
            query = """
            MATCH (n)<-[:DECLARES*]-(n1)<-[:DECLARES]-(n0:File)
            WHERE n.nodeId = $node_id
            RETURN n.name AS name, n1.name AS n1_name
            """
            key_target = []
            for i in node_list:
                result = await neo4j_interface.execute_query(query, {"node_id": i})
                if result:
                    record = result[0]
                    name = record['n1_name']
                    key_target.append(name)
        print("key_target:",key_target)
        query0 = """
        MATCH (n)<-[:DECLARES]-(n0:File)
        WHERE n.name = $name
        RETURN n.source_code AS n_code, n0.source_code AS file_code, n0.name AS file_name
        """
        query1 = """
        MATCH (n)-[:IMPLEMENTS]->(n0)<-[:DECLARES]-(n1:File)
        WHERE n.name = $name
        RETURN n0.name AS n0_name, n0.source_code AS n0_code, n1.source_code AS file_code, n1.name AS file_name
        """
        query2 = """
        MATCH (n)-[:EXTENDS]->(n0)<-[:DECLARES]-(n1:File)
        WHERE n.name = $name
        RETURN n0.name AS n0_name, n0.source_code AS n0_code, n1.source_code AS file_code, n1.name AS file_name
        """
        query3 = """
        MATCH (n)-[:DECLARES*1..]->(m1:Method)-[:CALLS]->(m2:Method)<-[:DECLARES*1..]-(n0)<-[:DECLARES]-(n1:File)
        WHERE n.name = $name AND n<>n0 AND n0.name in $key_target
        RETURN m1.name AS m1_name, m2.name AS m2_name, n0.name AS n0_name, n0.source_code AS n0_code, n1.source_code AS file_code, n1.name AS file_name
        """
        query4 = """
        MATCH (n)-[:DECLARES*1..]->(m1:Method)-[:USES]->(n0:Class)<-[:DECLARES]-(n1:File)
        WHERE n.name = $name AND n<>n0 AND n0.name in $key_target
        RETURN m1.name AS m1_name, n0.name AS n0_name, n0.source_code AS n0_code, n0.file_id AS file_id, n1.source_code AS file_code, n1.name AS file_name
        """
        query5 = """
        MATCH (n)-[:DECLARES*1..]->(m1:Method)-[:RETURNS]->(n0:Class)<-[:DECLARES]-(n1:File)
        WHERE n.name = $name AND n<>n0 and n0.name in $key_target
        RETURN m1.name AS m1_name, n0.name AS n0_name, n0.source_code AS n0_code, n0.file_id AS file_id, n1.source_code AS file_code, n1.name AS file_name
        """
        source_id_ai = []
        source_id_full = []
        source_id_range = {}
        node_information = []
        for name in key_target:
            result, result1, result2, result3, result4, result5 = await asyncio.gather(
                neo4j_interface.execute_query(query0, {"name": name}),
                neo4j_interface.execute_query(query1, {"name": name}),
                neo4j_interface.execute_query(query2, {"name": name}),
                neo4j_interface.execute_query(query3, {"name": name, "key_target": key_target}),
                neo4j_interface.execute_query(query4, {"name": name, "key_target": key_target}),
                neo4j_interface.execute_query(query5, {"name": name, "key_target": key_target}),
            )
            code = result[0]
            unique_key = name
            if unique_key not in source_id_range:
                lines = find_class_or_method_range(result[0]['file_code'], result[0]['n_code'], name)
                source_id_range[unique_key] = {
                    "file_name": result[0]['file_name'],
                    "name": name,
                    "lines": lines
                    }
            node_information.append(f"\n下面是与类 {name} 相关的类的介绍，类 {name} 的信息为 {simplify(code['n_code'])}")
            if result1:
                print(f"{name} 实现了", len(result1))
                for record in result1:
                    node_information.append(f"\n类 {name} 实现了 {record['n0_name']}，{record['n0_name']} 的信息为 {simplify(record['n0_code'])}")
                    unique_key = record['n0_name']
                    if unique_key not in source_id_range:
                        lines = find_class_or_method_range(record['file_code'], record['n0_code'], record['n0_name'])
                        source_id_range[unique_key] = {
                            "file_name": record['file_name'],
                            "name": record['n0_name'],
                            "lines": lines
                        }
            if result2:
                print(f"{name} 继承了", len(result2))
                for record in result2:
                    node_information.append(f"\n类 {name} 继承了 {record['n0_name']}，{record['n0_name']} 的信息为 {simplify(record['n0_code'])}")
                    unique_key = record['n0_name']
                    if unique_key not in source_id_range:
                        lines = find_class_or_method_range(record['file_code'], record['n0_code'], record['n0_name'])
                        source_id_range[unique_key] = {
                            "file_name": record['file_name'],
                            "name": record['n0_name'],
                            "lines": lines
                        }
            if result3:
                code_dict = {}
                rel_dict = {}
                for record in result3:
                    if record['n0_name'] not in code_dict:
                        code_dict[record['n0_name']] = record['n0_code']
                        unique_key = record['n0_name']
                        if unique_key not in source_id_range:
                            lines = find_class_or_method_range(record['file_code'], record['n0_code'], record['n0_name'])
                            source_id_range[unique_key] = {
                                "file_name": record['file_name'],
                                "name": record['n0_name'],
                                "lines": lines
                            }
                        rel_dict[record['n0_name']] = [record['m2_name']]
                        # file_id.append(record['file_id'])
                    else:
                        rel_dict[record['n0_name']].append(record['m2_name'])
                print(f"{name} 调用了", len(code_dict))
                for key, value in rel_dict.items():
                    node_information.append(f"\n类 {name} 调用了 {key} 的函数 {value}")
                    node_information.append(f"\n类 {key} 信息为 {simplify(code_dict[key])}")
            if result4:
                code_dict = {}
                rel_dict = {}
                for record in result4:
                    if record['n0_name'] not in code_dict:
                        code_dict[record['n0_name']] = record['n0_code']
                        rel_dict[record['n0_name']] = [record['m1_name']]
                        unique_key = record['n0_name']
                        if unique_key not in source_id_range:
                            lines = find_class_or_method_range(record['file_code'], record['n0_code'], record['n0_name'])
                            source_id_range[unique_key] = {
                                "file_name": record['file_name'],
                                "name": record['n0_name'],
                                "lines": lines
                            }
                        # file_id.append(record['file_id'])
                    else:
                        rel_dict[record['n0_name']].append(record['m1_name'])
                print(f"{name} 使用了", len(code_dict))
                for key, value in rel_dict.items():
                    node_information.append(f"\n类 {name} 使用了类型 {key} 的函数为 {value}")
            if result5:
                code_dict = {}
                rel_dict = {}
                for record in result5:
                    if record['n0_name'] not in code_dict:
                        code_dict[record['n0_name']] = record['n0_code']
                        rel_dict[record['n0_name']] = [record['m1_name']]
                        unique_key = record['n0_name']
                        if unique_key not in source_id_range:
                            lines = find_class_or_method_range(record['file_code'], record['n0_code'], record['n0_name'])
                            source_id_range[unique_key] = {
                                "file_name": record['file_name'],
                                "name": record['n0_name'],
                                "lines": lines
                            }
                        # file_id.append(record['file_id'])
                    else:
                        rel_dict[record['n0_name']].append(record['m1_name'])
                print(f"{name} 返回了", len(code_dict))
                for key, value in rel_dict.items():
                    node_information.append(f"\n类 {name} 返回类型为 {key} 的函数为 {value}")
        node_information = "\n".join(node_information)
        for item in source_id_range.values():
            uu_id = generate_uuid_4digits()
            key = {"source_id": uu_id, "name": item['file_name'], "lines": item['lines']}
            source_id_full.append(key)
            source_id_ai.append({"source_id": uu_id, "name": item['name']})
        # # 调试：将UML输入写入文件
        # uml_debug_path = os.path.join(os.path.dirname(__file__), "uml_input_debug.txt")
        # with open(uml_debug_path, "w", encoding="utf-8") as f:
        #     f.write("=== node_information ===\n")
        #     f.write(node_information)
        #     f.write("\n\n=== source_id ===\n")
        #     f.write(json.dumps(source_id_ai, ensure_ascii=False, indent=2))
        # print(f"[DEBUG] UML输入已写入 {uml_debug_path}")
        uml_parsed = await invoke_and_parse(uml_chain, {"node_information": node_information, "source_id": source_id_ai})
        uml_parsed['mermaid'] = sanitize_mermaid(uml_parsed['mermaid'])
        validate_result = validator.validate_file(f"```mermaid\n\n{uml_parsed['mermaid']}\n\n```")
        for _retry in range(MAX_MERMAID_RETRIES):
            if validate_result["result"]:
                break
            print(validate_result)
            uml_result = await uml_chain.ainvoke({"node_information": node_information + f"之前存在错误的情况，需要规避{validate_result['errors']}", "source_id": source_id_ai}, config=cb_config)
            uml_parsed = extract_json(uml_result)
            uml_parsed["mermaid"] = _sanitize_class_diagram(uml_parsed["mermaid"])
            validate_result = validator.validate_file(f"```mermaid\n\n{uml_parsed['mermaid']}\n\n```")

        mermaid_path = os.path.join(os.path.dirname(__file__), "uml_mermaid.md")
        return {"chart_type":"代码类\\接口之间关系uml图", "mermaid_content": uml_parsed["mermaid"], "mermaid_source_info":  f"重点关注对象为{key_target}, 和他们相关的信息是{node_information}", "write_path": mermaid_path, "mapping": uml_parsed["mapping"], "id_list": source_id_full, "uml_token_stats": uml_token_counter.summary()}

    async def generate_hybrid_uml(state: ChartState) -> ChartState:
        """混合型Block的UML图：用namespace分组标注直连类和子模块类的归属。
        始终使用extract_class_summary，因为JSON格式要求结构化字段（declaration/fields/methods）。
        """
        simplify = extract_class_summary

        # class_source_map: {"OrderController": "本模块", "OrderService": "订单服务", ...}
        source_map = class_source_map or {}

        if node_list[0] == "Class&Interface":
            key_target = node_list[1:]
        else:
            key_target = []
            for nid in node_list:
                query_class = """
                MATCH (n)<-[:DECLARES*1..]-(n1:Class|Interface)
                WHERE n.nodeId = $node_id
                RETURN n1.name AS n1_name
                """
                result = await neo4j_interface.execute_query(query_class, {"node_id": nid})
                if result:
                    record = result[0]
                    name = record['n1_name']
                    key_target.append(name)
        print("key_target (hybrid_uml):", key_target)

        query0 = """
        MATCH (n)<-[:DECLARES]-(n0:File)
        WHERE n.name = $name
        RETURN n.source_code AS n_code, n0.source_code AS file_code, n0.name AS file_name
        """
        query1 = """
        MATCH (n)-[:IMPLEMENTS]->(n0)<-[:DECLARES]-(n1:File)
        WHERE n.name = $name
        RETURN n0.name AS n0_name, n0.source_code AS n0_code, n1.source_code AS file_code, n1.name AS file_name
        """
        query2 = """
        MATCH (n)-[:EXTENDS]->(n0)<-[:DECLARES]-(n1:File)
        WHERE n.name = $name
        RETURN n0.name AS n0_name, n0.source_code AS n0_code, n1.source_code AS file_code, n1.name AS file_name
        """
        query3 = """
        MATCH (n)-[:DECLARES*1..]->(m1:Method)-[:CALLS]->(m2:Method)<-[:DECLARES*1..]-(n0)<-[:DECLARES]-(n1:File)
        WHERE n.name = $name AND n<>n0 AND n0.name in $key_target
        RETURN m1.name AS m1_name, m2.name AS m2_name, n0.name AS n0_name, n0.source_code AS n0_code, n1.source_code AS file_code, n1.name AS file_name
        """
        query4 = """
        MATCH (n)-[:DECLARES*1..]->(m1:Method)-[:USES]->(n0:Class)<-[:DECLARES]-(n1:File)
        WHERE n.name = $name AND n<>n0 AND n0.name in $key_target
        RETURN m1.name AS m1_name, n0.name AS n0_name, n0.source_code AS n0_code, n0.file_id AS file_id, n1.source_code AS file_code, n1.name AS file_name
        """
        query5 = """
        MATCH (n)-[:DECLARES*1..]->(m1:Method)-[:RETURNS]->(n0:Class)<-[:DECLARES]-(n1:File)
        WHERE n.name = $name AND n<>n0 and n0.name in $key_target
        RETURN m1.name AS m1_name, n0.name AS n0_name, n0.source_code AS n0_code, n0.file_id AS file_id, n1.source_code AS file_code, n1.name AS file_name
        """
        source_id_ai = []
        source_id_full = []
        source_id_range = {}
        # 收集每个类的结构化信息：{类名: {declaration, fields, methods, relations, namespace}}
        class_info = {}

        def ensure_class(cname, code_text=None, ns=None):
            """确保类信息存在，如果code_text提供则解析并填充"""
            if cname not in class_info:
                class_info[cname] = {"declaration": "", "fields": "", "methods": "", "relations": [], "namespace": ns or source_map.get(cname, "未知模块")}
            if code_text and not class_info[cname]["declaration"]:
                summary = simplify(code_text)
                lines_s = summary.split('\n')
                for l in lines_s:
                    if l.startswith("fields:"):
                        class_info[cname]["fields"] = l
                    elif l.startswith("methods:"):
                        class_info[cname]["methods"] = l
                    elif l.startswith("enum_constants:"):
                        class_info[cname]["fields"] = l + ("\n" + class_info[cname]["fields"] if class_info[cname]["fields"] else "")
                    else:
                        if not class_info[cname]["declaration"]:
                            class_info[cname]["declaration"] = l

        for name in key_target:
            result, result1, result2, result3, result4, result5 = await asyncio.gather(
                neo4j_interface.execute_query(query0, {"name": name}),
                neo4j_interface.execute_query(query1, {"name": name}),
                neo4j_interface.execute_query(query2, {"name": name}),
                neo4j_interface.execute_query(query3, {"name": name, "key_target": key_target}),
                neo4j_interface.execute_query(query4, {"name": name, "key_target": key_target}),
                neo4j_interface.execute_query(query5, {"name": name, "key_target": key_target}),
            )
            code = result[0]
            if name not in source_id_range:
                lines = find_class_or_method_range(result[0]['file_code'], result[0]['n_code'], name)
                source_id_range[name] = {
                    "file_name": result[0]['file_name'],
                    "name": name,
                    "lines": lines
                }
            ensure_class(name, code['n_code'])

            if result1:
                for record in result1:
                    ensure_class(record['n0_name'], record['n0_code'])
                    class_info[name]["relations"].append(f"实现 -> {record['n0_name']}")
                    if record['n0_name'] not in source_id_range:
                        lines = find_class_or_method_range(record['file_code'], record['n0_code'], record['n0_name'])
                        source_id_range[record['n0_name']] = {"file_name": record['file_name'], "name": record['n0_name'], "lines": lines}
            if result2:
                for record in result2:
                    ensure_class(record['n0_name'], record['n0_code'])
                    class_info[name]["relations"].append(f"继承 -> {record['n0_name']}")
                    if record['n0_name'] not in source_id_range:
                        lines = find_class_or_method_range(record['file_code'], record['n0_code'], record['n0_name'])
                        source_id_range[record['n0_name']] = {"file_name": record['file_name'], "name": record['n0_name'], "lines": lines}
            if result3:
                rel_dict = {}
                for record in result3:
                    ensure_class(record['n0_name'], record['n0_code'])
                    if record['n0_name'] not in source_id_range:
                        lines = find_class_or_method_range(record['file_code'], record['n0_code'], record['n0_name'])
                        source_id_range[record['n0_name']] = {"file_name": record['file_name'], "name": record['n0_name'], "lines": lines}
                    if record['n0_name'] not in rel_dict:
                        rel_dict[record['n0_name']] = []
                    rel_dict[record['n0_name']].append(record['m2_name'])
                for key, value in rel_dict.items():
                    class_info[name]["relations"].append(f"调用 -> {key}.{value}")
            if result4:
                rel_dict = {}
                for record in result4:
                    ensure_class(record['n0_name'], record['n0_code'])
                    if record['n0_name'] not in source_id_range:
                        lines = find_class_or_method_range(record['file_code'], record['n0_code'], record['n0_name'])
                        source_id_range[record['n0_name']] = {"file_name": record['file_name'], "name": record['n0_name'], "lines": lines}
                    if record['n0_name'] not in rel_dict:
                        rel_dict[record['n0_name']] = []
                    rel_dict[record['n0_name']].append(record['m1_name'])
                for key, value in rel_dict.items():
                    class_info[name]["relations"].append(f"使用 -> {key}")
            if result5:
                rel_dict = {}
                for record in result5:
                    ensure_class(record['n0_name'], record['n0_code'])
                    if record['n0_name'] not in source_id_range:
                        lines = find_class_or_method_range(record['file_code'], record['n0_code'], record['n0_name'])
                        source_id_range[record['n0_name']] = {"file_name": record['file_name'], "name": record['n0_name'], "lines": lines}
                    if record['n0_name'] not in rel_dict:
                        rel_dict[record['n0_name']] = []
                    rel_dict[record['n0_name']].append(record['m1_name'])
                for key, value in rel_dict.items():
                    class_info[name]["relations"].append(f"返回 -> {key}")

        # ---- 过滤：只保留与直连类有关系的子模块 ----
        direct_classes = {cname for cname, info in class_info.items() if info["namespace"] == "__direct__"}

        # 找出与直连类有关系的子模块类（双向检查）
        related_child_classes = set()
        for cname, info in class_info.items():
            for rel in info.get("relations", []):
                target = rel.split(" -> ")[-1].split(".")[0].strip()
                if cname in direct_classes and target in class_info and target not in direct_classes:
                    # 直连类指向子模块类
                    related_child_classes.add(target)
                elif cname not in direct_classes and target in direct_classes:
                    # 子模块类指向直连类
                    related_child_classes.add(cname)

        # 找出相关子模块类所属的namespace，保留整个namespace
        related_namespaces = {class_info[c]["namespace"] for c in related_child_classes if c in class_info}

        # 过滤class_info
        removed_namespaces = set()
        filtered_class_info = {}
        for cname, info in class_info.items():
            if info["namespace"] == "__direct__" or info["namespace"] in related_namespaces:
                filtered_class_info[cname] = info
            else:
                removed_namespaces.add(info["namespace"])

        if removed_namespaces:
            print(f"[hybrid_uml] 过滤掉与直连类无关的子模块: {removed_namespaces}")
        print(f"[hybrid_uml] 保留的子模块: {related_namespaces}")

        # 更新source_id_range，移除被过滤的类
        source_id_range = {k: v for k, v in source_id_range.items() if k in filtered_class_info}

        # ---- 按namespace分组，生成JSON格式 ----
        ns_groups = {}
        for cname, info in filtered_class_info.items():
            ns = info["namespace"]
            if ns not in ns_groups:
                ns_groups[ns] = []
            class_entry = {"name": cname, "declaration": info["declaration"]}
            if info["fields"]:
                class_entry["fields"] = info["fields"]
            if info["methods"]:
                class_entry["methods"] = info["methods"]
            if info["relations"]:
                # 清理指向已移除类的relation
                filtered_rels = [r for r in info["relations"]
                                 if r.split(" -> ")[-1].split(".")[0].strip() in filtered_class_info]
                if filtered_rels:
                    class_entry["relations"] = filtered_rels
            ns_groups[ns].append(class_entry)

        # __direct__ 的类不放在 namespace 中，其余按 namespace 分组
        node_information_json = []
        if "__direct__" in ns_groups:
            node_information_json.append({"direct_classes": ns_groups.pop("__direct__")})
        for ns, classes in ns_groups.items():
            node_information_json.append({"namespace": ns, "classes": classes})
        node_information = json.dumps(node_information_json, ensure_ascii=False, indent=2)
        for item in source_id_range.values():
            uu_id = generate_uuid_4digits()
            key = {"source_id": uu_id, "name": item['file_name'], "lines": item['lines']}
            source_id_full.append(key)
            source_id_ai.append({"source_id": uu_id, "name": item['name']})

        # 调试：将hybrid UML输入写入文件
        uml_debug_path = os.path.join(os.path.dirname(__file__), "hybrid_uml_input_debug.txt")
        with open(uml_debug_path, "w", encoding="utf-8") as f:
            f.write("=== node_information ===\n")
            f.write(node_information)
            f.write("\n\n=== source_id ===\n")
            f.write(json.dumps(source_id_ai, ensure_ascii=False, indent=2))
            f.write("\n\n=== class_source_map ===\n")
            f.write(json.dumps(source_map, ensure_ascii=False, indent=2))
        print(f"[DEBUG] Hybrid UML输入已写入 {uml_debug_path}")

        uml_token_counter = TokenCounter()
        cb_config = {"callbacks": [uml_token_counter]}
        print("node_information for hybrid UML:", node_information)
        def strip_namespace_prefix(mermaid_code: str) -> str:
            """去除关系线中的namespace前缀，避免Mermaid创建多余节点。
            例如: 'API Response and Error Management.CommonResult~T~ --> IErrorCode'
            变为: 'CommonResult~T~ --> IErrorCode'
            """
            # 收集所有已知的namespace名称
            ns_names = set(source_map.values()) - {"__direct__"}
            lines = mermaid_code.split('\n')
            cleaned = []
            for line in lines:
                for ns in ns_names:
                    # 替换 "namespace名." 前缀
                    line = line.replace(f"{ns}.", "")
                cleaned.append(line)
            return '\n'.join(cleaned)

        uml_result = await hybrid_uml_chain.ainvoke({"node_information": node_information, "source_id": source_id_ai}, config=cb_config)
        uml_parsed = extract_json(uml_result)
        uml_parsed["mermaid"] = strip_namespace_prefix(uml_parsed["mermaid"])
        uml_parsed["mermaid"] = _sanitize_class_diagram(uml_parsed["mermaid"])
        validate_result = validator.validate_file(f"```mermaid\n\n{uml_parsed['mermaid']}\n\n```")
        while not validate_result["result"]:
            print(validate_result)
            uml_result = await hybrid_uml_chain.ainvoke({"node_information": node_information + f"之前存在错误的情况，需要规避{validate_result['errors']}", "source_id": source_id_ai}, config=cb_config)
            uml_parsed = extract_json(uml_result)
            uml_parsed["mermaid"] = strip_namespace_prefix(uml_parsed["mermaid"])
            uml_parsed["mermaid"] = _sanitize_class_diagram(uml_parsed["mermaid"])
            validate_result = validator.validate_file(f"```mermaid\n\n{uml_parsed['mermaid']}\n\n```")

        mermaid_path = os.path.join(os.path.dirname(__file__), "hybrid_uml_mermaid.md")
        return {"chart_type": "混合模块类关系uml图（含namespace分组）", "mermaid_content": uml_parsed["mermaid"], "mermaid_source_info": node_information, "write_path": mermaid_path, "mapping": uml_parsed["mapping"], "id_list": source_id_full, "uml_token_stats": uml_token_counter.summary()}

    async def generate_time(state: ChartState) -> ChartState:
        query0 = """
        MATCH (n)<-[:DECLARES*1..]-(n0:Class|Interface)<-[:DECLARES]-(f:File)
        WHERE n.nodeId IN $node_list
        RETURN n.name AS name, n0.name AS n0_name, n0.semantic_explanation AS n0_sema, f.name AS file_name, n.semantic_explanation AS n_sema
        """
        key_target = []
        result = await neo4j_interface.execute_query(query0,{"node_list":node_list})
        name_list = []
        table_lines = ["\n下面介绍关键调用链上文件|类|函数的基本信息\n"]
        table_lines.append("| 所属文件 | 所属类 | 函数解释 |")
        table_lines.append("| --- | --- | --- |")
        for record in result:
            if record['n0_name'] not in name_list:
                name_list.append(record['n0_name'])
                table_lines.append(f"| {record['file_name']} | {record['n0_name']} | {json.loads(record['n0_sema'])['What']} |")

        query1="""
        MATCH (f1:File)-[:DECLARES]->(n1:Class|Interface)-[:DECLARES*1..]->(m1:Method)-[:CALLS]->(m2:Method)<-[:DECLARES*1..]-(n2:Class|Interface)<-[:DECLARES]-(f2:File)
        WHERE n1.name IN $name_list AND n2.name IN $name_list AND n1<>n2
        RETURN f1.name AS f1_name, n1.name AS n1_name, m1.name AS m1_name, f2.name AS f2_name, n2.name AS n2_name, m2.name AS m2_name,
                f1.source_code AS f1_code, n1.source_code AS n1_code, m1.source_code AS m1_code, m1.nodeId AS m1_id,
                f2.source_code AS f2_code, n2.source_code AS n2_code, m2.source_code AS m2_code, m2.nodeId AS m2_id
        """
        result = await neo4j_interface.execute_query(query1,{"name_list":name_list})
        source_id_ai = []
        source_id = []
        call_information = []
        method_groups = defaultdict(lambda: {
            "info": {}, #{file_name:, name: ,lines:}
            "method": {} #[methodname:{file_name:, name: ,lines:}]
        })
        for record in result:
            if record['n1_name'] not in method_groups:
                method_groups[record['n1_name']]['info'] = {
                    "file_name": record['f1_name'],
                    "name": record['n1_name'],
                    "lines": find_class_or_method_range(record['f1_code'], record['n1_code'], record['n1_name'])
                }
            method_key = f"{record['n1_name']}.{record['m1_name']}"
            if method_key not in method_groups[record['n1_name']]['method']:
                method_groups[record['n1_name']]['method'][method_key] = {
                    "file_name": record['f1_name'],
                    "name": method_key,
                    "lines": find_class_or_method_range(record['f1_code'], record['m1_code'], record['m1_name'])
              }            
            if record['n2_name'] not in method_groups:
                method_groups[record['n2_name']]['info'] = {
                    "file_name": record['f2_name'],
                    "name": record['n2_name'],
                    "lines": find_class_or_method_range(record['f2_code'], record['n2_code'], record['n2_name'])
                }
            method_key2 = f"{record['n2_name']}.{record['m2_name']}"
            if method_key2 not in method_groups[record['n2_name']]['method']:
                method_groups[record['n2_name']]['method'][method_key2] = {
                    "file_name": record['f2_name'],
                    "name": method_key2,
                    "lines": find_class_or_method_range(record['f2_code'], record['m2_code'], record['m2_name'])
                }
            if record['m1_id'] in node_list and record['m2_id'] in node_list:
                key_target.append(f"{record['n1_name']}.{record['m1_name']} calls {record['n2_name']}.{record['m2_name']}")
            # call_information.append(f"{record['n1_name']}.{record['m1_name']} calls {record['n2_name']}.{record['m2_name']}")
            call_information.append(f"{record['n1_name']}.{record['m1_name']} calls {record['n2_name']}")
        query2 = """
        MATCH (f1:File)-[:DECLARES]->(n1)-[:IMPLEMENTS]->(n2)<-[:DECLARES]-(f2:File)
        WHERE n1.name IN $name_list AND n2.name IN $name_list  AND n1<>n2
        RETURN f1.name AS f1_name, n1.name AS n1_name, f2.name AS f2_name, n2.name AS n2_name,
                f1.source_code AS f1_code, n1.source_code AS n1_code, 
                f2.source_code AS f2_code, n2.source_code AS n2_code
        """
        result = await neo4j_interface.execute_query(query2,{"name_list":name_list})
        for record in result:
            if record['n1_name'] not in method_groups:
                method_groups[record['n1_name']]['info'] = {
                    "file_name": record['f1_name'],
                    "name": record['n1_name'],
                    "lines": find_class_or_method_range(record['f1_code'], record['n1_code'], record['n1_name'])
                }
            if record['n2_name'] not in method_groups:
                method_groups[record['n2_name']]['info'] = {
                    "file_name": record['f2_name'],
                    "name": record['n2_name'],
                    "lines": find_class_or_method_range(record['f2_code'], record['n2_code'], record['n2_name'])
                }
            key_target.append(f"{record['n2_name']} implemented_by {record['n1_name']}")
            call_information.append(f"{record['n2_name']} implemented_by {record['n1_name']}")
        query3 = """
        MATCH (n:Class|Interface)-[:DECLARES*]->(m1:Method)-[:CALLS]->(m2:Method)<-[:DECLARES*]-(n:Class|Interface)
        MATCH (n)<-[:DECLARES]-(f:File)
        WHERE n.name IN $name_list AND m1.nodeId IN $node_list AND m2.nodeId IN $node_list
        RETURN f.name AS file_name, n.name AS n_name, m1.name AS m1_name, m2.name AS m2_name,
                f.source_code AS f_code, n.source_code AS n_code, m1.source_code AS m1_code, m2.source_code AS m2_code
        """
        result = await neo4j_interface.execute_query(query3,{"name_list":name_list,"node_list":node_list})
        for record in result:
            if record['n_name'] not in method_groups:
                method_groups[record['n_name']]['info'] = {
                    "file_name": record['file_name'],
                    "name": record['n_name'],
                    "lines": find_class_or_method_range(record['f_code'], record['n_code'], record['n_name'])
                }
            method_key = f"{record['n_name']}.{record['m1_name']}"
            if method_key not in method_groups[record['n_name']]['method']:
                method_groups[record['n_name']]['method'][method_key] = {
                    "file_name": record['file_name'],
                    "name": method_key,
                    "lines": find_class_or_method_range(record['f_code'], record['m1_code'], record['m1_name'])
                }
            method_key2 = f"{record['n_name']}.{record['m2_name']}"
            if method_key2 not in method_groups[record['n_name']]['method']:
                method_groups[record['n_name']]['method'][method_key2] = {
                    "file_name": record['file_name'],
                    "name": method_key2,
                    "lines": find_class_or_method_range(record['f_code'], record['m2_code'], record['m2_name'])
                }
            key_target.append(f"{record['n_name']}.{record['m1_name']} calls {record['n_name']}.{record['m2_name']}")
            # call_information.append(f"{record['n_name']}.{record['m1_name']} calls {record['n_name']}.{record['m2_name']}")
            call_information.append(f"{record['n_name']}.{record['m1_name']} calls {record['n_name']}")
        print("key_target", key_target)
        table_lines.append("\n关键调用链如下\n")
        table_lines.append("| from | relationship | to |")
        table_lines.append("| --- | --- | --- |")
        for item in key_target:
            calls_list = item.split(" ")
            table_lines.append(f"| {calls_list[0]} | {calls_list[1]} | {calls_list[2]} |")
        add_table = "\n".join(table_lines)
        for group in method_groups.values():
            info = group['info']
            uu_id = generate_uuid_4digits()
            source_id.append({"source_id": uu_id, "name": info['file_name'], "lines": info['lines']})
            source_id_ai.append({"source_id": uu_id, "name": info['name']})
            for method in group['method'].values():
                uu_id = generate_uuid_4digits()
                source_id.append({"source_id": uu_id, "name": info['file_name'], "lines": method['lines']})
                source_id_ai.append({"source_id": uu_id, "name": method['name']})
        call_information_str = "\n".join(call_information)
        time_parsed = await invoke_and_parse(time_chain, {"call_information": call_information_str, "source_id": source_id_ai})
        time_parsed['mermaid'] = sanitize_mermaid(time_parsed['mermaid'])
        validate_result = validator.validate_file(f"```mermaid\n\n{time_parsed['mermaid']}\n\n```")
        for _retry in range(MAX_MERMAID_RETRIES):
            if validate_result["result"]:
                break
            print(validate_result)
            time_parsed = await invoke_and_parse(time_chain, {"call_information": call_information_str + f"之前存在错误的情况，需要规避{validate_result['errors']}", "source_id": source_id_ai})
            time_parsed['mermaid'] = sanitize_mermaid(time_parsed['mermaid'])
            validate_result = validator.validate_file(f"```mermaid\n\n{time_parsed['mermaid']}\n\n```")

        mermaid_path = os.path.join(os.path.dirname(__file__), "time_mermaid.md")
        return {"chart_type":"代码调用链图", "mermaid_content": time_parsed["mermaid"], "mermaid_source_info": call_information_str, "write_path": mermaid_path, 'additional_info': add_table, "mapping": time_parsed["mapping"], "id_list": source_id}


    async def generate_block(state: ChartState) -> ChartState:
        query0 = """
        MATCH (n)<-[:DECLARES*1..]-(n0:Class|Interface)<-[:DECLARES]-(f:File)<-[:CONTAINS]-(p:Package)
        MATCH (n)<-[:DECLARES*1..]-(n0:Class|Interface)<-[:DECLARES]-(f:File)<-[:f2c]-(b:Block)
        WHERE n.nodeId IN $node_list
        RETURN n.name AS name, n0.name AS n0_name, b.name AS block_name, p.name AS package_name, f.name AS file_name,
               p.semantic_explanation AS package_sema, b.module_explaination AS block_sema
        """
        key_target = []
        package_info = {}
        module_info = {}
        result = await neo4j_interface.execute_query(query0,{"node_list":node_list})
        name_list = []
        module_package_info = []
        for record in result:
            if record['n0_name'] not in name_list:
                name_list.append(record['n0_name'])
            # key_target.append(f"{record['n0_name']}.{record['name']}")
                module_package_info.append(f"文件{record['file_name']} ，属于功能模块 {record['block_name']}，属于包 {record['package_name']}")
                if record['package_sema']:
                    package_info[record['package_name']] = json.loads(record['package_sema'])["What"] if isinstance(record['package_sema'], str) else record['package_sema']
                if record['block_sema']:
                    module_info[record['block_name']] = record['block_sema']

        # 生成 markdown 表格
        table_lines = ["\n下面介绍出现的包和功能模块的基本信息\n"]
        table_lines.append("| 类型 | 名称 | 语义解释 |")
        table_lines.append("| --- | --- | --- |")

        for package_name, explanation in package_info.items():
            table_lines.append(f"| Package | {package_name} | {explanation} |")

        for block_name, explanation in module_info.items():
            table_lines.append(f"| Block | {block_name} | {explanation} |")

        module_package_table = "\n".join(table_lines)
        print("name_list:",name_list)
        query1="""
        MATCH (f1:File)-[:DECLARES]->(n1:Class|Interface)-[:DECLARES*]->(m1:Method)-[:CALLS]->(m2:Method)<-[:DECLARES*]-(n2:Class|Interface)<-[:DECLARES]-(f2:File)
        WHERE n1.name IN $name_list AND n2.name IN $name_list
        RETURN f1.name AS f1_name, n1.name AS n1_name, m1.name AS m1_name, f2.name AS f2_name, n2.name AS n2_name, m2.name AS m2_name,
                f1.source_code AS f1_code, n1.source_code AS n1_code, m1.source_code AS m1_code, m1.nodeId AS m1_id,
                f2.source_code AS f2_code, n2.source_code AS n2_code, m2.source_code AS m2_code, m2.nodeId AS m2_id
        """
        result = await neo4j_interface.execute_query(query1,{"name_list":name_list})
        source_id_ai = []
        source_id = []
        call_information = []
        method_groups = defaultdict(lambda: {
            "info": {}, #{file_name:, name: ,lines:}
            "method": {} 
        })
        for record in result:
            if record['n1_name'] not in method_groups:
                method_groups[record['n1_name']]['info'] = {
                    "file_name": record['f1_name'],
                    "name": record['n1_name'],
                    "lines": find_class_or_method_range(record['f1_code'], record['n1_code'], record['n1_name'])
                }
                module_package_info.append(f"文件{record['f1_name']}定义了 {record['n1_name']} ")
            method_key = f"{record['n1_name']}.{record['m1_name']}"
            if method_key not in method_groups[record['n1_name']]['method']:
                method_groups[record['n1_name']]['method'][method_key] = {
                    "file_name": record['f1_name'],
                    "name": method_key,
                    "lines": find_class_or_method_range(record['f1_code'], record['m1_code'], record['m1_name'])
                }
            if record['n2_name'] not in method_groups:
                method_groups[record['n2_name']]['info'] = {
                    "file_name": record['f2_name'],
                    "name": record['n2_name'],
                    "lines": find_class_or_method_range(record['f2_code'], record['n2_code'], record['n2_name'])
                }
                module_package_info.append(f"文件{record['f2_name']}定义了 {record['n2_name']} ")
            method_key2 = f"{record['n2_name']}.{record['m2_name']}"
            if method_key2 not in method_groups[record['n2_name']]['method']:
                method_groups[record['n2_name']]['method'][method_key2] = {
                    "file_name": record['f2_name'],
                    "name": method_key2,
                    "lines": find_class_or_method_range(record['f2_code'], record['m2_code'], record['m2_name'])
                }
            if record['m1_id'] in node_list and record['m2_id'] in node_list:
                key_target.append(f"{record['n1_name']}.{record['m1_name']} calls {record['n2_name']}.{record['m2_name']}")
            call_information.append(f"{record['n1_name']}.{record['m1_name']} calls {record['n2_name']}.{record['m2_name']}")
        query2 = """
        MATCH (f1:File)-[:DECLARES]->(n1)-[:IMPLEMENTS]->(n2)<-[:DECLARES]-(f2:File)
        WHERE n1.name IN $name_list AND n2.name IN $name_list
        RETURN f1.name AS f1_name, n1.name AS n1_name, f2.name AS f2_name, n2.name AS n2_name,
                f1.source_code AS f1_code, n1.source_code AS n1_code, 
                f2.source_code AS f2_code, n2.source_code AS n2_code
        """
        result = await neo4j_interface.execute_query(query2,{"name_list":name_list})
        for record in result:
            if record['n1_name'] not in method_groups:
                method_groups[record['n1_name']]['info'] = {
                    "file_name": record['f1_name'],
                    "name": record['n1_name'],
                    "lines": find_class_or_method_range(record['f1_code'], record['n1_code'], record['n1_name'])
                }
                module_package_info.append(f"文件{record['f1_name']}定义了 {record['n1_name']} ")
            if record['n2_name'] not in method_groups:
                method_groups[record['n2_name']]['info'] = {
                    "file_name": record['f2_name'],
                    "name": record['n2_name'],
                    "lines": find_class_or_method_range(record['f2_code'], record['n2_code'], record['n2_name'])
                }
                module_package_info.append(f"文件{record['f2_name']}定义了 {record['n2_name']} ")
            key_target.append(f"{record['n2_name']} implemented_by {record['n1_name']}")
            call_information.append(f"{record['n2_name']} implemented_by {record['n1_name']}")
        query3 = """
        MATCH (n:Class|Interface)-[:DECLARES*]->(m1:Method)-[:CALLS]->(m2:Method)<-[:DECLARES*]-(n:Class|Interface)
        MATCH (n)<-[:DECLARES]-(f:File)
        WHERE n.name IN $name_list AND m1.nodeId IN $node_list AND m2.nodeId IN $node_list
        RETURN f.name AS file_name, n.name AS n_name, m1.name AS m1_name, m2.name AS m2_name,
                f.source_code AS f_code, n.source_code AS n_code, m1.source_code AS m1_code, m2.source_code AS m2_code
        """
        result = await neo4j_interface.execute_query(query3,{"name_list":name_list,"node_list":node_list})
        for record in result:
            if record['n_name'] not in method_groups:
                method_groups[record['n_name']]['info'] = {
                    "file_name": record['file_name'],
                    "name": record['n_name'],
                    "lines": find_class_or_method_range(record['f_code'], record['n_code'], record['n_name'])
                }
            method_key = f"{record['n_name']}.{record['m1_name']}"
            if method_key not in method_groups[record['n_name']]['method']:
                method_groups[record['n_name']]['method'][method_key] = {
                    "file_name": record['file_name'],
                    "name": method_key,
                    "lines": find_class_or_method_range(record['f_code'], record['m1_code'], record['m1_name'])
                }
            method_key2 = f"{record['n_name']}.{record['m2_name']}"
            if method_key2 not in method_groups[record['n_name']]['method']:
                method_groups[record['n_name']]['method'][method_key2] = {
                    "file_name": record['file_name'],
                    "name": method_key2,
                    "lines": find_class_or_method_range(record['f_code'], record['m2_code'], record['m2_name'])
                }
            key_target.append(f"{record['n_name']}.{record['m1_name']} calls {record['n_name']}.{record['m2_name']}")
            call_information.append(f"{record['n_name']}.{record['m1_name']} calls {record['n_name']}.{record['m2_name']}")
        for group in method_groups.values():
            info = group['info']
            uu_id = generate_uuid_4digits()
            source_id.append({"source_id": uu_id, "name": info['file_name'], "lines": info['lines']})
            source_id_ai.append({"source_id": uu_id, "name": info['name']})
            for method in group['method'].values():
                uu_id = generate_uuid_4digits()
                source_id.append({"source_id": uu_id, "name": info['file_name'], "lines": method['lines']})
                source_id_ai.append({"source_id": uu_id, "name": method['name']})
        call_information_str = "\n".join(call_information)
        module_package_info_str = "\n".join(module_package_info)
        print("key_target:",key_target)
        block_parsed = await invoke_and_parse(block_chain, {"call_information": call_information_str, "module_package_info": module_package_info_str, "source_id": source_id_ai})
        block_parsed['mermaid'] = sanitize_mermaid(block_parsed['mermaid'])
        validate_result = validator.validate_file(f"```mermaid\n\n{block_parsed['mermaid']}\n\n```")
        for _retry in range(MAX_MERMAID_RETRIES):
            if validate_result["result"]:
                break
            print(validate_result)
            block_parsed = await invoke_and_parse(block_chain, {"key_target": key_target, "call_information": call_information_str + f"之前存在错误的情况，需要规避{validate_result['errors']}", "module_package_info": module_package_info_str, "source_id": source_id_ai})
            block_parsed['mermaid'] = sanitize_mermaid(block_parsed['mermaid'])
            validate_result = validator.validate_file(f"```mermaid\n\n{block_parsed['mermaid']}\n\n```")

        mermaid_path = os.path.join(os.path.dirname(__file__), "block_mermaid.md")
        mermaid_source_info = f"module_package_info:{module_package_info_str}, \n call_information:{call_information_str}"
        return {"chart_type":"代码所属模块信息关系图", "mermaid_content": block_parsed["mermaid"], "mermaid_source_info": mermaid_source_info, "write_path": mermaid_path, "additional_info": module_package_table, "mapping": block_parsed["mapping"], "id_list": source_id}
    
    async def mermaid_description(state: ChartState) -> ChartState:
        mermaid_content = state["mermaid_content"]
        mermaid_path = state["write_path"]
        mermaid_source_info = state["mermaid_source_info"]
        chart_type = state["chart_type"]
        additional_info = state["additional_info"] if "additional_info" in state else ""
        uml_token_stats = state.get("uml_token_stats")
        if type == "hybrid_uml":
            # hybrid_uml 使用专用描述提示词，输入为 mermaid 图 + node_information(JSON)
            if uml_token_stats is not None:
                desc_counter = TokenCounter()
                mermaid_description = await hybrid_uml_desc_chain.ainvoke({"chart_mermaid": mermaid_content, "node_information": mermaid_source_info}, config={"callbacks": [desc_counter]})
                desc_stats = desc_counter.summary()
                uml_token_stats = {
                    "call_count": uml_token_stats["call_count"] + desc_stats["call_count"],
                    "total_input_tokens": uml_token_stats["total_input_tokens"] + desc_stats["total_input_tokens"],
                    "total_output_tokens": uml_token_stats["total_output_tokens"] + desc_stats["total_output_tokens"],
                    "total_tokens": uml_token_stats["total_tokens"] + desc_stats["total_tokens"],
                }
            else:
                mermaid_description = await hybrid_uml_desc_chain.ainvoke({"chart_mermaid": mermaid_content, "node_information": mermaid_source_info})
        elif type in ("cfg", "uml"):
            if uml_token_stats is not None:
                desc_counter = TokenCounter()
                mermaid_description = await description_chain.ainvoke({"chart_type": chart_type, "chart_mermaid": mermaid_content, "mermaid_source_info": mermaid_source_info}, config={"callbacks": [desc_counter]})
                desc_stats = desc_counter.summary()
                uml_token_stats = {
                    "call_count": uml_token_stats["call_count"] + desc_stats["call_count"],
                    "total_input_tokens": uml_token_stats["total_input_tokens"] + desc_stats["total_input_tokens"],
                    "total_output_tokens": uml_token_stats["total_output_tokens"] + desc_stats["total_output_tokens"],
                    "total_tokens": uml_token_stats["total_tokens"] + desc_stats["total_tokens"],
                }
            else:
                mermaid_description = await description_chain.ainvoke({"chart_type": chart_type, "chart_mermaid": mermaid_content, "mermaid_source_info": mermaid_source_info})
        else:
            mermaid_description = ""
        output = "```mermaid\n" + mermaid_content + "\n```\n" + mermaid_description + "\n" + additional_info + "\n"
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write(output)

        return {"output": output}


    app = StateGraph(ChartState)
    app.add_node("generate_cfg", generate_cfg)
    app.add_node("generate_uml", generate_uml)
    app.add_node("generate_hybrid_uml", generate_hybrid_uml)
    app.add_node("generate_time", generate_time)
    app.add_node("generate_block", generate_block)
    app.add_node("mermaid_description", mermaid_description)
    if type == "cfg":
        app.set_entry_point("generate_cfg")
    elif type == "uml":
        app.set_entry_point("generate_uml")
    elif type == "hybrid_uml":
        app.set_entry_point("generate_hybrid_uml")
    elif type == "time":
        app.set_entry_point("generate_time")
    elif type == "block":
        app.set_entry_point("generate_block")
    app.add_edge("generate_cfg", "mermaid_description")
    app.add_edge("generate_uml", "mermaid_description")
    app.add_edge("generate_hybrid_uml", "mermaid_description")
    app.add_edge("generate_time", "mermaid_description")
    app.add_edge("generate_block", "mermaid_description")
    app.add_edge("mermaid_description", END)

    app = app.compile(checkpointer=MemorySaver())
    return app

# ====================== 4. 独立运行入口 ======================
async def main():
    load_dotenv()
    print("=== 独立运行对外提供接口说明文档生成应用 ===")

    llm = LLMInterface(model_name="gpt-4.1", provider="openai")
    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )
    if not await neo4j.test_connection():
        print("[ERR] Neo4j 连接失败")
        return
    print("[INFO] Neo4j 连接成功")
    start_time = time.time()
    node_list = [17701] #17701,17762
    type = "cfg"

    # node_list = [17522, 17618, 17656, 17577, 17702, 17711]
    # type = "uml" "block" "time"

    app = chart_app(llm, neo4j, node_list=node_list, type=type)
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