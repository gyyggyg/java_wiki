"""用 Claude CLI 生成两个总揽页（读源码 + 现有 wiki 产出）

依赖本地 `claude` 命令（Claude Code CLI）。与走 LLM API 的 generate.py 不同，
Claude CLI 可以**自主用 Read / Glob / Grep / Write 等工具**探索目录、读取素材，
写出更贴合实际代码的总览文档。

产出（默认在 business_flow/output/ 下）：
  - _项目总览.meta.json       整体项目总览
  - 业务领域/业务领域总揽.meta.json  业务视角总览

用法:
    python business_flow/generate_overview_pages.py
    python business_flow/generate_overview_pages.py --only overall
    python business_flow/generate_overview_pages.py --only domain
    python business_flow/generate_overview_pages.py --model opus

环境变量:
    CLAUDE_MODEL      sonnet / opus / haiku（默认 sonnet）
    AGENT_TIMEOUT     单次 claude 调用超时（秒，默认 900）
"""
import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BF_DIR = os.path.join(PROJECT_ROOT, "business_flow")
DEFAULT_OUTPUT_DIR = os.path.join(BF_DIR, "output")
DEFAULT_SOURCE_ROOT = PROJECT_ROOT

OVERALL_PAGE_NAME = "_项目总览.meta.json"
# 业务领域总揽放到业务领域/ 子目录里，和该子目录的 _index.meta.json 并列
DOMAIN_PAGE_RELPATH = os.path.join("业务领域", "业务领域总揽.meta.json")

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "sonnet")
AGENT_TIMEOUT = int(os.environ.get("AGENT_TIMEOUT", "900"))


def _find_claude_cli() -> str:
    path = shutil.which("claude")
    if path:
        return path
    raise FileNotFoundError(
        "未找到 claude CLI。\n"
        "请先安装 Claude Code: brew install anthropics/tap/claude"
    )


META_SCHEMA_NOTE = """
## meta.json 格式约定
严格 JSON，结构：
```json
{
  "wiki": [
    {"markdown": "# 标题\\n\\n段落..."},
    {"mermaid": "```mermaid\\ngraph LR\\n  A --> B\\n```"},
    {"markdown": "更多 markdown..."}
  ],
  "source_id_list": []
}
```
- `wiki` 数组里每个元素要么是 `{"markdown": "..."}`，要么是 `{"mermaid": "...源码..."}`
- `mermaid` 字段的值必须是完整的围栏字符串（包含 ```mermaid 开头和 ``` 结尾）
- `source_id_list` 目前留空数组 `[]`
- 中文、emoji 都允许；JSON 里的换行必须转义为 `\\n`
"""


def build_overall_prompt(output_dir: str, source_root: str) -> str:
    out_path = os.path.join(output_dir, OVERALL_PAGE_NAME)
    return f"""
你要为一个软件项目写"项目整体总览"页面，面向新入职或跨团队协作者，目标是 15 分钟读完能建立整体认知。

## 已知信息
- 项目源码根目录：`{source_root}`
- 现有 wiki 目录：`{output_dir}`（里面有按类别组织的子目录和若干 meta.json 文件；**请自行探索其实际结构**）
- 业务流中间产物目录（可参考）：`{BF_DIR}`
- 最终输出路径（必须写到这里）：`{out_path}`

## 你需要做的事

**第一步：探索**
用 `LS` / `Glob` / `Bash ls` 摸清 `{output_dir}` 下的实际布局——有哪些顶层 wiki、有哪些子目录、有无索引文件。**不要假设目录命名**。
同样用 `LS` 粗看一遍 `{source_root}` 看项目物理结构、模块、配置文件。

**第二步：读代表性材料**
挑几个有代表性的 wiki 文件用 `Read` 读开头，理解项目做什么。想深入某部分再读对应 wiki。

**第三步：按真实内容设计章节**
没有硬模板，章节命名、合并、拆分、顺序都由你根据看到的内容决定。一份好的项目总览通常会覆盖：
- 业务定位（做什么、给谁用）
- 技术栈与架构（如果有前后端都有就分别讲）
- 代码组织（模块/目录结构）
- 主要业务领域 / 功能模块的鸟瞰
- 对新人的"从哪看起"指引
- 到其它文档的导航索引

发现前端代码就加前端章节；发现有定时任务、消息队列就提；没有就不写。**内容跟着现状走。**

## 输出
用 `Write` 工具写 meta.json 到：
```
{out_path}
```

{META_SCHEMA_NOTE}

## 硬性约束
- **忠实素材**：任何结论（技术栈、模块清单、实体名、API 数量等）必须是从实际文件读出来的；不确定就不写
- 禁用套话："本项目"、"本系统"、"旨在"、"综上所述"、"值得注意"、"通过分析"等开头
- 引用代码实体（类名、方法、注解、表名）用 markdown 反引号包裹
- mermaid 图语法必须正确；可用 `Bash` 跑 `node {source_root}/scripts/validate_mermaid.mjs` 校验
- 文档内链接路径要能被读者点开

完成后返回 "done"。
""".strip()


