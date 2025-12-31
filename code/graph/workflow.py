"""调用链分析工作流：负责流程编排和文档生成"""
import os
import logging
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from interfaces.neo4j_interface import Neo4jInterface
from interfaces.llm_interface import LLMInterface
from prompts import (
    SYSTEM_MESSAGE,
    SYSTEM_MESSAGE_DOC,
    TASK1_CALL_CHAIN_TEMPLATE,
    TASK2_MODULE_DIAGRAM_TEMPLATE,
    TASK2_TEXT_TABLE_TEMPLATE,
    TASK3_CONTROL_FLOW_TEMPLATE,
)

logger = logging.getLogger(__name__)


# ========== 状态定义 ==========

class CallChainState(TypedDict):
    """调用链分析工作流状态"""
    # 配置
    output_file: str
    
    # 接口实例
    neo4j: Optional[Neo4jInterface]
    llm: Optional[LLMInterface]
    
    # 从 Neo4j 提取的原始数据
    classes_data: Dict[str, Any]
    methods_data: Dict[str, Any]
    call_relations: List[Dict[str, Any]]
    module_relations: List[Dict[str, Any]]
    
    # 生成的结果
    task1_diagram: str
    task1_file_ids: str  # 任务1的 file_id 列表
    task1_block_node_ids: str  # 任务1的 block_node_id 列表
    task2_diagram: str
    task2_file_ids: str  # 任务2的 file_id 列表
    task2_block_node_ids: str  # 任务2的 block_node_id 列表
    task2_text: str
    task3_diagrams: List[Dict[str, str]]
    task3_file_ids_summary: str  # 任务3的 file_id 汇总

    # 最终输出
    markdown_content: str
    metadata: Dict[str, Any]


# ========== 工作流节点 ==========

def init_connections_node(state: CallChainState) -> CallChainState:
    """节点1: 初始化连接（Neo4j + LLM）"""
    logger.info("=" * 60)
    logger.info("🔌 [节点1] 初始化连接...")
    logger.info("=" * 60)
    
    # 初始化 Neo4j（配置从环境变量读取）
    neo4j = Neo4jInterface()
    
    # 初始化 LLM
    llm = LLMInterface()
    
    logger.info("✅ [节点1] 连接初始化完成（Neo4j + LLM）\n")
    return {"neo4j": neo4j, "llm": llm}


def extract_data_node(state: CallChainState) -> CallChainState:
    """节点2: 从 Neo4j 提取数据"""
    logger.info("=" * 60)
    logger.info("📊 [节点2] 从 Neo4j 提取数据...")
    logger.info("=" * 60)
    
    neo4j = state["neo4j"]
    data = neo4j.extract_all_data()
    
    logger.info("✅ [节点2] 数据提取完成\n")
    
    return {
        "classes_data": data["classes"],
        "methods_data": data["methods"],
        "call_relations": data["call_relations"],
        "module_relations": data["module_relations"]
    }


