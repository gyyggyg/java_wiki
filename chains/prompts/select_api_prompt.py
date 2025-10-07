from langchain.prompts import PromptTemplate

API_FILE_PROMPT = PromptTemplate(
    input_variables=["node_introduction"],
    template="""
我已将一个Java项目切分为Class/Enum/Interface/File/Method/Field等类型的代码片段, 每个片段对应一个Neo4j节点。
请你按以下规则分析，筛选出执行“对外提供接口/API服务功能”(用户角度的接口)的片段, 并按指定格式返回:
【API片段判断规则】
1. 代码逻辑需符合:语义解释包含“对外服务契约”“API接口”等类似功能描述。
2. 排除内部片段:若node_introduction提到“内部辅助”“仅包内使用”, 需要排除。
3. "node_introduction"包含某些节点的名称，包括代码片段的名字，解释等信息。

下面是"node_introduction"的内容
```
{node_introduction}
```
请分析这些代码片段的功能，选择功能是对项目外界提供接口/API服务的代码片段:

**重要：请严格按照以下JSON格式返回，不要添加任何其他文字说明:**

{{"node_id":[nodeId1, nodeId2, nodeId3]}}

示例输出：
{{"node_id":[111, 222, 333]}}
"""
)

API_PROMPT = PromptTemplate(
    input_variables=["readme_content", "all_content"],
    template="""
你的任务是分析一个Java项目的对外提供接口/API服务功能(用户角度的接口)，生成相应文档。

"readme_content"是Java项目中的README.md文件的内容, "all_content"是该项目可能包含与对外提供接口/API服务功能的所有代码片段的内容, 包含代码片段名和代码片段具体内容。
下面是"readme_content"的内容
```
{readme_content}
```
下面是"all_content"的内容
```
{all_content}
```
 **任务:**
    请结合以上两份输入，进行全面的分析：
    1.  **对外提供接口/API服务功能分析:说明此java项目对外提供的服务都包括哪些。
    2.  **对外提供接口/API服务数据结构说明和使用举例:说明此java项目对外提供的服务都包括哪些数据结构, 并举例说明如何使用这些数据结构。


    **输出要求:**
1. 必须以 frontmatter 开始，格式如下：
---
sidebar_position: 2
title: '2. 对外提供接口说明文档'
---

2. frontmatter 后直接跟正文内容，使用 `# 2. 对外提供接口说明文档` 作为唯一的H1主标题
3. 子层级标题使用 1, 1.1 格式
4. 内容直接是Markdown格式, 不要包含任何前言或解释, 直接输出Markdown格式
"""

)