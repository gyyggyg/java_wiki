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
3. **all_information**: 包含前=Block节点的详细信息，格式为 `id:{{nodeId}},name:{{name}},semantic_explanation:{{semantic_explanation}}`。

【筛选规则】
1. **理解意图**: 仔细阅读 `all_information` 中每个Block的语义解释，找出功能描述能回答 `query` 的 Block。
2. **多选允许**: 可以选择多个相关Block节点（不唯一）。
3. **避免直系关系**: 当同时选中了直系父节点和子节点，则只保留父节点。

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
3. **all_information**: 包含子树中所有Block节点的详细信息，格式为 `id:{{nodeId}},name:{{name}},semantic_explanation:{{semantic_explanation}}`。

【筛选规则】
1. **理解意图**: 仔细阅读 `all_information` 中每个Block的语义解释，找出功能描述能回答 `query` 的 Block。
2. **避免直系关系（关键规则）**:
   - 如果选择的Block中有父子关系（直系关系），**必须只保留父节点（顶层节点）**，删除子节点。。
3. **树结构理解**: 必须理解 `relation` 中描述的树结构，识别哪些Block之间存在父子关系。
4. **允许弃选**: 如果某个Block树上的节点全部与用户query无关，可以弃选，返回空列表。

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
请严格按照以下JSON格式返回与query相关的Block节点的ID列表，**不要包含任何其他解释、前言或Markdown标记**：

{{"block_id": [nodeId1, nodeId2, ...],"reason":"选择每个nodeId对应的block节点的原因，可以多条原因，用逗号分隔。如果排除了某些直系关系的子节点，请说明原因"}}

示例输出：
{{"block_id": [101, 205],"reason":"选择101号block节点的原因是：101号block节点是订单提交的入口模块。选择205号block节点的原因是：205号block节点是订单提交的出口模块。未选择101的子节点103，因为103与101是直系关系，已保留父节点101"}}
"""
)

# =============================================================================
# 3. 从下往上搜索的提示词模板
# =============================================================================
JUDGE_BLOOK_PROMPT = PromptTemplate(
###初始语义筛选底层Block节点
    input_variables=["query", "block_info","files_info"],
    template="""
你是一个代码分析专家。用户正在查询代码库中的相关信息。代码文件已经按照功能划分为模块，每个功能模块下包含多个文件。

【用户问题】
{query}

【当前模块和其所包含文件的信息】
- block_info: {block_info}
- files_info: {files_info}

【任务】
判断此模块能否直接回答用户的query或者作为能回答用户query的一部分。

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"relevant": "true"/"false", "reason": "说明判断理由。如果判断为true，则reason中要说明此模块如何回答用户的query或此模块可以作为回答用户query模块的子模块。如果判断为false，则reason中要说明此模块不能回答用户的query的原因。"}}
"""
)

JUDGE_BLOCK_LEVEL_PROMPT = PromptTemplate(
###判断取到什么层级的Block节点作为回答用户query的入口节点
    input_variables=["query", "parent_info","select_blocks_info", "all_child_blocks_info"],
    template="""
你是一个代码分析专家。用户正在查询代码库中的相关信息。代码文件已经按照功能划分为模块，每个功能模块下包含多个模块。
【任务】
select_blocks_info是我已经确定能回答用户query的block的信息，但是我还不确定其能否作为回答用户query的入口节点。
请你根据all_child_blocks_info里已选中节点及其兄弟的解释, 和"parent_info"其父节点的解释。
判断作为回答用户的query入口节点，是使用已选的节点，还是使用他们的父节点。

【用户问题】
{query}

【当前模块和其所包含文件的信息】
- parent_info: {parent_info}
- select_blocks_info: {select_blocks_info}
- all_child_blocks_info: {all_child_blocks_info}

