from langchain.prompts import PromptTemplate

MODULE_NAME_PROMPT = PromptTemplate(
    input_variables=["module_information","pom_content"], 
    template="""
你是模块命名专家。针对一个已按文件功能完成聚类的 Java 项目，请为出现的每个模块重新设计一个**自然语言风格的中文名称**。
【输入】
- 模块树信息：包含父子层级、唯一 nodeId、初始名称及语义说明，见 `module_information`：{module_information}
- `pom.xml` ：{pom_content}，含模块间依赖关系

【任务】
1. 根据 `module_information` 还原模块层级结构  
2. 依据 `pom_content` 中的依赖关系，推断各模块职责边界  
3. 综合层级位置、职责范围及与其他模块的关联，为 `module_information` 中出现的每个 nodeId 生成一个英文名称，要求：
   - 不要使用驼峰命名法
   - 使用自然语言、可读性强、空格分隔、一眼看懂，控制在5个词内
   - 高度展示概括模块的具体功能，体现差异和联系 
   - 体现上下级关系  
   - 同级名称保持相关性  
   - 与依赖模块名称呼应  
   - 避免模棱两可功能不清晰的名称，如 "Module1"、"FoundationA"
4. 仅返回 nodeId 到新名称的映射

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"module1_id":"商品搜索核心服务模块","module2_id":"商品搜索系统实现与保障模块",...}} 
"""
)
#生成source_id提示词;
SOURCE_ID_PROMPT= PromptTemplate(
    input_variables=["source_code","explanation"],
    template="""
你是代码控制流分析专家，你需要根据我给你提供的源代码，和代码语义解释，为我拆解整个代码的控制流，并返回功能片段和行号范围。
【任务】
1、根据代码语义解释和源代码，拆解代码控制流, 源码已注明行号
2、你的拆解结果尽量覆盖源码所有行，不能遗漏缺失任何行号
3、输出功能片段对应的行号范围和拆解原因。
4、必须是给出的源代码实际行号，如果拆分出的功能片段包括多段代码，需要用数组（如`["49", "55-59"]`）
【核心要求】
1. **完整覆盖**：必须覆盖源代码中所有功能行（除注释、空行、单独的花括号外）
   - 检查方法：从第一行功能代码到最后一行功能代码，不能有任何功能行被遗漏
   - 特别注意：连续的代码块之间不能有间隙（如节点A覆盖到73行，节点B从75行开始，则74行必须被某个节点覆盖）

2. **避免不必要的重叠**：
   - 允许的重叠：异常终止节点可以与其判断节点重叠（如判断节点包含if和异常throw）
   - 不允许的重叠：两个功能节点覆盖相同的代码段（如B13和B17都包含201-215行）
   - 如果两个节点描述不同功能但覆盖相同代码，需要重新划分边界

3. **避免过于细致的行号范围**：
    - 功能片段不应过于细化到单行，除非该行代码确实是独立功能

4. **特别注意的代码段**：
   - 方法调用后的赋值语句（如order.setPayAmount(...)）不要遗漏
   - 连续的属性设置代码（如order.setMemberId, order.setCreateTime等）要完整覆盖
   - if-else块中的所有分支都要覆盖

【输入】
源代码：
{source_code}
代码语义解释：
{explanation}

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"lines":[["8-10"],["11-20","80"],["21"],["22"],...], "reason":"解释划分原因，例如：8-10行代码是查询信息，没给任何节点分配的行号被遗留的原因" }}
  输出格式示例说明：
  - 外层数组：每个元素代表一个功能片段
  - 内层数组：该功能片段涉及的代码行号范围（可能不连续）
  - 行号格式："单行"或"范围"（如 "8" 或 "8-10"）

"""
)