def generate_task1_node(state: CallChainState) -> CallChainState:
    """节点3: 生成任务1图表（类调用链时序图）"""
    logger.info("=" * 60)
    logger.info("📈 [节点3] 生成任务1：类调用链时序图...")
    logger.info("=" * 60)

    llm = state["llm"]
    classes_data = state["classes_data"]
    methods_data = state["methods_data"]
    call_relations = state["call_relations"]

    # 收集使用到的 file_id 和 block_node_id
    task1_file_ids = set()
    task1_block_node_ids = set()

    # 构建类信息文本（使用已提取的类列表）
    classes_info_parts = []

    for class_name in classes_data.keys():
        if class_name in classes_data:
            class_info = classes_data[class_name]
            classes_info_parts.append(f"### 类: {class_name}\n")

            # 收集该类的 file_id
            if class_info.get("file_id") is not None:
                task1_file_ids.add(class_info["file_id"])

            semantic = class_info.get("semantic_explanation")
            if semantic and isinstance(semantic, dict):
                what = semantic.get("What", "")
                if what:
                    classes_info_parts.append(f"**功能说明**: {what}\n")

            class_methods = [m for m in methods_data.values() if m.get("class_name") == class_name]
            if class_methods:
                classes_info_parts.append("**方法列表**:\n")
                for method in class_methods:
                    method_name = method.get("name", "")
                    method_semantic = method.get("semantic_explanation")
                    method_what = ""
                    if method_semantic and isinstance(method_semantic, dict):
                        method_what = method_semantic.get("What", "")
                    classes_info_parts.append(f"- {method_name}")
                    if method_what:
                        classes_info_parts.append(f": {method_what}\n")
                    else:
                        classes_info_parts.append("\n")

                    # 收集方法的 file_id
                    if method.get("file_id") is not None:
                        task1_file_ids.add(method["file_id"])
            classes_info_parts.append("\n")

    classes_info = "".join(classes_info_parts)

    # 构建调用关系文本
    call_relations_parts = []
    for relation in call_relations:
        call_relations_parts.append(
            f"- {relation['from_class']}.{relation['from_method']} -> "
            f"{relation['to_class']}.{relation['to_method']}\n"
        )
        # 收集调用关系中的 file_id
        if relation.get("from_file_id") is not None:
            task1_file_ids.add(relation["from_file_id"])
        if relation.get("to_file_id") is not None:
            task1_file_ids.add(relation["to_file_id"])
    call_relations_text = "".join(call_relations_parts)

    # 调用LLM生成图表（自动验证和修复）
    mermaid_code = llm.invoke_with_template(
        template=TASK1_CALL_CHAIN_TEMPLATE,
        variables={
            "classes_info": classes_info,
            "call_relations": call_relations_text
        },
        system_message=SYSTEM_MESSAGE,
        expected_diagram_type="sequenceDiagram"
    )

    # 从 module_relations 中收集 block_node_id
    module_relations = state["module_relations"]
    for relation in module_relations:
        if relation.get("class_name") in classes_data:
            block_node_id = relation.get("block_node_id")
            if block_node_id is not None:
                task1_block_node_ids.add(block_node_id)

    # 添加 file_id 列表到输出
    file_ids_list = sorted(list(task1_file_ids))
    file_ids_text = "\n\n**使用到的文件节点ID列表**:\n\n" + "\n".join([f"- File ID: {fid}" for fid in file_ids_list])

    # 添加 block_node_id 列表到输出
    block_node_ids_list = sorted(list(task1_block_node_ids))
    block_node_ids_text = ""
    if block_node_ids_list:
        block_node_ids_text = "\n\n**使用到的Block节点ID列表**:\n\n" + "\n".join([f"- Block Node ID: {bid}" for bid in block_node_ids_list])

    logger.info(f"✅ [节点3] 任务1图表生成完成，使用了 {len(file_ids_list)} 个文件节点，{len(block_node_ids_list)} 个Block节点\n")
    return {
        "task1_diagram": mermaid_code,
        "task1_file_ids": file_ids_text,
        "task1_block_node_ids": block_node_ids_text
    }


