"""
Neo4j数据库接口

提供层级化模块生成所需的数据库操作功能
"""

from typing import Dict, List, Any, Optional
import asyncio
import json
from neo4j import GraphDatabase
from collections import defaultdict
from collections import deque




class Neo4jInterface:
    """Neo4j数据库接口，专门用于层级化模块生成"""

    def __init__(self, uri: str, user: str, password: str):
        """初始化Neo4j连接

        Args:
            uri: Neo4j数据库URI
            user: 用户名
            password: 密码
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()

    async def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """执行Cypher查询并返回结果

        Args:
            query: Cypher查询语句
            parameters: 查询参数

        Returns:
            查询结果列表
        """
        def _execute(query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
            with self.driver.session() as session:
                result = session.run(query, params or {})
                records = []
                for record in result:
                    record_dict = {}
                    for key in record.keys():
                        record_dict[key] = record[key]
                    records.append(record_dict)
                return records

        # 在线程池中执行同步查询
        return await asyncio.to_thread(_execute, query, parameters)
    

    async def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """根据nodeId获取节点信息

        Args:
            node_id: 节点ID

        Returns:
            节点信息字典，如果不存在返回None
        """
        # 尝试不同的数据类型
        queries_to_try = [
            ("字符串参数", "MATCH (n) WHERE n.nodeId = $node_id RETURN n.name AS name, n.background AS background, n.source_code AS source_code, n.nodeId AS nodeId, n.semantic_explanation AS semantic_explanation, n.child_blocks AS child_blocks, n.contain_nodes AS contain_nodes, labels(n) AS labels", str(node_id)),
            ("整数参数", "MATCH (n) WHERE n.nodeId = $node_id RETURN n.name AS name, n.background AS background, n.source_code AS source_code, n.nodeId AS nodeId, n.semantic_explanation AS semantic_explanation, n.child_blocks AS child_blocks, n.contain_nodes AS contain_nodes, labels(n) AS labels", int(node_id) if str(node_id).isdigit() else node_id),
        ]

        for query_name, query, param_value in queries_to_try:
            try:
                result = await self.execute_query(query, {"node_id": param_value})
                if result:
                    return result[0]
            except Exception as e:
                print(f"查询失败 ({query_name}): {e}")
                continue

        return None
    
    async def get_all_node_relationship():

        return None

    async def test_connection(self) -> bool:
        """测试数据库连接

        Returns:
            连接是否成功
        """
        try:
            query = "RETURN 1 as test"
            result = await self.execute_query(query)
            return len(result) > 0
        except Exception:
            return False

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self.close()




# async def main():
#     # 相对导入
#     from chains.prompts.component import BLOCK_RELATIONSHIP_PROMPT
#     from chains.common_chains import ChainFactory
#     from interfaces.llm_interface import LLMInterface
#     from dotenv import load_dotenv
#     load_dotenv()
#     neo4j_interface = Neo4jInterface("bolt://localhost:7689", "neo4j", "passwd123")
#     a = await neo4j_interface.get_high_module()
#     d = await neo4j_interface.get_block_relationship(a)
#     # name = a[4]["name"]
#     # # id = a[4]['child_blocks']
#     # d = await neo4j_interface.get_module_call("ext4_superblock_and_fs_control_interface", 5005)
#     # llm = LLMInterface(model_name="gpt-4.1-2025-04-14", provider="openai")
#     # relation_chain = ChainFactory.create_generic_chain(llm, BLOCK_RELATIONSHIP_PROMPT)
#     # r = await relation_chain.ainvoke({"cross_module_calls": d})
#     with open("result.md", "w", encoding="utf-8") as f:
#         f.write(d)
#     neo4j_interface.close()

# if __name__ == "__main__":
#     asyncio.run(main())