#修正提示词：
#修正提示词：
CFG_ID_PROMPT= PromptTemplate(
    input_variables=["source_code","mermaid","mapping","reason"],
    template="""
你是代码控制流分析专家，你需要根据我给你提供的源代码，代码控制流图，为图中每个节点调整源码对应行号范围。
【输入介绍】
控制流源代码'source_code'：{source_code}, 源码已注明行号
根据源代码画出的控制流图'mermaid'：{mermaid}
控制流图中节点和源码行号范围的映射关系'mapping'：{mapping}
目前每个节点对应行号的划分原因'reason'：{reason}
【任务】
1. 根据源代码和控制流图，调整每个节点对应的源码行号范围
2. 输出调整后的每个节点对应的源码行号范围和调整原因
3. 必须是给出的源代码实际行号，图中节点包括多段代码，需要用数组（如`["49", "55-59"]`）
4. 保证覆盖源代码所有功能行
5. 严格注意代码行号范围，绝对不能出现超出源代码实际行号，如果输入里行号范围不正确，请进行修正

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"mapping": 图中节点对应源码行号，例如{{"A1":["8-10"], "B1":["11-20","80"]}}, "reason": "如果你进行了调整，请说明调整原因"}}
"""
)
##########四个视图提示词


CFG_PROMPT= PromptTemplate(
    input_variables=["source_code","explanation","source_id", "code_block"],
    template="""
你是代码语义分析专家，需基于我给你的输入生成**业务导向的语义控制流图(semantic cFG)**，并输出Mermaid图和节点对应代码行号范围的id。严格遵循以下原则:
### 输入信息
```
源代码：{source_code}
代码涉及信息的语义解释：{explanation}
mermaid图中代码行号范围对应的id：{source_id}, 例如{{188：["8-10","15-20"]}}
代码片段的功能信息：{code_block}
```

### 核心原则
1、控制流图里的节点参考'source_id'里存在的代码行号范围和'code_block'里的功能信息进行构造
2、保证所有图中节点信息来源的代码行号范围都能对应到'source_id'里的代码行号范围的id，或者范围附近的代码行号范围id
3、你要保证覆盖源代码所有功能行
4、严格注意代码行号范围，绝对不能出现超出源代码实际行号，如果输入里行号范围不正确，请进行修正
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
```

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
注意：mapping'中的每个节点对应的应该是'source_id'中的id，而不是行号或者名称
{{"mermaid": "这里是输出的mermaid内容", "mapping": "你输出的节点代号和代码行号范围对应id的映射关系，例如{{"A1":"188"}}"}}

"""
)