def generate_task2_node(state: CallChainState) -> CallChainState:
    """节点4: 生成任务2图表（模块关系图）"""
    logger.info("=" * 60)
    logger.info("📊 [节点4] 生成任务2：模块关系图...")
    logger.info("=" * 60)
    
    llm = state["llm"]
    methods_data = state["methods_data"]
    module_relations = state["module_relations"]
    call_relations = state["call_relations"]
    
    # 按 Block 分组组织模块关系（统一使用 Block 作为外层）
    from collections import defaultdict
    blocks = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
        "classes": [],
        "block_semantic": None,
        "package_semantic": None,
        "file_semantic": None
    })))
    
    # 组织数据：Block -> Package -> File -> Classes
    for relation in module_relations:
        block = relation.get('block') or "(unassigned)"
        pkg = relation['package_name']
        file = relation['file_name']
        class_name = relation['class_name']
        
        blocks[block][pkg][file]["classes"].append(class_name)
        # 保存语义信息
        if relation.get('block_semantic'):
            blocks[block][pkg][file]["block_semantic"] = relation['block_semantic']
        if relation.get('package_semantic'):
            blocks[block][pkg][file]["package_semantic"] = relation['package_semantic']
        if relation.get('file_semantic'):
            blocks[block][pkg][file]["file_semantic"] = relation['file_semantic']
    
    # 提取所有在调用关系中涉及的方法（仅保留有跨类调用关系的方法）
    methods_in_calls = set()
    for relation in call_relations:
        methods_in_calls.add((relation['from_class'], relation['from_method']))
        methods_in_calls.add((relation['to_class'], relation['to_method']))
    
    # 构建模块关系文本（Block > Package > File > Class > Method 层级）
    module_relations_parts = []
    module_relations_parts.append("# 代码结构层级（按 Block 分组）\n\n")
    
    for block_name in sorted(blocks.keys()):
        module_relations_parts.append(f"## Block: {block_name}\n")
        packages = blocks[block_name]
        
        for pkg_name in sorted(packages.keys()):
            module_relations_parts.append(f"\n### Package: {pkg_name}\n")
            files = packages[pkg_name]
            
            for file_name in sorted(files.keys()):
                module_relations_parts.append(f"\n#### File: {file_name}\n")
                
                # 列出该文件声明的所有Classes
                classes = files[file_name]["classes"]
                module_relations_parts.append(f"**Classes (declares关系):**\n")
                for cls in sorted(classes):
                    module_relations_parts.append(f"  - {file_name} -[declares]-> {cls}\n")
                    
                    # 只列出该类中有调用关系的方法
                    class_methods_in_calls = [
                        method_name for class_name, method_name in methods_in_calls
                        if class_name == cls
                    ]
                    if class_methods_in_calls:
                        module_relations_parts.append(f"    **Methods (有调用关系):**\n")
                        for method in sorted(class_methods_in_calls):
                            module_relations_parts.append(f"      - {cls} -[declares]-> {method}\n")
                
                module_relations_parts.append("\n")
        
        module_relations_parts.append("\n")
    
    module_relations_text = "".join(module_relations_parts)
    
    # 构建方法级别的调用关系文本
    method_call_relations_parts = []
    method_call_relations_parts.append("# 方法调用关系\n\n")
    
    for relation in call_relations:
        from_class = relation['from_class']
        from_method = relation['from_method']
        to_class = relation['to_class']
        to_method = relation['to_method']
        
        method_call_relations_parts.append(
            f"- {from_class}.{from_method} -[calls]-> {to_class}.{to_method}\n"
        )
    
    method_call_relations_text = "".join(method_call_relations_parts)
    
    # 收集使用到的 file_id 和 block_node_id
    task2_file_ids = set()
    task2_block_node_ids = set()
    classes_data = state["classes_data"]

    # 从 classes_data 中收集 file_id
    for class_name in classes_data.keys():
        class_info = classes_data[class_name]
        if class_info.get("file_id") is not None:
            task2_file_ids.add(class_info["file_id"])

    # 从 methods_data 中收集 file_id
    for method_info in methods_data.values():
        if method_info.get("file_id") is not None:
            task2_file_ids.add(method_info["file_id"])

    # 从 call_relations 中收集 file_id
    for relation in call_relations:
        if relation.get("from_file_id") is not None:
            task2_file_ids.add(relation["from_file_id"])
        if relation.get("to_file_id") is not None:
            task2_file_ids.add(relation["to_file_id"])

    # 从 module_relations 中收集 block_node_id
    for relation in module_relations:
        block_node_id = relation.get("block_node_id")
        if block_node_id is not None:
            task2_block_node_ids.add(block_node_id)

    # 调用LLM生成图表（自动验证和修复）
    mermaid_code = llm.invoke_with_template(
        template=TASK2_MODULE_DIAGRAM_TEMPLATE,
        variables={
            "module_relations": module_relations_text,
            "method_call_relations": method_call_relations_text
        },
        system_message=SYSTEM_MESSAGE,
        expected_diagram_type="graph TD"
    )

    # 添加 file_id 列表到输出
    file_ids_list = sorted(list(task2_file_ids))
    file_ids_text = "\n\n**使用到的文件节点ID列表**:\n\n" + "\n".join([f"- File ID: {fid}" for fid in file_ids_list])

    # 添加 block_node_id 列表到输出
    block_node_ids_list = sorted(list(task2_block_node_ids))
    block_node_ids_text = ""
    if block_node_ids_list:
        block_node_ids_text = "\n\n**使用到的Block节点ID列表**:\n\n" + "\n".join([f"- Block Node ID: {bid}" for bid in block_node_ids_list])

    logger.info(f"✅ [节点4] 任务2图表生成完成，使用了 {len(file_ids_list)} 个文件节点，{len(block_node_ids_list)} 个Block节点\n")
    return {
        "task2_diagram": mermaid_code,
        "task2_file_ids": file_ids_text,
        "task2_block_node_ids": block_node_ids_text
    }


