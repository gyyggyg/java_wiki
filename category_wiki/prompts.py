"""各章节的 LLM prompt 模板"""

from langchain.prompts import PromptTemplate


# §1 业务概述
OVERVIEW_PROMPT = PromptTemplate(
    input_variables=["category_path", "category_description", "class_briefs", "pages_brief"],
    template="""你是一个技术文档撰写者。任务：为下列"业务流分类"撰写 2-3 段中文业务概述。

## 分类信息
- 分类路径: {category_path}
- 分类描述: {category_description}

## 该分类下聚合的 wiki 页面（简介）
{pages_brief}

## 该分类下核心类/接口（带 SE_What/SE_Why 语义解释）
{class_briefs}

## 要求
1. 概述要体现业务价值（解决什么问题、面向谁、产生什么结果），**不是罗列类名**
2. 第一段: 一句话业务定位 + 读者群体
3. 第二段: 关键能力 / 核心业务对象 / 典型使用场景
4. 第三段（可选）: 与其它分类的协作关系（如果能从页面描述中看出来）
5. 总长度 250-400 字，用 Markdown
6. 不要输出标题 "## 1. 业务概述" —— 只输出正文段落

【输出格式】（严格 JSON，无围栏、无前言）
{{"markdown": "这里是概述的 markdown 正文，只包含段落文本"}}
"""
)


# §2 触发入口 — 新版策略: 直接看所有类源码 + SE_What 由 LLM 自己判断
ENTRYPOINTS_PROMPT = PromptTemplate(
    input_variables=["category_path", "class_contexts"],
    template="""你是 Java 代码分析专家。下面是一个业务分类下**所有相关类**的源码与语义解释。
你的任务：**直接从源码里分析**这个业务模块的所有触发入口（能由外部触发进入本模块逻辑的位置）。

## 分类路径
{category_path}

## 输入类上下文
{class_contexts}

## 触发入口类型（需全部识别）
1. **HTTP 接口**：类有 `@RestController` / `@Controller` 且方法有 `@GetMapping` / `@PostMapping` / `@PutMapping` / `@DeleteMapping` / `@RequestMapping` / `@PatchMapping`
2. **定时任务**：方法注解 `@Scheduled`（读注解里的 `cron` / `fixedRate` / `fixedDelay` 参数）
3. **消息消费**：方法或类注解 `@RabbitListener` / `@RabbitHandler` / `@KafkaListener` / `@JmsListener` / `@StreamListener`
4. **事件监听**：方法注解 `@EventListener` / `@ApplicationListener`
5. **生命周期回调**：`@PostConstruct` / `@PreDestroy` / 实现 `InitializingBean` / `ApplicationRunner` / `CommandLineRunner`
6. **其它**：Feign 客户端接口（`@FeignClient`）、gRPC Server 方法、WebSocket Handler 等被框架反射调用的方法

## 工作步骤
1. 扫描每个类的源码开头（类注解）和每个方法的方法签名上方（方法注解）
2. 识别出符合上述 6 类的入口方法
3. 针对每个入口，从源码/SE_What 推断它的业务作用
4. 按 HTTP / 定时任务 / MQ / 其它 分组整理

## 输出要求
- 按 4 类分子节（### 2.1 HTTP 接口 / ### 2.2 定时任务 / ### 2.3 消息消费 / ### 2.4 其它入口）
- 每类用 Markdown 表格:
  - 2.1 HTTP: `| 类 | 方法 | HTTP Method + Path | 作用 |`
  - 2.2 Scheduled: `| 类 | 方法 | Cron / FixedRate | 作用 |`
  - 2.3 MQ: `| 类 | 方法 | 监听队列/交换机 | 作用 |`
  - 2.4 其它: `| 类 | 方法 | 入口类型 | 作用 |`
- 找不到具体参数就写 `-`，不要编造
- 完全没有该类入口时写 `_(无)_`
- 不要输出 "## 2. 触发入口" 主标题，只输出 4 个子节

## 额外输出: entry_class_ids
除 markdown 外，还要返回**所有已识别为入口所在类**的 class_id 列表，供 §3 时序图使用。
从输入里每个类的 `class_id=...` 字段取值。

【输出格式】（严格 JSON，所有 reason 中避免使用 ASCII 双引号）
{{
  "markdown": "### 2.1 HTTP 接口\\n...\\n### 2.2 定时任务\\n...\\n### 2.3 消息消费\\n...\\n### 2.4 其它入口\\n...",
  "entry_class_ids": ["<class_id>", ...]
}}
"""
)


# §3 端到端时序图 — 新版策略: 从全体类源码里让 LLM 推断调用链
SEQUENCE_PROMPT = PromptTemplate(
    input_variables=["category_path", "class_contexts"],
    template="""你是 Java 代码控制流专家。下面是一个业务分类下**所有相关类**的源码与语义解释。
你的任务：**从源码里推断**这个业务模块的端到端调用链，并绘制 Mermaid `sequenceDiagram`。

## 分类路径
{category_path}

## 输入类上下文
{class_contexts}

## 分析步骤
1. **找入口**：类里带 `@RestController` / `@Controller` 的方法（加了 `@*Mapping`）、`@Scheduled`、`@RabbitListener` 等，作为 sequenceDiagram 的起点
2. **追调用链**：在每个入口方法体里扫描 `someService.xxx()` / `this.yyy()` / `new XxxClient()` 等语句，找出**跨类方法调用**
3. **递归展开**：沿着调用链，看被调用的方法内部又调用了谁，最多追 3-4 层
4. **关注核心路径**：忽略日志/工具类/Getter/Setter，聚焦业务主流程

## 输出要求
- 用 `sequenceDiagram` 语法
- participant 用**简短类名**（不含包名），类名在多个类出现只声明一次
- 消息箭头标注**方法名**，例: `Controller ->> Service : doCheckin`
- 同一对 participant 间的同名方法只画**一次**（避免重复）
- **最多 20 条箭头**，只保留核心业务路径
- 可选 `autonumber` 开头让步骤有序号

## mapping 字段要求
除了 mermaid 外，同时返回 `mapping: {{类名 -> class_id}}`。
class_id 必须从输入里该类的 `class_id=...` 字段里**原样取值**，不要编造。
只给在 mermaid 中真正出现过的 participant 配 mapping 条目即可。

【输出格式】（严格 JSON）
{{
  "mermaid": "sequenceDiagram\\n    autonumber\\n    participant A as CheckinController\\n    participant B as CheckinService\\n    A ->> B : doCheckin\\n    ...",
  "mapping": {{
      "CheckinController": "<class_id>",
      "CheckinService": "<class_id>"
  }}
}}

## 兜底规则
- 如果该分类下的类**几乎没有跨类调用**（例如全是 DTO / 配置类 / 工具类），输出一个最小的占位 sequenceDiagram，并在 markdown 里说明原因
- 不要编造源码里没有的调用关系
"""
)