UML_PROMPT= PromptTemplate(
    input_variables=["node_information","source_id"],
    template="""
现在我有一个Java项目，你需要为我做出UML类图，并按照指定格式回复。
### 输入信息
```
所有涉及到的类/接口结构信息'node_information'（包含类声明、字段列表、方法签名列表、以及类之间的关系描述）
图中出现的类/接口对应的id'source_id'
```

要求：
1、'source_id'中的类节点必须出现在图中
2、体现"node_information"中所有节点和关系，接口、枚举、抽象类要用 `<<interface>>`、`<<enum>>`、`<<abstract>>` 标注
3、每个类节点的信息要包含类/接口和外界产生联系的属性和函数
4、关系例如实现、继承、使用、返回等要在图中体现
5、枚举类的枚举常量要在类图中体现

uml类图语法规则（必须严格遵守）：
1. 类节点命名：
   - 必须使用给你提供的实际类名作为节点ID，不能使用数字ID，类名、关系标签都不能用单引号或双引号包裹,关系上不要加标签
   - 类名里禁止出现 $、.、- 等符号；
   - 正确：class Order, class AlipayService, class CommonResult~T~
   - 错误：class 2841, class 5554, class 2907
2. 泛型类型必须使用波浪号~而不是尖括号<>
   - 一对波浪号~只能出现一次，禁止嵌套波浪号
   - 嵌套泛型必须展平：用下划线或逗号代替内层泛型括号
   - 正确：class Result~T~, List~String~, Map~K,V~, CommonResult~List_CmsPrefrenceArea~
   - 错误：class Result<T>, List<String>, CommonResult~List~CmsPrefrenceArea~~, CommonResult~List~String~~
3. 类定义中禁止出现第二对 {{ }}、方法体、分号、注释、修饰符（如 public/private）
   - 可见性符号只能保留 + - # ~
   - 抽象类用 <<abstract>>，接口用 <<interface>>，枚举用 <<enumeration>>，放在第二行开头
4. 内部类/嵌套类处理：
   - 必须将内部类拆分为独立的类节点，不要在类定义内部再定义类
   - 使用组合关系（*--）或聚合关系（o--）表示外部类与内部类的包含关系
   - 内部类命名：使用下划线连接，如 OuterClass_InnerClass
   - 禁止使用 $ 或 . 作为内部类分隔符（$ 和 . 是mermaid非法字符）
   - 正确示例：
     class Order {{
        <<interface>> %%类型放在这里
         +validate()
     }}
   - 错误示例（禁止）：
     class Order {{
         class Item {{
             +getPrice()
         }}
     }}
5. 禁止把多个类名用逗号拼接在同一行

完整语法示例（注意第一行必须是classDiagram），类的开头必须是class：
classDiagram
    class Result~T~ {{
        - T data
        - String message
        +getData()
        +setData(T)
        +success(T)
    }}

    class Order {{
        <<abstract>>
        #String orderId
        #BigDecimal amount
        +validate()
    }}
    
    OrderProcessor <|-- DomesticOrderProcessor %% 关系上不要加标签


### 输入信息
```
'node_information'：{node_information}
图中出现的类/接口对应的id'source_id'：{source_id}, 例如{{188："Order"}}
```
【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
注意：mapping'中的每个节点对应的应该是'source_id'中的id，而不是行号或者名称
{{"mermaid": "这里是输出的uml内容", "mapping": "你输出的节点代号和类/接口在'source_id'对应id的映射关系，例如{{"Order":"188"}}"}}

"""
)