【判断依据】
1、如果已选中节点占父节点孩子中大多数或者全部，则使用父节点。
2、如果未选中的兄弟节点也是设计来回答或者部分回答用户query的，则使用父节点。
3、如果已选中节点占少数且兄弟节点和回答query基本无关，则使用已选中节点。

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"judgement": "now"/"parent", "reason": "说明判断理由。now表示使用已选的节点，parent表示使用其父节点。"}}
"""
)

# # 判断root直连File的相关性
# JUDGE_ROOT_FILE_PROMPT = PromptTemplate(
#     input_variables=["query", "file_info"],
#     template="""
# 你是一个代码分析专家。用户正在查询代码库中的相关信息。

# 【用户问题】
# {query}

# 【当前文件信息】
# - file_info: {file_info}

# 【任务】
# 判断该文件是否能够帮助回答用户的问题。

# 【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
# {{"relevant": true/false, "reason": "说明判断理由"}}

# 【判断标准】
# - 文件的功能、职责是否与问题直接相关
# - 文件中可能包含的信息是否能回答问题
# - 保持严格标准，不确定时返回false
# """
# )

# # 判断Block下File的相关性（Layer 0）
# JUDGE_FILES_IN_BLOCK_PROMPT = PromptTemplate(
#     input_variables=["query", "block_info", "files_info"],
#     template="""
# 你是一个代码分析专家。代码文件已经按照功能划分为模块，每个功能模块下包含多个文件。

# 【用户问题】
# {query}

# 【当前模块（Block）信息】
# - block_info: {block_info}

# 【该Block下的所有文件】
# {files_info}

# 【任务】
# 分析该Block下的所有文件，判断哪些文件能够帮助回答用户的问题。

# 【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
# {{"relevant_files":[{{"id":文件id, "reason": 判断理由}},...], "irrelevant_files":[{{"id":文件id, "reason": 判断理由}},...]}}

# 【判断标准】
# 1. 考虑文件的功能、模块说明与问题的相关性
# 2. 保持严格标准，不确定时标记为不相关，但也要给出不相关的理由
# 3. relevant_files数组必须包含所有和query相关文件，不能遗漏
# 4. irrelevant_files数组必须包含所有和query不相关文件，不能遗漏
# 5. relevant_files和irrelevant_files可以为空，但是不能有交集

# 【注意】
# - id必须是整数类型
# - reason要具体说明相关或不相关的原因
# """
# )

# # 判断兄弟Block的相关性（Layer N）
# JUDGE_SIBLING_BLOCKS_PROMPT = PromptTemplate(
#     input_variables=["query", "parent_info", "known_children_info", "sibling_blocks_info"],
#     template="""
# 你是一个代码分析专家。用户正在查询代码库中的相关信息。代码文件已经按照功能划分为模块，每个功能模块下包含多个文件。

# 【用户问题】
# {query}

# 【父Block信息】
# - parent_info: {parent_info}

# 【该父Block下已确认相关的子Block】
# {known_children_info}

# 【该父Block下所有兄弟Block信息】
# {sibling_blocks_info}

# 【任务】
# 基于已确认相关的子Block，判断其余兄弟Block中哪些也能帮助回答用户的问题。

# 【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
# {{"relevant_siblings": [{{"id": block id, "reason": 判断理由}}, ...],"irrelevant_siblings": [{{"id": block id, "reason": 判断理由}}, ...]}}

# 【判断标准】
# 1. 考虑兄弟Block与已选Block的协作关系
# 2. 判断是否能补充回答用户问题
# 3. 关注功能上的相关性
# 4. relevant_siblings数组必须包含所有和query相关兄弟Block，不能遗漏
# 5. irrelevant_siblings数组必须包含所有和query不相关兄弟Block，不能遗漏
# 5. 功能描述可能较为模糊，你要根据提供的信息选择可能相关的所有Block，明确不相关的要排除

# 【注意】
# - nodeId必须从提供的兄弟Block中选择
# - 可以返回空数组
# - reason要说明该Block如何帮助回答问题
# """
# )
