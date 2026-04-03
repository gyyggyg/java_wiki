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
import uuid
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
from chains.prompts.optional_section_prompt import (
    BATCH_RELEVANCE_PROMPT,
    STATE_MACHINE_RELEVANCE_PROMPT,
    MESSAGE_QUEUE_RELEVANCE_PROMPT,
    MERMAID_FIX_PROMPT,
)
from graph.optional_section_agent import run_section_agent
from interfaces.simple_validate_mermaid import SimpleMermaidValidator

_mermaid_validator = SimpleMermaidValidator()

# ====================== 1. 可选章节注册表 ======================

OPTIONAL_SECTIONS = [
    {
        "key": "state_machine",
        "title": "状态机分析",
        "description": "分析模块中的状态机模式，包括状态/阶段枚举定义、状态转换逻辑、状态流转规则等。"
                       "适用于任何包含有限状态集合及其转换关系的模块，例如：业务流程阶段管理、实体生命周期控制、"
                       "审批/审核流程、任务调度状态、连接/会话状态管理等。",
        "search_hints": [
            "Status", "State", "Phase", "Stage",
            "enum.*Status", "enum.*State", "enum.*Phase",
            "stateMachine", "transition", "lifecycle",
            "updateStatus", "changeStatus", "setState",
        ],
        "agent_instruction": """在源码中搜索状态机的**行为实现**，重点关注：
1. 驱动状态变化的方法（如 updateStatus、changeState、transition，以及 UPDATE SQL 中直接修改 status 字段的方法）
2. 状态判断逻辑（switch/if-else 根据 status 值分支处理）
3. 状态流转的守卫约束（代码中对"当前状态必须为X才允许转换"的校验）
4. 状态值的来源定义（枚举类、常量、注解注释中的说明）

**分析要求：**
- 必须从源码中完整枚举所有状态值，不遗漏任何一个（以代码注释、常量定义为准）
- 区分"存储状态字段的类"（Entity/DTO，只持有字段）和"执行状态转换的类"（ServiceImpl，含修改逻辑），只分析后者
- 若该模块只有 status 字段定义而无任何转换方法，输出 {{"has_content": false, "referenced_files": []}}

**文字描述要包含：**
- 每个状态的值、名称、业务含义（表格形式）
- 每个状态转换的：触发入口方法 → 守卫条件 → 执行动作（列表形式）
- 业务约束规则（如"只有 status=0 的订单才能取消"）

**mermaid图要求：**
- 每个独立的状态字段/实体单独一张 stateDiagram-v2，多个状态机对应多张图（通过多次调用返回多个图不可行，因此若存在多套独立状态机，在 mermaid 字段中只画最核心的一张，其余在文字中描述）
- stateDiagram-v2 的转换标签使用 `: label` 格式（冒号后直接跟文字），不使用 `|label|`
- 标签中含 `()` 括号、`[]` 方括号或中文冒号时，可正常书写；但不要在标签中使用 HTML 标签（如 `<br/>`）
- 不要把动作（如"释放库存"）画成状态节点
- 示例：
stateDiagram-v2
    [*] --> 待付款 : generateOrder()
    待付款 --> 待发货 : paySuccess()[status=0]
    待付款 --> 已关闭 : cancelOrder()[status=0]
    待发货 --> 已发货 : delivery()
    已发货 --> 已完成 : confirmReceive()
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

**mermaid边标签语法规则（必须遵守）：**
- 边标签（`|...|` 内的文字）含以下任意字符时，必须用双引号包裹整个标签：
  - `@` 符号（如 `@RabbitListener`、`@KafkaListener`）
  - `<`、`>` 及任何 HTML 标签（`<br/>` 禁止出现在边标签中，只能用于节点标签 `[]` 内）
  - `:`、`"`、`()`、`;` 等特殊符号
- 正确写法：`F -->|"@RabbitListener"| G`、`B -->|"routingKey: order.cancel"| C`
- 错误写法：`F -->|@RabbitListener| G`（缺少引号）、`A -->|发送<br/>消息| B`（边标签含 br）

mermaid流程图示例格式：
graph LR
    A[OrderService] -->|"sendMessage(orderId)"| B[order.exchange]
    B -->|"routingKey: order.cancel"| C[order.cancel.ttl队列]
    C -->|"TTL过期 → 死信转发"| D[order.cancel队列]
    D -->|"@RabbitListener"| E[OrderConsumer]
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
    scan_results: Dict[str, List[Dict]] # {block_name: [{"key": section_key, "hints": [动态搜索线索]}]}

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
            if f.endswith(".meta.json") and f != "root_doc.meta.json":
                block_name = f[:-10]
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
    每个root分支 = 根目录下的一个json文件（可选）+ 其同名文件夹下递归的所有json文件。
    支持只有子目录、没有根JSON文件的分支（如 Portal Core Foundation）。

    返回 {branch_name: {block_name: json_path}}
    例如 {"Admin System Core Suite": {"Admin System Core Suite": "xxx.json", "子block": "xxx.json", ...}}
    """
    result = {}
    if not os.path.isdir(wiki_path):
        return result

    entries = os.listdir(wiki_path)
    json_files = {e[:-10] for e in entries if e.endswith(".meta.json") and e != "root_doc.meta.json"}
    sub_dirs = {e for e in entries if os.path.isdir(os.path.join(wiki_path, e)) and not e.startswith(".")}

    # 所有根JSON文件和根子目录的并集都是分支
    branch_names = json_files | sub_dirs

    for branch_name in branch_names:
        branch_blocks = {}

        # 根JSON（可能不存在）
        root_json = os.path.join(wiki_path, branch_name + ".meta.json")
        if os.path.isfile(root_json):
            branch_blocks[branch_name] = root_json

        # 同名子目录下递归收集所有json
        branch_dir = os.path.join(wiki_path, branch_name)
        if os.path.isdir(branch_dir):
            for root, dirs, files in os.walk(branch_dir):
                for f in files:
                    if f.endswith(".meta.json"):
                        block_name = f[:-10]
                        branch_blocks[block_name] = os.path.join(root, f)

        if branch_blocks:
            result[branch_name] = branch_blocks

    return result


def _load_leaf_paths() -> Dict[str, str]:
    """
    加载 internal_result/file_block_leaves.json 和 file_leaves.json，
    合并为 {nodeId: relative_output_path} 映射。
    只加载一次，缓存结果。
    """
    if hasattr(_load_leaf_paths, "_cache"):
        return _load_leaf_paths._cache

    result = {}
    for fname in ["file_block_leaves.json", "file_leaves.json"]:
        fpath = os.path.join(PROJECT_ROOT, "internal_result", fname)
        if os.path.isfile(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            result.update(data)  # {nodeId: "output\\Branch\\Sub\\LeafName"}
    _load_leaf_paths._cache = result
    return result


def _extract_leaf_summary(wiki_json_path: str) -> dict:
    """
    从叶子block的wiki JSON中提取精简摘要：
    - 第1章第一段（模块功能概述）
    - 第2章中所有组件类名列表
    返回 {"description": "...", "components": ["ClassName(Class)", ...]}
    """
    result = {"description": "", "components": []}
    try:
        with open(wiki_json_path, 'r', encoding='utf-8') as f:
            wiki_data = json.load(f)
    except Exception:
        return result

    sections = wiki_data.get("wiki", [])

    # 第1章：只取第一段（标题之后、第一个空行之前的内容）
    if len(sections) > 0:
        ch1 = sections[0].get("markdown", "")
        if ch1:
            # 去掉 ## 1. xxx 标题行，取剩余内容的第一段
            lines = ch1.split("\n")
            body_lines = []
            started = False
            for line in lines:
                if not started:
                    if line.strip() and not line.strip().startswith("##"):
                        started = True
                        body_lines.append(line.strip())
                else:
                    if not line.strip():
                        break
                    body_lines.append(line.strip())
            result["description"] = " ".join(body_lines)

    # 第2章：提取组件名及其主要职责。如果整章就是"子模块介绍"则置空，否则截取到"子模块简要介绍"之前
    if len(sections) > 1:
        ch2 = sections[1].get("markdown", "")
        if ch2 and not re.match(r'##\s+\d+\.\s*子模块介绍', ch2.strip()):
            cut = re.split(r'###\s+[\d.]+\s+子模块简要介绍', ch2)[0]
            # 按 ### 标题拆分各组件段落
            component_sections = re.split(r'(#{3,4}\s+[\d.]+\s+.+)', cut)
            skip = {"核心组件"}
            components = []
            i = 1  # component_sections[0] 是 ## 2. 标题前的内容，跳过
            while i < len(component_sections):
                header = component_sections[i]
                body = component_sections[i + 1] if i + 1 < len(component_sections) else ""
                # 提取类名（如 "PmsProductServiceImpl(Class)"）
                name_match = re.search(r'#{3,4}\s+[\d.]+\s+(.+)', header)
                if name_match:
                    comp_name = name_match.group(1).strip()
                    if comp_name not in skip:
                        # 提取 **主要职责** 到下一个 **xxx** 之间的内容
                        duty_match = re.search(
                            r'\*\*主要职责\*\*[：:\s]*\n?(.*?)(?=\n\s*-\s*\*\*|\Z)',
                            body, re.DOTALL
                        )
                        if duty_match:
                            duty_text = duty_match.group(1).strip()
                            # 清理 markdown 列表前缀和多余空白
                            duty_text = re.sub(r'^\s*-\s*', '', duty_text)
                            duty_text = re.sub(r'\s+', ' ', duty_text).strip()
                            # 截断过长的职责描述，保留前150字
                            if len(duty_text) > 150:
                                duty_text = duty_text[:150] + "…"
                            components.append(f"{comp_name}: {duty_text}")
                        else:
                            components.append(comp_name)
                i += 2
            result["components"] = components

    # 补充扫描：从第3章及之后的所有章节中提取关键技术组件名（用于可选章节检测）
    # 专门抓取MQ相关类（*Sender/*Consumer/*Listener/*Producer/*Receiver）和MQ注解，
    # 解决可选章节写入后的内容对下一次扫描不可见的问题
    # TODO: 暂时注释，待 Order Auto Cancellation Engine 等缺失模块文档补全后再评估是否需要启用
    # if len(sections) > 2:
    #     all_extra_text = " ".join(
    #         entry.get("markdown", "") or entry.get("mermaid", "")
    #         for entry in sections[2:]
    #     )
    #     extra_classes = re.findall(
    #         r'\b([A-Z][a-zA-Z]{3,}(?:Sender|Consumer|Listener|Producer|Receiver))\b',
    #         all_extra_text
    #     )
    #     extra_annotations = re.findall(
    #         r'(@(?:RabbitListener|RabbitHandler|KafkaListener|RocketMQMessageListener|JmsListener))',
    #         all_extra_text
    #     )
    #     extras = list(dict.fromkeys(extra_classes + extra_annotations))  # 去重并保留顺序
    #     if extras:
    #         result["components"].extend(extras)

    return result


def build_branch_tree(wiki_path: str, branch_name: str, branch_blocks: Dict[str, str],
                      summary_max_chars: int) -> str:
    """
    为一个root分支构建JSON格式的树形结构。
    - 非叶子节点：只有 name 和 children
    - 叶子节点：有 name, description（第1章第一段）, components（类名列表）

    通过 file_block_leaves.json 和 file_leaves.json 判断哪些是叶子block。
    返回 JSON 字符串。
    """
    leaf_paths = _load_leaf_paths()

    # 构建叶子block名称集合
    prefix = f"output\\{branch_name}"
    leaf_names = set()
    for node_id, rel_path in leaf_paths.items():
        if rel_path.startswith(prefix):
            leaf_names.add(rel_path.rsplit("\\", 1)[-1])

    branch_dir = os.path.join(wiki_path, branch_name)
    root_json = os.path.join(wiki_path, f"{branch_name}.meta.json")

    def _build_node(block_name: str, json_path: str) -> dict:
        """所有有 json 的节点都提取 description 和 components，不管是否叶子"""
        node = {"name": block_name}
        if os.path.isfile(json_path):
            info = _extract_leaf_summary(json_path)
            if info.get("description"):
                node["description"] = info["description"]
            if info.get("components"):
                node["components"] = info["components"]
        return node

    def _walk_dir(dir_path: str) -> List[dict]:
        if not os.path.isdir(dir_path):
            return []
        entries = sorted(os.listdir(dir_path))
        json_files = [e for e in entries if e.endswith(".meta.json")]
        sub_dirs = [e for e in entries if os.path.isdir(os.path.join(dir_path, e))]
        nodes = []

        for jf in json_files:
            block_name = jf[:-10]
            json_path = os.path.join(dir_path, jf)
            node = _build_node(block_name, json_path)
            has_sub = block_name in sub_dirs
            if has_sub:
                node["children"] = _walk_dir(os.path.join(dir_path, block_name))
                sub_dirs.remove(block_name)
            nodes.append(node)

        for sd in sub_dirs:
            children = _walk_dir(os.path.join(dir_path, sd))
            if children:
                nodes.append({"name": sd, "children": children})

        return nodes

    # 构建根节点
    root = _build_node(branch_name, root_json) if os.path.isfile(root_json) else {"name": branch_name}
    children = _walk_dir(branch_dir)
    if children:
        root["children"] = children

    return json.dumps(root, ensure_ascii=False, indent=2)


async def fix_mermaid(
    mermaid_code: str,
    markdown_text: str,
    error_msg: str,
    llm_interface: LLMInterface,
    max_retries: int = 5,
) -> Optional[str]:
    """
    调用 GPT-4.1 修复有语法错误的 mermaid 代码。
    每次将错误信息 + 当前 mermaid + 章节文字一并发送，让模型只修语法不改语义。
    修复成功返回新代码，全部失败返回 None（调用方降级为不输出 mermaid）。
    """
    current_mermaid = mermaid_code
    current_error = error_msg

    for attempt in range(1, max_retries + 1):
        try:
            user_prompt = MERMAID_FIX_PROMPT.format(
                markdown=markdown_text,
                mermaid=current_mermaid,
                error=current_error,
            )
            fixed = await llm_interface.generate_with_retry(
                system_prompt="你是 Mermaid 图表语法专家，只输出修复后的 mermaid 代码，不含任何解释。",
                user_prompt=user_prompt,
                retry_count=1,
            )
            # 去掉模型可能多输出的 ```mermaid``` 包裹
            fixed = re.sub(r'^```(?:mermaid)?\s*\n?', '', fixed.strip())
            fixed = re.sub(r'\n?```\s*$', '', fixed).strip()

            val = _mermaid_validator.validate_file(f"```mermaid\n{fixed}\n```")
            if val["result"]:
                logger.info(f"  [mermaid修复] 第{attempt}次成功")
                return fixed

            current_error = str(val["errors"])
            current_mermaid = fixed
            logger.warning(f"  [mermaid修复] 第{attempt}次修复后仍有错误: {current_error}")

        except Exception as e:
            logger.warning(f"  [mermaid修复] 第{attempt}次调用失败: {e}")

    logger.warning("  [mermaid修复] 全部重试失败，降级为 null")
    return None


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
    from langchain.schema import StrOutputParser

    # 按章节 key 选择专用提示词，未单独定制的章节类型回落到通用提示词
    _SECTION_PROMPTS = {
        "state_machine": STATE_MACHINE_RELEVANCE_PROMPT,
        "message_queue": MESSAGE_QUEUE_RELEVANCE_PROMPT,
    }
    _json_llm = llm_interface.get_json_llm()
    _parser = StrOutputParser()
    relevance_chains = {
        key: (prompt | _json_llm | _parser)
        for key, prompt in _SECTION_PROMPTS.items()
    }
    _default_chain = BATCH_RELEVANCE_PROMPT | _json_llm | _parser

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
                hints_str = "\n".join(f"  - {h}" for h in section.get("search_hints", []))
                chain = relevance_chains.get(section["key"], _default_chain)
                relevance_result = await chain.ainvoke({
                    "section_title": section["title"],
                    "section_description": section["description"],
                    "search_hints": hints_str,
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
                        for item in needed_blocks:
                            # 兼容新格式 {"模块名": "xxx", "搜索线索": [...]} 和旧格式 "模块名"
                            if isinstance(item, dict):
                                bname = item.get("模块名", "")
                                dynamic_hints = item.get("搜索线索", [])
                            else:
                                bname = str(item)
                                dynamic_hints = []

                            matched = bname if bname in branch_blocks else None
                            if not matched:
                                # 尝试各种分隔符取最后一段：处理 "A > B"、"A.B"、"A / B" 等路径式写法
                                for sep in (" > ", " / ", ".", "/"):
                                    if sep in bname:
                                        candidate = bname.split(sep)[-1].strip()
                                        if candidate in branch_blocks:
                                            matched = candidate
                                            break
                            if matched:
                                if matched not in scan_results:
                                    scan_results[matched] = []
                                scan_results[matched].append({
                                    "key": section["key"],
                                    "hints": dynamic_hints,
                                })
                                logger.info(f"  → {matched}: 需要「{section['title']}」, 线索: {dynamic_hints}")
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

        # 并发获取所有block的文件列表
        block_names = list(scan_results.keys())
        file_list_results = await asyncio.gather(
            *(get_block_files_from_neo4j(neo4j_interface, bn) for bn in block_names)
        )
        block_file_lists = dict(zip(block_names, file_list_results))

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

            file_list = block_file_lists[block_name]

            for section_item in section_keys:
                section_key = section_item["key"]
                dynamic_hints = section_item.get("hints", [])

                section_def = next((s for s in active_sections if s["key"] == section_key), None)
                if not section_def:
                    continue

                # 合并：动态线索优先，注册表hints作为补充
                merged_hints = dynamic_hints + [
                    h for h in section_def.get("search_hints", [])
                    if h not in dynamic_hints
                ]

                # section_number 不在这里预分配，而是在merge阶段根据实际成功的结果动态编号
                tasks_info.append({
                    "block_name": block_name,
                    "block_desc": block_desc,
                    "file_list": file_list,
                    "section_def": section_def,
                    "search_hints": merged_hints,
                    "max_section_num": max_section_num,
                    "wiki_json_path": wiki_json_path,
                })

        logger.info(f"共 {len(tasks_info)} 个章节生成任务")

        max_concurrent = int(os.environ.get("MAX_CONCURRENT_BLOCKS", "3"))
        semaphore = asyncio.Semaphore(max_concurrent)
        generated_results = []

        max_retries = int(os.environ.get("AGENT_MAX_RETRIES", "2"))
        agent_timeout = int(os.environ.get("AGENT_TIMEOUT", "180"))

        async def generate_single(task: dict, index: int):
            async with semaphore:
                block_name = task["block_name"]
                section_def = task["section_def"]
                section_key = section_def["key"]
                # 给agent一个临时序号用于生成标题，merge阶段会替换为正确的连续序号
                temp_section_number = task["max_section_num"] + 1

                label = f"[{index}/{len(tasks_info)}] {block_name} - {section_def['title']}"

                for attempt in range(1, max_retries + 1):
                    logger.info(f"  {label}: 第{attempt}次尝试" if attempt > 1 else f"  {label}: 开始生成")

                    try:
                        result = await run_section_agent(
                            block_name=block_name,
                            block_description=task["block_desc"],
                            file_list=task["file_list"],
                            section_title=section_def["title"],
                            section_description=section_def["description"],
                            agent_instruction=section_def["agent_instruction"],
                            search_hints=task["search_hints"],
                            section_number=temp_section_number,
                            source_root=source_root,
                            timeout=agent_timeout,
                        )

                        # 记录Agent完整返回到日志
                        logger.debug(f"[AGENT] {label} 返回:\n"
                                     f"  has_content={result.get('has_content')}\n"
                                     f"  markdown长度={len(result.get('markdown', ''))}\n"
                                     f"  mermaid={'有' if result.get('mermaid') else '无'}\n"
                                     f"  referenced_files={result.get('referenced_files', [])}\n"
                                     f"  markdown预览={result.get('markdown', '')[:300]}")

                        if not result.get("has_content"):
                            logger.info(f"  {label}: 无相关内容，跳过")
                            return None

                        logger.info(f"  {label}: 完成")

                        return {
                            "block_name": block_name,
                            "section_key": section_key,
                            "section_title": section_def["title"],
                            "max_section_num": task["max_section_num"],
                            "wiki_json_path": task["wiki_json_path"],
                            "content": result,
                        }
                    except Exception as e:
                        logger.warning(f"  {label}: 第{attempt}次失败 - {e}")
                        if attempt < max_retries:
                            wait = 5 * attempt
                            logger.info(f"  {label}: {wait}秒后重试...")
                            await asyncio.sleep(wait)

                logger.error(f"  {label}: {max_retries}次尝试均失败，放弃")
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
            # 同一个wiki文件的多个可选章节在此循环中依次 +1，保证序号连续
            current_max = get_max_section_number(wiki_data)

            # 从第一章（模块功能概述）的neo4j_id提取block级别的nodeId列表，作为fallback
            block_fallback_ids = []
            first_entry = wiki_data["wiki"][0] if wiki_data.get("wiki") else {}
            for v in first_entry.get("neo4j_id", {}).values():
                if isinstance(v, list):
                    block_fallback_ids.extend(str(x) for x in v)
                else:
                    block_fallback_ids.append(str(v))

            for section_info in sections:
                content = section_info["content"]
                section_key = section_info["section_key"]
                temp_num = section_info["max_section_num"] + 1  # agent生成时用的临时序号

                # 直接追加：分配连续序号
                current_max += 1
                actual_num = current_max

                # # -------- is_replace 逻辑（暂时注释，目前仅处理首次生成场景）--------
                # title_to_num = {}
                # num_to_indices = {}
                # for idx, entry in enumerate(wiki_data.get("wiki", [])):
                #     text = entry.get("markdown", "") + entry.get("mermaid", "")
                #     for m in re.finditer(r'(?<!#)##(?!#)\s+(\d+)\.\s*(.+)', text):
                #         title_to_num[m.group(2).strip()] = int(m.group(1))
                #     for nm in re.findall(r'(?m)^#{2,3}\s+(\d+)(?:\.\d+)?[\.\s]', text):
                #         main_num = int(nm)
                #         num_to_indices.setdefault(main_num, [])
                #         if idx not in num_to_indices[main_num]:
                #             num_to_indices[main_num].append(idx)
                # section_title = section_info.get("section_title", "")
                # if section_title and section_title in title_to_num:
                #     actual_num = title_to_num[section_title]
                #     old_indices_set = set(num_to_indices.get(actual_num, []))
                #     if old_indices_set:
                #         last_idx = max(old_indices_set)
                #         for pos in range(last_idx + 1, min(last_idx + 3, len(wiki_data["wiki"]))):
                #             candidate = wiki_data["wiki"][pos]
                #             if "mermaid" in candidate and "mapping" not in candidate:
                #                 if re.match(r'(?m)^###\s+\d+\.', candidate.get("mermaid", "")):
                #                     old_indices_set.add(pos)
                #     old_indices = sorted(old_indices_set)
                #     insert_pos = old_indices[0]
                #     for i in sorted(old_indices, reverse=True):
                #         del wiki_data["wiki"][i]
                #     insert_pos = min(insert_pos, len(wiki_data["wiki"]))
                #     for i, entry in enumerate(new_entries):
                #         wiki_data["wiki"].insert(insert_pos + i, entry)
                # # -------- end is_replace --------

                # ---- 提取 referenced_files 中的文件路径（兼容新旧格式）----
                raw_refs = content.get("referenced_files", [])
                file_paths = []
                for ref in raw_refs:
                    if isinstance(ref, dict):
                        file_paths.append(ref.get("path", ""))
                    elif isinstance(ref, str):
                        file_paths.append(ref)
                file_paths = [p for p in file_paths if p]

                # 查找referenced_files对应的neo4j nodeId（用于markdown章节的neo4j_id）
                file_node_ids = await resolve_file_node_ids(
                    neo4j_interface, file_paths
                )

                node_id_list = [str(v) for v in file_node_ids.values()] if file_node_ids else []

                # 兜底：若无法通过文件路径解析到nodeId，使用第一章模块功能概述的neo4j_id
                if not node_id_list:
                    node_id_list = block_fallback_ids

                # 替换markdown中的临时序号为实际序号
                # 注意：f-string中 {{2,3}} 才能输出正确的regex量词 {2,3}
                markdown_text = content.get("markdown", "")
                if temp_num != actual_num:
                    markdown_text = re.sub(
                        rf'(#{{2,3}}\s+){temp_num}(\.|(?=\s))',
                        rf'\g<1>{actual_num}\2',
                        markdown_text
                    )

                # 从markdown中提取###级子标题编号，构建neo4j_id映射
                # 只匹配 ### 子标题，避免把 ## 主标题误捕获为 key
                sub_titles = re.findall(r'(?m)^###\s+([\d.]+)', markdown_text)
                if sub_titles:
                    neo4j_id_map = {t: node_id_list for t in sub_titles}
                else:
                    neo4j_id_map = {str(actual_num): node_id_list}

                # 构建新的markdown条目（文字部分始终使用neo4j_id）
                markdown_entry = {
                    "markdown": markdown_text,
                    "neo4j_id": neo4j_id_map
                }

                # 构建新的mermaid条目（如果有）
                # 若markdown中已内嵌了```mermaid块，则不再单独创建mermaid条目，避免重复
                markdown_has_mermaid = "```mermaid" in markdown_text
                mermaid_entry = None
                if content.get("mermaid") and not markdown_has_mermaid:
                    mermaid_text = content["mermaid"]

                    # 校验 mermaid 语法，不通过则用 GPT-4.1 修复
                    val = _mermaid_validator.validate_file(f"```mermaid\n{mermaid_text}\n```")
                    if not val["result"]:
                        logger.warning(f"  [mermaid校验] 章节{actual_num} 语法错误: {val['errors']}，尝试修复...")
                        mermaid_text = await fix_mermaid(
                            mermaid_text, markdown_text, str(val["errors"]), llm_interface
                        )
                        if mermaid_text is None:
                            logger.warning(f"  [mermaid校验] 修复失败，跳过 mermaid 条目")
                    else:
                        logger.debug(f"  [mermaid校验] 章节{actual_num} 语法正确")

                if content.get("mermaid") and not markdown_has_mermaid and mermaid_text is not None:
                    if temp_num != actual_num:
                        mermaid_text = mermaid_text.replace(f"{temp_num}.", f"{actual_num}.")

                    # 找出已有子标题中属于本章的最大子序号，+1作为mermaid的子序号
                    existing_sub_nums = [
                        int(t.split(".")[1])
                        for t in sub_titles
                        if "." in t and t.startswith(f"{actual_num}.")
                    ]
                    next_sub = (max(existing_sub_nums) + 1) if existing_sub_nums else 1
                    mermaid_sub = f"{actual_num}.{next_sub}"
                    mermaid_title = f"### {mermaid_sub} 架构图"

                    # ---- mermaid 章节使用 mapping + source_id_list ----
                    mermaid_mapping_raw = content.get("mermaid_mapping")
                    if mermaid_mapping_raw and isinstance(mermaid_mapping_raw, dict):
                        # 收集已有的 source_id，用于避免碰撞
                        existing_sids = set()
                        for entry in wiki_data.get("source_id_list", []):
                            existing_sids.add(str(entry.get("source_id", "")))

                        def _gen_unique_sid() -> str:
                            """生成8位唯一source_id，保证不与已有ID碰撞"""
                            for _ in range(100):
                                sid = str(uuid.uuid4().int)[:8]
                                if sid not in existing_sids:
                                    existing_sids.add(sid)
                                    return sid
                            # 极端情况fallback到完整uuid前12位
                            sid = str(uuid.uuid4().int)[:12]
                            existing_sids.add(sid)
                            return sid

                        # 为每个唯一的 (path, lines) 生成 source_id
                        # path_key → source_id 的去重映射
                        path_to_source_id = {}
                        new_source_entries = []
                        mapping_result = {}

                        for node_id, loc in mermaid_mapping_raw.items():
                            if not isinstance(loc, dict) or not loc.get("path"):
                                continue
                            fpath = loc["path"]
                            flines = loc.get("lines", [])
                            # 用 (path, 排序后lines元组) 作为去重key
                            dedup_key = (fpath, tuple(sorted(flines)))

                            if dedup_key not in path_to_source_id:
                                sid = _gen_unique_sid()
                                path_to_source_id[dedup_key] = sid
                                new_source_entries.append({
                                    "source_id": sid,
                                    "name": fpath,
                                    "lines": flines if flines else [],
                                })

                            mapping_result[node_id] = path_to_source_id[dedup_key]

                        if mapping_result:
                            mermaid_entry = {
                                "mermaid": f"{mermaid_title}\n\n```mermaid\n{mermaid_text}\n```",
                                "mapping": mapping_result,
                            }
                            # 追加到 wiki 的 source_id_list
                            if "source_id_list" not in wiki_data:
                                wiki_data["source_id_list"] = []
                            wiki_data["source_id_list"].extend(new_source_entries)
                            logger.info(f"  [mermaid] 章节{actual_num}: 生成 {len(mapping_result)} 个mapping, "
                                        f"{len(new_source_entries)} 个source_id")
                        else:
                            # mapping为空，fallback到neo4j_id
                            mermaid_entry = {
                                "mermaid": f"{mermaid_title}\n\n```mermaid\n{mermaid_text}\n```",
                                "neo4j_id": {mermaid_sub: node_id_list}
                            }
                    else:
                        # 无 mermaid_mapping（兼容旧agent），fallback到neo4j_id
                        mermaid_entry = {
                            "mermaid": f"{mermaid_title}\n\n```mermaid\n{mermaid_text}\n```",
                            "neo4j_id": {mermaid_sub: node_id_list}
                        }

                # 构建新条目列表，追加到末尾
                new_entries = [markdown_entry]
                if mermaid_entry:
                    new_entries.append(mermaid_entry)
                wiki_data["wiki"].extend(new_entries)

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

    llm = LLMInterface(model_name="gpt-4.1", provider="openai")

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
