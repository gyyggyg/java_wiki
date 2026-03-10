from langchain.prompts import PromptTemplate

# 1. 项目介绍提示词
# 输入：root Block的子模块信息
# 输出：项目整体介绍的Markdown文本
PROJECT_INTRO_PROMPT = PromptTemplate(
    input_variables=["modules_info"],
    template="""
你的任务是根据项目的模块信息，生成项目的整体介绍文档。

## 输入数据说明
`modules_info` 包含项目的所有一级模块信息，每个模块包含：
- 模块名称 (name)
- 模块功能说明 (module_explaination)

## 输出要求
生成一个Markdown格式的项目介绍项目的整体定位和目标


**格式要求**：
- 使用 `## 1. 项目介绍` 作为标题
- 不要使用子标题
- 内容要简洁明了，突出重点
- 不要添加代码块，除非确实需要展示代码示例

**重要**：
- 直接输出Markdown内容，不要添加任何前言或解释
- 基于模块信息进行合理推断，不要编造不存在的功能
- 保持客观专业的语气

---
### 模块信息 (`modules_info`):
```
{modules_info}
```
---

直接开始生成项目介绍的Markdown内容：
"""
)

# 2. 项目模块架构提示词
# 输入：root Block的子模块信息
# 输出：模块架构说明的Markdown文本
MODULE_ARCHITECTURE_PROMPT = PromptTemplate(
    input_variables=["modules_info"],
    template="""
你的任务是根据项目的模块信息，生成项目的模块架构说明文档。

## 输入数据说明
`modules_info` 包含项目的所有一级模块信息，每个模块包含：
- 模块名称 (name)
- 模块功能说明 (module_explaination)
- 模块ID (nodeId)

## 输出要求
生成一个Markdown格式的模块架构说明，包含以下内容：

例如，对于一个模块，输出应类似于：
### 标题 [模块名称]
1.  **核心职责和功能**：...
2.  **在整个系统中的作用**：...


**格式要求**：
- 使用 `## 2. 项目模块架构` 作为标题
- 可以使用 `### 2.1`、`### 2.2` 等子标题, 对应各个模块，但是不要使用更多层级的子标题
- 不要使用表格、图表等复杂结构

---
### 模块信息 (`modules_info`):
```
{modules_info}
```
---
【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"markdown": "这里是你输出的文字内容", "mapping": 图中每个小标题信息来源的模块id, 例如{{"2.1":"110",...}}}}
"""
)
