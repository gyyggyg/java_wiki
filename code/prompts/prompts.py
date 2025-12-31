"""调用链分析提示词模板"""
from typing import Dict, List, Any

# 统一系统消息
SYSTEM_MESSAGE = (
    "你是一名技术文档专家，专门生成 Mermaid 图表。"
    "\n\n核心规则："
    "\n1. 只输出纯 Mermaid 代码，不要任何解释或代码块标记"
    "\n2. 第一行必须是图表标题注释（格式：%% 标题），第二行是图表类型声明"
    "\n3. 箭头两侧加空格（如 A --> B）"
    "\n4. 节点标签如有中文/特殊字符，用引号包裹（如 A[\"中文\"]）"
)

# 面向文字与表格说明的系统消息（非 Mermaid 输出）
SYSTEM_MESSAGE_DOC = (
    "你是一名技术文档专家，擅长将结构化数据总结为清晰的 Markdown 文本与表格。"
    "\n\n输出规则："
    "\n1. 只输出 Markdown 内容，不要额外解释，不要使用代码块标记。"
    "\n2. 优先使用表格展现，必要时用小标题分组。"
    "\n3. 表格列名简洁统一，单元格内容尽量精炼。"
)


# 任务1：类调用链时序图（对应文档第2部分）
TASK1_CALL_CHAIN_TEMPLATE = """
生成 Mermaid 时序图，展示类之间的调用关系。

要求：
1. 输出格式（重要）：
   第1行：%% 2. 类调用链时序图
   第2行：sequenceDiagram
   （注释行和图表类型之间必须有换行）
2. 第三行开始：参与者和箭头定义
3. 使用箭头展示调用：ClassA ->> ClassB: methodName
4. 按调用顺序从上到下排列
5. 只输出 Mermaid 代码（包含标题注释）

输入数据：

**调用关系**：
{call_relations}

**类信息**：
{classes_info}
"""


# 任务2：模块关系图（对应文档第3部分）
TASK2_MODULE_DIAGRAM_TEMPLATE = """
生成 Mermaid 关系图（graph TD），展示代码的层级结构和调用关系。

核心要求：
1. 输出格式（重要）：
   第1行：%% 3. 模块关系图
   第2行：graph TD
   （注释行和图表类型之间必须有换行）

2. 布局策略（三层嵌套）：
   - 外层：使用 subgraph 按 Block 分组
   - 内层：在每个 Block 内，使用 subgraph 按 Package 分组
   - 节点：在 Package 内组织 File -> Class -> Method 的层级关系

3. 节点形状：
   - File: [FileName.java]
   - Class: {{ClassName}}
   - Method: ((MethodName))

4. 关系链（重要：不要在箭头上加标签）：
   - File --> Class （实线，表示文件声明类）
   - Class --> Method （实线，表示类声明方法）
   - Method1 ==> Method2 （粗箭头，表示跨类的方法调用，这是核心调用关系）

5. 节点ID规则（重要）：
   - 使用驼峰命名法，前缀避免冲突：fileXxx, classXxx, methodXxx
   - 例如：fileOrder, classOrderController, methodCreateOrder
   - 不要使用下划线：避免 file_1, method_11 这样的命名
   - 中文标签需要引号：["中文文件.java"]
   - 六边形节点{{}}中避免使用中文+空格组合

6. 方法筛选原则：
   - 只展示能串联不同Class的Method（即有跨类调用关系的方法）
   - 如果某个Class没有参与跨类调用，可以不展示其Method，只展示Class节点

7. 只输出 Mermaid 代码（包含标题注释）

输入数据：

**模块层级（按 Block > Package > File > Class 组织）**：
{module_relations}

**方法调用**：
{method_call_relations}

参考示例：
%% 3. 模块关系图
graph TD
    subgraph block1["Block: module-order"]
        subgraph pkg1["Package: com.example.order"]
            fileOrderCtrl["OrderController.java"]
            classOrderCtrl{{"OrderController"}}
            methodCreate(("createOrder"))
            
            fileOrderCtrl --> classOrderCtrl
            classOrderCtrl --> methodCreate
        end
        
        subgraph pkg2["Package: com.example.service"]
            fileOrderSvc["OrderService.java"]
            classOrderSvc{{"OrderService"}}
            methodSave(("save"))
            
            fileOrderSvc --> classOrderSvc
            classOrderSvc --> methodSave
        end
    end
    
    subgraph block2["Block: module-handler"]
        subgraph pkg3["Package: com.handler.order"]
            fileHandler["OrderHandler.java"]
            classHandler{{"OrderHandler"}}
            methodHandle(("handle"))
            
            fileHandler --> classHandler
            classHandler --> methodHandle
        end
    end
    
    methodCreate ==> methodSave
    methodSave ==> methodHandle

重要规则：
- 箭头上不要加标签（如 -->|text| 或 -- "text" -->），直接用 --> 或 ==> 即可
- 节点ID使用驼峰命名（fileOrder, methodCreate），绝对不要用下划线（file_1, method_11）
- 严格遵守三层嵌套：Block(外层) > Package(内层) > File/Class/Method(节点)
- 只展示有跨类调用关系的Method，避免图表过于复杂
- Block名称使用简短英文描述（如 module-order, module-handler）
- Package使用完整包名（如 com.example.order）
- 跨Package、跨Block的方法调用用粗箭头(==>)突出显示
"""


