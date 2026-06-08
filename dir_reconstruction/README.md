# wiki_index 重聚类工具

把 `output/wiki_result/.index/wiki_index.json`（405 条 wiki 页面）按用户指定的**新分类树**重新聚类，每次用 Claude CLI 处理 10 条。

## 目标分类树

来自产品提供的 UI 截图（[categories.py](categories.py) 中维护）：

```
架构概述
后端框架
├── Maven 多模块设计
├── JWT 认证流程
├── Spring Security 配置
├── AOP 切面系统
├── MyBatis-Plus 集成
└── 动态数据源切换
业务领域 (wlx)
├── 社区与网格管理
├── 打卡系统
├── 积分与抽奖引擎
├── 活动与圈子平台
├── 上报与通讯系统
├── App API 层
└── 分析与统计
前端应用
基础架构模块
配置参考
```

## 工作原理

1. 读取源 `wiki_index.json` 的 `pages[]`
2. 按 10 条一批，把每条的 `path / summary / classes` 发给 Claude CLI
3. Claude 返回每条应该归入哪个分类（只能选分类树中已定义的 path）
4. 增量写到 `output/progress.json`（支持中断后 resume）
5. 全部跑完后生成：
   - `output/new_wiki_index.json`：按新分类重组的完整索引
   - `output/category_stats.txt`：各分类下的条数统计
   - `output/failures.json`：失败的 batch 记录（如有）

## 前置依赖

1. **本地已安装 Claude Code CLI** — `which claude` 能找到
2. **已登录 Anthropic 账号** — Claude CLI 用自己的订阅计费，与 `OPENAI_API_KEY` 完全无关
3. **源文件存在** — 默认路径为 `/Users/uinas/code/wiki2/output 12-27-55-174/wiki_result/.index/wiki_index.json`（可通过 `--source` 或 `WIKI_INDEX_PATH` 覆盖）

## 用法

```bash
# 默认：全量跑，batch=10，串行执行，支持 resume
python dir_reconstruction/reconstruct.py

# 指定源文件（如果源路径有变）
python dir_reconstruction/reconstruct.py --source "/path/to/wiki_index.json"

# 改批大小
python dir_reconstruction/reconstruct.py --batch 20

# 并发跑（注意 claude CLI 是本地进程，不宜设太大）
python dir_reconstruction/reconstruct.py --concurrency 3

# 只跑 N 个 batch 做调试
python dir_reconstruction/reconstruct.py --max-batches 2

# dry-run：只打印要发送的第一个 batch，不实际调 Claude
python dir_reconstruction/reconstruct.py --dry-run

# 从零开始（忽略已有 progress.json）
python dir_reconstruction/reconstruct.py --no-resume
```

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `WIKI_INDEX_PATH` | `/Users/uinas/code/wiki2/output 12-27-55-174/wiki_result/.index/wiki_index.json` | 源 wiki_index.json 的路径，被 `--source` 参数覆盖 |
| `CLAUDE_MODEL` | `sonnet` | Claude CLI 使用的模型，可选 `opus` / `haiku` |
| `DIR_RECONSTRUCTION_TIMEOUT` | `180` | 单次 Claude CLI 调用超时（秒） |

## 输出文件

全部在 `dir_reconstruction/output/` 下：

| 文件 | 用途 |
|---|---|
| `progress.json` | 增量保存的每条 wiki path → {category, reason}。resume 时读它 |
| `failures.json` | 失败的 batch 记录（batch_idx / error / wiki_paths） |
| `new_wiki_index.json` | **最终产物**：按新分类重组后的完整索引 |
| `category_stats.txt` | 各分类下的 wiki 数量统计（人读） |

日志文件在 `dir_reconstruction/logs/reconstruct_<timestamp>.log`。

## `new_wiki_index.json` 结构

```json
{
  "categories": [
    {
      "path": "架构概述",
      "description": "...",
      "count": 2,
      "pages": [
        {
          "path": "总揽.json",
          "summary": "...",
          "classes": [...],
          "_classify_reason": "LLM 分类理由"
        }
      ]
    },
    ...
  ],
  "unclassified": [...],
  "total_classified": 403,
  "total_unclassified": 2
}
```

## 中断恢复

脚本设计成 **幂等 + 可 resume**：
- 每个 batch 成功后立即写 `progress.json`
- 再次运行时默认会跳过已在 `progress.json` 里的 wiki path
- 所以你可以任意时刻 Ctrl+C，下次 `python reconstruct.py` 会继续从上次的地方

如果想重新分类某一批，直接从 `progress.json` 里删除那些 wiki path 再 resume 即可。

## 调整分类树

所有可选分类定义在 [categories.py](categories.py) 的 `CATEGORY_TREE`。
- 新增分类：加一条 `{"path": "...", "description": "..."}`
- 改名：修改 `path` 字段（注意已分类的 progress.json 里保存的旧分类名会变成非法，重跑时会被剔除）
- 若要强制所有 wiki 重新分类：删除 `output/progress.json` 再跑

## 注意事项

- Claude CLI 是**本地子进程**。`--concurrency` 建议不超过 3-5，否则可能打满 CPU/网络
- 每次 batch 的输入大约 1-4k tokens，Claude sonnet 可以轻松处理 10 条/batch
- LLM 偶尔会漏掉某些 wiki（返回的 assignments 条数 < 输入的 wiki 条数），这些会在日志里 warning，下次 resume 时自动会重新尝试（因为它们仍不在 progress.json 里）