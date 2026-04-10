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

### 3. Claude Code CLI（可选，启用 step2 扩展章节 / step8 时必需）

step2 的 Root 文档扩展章节和 step8 的 Block 级可选章节**依赖本地 `claude` 命令**（Claude Code CLI），由 Claude 自主读源码生成高质量内容。如果不使用这两个功能，可以跳过本小节。

**安装 Claude Code CLI**：

```bash
# macOS / Linux
brew install anthropics/tap/claude       # Homebrew
# 或
npm install -g @anthropic-ai/claude-code  # npm

# 验证
which claude   # 应能输出 claude 可执行文件路径
claude --version
```

**登录 / 配置**：首次使用需要运行 `claude` 并按提示登录 Anthropic 账号，CLI 会使用你的 Claude 订阅进行调用（**不占用项目的 `OPENAI_API_KEY`**，是独立的计费通道）。

**什么时候需要**：

| 场景 | 是否需要 Claude CLI |
|---|---|
| 默认 `python run_all.py` 跑完整 7 步 | ❌ 不需要（未配置 `SOURCE_ROOT_PATH` 时自动跳过扩展章节） |
| step2 生成技术栈/分层/核心类等扩展章节 | ✅ 需要（`SOURCE_ROOT_PATH` + `claude`） |
| `python run_all.py --run-optional` 生成状态机/MQ 可选章节 | ✅ 需要 |
| 单独运行 `python workflows/optional_sections_workflow.py` | ✅ 需要 |

**为什么用 Claude CLI 而不是 OpenAI API**：这两个扩展功能需要**真实读取源码**文件（Grep / Read / Glob 大量源码文件来总结），Claude Code 内置工具可以直接访问本地文件系统，OpenAI API 做不到。

### 4. 环境变量

手动创建 `.env` 文件（已在 `.gitignore` 中），参考 [.env.example](.env.example)：

```bash
# Neo4j 连接（必需）
WIKI_NEO4J_URI=bolt://localhost:7689
WIKI_NEO4J_USER=neo4j
WIKI_NEO4J_PASSWORD=your_password

# LLM API（必需）
OPENAI_API_KEY=your_api_key
BASE_URL=https://api.openai.com/v1       # 或自建 OpenAI 兼容网关
LLM_MODEL=gpt-5-mini                     # 所有 step 的默认模型
LLM_PROVIDER=openai

# 并发 / 超时 / 重试（可选）
MAX_CONCURRENT_BLOCKS=10                 # Block 生成并发度，默认 10
LLM_TIMEOUT=120                          # step5 API 文档的 urllib 单次超时（秒）
LLM_CHAIN_MAX_RETRIES=4                  # LangChain 链路 transient error 重试次数

# 源码路径前缀（可选，默认 "mall"，用于 API 文档 / RabbitMQ 分析中拼接文件路径）
ROOT_PREFIX=mall

# ====== 以下仅在使用 Claude CLI 扩展章节 / 可选章节时需要 ======
# Java 源码根目录（绝对路径），被 step2 扩展章节和 step8 共用
# SOURCE_ROOT_PATH=/path/to/java/source/root

# Claude CLI 使用的模型，默认 sonnet，可选 opus / haiku
# CLAUDE_MODEL=sonnet

# Claude CLI 单次调用超时（秒）
# AGENT_TIMEOUT=600

# Claude CLI 调用失败重试次数
# AGENT_MAX_RETRIES=2
```

**关于环境变量的透传**：

- `run_all.py` 在启动时会 `load_dotenv()`，然后在 step5/6/7 自动把 `WIKI_NEO4J_*` / `OPENAI_API_KEY` / `BASE_URL` 映射到 `Api_and_Rabbitmq/` 里脚本期望的变量名（`NEO4J_*` / `LLM_API_KEY` / `LLM_BASE_URL`），无需在 .env 里重复配置
- 若看到 `ConnectError` 且 trace 里出现 `http_proxy.py`，检查 shell 里是否有 `HTTPS_PROXY` 指向不可达的代理。默认情况下 `interfaces/llm_interface.py` 会把 `.env` 里的 `BASE_URL` 传给 `ChatOpenAI`，使请求走 HTTP 而非 HTTPS，代理将被自动绕过
- **Claude CLI 不经过 `.env`** — Claude Code CLI 使用它自己的登录态（`~/.claude/` 下的配置），与 `OPENAI_API_KEY` 完全独立