def generate_task2_text_node(state: CallChainState) -> CallChainState:
    """节点5: 生成任务2文字说明（表格：Block 外层，Package 内层）"""
    logger.info("=" * 60)
    logger.info("🗒️ [节点5] 生成任务2：表格文字说明（Block > Package）...")
    logger.info("=" * 60)

    llm = state["llm"]
    module_relations = state["module_relations"]
    call_relations = state["call_relations"]

    # 汇总参与跨类调用的方法集合
    methods_in_calls = set()
    for relation in call_relations:
        methods_in_calls.add((relation['from_class'], relation['from_method']))
        methods_in_calls.add((relation['to_class'], relation['to_method']))

    # 组装行数据（简化：一个 Class 只有一行记录）
    import json
    rows = []
    for relation in module_relations:
        block = relation.get('block') or "(unassigned)"
        pkg = relation.get('package_name', '')
        file = relation.get('file_name', '')
        cls = relation.get('class_name', '')
        
        # 语义说明（仅提取 What 字段）
        pkg_sem = relation.get('package_semantic') or {}
        file_sem = relation.get('file_semantic') or {}
        block_sem = relation.get('block_semantic') or {}
        
        package_what = pkg_sem.get('What', '') if isinstance(pkg_sem, dict) else ''
        file_what = file_sem.get('What', '') if isinstance(file_sem, dict) else ''
        block_explanation = block_sem if block_sem else ""
        
        # 该类参与跨类调用的方法
        class_methods = sorted({m for (c, m) in methods_in_calls if c == cls})

        rows.append({
            "block": block,
            "package": pkg,
            "file": file,
            "class": cls,
            "methods": class_methods,
            "block_explanation": block_explanation,
            "package_what": package_what,
            "file_what": file_what
        })

    block_rows = json.dumps(rows, ensure_ascii=False, indent=2)

    # 构建方法调用关系列表文本
    cr_lines = []
    for cr in call_relations:
        cr_lines.append(f"{cr['from_class']}.{cr['from_method']} -> {cr['to_class']}.{cr['to_method']}")
    call_relations_text = "\n".join(cr_lines)

    # 收集使用到的 file_id 和 block_node_id
    task2_text_file_ids = set()
    task2_text_block_node_ids = set()
    classes_data = state["classes_data"]
    methods_data = state["methods_data"]

    # 从 classes_data 中收集 file_id
    for class_name in classes_data.keys():
        class_info = classes_data[class_name]
        if class_info.get("file_id") is not None:
            task2_text_file_ids.add(class_info["file_id"])

    # 从 methods_data 中收集 file_id（仅收集参与调用的方法）
    for (class_name, method_name) in methods_in_calls:
        method_key = f"{class_name}.{method_name}"
        if method_key in methods_data:
            method_info = methods_data[method_key]
            if method_info.get("file_id") is not None:
                task2_text_file_ids.add(method_info["file_id"])

    # 从 call_relations 中收集 file_id
    for relation in call_relations:
        if relation.get("from_file_id") is not None:
            task2_text_file_ids.add(relation["from_file_id"])
        if relation.get("to_file_id") is not None:
            task2_text_file_ids.add(relation["to_file_id"])

    # 从 module_relations 中收集 block_node_id
    for relation in module_relations:
        block_node_id = relation.get("block_node_id")
        if block_node_id is not None:
            task2_text_block_node_ids.add(block_node_id)

    # 调用 LLM 生成 Markdown 表格说明
    text_description = llm.invoke_with_template(
        template=TASK2_TEXT_TABLE_TEMPLATE,
        variables={
            "block_rows": block_rows,
            "call_relations": call_relations_text
        },
        system_message=SYSTEM_MESSAGE_DOC,
    )

    # 添加 file_id 列表到输出
    file_ids_list = sorted(list(task2_text_file_ids))
    file_ids_text = "\n\n**使用到的文件节点ID列表**:\n\n" + "\n".join([f"- File ID: {fid}" for fid in file_ids_list])

    # 添加 block_node_id 列表到输出
    block_node_ids_list = sorted(list(task2_text_block_node_ids))
    block_node_ids_text = ""
    if block_node_ids_list:
        block_node_ids_text = "\n\n**使用到的Block节点ID列表**:\n\n" + "\n".join([f"- Block Node ID: {bid}" for bid in block_node_ids_list])

    logger.info(f"✅ [节点5] 任务2表格说明生成完成，使用了 {len(file_ids_list)} 个文件节点，{len(block_node_ids_list)} 个Block节点\n")
    return {"task2_text": text_description + file_ids_text + block_node_ids_text}


