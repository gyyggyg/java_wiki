"""
Wiki 交互式修改智能体

使用 Anthropic Claude API 的 tool use 模式，实现 agentic loop：
Claude 根据用户需求自主决定需要哪些数据源，收集信息后提交结构化修改。
"""

import os
import json
import subprocess
import re
from typing import List, Dict, Any, Optional

# ==================== 配置 ====================

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "sonnet")  # claude CLI 支持: sonnet, opus, haiku
MAX_TOOL_ROUNDS = int(os.environ.get("MAX_TOOL_ROUNDS", "15"))
SOURCE_ROOT_PATH = os.environ.get("SOURCE_ROOT_PATH", "")

# ==================== System Prompt ====================

SYSTEM_PROMPT = """你是一个代码仓库 Wiki 文档的专业编辑智能体。

## 你的任务
用户选中了当前 Wiki 页面中的一些内容块（blocks），并提出了修改需求。你需要：
1. 理解用户的修改意图
2. 自主判断是否需要额外信息（源码、其他 Wiki 页面、代码库搜索、Neo4j 关系图谱）
3. 使用提供的工具收集所需信息
4. 完成后调用 submit_page_diff（修改当前页面）或 submit_create_page（新建页面）提交结果

## Wiki 数据结构
Wiki 页面由嵌套的 block 组成，有两种类型：

### section 块（章节容器）
```json
{
  "type": "section",
  "id": "S1",
  "title": "## 章节标题",
  "content": [ ...子块... ]
}
```

### text 块（内容叶子节点）
```json
{
  "type": "text",
  "id": "S3",
  "content": {
    "markdown": "正文内容，支持 Markdown 格式",
    "mermaid": "可选的 Mermaid 图表代码"
  },
  "source_id": ["1", "2"],
  "neo4j_id": { "section_ref": "xxx" },
  "neo4j_source": { "section_ref": "xxx" }
}
```

## 提交规则
- insert_blocks 中的 after_block 必须是页面中已存在的 block ID
- delete_blocks 中的 ID 应来自用户选中的 blocks
- 新建 block 的 ID 使用 "NEW_1", "NEW_2" 等格式，避免与已有 ID 冲突
- markdown 内容使用中文
- source_id 引用真实存在的源码文件
- 如果需要 Mermaid 图表，放在 text 块的 content.mermaid 字段中

## 工作原则
- 先充分了解上下文再提交修改，不要猜测
- 如果需要查看源码才能写出准确的描述，先调用 read_source_file
- 如果不确定代码关系，先调用 search_codebase 或 query_neo4j
- 一次性收集完所有需要的信息，避免不必要的多轮调用
- 最终必须调用 submit_page_diff 或 submit_create_page 提交结果
"""

# ==================== 工具定义 ====================

