from langchain.prompts import PromptTemplate


#生成source_id提示词;
SOURCE_ID_PROMPT= PromptTemplate(
    input_variables=["source_code","explanation"],
    template="""
你是代码控制流分析专家，你需要根据我给你提供的源代码，和代码语义解释，为我拆解代码控制流，并返回功能片段和行号范围。
【任务】
1、根据代码语义解释和源代码，拆解代码控制流
2、输出功能片段对应的行号范围和拆解原因。
3、必须是给出的源代码实际行号，如果拆分出的功能片段包括多段代码，需要用数组（如`["49", "55-59"]`）

【输入】
源代码：
{source_code}
代码语义解释：
{explanation}

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"lines":[["8-10"],["11-20","80"],["21"],["22"],...], "reason":"解释划分原因，例如：8-10行代码是查询信息，11-20行做判断xxx，21，22分别执行判断结果为xx的逻辑" }}
  输出格式示例说明：
  - 外层数组：每个元素代表一个功能片段
  - 内层数组：该功能片段涉及的代码行号范围（可能不连续）
  - 行号格式："单行"或"范围"（如 "8" 或 "8-10"）

"""
)

#修正提示词：
CFG_VALIDATE_PROMPT= PromptTemplate(
    input_variables=["source_code","explanation","source_id"],
    template="""
你是代码控制流分析专家，你需要根据我给你提供的源代码，和代码语义解释，判断我拆解的功能片段和行号范围是否正确且合理。
【输入介绍】
源代码'source_code'：{source_code}
源代码语义解释'explanation'：{explanation}
已经拆分的功能片段和行号范围'source_id'：{source_id}
【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"result": "true/false", "reason": "拆解的如果正确好在哪，拆解的如果不正确错误在哪"}}
"""
)

##########四个视图提示词


CFG_PROMPT= PromptTemplate(
    input_variables=["source_code","explanation","key_target","source_id"],
    template="""
你是代码语义分析专家，需基于我给你的输入生成**业务导向的语义控制流图(semantic cFG)**，并输出Mermaid图和节点对应代码行号范围的id。严格遵循以下原则:
### 输入信息
```
源代码：{source_code}
代码涉及信息的语义解释：{explanation}
你需要在mermaid图中突出的调用对象：{key_target}
mermaid图中代码行号范围对应的id：{source_id}, 例如{{188：["8-10","15-20"]}}
```

### 核心原则
1、控制流图里的节点必须依据'source_id'里存在的代码行号范围构造
2、你要保证所有节点都能在'source_id'里找到对应的代码行号范围id
3、图中要突出代码与'key_target'相关的调用逻辑
---

### 输出要求

1.**语义优先**
 - 节点描述需从`语义解释`中提炼，避免技术术语
2. **结构化组织**
 - 用`subgraph 分组(如`Initialization`,`MainLoop`,`cleanup`)
 - 层级不超过3层，确保视觉清晰度
3. **视觉差异化**
 - 决策点:菱形 + 白底细边框
 - 关键操作:深蓝填充 +粗边框(如`write block`)
 - 错误路径:红色虚线边框 + 浅紅填充
 - 使用vs Code风格配色(主色:'#0af，｀#f96`，｀#fbb)
 - 所有错误节点统一用`stroke-dasharray:5 5`
 - 线条加粗：关键路径`stroke-width:3px`，默认`2px`
4. **复杂度控制**
 - 总节点数≤20(含决策点)
 - 合并非关键逻辑(如“更新统计”涵盖多行代码)
5. **节点标识规范**
 - 代号:唯一字母数字(如`A1'，“B3)，仅用于连接和样式
 - 标签:业务描述文本(如“分配SSD缓存缓冲区”)
6. **确保JSON可以被标准解析器解析**
	- mermaid字符串复制到Mermaid编辑器中应能正常渲染
	- 节点标签中的换行符应显示为实际换行，而非 `\\n` 文本
7. **使用方括号代替花括号**

#### Mermaid示例
```mermaid
flowchart TD
    direction TB
    subgraph Initialization
        A1["打开日志文件\n(准备记录IO延迟)"]
        A3["内存分配成功?"]
        style A3 fill:#fff,stroke:#333,stroke-width:2px,shape:diamond %% 决策点
    end
    A1 --> A3
    style A1 fill:#0af,stroke:#036,stroke-width:4px %% 关键操作
```

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
注意：mapping'中的每个节点对应的应该是'source_id'中的id，而不是行号或者名称
{{"mermaid": "这里是输出的mermaid内容", "mapping": "你输出的节点代号和代码行号范围对应id的映射关系，例如{{"A1":"188"}}"}}

"""
)


