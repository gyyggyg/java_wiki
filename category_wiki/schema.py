"""节点 schema — 对齐总揽.json 的 markdown_content 树形结构

每个节点三种类型:
- SectionNode: 有 title + nested content 列表
- TextNode: 叶子 markdown 文本
- ChartNode: 叶子 mermaid 图

所有节点都带 neo4j_id + neo4j_source 平行字典:
  neo4j_id[key]     -> nodeId (str) 或 list[str]
  neo4j_source[key] -> 对应 Neo4j 节点 name (str) 或 list[str]
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Union


NodeIdValue = Union[str, List[str]]


@dataclass
class TextNode:
    content: Dict[str, Any] = field(default_factory=lambda: {"markdown": ""})
    source_id: List[Any] = field(default_factory=list)
    neo4j_id: Dict[str, NodeIdValue] = field(default_factory=dict)
    neo4j_source: Dict[str, NodeIdValue] = field(default_factory=dict)
    id: str = ""
    type: str = "text"

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "id": self.id,
            "content": self.content,
            "source_id": self.source_id,
            "neo4j_id": self.neo4j_id,
            "neo4j_source": self.neo4j_source,
        }


@dataclass
class ChartNode:
    content: Dict[str, Any] = field(default_factory=lambda: {"mermaid": "", "mapping": {}})
    source_id: List[Any] = field(default_factory=list)
    neo4j_id: Dict[str, NodeIdValue] = field(default_factory=dict)
    neo4j_source: Dict[str, NodeIdValue] = field(default_factory=dict)
    id: str = ""
    type: str = "chart"

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "id": self.id,
            "content": self.content,
            "source_id": self.source_id,
            "neo4j_id": self.neo4j_id,
            "neo4j_source": self.neo4j_source,
        }


@dataclass
class SectionNode:
    title: str = ""
    content: List[Any] = field(default_factory=list)  # 子节点: Section/Text/Chart
    neo4j_id: Dict[str, NodeIdValue] = field(default_factory=dict)
    neo4j_source: Dict[str, NodeIdValue] = field(default_factory=dict)
    id: str = ""
    type: str = "section"

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "id": self.id,
            "title": self.title,
            "content": [c.to_dict() if hasattr(c, "to_dict") else c for c in self.content],
            "neo4j_id": self.neo4j_id,
            "neo4j_source": self.neo4j_source,
        }


AnyNode = Union[SectionNode, TextNode, ChartNode]
