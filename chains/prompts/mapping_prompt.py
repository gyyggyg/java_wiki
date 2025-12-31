from langchain.prompts import PromptTemplate


GENERATE_JSON_PROMPT = PromptTemplate(
    input_variables=["target","related_context"],
    template="""
你是代码语义分析专家，需要基于我提供给你的输出任务和相关信息，输出分别包含我需要的markdown内容和对应内容信息来源的JSON。严格遵循以下原则：
### 输入信息
1. **输出内容任务**  
   ```
   {target}
   ```
2. **相关信息**  
   ```
   {related_context}
   ```
---
### 输出格式
你需要输出两个JSON数组，分别是`markdown_content`和`source_id`，严格按照下面的格式要求输出：
```markdown_content的格式示例
[
    {{
        "type":"section",
        "id":"S1",
        "title":"# 6.数据结构说明",
        "content":[
            {{
                "type":"text",
                "id":"S2",
                "content":{{
                    "markdown":"下面是内容"
                }},
                "source_id":["566"]
            }},
            {{
                "type":"section",
                "id":"S3",
                "title":"## 6.1 标题",
                "content":[]
            }}
        ]
    }},
    {{
        "type":"section",
        "id":"S4",
        "title":"# 7. 标题",
        "content":[
            {{
                "type":"chart",
                "id":"S5",
                "content":{{
                    "mapping":{{"A1":"111"}},
                    "mermaid":"flowchart TD\\n    A1[\"节点1\"]\\n    A2[\"节点2\"]\\n    B1[\"节点3\"]\\n    A1 --> A2\\n    A2 --> B1\\n    style A1 fill:#0af,stroke:#036,stroke-width:4px"
                }},
                "source_id":["566"]
            }}
        ]
    }}
]
```
#### markdown_content的json字段说明
`type`: 下面markdown内容的类型，支持`section`（章节）、`text`（文本内容）、`chart`（图表）  
`id`: 板块唯一标识符，**必须全局唯一**
`title`: 章节标题，仅当`type`为`section`时需要
`content`: 章节内容数组，包含子章节、文本或图表
- 当`type`为`text`时，`content`包含字段`markdown`，表示文本内容的Markdown格式字符串
- 当`type`为`chart`时，`content`包含字段：
  - `mapping`: 对象，表示图中每个节点ID和source_id的映射关系（如 {{"A1":"111", "B2":"112"}}）
  - `mermaid`: 字符串，使用Mermaid语法描述的图表内容
`source_id`: 字符串数组，表示该内容引用的信息来源标识符列表（如 ["566", "111"]）
**重要说明**：
- markdown_content 中的 `source_id` 是引用（指针），指向 source_id 数组中的具体定义
- 所有引用的 source_id 都必须在顶层 source_id 数组的json中定义
- 所有被用到的文件，都要在source_id中定义。

```source_id的json格式示例
[
    {{
        "source_id":"111",
        "name":"/path/to/file1.java",
        "lines": [
            "80-100"
        ]
    }},
    {{
        "source_id":"566",
        "name":"/path/to/file2.java",
        "lines": [
            "8-10", "11-20"
        ]
    }}
]
```
#### source_id的json字段说明
`source_id`: 信息来源标识符（字符串），与 markdown_content 中引用的 source_id 一一对应
`name`: 信息来源文件名称（完整路径），必须是 related_context 中提供的文件名
`lines`: 字符串数组，表示该内容对应的源代码行号范围，格式如 ["8-10", "15", "20-25"]
如果某一板块内容来自文件某几行，而另一板块来自该文件另外行数或者全文，这应该是两个不同的 source_id 条目
---

---

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"markdown_content": "[]", "source_id": "[]"}}
"""
)