HYBRID_UML_PROMPT = PromptTemplate(
    input_variables=["node_information", "source_id"],
    template="""
你的任务是将输入的JSON数据转换为Mermaid classDiagram。

## 输入格式
'node_information'是一个JSON数组，包含两种元素：

**1. 直连类（不放在任何namespace中）**：
```json
{{
  "direct_classes": [
    {{"name": "类名", "declaration": "Java类声明", "fields": "...", "methods": "...", "relations": [...]}}
  ]
}}
```
这些类直接定义在classDiagram顶层，不包裹在namespace中。

**2. 子模块类（按namespace分组）**：
```json
{{
  "namespace": "子模块名称",
  "classes": [
    {{"name": "类名", "declaration": "Java类声明", "fields": "...", "methods": "...", "relations": [...]}}
  ]
}}
```
这些类放在对应的namespace中。

'source_id'是每个类对应的唯一标识id。

## 转换步骤（请严格按此顺序执行）

**步骤1：遍历JSON，处理两种类型的元素**
- 含"direct_classes"的元素 → 类直接定义在classDiagram顶层，不包裹在namespace中
- 含"namespace"的元素 → 类放在对应的namespace中，namespace名称直接使用JSON中的值，禁止修改或编造

**步骤2：为每个class生成类定义**
- "name" → 类节点ID（泛型用波浪号~替换尖括号<>）
- "declaration"中含interface → 添加<<interface>>，含abstract → 添加<<abstract>>，含enum → 添加<<enumeration>>
- "fields" → 转换为UML字段（public→+, private→-, protected→#, 无修饰符→~）
- "methods" → 转换为UML方法（同上）
- 禁止添加JSON中不存在的类

**步骤3：在所有namespace外部，根据relations生成关系连线**
- "实现 ->" → `<|..`（虚线继承）
- "继承 ->" → `<|--`（实线继承）
- "调用 ->" → `-->`（依赖）
- "使用 ->" → `-->`（依赖）
- "返回 ->" → `-->`（依赖）
- 关系线上不要加标签
- **关键：关系线中只使用类名，禁止加namespace前缀**
  - 正确：`CommonResult~T~ --> IErrorCode`
  - 错误：`API Response and Error Management.CommonResult~T~ --> API Response and Error Management.IErrorCode`
  - 原因：Mermaid会将带前缀的名称视为新节点，导致图中出现多余节点

## Mermaid语法约束
1. 第一行必须是classDiagram
2. 泛型必须用波浪号~，不能用<>。正确：CommonResult~T~，错误：CommonResult<T>
3. 类定义中禁止出现：第二对花括号、方法体、分号、注释、Java修饰符（用+-#~替代）
4. 内部类拆分为独立节点，用组合关系（*--）连接
5. 每行只能定义一个类

## 语法骨架（仅展示格式，不要复制内容）
```
classDiagram
    %% direct_classes中的类：直接定义在顶层
    class [direct_classes中的name值] {{
        [字段和方法]
    }}

    %% namespace中的类：包裹在namespace内
    namespace [JSON中的namespace值] {{
        class [classes中的name值] {{
            [字段和方法]
        }}
    }}

    [类A] --> [类B]  %% 根据relations生成
```

## 转换规则速查
| JSON字段 | 转换方式 |
|----------|---------|
| declaration含"interface" | 类定义内第一行加<<interface>> |
| declaration含"abstract" | 类定义内第一行加<<abstract>> |
| declaration含"enum" | 类定义内第一行加<<enumeration>> |
| fields中"private X y" | -X y |
| fields中"public X y" | +X y |
| fields中"protected X y" | #X y |
| methods中"public foo():Bar" | +foo() Bar |
| methods中"private foo():Bar" | -foo() Bar |
| 泛型 CommonResult<T> | CommonResult~T~ |
| relations中"实现 ->" | <\|.. |
| relations中"继承 ->" | <\|-- |
| relations中"调用/使用/返回 ->" | --> |

---

### 以下是你需要转换的实际输入数据（请严格基于此数据生成，禁止使用上面骨架中的占位内容）

'node_information'：
```json
{node_information}
```

'source_id'：
```json
{source_id}
```

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
mapping中的值必须是source_id中对应的id字符串，不是行号或名称
{{"mermaid": "classDiagram\\n    namespace ...", "mapping": {{"类名1": "source_id值1", "类名2": "source_id值2"}}}}

"""
)

TIME_PROMPT= PromptTemplate(
    input_variables=["call_information","source_id"],
    template="""
你需要分析我给你提供的信息，生成 Mermaid 时序图，展示类之间的调用关系顺序。

### 输入信息
```
图中涉及到的类直接方法调用'call_information'：{call_information}
图中出现的类/方法对应的id'source_id'：{source_id}, 例如{{"188":"Browser","189":"Browser.orderRequest"...}}
```

要求：
1、'source_id'中的类/方法必须出现在图中
2、类之间关系包括calls，implemented_by
 - 如果是calls，你需要在箭头标签上注明你需要注明发起调用的类的和方法，正确示例例如Browser.orderRequest，但是不能写被调用的类和方法，错误示例：Browser.orderRequest calls Gateway
 - 如果是实现关系写implemented_by
5、同一个类方法多次调用另一个类的方法时，只需展示一次调用关系
6、participant只能是类命称，箭头上的标签是方法调用或者实现关系

语法示例：
sequenceDiagram
    autonumber
    participant Browser as Browser
    participant Gateway as Gateway
    participant GatewayImpl as GatewayImpl

    Browser->>Gateway: Browser.orderRequest %% 调用
    Gateway-->>GatewayImpl: implemented_by %% 实现

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
注意：mapping'中的每个节点对应的应该是'source_id'中的id，而不是行号或者名称
{{"mermaid": "这里是输出的Mermaid 时序图内容", "mapping": "图中节点类/方法在'source_id'对应id的映射关系，例如{{"Browser.orderRequest":"189","Browser":"188"}}"}}
"""
)

