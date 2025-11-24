from langchain.prompts import PromptTemplate


API_FILE_PROMPT = PromptTemplate(
    input_variables=["file_introduction"],
    template="""
### 角色与任务
你是代码语义分析与文档生成专家，我会给你提供代码片段的信息，
你是代码语义分析专家，需基于源码生成**业务导向的语义控制流图(Semantic CFG)**，并输出包含映射关系和Mermaid图的JSON。严格遵循以下原则：

### 核心原则
1. **语义优先**  
   - 用业务术语描述节点（如“记录IO延迟”而非“fopen(log_lat_path)”）
   - 关键对象（如`{{key_objects}}`）需突出但简化（最多3步）

2. **结构化组织**  
   - 用`subgraph`分组（如`Initialization`, `MainLoop`, `Cleanup`）
   - 层级不超过3层，确保视觉清晰度

3. **视觉差异化**  
   - 决策点：菱形 + 白底细边框  
   - 关键操作：深蓝填充 + 粗边框（如`write_block`）  
   - 错误路径：红色虚线边框 + 浅红填充  
   - 使用VS Code风格配色（主色：`#0af`, `#f96`, `#fbb`）

4. **复杂度控制**  
   - 总节点数≤20（含决策点）
   - 合并非关键逻辑（如“更新统计”涵盖多行代码）

5. **节点标识规范**  
   - 代号：唯一字母数字（如`A1`, `B3`），仅用于连接和样式  
   - 标签：业务描述文本（如“分配SSD缓存缓冲区”）  

---

### 输入信息
1. **源代码**  
   ```
   {{source_code}}
   ```
2. **关键对象**  （必须在图中突出显示）
   {{key_objs}}

3. **语义解释**  
   ```json
   {{code_context}}
   ```

---

### 输出格式
输出**严格遵循此JSON结构**：
```json
{
  "mapping": {
    "节点代号": {
      "lines": ["行号或区间"],
      "description": "业务描述文本"
    },
    // ...其他节点
  },
  "mermaid": "MermaidJS代码字符串"
}
```

#### 字段说明

`mapping`: - Key为节点代号（如`B2`）<br>- `lines`：数组，行号用区间表示（如`["24", "31-34"]`）<br>- `description`：直接使用Mermaid中的节点标签文本 |
`mermaid`: 需满足：<br>1. 开头声明流向：`flowchart TD` 或 `flowchart TB`<br>2. 用`%%`注释分组逻辑<br>3. 关键对象样式：`style 节点代号 fill:#0af,stroke:#036,stroke-width:4px`<br>4. 错误路径样式：`stroke-dasharray: 5 5,stroke:#a00` |

#### Mermaid示例
```mermaid
flowchart TD
    direction TB
    subgraph Initialization
        A1["打开日志文件\n(准备记录IO延迟)"]
        A3{"内存分配成功?"} 
        style A3 fill:#fff,stroke:#333,stroke-width:2px,shape:diamond %% 决策点
    end
    A1 --> A3
    style A1 fill:#0af,stroke:#036,stroke-width:4px %% 关键操作
```
#### mermaid字段特别要求：
1. **字符串转义规则**：
   - 换行符使用：`\n`
   - 双引号使用：`\"` （仅JSON级别转义）
   - 反斜杠使用：`\\`

2. **Mermaid节点标签格式**：
   ```json
   "mermaid": "flowchart TD\n    A1[\"节点描述文本\"]\n    A2{\"决策点描述\"}"
   ```
   
3. **禁止双重转义**：
   - ✅ 正确：`A1[\"打开日志文件\\n(准备记录IO延迟)\"]`
   - ❌ 错误：`A1[\\\"打开日志文件\\\\n(准备记录IO延迟)\\\"]`

#### 完整示例：
```json
{
  "mapping": { ... },
  "mermaid": "flowchart TD\n    direction TB\n    A1[\"初始化系统\"]\n    A2{\"检查状态?\"}\n    A1 --> A2"
}
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
6. **使用方括号代替花括号**：
   - 决策节点：`A2[\"决策点描述\"]` 而非 `A2{\"决策点描述\"}`
"""
)

# 【query, relation,all_information】
# 测试 query："前台是如何配置并调用支付宝客户端来处理支付和回调的？"
# 初始 file_name（file_list）：[559]
# 找到的block_id: [18394]
# 预期结果：[497, 498, 559]


# 测试 query："前台是如何完成会员登录、生成 JWT、缓存会员资料的？"
# 初始 file_name（file_list）：[573]
# 找到的block_id: [18354]
# 预期结果：[573, 570]

# 测试 query："前台如何完成会员登录、生成 JWT、缓存会员资料，配置并调用支付宝客户端来处理支付和回调的?"
# 初始 file_name（file_list）：[573, 559]
# 找到的block_id: [18354, 18394]
# 预期结果：[573, 570, 497, 498, 559]