## 快速开始

### 一键生成全部文档

```bash
python run_all.py
```

默认启用 `--skeleton` 源码精简模式，**执行 7 个步骤**（step8 默认关闭，见下方说明）：

1. **模块取名** — 为每个 Block 生成可读名称 → `graph/block_new_names.json`
2. **Root 文档** — 生成项目总览页 → `output/root_doc.meta.json`
3. **中间层 Block** — 生成中间层模块文档 + 分类叶子/混合 Block
4. **叶子 + 混合 Block** — 并发生成所有末端模块文档
5. **API 文档** — 扫描 Controller 生成 REST API 接口文档 → `output/API说明文档/*.meta.json`（与步骤 4 并发）
6. **后端集成清单** — 扫描 RabbitMQ/定时任务/ES/Mongo/Redis/OSS 依赖 → `output/后端接口清单.meta.json`（与步骤 4/5 并发）
7. **RabbitMQ 消息流分析** — 确定性查询 + LLM 结构化提取 + 链路匹配 → `output/RabbitMQ消息流分析.meta.json`（与步骤 4/5/6 并发）
8. **Block 级可选章节**（**⚠️ 默认关闭**）— 为每个 Block 追加状态机/消息队列等可选章节

步骤 4-7 在同一个 `asyncio.gather` 里并发执行，显著缩短总耗时。步骤 8 依赖步骤 4 的产物，必须串行在并发块之后。

### ⚠️ 步骤 8（Block 级可选章节）默认关闭

步骤 8 代价较高，**不会在默认 `python run_all.py` 中自动运行**。原因：

