"""Neo4j 数据库连接和数据提取接口"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class Neo4jInterface:
    """Neo4j 数据库接口：负责连接、查询和数据提取"""
    
    def __init__(self, uri: str = None, username: str = None, 
                 password: str = None, database: str = None,
                 target_classes: List[str] = None):
        """
        初始化 Neo4j 连接
        
        Args:
            uri: Neo4j连接URI
            username: 用户名
            password: 密码
            database: 数据库名称
            target_classes: 目标类名列表
        """
        # 优先从参数读取，否则从环境变量/.env读取
        uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        password = password or os.getenv("NEO4J_PASSWORD", "neo4j")
        database = database or os.getenv("NEO4J_DATABASE", "neo4j")
        
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        
        # 目标类列表
        self.target_classes = target_classes or [
            "AlipayController",
            "AlipayServiceImpl",
            "OmsPortalOrderServiceImpl",
            "OmsOrderExample"
        ]
        
        # 创建驱动
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        logger.info(f"✅ 已连接到 Neo4j: {uri} (数据库: {database})")
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            logger.info("已关闭 Neo4j 连接")
    
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        执行 Cypher 查询
        
        Args:
            query: Cypher 查询语句
            parameters: 查询参数
            
        Returns:
            查询结果列表
        """
        parameters = parameters or {}
        results = []
        
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters)
            for record in result:
                # 将 Neo4j Record 转换为字典
                record_dict = {}
                for key in record.keys():
                    value = record[key]
                    # 处理节点对象
                    if hasattr(value, 'id') and hasattr(value, 'labels'):
                        record_dict[key] = {
                            'id': value.id,
                            'labels': list(value.labels),
                            'properties': dict(value)
                        }
                    elif isinstance(value, dict):
                        record_dict[key] = value
                    else:
                        record_dict[key] = value
                results.append(record_dict)
        
        logger.debug(f"查询返回 {len(results)} 条结果")
        return results
    
    # ========== 数据提取方法 ==========
    
    def extract_all_data(self) -> Dict[str, Any]:
        """
        提取所有需要的数据
        
        Returns:
            包含所有提取数据的字典:
            {
                "classes": {...},      # 类信息
                "methods": {...},      # 方法信息
                "call_relations": [...],  # 调用关系
                "module_relations": [...] # 模块关系
            }
        """
        logger.info("开始从 Neo4j 提取数据...")
        
        classes_data = self._extract_classes()
        methods_data = self._extract_methods()
        call_relations = self._extract_call_relations()
        module_relations = self._extract_module_relations()
        
        logger.info(f"✅ 数据提取完成: {len(classes_data)} 个类, "
                   f"{len(methods_data)} 个方法, "
                   f"{len(call_relations)} 个调用关系, "
                   f"{len(module_relations)} 个模块关系")
        
        return {
            "classes": classes_data,
            "methods": methods_data,
            "call_relations": call_relations,
            "module_relations": module_relations
        }
    
    def _extract_classes(self) -> Dict[str, Any]:
        """提取类节点信息"""
        classes_data = {}
        
        for class_name in self.target_classes:
            query = """
            MATCH (c:Class)
            WHERE c.name = $class_name
            RETURN c
            LIMIT 1
            """
            results = self.execute_query(query, {"class_name": class_name})
            
            if not results:
                logger.warning(f"未找到类: {class_name}")
                continue
            
            class_node = results[0].get('c')
            if not class_node:
                continue
            
            class_id = class_node.get('id')
            class_props = class_node.get('properties', {})
            
            classes_data[class_name] = {
                "id": class_id,
                "name": class_name,
                "file_id": class_props.get("file_id"),  # 直接从节点属性获取 file_id
                "source_code": class_props.get("source_code", ""),
                "semantic_explanation": self._parse_semantic_explanation(
                    class_props.get("semantic_explanation")
                )
            }
        
        logger.info(f"  ✓ 提取了 {len(classes_data)} 个类")
        return classes_data
    
    def _extract_methods(self) -> Dict[str, Any]:
        """提取方法节点信息"""
        methods_data = {}
        
        for class_name in self.target_classes:
            query = """
            MATCH (c:Class)-[:DECLARES*1..]->(m:Method)
            WHERE c.name = $class_name
            RETURN m
            """
            results = self.execute_query(query, {"class_name": class_name})
            
            for record in results:
                method_node = record.get('m')
                if not method_node:
                    continue
                
                method_id = method_node.get('id')
                method_props = method_node.get('properties', {})
                method_name = method_props.get("name", f"method_{method_id}")
                
                method_key = f"{class_name}.{method_name}"
                methods_data[method_key] = {
                    "id": method_id,
                    "name": method_name,
                    "class_name": class_name,
                    "file_id": method_props.get("file_id"),  # 直接从节点属性获取 file_id
                    "source_code": method_props.get("source_code", ""),
                    "semantic_explanation": self._parse_semantic_explanation(
                        method_props.get("semantic_explanation")
                    )
                }
        
        logger.info(f"  ✓ 提取了 {len(methods_data)} 个方法")
        return methods_data
    
    def _extract_call_relations(self) -> List[Dict[str, Any]]:
        """提取方法调用关系"""
        query = """
        MATCH (c1:Class)-[:DECLARES*1..]->(m1:Method)-[:CALLS]->(m2:Method)<-[:DECLARES*1..]-(c2:Class)
        WHERE c1.name IN $class_names AND c2.name IN $class_names AND c1.name <> c2.name
        RETURN c1, m1, m2, c2
        """
        
        results = self.execute_query(query, {"class_names": self.target_classes})
        
        call_relations = []
        for record in results:
            c1_node = record.get('c1')
            m1_node = record.get('m1')
            m2_node = record.get('m2')
            c2_node = record.get('c2')
            
            if not all([c1_node, m1_node, m2_node, c2_node]):
                continue
            
            c1_name = c1_node.get('properties', {}).get('name', '')
            c2_name = c2_node.get('properties', {}).get('name', '')
            m1_name = m1_node.get('properties', {}).get('name', '')
            m2_name = m2_node.get('properties', {}).get('name', '')
            m1_id = m1_node.get('id')
            m2_id = m2_node.get('id')
            m1_props = m1_node.get('properties', {})
            m2_props = m2_node.get('properties', {})

            call_relations.append({
                "from_class": c1_name,
                "from_method": m1_name,
                "from_method_id": m1_id,
                "from_file_id": m1_props.get("file_id"),  # 从 method 节点属性获取 file_id
                "to_class": c2_name,
                "to_method": m2_name,
                "to_method_id": m2_id,
                "to_file_id": m2_props.get("file_id")  # 从 method 节点属性获取 file_id
            })
        
        logger.info(f"  ✓ 提取了 {len(call_relations)} 个调用关系")
        return call_relations
    
    def _extract_module_relations(self) -> List[Dict[str, Any]]:
        """提取模块层级关系"""
        query = """
        MATCH (p:Package)-[:CONTAINS]->(f:File)-[:DECLARES]->(c:Class)
        WHERE c.name IN $class_names
        OPTIONAL MATCH (b:Block)-[:f2c]->(f)
        RETURN p, f, c, b
        """
        
        results = self.execute_query(query, {"class_names": self.target_classes})
        
        module_relations = []
        class_module_map = {}  # 用于去重（一个 Class 只记录一次）
        
        for record in results:
            p_node = record.get('p')
            f_node = record.get('f')
            c_node = record.get('c')
            b_node = record.get('b')
            
            if not all([p_node, f_node, c_node]):
                continue
            
            package_name = p_node.get('properties', {}).get('name', '')
            file_name = f_node.get('properties', {}).get('name', '')
            class_name = c_node.get('properties', {}).get('name', '')
            block_name = b_node.get('properties', {}).get('name', '') if b_node else None
            block_node_id = b_node.get('properties', {}).get('nodeId') if b_node else None

            # 解析语义说明（仅在存在时解析）
            package_semantic = self._parse_semantic_explanation(
                p_node.get('properties', {}).get('semantic_explanation')
            )
            file_semantic = self._parse_semantic_explanation(
                f_node.get('properties', {}).get('semantic_explanation')
            )
            block_semantic = None
            if b_node:
                block_semantic = self._parse_semantic_explanation(
                    b_node.get('properties', {}).get('semantic_explanation')
                )
            
            # 检查是否已存在该类的模块关系（一个 Class 只记录一次，因为一个 File 只能属于一个 Block）
            if class_name in class_module_map:
                # 已存在则跳过（理论上不应该出现，因为一个 File 只能属于一个 Block）
                continue
            else:
                # 创建新记录
                module_relation = {
                    "class_name": class_name,
                    "file_name": file_name,
                    "package_name": package_name,
                    "block": block_name,  # 单个 Block（可能为 None）
                    "block_node_id": block_node_id,  # Block 节点的 nodeId
                    # 附带语义说明，供文字模板引用 what 字段
                    "package_semantic": package_semantic,
                    "file_semantic": file_semantic,
                    "block_semantic": block_semantic  # 单个 Block 的语义说明
                }
                class_module_map[class_name] = module_relation
                module_relations.append(module_relation)
        
        logger.info(f"  ✓ 提取了 {len(module_relations)} 个模块关系")
        return module_relations
    
    def _parse_semantic_explanation(self, semantic_explanation: Any) -> Optional[Dict[str, Any]]:
        """
        解析 semantic_explanation 属性
        
        Args:
            semantic_explanation: semantic_explanation 属性值（可能是字符串或字典）
            
        Returns:
            解析后的字典，如果解析失败则返回 None
        """
        if semantic_explanation is None:
            return None
        
        # 如果是字符串，尝试解析为 JSON
        if isinstance(semantic_explanation, str):
            try:
                return json.loads(semantic_explanation)
            except json.JSONDecodeError:
                return {"raw": semantic_explanation}
        
        # 如果已经是字典，直接返回
        if isinstance(semantic_explanation, dict):
            return semantic_explanation
        
        return None
    
    # ========== 工具方法 ==========
    
    def get_node_by_property(self, label: str, property_name: str, property_value: str) -> Optional[Dict[str, Any]]:
        """
        根据属性查找节点
        
        Args:
            label: 节点标签
            property_name: 属性名
            property_value: 属性值
            
        Returns:
            节点信息字典，如果不存在则返回 None
        """
        query = f"""
        MATCH (n:{label} {{{property_name}: $value}})
        RETURN n
        LIMIT 1
        """
        results = self.execute_query(query, {"value": property_value})
        if results:
            return results[0].get('n')
        return None
    
    def get_node_properties(self, node_id: int) -> Optional[Dict[str, Any]]:
        """
        根据节点ID获取节点属性
        
        Args:
            node_id: 节点ID
            
        Returns:
            节点属性字典
        """
        query = """
        MATCH (n)
        WHERE id(n) = $node_id
        RETURN n
        """
        results = self.execute_query(query, {"node_id": node_id})
        if results:
            return results[0].get('n')
        return None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

