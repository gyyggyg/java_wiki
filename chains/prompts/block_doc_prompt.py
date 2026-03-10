from langchain.prompts import PromptTemplate

# 1. 模块功能概述提示词
BLOCK_OVERVIEW_PROMPT = PromptTemplate(
    input_variables=["block_name", "block_explaination", "file_info"],
    template="""
你的任务是为项目的某一模块生成功能概述文档。

## 输入数据
- **当前模块名称**: {block_name}
- **当前模块说明**: {block_explaination}

## 包含文件说明信息
```
{file_info}
```

## 输出要求
基于当前模块的说明和所有文件的功能，生成完整的模块功能概述，说明：
该模块的核心功能和职责（基于当前模块说明和子文件功能综合分析）


**格式要求**：
- 使用 `## 1. 模块功能概述` 作为标题
- 不要使用子标题
- 内容控制在2-3段，简洁明了
- 基于提供的信息进行合理推断，不要编造不存在的功能

---
直接输出Markdown内容（不要添加任何前言或解释）：
"""
)

# 2. 子模块介绍提示词
CORE_COMPONENTS_PROMPT = PromptTemplate(
    input_variables=["child_modules"],
    template="""
你的任务是为项目模块下的每个类生成介绍文档。

## 输入数据说明
`child_modules` 包含所有子模块信息，每个子模块包含：
- 模块名称 (name)
- 模块功能说明 (module_explaination)
- 模块ID (nodeId)

## 输出要求
为每个子模块生成介绍，说明：
1. 子模块的核心职责
2. 子模块的主要功能
3. 子模块在当前模块中的作用

**格式要求**：
- 使用 `## 2. 子模块介绍` 作为标题
- 使用 `### 2.1 [子模块名称]`、`### 2.2 [子模块名称]` 等作为每个子模块的小标题
- 每个子模块的介绍控制在1-2段
- 不要使用更深层级的标题

---
### 子模块信息 (`child_modules`):
```
{child_modules}
```
---

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"markdown": "这里是你输出的文字内容", "mapping": {{"2.1": "子模块1的nodeId", "2.2": "子模块2的nodeId", ...}}}}
"""
)

MODULE_CHART_PROMPT = PromptTemplate(
    input_variables=["project_information", "relationship"],
    template="""
你是模块架构分析专家, 我已经将一个java项目按照文件功能聚类为模块, 现在我需要你根据我给你的项目介绍, 为我画出该项目的模块架构示意图。
【输入】
代码模块架构'project_information'：{project_information}
关系描述'relationship'：{relationship}

【任务】
1、根据'project_information'里节点的描述，为我设计模块节点，要求子模块/子文件要在父模块图中。
2、根据'relationship'里描述的关系，和'project_information'里的path字段，为我画出模块之间的关系。
3、图中节点的名称必须和'project_information'里的name字段一致，不能修改节点名称。
4、图中节点的层级关系必须和'project_information'里一致，不能修改节点层级。
5、每个节点必须同时显示：
   第一行：name  
   第二行：path  
   两行之间用 `<br/>` 连接。
6、你只展示不属于一个顶层模块的跨模块关系, 不展示同模块内的关系。
【mermaid示例】
flowchart TD
    subgraph A["Admin System Core Suite<br/>mall-admin/src/"]
        A1["Admin System Application Layer<br/>../main/java/com/macro/mall/"]
        A2["Admin Config Management<br/>../config/"]
    end

    subgraph B["Core Utilities and Configuration<br/>mall-common/src/main/java/com/macro/mall/common/"]
    end

    A1 --> B
    A2 --> B

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"mermaid": "这里是输出模块架构图的Mermaid", "mapping": 图中每个节点名称和其在'project_information'里对应id的映射关系，例如{{"A":"1","A1":"2"...}}}}
"""
)

BLOCK_RELATIONSHIP_PROMPT = PromptTemplate(
    input_variables=["cross_module_calls"],
    template="""
你的任务是根据给定的模块和其他模块之间的调用关系，总结出该模块和其他代码模块之间关系的文档，作为文档的第四章节。
你的输出必须以 `## 5. 和其他模块之间的关系` 作为唯一的 H2 标题。其子层级的内容标题应该是5.1，5.1.1这种格式。

## 输入数据说明
`cross_module_calls` 包含模块的调用关系，结构如下：
- 该模块和其他模块之间存在调用关系类的解释
- 该模块和其他模块之间的调用情况
- 其他模块的id和名称

你需要根据 `cross_module_calls` 中提供的调用关系，只生成文字部分，不要做图

解析内容应包括：
5.1 **调用其他模块的关系**：分析该模块调用其他模块的情况，说明调用的其他模块中类的作用和重要性
这下面每一个小标题例如5.1.1, 5.1.2对应`cross_module_calls`中每一个该模块调用的其他模块

5.2 **被其他模块调用的关系**：分析其他模块调用该模块的情况，说明此模块中被调用类的作用和重要性
这下面每一个小标题例如5.2.1, 5.2.2对应`cross_module_calls`中每一个调用该模块的模块

### 注意事项：
1、你只能生成文字解释, 不要生成任何图表
2、你必须严格按照要求的标题格式生成内容
3、返回标题和模块名称的映射关系

---
### 模块间调用信息 (`cross_module_calls`):
```text
{cross_module_calls}
```

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"markdown": "这里是输出md文字内容", "mapping": 你的每个小标题描述的对象模块id例如{{"5.1.1":"111","5.2.1":"2"...}}}}
"""
)