def generate_task3_node(state: CallChainState) -> CallChainState:
    """节点6: 生成任务3图表（方法控制流图）"""
    logger.info("=" * 60)
    logger.info("🔀 [节点6] 生成任务3：方法控制流图...")
    logger.info("=" * 60)
    
    llm = state["llm"]
    methods_data = state["methods_data"]
    call_relations = state["call_relations"]
    
    import os
    import asyncio
    
    # 根据调用关系构建方法对
    method_pairs = []
    for relation in call_relations:
        method1_key = f"{relation['from_class']}.{relation['from_method']}"
        method2_key = f"{relation['to_class']}.{relation['to_method']}"
        
        method1 = methods_data.get(method1_key)
        method2 = methods_data.get(method2_key)
        
        if method1 and method2:
            method_pairs.append((method1, method2))
    
    if not method_pairs:
        logger.info("  无方法对，跳过任务3")
        return {"task3_diagrams": []}
    
    # 从环境变量读取并发度，默认 5
    try:
        concurrency = int(os.getenv("LLM_CONCURRENCY", "5"))
    except ValueError:
        concurrency = 5
    
    logger.info(f"  任务3并发度: {concurrency}，方法对数量: {len(method_pairs)}")
    
    variables_list = []
    name_pairs = []
    for method1, method2 in method_pairs:
        method1_name = f"{method1.get('class_name')}.{method1.get('name')}"
        method2_name = f"{method2.get('class_name')}.{method2.get('name')}"
        name_pairs.append((method1_name, method2_name))
        logger.info(f"  生成: {method1_name} -> {method2_name}")
        
        method1_source = method1.get("source_code", "")
        method1_semantic = method1.get("semantic_explanation", {})
        method1_what = ""
        method1_how = ""
        if method1_semantic and isinstance(method1_semantic, dict):
            method1_what = method1_semantic.get("What", "")
            method1_how = method1_semantic.get("How", "")
        method2_semantic = method2.get("semantic_explanation", {})
        method2_what = ""
        if method2_semantic and isinstance(method2_semantic, dict):
            method2_what = method2_semantic.get("What", "")
        
        variables_list.append({
            "method1_name": method1_name,
            "method1_what": method1_what or "待补充",
            "method1_how": method1_how or "待补充",
            "method1_source": method1_source or "// 源代码不可用",
            "method2_name": method2_name,
            "method2_what": method2_what or "待补充"
        })
    
    # 收集使用到的 file_id
    task3_file_ids = set()
    for method1, method2 in method_pairs:
        if method1.get("file_id") is not None:
            task3_file_ids.add(method1["file_id"])
        if method2.get("file_id") is not None:
            task3_file_ids.add(method2["file_id"])

    # 并发调用 LLM（自动验证和修复）
    async def _run_batch():
        return await llm.abatch_with_template(
            template=TASK3_CONTROL_FLOW_TEMPLATE,
            variables_list=variables_list,
            system_message=SYSTEM_MESSAGE,
            concurrency=concurrency,
            expected_diagram_type="flowchart TD"
        )
    contents = asyncio.run(_run_batch())

    control_flow_diagrams = []
    for (m1, m2), mermaid_code in zip(name_pairs, contents):
        control_flow_diagrams.append({
            "method1_name": m1,
            "method2_name": m2,
            "mermaid_code": mermaid_code
        })

    # 添加 file_id 列表（作为整个任务3的汇总）
    file_ids_list = sorted(list(task3_file_ids))
    file_ids_summary = "\n\n**任务3使用到的文件节点ID列表**:\n" + "\n".join([f"- File ID: {fid}" for fid in file_ids_list])

    logger.info(f"✅ [节点6] 任务3图表生成完成，共 {len(control_flow_diagrams)} 个控制流图，使用了 {len(file_ids_list)} 个文件节点\n")
    return {
        "task3_diagrams": control_flow_diagrams,
        "task3_file_ids_summary": file_ids_summary
    }


