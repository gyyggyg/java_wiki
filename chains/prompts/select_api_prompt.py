from langchain.prompts import PromptTemplate


API_FILE_PROMPT = PromptTemplate(
    input_variables=["file_introduction"],
    template="""
现在我有一个Java项目。
请你按以下规则分析，筛选出执行“此项目对外提供调用/API服务功能”的文件, 例如为用户调用项目，使用项目提供的函数/API服务, 并按指定格式返回:
【API片段判断规则】
1. 文件逻辑需符合:语义解释包含“为用户提供服务”“API”等类似功能描述。
2. 你还需要找到实现这些接口的文件，帮助更全面的理解和使用这些接口。
2. 排除内部功能文件:若file_introduction仅提到“内部辅助”“仅包内使用”, 需要排除。
3. "file_introduction"包含文件的名字，解释等信息。

下面是"file_introduction"的内容
```
{file_introduction}
```
请分析这些文件的功能，选择功能是对项目外界提供调用/API服务的文件:

**重要：请严格按照以下JSON格式返回，不要添加任何其他文字说明:**

{{"file_id":[fileId1, fileId2, fileId3]}}

示例输出：
{{"file_id":[111, 222, 333]}}
"""
)

API_CLASS_PROMPT = PromptTemplate(
    input_variables=["node_introduction"],
    template="""
我已将一个Java项目切分为Class/Enum/Interface/File/Method/Field等类型的代码片段, 每个片段对应一个Neo4j节点。
请你按以下规则分析，筛选出执行“此项目对外提供调用/API服务功能”的片段, 例如为用户调用项目，使用项目提供的函数/API服务, 并按指定格式返回:
【API片段判断规则】
1. 代码逻辑需符合:语义解释包含“为用户提供服务”“API”等类似功能描述。
2. 你还需要找到实现这些接口的代码片段类，帮助更全面的理解和使用这些接口。
3. 排除内部功能片段:若node_introduction仅提到“内部辅助”“仅包内使用”, 需要排除。
4. "node_introduction"包含某些节点的名字，解释等信息。

下面是"node_introduction"的内容
```
{node_introduction}
```
请分析这些代码片段的功能，选择功能是对项目外界提供调用/API服务的代码片段:

**重要：请严格按照以下JSON格式返回，不要添加任何其他文字说明:**

{{"node_id":[nodeId1, nodeId2, nodeId3]}}

示例输出：
{{"node_id":[111, 222, 333]}}
"""
)

API_1_PROMPT = PromptTemplate(
    input_variables=["readme_content", "all_content"],
    template="""
你的任务是分析一个Java项目的对外提供调用/API接口服务功能(用户角度的接口)，生成相应文档的前两个章节。

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
    请结合以上两份输入，进行此java项目对外提供调用/接口的全面分析，且所有类名、URL、字段名必须与源码大小写完全一致。：
    第一章节.  **功能分析:此java项目对外提供的服务都包括哪些, 这些服务都由哪些类组成，这些服务之间的关系是什么
    第二章节.  **调用类说明:说明此java项目对外提供的服务分别来自于什么类, 类的功能是什么，这些类所属的文件名字是什么, 调用类的package是什么。


    **输出要求:**
1. 使用 `# 2. 对外提供接口说明文档` 作为唯一的H1主标题
2. 以 `## 1. 功能分析` `## 2. 调用类说明`作为唯二的 H2 标题。其子层级的内容标题应该分别是1.1, 1.1.1, 2.1, 2.1.1这种格式。
3. 内容直接是Markdown格式, 不要包含任何前言或解释, 直接输出Markdown格式
4. 尽量使用表格＋文字描述等更美观的格式，不要使用子弹列表。
"""

)

API_2_PROMPT = PromptTemplate(
    input_variables=["readme_content", "all_content", "exist_content"],
    template="""
你的任务是分析一个Java项目的对外提供调用/API接口服务功能(用户角度的接口)，生成相应文档的第三章节。

"readme_content"是Java项目中的README.md文件的内容, "all_content"是该项目可能包含与对外提供接口/API服务功能的所有代码片段的内容, 包含代码片段名和代码片段具体内容。
"exist_content"是现在已经生成的第一章第二章的内容。
下面是"readme_content"的内容
```
{readme_content}
```
下面是"all_content"的内容
```
{all_content}
```
下面是"exist_content"的内容
```
{exist_content}
```
**任务:**
    请结合以上两份输入，要求给出全部涉及的类和可以对外提供服务的函数介绍，不能省略，用以提供完整指导：
    第三章节.  **数据结构说明:针对"exist_content"涉及到的所有类，详细说明各个类包括的哪些函数提供对外服务，例如1.完整类名和方法签名 2.请求/响应参数格式 3.各种函数操作的含义是什么。



    **输出要求:**
1. 以 `## 3. 数据结构说明` 作为唯一的 H2 标题。其子层级的内容标题应该分别是3.1, 3.1.1这种格式。
2. 内容直接是Markdown格式, 不要包含任何前言或解释, 直接输出Markdown格式。
3. 你只负责生成第三章的内容，不要重复第一第二章的内容。
4. 尽量使用表格＋文字描述等更美观的格式，不要使用子弹列表。
"""

)