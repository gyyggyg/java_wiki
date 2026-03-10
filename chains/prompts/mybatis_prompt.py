from langchain.prompts import PromptTemplate

# 1. 模块功能概述提示词
MYBATIS_METHOD_PROMPT = PromptTemplate(
    input_variables=["xml_content", "interface_code", "characteristic_info"],
    template="""
你的任务是为一个java项目中通过Mybatis架构实现的方法生成md的介绍内容。

## 输入数据
- 方法在xml文件里的代码: {xml_content}
- 方法所属接口代码: {interface_code}
- 承载方法属性数据类的代码: {characteristic_info}


## 输出要求
包含下面四个内容：
- 功能说明 — 一句话讲清楚做什么
- 字段表格 — 用表格直观展示涉及哪些字段及含义
- 效果示例 — 用具体数据展示运行时实际生成的样例，这是最能帮助理解的部分
- 注意事项 — 标注特殊行为，防止误用，仅当方法存在容易误用的特殊行为时才输出


**格式要求**：
- 每个板块内容标题使用子弹点开头，标题后面换行再写内容
- 不要使用任何序号标题或者子标题
- 不要作图片，直接用文字和表格说明
- 基于提供的信息进行合理推断，不要编造不存在的功能

---
【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"markdown": "这里是你输出的文字内容"}}
"""
)