def assemble_document_node(state: CallChainState) -> CallChainState:
    """节点7: 组装最终文档"""
    logger.info("=" * 60)
    logger.info("📝 [节点7] 组装 Markdown 文档...")
    logger.info("=" * 60)
    
    md_parts = []
    
    # 文档标题
    md_parts.append("# Java项目调用链分析文档\n\n")
    md_parts.append("本文档包含三个部分：\n")
    md_parts.append("1. 类调用链时序图\n")
    md_parts.append("2. 模块关系图\n")
    md_parts.append("3. 方法控制流图\n\n")
    md_parts.append("---\n\n")
    
    # 任务1：类调用链时序图
    md_parts.append("## 任务1：类调用链时序图\n\n")
    md_parts.append("展示目标类之间的调用关系和调用顺序。\n\n")
    md_parts.append("```mermaid\n")
    md_parts.append(state["task1_diagram"])
    md_parts.append("\n```\n\n")
    
    # 添加文件ID列表
    if state.get("task1_file_ids"):
        md_parts.append(state["task1_file_ids"])
        md_parts.append("\n\n")

    # 添加Block节点ID列表
    if state.get("task1_block_node_ids"):
        md_parts.append(state["task1_block_node_ids"])
        md_parts.append("\n\n")

    # 添加类的详细信息
    md_parts.append("### 类详细信息\n\n")
    classes_data = state["classes_data"]
    for class_name in classes_data.keys():
        class_info = classes_data[class_name]
        md_parts.append(f"#### {class_name}\n\n")
        
        semantic = class_info.get("semantic_explanation")
        if semantic and isinstance(semantic, dict):
            what = semantic.get("What", "")
            if what:
                md_parts.append(f"**功能说明**: {what}\n\n")
    
    md_parts.append("---\n\n")
    
    # 任务2：模块关系图
    md_parts.append("## 任务2：模块关系图\n\n")
    md_parts.append("展示类所属的Package、File、Block层级关系，以及类之间的调用关系。\n\n")
    md_parts.append("```mermaid\n")
    md_parts.append(state["task2_diagram"])
    md_parts.append("\n```\n\n")
    
    # 添加文件ID列表
    if state.get("task2_file_ids"):
        md_parts.append(state["task2_file_ids"])
        md_parts.append("\n\n")

    # 添加Block节点ID列表
    if state.get("task2_block_node_ids"):
        md_parts.append(state["task2_block_node_ids"])
        md_parts.append("\n\n")

    # 添加文字说明
    md_parts.append(state["task2_text"])
    
    md_parts.append("---\n\n")
    
    # 任务3：方法控制流图
    md_parts.append("## 任务3：方法控制流图\n\n")
    md_parts.append("展示方法之间的调用关系，以及method1在什么条件下会调用method2。\n\n")
    
    methods_data = state["methods_data"]
    for i, diagram_info in enumerate(state["task3_diagrams"], 1):
        method1_name = diagram_info["method1_name"]
        method2_name = diagram_info["method2_name"]
        mermaid_code = diagram_info["mermaid_code"]
        
        md_parts.append(f"### {i}. {method1_name} -> {method2_name}\n\n")
        
        method1_data = methods_data.get(method1_name)
        method2_data = methods_data.get(method2_name)
        
        if method1_data:
            md_parts.append(f"#### {method1_name}\n\n")
            semantic1 = method1_data.get("semantic_explanation", {})
            if semantic1 and isinstance(semantic1, dict):
                what1 = semantic1.get("What", "")
                if what1:
                    md_parts.append(f"**功能说明**: {what1}\n\n")
        
        if method2_data:
            md_parts.append(f"#### {method2_name}\n\n")
            semantic2 = method2_data.get("semantic_explanation", {})
            if semantic2 and isinstance(semantic2, dict):
                what2 = semantic2.get("What", "")
                if what2:
                    md_parts.append(f"**功能说明**: {what2}\n\n")
        
        md_parts.append("**控制流图**:\n\n")
        md_parts.append("```mermaid\n")
        md_parts.append(mermaid_code)
        md_parts.append("\n```\n\n")

    # 添加任务3的 file_id 汇总
    if state.get("task3_file_ids_summary"):
        md_parts.append(state["task3_file_ids_summary"])
        md_parts.append("\n\n")

    markdown_content = "".join(md_parts)
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "classes_count": len(state["classes_data"]),
        "methods_count": len(state["methods_data"]),
        "call_relations_count": len(state["call_relations"]),
        "module_relations_count": len(state["module_relations"]),
    }
    
    logger.info("✅ [节点7] 文档组装完成\n")
    return {
        "markdown_content": markdown_content,
        "metadata": metadata
    }


