# RabbitMQ Flow Analyzer

通用的 RabbitMQ 消息链路分析工具，基于 Neo4j 图数据库和 LLM 分析。

## 功能特点

- **锚点发现**: 通过 Cypher 查询自动发现 RabbitMQ 相关组件（Consumer/Producer/Config）
- **语义分析**: 利用 LLM 理解代码语义，提取消息队列配置信息
- **迭代探索**: 根据 LLM 分析结果，递归查找相关枚举定义、配置等
- **链路组装**: 综合所有信息，构建完整的消息流转链路
- **报告生成**: 生成包含 Mermaid 图表的 Markdown 分析报告

## 工作原理

1. **锚点发现**: 从 Neo4j 查找所有带 `@RabbitListener`、注入 `RabbitTemplate` 的类、`@Bean` 配置等
2. **LLM 分析**: 使用 LLM 分析每个组件的源代码，提取队列名、交换机、路由键等信息
3. **迭代探索**: 根据提取的枚举引用，在图中查找枚举定义；分析死信队列（DLX）配置
4. **链路组装**: 让 LLM 根据所有收集的信息，推理出完整的消息流转路径
5. **报告生成**: 输出 Markdown 报告，包含流程图和详细分析

## 前置条件

1. **Neo4j 数据库**: 需要运行 Neo4j，并已导入 Java 项目的代码图
2. **LLM API**: 需要 OpenAI API key（或兼容的服务，如 DeepSeek）
3. **Python 3.8+**

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

通过环境变量配置：

```bash
# Neo4j 配置
export NEO4J_URI="bolt://localhost:7689"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"

# LLM 配置
export LLM_PROVIDER="openai"          # 或 "deepseek"
export LLM_MODEL="gpt-4o-mini"        # 或 "deepseek-chat"
export OPENAI_API_KEY="sk-..."        # OpenAI API Key
# export DEEPSEEK_API_KEY="sk-..."   # DeepSeek API Key (如使用 DeepSeek)
```

Windows 用户使用 `set` 代替 `export`：

```cmd
set OPENAI_API_KEY=sk-...
```

## 运行

```bash
cd scripts/rabbitmq_analyzer
python analyzer.py
```

运行完成后，会在当前目录生成 `rabbitmq_flow_report.md` 报告文件。

## 输出报告示例

报告包含：

- **Overview**: 发现的组件统计
- **Message Flows**: 识别出的消息流转链路（带 Mermaid 流程图）
- **Unlinked Components**: 未能关联的生产者/消费者
- **Component Details**: 每个组件的详细分析结果（JSON 格式）

## 适用场景

- 分析 Spring Boot + RabbitMQ 项目的消息流转关系
- 理解延时队列 + 死信队列的实现
- 找出生产者和消费者的对应关系
- 文档化消息队列架构

## 限制

- 需要代码已导入 Neo4j 图数据库
- 依赖 LLM 进行语义分析（需要 API 调用）
- 对复杂的动态配置可能识别不完整

## 目录结构

```
rabbitmq_analyzer/
├── analyzer.py           # 主分析脚本
├── llm_interface.py      # LLM 接口封装
├── requirements.txt      # 依赖列表
└── README.md             # 本文档
```

## 许可证

MIT
