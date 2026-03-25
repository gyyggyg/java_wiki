"""
可选章节生成工作流

扫描已生成的Block Wiki，通过Claude Agent搜索源码，
为符合条件的Block追加可选章节（如状态机、消息队列等）。

与已有workflow不同，本工作流不固定从neo4j读取信息，
而是通过Claude Agent自主搜索源码来发现相关信息并生成内容。
"""

import os
import sys
import json
import re
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 项目根目录（java_wiki）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ====================== 日志配置 ======================
_log_dir = os.path.join(PROJECT_ROOT, "internal_result")
os.makedirs(_log_dir, exist_ok=True)
_log_path = os.path.join(_log_dir, f"optional_sections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logger = logging.getLogger("optional_sections")
logger.setLevel(logging.DEBUG)
# 文件handler：记录所有级别（含LLM返回原文）
_fh = logging.FileHandler(_log_path, encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
_fh.flush = _fh.stream.flush
logger.addHandler(_fh)
# 控制台handler：只记录INFO及以上
_ch = logging.StreamHandler()
_ch.setLevel(logging.INFO)
_ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logger.addHandler(_ch)
logger.propagate = False
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
from interfaces.neo4j_interface import Neo4jInterface
from interfaces.llm_interface import LLMInterface
from chains.common_chains import ChainFactory
from chains.prompts.optional_section_prompt import BATCH_RELEVANCE_PROMPT
from graph.optional_section_agent import run_section_agent

# ====================== 1. 可选章节注册表 ======================

OPTIONAL_SECTIONS = [
    {
        "key": "state_machine",
        "title": "状态机分析",
        "description": "分析模块中的状态机模式，包括状态枚举定义、状态转换逻辑、状态流转图等。"
                       "适用于包含订单状态、审核流程、工单流转等业务状态管理的模块。",
        "search_hints": [
            "Status", "State", "stateMachine", "orderStatus",
            "enum.*Status", "transition", "updateStatus", "changeStatus",
        ],
        "agent_instruction": """在源码中搜索状态机相关的实现，包括：
1. 状态枚举定义（如OrderStatus, PaymentStatus, AuditStatus等）
2. 状态转换方法（改变状态的方法，如updateStatus, changeOrderStatus等）
3. 状态判断逻辑（根据状态做不同处理的switch/if-else）
4. 状态流转的业务规则

请生成：
- 文字描述：列出发现的状态枚举、状态转换方法及其业务含义
- mermaid状态图（stateDiagram-v2）：展示状态之间的流转关系

mermaid状态图示例格式：
stateDiagram-v2
    [*] --> Created
    Created --> Paid : 支付成功
    Paid --> Shipped : 发货
    Shipped --> Completed : 确认收货
    Created --> Cancelled : 取消订单
"""
    },
    {
        "key": "message_queue",
        "title": "消息队列分析",
        "description": "分析模块中的消息队列使用，包括消息生产者、消费者、队列/Topic定义和消息体结构。"
                       "适用于使用RabbitMQ、Kafka、RocketMQ等消息中间件的模块。",
        "search_hints": [
            "@RabbitListener", "@RabbitHandler", "RabbitTemplate",
            "@KafkaListener", "KafkaTemplate",
            "RocketMQ", "@RocketMQMessageListener",
            "JmsTemplate", "@JmsListener",
            "MessageQueue", "MQProducer", "MQConsumer",
            "amqp", "exchange", "routingKey", "binding",
        ],
        "agent_instruction": """在源码中搜索消息队列相关的实现，包括：
1. 消息生产者（Producer/Sender）：发送消息的类和方法
2. 消息消费者（Consumer/Listener）：监听和处理消息的类和方法
3. 队列/Topic/Exchange定义和配置
4. 消息体结构（Message DTO）
5. 消息队列相关的配置文件

请生成：
- 文字描述：列出所有消息队列相关的组件及其职责
- mermaid流程图（graph LR）：展示消息的生产-传递-消费关系

mermaid流程图示例格式：
graph LR
    A[OrderService] -->|发送订单消息| B[order.exchange]
    B -->|routing.key.order| C[order.queue]
    C -->|消费| D[OrderConsumer]
"""
    },
    # ==================== 可扩展：在此添加更多可选章节 ====================
    # {
    #     "key": "cache_strategy",
    #     "title": "缓存策略分析",
    #     "description": "...",
    #     "search_hints": ["@Cacheable", "RedisTemplate", "Cache", ...],
    #     "agent_instruction": "..."
    # },
    # {
    #     "key": "scheduled_tasks",
    #     "title": "定时任务分析",
    #     "description": "...",
    #     "search_hints": ["@Scheduled", "CronTrigger", "ScheduledExecutorService", ...],
    #     "agent_instruction": "..."
    # },
]


# ====================== 2. 状态定义 ======================

class OptionalSectionState(TypedDict, total=False):
    # 输入参数
    target_block: Optional[str]        # 指定block名（None表示全部）
    target_section: Optional[str]      # 指定章节key（None表示全部）

    # 扫描结果
    block_wiki_map: Dict[str, str]     # {block_name: wiki_json_path}
    scan_results: Dict[str, List[str]] # {block_name: [适用的section_key列表]}

    # 生成结果
    generated_results: List[Dict]      # [{block_name, section_key, content, ...}]

    # 最终输出
    final_output: Dict


# ====================== 3. 辅助函数 ======================

def find_wiki_files(wiki_path: str) -> Dict[str, str]:
    """递归扫描WIKI_PATH下所有block wiki JSON文件，返回 {block_name: json_path}"""
    result = {}
    if not os.path.isdir(wiki_path):
        logger.warning(f" WIKI_PATH 不存在: {wiki_path}")
        return result

    for root, dirs, files in os.walk(wiki_path):
        for f in files:
            if f.endswith(".json") and f != "root_doc.json":
                block_name = f[:-5]
                result[block_name] = os.path.join(root, f)
    return result


def get_max_section_number(wiki_data: dict) -> int:
    """从wiki JSON中提取最大章节序号"""
    max_num = 0
    for entry in wiki_data.get("wiki", []):
        text = entry.get("markdown", entry.get("mermaid", ""))
        # 匹配 ## N. 或 ### N.M 格式
        matches = re.findall(r'#{2,3}\s+(\d+)', text)
        for m in matches:
            num = int(m)
            if num > max_num:
                max_num = num
    return max_num


def group_wiki_by_branch(wiki_path: str) -> Dict[str, Dict[str, str]]:
    """
    按root分支聚合所有wiki文件。
    每个root分支 = 根目录下的一个json文件 + 其同名文件夹下递归的所有json文件。

    返回 {branch_name: {block_name: json_path}}
    例如 {"Admin System Core Suite": {"Admin System Core Suite": "xxx.json", "子block": "xxx.json", ...}}
    """
    result = {}
    if not os.path.isdir(wiki_path):
        return result

    # 找出根目录下的json文件（即root分支）
    for entry in os.listdir(wiki_path):
        if not entry.endswith(".json") or entry == "root_doc.json":
            continue

        branch_name = entry[:-5]
        branch_blocks = {branch_name: os.path.join(wiki_path, entry)}

        # 找同名文件夹，递归收集所有子json
        branch_dir = os.path.join(wiki_path, branch_name)
        if os.path.isdir(branch_dir):
            for root, dirs, files in os.walk(branch_dir):
                for f in files:
                    if f.endswith(".json"):
                        block_name = f[:-5]
                        branch_blocks[block_name] = os.path.join(root, f)

        result[branch_name] = branch_blocks

    return result


def read_block_summary(wiki_json_path: str, max_chars: int = 800) -> str:
    """
    读取wiki JSON文件的前两个章节内容（第1章模块功能概述 + 第2章核心组件介绍），
    拼接返回用于LLM相关性判断，截取前max_chars字符。
    """
    try:
        with open(wiki_json_path, 'r', encoding='utf-8') as f:
            wiki_data = json.load(f)
        sections = wiki_data.get("wiki", [])
        parts = []
        for s in sections[:2]:
            md = s.get("markdown", "")
            if md:
                parts.append(md)
        full = "\n".join(parts)
        return full[:max_chars]
    except Exception:
        pass
    return ""


def build_branch_tree(wiki_path: str, branch_name: str, branch_blocks: Dict[str, str],
                      summary_max_chars: int) -> str:
    """
    为一个root分支构建树形文本，展示层级关系和每个block的摘要。
    利用wiki文件的目录层级来推断树形结构。

    返回格式：
    [Admin System Core Suite]
      摘要...
      ├── [Admin System Application Layer]
      │     摘要...
      │     ├── [Admin System Business Controllers]
      │     │     摘要...
    """
    # 按json文件路径排序并建立层级
    branch_dir = os.path.join(wiki_path, branch_name)
    root_json = os.path.join(wiki_path, f"{branch_name}.json")

    lines = []

    def _add_block(block_name: str, json_path: str, depth: int):
        indent = "  " * depth
        summary = read_block_summary(json_path, summary_max_chars)
        summary_oneline = summary.replace("\n", " ").strip()
        lines.append(f"{indent}[{block_name}]")
        if summary_oneline:
            lines.append(f"{indent}  {summary_oneline}")

    def _walk_dir(dir_path: str, depth: int):
        """递归处理目录：先找该目录对应的json，再处理子目录"""
        if not os.path.isdir(dir_path):
            return

        entries = sorted(os.listdir(dir_path))
        # 先处理json文件（叶子block）
        json_files = [e for e in entries if e.endswith(".json")]
        sub_dirs = [e for e in entries if os.path.isdir(os.path.join(dir_path, e))]

        for jf in json_files:
            block_name = jf[:-5]
            json_path = os.path.join(dir_path, jf)
            # 如果有同名子目录，说明这是一个中间层block，先输出它再递归子目录
            has_sub = block_name in sub_dirs
            _add_block(block_name, json_path, depth)
            if has_sub:
                _walk_dir(os.path.join(dir_path, block_name), depth + 1)
                sub_dirs.remove(block_name)

        # 处理剩余没有对应json的子目录（理论上不应该有）
        for sd in sub_dirs:
            _walk_dir(os.path.join(dir_path, sd), depth + 1)

    # 根block
    if os.path.isfile(root_json):
        _add_block(branch_name, root_json, 0)

    # 递归子目录
    _walk_dir(branch_dir, 1)

    return "\n".join(lines)


async def resolve_file_node_ids(neo4j_interface: Neo4jInterface, file_paths: List[str]) -> Dict[str, int]:
    """将文件相对路径映射到neo4j File节点的nodeId"""
    if not file_paths:
        return {}

    # File节点的name字段存储的是文件路径，尝试匹配
    query = """
    MATCH (f:File)
    WHERE ANY(path IN $file_paths WHERE f.name CONTAINS path)
    RETURN f.name AS name, f.nodeId AS nodeId
    """
    try:
        results = await neo4j_interface.execute_query(query, {"file_paths": file_paths})
        mapping = {}
        for r in results:
            for fp in file_paths:
                if fp in str(r["name"]):
                    mapping[fp] = r["nodeId"]
        return mapping
    except Exception as e:
        logger.warning(f" 查询File nodeId失败: {e}")
        return {}


async def get_block_files_from_neo4j(neo4j_interface: Neo4jInterface, block_name: str) -> List[str]:
    """从neo4j获取block下所有文件路径"""
    query = """
    MATCH (b:Block)-[:f2c*]->(f:File)
    WHERE b.name = $block_name
    RETURN f.name AS file_name
    """
    try:
        results = await neo4j_interface.execute_query(query, {"block_name": block_name})
        return [r["file_name"] for r in results if r.get("file_name")]
    except Exception:
        return []


# ====================== 4. 工作流定义 ======================

def optional_sections_workflow(
    neo4j_interface: Neo4jInterface,
    llm_interface: LLMInterface,
    wiki_path: str,
    source_root: str,
    sections: Optional[List[dict]] = None,
):
    """
    构建可选章节生成的langgraph工作流。

    Args:
        neo4j_interface: Neo4j接口
        llm_interface: LLM接口（用于相关性判断）
        wiki_path: wiki输出目录路径
        source_root: 源码根目录路径
        sections: 要处理的可选章节列表，默认使用OPTIONAL_SECTIONS
    """
    active_sections = sections or OPTIONAL_SECTIONS
    relevance_chain = ChainFactory.create_generic_chain(llm_interface, BATCH_RELEVANCE_PROMPT)

    # ---------- 节点1: 扫描所有block wiki ----------
    async def scan_blocks(state: OptionalSectionState) -> OptionalSectionState:
        """
        按root分支聚合所有wiki，每个分支构建树形结构文本，
        一次LLM调用让模型看到完整层级并选择最合适的block生成可选章节。
        """
        target_block = state.get("target_block")
        target_section = state.get("target_section")

        # 1. 按root分支聚合
        branch_groups = group_wiki_by_branch(wiki_path)
        # 构建全局 block_wiki_map
        block_wiki_map = {}
        for branch_name, blocks in branch_groups.items():
            block_wiki_map.update(blocks)

        total_blocks = len(block_wiki_map)
        logger.info(f"找到 {total_blocks} 个block wiki文件，{len(branch_groups)} 个分支")

        # 如果指定了目标block，找到它所在的分支
        if target_block:
            if target_block not in block_wiki_map:
                logger.warning(f" 指定的block '{target_block}' 未找到wiki文件")
                return {"block_wiki_map": {}, "scan_results": {}}
            # 找到该block所在的分支，只处理该分支
            filtered = {}
            for branch_name, blocks in branch_groups.items():
                if target_block in blocks:
                    filtered[branch_name] = blocks
                    break
            branch_groups = filtered

        # 2. 确定要处理的章节列表
        sections_to_check = active_sections
        if target_section:
            sections_to_check = [s for s in active_sections if s["key"] == target_section]
            if not sections_to_check:
                logger.warning(f" 指定的章节key '{target_section}' 未在注册表中找到")
                return {"block_wiki_map": block_wiki_map, "scan_results": {}}

        # 3. 并发判断：所有(branch, section)组合同时发起LLM调用
        scan_results = {}
        scan_lock = asyncio.Lock()

        async def scan_one(branch_name: str, branch_blocks: Dict, section: dict):
            """单个(分支, 章节类型)的LLM判断"""
            block_count = len(branch_blocks)

            # 动态调整摘要长度
            if block_count <= 15:
                summary_chars = 800
            elif block_count <= 30:
                summary_chars = 500
            else:
                summary_chars = 300

            branch_tree = build_branch_tree(
                wiki_path, branch_name, branch_blocks, summary_chars
            )

            if not branch_tree.strip():
                logger.warning(f"[SCAN] {branch_name} - {section['key']}: 分支树为空，跳过")
                return

            logger.info(f"[SCAN] {branch_name} × {section['key']} ({block_count} blocks)...")
            logger.debug(f"[SCAN] 分支树内容:\n{branch_tree[:2000]}")

            try:
                relevance_result = await relevance_chain.ainvoke({
                    "section_title": section["title"],
                    "section_description": section["description"],
                    "branch_tree": branch_tree,
                })

                result_str = str(relevance_result)
                logger.debug(f"[SCAN] {branch_name} × {section['key']} LLM原始返回:\n{result_str}")

                json_match = re.search(r'\{.*\}', result_str, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    needed_blocks = parsed.get("需要", [])
                    reason = parsed.get("不需要原因", "")
                else:
                    logger.warning(f"[SCAN] {branch_name} × {section['key']} LLM返回格式异常: {result_str[:200]}")
                    return

                if needed_blocks:
                    async with scan_lock:
                        for bname in needed_blocks:
                            matched = bname if bname in branch_blocks else None
                            if not matched:
                                short_name = bname.split(".")[-1].strip()
                                if short_name in branch_blocks:
                                    matched = short_name
                            if matched:
                                if matched not in scan_results:
                                    scan_results[matched] = []
                                scan_results[matched].append(section["key"])
                                logger.info(f"  → {matched}: 需要「{section['title']}」")
                            else:
                                logger.warning(f"  → LLM返回的 '{bname}' 不在分支中，忽略")
                else:
                    logger.info(f"[SCAN] {branch_name} × {section['key']}: 不需要 ({reason[:80]})")

            except Exception as e:
                logger.error(f"[SCAN] {branch_name} × {section['key']} 判断失败: {e}")

        # 构建所有scan任务并发执行
        scan_tasks = []
        for branch_name, branch_blocks in branch_groups.items():
            for section in sections_to_check:
                scan_tasks.append(scan_one(branch_name, branch_blocks, section))

        logger.info(f"并发发起 {len(scan_tasks)} 个扫描任务（{len(branch_groups)} 分支 × {len(sections_to_check)} 章节类型）")
        await asyncio.gather(*scan_tasks)

        logger.info(f"\n[INFO] 扫描完成: {len(scan_results)} 个block需要生成可选章节")
        for bname, skeys in scan_results.items():
            logger.info(f"  - {bname}: {skeys}")

        return {"block_wiki_map": block_wiki_map, "scan_results": scan_results}

    # ---------- 节点2: 并发生成章节 ----------
    async def generate_sections(state: OptionalSectionState) -> OptionalSectionState:
        """并发调用Claude Agent为每个(block, section)组合生成章节内容"""
        scan_results = state.get("scan_results", {})
        block_wiki_map = state.get("block_wiki_map", {})

        if not scan_results:
            logger.info("无需生成任何可选章节")
            return {"generated_results": []}

        # 构建所有任务
        tasks_info = []
        for block_name, section_keys in scan_results.items():
            wiki_json_path = block_wiki_map[block_name]

            # 读取已有wiki获取当前最大章节号
            try:
                with open(wiki_json_path, 'r', encoding='utf-8') as f:
                    wiki_data = json.load(f)
                max_section_num = get_max_section_number(wiki_data)
            except Exception:
                max_section_num = 6  # 默认从第7章开始

            # 获取block描述
            block_desc = ""
            if wiki_data.get("wiki"):
                block_desc = wiki_data["wiki"][0].get("markdown", "")[:500]

            # 获取block文件列表
            file_list = await get_block_files_from_neo4j(neo4j_interface, block_name)

            for section_key in section_keys:
                section_def = next((s for s in active_sections if s["key"] == section_key), None)
                if not section_def:
                    continue

                # section_number 不在这里预分配，而是在merge阶段根据实际成功的结果动态编号
                tasks_info.append({
                    "block_name": block_name,
                    "block_desc": block_desc,
                    "file_list": file_list,
                    "section_def": section_def,
                    "max_section_num": max_section_num,
                    "wiki_json_path": wiki_json_path,
                })

        logger.info(f"共 {len(tasks_info)} 个章节生成任务")

        max_concurrent = int(os.environ.get("MAX_CONCURRENT_BLOCKS", "5"))
        semaphore = asyncio.Semaphore(max_concurrent)
        generated_results = []

        async def generate_single(task: dict, index: int):
            async with semaphore:
                block_name = task["block_name"]
                section_def = task["section_def"]
                section_key = section_def["key"]
                # 给agent一个临时序号用于生成标题，merge阶段会替换为正确的连续序号
                temp_section_number = task["max_section_num"] + 1

                logger.info(f"  [{index}/{len(tasks_info)}] 生成: {block_name} - {section_def['title']}")

                try:
                    result = await run_section_agent(
                        block_name=block_name,
                        block_description=task["block_desc"],
                        file_list=task["file_list"],
                        section_title=section_def["title"],
                        section_description=section_def["description"],
                        agent_instruction=section_def["agent_instruction"],
                        search_hints=section_def["search_hints"],
                        section_number=temp_section_number,
                        source_root=source_root,
                    )

                    # 记录Agent完整返回到日志
                    logger.debug(f"[AGENT] {block_name} - {section_def['title']} 返回:\n"
                                 f"  has_content={result.get('has_content')}\n"
                                 f"  markdown长度={len(result.get('markdown', ''))}\n"
                                 f"  mermaid={'有' if result.get('mermaid') else '无'}\n"
                                 f"  referenced_files={result.get('referenced_files', [])}\n"
                                 f"  markdown预览={result.get('markdown', '')[:300]}")

                    if not result.get("has_content"):
                        logger.info(f"  [{index}/{len(tasks_info)}] {block_name} - {section_def['title']}: 无相关内容，跳过")
                        return None

                    logger.info(f"  [{index}/{len(tasks_info)}] 完成: {block_name} - {section_def['title']}")

                    return {
                        "block_name": block_name,
                        "section_key": section_key,
                        "max_section_num": task["max_section_num"],
                        "wiki_json_path": task["wiki_json_path"],
                        "content": result,
                    }
                except Exception as e:
                    logger.error(f"  [{index}/{len(tasks_info)}] 失败: {block_name} - {section_def['title']} - {e}")
                    return None

        # 并发执行
        tasks = [generate_single(t, i + 1) for i, t in enumerate(tasks_info)]
        results = await asyncio.gather(*tasks)
        generated_results = [r for r in results if r is not None]

        logger.info(f"章节生成完成: 成功 {len(generated_results)}/{len(tasks_info)}")

        return {"generated_results": generated_results}

    # ---------- 节点3: 合并到wiki ----------
    async def merge_to_wiki(state: OptionalSectionState) -> OptionalSectionState:
        """将生成的可选章节追加到原有wiki JSON中"""
        generated_results = state.get("generated_results", [])

        if not generated_results:
            logger.info("无需合并任何章节")
            return {"final_output": {"merged_count": 0}}

        # 按wiki文件分组（同一个block的多个章节追加到同一个wiki）
        by_wiki = {}
        for r in generated_results:
            wiki_path_key = r["wiki_json_path"]
            if wiki_path_key not in by_wiki:
                by_wiki[wiki_path_key] = []
            by_wiki[wiki_path_key].append(r)

        merged_count = 0

        for wiki_json_path, sections in by_wiki.items():
            block_name = sections[0]["block_name"]
            logger.info(f"\n[MERGE] {block_name}: 追加 {len(sections)} 个章节")

            # 读取原wiki
            try:
                with open(wiki_json_path, 'r', encoding='utf-8') as f:
                    wiki_data = json.load(f)
            except Exception as e:
                logger.error(f"   读取wiki失败: {e}")
                continue

            # 获取当前wiki的最大章节号，从这里开始连续编号
            current_max = get_max_section_number(wiki_data)

            for section_info in sections:
                content = section_info["content"]
                section_key = section_info["section_key"]
                temp_num = section_info["max_section_num"] + 1  # agent生成时用的临时序号

                # 动态分配连续序号
                current_max += 1
                actual_num = current_max

                # 查找referenced_files对应的neo4j nodeId
                file_node_ids = await resolve_file_node_ids(
                    neo4j_interface,
                    content.get("referenced_files", [])
                )

                node_id_list = list(file_node_ids.values()) if file_node_ids else []

                # 替换markdown中的临时序号为实际序号
                markdown_text = content.get("markdown", "")
                if temp_num != actual_num:
                    # 替换 ## N. → ## M. 和 ### N.x → ### M.x
                    markdown_text = re.sub(
                        rf'(#{{{2,3}}}\s+){temp_num}(\.|(?=\s))',
                        rf'\g<1>{actual_num}\2',
                        markdown_text
                    )

                # 从markdown中提取所有小标题，构建neo4j_id映射
                sub_titles = re.findall(r'#{2,3}\s+([\d.]+)', markdown_text)
                if sub_titles:
                    neo4j_id_map = {t: node_id_list for t in sub_titles}
                else:
                    neo4j_id_map = {str(actual_num): node_id_list}

                # 追加markdown章节
                markdown_entry = {
                    "markdown": markdown_text,
                    "neo4j_id": neo4j_id_map
                }
                wiki_data["wiki"].append(markdown_entry)

                # 如果有mermaid图，追加为独立章节
                if content.get("mermaid"):
                    mermaid_text = content["mermaid"]
                    # 替换mermaid中可能出现的临时序号
                    if temp_num != actual_num:
                        mermaid_text = mermaid_text.replace(f"{temp_num}.", f"{actual_num}.")

                    mermaid_sub = f"{actual_num}.1"
                    if mermaid_sub in sub_titles:
                        mermaid_sub = f"{actual_num}.{len(sub_titles) + 1}"
                    mermaid_title = f"### {mermaid_sub} 架构图"
                    mermaid_entry = {
                        "mermaid": f"{mermaid_title}\n\n```mermaid\n{mermaid_text}\n```",
                        "neo4j_id": {mermaid_sub: node_id_list}
                    }
                    wiki_data["wiki"].append(mermaid_entry)

                merged_count += 1
                logger.info(f"  [OK] 追加章节 {actual_num}: {section_key}")

            # 写回文件
            try:
                write_path = wiki_json_path
                if sys.platform == "win32" and not write_path.startswith("\\\\?\\"):
                    write_path = "\\\\?\\" + os.path.abspath(write_path)

                with open(write_path, 'w', encoding='utf-8') as f:
                    json.dump(wiki_data, f, ensure_ascii=False, indent=2)
                logger.info(f"  [OK] 已写回: {wiki_json_path}")
            except Exception as e:
                logger.error(f"   写回wiki失败: {e}")

        final_output = {
            "merged_count": merged_count,
            "blocks_updated": list(by_wiki.keys()),
            "details": [
                {
                    "block": r["block_name"],
                    "section": r["section_key"],
                    "files_referenced": len(r["content"].get("referenced_files", [])),
                }
                for r in generated_results
            ]
        }

        logger.info(f"\n[INFO] 合并完成: 共追加 {merged_count} 个章节到 {len(by_wiki)} 个wiki文件")
        return {"final_output": final_output}

    # ---------- 构建状态图 ----------
    graph = StateGraph(OptionalSectionState)
    graph.add_node("scan", scan_blocks)
    graph.add_node("generate", generate_sections)
    graph.add_node("merge", merge_to_wiki)

    graph.set_entry_point("scan")
    graph.add_edge("scan", "generate")
    graph.add_edge("generate", "merge")
    graph.add_edge("merge", END)

    app = graph.compile(checkpointer=MemorySaver())
    return app


# ====================== 5. 独立运行入口 ======================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description="可选章节生成工作流")
    parser.add_argument("--block", type=str, default=None,
                        help="指定block名称（不指定则处理所有block）")
    parser.add_argument("--section", type=str, default=None,
                        help="指定章节key（如 state_machine, message_queue）")
    parser.add_argument("--list-sections", action="store_true",
                        help="列出所有可用的可选章节")
    args = parser.parse_args()

    if args.list_sections:
        logger.info("可用的可选章节：")
        for s in OPTIONAL_SECTIONS:
            logger.info(f"  - {s['key']}: {s['title']}")
            logger.info(f"    {s['description'][:80]}...")
        return

    load_dotenv()

    wiki_path = os.environ.get("WIKI_PATH", "")
    source_root = os.environ.get("SOURCE_ROOT_PATH", "")

    if not wiki_path:
        logger.info("[ERROR] 未配置 WIKI_PATH 环境变量")
        return
    if not source_root:
        logger.info("[ERROR] 未配置 SOURCE_ROOT_PATH 环境变量")
        return

    print("=== 可选章节生成工作流 ===")
    print(f"  WIKI_PATH: {wiki_path}")
    print(f"  SOURCE_ROOT_PATH: {source_root}")
    print(f"  日志文件: {_log_path}")
    if args.block:
        print(f"  目标Block: {args.block}")
    if args.section:
        print(f"  目标章节: {args.section}")
    print()

    neo4j = Neo4jInterface(
        uri=os.environ["WIKI_NEO4J_URI"],
        user=os.environ["WIKI_NEO4J_USER"],
        password=os.environ["WIKI_NEO4J_PASSWORD"],
    )

    if not await neo4j.test_connection():
        logger.info("[ERROR] Neo4j 连接失败")
        return

    print("[INFO] Neo4j 连接成功")

    llm = LLMInterface(model_name="gpt-4.1-mini", provider="openai")

    app = optional_sections_workflow(
        neo4j_interface=neo4j,
        llm_interface=llm,
        wiki_path=wiki_path,
        source_root=source_root,
    )

    result = await app.ainvoke(
        {
            "target_block": args.block,
            "target_section": args.section,
        },
        config={"configurable": {"thread_id": "optional-sections"}}
    )

    print("\n=== 执行结果 ===")
    print(json.dumps(result.get("final_output", {}), ensure_ascii=False, indent=2))

    neo4j.close()
    print("[INFO] 工作流执行完成")


if __name__ == "__main__":
    asyncio.run(main())
