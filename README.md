# Java Wiki — Java 代码库自动化文档生成系统

将大型 Java 代码库解析为 Neo4j 知识图谱，基于图谱数据通过 LLM 自动生成结构化 Wiki 文档。

## 项目架构

```
Java 代码库 → Neo4j 知识图谱 → LLM + LangGraph 工作流 → Wiki 文档（JSON）
```

系统将代码中的实体（类、接口、方法、字段等）存储为 Neo4j 节点，将依赖关系（调用、继承、实现等）存储为边。然后按模块（Block）层级自动生成包含文字说明、Mermaid 图表、源码定位的完整 Wiki 页面。

## 环境准备

### 1. Python 依赖

```bash
pip install -r requirement.txt
```

核心依赖：
- `langchain` + `langgraph` — LLM 编排框架
- `neo4j` — 图数据库驱动
- `langchain-openai` / `langchain-anthropic` / `langchain-google-genai` — LLM 提供商

### 2. Node.js 依赖

用于 Mermaid 图表语法校验：

```bash
npm install
```

### 3. 环境变量

复制 `.env.example` 或手动创建 `.env` 文件，配置以下变量：

```bash
# Neo4j 连接（必需）
WIKI_NEO4J_URI=bolt://localhost:7689
WIKI_NEO4J_USER=neo4j
WIKI_NEO4J_PASSWORD=your_password

# LLM API（必需）
OPENAI_API_KEY=your_api_key
BASE_URL=https://api.openai.com/v1

# 并发控制（可选）
MAX_CONCURRENT_BLOCKS=10
```

## 快速开始

### 一键生成全部文档

```bash
python run_all.py --skeleton
```

执行 4 个步骤：

1. **模块取名** — 为每个 Block 生成可读名称 → `graph/block_new_names.json`
2. **Root 文档** — 生成项目总览页 → `output/root_doc.meta.json`
3. **中间层 Block** — 生成中间层模块文档 + 分类叶子/混合 Block
4. **叶子 + 混合 Block** — 并发生成所有末端模块文档

### 常用命令

```bash
# 完整执行
python run_all.py

# 指定模型
python run_all.py --model gpt-4.1 --provider openai

# 精简 UML 输入（减少 token 消耗）
python run_all.py --skeleton

# 跳过已完成的步骤
python run_all.py --skip-name --skip-root    # 跳过取名和 Root
python run_all.py --only-leaves              # 只跑叶子+混合 Block

# 单独生成某个节点
python generate_wiki.py 318
python generate_wiki.py 318 327 --skeleton

# 批量生成混合型 Block
python generate_hybrid_batch.py --skeleton --ids 18468 18475
```

## 代码逻辑

### Block 类型与工作流

系统将代码模块分为三种类型，每种对应不同的工作流：

| Block 类型 | 特征 | 工作流 | 输出章节 |
|-----------|------|--------|---------|
| 叶子 Block | 只有直连 File，无子 Block | `block_module_workflow` | 6 章 |
| 中间层 Block | 只有子 Block，无直连 File | `internal_block_workflow` | 2 章 |
| 混合型 Block | 既有直连 File 又有子 Block | `hybrid_block_workflow` | 6 章 |

### 叶子 Block Wiki 结构（6 章）

| 章节 | 内容 | 生成方式 |
|------|------|---------|
| 1. 模块功能概述 | 模块定位和职责 | LLM 生成 |
| 2. 核心组件介绍 | 类/接口的详细说明 | Neo4j 查询 + 模板 |
| 3. 模块内架构图 | File 间依赖关系图 | LLM 生成 Mermaid |
| 4. 关键控制流 | 核心方法的 CFG 图 | LLM 生成 Mermaid |
| 5. 模块关系 | 与兄弟模块的依赖 | LLM 生成 |
| 6. 数据结构 UML | 类关系图 | LLM 生成 Mermaid |

### 混合型 Block Wiki 结构（6 章）

与叶子 Block 类似，但有两个关键区别：
- **章节 2** 同时包含核心组件（直连 File）和子模块概览
- **章节 6** 使用 `namespace` 分组，区分直连类和子模块类

### 并发执行流程

```
章节1: generate_summary
    ├── 章节2: generate_components  ─┐
    ├── 章节3: architecture_diagram ─┤
    ├── 章节4: main_control_flow    ─┤── 全部完成 → 合并输出
    │       └── 章节6: data_uml     ─┤
    └── 章节5: module_relation      ─┘
```