BLOCK_PROMPT= PromptTemplate(
    input_variables=["call_information","module_package_info","source_id"],
    template="""
我现在有一些java文件，已经按照功能划分模块，你需要生成 Mermaid 关系图（graph TD），展示代码的层级结构和调用关系。
```
类所在文件，所属的模块和包信息'module_package_info'
图中涉及到的文件之间方法调用'call_information'
图中出现的类/方法对应的id'source_id' 例如{{"189":"OrderController","190":"OrderController.createOrder"...}}
```

核心要求：
1. 要体现模块，包，文件，类，方法的层级关系，展示'module_package_info'和'call_information'中所有涉及到的包，文件，类，方法节点和方法调用/实现关系
2. 图中节点的信息必须全部来自输入信息，不能修改删减输入中模块/包/文件/类/方法的命名
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
    subgraph block1["Block:a/module-order"]
        subgraph pkg1["Package:com.example.order"]
            fileOrderCtrl["a/abc/OrderController.java"]
            classOrderCtrl{{"OrderController"}}
            methodCreate(("createOrder"))
            
            fileOrderCtrl --> classOrderCtrl
            classOrderCtrl --> methodCreate
        end
        
        subgraph pkg2["Package:com.example.service"]
            fileOrderSvc["a/abc/OrderService.java"]
            classOrderSvc{{"OrderService"}}
            methodSave(("save"))
            
            fileOrderSvc --> classOrderSvc
            classOrderSvc --> methodSave
        end
    end
    
    subgraph block2["Block:b/module-handler"]
        subgraph pkg3["Package:com.handler.order"]
            fileHandler["b/handler/OrderHandler.java"]
            classHandler{{"OrderHandler"}}
            methodHandle(("handle"))
            
            fileHandler --> classHandler
            classHandler --> methodHandle
        end
    end
    
    methodCreate ==> methodSave
    methodSave ==> methodHandle

【输入】
'module_package_info'：{module_package_info}
'call_information'：{call_information}
'source_id'：{source_id}, 例如{{"189":"OrderController","190":"OrderController.createOrder"...}}

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
注意：mapping'中的每个节点对应的应该是'source_id'中的id，而不是行号或者名称
{{"mermaid": "这里是输出的Mermaid模块架构图", "mapping": "图中节点使用的类/方法在'source_id'，节点名和其对应id的映射关系，例如{{"classOrderCtrl":"189","methodCreate":"190"...}}"}}

"""
)

MERMIAD_DESC_PROMPT= PromptTemplate(
    input_variables=["chart_mermaid","chart_type","mermaid_source_info"],
    template="""
你是mermaid图解释专家，现在你需要为我输入给你的mermaid图进行简要精准的解释。
【输入】
输入的mermaid图内容'chart_mermaid'：{chart_mermaid}
图的类型'chart_type'：{chart_type}
生成该图时使用的信息'mermaid_source_info'：{mermaid_source_info}


【任务】
1、根据图的类型'chart_type'，结合'mermaid_source_info'，为我简要精准的解释该图表达的内容
2、解释内容要符合图的类型'chart_type'，例如代码控制流图、UML图
3、你的解释的信息来源必须完全基于'mermaid_source_info'，不能凭空添加任何信息
4、控制流图要结合代码逻辑进行解释，UML图要结合重点类和方法的关系进行解释
5、以子弹列表形式呈现，要排版逻辑清晰 


【输出格式】
内容直接是Markdown格式, 不要包含任何前言或解释, 直接输出中文Markdown格式。
"""
)