def build_domain_prompt(output_dir: str, source_root: str) -> str:
    out_path = os.path.join(output_dir, DOMAIN_PAGE_RELPATH)
    return f"""
你要写一份"业务领域总揽"页面，**从业务视角**（不讲技术实现）给读者一个业务鸟瞰。

## 已知信息
- 现有 wiki 目录：`{output_dir}`（里面有按类别/主题组织的子目录；业务相关 wiki 应该在其中某个子目录下）
- 业务流中间产物目录（可参考）：`{BF_DIR}`
- 最终输出路径（必须写到这里）：`{out_path}`

如果 `{out_path}` 已存在，**允许直接覆盖**（这是预期行为，每次运行都要输出新版本）。

## 你需要做的事

**第一步：探索**
用 `LS` / `Glob` 看 `{output_dir}` 的实际结构，找到业务相关的 wiki 在哪。**不要假设目录名**。可能有顶层索引文件帮你理解组织方式。

**第二步：读业务 wiki**
挑几个业务 wiki 用 `Read` 看开头（通常是业务概述段），理解每个业务域在做什么。wiki 末尾如果有"跨模块业务流"章节，能帮你理解主题之间的业务协作。

**第三步：按真实内容设计章节**
一份好的业务领域总揽通常会有：
- 业务整体定位与边界
- 业务主题全景（配 mermaid 图）
- 每个主题的业务职责
- 跨主题的业务协作模式
- 核心业务实体
- 典型业务场景（从 wiki 里挑最有代表性的）
- 业务术语表（项目有特有名词时）

章节的拆分、命名、顺序都由你根据读到的真实内容决定。

## 输出
用 `Write` 工具写 meta.json 到：
```
{out_path}
```

{META_SCHEMA_NOTE}

## 硬性约束
- **纯业务视角**：技术细节（分层、注解、接口实现）留给单域 wiki 去讲，这里只讲业务语义
- **忠实素材**：主题名、业务域名、实体名、场景名必须从实际 wiki 读出来，禁止编造
- 禁用套话："本业务"、"旨在"、"综上"、"通过"、"综上所述"等开头或结句
- 具体业务名词用反引号包裹
- mermaid 图语法必须正确

完成后返回 "done"。
""".strip()


def run_claude_cli(prompt: str, label: str, timeout: int = AGENT_TIMEOUT) -> None:
    """同步子进程调用 claude CLI。Claude 会用工具自主读写文件。"""
    claude_bin = _find_claude_cli()

    cmd = [
        claude_bin, "-p",
        "--model", CLAUDE_MODEL,
        "--permission-mode", "bypassPermissions",
    ]

    print("=" * 72)
    print(f"▶  {label}")
    print("=" * 72)
    print(f"   model: {CLAUDE_MODEL}  timeout: {timeout}s")
    print(f"   cmd: {' '.join(cmd)}")
    print(f"   prompt size: {len(prompt)} chars\n")

    t0 = datetime.now()
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            timeout=timeout,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        print(f"❌ {label} 超时（{timeout}s）", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ 找不到 claude 命令", file=sys.stderr)
        sys.exit(1)

    elapsed = (datetime.now() - t0).total_seconds()

    if proc.returncode != 0:
        print(f"❌ {label} 失败 (rc={proc.returncode})", file=sys.stderr)
        sys.exit(1)

    print(f"\n✓ {label} 完成（耗时 {elapsed:.1f}s）")


def verify_output(path: str, label: str) -> None:
    if not os.path.isfile(path):
        print(f"⚠ 警告：{label} 未产出文件 {path}", file=sys.stderr)
        return
    size = os.path.getsize(path)
    print(f"   📄 {path}  ({size:,} bytes)")


def main():
    global CLAUDE_MODEL
    parser = argparse.ArgumentParser(
        description="用 Claude CLI 生成项目总览 + 业务领域总揽两份 meta.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR,
                        help="wiki 所在目录（也是总览页写入目录）")
    parser.add_argument("--source-root", default=DEFAULT_SOURCE_ROOT,
                        help="项目源码根目录")
    parser.add_argument("--only", choices=["overall", "domain"], default=None,
                        help="只生成其中一个")
    parser.add_argument("--model", default=None,
                        help=f"Claude 模型（默认 {CLAUDE_MODEL}，来自 CLAUDE_MODEL env）")
    parser.add_argument("--timeout", type=int, default=AGENT_TIMEOUT,
                        help=f"单次调用超时（秒，默认 {AGENT_TIMEOUT}）")
    args = parser.parse_args()

    # 允许 --model 覆盖
    if args.model:
        os.environ["CLAUDE_MODEL"] = args.model
        CLAUDE_MODEL = args.model

    # 前置检查
    _find_claude_cli()
    if not os.path.isdir(args.output_dir):
        print(f"ERROR: 输出目录不存在 {args.output_dir}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(args.source_root):
        print(f"ERROR: 源码目录不存在 {args.source_root}", file=sys.stderr)
        sys.exit(1)

    output_dir_abs = os.path.abspath(args.output_dir)
    source_root_abs = os.path.abspath(args.source_root)

    overall_path = os.path.join(output_dir_abs, OVERALL_PAGE_NAME)
    domain_path = os.path.join(output_dir_abs, DOMAIN_PAGE_RELPATH)

    if args.only != "domain":
        # 确保 overall 输出目录存在（就是 output_dir 本身）
        prompt = build_overall_prompt(output_dir_abs, source_root_abs)
        run_claude_cli(prompt, "生成项目总览（_项目总览.meta.json）", args.timeout)
        verify_output(overall_path, "项目总览")

    if args.only != "overall":
        # 确保 domain 输出目录存在（业务领域/ 子目录）
        os.makedirs(os.path.dirname(domain_path), exist_ok=True)
        prompt = build_domain_prompt(output_dir_abs, source_root_abs)
        run_claude_cli(prompt, "生成业务领域总揽（业务领域/业务领域总揽.meta.json）", args.timeout)
        verify_output(domain_path, "业务领域总揽")

    print()
    print("=" * 72)
    print("✅ 完成")
    print("=" * 72)


if __name__ == "__main__":
    main()
