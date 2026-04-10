from langchain.prompts import PromptTemplate

# ====================== 状态机章节相关性判断 ======================

STATE_MACHINE_RELEVANCE_PROMPT = PromptTemplate(
    input_variables=["section_title", "section_description", "search_hints", "branch_tree"],
    template="""你是一个代码分析专家。以下是一个代码仓库的模块分支树，请判断哪些模块需要生成「{section_title}」章节。

## 章节说明
{section_description}

## 关键识别信号
以下类名或方法名出现在模块组件中时，强烈提示该模块需要生成此章节：
{search_hints}

## 模块分支树（JSON）
{branch_tree}

## 判断规则

### 核心判断条件
模块中存在**执行状态转换的方法**（如 updateStatus、changeState、transition、close、cancel，或直接 UPDATE status 字段的方法）即可选中。

状态值的枚举定义可以在同一模块，也可以在被引用的外部实体类中——只要转换逻辑在此模块中实现，就满足条件。

### 应选 ✅
- XxxServiceImpl：含 updateStatus / changeState / setState 等状态变更方法
- XxxProcessor / XxxHandler / XxxManager：直接驱动业务状态流转的实现类
- 同时包含枚举定义和转换逻辑的聚合模块

### 不选 ❌
- 纯 Interface / 抽象类（转换逻辑在实现层，不在接口层）
- Entity / Model / DO / DTO / VO：只持有 status 字段，不驱动转换
- Controller 层（除非它直接管理状态而非委托给 Service）
- 配置类、工具类、DAO / Repository 层

### 避免重复
- 同一套状态机逻辑只选**最权威的实现模块**。若多个模块都涉及同一实体的状态变更，选覆盖最完整的那个，其余跳过。
- 若同一模块包含**多套独立的状态机**（如优惠券状态、闪购状态分别是独立的状态字段），可以为每套状态机单独列一条，每条给出各自的搜索线索，以便分章节生成。

### 选择层级
- 优先选叶子模块（最具体的实现层）
- 若同一中间层下多个叶子都涉及**同一套**状态机，选中间层避免重复
- 不要同时选父模块和子模块

## 输出格式
请严格按以下JSON格式输出，不要包含任何其他文字：
{{"需要": [{{"模块名": "模块名1", "搜索线索": ["具体类名或方法名"]}}, {{"模块名": "模块名2", "搜索线索": ["具体类名或方法名"]}}], "不需要原因": "简要说明为什么其他模块不需要"}}

说明：
- "模块名"必须与分支树中的 name 字段**完全一致**，不要用路径格式
- "搜索线索"写行为实现的类名和方法名，例如 ["OmsPortalOrderServiceImpl", "updateStatus"]
- 若整个分支都不需要：{{"需要": [], "不需要原因": "说明原因"}}"""
)


# ====================== 消息队列章节相关性判断 ======================

MESSAGE_QUEUE_RELEVANCE_PROMPT = PromptTemplate(
    input_variables=["section_title", "section_description", "search_hints", "branch_tree"],
    template="""你是一个代码分析专家。以下是一个代码仓库的模块分支树，请判断哪些模块需要生成「{section_title}」章节。

## 章节说明
{section_description}

## 关键识别信号
以下类名、注解或关键词出现在模块组件中时，强烈提示该模块需要生成此章节：
{search_hints}

## 模块分支树（JSON）
{branch_tree}

## 判断规则

消息队列章节涉及三类组件，每类出现都是选择依据：

### 三类目标组件
1. **生产者（Producer/Sender）**：使用 RabbitTemplate / AmqpTemplate / KafkaTemplate 发送消息的 @Component 类（类名通常含 Sender / Producer）
2. **消费者（Consumer/Listener）**：带有 @RabbitListener / @KafkaListener / @RabbitHandler 注解的类（类名通常含 Receiver / Consumer / Listener）
3. **队列配置（QueueConfig）**：带有 @Configuration 注解、专门定义 Exchange / Queue / Binding Bean 的配置类

三类组件集中在同一模块 → 只选该模块；分布在不同模块 → 每个模块分别选中。

### 应选 ✅
- 含 Sender / Producer 类（使用 AmqpTemplate 发消息的 @Component）
- 含 @RabbitListener / @KafkaListener 标注的消费者类
- 含专项 MQ 配置的 @Configuration 类（只定义 Exchange/Queue/Binding，不是混杂了 Security/MyBatis/Swagger 的通用配置类）
- 同时包含上述多类组件的聚合模块（优先选此，避免拆散）

### 不选 ❌
- 只有消息体 DTO / VO，没有发送或接收逻辑
- 通用 Spring 配置类（同时包含 Security、MyBatis、Swagger 等多项配置，MQ 配置只是其中一项）
- 纯业务 Service（只是调用 Sender 的方法，自身不包含 MQ 逻辑）
- Controller / DAO / Repository 层

### 选择层级
- 优先选包含完整 Producer + Consumer（+ 专项 Config）的叶子或中间层模块
- 若三类组件分散在不同叶子，分别选对应叶子，不要选它们的公共父模块（除非父模块本身就包含这些组件）
- 不要同时选父模块和子模块

## 输出格式
请严格按以下JSON格式输出，不要包含任何其他文字：
{{"需要": [{{"模块名": "模块名1", "搜索线索": ["具体类名或注解"]}}, {{"模块名": "模块名2", "搜索线索": ["具体类名或注解"]}}], "不需要原因": "简要说明为什么其他模块不需要"}}

说明：
- "模块名"必须与分支树中的 name 字段**完全一致**，不要用路径格式
- "搜索线索"应明确指出组件类型，例如 ["CancelOrderSender（生产者）", "CancelOrderReceiver（消费者）", "@RabbitListener"]
- 若整个分支都不需要：{{"需要": [], "不需要原因": "说明原因"}}"""
)


