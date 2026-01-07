import os
import sys
import json
import asyncio
import re
import uuid
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
from chains.prompts.type_chart_prompt import SOURCE_ID_PROMPT, CFG_PROMPT, UML_PROMPT, TIME_PROMPT, BLOCK_PROMPT, VALIDATE_PROMPT, CFG_ID_PROMPT

def generate_uuid_4digits() -> str:
    """生成4位唯一ID"""
    return str(uuid.uuid4().int)[:4]

class ChartState(TypedDict, total=False):
    chart_type: str

def chart_app(llm_interface: LLMInterface, neo4j_interface: Neo4jInterface, node_list: List[int] , type: str) -> StateGraph:
    cfg_id_chain = ChainFactory.create_generic_chain(llm_interface, SOURCE_ID_PROMPT)
    cfg_chain = ChainFactory.create_generic_chain(llm_interface, CFG_PROMPT)
    cfg_id_validate_chain = ChainFactory.create_generic_chain(llm_interface, CFG_ID_PROMPT)
    uml_chain = ChainFactory.create_generic_chain(llm_interface, UML_PROMPT)
    time_chain = ChainFactory.create_generic_chain(llm_interface, TIME_PROMPT)
    block_chain = ChainFactory.create_generic_chain(llm_interface, BLOCK_PROMPT)
    validate_chain = ChainFactory.create_generic_chain(llm_interface, VALIDATE_PROMPT)

    async def generate_cfg(state: ChartState) -> ChartState:
        node_id = node_list[0]
         # ---- Cypher 查询 ----
        # query0 = """
        # MATCH (n)-[:CALLS]->(m)
        # WHERE n.nodeId = $node_id AND m.nodeId IN $to_id_list
        # RETURN DISTINCT m.name AS name
        # """
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
        result1, result2, result3, result4 = await asyncio.gather(
            # neo4j_interface.execute_query(query0, {"node_id": node_id, "to_id_list": node_list}),
            neo4j_interface.execute_query(query1, {"node_id": node_id}),
            neo4j_interface.execute_query(query2, {"node_id": node_id}),
            neo4j_interface.execute_query(query3, {"node_id": node_id}),
            neo4j_interface.execute_query(query4, {"node_id": node_id}),
        )
        node_information = []

        # if result0:
        #     key_target = result0[0]
        #     print("key_target:",key_target)
        if result1:
            code = result1[0]
            # if not key_target:
            #     key_target = name
            file_name = code['file_name']
            source_code = code['source_code']
            semantic_explanation = code['SE_How']
            node_information.append(
                f"函数 {code['name']} 语义解释为 {code['SE_How']}\n下面是与其相关的类的介绍"
            )
            base_lines = find_class_or_method_range(code['file_code'], code['source_code'], code['name'])
        print("base_lines:", base_lines)
        base_start = int(base_lines[0].split('-')[0])
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
        source_id_result = await cfg_id_chain.ainvoke({"source_code": tag_code, "explanation": semantic_explanation})
        print("source_id:",source_id_result)
        reason = json.loads(source_id_result)["reason"]
        id_list = [] #[{'source_id': '2662', 'lines': ['1-2']}]
        id_list_map = {} #{'2662': ['1-2']}
        cfg_lines_map = {} #{'A1': ['1-2']}

        for item in json.loads(source_id_result)["lines"]:
            uu_id = generate_uuid_4digits()
            id_list.append({"source_id": uu_id, "lines": item})
            id_list_map[uu_id] = item

        cfg_result = await cfg_chain.ainvoke({"source_code": tag_code, "explanation": all_in, "source_id": id_list, "code_block": reason})
        cfg_map = json.loads(cfg_result)["mapping"] # {'A1': '2662'}
        for key,value in cfg_map.items():
            lines = id_list_map[value]
            cfg_lines_map[key] = lines
        print("old_id_result:", cfg_lines_map)
        new_id_result = await cfg_id_validate_chain.ainvoke({"source_code": tag_code, "mermaid": json.loads(cfg_result)["mermaid"], "reason": reason, "mapping": cfg_lines_map})
        print("new_id_result:",json.loads(new_id_result)["mapping"], json.loads(new_id_result)["reason"])
        new_map = json.loads(new_id_result)["mapping"] # {'A1': ['8-10'], 'B1': ['11-20','80']}
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
        resultt = json.dumps({"mermaid": json.loads(cfg_result)["mermaid"], "mapping": json.loads(cfg_result)["mapping"], "id_list": new_id_list}, ensure_ascii=False, indent=4)
        out_path = os.path.join(os.path.dirname(__file__), "cfg.json")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(resultt)
        mermaid_path = os.path.join(os.path.dirname(__file__), "cfg_mermaid.md")
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write("```mermaid\n")
            f.write(json.loads(cfg_result)["mermaid"])
            f.write("\n```")
        return

    async def generate_uml(state: ChartState) -> ChartState:
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
        WHERE n.name = $name AND n<>n0
        RETURN m1.name AS m1_name, m2.name AS m2_name, n0.name AS n0_name, n0.source_code AS n0_code, n1.source_code AS file_code, n1.name AS file_name
        """
        query4 = """
        MATCH (n)-[:DECLARES*1..]->(m1:Method)-[:USES]->(n0:Class)<-[:DECLARES]-(n1:File)
        WHERE n.name = $name AND n<>n0
        RETURN m1.name AS m1_name, n0.name AS n0_name, n0.source_code AS n0_code, n0.file_id AS file_id, n1.source_code AS file_code, n1.name AS file_name
        """
        query5 = """
        MATCH (n)-[:DECLARES*1..]->(m1:Method)-[:RETURNS]->(n0:Class)<-[:DECLARES]-(n1:File)
        WHERE n.name = $name AND n<>n0
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
                neo4j_interface.execute_query(query3, {"name": name}),
                neo4j_interface.execute_query(query4, {"name": name}),
                neo4j_interface.execute_query(query5, {"name": name}),
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
            node_information.append(f"\n下面是与类 {name} 相关的类的介绍，类 {name} 的源码为 {code['n_code']}")
            # file_id.append(code['file_id'])
            if result1:
                print(f"{name} 实现了", len(result1))
                for record in result1:
                    node_information.append(f"\n类 {name} 实现了 {record['n0_name']}，{record['n0_name']} 的源码为 {record['n0_code']}")
                    unique_key = record['n0_name']
                    if unique_key not in source_id_range:
                        lines = find_class_or_method_range(record['file_code'], record['n0_code'], record['n0_name'])
                        source_id_range[unique_key] = {
                            "file_name": record['file_name'],
                            "name": record['n0_name'],
                            "lines": lines
                        }
                    # file_id.append(record['file_id'])
            if result2:
                print(f"{name} 继承了", len(result2))
                for record in result2:
                    node_information.append(f"\n类 {name} 继承了 {record['n0_name']}，{record['n0_name']} 的源码为 {record['n0_code']}")
                    unique_key = record['n0_name']
                    if unique_key not in source_id_range:
                        lines = find_class_or_method_range(record['file_code'], record['n0_code'], record['n0_name'])
                        source_id_range[unique_key] = {
                            "file_name": record['file_name'],
                            "name": record['n0_name'],
                            "lines": lines
                        }
                    # file_id.append(record['file_id'])
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
                    node_information.append(f"\n类 {key} 源码为 {code_dict[key]}")
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
        uml_result = await uml_chain.ainvoke({"node_information": node_information, "source_id": source_id_ai})
        # validate_uml_result = await validate_chain.ainvoke({"source_information": node_information, "source_id": source_id_ai, "chart_mermaid": json.loads(uml_result)["mermaid"], "chart_mapping": json.loads(uml_result)["mapping"]})
        # while json.loads(validate_uml_result)["result"] == "false":
        #     print(validate_uml_result)
        #     uml_result = await uml_chain.ainvoke({"node_information": node_information + f"之前存在错误的情况，需要规避{json.loads(validate_uml_result)['reason']}", "source_id": source_id_ai})
        #     validate_uml_result = await validate_chain.ainvoke({"source_information": node_information, "source_id": source_id_ai, "chart_mermaid": json.loads(uml_result)["mermaid"], "chart_mapping": json.loads(uml_result)["mapping"]})
        resultt = json.dumps({"mermaid": json.loads(uml_result)["mermaid"], "mapping": json.loads(uml_result)["mapping"], "id_list": source_id_full}, ensure_ascii=False, indent=4)
        out_path = os.path.join(os.path.dirname(__file__), "uml.json")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(resultt) 
        mermaid_path = os.path.join(os.path.dirname(__file__), "uml_mermaid.md")
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write("```mermaid\n")
            f.write(json.loads(uml_result)["mermaid"])
            f.write("\n```")
        return
    
    async def generate_time(state: ChartState) -> ChartState:
        query0 = """
        MATCH (n)<-[:DECLARES*1..]-(n0:Class|Interface)<-[:DECLARES]-(f:File)
        WHERE n.nodeId IN $node_list
        RETURN n.name AS name, n0.name AS n0_name
        """
        key_target = []
        result = await neo4j_interface.execute_query(query0,{"node_list":node_list})
        name_list = []
        for record in result:
            if record['n0_name'] not in name_list:
                name_list.append(record['n0_name'])
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
        time_result = await time_chain.ainvoke({"call_information": call_information_str, "source_id": source_id_ai})
        # validate_time_result = await validate_chain.ainvoke({"source_information": call_information_str, "source_id": source_id_ai, "chart_mermaid": json.loads(time_result)["mermaid"], "chart_mapping": json.loads(time_result)["mapping"]})
        # while json.loads(validate_time_result)["result"] == "false":
        #     print(validate_time_result)
        #     time_result = await time_chain.ainvoke({"key_target": key_target, "call_information": call_information_str + f"之前存在错误的情况，需要规避{json.loads(validate_time_result)['reason']}", "source_id": source_id_ai})
        #     validate_time_result = await validate_chain.ainvoke({"source_information": call_information_str, "source_id": source_id_ai, "chart_mermaid": json.loads(time_result)["mermaid"], "chart_mapping": json.loads(time_result)["mapping"]})  
        resultt = json.dumps({"mermaid": json.loads(time_result)["mermaid"], "mapping": json.loads(time_result)["mapping"], "id_list": source_id}, ensure_ascii=False, indent=4)
        out_path = os.path.join(os.path.dirname(__file__), "time.json")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(resultt)
        mermaid_path = os.path.join(os.path.dirname(__file__), "time_mermaid.md")
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write("```mermaid\n")
            f.write(json.loads(time_result)["mermaid"])
            f.write("\n```")
        return

    async def generate_block(state: ChartState) -> ChartState:
        query0 = """
        MATCH (n)<-[:DECLARES*1..]-(n0:Class|Interface)<-[:DECLARES]-(f:File)<-[:CONTAINS]-(p:Package)
        MATCH (n)<-[:DECLARES*1..]-(n0:Class|Interface)<-[:DECLARES]-(f:File)<-[:f2c]-(b:Block)
        WHERE n.nodeId IN $node_list
        RETURN n.name AS name, n0.name AS n0_name, b.name AS block_name, p.name AS package_name, f.name AS file_name
        """
        key_target = []
        result = await neo4j_interface.execute_query(query0,{"node_list":node_list})
        name_list = []
        module_package_info = []
        for record in result:
            if record['n0_name'] not in name_list:
                name_list.append(record['n0_name'])
            # key_target.append(f"{record['n0_name']}.{record['name']}")
                module_package_info.append(f"文件{record['file_name']} ，属于功能模块 {record['block_name']}，属于包 {record['package_name']}")
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
        block_result = await block_chain.ainvoke({"call_information": call_information_str, "module_package_info": module_package_info_str, "source_id": source_id_ai})
        # validate_block_result = await validate_chain.ainvoke({"source_information": call_information_str + module_package_info_str, "source_id": source_id_ai, "chart_mermaid": json.loads(block_result)["mermaid"], "chart_mapping": json.loads(block_result)["mapping"]})
        # while json.loads(validate_block_result)["result"] == "false":
        #     print(validate_block_result)
        #     block_result = await block_chain.ainvoke({"key_target": key_target, "call_information": call_information_str + f"之前存在错误的情况，需要规避{json.loads(validate_block_result)['reason']}", "module_package_info": module_package_info_str, "source_id": source_id_ai})
        #     validate_block_result = await validate_chain.ainvoke({"source_information": call_information_str + module_package_info_str, "source_id": source_id_ai, "chart_mermaid": json.loads(block_result)["mermaid"], "chart_mapping": json.loads(block_result)["mapping"]})
        resultt = json.dumps({"mermaid": json.loads(block_result)["mermaid"], "mapping": json.loads(block_result)["mapping"], "id_list": source_id}, ensure_ascii=False, indent=4)
        out_path = os.path.join(os.path.dirname(__file__), "block.json")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(resultt)
        mermaid_path = os.path.join(os.path.dirname(__file__), "block_mermaid.md")
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write("```mermaid\n")
            f.write(json.loads(block_result)["mermaid"])
            f.write("\n```")
        return
    # async def route_decision(state: NodeState) -> str:
    #     """根据 choice 的值决定下一个节点"""
    #     if type == "block":
    #         return "generate_block"  
    #     elif type == "time":
    #         return "generate_time"  
    #     elif type == "uml":
    #         return "generate_uml"  
    #     elif type == "cfg":
    #         return "generate_cfg"

    app = StateGraph(ChartState)
    app.add_node("generate_cfg", generate_cfg)
    app.add_node("generate_uml", generate_uml)
    app.add_node("generate_time", generate_time)
    app.add_node("generate_block", generate_block)
    # app.add_node("route", route_decision)
    # app.add_edge("route", "generate_cfg")
    # app.add_edge("route", "generate_uml")
    # app.add_edge("route", "generate_time")
    # app.add_edge("route", "generate_block")
    # app.set_entry_point("route")
    if type == "cfg":
        app.set_entry_point("generate_cfg")
    elif type == "uml":
        app.set_entry_point("generate_uml")
    elif type == "time":
        app.set_entry_point("generate_time")
    elif type == "block":
        app.set_entry_point("generate_block")
    app.add_edge("generate_cfg", END)
    app.add_edge("generate_uml", END)
    app.add_edge("generate_time", END)
    app.add_edge("generate_block", END)

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
    node_list = [17762] #17701
    type = "cfg"

    # node_list = [17522, 17618, 17656, 17577, 17702, 17711]
    # type = "time"

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