def save_output_node(state: CallChainState) -> CallChainState:
    """节点8: 保存输出文档"""
    logger.info("=" * 60)
    logger.info("💾 [节点8] 保存文档到文件...")
    logger.info("=" * 60)
    
    output_file = state.get("output_file", "output.md")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(state["markdown_content"])
    
    logger.info(f"✅ [节点8] 文档已保存: {output_file}")
    
    # 关闭 Neo4j 连接
    if state.get("neo4j"):
        state["neo4j"].close()
        logger.info("已关闭 Neo4j 连接")
    
    return {}


# ========== 工作流构建 ==========

class CallChainGraph:
    """调用链分析工作流：协调数据提取、LLM生成、文档组装"""
    
    def __init__(self):
        """初始化工作流"""
        self.graph = self._build_graph()
        logger.info("🔧 调用链分析工作流初始化完成")
    
    def _build_graph(self) -> StateGraph:
        """
        构建 LangGraph 工作流
        
        工作流节点：
        1. init_connections: 初始化 Neo4j 和 LLM 连接
        2. extract_data: 从 Neo4j 提取数据
        3. generate_task1: 生成类调用链时序图
        4. generate_task2: 生成模块关系图
        5. generate_task2_text: 生成模块关系表格说明（Block > Package）
        6. generate_task3: 生成方法控制流图
        7. assemble_document: 组装 Markdown 文档
        8. save_output: 保存文档到文件
        """
        workflow = StateGraph(CallChainState)
        
        # 添加节点
        workflow.add_node("init_connections", init_connections_node)
        workflow.add_node("extract_data", extract_data_node)
        workflow.add_node("generate_task1", generate_task1_node)
        workflow.add_node("generate_task2", generate_task2_node)
        workflow.add_node("generate_task3", generate_task3_node)
        workflow.add_node("generate_task2_text", generate_task2_text_node)
        workflow.add_node("assemble_document", assemble_document_node)
        workflow.add_node("save_output", save_output_node)
        
        # 定义流程
        workflow.set_entry_point("init_connections")
        workflow.add_edge("init_connections", "extract_data")
        workflow.add_edge("extract_data", "generate_task1")
        workflow.add_edge("generate_task1", "generate_task2")
        workflow.add_edge("generate_task2", "generate_task2_text")
        workflow.add_edge("generate_task2_text", "generate_task3")
        workflow.add_edge("generate_task3", "assemble_document")
        workflow.add_edge("assemble_document", "save_output")
        workflow.add_edge("save_output", END)
        
        return workflow.compile()
    
    def run(self, output_file: str = "output.md") -> Dict[str, Any]:
        """
        运行工作流
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            包含最终文档的状态字典
        """
        logger.info("🚀 开始执行调用链分析工作流")
        logger.info("=" * 60)
        
        # 初始化状态
        initial_state: CallChainState = {
            "output_file": output_file,
            "neo4j": None,
            "llm": None,
            "classes_data": {},
            "methods_data": {},
            "call_relations": [],
            "module_relations": [],
            "task1_diagram": "",
            "task1_file_ids": "",
            "task1_block_node_ids": "",
            "task2_diagram": "",
            "task2_file_ids": "",
            "task2_block_node_ids": "",
            "task2_text": "",
            "task3_diagrams": [],
            "task3_file_ids_summary": "",
            "markdown_content": "",
            "metadata": {}
        }
        
        # 执行工作流
        result = self.graph.invoke(initial_state)
        
        logger.info("=" * 60)
        logger.info("✅ 工作流执行完成")
        logger.info(f"📄 文档已保存: {output_file}")
        logger.info("=" * 60)
        
        return result


# ========== 主函数（可直接运行）==========

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 运行工作流
    graph = CallChainGraph()
    graph.run()
