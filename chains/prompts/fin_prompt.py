from langchain.prompts import PromptTemplate
input_variables=["query", "all_information"],

UML_PROMPT = PromptTemplate(
    input_variables=["node_information"],
    template="""
现在我有一个Java项目。
"node_information"包含类的介绍和类之间的关系，你需要为我做出UML图，使用markdown语法并使用中文回复

下面是"node_information"的内容
```
{node_information}
```
要求：
1、体现"node_information"中所有节点和关系，接口、枚举、抽象类要用 `<<interface>>`、`<<enum>>`、`<<abstract>>` 标注
2、每个类节点的信息要包含类/接口和外界产生联系的属性和函数
3、关系例如实现、继承、使用、返回等要在图中体现
语法示例：
    OrderProcessor <|-- DomesticOrderProcessor
    OrderProcessor <|-- InternationalOrderProcessor
    OrderProcessor <|-- CODOrderProcessor


    class Order {{
        <<abstract>>
        #String orderId
        #BigDecimal amount
        #String status
        +validate() void
    }}
    **输出要求:**
1. 以 `## 5. 类之间关系说明` 作为唯一的 H2 标题。
2. 内容直接是Markdown格式, 不要包含任何前言或解释, 直接输出Markdown格式。
"""
)

CONTENT_PROMPT = PromptTemplate(
    input_variables=["class_information"],
    template="""
现在我有一个Java项目。
下面是关于其中一个类的所有介绍信息，你需要为我生成详细的介绍文档，来帮助我理解其职责、控制逻辑与配置方式，以便复用或扩展。
下面是关于这个类的所有介绍信息，来源包括源码、注释、注解、字段、方法签名等：
下面是"class_information"的内容
```
{class_information}
```
文档应包含以下部分
## 一、整体介绍
说明这个类在系统中的定位与职责，它解决了什么问题。
## 二、控制流
用mermaid语法做出图描述该类主要方法之间的调用关系。
## 三、关键属性与配置信息
说明该类的核心字段、配置项、外部资源。

    **输出要求:**
1. 以 `## 6. 数据结构说明` 作为唯一的 H2 标题。其子层级的内容标题应该分别是6.1, 6.1.1这种格式。
2. 内容直接是Markdown格式, 不要包含任何前言或解释, 直接输出Markdown格式。
3. 尽量使用表格＋文字描述等更美观的格式，不要使用子弹列表。

"""
)

INDIVIDUL_PROMPT = PromptTemplate(
    input_variables=["all_in"],
    template="""
### 角色与任务
# 你是代码语义分析专家，需基于源码生成**业务导向的语义控制流图(semantic cFG)**，并输出Mermaid图。严格遵循以下原则:
### 核心原则
1.**语义优先**
 - 用业务术语描述节点(如“记录I0延迟”而非“fopen(log_lat_path)”)
2. **结构化组织**
 - 用`subgraph 分组(如`Initialization,MainLoop`,cleanup`)
 - 层级不超过3层，确保视觉清晰度
3. **视觉差异化**
 - 决策点:菱形 + 白底细边框
 - 关键操作:深蓝填充 +粗边框(如`write block')
 - 错误路径:红色虚线边框 + 浅紅填充
 - 使用vs Code风格配色(主色:'#0af，｀#f96`，｀#fbb)
4. **复杂度控制**
 - 总节点数≤20(含决策点)
 - 合并非关键逻辑(如“更新统计”涵盖多行代码)
5. **节点标识规范**
 - 代号:唯一字母数字(如`A1'，“B3)，仅用于连接和样式
 - 标签:业务描述文本(如“分配SSD缓存缓冲区”)

 --- 
### 输入信息
1.**源代码和相关解释**
```
{all_in}
```
 --- 
### 输出格式
使用markdown语法并使用中文回复
内容直接是Markdown格式，不要包含任何前言或解释，直接输出Markdown格式。

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
---

### 校验规则
1. **行号精确性**  
   - 每节点必须覆盖实际行号，多段代码用数组（如`["49", "55-59"]`）
2. **业务语义对齐**  
   - 节点描述需从`语义解释`中提炼，避免技术术语
3. **视觉一致性**  
   - 所有错误节点统一用`stroke-dasharray:5 5`
   - 线条加粗：关键路径`stroke-width:3px`，默认`2px`
4. **代码合规性**  
   - 禁用Mermaid不支持的CSS（如`border-radius`）
   - 子图命名用英文（如`MainLoop`而非`主循环`）
5. **确保JSON可以被标准解析器解析**
		- mermaid字符串复制到Mermaid编辑器中应能正常渲染
		- 节点标签中的换行符应显示为实际换行，而非 `\\n` 文本
6. **使用方括号代替花括号**

"""
)