HYBRID_UML_DESC_PROMPT = PromptTemplate(
    input_variables=["chart_mermaid", "node_information"],
    template="""
你是Java项目架构分析专家。现在你需要为一个混合型模块的UML类图撰写说明。

该UML类图展示的是该模块**自身直接实现的类与其直接关联的子模块类**之间的关系。
图中已过滤掉与模块自身代码无直接关系的子模块，只保留有依赖交互的部分。

图的结构：
- 顶层的类（不在任何分组中）是该模块自身直接实现的代码
- 分组中的类属于与模块自身代码有直接依赖的子模块

### 输入
UML类图（Mermaid格式）：
```mermaid
{chart_mermaid}
```

模块结构信息（JSON格式）：
```json
{node_information}
```

### 任务
为该UML图撰写说明，分为三部分：

**第一部分：整体概述（2-3句）**
- 说明该模块自身直接实现了哪些核心类
- 这些核心类与哪些子模块存在依赖关系
- 整体呈现什么样的协作模式

**第二部分：关联子模块中的类说明**
按子模块分组，为每个子模块中的类撰写简要说明：
- 每个类1-2句，说明该类的职责和核心方法的作用
- 顶层类（模块自身直接实现的类）不需要描述（前文已有详细介绍）
- 重点说明类的关键方法做了什么，而不是罗列所有方法
- 说明该子模块中的类为什么会被模块自身的代码所依赖

**第三部分：关系线逐条解读**
逐条解释UML图中的**每条关系线**（即 `-->`, `<|..`, `<|--` 等连线），说明每条连线在业务上的含义。格式：
- `类A --> 类B`：一句话解释这条依赖在业务上意味着什么
- 如果是接口实现关系（`<|..`），说明这样设计的好处
- 如果是继承关系（`<|--`），说明继承的目的

### 要求
- 第二部分只描述子模块内的类，不要重复描述顶层类
- 输出文本中不要出现"namespace"一词，统一使用"模块"或"子模块"
- 第三部分只解释图中实际存在的关系线，不要编造图中没有的连线
- 每条连线的解释控制在1-2句
- 信息来源必须完全基于输入的UML图和JSON数据

【输出格式】
直接输出中文Markdown格式，不要包含任何前言或解释。
"""
)

PROJECT_MODULE_PROMPT = PromptTemplate(
    input_variables=["project_information", "pom_content"],
    template="""
你是模块架构分析专家, 我已经将一个java项目按照文件功能聚类为模块, 现在我需要你根据我给你的项目介绍和pom.xml内容, 为我画出该项目的模块架构示意图。
【输入】
代码模块架构'project_information'：{project_information}
pom.xml内容'pom_content'：{pom_content}
【任务】
1、根据'project_information'里节点的描述，为我设计模块节点，要求子模块要在父模块图中。
2、根据'pom_content'里描述的关系，和'project_information'里的path字段，为我画出模块之间的关系。
3、图中节点的名称必须和'project_information'里的name字段一致，不能修改节点名称。
4、图中节点的层级关系必须和'project_information'里一致，不能修改节点层级。
5、每个节点必须同时显示：
   第一行：name  
   第二行：path  
   两行之间用 `<br/>` 连接。
6、你只展示不属于一个顶层模块的跨模块关系, 不展示同模块内的关系。
【mermaid示例】
flowchart TD
    subgraph A["Admin System Core Suite<br/>mall-admin/src/"]
        A1["Admin System Application Layer<br/>../main/java/com/macro/mall/"]
        A2["Admin Config Management<br/>../config/"]
    end

    subgraph B["Core Utilities and Configuration<br/>mall-common/src/main/java/com/macro/mall/common/"]
    end

    A1 --> B
    A2 --> B

【输出格式】（严格JSON，不要包含任何其他解释、前言或Markdown标记）
{{"mermaid": "这里是输出模块架构图的Mermaid", "mapping": 图中每个节点名称和其在'project_information'里对应id的映射关系，例如{{"A":"1","A1":"2"...}}}}
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