TOOLS = [
    {
        "name": "read_source_file",
        "description": "读取项目源码文件。可以指定行范围只读取部分内容。",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "源码文件路径（相对于项目根目录）"
                },
                "start_line": {
                    "type": "integer",
                    "description": "起始行号（从1开始，含）"
                },
                "end_line": {
                    "type": "integer",
                    "description": "结束行号（从1开始，含）"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "search_codebase",
        "description": "在代码库中搜索文本模式，返回匹配的文件和行号。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索模式（支持正则表达式）"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "文件过滤模式，例如 '*.java'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_wiki_page",
        "description": "读取其他 Wiki 页面的内容，了解相关模块的文档。",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_path": {
                    "type": "string",
                    "description": "Wiki 页面路径"
                }
            },
            "required": ["page_path"]
        }
    },
    {
        "name": "query_neo4j",
        "description": "执行 Cypher 查询，从 Neo4j 知识图谱获取代码实体和关系信息。",
        "input_schema": {
            "type": "object",
            "properties": {
                "cypher_query": {
                    "type": "string",
                    "description": "Cypher 查询语句"
                }
            },
            "required": ["cypher_query"]
        }
    },
    {
        "name": "submit_page_diff",
        "description": "提交对当前 Wiki 页面的修改。收集完信息后调用此工具，会终止对话。",
        "input_schema": {
            "type": "object",
            "properties": {
                "insert_blocks": {
                    "type": "array",
                    "description": "要插入的 block 列表。each: {after_block: 目标block ID, block: 新block对象}",
                    "items": {
                        "type": "object",
                        "properties": {
                            "after_block": {"type": "string"},
                            "block": {"type": "object"}
                        },
                        "required": ["after_block", "block"]
                    }
                },
                "delete_blocks": {
                    "type": "array",
                    "description": "要删除的 block ID 列表",
                    "items": {"type": "string"}
                },
                "insert_sources": {
                    "type": "array",
                    "description": "要添加的源码引用",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source_id": {"type": "string"},
                            "name": {"type": "string"},
                            "lines": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["source_id", "name", "lines"]
                    }
                },
                "delete_sources": {
                    "type": "array",
                    "description": "要删除的源码引用 ID 列表",
                    "items": {"type": "string"}
                }
            }
        }
    },
    {
        "name": "submit_create_page",
        "description": "创建新的 Wiki 页面。当用户需求需要新建独立页面时调用，会终止对话。",
        "input_schema": {
            "type": "object",
            "properties": {
                "new_page_path": {
                    "type": "string",
                    "description": "新页面路径，例如 'module-name/page-name.json'"
                },
                "content": {
                    "type": "array",
                    "description": "页面内容 blocks（同 markdown_content 结构）"
                },
                "source": {
                    "type": "array",
                    "description": "页面源码引用列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source_id": {"type": "string"},
                            "name": {"type": "string"},
                            "lines": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["source_id", "name", "lines"]
                    }
                }
            },
            "required": ["new_page_path", "content", "source"]
        }
    }
]

# ==================== 工具执行 ====================


def _read_source_file(tool_input: dict) -> str:
    """读取源码文件"""
    file_path = tool_input["file_path"]
    source_root = SOURCE_ROOT_PATH

    if not source_root:
        return "错误：未配置 SOURCE_ROOT_PATH 环境变量，无法读取源码文件。"

    full_path = os.path.join(source_root, file_path)
    if not os.path.isfile(full_path):
        return f"文件不存在：{file_path}"

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return f"读取文件失败：{e}"

    start = tool_input.get("start_line")
    end = tool_input.get("end_line")

    if start is not None or end is not None:
        start = max(1, start or 1)
        end = min(len(lines), end or len(lines))
        lines = lines[start - 1:end]
        header = f"文件：{file_path} (行 {start}-{end})\n"
    else:
        header = f"文件：{file_path} (共 {len(lines)} 行)\n"

    # 限制输出大小
    content = "".join(lines)
    if len(content) > 50000:
        content = content[:50000] + "\n... (内容已截断)"

    return header + content


def _search_codebase(tool_input: dict) -> str:
    """搜索代码库"""
    source_root = SOURCE_ROOT_PATH
    if not source_root:
        return "错误：未配置 SOURCE_ROOT_PATH 环境变量，无法搜索代码库。"

    query = tool_input["query"]
    file_pattern = tool_input.get("file_pattern")

    cmd = ["grep", "-rn", "--max-count=5", query, source_root]
    if file_pattern:
        cmd = ["grep", "-rn", "--max-count=5", "--include", file_pattern, query, source_root]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        if not output:
            return f"未找到匹配 '{query}' 的结果。"
        # 将绝对路径转为相对路径
        output = output.replace(source_root + "/", "")
        # 限制输出行数
        lines = output.split("\n")
        if len(lines) > 100:
            output = "\n".join(lines[:100]) + f"\n... (共 {len(lines)} 条结果，已截断)"
        return output
    except subprocess.TimeoutExpired:
        return "搜索超时（30秒）。请尝试更精确的搜索模式。"
    except Exception as e:
        return f"搜索失败：{e}"


