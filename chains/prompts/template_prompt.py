from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI

# 1. 组件概述与职责
# 输入：模块的完整信息 (block_summary)，包括子文件、语义解释、背景。
# 目标：生成模块的功能、设计理念和职责范围的文字介绍。
OVERVIEW_PROMPT = PromptTemplate(
    input_variables=["block_summary", "module_name", "sidebar_position", "title_prefix"],
    template="""
你的任务是为软件模块撰写一份详细的组件概述与职责文档，作为 Docusaurus 文档。

输出要求：
1. 必须以 frontmatter 开始，格式如下（注意：sidebar_position 必须是数字）：
---
title: '{title_prefix} {module_name}'
sidebar_position: {sidebar_position}
---
2. frontmatter 后使用 `# {title_prefix} {module_name}` 作为唯一的H1主标题
3. 使用 `## 1 板块概述与职责` 作为唯一的H2标题
4. 子层级标题使用 1.1，1.1.1 格式

**重要：不要在文档中添加任何多余的代码块标记（```），只在需要展示代码时才使用。**

MDX/Markdown 安全规则（必须遵守）：
- 正文禁止出现裸露尖括号 < 和 >。比较符与占位符必须使用反引号或实体：如 `<=`、`>=`、`<=>`、`\\<partition\\>`、`&lt;`、`&gt;`。
- 头文件、路径、命令、占位符一律使用反引号或代码块包裹（例如 `\\<asm/errno.h\\>`、`/sys/fs/ext4/\\<partition\\>/mb_stats`）。
- 表格单元格同样适用上述规则。
- Mermaid 图必须放在 mermaid 代码块内；图内可正常使用 < 和 >。

## 输入数据说明
`block_summary` 包含模块的语义信息，结构如下：
- 模块名称
- 子文件的 semantic_explanation（语义解释，包括 What、Why、key_components 等）
- 子文件的 background（背景信息）

**注意**：此处不包含源代码，请基于语义解释和背景信息来分析模块的职责和功能。

请专注于以下几点：
1.  **核心功能**：该组件最主要的功能是什么？它解决了什么问题？
2.  **设计目的**：从代码结构和概要信息推断，设计者为什么要创建这个组件？它的设计哲学是什么？
3.  **职责边界**：明确该组件负责什么，不负责什么。
4.  **与其他组件的关联**：如果信息中包含"跨模块调用信息"，请结合该内容，精准说明组件如何与系统中的其他顶层模块交互。
---
### 模块信息 (`block_summary`):
```text
{block_summary}
```
---
直接开始生成"组件概述与职责"部分的Markdown文档内容。你的输出必须直接是文档内容，不要包含任何前言、自我介绍或解释性文字。

**🚨 输出格式严格要求：**
- 直接以frontmatter（---）开始
- 不要在frontmatter前后添加任何```标记
- 只有在展示具体代码时才使用代码块标记
"""
)