# 任务2-文字说明：按 Block 外层、Package 内层的表格说明
TASK2_TEXT_TABLE_TEMPLATE = """
生成 Markdown 说明，要求以表格为主，外层按 Block 分组，内层按 Package 分组，并补充语义解释。

输出要求：
1. 只输出 Markdown 文本，不要使用任何代码块标记。
2. 对每个 Block，输出小标题：### Block: <blockName>。然后按 Package 聚合展示表格。
3. 表格列：Package | File | Class | Methods(跨类调用)。
4. Methods 仅展示参与跨类调用的方法；多个方法用逗号+空格分隔；若无则填 “-”。
5. 在每个 Block 的表格之后，追加一个小节：#### 语义解释。内容规则：
   - Block：直接输出该 Block 的 semantic_explanation（原始 JSON 或文本，若无则 “-”）。
   - Package：仅输出 What 字段（若无则 “-”）。
   - File：仅输出 What 字段（若无则 “-”）。
   - 展现形式建议用列表，保持简洁：
     - Block: <semantic_explanation>
     - Packages:
       - <packageName>: <what>
         - <fileName>: <what>
6. 末尾追加“方法调用关系”表，列：From(class.method) | To(class.method)。

输入数据：

[Block 分组的行数据（JSON 数组，每行一条记录）]
（每行包含：block（单个），package, file, class, methods；语义字段：block_explanation, package_what, file_what）
{block_rows}

[方法调用关系列表（每行一条 from -> to 描述）]
{call_relations}
"""


# 任务3：方法语义控制流图（对应文档第4部分）
TASK3_CONTROL_FLOW_TEMPLATE = """
生成 Mermaid 语义控制流图（flowchart TD），以业务语义展示 method1 如何调用 method2，突出关键对象与关键路径。

核心要求：
1. 输出格式（重要）：
   第1行：%% 4. 方法控制流图
   第2行：flowchart TD
   （注释行和图表类型之间必须有换行）

2. 语义优先：
   - 节点标签使用业务术语（如“校验订单参数”而非“check(x)”）
   - 合并非关键细节为概括动作（如“更新统计”）以控制复杂度
   - 明确“调用 {method2_name}”的节点，并在视觉上突出

3. 分组与层级：
   - 使用 subgraph 对流程分组，建议分为 Initialization、MainFlow、Cleanup（可根据代码语义自定义，但不超过3层）
   - 每个分组内自上而下排列节点，保持从入口到出口的完整路径

4. 视觉差异化（遵循 VS Code 风格配色）：
   - 决策点：白底细边框（矩形呈现，避免花括号），例如：style A3 fill:#fff,stroke:#333,stroke-width:2px
   - 关键操作：深蓝填充 + 粗边框（如“调用 {method2_name}”）：fill:#0af,stroke:#036,stroke-width:4px
   - 错误处理：浅红填充 + 红色虚线边框：fill:#fbb,stroke:#a00,stroke-width:3px,stroke-dasharray: 5 5
   - 关键路径连线可加粗（可选）：linkStyle 索引 stroke-width:3px

5. 复杂度控制：
   - 总节点数（含决策点）不超过 20
   - 仅保留能影响分支或外部交互的关键步骤

6. 节点与ID规范（重要）：
   - 使用字母数字代号（如 A1, B2, C3）作为节点ID，唯一且用于连接与样式
   - 标签为中文业务描述文本，可用 \n 换行，不超过两行
   - 避免使用 call、end、start、process 等作为ID；不要使用下划线、连字符

7. 节点形状约定：
   - 开始/结束: ([文本])
   - 决策点：使用方括号 ["条件描述?"]，并通过 style 设置白底细边框（禁止使用花括号）
   - 普通步骤: [步骤说明]
   - 方法调用: [调用: 业务方法]

8. 箭头与条件：
   - 使用无标签箭头：A1 --> B1；条件语义体现在节点标签中，禁止在箭头上加文字
   - 错误路径可使用虚线样式（通过 linkStyle 指定索引），或仅标注错误节点为红色虚线边框

9. 只输出 Mermaid 代码（包含标题注释）。

method1 信息：
- 名称: {method1_name}
- 功能: {method1_what}
- 实现: {method1_how}
- 源代码:
{method1_source}

method2 信息：
- 名称: {method2_name}
- 功能: {method2_what}

参考示例（结构与样式示意）：
%% 4. 方法控制流图
flowchart TD
    direction TB

    subgraph Initialization
        A1["读取与初步校验入参"]
        A2["参数完整?\n(必填/格式)"]
        style A2 fill:#fff,stroke:#333,stroke-width:2px %% 决策点
    end

    subgraph MainFlow
        B1["准备业务上下文"]
        B2["处理核心逻辑"]
        B3["调用: {method2_name}"]
        style B3 fill:#0af,stroke:#036,stroke-width:4px %% 关键操作
    end

    subgraph Cleanup
        C1["记录审计/统计"]
        C2([结束])
    end

    A1 --> A2
    A2 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> C1
    C1 --> C2

    %% 错误路径示例（可选）
    E1["参数无效/异常处理"]
    style E1 fill:#fbb,stroke:#a00,stroke-width:3px,stroke-dasharray: 5 5
    A2 --> E1
    E1 --> C2
"""


__all__ = [
    "SYSTEM_MESSAGE",
    "SYSTEM_MESSAGE_DOC",
    "TASK1_CALL_CHAIN_TEMPLATE",
    "TASK2_MODULE_DIAGRAM_TEMPLATE",
    "TASK2_TEXT_TABLE_TEMPLATE",
    "TASK3_CONTROL_FLOW_TEMPLATE",
]
