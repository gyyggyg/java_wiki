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

你的任务是根据用户的查询（query），结合层级关系和语义解释，筛选出每个链条上最相关的Block节点（功能模块）。

【输入信息说明】
1. **query**: 用户的查询问题或需求。
2. **relation**: 展示了从底层文件到顶层Block的层级归属关系链条（例如：File A <- Block a <- Block b <- Root）。
   **注意**：`relation`可能包含多条链条。我们需要针对**每一条**链条，从中找出一个最相关的Block节点。
3. **all_information**: 包含链条上各个Block节点的详细信息，格式通常包含 `node_id` (节点ID), `name` (名称), `semantic_explanation` (语义解释)。

【筛选规则】
1. **理解意图**: 仔细阅读 `all_information` 中的语义解释，找出功能描述能回答 `query` 的 Block。
2. **注意事项**: 每个链条第一个节点为File节点，最后一个为root节点，你要筛选返回的是他们中间的Block节点，而不能是这两个节点之一。
3. **避免父子**: 你最后返回的所有Block列表, 不应出现在某一链条上有上下级关系的多个Block，如果链条1所选Block a是链条2 所选Block b的下级，应该统一都为Block b.
4. **链条筛选**: 针对输入的每一条 `relation` 链条，必须选出该链条上一个最相关的 Block。

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
请严格按照以下JSON格式返回每个链条上和query最相关的Block节点的ID列表，**不要包含任何其他解释、前言或Markdown标记**：

{{"block_id": [nodeId1, nodeId2, ...],"reason":"选择每个nodeId对应的block节点的原因，可以多条原因，用逗号分隔"}}

示例输出：
{{"block_id": [101, 205],"reason":"选择101号block节点的原因是：101号block节点是订单提交的入口，205号block节点是订单提交的出口"}}
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
2. **语义分析**: 阅读 `all_information` 中每个文件的语义解释，只要跟用户query相关，能帮助用户理解需求和使用代码就选入。
    - 如果文件实现了 `query` 中提到的功能，选入。
    - 如果文件定义了 `query` 中涉及的核心数据模型，选入。

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

{{"file_id": [fileId1, fileId2, ...],"reason":"选择/不选择每个nodeId对应的file节点的原因，可以多条原因，用逗号分隔，要给出每一个文件选/不选的解释"}}

示例输出：
{{"file_id": [3001, 4052, 5009], ,"reason":"选择3001，4052，5009因为其功能描述字段xxx和用户问题高度相关，不选择91因为其功能为xx, 不选择92原因是xx"}}
"""
)

FETCH_BLOCK1_PROMPT = PromptTemplate(
    input_variables=["query", "relation", "all_information"],
    template="""
你是一个精通Java项目架构的智能助手。
【项目背景】
我已将一个Java项目切分为Class/Enum/Interface/File/Method/Field等类型的代码片段, 每个片段对应一个Neo4j节点。
相关的File节点进行了聚类，在上层有个Block类型的节点。Block和File节点的关系是f2c。

你的任务是根据用户的查询（query），从前三层Block节点（root -> 第一层 -> 第二层）中筛选出与query最相关的Block节点。

【输入信息说明】
1. **query**: 用户的查询问题或需求。
2. **relation**: 展示了前三层Block的父子关系，格式为 `father_id : child_id_list`。这表示某个父Block节点包含哪些子Block节点。
   **注意**：这里只包含前三层Block的层级关系（root层、第一层、第二层）。
3. **all_information**: 包含前三层Block节点的详细信息，格式为 `id:{{nodeId}},name:{{name}},semantic_explanation:{{semantic_explanation}}`。

【筛选规则】
1. **理解意图**: 仔细阅读 `all_information` 中每个Block的语义解释，找出功能描述能回答 `query` 的 Block。
2. **层级范围**: 只从前三层Block（root、第一层、第二层）中选择，不包括更深层的Block。
3. **多选允许**: 可以选择多个相关Block节点（不唯一），只要它们的功能描述与query相关即可。
4. **语义匹配**: 优先选择语义解释与用户query高度相关的Block节点。

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
请严格按照以下JSON格式返回与query最相关的Block节点的ID列表，**不要包含任何其他解释、前言或Markdown标记**：

{{"node_id": [nodeId1, nodeId2, ...],"reason":"选择每个nodeId对应的block节点的原因，可以多条原因，用逗号分隔"}}

示例输出：
{{"node_id": [101, 205],"reason":"选择101号block节点的原因是：101号block节点是订单提交的入口模块，205号block节点是订单提交的出口模块"}}
"""
)

FETCH_BLOCK2_PROMPT = PromptTemplate(
    input_variables=["query", "relation", "all_information"],
    template="""
你是一个精通Java项目架构的智能助手。
【项目背景】
我已将一个Java项目切分为Class/Enum/Interface/File/Method/Field等类型的代码片段, 每个片段对应一个Neo4j节点。
相关的File节点进行了聚类，在上层有个Block类型的节点。Block和File节点的关系是f2c。

你的任务是根据用户的查询（query），从某个Block的完整子树中选择与query最相关的Block节点，**但必须避免选择具有直系关系（父子关系）的Block**。

【输入信息说明】
1. **query**: 用户的查询问题或需求。
2. **relation**: 展示了以某个Block节点为顶点的完整子树结构，包含该子树中所有Block节点的父子关系。
   格式示例：`下面是以id为{{nodeId}}顶点的树的信息：\nid为{{nodeId}}的节点可以划分为子节点{{child_blocks}}\n...`
   **注意**：`relation` 描述了整个子树的结构，包括所有层级的父子关系。
3. **all_information**: 包含子树中所有Block节点的详细信息，格式为 `id:{{nodeId}},name:{{name}},semantic_explanation:{{semantic_explanation}}`。

【筛选规则】
1. **理解意图**: 仔细阅读 `all_information` 中每个Block的语义解释，找出功能描述能回答 `query` 的 Block。
2. **避免直系关系（关键规则）**: 
   - 如果选择的Block中有父子关系（直系关系），**必须只保留父节点（顶层节点）**，删除子节点。
   - 例如：如果block a有两个子block c和d，block c有子block e和f，block d有子block g和h。
     如果模型判断应该选择block c和block e，那么block c和block e是直系关系（父子关系），
     应该只保留顶层的block c，删除block e。
   - 但如果选择的是block e和block h，它们不是直系关系（它们分别属于不同的分支），可以都保留。
3. **树结构理解**: 必须理解 `relation` 中描述的树结构，识别哪些Block之间存在父子关系。
4. **语义匹配**: 优先选择语义解释与用户query高度相关的Block节点。

【输入内容】
用户查询 (query):
```
{query}
```

子树结构关系 (relation):
```
{relation}
```

Block详细信息 (all_information):
```
{all_information}
```

【输出要求】
请严格按照以下JSON格式返回与query最相关的Block节点的ID列表，**不要包含任何其他解释、前言或Markdown标记**：

{{"block_id": [nodeId1, nodeId2, ...],"reason":"选择每个nodeId对应的block节点的原因，可以多条原因，用逗号分隔。如果排除了某些直系关系的子节点，请说明原因"}}

示例输出：
{{"block_id": [101, 205],"reason":"选择101号block节点的原因是：101号block节点是订单提交的入口模块。选择205号block节点的原因是：205号block节点是订单提交的出口模块。未选择101的子节点103，因为103与101是直系关系，已保留父节点101"}}
"""
)