def _read_wiki_page(tool_input: dict, wiki_root: str) -> str:
    """读取其他 Wiki 页面"""
    page_path = tool_input["page_path"].lstrip("/")
    if os.path.isabs(wiki_root):
        json_path = os.path.join(wiki_root, page_path)
    else:
        json_path = os.path.join(os.path.dirname(__file__), wiki_root, page_path)

    if not os.path.isfile(json_path):
        return f"Wiki 页面不存在：{page_path}"

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        content = json.dumps(data, ensure_ascii=False, indent=2)
        if len(content) > 50000:
            content = content[:50000] + "\n... (内容已截断)"
        return content
    except Exception as e:
        return f"读取 Wiki 页面失败：{e}"


def _query_neo4j(tool_input: dict) -> str:
    """查询 Neo4j"""
    neo4j_uri = os.environ.get("NEO4J_URI")
    if not neo4j_uri:
        return "Neo4j 未配置（缺少 NEO4J_URI 环境变量）。请使用其他工具获取代码关系信息。"

    try:
        from neo4j import GraphDatabase
        neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        neo4j_password = os.environ.get("NEO4J_PASSWORD", "")
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

        with driver.session() as session:
            result = session.run(tool_input["cypher_query"])
            records = [dict(record) for record in result]

        driver.close()

        if not records:
            return "查询无结果。"

        output = json.dumps(records, ensure_ascii=False, indent=2, default=str)
        if len(output) > 30000:
            output = output[:30000] + "\n... (结果已截断)"
        return output
    except ImportError:
        return "Neo4j 驱动未安装。请安装 neo4j 包或使用其他工具。"
    except Exception as e:
        return f"Neo4j 查询失败：{e}"


def execute_tool(tool_name: str, tool_input: dict, wiki_root: str) -> str:
    """工具分发器"""
    if tool_name == "read_source_file":
        return _read_source_file(tool_input)
    elif tool_name == "search_codebase":
        return _search_codebase(tool_input)
    elif tool_name == "read_wiki_page":
        return _read_wiki_page(tool_input, wiki_root)
    elif tool_name == "query_neo4j":
        return _query_neo4j(tool_input)
    else:
        return f"未知工具：{tool_name}"


# ==================== 辅助函数 ====================


def find_blocks_by_ids(blocks: list, target_ids: set) -> list:
    """递归查找指定 ID 的 blocks"""
    found = []
    for block in blocks:
        if block.get("id") in target_ids:
            found.append(block)
        children = block.get("content")
        if isinstance(children, list):
            found.extend(find_blocks_by_ids(children, target_ids))
    return found


def build_page_outline(blocks: list, depth: int = 0) -> str:
    """生成页面结构概览（只包含 ID 和标题）"""
    lines = []
    for block in blocks:
        indent = "  " * depth
        if block.get("type") == "section":
            lines.append(f"{indent}- [{block.get('id')}] {block.get('title', '(无标题)')}")
            children = block.get("content")
            if isinstance(children, list):
                lines.append(build_page_outline(children, depth + 1))
        else:
            block_id = block.get("id", "?")
            # text 块只显示前 50 个字符
            md = ""
            content = block.get("content")
            if isinstance(content, dict):
                md = content.get("markdown", "")
            preview = md[:50].replace("\n", " ") + ("..." if len(md) > 50 else "")
            lines.append(f"{indent}- [{block_id}] text: {preview}")
    return "\n".join(lines)


# ==================== 核心 agentic loop ====================