UML_PROMPT= PromptTemplate(
    input_variables=["node_information","key_target","source_id"],
    template="""
现在我有一个Java项目，你需要为我做出UML类图，并按照指定格式回复。
### 输入信息
```
所有涉及到的类/接口源代码信息'node_information'
你需要在mermaid图中突出的类/接口'key_target'
图中出现的类/接口对应的id'source_id'
```

要求：
1、'source_id'中的类节点必须出现在图中
2、用不同的颜色突出和'key_target'类相关的类节点和关系
3、体现"node_information"中所有节点和关系，接口、枚举、抽象类要用 `<<interface>>`、`<<enum>>`、`<<abstract>>` 标注
4、每个类节点的信息要包含类/接口和外界产生联系的属性和函数
5、关系例如实现、继承、使用、返回等要在图中体现

uml类图语法规则（必须严格遵守）：
1. 类节点命名：
   - 必须使用给你提供的实际类名作为节点ID，不能使用数字ID，类名、关系标签都不能用单引号或双引号包裹,关系上不要加标签
   - 类名里不要出现 $、.、- 等符号；
   - 正确：class Order, class AlipayService, class CommonResult~T~
   - 错误：class 2841, class 5554, class 2907
2. 泛型类型必须使用波浪号~而不是尖括号<>
   - 正确：class Result~T~, List~String~, Map~K,V~
   - 错误：class Result<T>, List<String>, Map<K,V>
3. 类定义中禁止出现第二对 {{ }}、方法体、分号、注释、修饰符（如 public/private）
   - 可见性符号只能保留 + - # ~
   - 抽象类用 <<abstract>>，接口用 <<interface>>，枚举用 <<enumeration>>
4. 内部类/嵌套类处理：
   - 必须将内部类拆分为独立的类节点，不要在类定义内部再定义类
   - 使用组合关系（*--）或聚合关系（o--）表示外部类与内部类的包含关系
   - 内部类命名：OuterClass.InnerClass 或 OuterClass$InnerClass
   - 正确示例：
     class Order {{
         +validate() void
     }}
     class Order$Item {{
         +getPrice() BigDecimal
     }}
     Order *-- Order$Item : contains
   - 错误示例（禁止）：
     class Order {{
         class Item {{
             +getPrice() BigDecimal
         }}
     }}
5. 禁止把多个类名用逗号拼接在同一行；高亮语法使用style而不是highlight。
错误：    %% 高亮目标节点class AlipayController,AlipayService,AlipayServiceImpl,OmsPortalOrderService,OmsPortalOrderServiceImpl highlight
正确：   style AlipayController fill:#ffe4e1,stroke:#d60000,stroke-width:2px
6. linkStyle使用注意换行：
正确：
linkStyle 0 stroke:#d60000,
stroke-width:2px
错误：
linkStyle 0 stroke:#d60000, stroke-width:2px

语法示例：
    class Result~T~ {{
        - T data
        - String message
        +getData() T
        +setData(T) void
        +success(T) Result~T~
    }}

    class Order {{
        <<abstract>>
        #String orderId
        #BigDecimal amount
        +validate() void
    }}
    
    OrderProcessor <|-- DomesticOrderProcessor %% 关系上不要加标签
    linkStyle 0 stroke:#d60000,
    stroke-width:2px %%这里必须换行

### 输入信息
```
'node_information'：{node_information}
'key_target'：{key_target}
图中出现的类/接口对应的id'source_id'：{source_id}, 例如{{188："Order"}}
```
【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
注意：mapping'中的每个节点对应的应该是'source_id'中的id，而不是行号或者名称
{{"mermaid": "这里是输出的uml内容", "mapping": "你输出的节点代号和类/接口在'source_id'对应id的映射关系，例如{{"Order":"188"}}"}}

"""
)