# ====================== 通用兜底提示词（供未单独定制的章节类型使用）======================

BATCH_RELEVANCE_PROMPT = PromptTemplate(
    input_variables=["section_title", "section_description", "search_hints", "branch_tree"],
    template="""你是一个代码分析专家。以下是一个代码仓库的模块分支树，请判断哪些模块需要生成「{section_title}」章节，并选择在最合适的层级生成。

## 章节说明
{section_description}

## 关键识别信号
以下类名、注解或关键词出现在模块组件中时，强烈提示该模块需要生成此章节：
{search_hints}

## 模块分支树（JSON）
{branch_tree}

## 判断规则
1. 只有当模块的功能描述或核心组件中明确涉及与「{section_title}」直接相关的**行为实现**时，才需要生成此章节
2. 仔细阅读叶子模块的组件介绍（类名和职责），从中寻找与章节主题相关的具体证据
3. 选择最合适的层级生成：
   - 如果某个中间层模块下的多个叶子模块都涉及同一主题，优先在该中间层模块生成（避免重复）
   - 如果只有个别叶子模块涉及，则在该叶子模块生成
   - 不要同时选择父模块和它的子模块
4. 仅提到通用功能（如CRUD、配置管理、数据模型定义）的模块不需要
5. 【实现层 vs 数据层】只选择**主导实现**该章节主题行为的模块，不选择仅定义数据结构或传递参数的模块：
   - ✅ 应选：ServiceImpl、Handler、Processor、Manager、Consumer、Listener 等行为实现层
   - ❌ 不选：Entity、Model、DO、DTO、VO、Param 等数据定义/传输层
   - ❌ 不选：Controller 层（除非 Controller 本身就是消费者/监听器等直接实现层）
6. 【避免重复】同一套业务逻辑只在最权威的一个模块生成。若多个模块都涉及相同主题，选覆盖最完整的那个，其余跳过

## 输出格式
请严格按以下JSON格式输出，不要包含任何其他文字：
{{"需要": [{{"模块名": "模块名1", "搜索线索": ["从摘要中提取的具体类名、方法名、关键词"]}}, {{"模块名": "模块名2", "搜索线索": ["具体线索"]}}], "不需要原因": "简要说明为什么其他模块不需要"}}

说明：
- "模块名"必须与模块分支树中的 name 字段**完全一致**，不要使用路径格式（如"父模块 > 子模块"）或省略写法
- "搜索线索"应指向**行为实现**（方法名、注解名、接口名），而非纯数据字段名
- 若整个分支都不需要：{{"需要": [], "不需要原因": "简要说明原因"}}"""
)


# ====================== mermaid 语法修复提示词 ======================

MERMAID_FIX_PROMPT = PromptTemplate(
    input_variables=["markdown", "mermaid", "error"],
    template="""你是一个 Mermaid 图表语法专家。下面的 mermaid 代码存在语法错误，请修复它。

## 所在章节的文字内容（只读，理解图表含义用，不要修改）
{markdown}

## 待修复的 mermaid 代码
```mermaid
{mermaid}
```

## 解析器报告的错误信息
{error}

## 修复规则（按优先级）
1. **边标签特殊字符必须加双引号**：`|...|` 内含 `@`、`:`、`()`、`<`、`>` 等字符时，用双引号包裹整个标签
   - 正确：`A -->|"@RabbitListener"| B`、`A -->|"paySuccess()[status=0]"| B`
   - 错误：`A -->|@RabbitListener| B`
2. **`<br/>` 禁止出现在边标签中**：只能用于节点标签 `[]` 内，边标签中改为空格或去掉
3. **stateDiagram-v2 用 `: label` 格式**，不用 `|label|`
4. **节点 ID 不能是保留字**：`end`、`class`、`style`、`subgraph`、`click` 等需改名
5. **subgraph 必须有对应的 `end`**，不能多也不能少

只输出修复后的 mermaid 图表代码本身，不包含 ```mermaid``` 标记，不包含任何解释文字。"""
)