async def run_detailed_query(
    page_path: str,
    block_ids: List[str],
    user_query: str,
    wiki_root: str,
) -> dict:
    """
    使用 Claude agentic loop 处理用户的详细查询请求。

    Returns:
        dict: PageDiffResponse 或 CreatePageResponse 格式的结果
    """
    # 1. 加载当前页面（路径逻辑与 server.py 的 fetch_page 一致）
    page_path_clean = page_path.lstrip("/")
    if os.path.isabs(wiki_root):
        json_path = os.path.join(wiki_root, page_path_clean)
    else:
        json_path = os.path.join(os.path.dirname(__file__), wiki_root, page_path_clean)

    print(f"[Agent] wiki_root={wiki_root}, page_path={page_path}, json_path={json_path}")

    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"Wiki 页面文件不存在: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        page_data = json.load(f)

    page_content = page_data.get("markdown_content", [])
    page_sources = page_data.get("source_id", [])

    # 2. 提取选中的 blocks
    selected_blocks = find_blocks_by_ids(page_content, set(block_ids))

    # 3. 构建页面结构概览
    outline = build_page_outline(page_content)

    # 4. 构建初始消息
    initial_message = f"""## 当前 Wiki 页面
页面路径：{page_path}

### 页面结构概览
{outline}

### 用户选中的 blocks
{json.dumps(selected_blocks, ensure_ascii=False, indent=2)}

### 页面源码引用列表
{json.dumps(page_sources, ensure_ascii=False, indent=2)}

## 用户需求
{user_query}
"""

    # 5. 通过 claude CLI 调用（复用本地 Claude Code 认证）
    prompt = f"""{SYSTEM_PROMPT}

{initial_message}

请根据以上信息，直接输出一个 JSON 对象作为你的修改结果。不要输出任何其他内容。

如果是修改当前页面，输出格式：
{{
  "action": "page_diff",
  "insert_blocks": [{{ "after_block": "目标block ID", "block": {{...}} }}],
  "delete_blocks": ["要删除的block ID"],
  "insert_sources": [{{ "source_id": "...", "name": "...", "lines": ["..."] }}],
  "delete_sources": ["要删除的source ID"]
}}

如果是新建页面，输出格式：
{{
  "action": "create_page",
  "new_page_path": "路径.json",
  "content": [{{...blocks...}}],
  "source": [{{ "source_id": "...", "name": "...", "lines": ["..."] }}]
}}

只输出 JSON，不要用 markdown 代码块包裹，不要输出解释文字。"""

    print(f"[Agent] 调用 claude CLI (model={CLAUDE_MODEL})...")

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", CLAUDE_MODEL, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=SOURCE_ROOT_PATH or None,
        )
    except FileNotFoundError:
        raise RuntimeError("未找到 claude CLI，请确认已安装 Claude Code")
    except subprocess.TimeoutExpired:
        raise TimeoutError("claude CLI 调用超时（120秒）")

    if result.returncode != 0:
        print(f"[Agent] claude CLI 错误: {result.stderr}")
        raise RuntimeError(f"claude CLI 调用失败: {result.stderr}")

    raw_output = result.stdout.strip()
    print(f"[Agent] claude CLI 原始输出长度: {len(raw_output)}")

    # 解析 claude --output-format json 的输出
    # 格式为 {"type":"result","subtype":"success","cost_usd":...,"result":"..."}
    try:
        cli_response = json.loads(raw_output)
        if isinstance(cli_response, dict) and "result" in cli_response:
            raw_output = cli_response["result"]
    except json.JSONDecodeError:
        pass  # 不是 JSON 包装，直接使用原始输出

    # 从输出中提取 JSON（处理可能的 markdown 代码块包裹）
    json_str = raw_output.strip()
    # 去除 ```json ... ``` 包裹
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', json_str, re.DOTALL)
    if json_match:
        json_str = json_match.group(1).strip()
    # 去除前后非 JSON 文字，找到第一个 { 和最后一个 }
    brace_start = json_str.find('{')
    brace_end = json_str.rfind('}')
    if brace_start != -1 and brace_end != -1:
        json_str = json_str[brace_start:brace_end + 1]

    try:
        parsed = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[Agent] JSON 解析失败: {e}")
        print(f"[Agent] 原始输出: {raw_output[:500]}")
        raise RuntimeError(f"智能体输出的 JSON 格式无效: {e}")

    print(f"[Agent] 完成，action={parsed.get('action', 'unknown')}")

    # 转换为 server.py 期望的格式
    action = parsed.get("action", "")
    if action == "create_page":
        return {
            "new_page_path": parsed["new_page_path"],
            "new_page": {
                "content": parsed["content"],
                "source": parsed.get("source", []),
            }
        }
    else:
        # page_diff（默认）
        return {
            "insert_blocks": parsed.get("insert_blocks", []),
            "delete_blocks": parsed.get("delete_blocks", []),
            "insert_sources": parsed.get("insert_sources", []),
            "delete_sources": parsed.get("delete_sources", []),
        }