TIME_PROMPT= PromptTemplate(
    input_variables=["key_target","call_information","source_id"],
    template="""
你需要分析我给你提供的信息，生成 Mermaid 时序图，展示类之间的调用关系顺序。

### 输入信息
```
图中涉及到的类直接方法调用'call_information'：{call_information}
你需要在图中突出的调用链'key_target'：{key_target}
图中出现的类/方法对应的id'source_id'：{source_id}, 例如{{"188":"Browser","189":"Browser.orderRequest()"...}}
```

要求：
1、'source_id'中的类/方法必须出现在图中
2、'key_target'中的调用链包括函数调用，类实现等必须用颜色突出rect rgb(240,248,255)，其余关系保持默认样式
3、类之间关系包括calls，implemented_by等，如果是调用关系写调用的方法，如果是实现关系写implemented_by
4、同一个类方法多次调用另一个类的方法时，只需展示一次调用关系
5、participant只能是类命称，箭头上的标签是方法调用或者实现关系

语法示例：
sequenceDiagram
    autonumber
    participant Browser as Browser
    participant Gateway as Gateway
    participant GatewayImpl as GatewayImpl

    Browser->>Gateway: Browser.orderRequest() calls Gateway.handleRequest()
    rect rgb(240,248,255) %% 突出显示的调用链
        Gateway->>GatewayImpl: implemented_by
    end

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
注意：mapping'中的每个节点对应的应该是'source_id'中的id，而不是行号或者名称
{{"mermaid": "这里是输出的Mermaid 时序图内容", "mapping": "图中类/方法在'source_id'对应id的映射关系，例如{{"Browser.orderRequest()":"189","Browser":"188"}}"}}

    
"""
)

