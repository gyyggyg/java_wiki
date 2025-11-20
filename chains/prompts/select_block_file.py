from langchain.prompts import PromptTemplate


# =============================================================================
# 1. Block 筛选提示词 (基于 Query 和 聚类链条)
# =============================================================================
SELECT_BLOCK_PROMPT = PromptTemplate(
    input_variables=["query", "relation", "all_information"],
    template="""
你是一个精通Java项目架构的智能助手。
【项目背景】
我已将一个Java项目切分为Class/Enum/Interface/File/Method/Field等类型的代码片段, 每个片段对应一个Neo4j节点。
相关的File节点进行了聚类，在上层有个Block类型的节点。Block和File节点的关系是f2c。

你的任务是根据用户的查询（query），结合层级关系和语义解释，筛选出最相关的Block节点（功能模块）。

【输入信息说明】
1. **query**: 用户的查询问题或需求。
2. **relation**: 展示了从底层文件到顶层Block的层级归属关系链条（例如：File A <- Block a <- Block b <- Root）。
   **注意**：`relation`可能包含多条链条。我们需要针对**每一条**链条，从中找出一个最相关的Block节点。
3. **all_information**: 包含链条上各个Block节点的详细信息，格式通常包含 `node_id` (节点ID), `name` (名称), `semantic_explanation` (语义解释)。

【筛选规则】
1. **理解意图**: 分析用户的 `query` 到底在问什么（是具体的业务逻辑、数据结构，还是宏观的架构）。
2. **链条筛选**: 针对输入的每一条 `relation` 链条，必须且只能选出该链条上一个最相关的 Block。
3. **结合层级**: 利用 `relation` 判断 Block 的层级。通常情况下，中间层级的 Block (如业务模块) 比 根节点(Root) 或 过于底层的通用 Block 更具区分度。
4. **语义匹配**: 仔细阅读 `all_information` 中的语义解释，找出功能描述与 `query` 高度重合的 Block。

【输入内容】
用户查询 (query):
```
{query}
```

层级关系 (relation):
```
{relation}
```

Block详细信息 (all_information):
```
{all_information}
```

【输出要求】
请严格按照以下JSON格式返回最相关的Block节点的ID列表，**不要包含任何其他解释、前言或Markdown标记**：

{{"block_id": [nodeId1, nodeId2, ...]}}

示例输出：
{{"block_id": [101, 205]}}
"""
)

# =============================================================================
# 2. File 筛选提示词 (基于 Query 和 候选文件语义)
# =============================================================================
SELECT_FILE_PROMPT = PromptTemplate(
    input_variables=["query", "all_information"],
    template="""
你是一个精通Java代码理解的智能助手。我将提供一组Java代码文件（File节点）的详细信息。
你的任务是根据用户的查询（query），从这些候选文件中筛选出最能回答或解决用户问题的相关文件。

【输入信息说明】
1. **query**: 用户的查询问题。
2. **all_information**: 包含候选文件的详细信息，格式通常包含 `node_id` (节点ID), `name` (文件名), `semantic_explanation` (语义解释/功能摘要)。

【筛选规则】
1. **精准匹配**: 用户的 `query` 可能涉及具体的类名、方法功能或业务流程。
2. **语义分析**: 阅读 `all_information` 中每个文件的语义解释。
    - 如果文件实现了 `query` 中提到的功能，选入。
    - 如果文件定义了 `query` 中涉及的核心数据模型，选入。
    - 忽略那些仅提及相关词汇但实际功能无关的工具类或通用类（除非 Query 明确询问工具类）。
3. **宁缺毋滥**: 只返回真正相关的文件 ID。

【输入内容】
用户查询 (query):
```
{query}
```

文件详细信息 (all_information):
```
{all_information}
```

【输出要求】
请严格按照以下JSON格式返回最相关的File节点的ID列表，**不要包含任何其他解释、前言或Markdown标记**：

{{"file_id": [fileId1, fileId2, ...]}}

示例输出：
{{"file_id": [3001, 4052, 5009]}}
"""
)