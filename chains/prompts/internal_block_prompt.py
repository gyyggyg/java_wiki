from langchain.prompts import PromptTemplate

# 1. 模块功能概述提示词
INTERNAL_BLOCK_OVERVIEW_PROMPT = PromptTemplate(
    input_variables=["block_name", "block_explaination", "child_modules_info"],
    template="""
你的任务是为项目的中间层模块生成功能概述文档。

## 输入数据
- **当前模块名称**: {block_name}
- **当前模块说明**: {block_explaination}

## 子模块信息
```
{child_modules_info}
```

## 输出要求
基于当前模块的说明和所有子模块的功能，生成一个简洁的模块功能概述，说明：
该模块的核心功能和职责（基于当前模块说明和子模块功能综合分析）


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
INTERNAL_BLOCK_CHILDREN_PROMPT = PromptTemplate(
    input_variables=["child_modules"],
    template="""
你的任务是为项目模块的子模块生成介绍文档。

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