章节 1 先执行，然后 2/3/4/5 并发，章节 6 等章节 4 完成后执行。

## 目录结构

```
java_wiki/
├── run_all.py                    # 全局启动脚本（4 步顺序执行）
├── generate_wiki.py              # 单节点/全量生成脚本
├── generate_hybrid_batch.py      # 混合型 Block 批量生成
│
├── workflows/                    # LangGraph 工作流定义
│   ├── root_doc_workflow.py      #   Root Block 文档
│   ├── internal_block_workflow.py#   中间层 Block 文档
│   ├── block_module_workflow.py  #   叶子 Block 文档（6 章节）
│   └── hybrid_block_workflow.py  #   混合型 Block 文档（6 章节）
│
├── graph/                        # 图表生成与分析
│   ├── four_chart.py             #   4 种图表生成（CFG/UML/时序/模块图）
│   ├── module_name.py            #   Block 命名
│   ├── module_target.py          #   模块关系分析
│   └── id_generate.py            #   源码行号定位
│
├── chains/                       # LLM Chain 定义
│   ├── common_chains.py          #   通用 Chain 工厂
│   └── prompts/                  #   提示词模板
│       ├── block_doc_prompt.py   #     Block 文档相关提示词
│       ├── type_chart_prompt.py  #     图表生成提示词（CFG/UML/时序）
│       ├── root_doc_prompt.py    #     Root 文档提示词
│       └── ...
│
├── interfaces/                   # 外部服务接口
│   ├── neo4j_interface.py        #   Neo4j 异步查询接口
│   ├── llm_interface.py          #   LLM 多提供商抽象（OpenAI/Claude/Google）
│   └── simple_validate_mermaid.py#   Mermaid 图表校验器
│
├── scripts/
│   └── validate_mermaid.mjs      # Node.js Mermaid 语法校验（替代 Chrome）
│
├── output/                       # 生成的 Wiki 文档（JSON）
├── internal_result/              # 中间结果（Block 分类列表）
└── logs/                         # 执行日志
```

## 输出格式

每个 Block 生成一个 JSON 文件，结构如下：

```json
{
    "wiki": [
        {
            "markdown": "# 章节标题\n内容...",
            "neo4j_id": {
                "小标题": ["nodeId1", "nodeId2"]
            }
        },
        {
            "mermaid": "# 图表标题\n```mermaid\nclassDiagram\n...\n```\n说明文字",
            "mapping": {
                "MermaidNodeId": "source_id"
            }
        }
    ],
    "source_id_list": [
        {
            "source_id": "1234",
            "name": "com/example/Service.java",
            "lines": ["10-50", "60-80"]
        }
    ]
}
```

- `wiki` 数组中每个元素对应一个章节
- `markdown` 章节用 `neo4j_id` 关联到图谱节点
- `mermaid` 章节用 `mapping` 将图中节点映射到 `source_id_list` 中的源码位置
- `source_id_list` 提供源码文件路径和行号范围，供前端跳转

## 关键设计

### UML 输入优化

UML 图生成时，通过 `--skeleton` 模式将完整 Java 源码压缩为结构化摘要：

```
# 原始源码（~1500 tokens）
public class OrderService extends BaseService {
    @Autowired private OrderDao orderDao;
    public Order createOrder(CreateOrderRequest req) {
        // 100 行实现...
    }
}

# 结构化摘要（~60 tokens）
public class OrderService extends BaseService
fields: private OrderDao orderDao
methods: public createOrder(CreateOrderRequest):Order
```

配合跨类去重，总 token 减少约 98%。

### Mermaid 校验

使用 Node.js + `mermaid.parse()` 做纯语法校验，无需启动 Chrome 浏览器，速度提升 5-10 倍。校验脚本位于 `scripts/validate_mermaid.mjs`。

### 并发控制

通过 `MAX_CONCURRENT_BLOCKS` 环境变量控制并发 LLM 调用数量，避免超出 API 速率限制：
- GPT-4 Tier 1（500 RPM）：建议 10-20
- GPT-4 Tier 2（5000 RPM）：建议 50-100

## 注意事项

- 系统**只读取** Neo4j 数据，不会写入任何数据到数据库
- 所有输出写入本地 `output/` 目录
- 日志文件按时间戳存储在 `logs/` 目录
- `graph/block_new_names.json` 是所有工作流的共享依赖，步骤 1 生成后后续步骤引用