BLOCK_PROMPT= PromptTemplate(
    input_variables=["key_target","call_information","module_package_info","source_id"],
    template="""
我现在有一些java文件，已经按照功能划分模块，你需要生成 Mermaid 关系图（graph TD），展示代码的层级结构和调用关系。
```
类所在文件，所属的模块和包信息'module_package_info'
图中涉及到的文件之间方法调用'call_information'
你需要在图中突出的调用链'key_target'
图中出现的类/方法对应的id'source_id' 例如{{"189":"OrderController","190":"OrderController.createOrder()"...}}
```

核心要求：
1. 要体现模块，包，文件，类，方法的层级关系，展示'module_package_info'和'call_information'中所有涉及到的包，文件，类，方法节点和方法调用/实现关系
2. 'source_id'中没有package和block的id，在返回时不需要注明图中package和block节点的id

3. 布局策略（三层嵌套）：
   - 外层：使用 subgraph 按 Block 分组
   - 内层：在每个 Block 内，使用 subgraph 按 Package 分组
   - 节点：在 Package 内组织 File -> Class -> Method 的层级关系

4. 节点形状：
   - File: [FileName.java]
   - Class: {{ClassName}}
   - Method: ((MethodName))

5. 关系链（重要：不要在箭头上加标签）：
   - File --> Class （实线，表示文件声明类）
   - Class --> Method （实线，表示类声明方法）
   - Method1 ==> Method2 （粗箭头，表示方法调用，这是核心调用关系）

6. 节点ID规则（重要）：
   - 节点命名完全来自输入数据，使用驼峰命名法
   - 绝对不要使用下划线（如file_1, method_11）
   - 中文标签需要引号：["中文文件.java"]
   - 六边形节点{{}}中避免使用中文+空格组合

7. 每个节点第一次出现时用 id[label] 或 id(("label")) 定义，后续只能引用该 id，绝不再重复定义,同一对节点之间同方向仅允许一条边。


参考示例：
%% 3. 模块关系图
    graph TD
    subgraph block1["Block:module-order"]
        subgraph pkg1["Package:com.example.order"]
            fileOrderCtrl["OrderController.java"]
            classOrderCtrl{{"OrderController"}}
            methodCreate(("createOrder"))
            
            fileOrderCtrl --> classOrderCtrl
            classOrderCtrl --> methodCreate
        end
        
        subgraph pkg2["Package:com.example.service"]
            fileOrderSvc["OrderService.java"]
            classOrderSvc{{"OrderService"}}
            methodSave(("save"))
            
            fileOrderSvc --> classOrderSvc
            classOrderSvc --> methodSave
        end
    end
    
    subgraph block2["Block:module-handler"]
        subgraph pkg3["Package:com.handler.order"]
            fileHandler["OrderHandler.java"]
            classHandler{{"OrderHandler"}}
            methodHandle(("handle"))
            
            fileHandler --> classHandler
            classHandler --> methodHandle
        end
    end
    
    methodCreate ==> methodSave
    methodSave ==> methodHandle
    linkStyle 6 stroke:#ff0000,stroke-width:4px %% 突出显示关键调用链


【高亮规则-严格遵守】
1. 只高亮'key_target'中明确列出的关系，不要高亮其他任何关系
2. 'key_target'格式："ClassA.methodA calls ClassB.methodB" 或 "InterfaceA implemented_by ClassB"
3. 对于calls关系：找到图中 methodA ==> methodB 的边，用 linkStyle 高亮
4. 对于implemented_by关系：找到图中 InterfaceA ==> ClassB 的边，用 linkStyle 高亮
5. 其他所有边（File-->Class, Class-->Method, 以及不在key_target中的调用/实现关系）保持默认样式
6. 高亮样式统一使用：stroke:#ff0000,stroke-width:4px

【输入】
'module_package_info'：{module_package_info}
'call_information'：{call_information}
'key_target'：{key_target}
'source_id'：{source_id}, 例如{{"189":"OrderController","190":"OrderController.createOrder()"...}}

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
注意：mapping'中的每个节点对应的应该是'source_id'中的id，而不是行号或者名称
{{"mermaid": "这里是输出的Mermaid模块架构图", "mapping": "图中使用的类/方法在'source_id'对应id的映射关系，例如{{"OrderController":"189","OrderController.createOrder()":"190"...}}"}}

"""
)

#校验提示词
VALIDATE_PROMPT= PromptTemplate(
    input_variables=["source_information","source_id","chart_mermaid","chart_mapping"],
    template="""
你是校验分析专家，执行校验任务：

【输入介绍】
1、mermaid图中信息来源'source_information'：{source_information}
2、每个id对应的信息片段'source_id'：{source_id}
3、根据来源信息'source_information','source_id'生成的mermiad图'chart_mermaid'：{chart_mermaid}
4、mermaid图中节点id和信息片段id的映射关系'chart_mapping'：{chart_mapping}

【具体事项】
1. 对于控制流图，重点关注代码与行号的对应关系是否准确，行号划分是否合理
2. 对于uml图，重点关注类名、方法名、关系等是否准确。是否符合mermaid类图语法规范
3、对于调用链图，如果是调用关系写发出调用的方法，如果是实现关系应该写implemented_by,重点关注类之间的调用顺序和关系是否准确，时序图是展示调用链的，
4、对于模块架构图，重点关注模块、包、文件、类、方法的层级关系和调用关系是否准确

【校验任务】
根据'source_information', 校验'source_id'和'chart_mermaid'和'chart_mapping'的正确性，输出校验结果，包括：
1. 'source_id'中的每个id对应的内容是否都能在'source_information'中找到对应的信息片段
2. 'chart_mapping'中的每个节点的id是否都能在'source_id'，并且对应是否正确
3. 'chart_mapping'中的每个节点对应的是'source_id'中的id，而不是行号或者名称
4. 'chart_mermaid'的mermaid语法是否正确，能否被标准mermaid解析器解析


【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"result": "true/false", "reason": "校验结果原因"}}
"""
)