- **扫描阶段**：对所有 root 分支 × 每个可选章节类型各发一次 OpenAI LLM 调用做相关性判断，中型项目约 10-20 次调用、每次 3-10k tokens
- **生成阶段**：对识别出的每个 `(Block, 章节类型)` 组合调用一次本地 `claude` CLI 进程，Claude 自主读源码生成内容，单次几分钟级
- **两个硬依赖**：
  1. `.env` 里配好 `SOURCE_ROOT_PATH`（Java 源码根目录的绝对路径）
  2. 本地安装了 Claude Code CLI，且 `which claude` 能找到它（参见 [环境准备 § 3](#3-claude-code-cli可选启用-step2-扩展章节--step8-时必需)）
- 适合只在**需要补充状态机/MQ 分析**时显式启用，而不是作为默认流程的一部分

任一前置条件缺失时，步骤 8 会**自动跳过并 warning**，不会导致整个流程失败。

显式启用步骤 8：

```bash
# 前置：
#   1. pip install / npm install 都已完成
#   2. .env 里配好 SOURCE_ROOT_PATH=/path/to/java/source/root
#   3. which claude 能找到 Claude Code CLI
python run_all.py --run-optional
```

未启用时，日志会显示：
```
[INFO] 跳过步骤8（Block 级可选章节）—— 如需启用请加 --run-optional
```

前置缺失时，日志会显示：
```
[WARNING] 未配置 SOURCE_ROOT_PATH，跳过步骤 8（Block 级可选章节）
[WARNING] 未找到 claude CLI，跳过步骤 8（请先安装 Claude Code）
```

### 关于 step2 的扩展章节（也依赖 Claude CLI）

步骤 2 Root 文档默认会生成三个基础章节（项目介绍 / 模块架构 / 架构图）。如果 `.env` 中配置了 `SOURCE_ROOT_PATH` 并且本地装了 Claude Code CLI，**会自动补充 5 个扩展章节**：

| 章节 | 内容 |
|---|---|
| 技术栈概览 | 扫 pom.xml / 注解 / application.yml 自动识别 |
| 分层架构设计 | 扫 Controller/Service/DAO 分层生成 mermaid 图 |
| 核心类与接口 | 识别最核心的 Service 接口和实现类，生成类图 |
| 核心业务流程 | 追跨模块调用链，生成时序图 |
| 核心数据模型 | 扫实体类生成 ER 图 |

与步骤 8 的区别：**步骤 2 扩展章节不需要额外加 `--run-optional` 开关**，只要 `SOURCE_ROOT_PATH` 有配且 claude CLI 可用就会自动启用。两者的执行代价差异：

|  | step2 扩展章节 | step8 可选章节 |
|---|---|---|
| 扫描代价 | 无（直接 claude CLI 决策） | 对所有 Block 做 LLM 相关性评分 |
| 生成代价 | 5 次 claude CLI 调用（项目级） | `N × M` 次（Block 数 × 章节类型数） |
| 默认行为 | 自动（`SOURCE_ROOT_PATH` 存在就跑） | **默认关闭**，需要 `--run-optional` |

如果想跳过 step2 扩展章节（只保留 1-3 章），不要配 `SOURCE_ROOT_PATH`，或用 `--skip-root`（但这会连基础 1-3 章一起跳过）。

### 常用命令

```bash
# 默认：跑 step1~7，跳过 step8
python run_all.py

# 完整跑 step1~8（包括 Block 级可选章节，需 SOURCE_ROOT_PATH + claude CLI）
python run_all.py --run-optional

# 关闭源码精简（当 LLM 上下文充足、追求更完整的 UML 细节时）
python run_all.py --no-skeleton

# 指定模型
python run_all.py --model gpt-4.1 --provider openai

# 跳过已完成/不需要的步骤
python run_all.py --skip-name --skip-root    # 跳过取名和 Root
python run_all.py --skip-api                 # 跳过 API 文档生成
python run_all.py --skip-backend             # 跳过后端集成清单
python run_all.py --skip-rabbitmq            # 跳过 RabbitMQ 消息流分析
python run_all.py --only-leaves              # 只跑叶子+混合 Block（仍会跳过 5/6/7/8）

# 单独生成某个 Block 节点
python generate_wiki.py 318
python generate_wiki.py 318 327 --skeleton

# 批量生成混合型 Block
python generate_hybrid_batch.py --skeleton --ids 18468 18475

# 单独运行 API / RabbitMQ 分析（需在 shell 里 export 对应环境变量）
python Api_and_Rabbitmq/generate_api_docs.py
python Api_and_Rabbitmq/generate_backend_interfaces.py
python Api_and_Rabbitmq/rabbitmq_analyzer/analyzer_v3.py

# 单独跑 Block 级可选章节工作流（不经过 run_all）
python workflows/optional_sections_workflow.py --list-sections
python workflows/optional_sections_workflow.py                        # 对所有 Block 跑所有可选章节
python workflows/optional_sections_workflow.py --section state_machine  # 只做状态机
python workflows/optional_sections_workflow.py --block "Portal Order Service"  # 只做指定 Block
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

### 单个 Block 的内部并发

```
章节1: generate_summary
    ├── 章节2: generate_components  ─┐
    ├── 章节3: architecture_diagram ─┤
    ├── 章节4: main_control_flow    ─┤── 全部完成 → 合并输出
    │       └── 章节6: data_uml     ─┤
    └── 章节5: module_relation      ─┘
```

章节 1 先执行，然后 2/3/4/5 并发，章节 6 等章节 4 完成后执行。

### 全局步骤之间的并发

`run_all.py` 中步骤 4-7 共享同一个 `asyncio.gather`：

```
step1: 模块取名 ──▶ step2: Root 文档 ──▶ step3: 中间层 Block
                                              │
                                              ▼
                                   ┌──────────┴──────────┬──────────────┐
                                   ▼                     ▼              ▼
                             step4: 叶子+混合      step5: API 文档   step6: 后端集成清单
                                                                       ▼
                                                                 step7: RabbitMQ 消息流
                                                 （step4/5/6/7 同时执行）
```

- 步骤 4 由 `MAX_CONCURRENT_BLOCKS` 控制 LLM 调用并发
- 步骤 5/6/7 各自是一个独立任务，通过 `asyncio.gather` 与步骤 4 一起并发推进
- 任一专项步骤失败不会影响其它步骤（通过 `try/except` 隔离）

## 专项文档生成器

`Api_and_Rabbitmq/` 下的三个脚本都是**独立的 `.meta.json` 生成器**，与 Block 文档使用相同的输出格式，便于前端统一消费。

### step5 — REST API 文档（[generate_api_docs.py](Api_and_Rabbitmq/generate_api_docs.py)）

- 扫描 `@RestController` / `@Controller`，结合 LLM 生成模块介绍、架构分析、请求/响应示例
- 支持自动解析 `@PathVariable` / `@RequestParam` / `@RequestBody` + DTO 字段
- 按模块分组输出到 `output/API说明文档/<模块名>.meta.json`
- 每个方法配 Mermaid 时序图（调用链 trace）

### step6 — 后端集成清单（[generate_backend_interfaces.py](Api_and_Rabbitmq/generate_backend_interfaces.py)）

- **不调用 LLM**，全靠 Cypher 查询 + 正则解析，速度快
- 六个章节：概览、RabbitMQ、定时任务、ES/Mongo、Redis、OSS/MinIO
- 解析 Spring `application.yml`（自动匹配 `spring.profiles.active`）以解析配置占位符
- 解析枚举常量的构造函数参数（如 `QueueEnum.QUEUE_ORDER_CANCEL` → 真实 queue 名）
- 输出 `output/后端接口清单.meta.json`

### step7 — RabbitMQ 消息流分析（[analyzer_v3.py](Api_and_Rabbitmq/rabbitmq_analyzer/analyzer_v3.py)）

- 使用 **analyzer_v3**（v1/v2 已弃用，v3 直接产出 `.meta.json`）
- 流程：确定性 Cypher 查询 → LLM 结构化提取（每个组件的 queue/exchange/routing key）→ 确定性链路匹配（基于 RabbitMQ 语义）
- 识别 **TTL + 死信队列** 的延时消息链路
- 每条消息流转链路配 Mermaid `graph LR` 可视化图
- 输出 `output/RabbitMQ消息流分析.meta.json`

## 目录结构

```
java_wiki/
├── run_all.py                    # 全局启动脚本（7 步并发执行）
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
│   ├── llm_interface.py          #   LLM 多提供商抽象（OpenAI/Claude/Google，支持自定义 base_url）
│   └── simple_validate_mermaid.py#   Mermaid 图表校验器
│
├── Api_and_Rabbitmq/             # 专项文档生成器（独立脚本，被 run_all 集成）
│   ├── generate_api_docs.py      #   REST API 文档（StrictApiDocGenerator，LLM 增强）
│   ├── generate_backend_interfaces.py  # 后端集成清单（扫描 MQ/DB/Cache/OSS，无 LLM）
│   └── rabbitmq_analyzer/        #   RabbitMQ 消息流分析
│       ├── analyzer.py           #     v1 — 锚点 + LLM 逐个分析（已弃用）
│       ├── analyzer_v2.py        #     v2 — 全量查 + 正则解析（已弃用）
│       ├── analyzer_v3.py        #     v3 — 确定性查询 + LLM 结构化提取（run_all 采用）
│       └── llm_interface.py      #     独立的轻量 LLM 客户端（httpx + OpenAI 兼容）
│
├── scripts/
│   └── validate_mermaid.mjs      # Node.js Mermaid 语法校验（替代 Chrome）
│
├── output/                       # 生成的 Wiki 文档（.meta.json）
│   ├── API说明文档/              #   step5 输出：按模块分组的 API 接口文档
│   ├── 后端接口清单.meta.json     #   step6 输出：后端集成清单
│   └── RabbitMQ消息流分析.meta.json  # step7 输出：MQ 消息流转
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

### UML 输入优化（默认开启）

UML 图生成时，`--skeleton` 模式（默认开启）将完整 Java 源码压缩为结构化摘要：

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

配合跨类去重，总 token 减少约 98%。如果追求更完整的 UML 细节，可以用 `--no-skeleton` 关闭。

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
- 步骤 5/6/7 中任一专项失败不会中断其它步骤（通过 `try/except` 隔离，失败时写 error log 继续）
- 若 `OPENAI_API_KEY` 未配置，步骤 5/7 会降级或跳过（步骤 5 输出无 LLM 增强内容，步骤 7 直接跳过并 warning）
- 步骤 6 不依赖 LLM，只要 Neo4j 可连通即可运行，适合在 CI 环境离线生成
- **Claude CLI 与 OpenAI API 是两条独立通道**：
  - OpenAI API 通过 `OPENAI_API_KEY` + `BASE_URL` 配置，被 step1-7 使用
  - Claude Code CLI 使用本地 `~/.claude/` 下的登录态，被 step2 扩展章节、step8 使用
  - 两者互不影响，单独缺失不会影响另一条通道
- Claude CLI 是**本地子进程**，并发数受 `MAX_CONCURRENT_BLOCKS` 控制，建议不超过 5（CPU / 网络压力大）
