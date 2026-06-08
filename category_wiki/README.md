# category_wiki — 按业务流分类生成 wiki

基于 `dir_reconstruction/output/new_wiki_index.json` 的聚类结果，为「**业务领域 (wlx)**」下 7 个子分类各生成一份**业务流 wiki**，数据源是 **Neo4j 图谱 + 已有 wiki page 的 .json**。

## 目标分类（MVP 固定 7 个）

| 分类 | 页数 |
|---|---|
| 业务领域 (wlx)/社区与网格管理 | ~10 |
| 业务领域 (wlx)/打卡系统 | ~3 |
| 业务领域 (wlx)/积分与抽奖引擎 | ~19 |
| 业务领域 (wlx)/活动与圈子平台 | ~24 |
| 业务领域 (wlx)/上报与通讯系统 | ~22 |
| 业务领域 (wlx)/App API 层 | ~4 |
| 业务领域 (wlx)/分析与统计 | ~12 |

合计约 94 页，产出 7 份 JSON。

## 章节结构（MVP 四章）

| # | 章节 | 数据来源 | 生成方式 |
|---|---|---|---|
| §1 | 业务概述 | Neo4j: `SE_What/SE_Why` | LLM 合成 |
| §2 | 触发入口 | Neo4j: `@RestController` / `@Scheduled` / `@RabbitListener` | LLM 表格化 |
| §3 | 端到端时序图 | Neo4j: `CALLS*1..3` 边 | LLM 生成 Mermaid sequenceDiagram |
| §6 | 组件索引 | `new_wiki_index.json` 的 pages | 纯模板，无 LLM |

每个章节节点都携带 **`neo4j_id`** + **`neo4j_source`** 平行字典，对齐 `output/wiki_result/总揽.json` 的数据 schema。

## 输出格式（样例）

```json
{
  "markdown_content": [
    {
      "type": "section",
      "id": "S1",
      "title": "# 打卡系统",
      "content": [
        {
          "type": "section", "id": "S2",
          "title": "## 1. 业务概述",
          "content": [
            {"type": "text", "id": "S3", "content": {"markdown": "..."}, "source_id": [], "neo4j_id": {}, "neo4j_source": {}}
          ],
          "neo4j_id": {"1": ["9670", "9671"]},
          "neo4j_source": {"1": ["CheckinController", "CheckinService"]}
        },
        ...
      ],
      "neo4j_id": {},
      "neo4j_source": {}
    }
  ],
  "source_id": []
}
```

## 前置依赖

1. **`dir_reconstruction/output/new_wiki_index.json` 已生成**（即你已跑过 `python dir_reconstruction/reconstruct.py`）
2. **`output/wiki_result/<path>.json` 每个页面文件都存在**（被 scope 解析读入）
3. **Neo4j 可连通**（`.env` 里 `WIKI_NEO4J_*` 配好）
4. **LLM 可用**（`.env` 里 `OPENAI_API_KEY` + `BASE_URL` 配好）

## 用法

```bash
# 默认：处理所有 7 个 wlx 子分类，串行执行
python category_wiki/generate.py

# 只跑一个分类（方便调试）
python category_wiki/generate.py --category "业务领域 (wlx)/打卡系统"

# 分类间并发 2 个（LLM/Neo4j 并发压力会倍增，建议 ≤3）
python category_wiki/generate.py --concurrency 2

# dry-run：打印将处理的分类清单
python category_wiki/generate.py --dry-run

# 覆盖源路径
python category_wiki/generate.py \
    --new-index /some/path/new_wiki_index.json \
    --wiki-root /some/path/wiki_result
```

## 输出位置

`category_wiki/output/<分类路径扁平化>.json`，例如：

```
category_wiki/output/业务领域_wlx_打卡系统.json
category_wiki/output/业务领域_wlx_社区与网格管理.json
...
```

日志在 `category_wiki/logs/generate_<timestamp>.log`。

## 目录结构

```
category_wiki/
├── __init__.py
├── README.md                  # 本文件
├── schema.py                  # SectionNode / TextNode / ChartNode dataclass
├── id_generator.py            # S1, S2, ... 短 id 生成器
├── scope.py                   # 从 page .json 收集 in_scope_nodeids
├── source_resolver.py         # 批量查 nodeId → name（填 neo4j_source）
├── neo4j_queries.py           # 所有 Cypher 查询
├── prompts.py                 # 各章节 LLM prompt 模板
├── assembler.py               # 组装树 + 打 id + 填 neo4j_source
├── workflow.py                # 单分类的并发编排
├── generate.py                # CLI 入口
├── sections/
│   ├── __init__.py
│   ├── _base.py               # invoke_llm_strict / helpers
│   ├── s1_overview.py
│   ├── s2_entrypoints.py
│   ├── s3_sequence.py
│   └── s6_components.py
├── output/                    # 落盘产物（见上）
└── logs/                      # 执行日志
```

## 下一步扩展

- **§4 数据模型**：扫 `@TableName/@Entity` 类 → Mermaid `erDiagram`
- **§5 业务规则**：扫 Service 方法 source_code → Claude CLI 总结
- **§7 异常与错误处理**：扫 `throw new XxxException` → 聚合
- **对非 wlx 分类**的处理：在 `WLX_SUB_CATEGORIES` 基础上放开

## 失败容错

- **单分类失败**：`try/except` 捕获，只影响本分类的输出；其它分类不受影响
- **单章节失败**：该章节用占位 markdown 填上，整篇 JSON 不会中断
- **LLM JSON 解析**：`invoke_llm_strict` 自带 5 次重试 + schema 校验
- **调用边过多**：`fetch_call_edges_*` 自动 LIMIT，超过 80 条后 prompt 内再截断

## 与已有脚本的关系

| 脚本 | 输入 | 输出 | 本脚本与它的关系 |
|---|---|---|---|
| `dir_reconstruction/reconstruct.py` | 原始 wiki_index.json | new_wiki_index.json（分类映射） | 本脚本的**上游**，必须先跑 |
| `run_all.py` | Neo4j + 源码 | 单个 Block 的 .meta.json | 本脚本的**数据源之一**（读已有 page .json） |
| `category_wiki/generate.py` | new_wiki_index.json + Neo4j + 已有 page .json | 按分类聚合的业务流 wiki .json | 本脚本 |
