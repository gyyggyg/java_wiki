"""
Neo4j MCP Server

提供 Cypher 只读查询工具，供 Claude CLI 通过 MCP 协议调用。
启动方式: python neo4j_mcp_interface.py
"""

import os
import sys
import json
import logging
import atexit
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录的 .env
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# 日志配置
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("neo4j_mcp")
logger.setLevel(logging.DEBUG)
_handler = logging.FileHandler(os.path.join(LOG_DIR, "neo4j_mcp.log"), encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(_handler)

# 关键：在导入 neo4j 前，先保存真实的 stdout/stderr，
# 然后将 sys.stdout/stderr 重定向到 devnull，防止第三方库（如 NumExpr）
# 向 stdout 输出信息从而污染 MCP stdio 协议。
_real_stderr = sys.stderr

logger.debug("开始导入 neo4j...")
_devnull = open(os.devnull, "w")
sys.stderr = _devnull  # NumExpr 输出到 stderr
try:
    from neo4j import GraphDatabase
finally:
    sys.stderr = _real_stderr
    _devnull.close()
logger.debug("neo4j 导入完成")

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("neo4j-knowledge-graph")

# 写操作关键词黑名单
_WRITE_KEYWORDS = {'CREATE', 'DELETE', 'SET', 'MERGE', 'REMOVE', 'DROP', 'DETACH'}

# 查询计数器
_query_counter = 0

# 驱动单例
_driver = None


def _get_driver():
    """获取或创建 Neo4j 驱动单例。"""
    global _driver
    if _driver is None:
        neo4j_uri = os.environ.get("WIKI_NEO4J_URI")
        neo4j_user = os.environ.get("WIKI_NEO4J_USER", "neo4j")
        neo4j_password = os.environ.get("WIKI_NEO4J_PASSWORD", "")
        logger.debug(f"Neo4j连接: uri={neo4j_uri}, user={neo4j_user}")
        if not neo4j_uri:
            logger.error("WIKI_NEO4J_URI 环境变量为空!")
            raise ValueError("WIKI_NEO4J_URI not set")
        _driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        logger.debug("driver创建成功")
        atexit.register(_close_driver)
    return _driver


def _close_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


@mcp.tool()
def query_neo4j(cypher_query: str) -> str:
    """执行只读 Cypher 查询，从 Neo4j 知识图谱获取代码实体和关系信息。

    可查询的节点类型: Block, Directory, Package, File, Class, Interface,
    Enum, Record, Annotation, Method, Field, Enumconstant。
    可查询的关系类型: CALLS, EXTENDS, IMPLEMENTS, USES, DECLARES, CONTAINS,
    ANNOTATED_BY, HAS_TYPE, RETURNS, DIR_INCLUDE, f2c。

    Args:
        cypher_query: 只读 Cypher 查询语句（不允许写操作）
    """
    neo4j_uri = os.environ.get("WIKI_NEO4J_URI")
    if not neo4j_uri:
        return "Neo4j 未配置（缺少 WIKI_NEO4J_URI 环境变量）。请使用其他工具获取代码关系信息。"

    # 只读保护
    tokens = cypher_query.upper().split()
    if _WRITE_KEYWORDS & set(tokens):
        return "只允许只读查询，不能执行写操作（CREATE/DELETE/SET/MERGE/REMOVE/DROP）。"

    global _query_counter
    _query_counter += 1
    qid = _query_counter
    logger.info(f"[Q{qid}] 执行 Cypher 查询:\n{cypher_query}")

    try:
        driver = _get_driver()
        with driver.session() as session:
            result = session.run(cypher_query)
            records = [dict(record) for record in result]

        if not records:
            logger.info(f"[Q{qid}] 查询无结果")
            return "查询无结果。"

        output = json.dumps(records, ensure_ascii=False, indent=2, default=str)
        if len(output) > 30000:
            output = output[:30000] + "\n... (结果已截断)"

        logger.info(f"[Q{qid}] 查询成功: {len(records)} 条记录")
        return output
    except Exception as e:
        logger.error(f"[Q{qid}] Neo4j 查询失败: {e}", exc_info=True)
        return f"Neo4j 查询失败：{e}"


if __name__ == "__main__":
    logger.info("MCP Server 启动中...")
    mcp.run()
    logger.info("MCP Server 已退出")
