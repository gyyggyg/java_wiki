"""一键从 business_flows_with_span.json 生成完整的按主题分类业务流 wiki。

**项目无关**：用 `--span-path` 指向任意 Java 项目的 span 文件，所有中间产物和最终 wiki
会生成在 span 文件所在目录（或显式 `--work-dir`）。

4 个阶段自动串联（已有产物自动跳过，`--force-*` 强制重跑）：

  阶段 1/4：生成模块内流 wiki         → <work_dir>/output/<domain>.meta.json × N
  阶段 2/4：LLM 抽取跨模块场景        → <work_dir>/business_scenarios.json
  阶段 3/4：LLM 主题分类              → <work_dir>/theme_mapping.json
  阶段 4/4：分发跨模块场景到各主题下的 per-flow wiki + 建索引
                                      → <work_dir>/output/themes/<主题>/<domain>.meta.json
                                        (追加「跨模块业务流」章节；组件索引永远是最后一章)

**缓存策略**：任一阶段产物存在则跳过；阶段 4（渲染与组织）总是跑。
所以 26 个模块内流 + scenarios + theme mapping 都已存在时，**只做分发+组织**。

用法:
    # 当前 java_wiki 项目（默认）
    python business_flow/generate_wiki.py

    # 用其他项目的 span 文件
    python business_flow/generate_wiki.py \\
        --span-path /path/to/other_project/business_flows_with_span.json

    # 强制重跑
    python business_flow/generate_wiki.py --force                  # 全部 LLM 阶段
    python business_flow/generate_wiki.py --force-flows            # 只重生成 26 个模块内流
    python business_flow/generate_wiki.py --force-extract          # 只重抽场景
    python business_flow/generate_wiki.py --force-classify         # 只重新分类主题

    # 行为
    python business_flow/generate_wiki.py --all-scenarios          # 摘要包含单域场景
    python business_flow/generate_wiki.py --concurrency 10         # LLM 并发度
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from typing import Dict, List


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BF_DIR = os.path.join(PROJECT_ROOT, "business_flow")

# 默认 span 路径（当前 java_wiki 项目）—— 可用 --span-path 覆盖
DEFAULT_SPAN_PATH = os.path.join(BF_DIR, "business_flows_with_span.json")


# ============================================================
# 工具
# ============================================================

def _flow_to_filename(flow_name: str) -> str:
    safe = flow_name.replace("/", "_").replace(" ", "_") \
                    .replace("(", "").replace(")", "")
    if safe.endswith("流") and len(safe) > 1:
        safe = safe[:-1]
    return f"{safe}.meta.json"


def _safe_dirname(name: str) -> str:
    return re.sub(r'[/\\:*?"<>|]', "_", name)


def _banner(title: str) -> None:
    print()
    print("=" * 72)
    print(f"▶  {title}")
    print("=" * 72)


def _run_cmd(cmd, desc):
    _banner(desc)
    print(f"   $ {' '.join(cmd)}\n")
    t0 = datetime.now()
    subprocess.run(cmd, check=True)
    elapsed = (datetime.now() - t0).total_seconds()
    print(f"\n   ✓ {desc} 完成（耗时 {elapsed:.1f}s）")


def _load_flow_names(span_path: str) -> List[str]:
    with open(span_path, encoding="utf-8") as f:
        return [f["name"] for f in json.load(f).get("flows", [])]


def _check_flow_wikis_missing(flow_names: List[str], flows_out_dir: str) -> List[str]:
    missing = []
    for name in flow_names:
        fname = _flow_to_filename(name)
        if not os.path.isfile(os.path.join(flows_out_dir, fname)):
            missing.append(fname)
    return missing


# ============================================================
# 阶段 5：按主题组织文件结构 + 索引
# ============================================================

def organize_by_theme(
    flow_names: List[str],
    theme_mapping_path: str,
    flows_out_dir: str,
    themes_out_dir: str,
) -> Dict[str, Dict]:
    with open(theme_mapping_path, encoding="utf-8") as f:
        theme_data = json.load(f)
    themes = theme_data.get("themes", [])

    organized: Dict[str, Dict] = {}
    for t in themes:
        theme_name = t["name"]
        theme_subdir = os.path.join(themes_out_dir, _safe_dirname(theme_name))
        os.makedirs(theme_subdir, exist_ok=True)

        info = {"description": t.get("description", ""),
                "summary_exists": False, "flows": []}

        # 跨模块摘要：render 产出的 flat <主题>.meta.json → <主题>/_summary.meta.json
        flat_summary = os.path.join(
            themes_out_dir, _safe_dirname(theme_name) + ".meta.json",
        )
        nested_summary = os.path.join(theme_subdir, "_summary.meta.json")
        if os.path.isfile(flat_summary):
            if os.path.isfile(nested_summary):
                os.remove(nested_summary)
            shutil.move(flat_summary, nested_summary)
            info["summary_exists"] = True

        # 每个 domain 的 wiki 拷贝进主题子目录
        for domain in t.get("domains", []):
            flow_fname = _flow_to_filename(domain)
            src = os.path.join(flows_out_dir, flow_fname)
            dst = os.path.join(theme_subdir, flow_fname)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                info["flows"].append({
                    "domain": domain, "file": flow_fname,
                    "relpath": f"themes/{_safe_dirname(theme_name)}/{flow_fname}",
                })
            else:
                info["flows"].append({
                    "domain": domain, "file": flow_fname,
                    "relpath": None, "missing": True,
                })

        organized[theme_name] = info
        n_ok = len([f for f in info["flows"] if not f.get("missing")])
        n_miss = len([f for f in info["flows"] if f.get("missing")])
        tag = "📑 summary" if info["summary_exists"] else "(无跨模块场景)"
        print(f"   [{theme_name:12s}] {n_ok}/{len(info['flows'])} 个 domain wiki + {tag}"
              + (f", 缺失 {n_miss} 个" if n_miss else ""))

    return organized


def build_index(
    organized: Dict[str, Dict],
    unclassified: List[str],
    themes_out_dir: str,
) -> None:
    n_themes = len(organized)
    n_flows = sum(len([f for f in info["flows"] if not f.get("missing")])
                   for info in organized.values())
    n_summary = sum(1 for info in organized.values() if info["summary_exists"])

    lines = [
        "# 业务主题索引",
        "",
        f"- **{n_themes}** 个业务主题",
        f"- **{n_flows}** 个模块内流 wiki",
        f"- **{n_summary}** 个主题含跨模块场景摘要",
        "",
    ]
    for theme_name, info in organized.items():
        lines.append(f"## {theme_name}")
        lines.append("")
        if info["description"]:
            lines.append(f"> {info['description']}")
            lines.append("")
        if info["summary_exists"]:
            lines.append(
                f"- 📑 **[跨模块场景摘要](themes/{_safe_dirname(theme_name)}/_summary.meta.json)**"
            )
        else:
            lines.append("- 📑 （本主题无跨模块场景）")
        lines.append("")
        if info["flows"]:
            lines.append("**模块内流**：")
            lines.append("")
            for f in info["flows"]:
                if f.get("missing"):
                    lines.append(f"- ⚠ `{f['domain']}`（wiki 未生成：{f['file']}）")
                else:
                    lines.append(f"- [`{f['domain']}`]({f['relpath']})")
            lines.append("")

    if unclassified:
        lines.append("## ⚠ 未归类 domain")
        lines.append("")
        for d in unclassified:
            lines.append(f"- `{d}` 未在 theme_mapping 中出现")
        lines.append("")

    index = {
        "wiki": [{"markdown": "\n".join(lines), "neo4j_id": {}}],
        "source_id_list": [],
    }
    index_path = os.path.join(themes_out_dir, "_index.meta.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"   ✓ 索引: {index_path}")


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="一键生成按主题分类的业务流 wiki（项目无关）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--span-path", default=DEFAULT_SPAN_PATH,
                        help=f"business_flows_with_span.json 路径（默认：{DEFAULT_SPAN_PATH}）")
    parser.add_argument("--work-dir", default=None,
                        help="中间产物与输出目录（默认：span 文件所在目录）")
    parser.add_argument("--concurrency", type=int, default=5,
                        help="LLM 阶段并发数（默认 5）")
    parser.add_argument("--force", action="store_true", help="强制重跑所有 LLM 阶段")
    parser.add_argument("--force-flows", action="store_true", help="强制重生成模块内流 wiki")
    parser.add_argument("--force-extract", action="store_true", help="强制重抽场景")
    parser.add_argument("--force-classify", action="store_true", help="强制重新分类主题")
    parser.add_argument("--all-scenarios", action="store_true",
                        help="摘要包含单域场景（默认只跨模块）")
    args = parser.parse_args()

    # ---------- 路径解析 ----------
    span_path = os.path.abspath(args.span_path)
    if not os.path.isfile(span_path):
        print(f"ERROR: 找不到 span 文件 {span_path}", file=sys.stderr)
        print("请先运行 `python business_flow/span.py` 或用 --span-path 指定。", file=sys.stderr)
        sys.exit(1)

    work_dir = os.path.abspath(args.work_dir) if args.work_dir else os.path.dirname(span_path)
    scenarios_path = os.path.join(work_dir, "business_scenarios.json")
    theme_mapping_path = os.path.join(work_dir, "theme_mapping.json")
    flows_out_dir = os.path.join(work_dir, "output")
    themes_out_dir = os.path.join(work_dir, "output", "themes")

    os.makedirs(flows_out_dir, exist_ok=True)

    _banner("路径配置")
    print(f"   span_path         = {span_path}")
    print(f"   work_dir          = {work_dir}")
    print(f"   scenarios_path    = {scenarios_path}")
    print(f"   theme_mapping     = {theme_mapping_path}")
    print(f"   flows_out_dir     = {flows_out_dir}")
    print(f"   themes_out_dir    = {themes_out_dir}")

    python = sys.executable
    flow_names = _load_flow_names(span_path)

    # ---------- 阶段 1/5：生成模块内流 wiki ----------
    missing = _check_flow_wikis_missing(flow_names, flows_out_dir)
    need_flows = args.force or args.force_flows or bool(missing)
    if need_flows:
        if missing:
            print(f"   ℹ 缺失 {len(missing)} 个模块内流 wiki: {missing[:5]}"
                  + (" ..." if len(missing) > 5 else ""))
        _run_cmd(
            [
                python, os.path.join(BF_DIR, "generate.py"),
                "--input", span_path,
                "--output-dir", flows_out_dir,
                "--concurrency", str(args.concurrency),
            ],
            f"阶段 1/5：生成 {len(flow_names)} 个模块内流 wiki",
        )
    else:
        _banner("阶段 1/5：跳过（使用缓存）")
        print(f"   ✓ {len(flow_names)} 个模块内流 wiki 都已存在")
        print(f"     （加 --force-flows 可强制重生成）")

    # ---------- 阶段 2/5：LLM 抽取场景 ----------
    need_extract = args.force or args.force_extract or not os.path.isfile(scenarios_path)
    if need_extract:
        _run_cmd(
            [
                python, os.path.join(BF_DIR, "extract_scenarios.py"),
                "--all",
                "--input", span_path,
                "--concurrency", str(args.concurrency),
                "--out", scenarios_path,
            ],
            "阶段 2/5：LLM 抽取场景 → business_scenarios.json",
        )
    else:
        _banner("阶段 2/5：跳过（使用缓存）")
        print(f"   ✓ {scenarios_path}（加 --force-extract 可强制重跑）")

    # ---------- 阶段 3/5：LLM 主题分类 ----------
    need_classify = args.force or args.force_classify or not os.path.isfile(theme_mapping_path)
    if need_classify:
        _run_cmd(
            [
                python, os.path.join(BF_DIR, "classify_themes.py"),
                "--span-path", span_path,
                "--scenarios-path", scenarios_path,
                "--out", theme_mapping_path,
            ],
            "阶段 3/5：LLM 主题分类 → theme_mapping.json",
        )
    else:
        _banner("阶段 3/5：跳过（使用缓存）")
        print(f"   ✓ {theme_mapping_path}（加 --force-classify 可强制重跑）")
        print(f"   ℹ 可手动编辑后重跑本脚本")

    # ---------- 阶段 4/4：按主题组织 per-flow wiki + 分发跨模块场景 ----------
    render_cmd = [
        python, os.path.join(BF_DIR, "render_scenarios_by_theme.py"),
        "--input", scenarios_path,
        "--theme-mapping", theme_mapping_path,
        "--flows-dir", flows_out_dir,
        "--out-dir", themes_out_dir,
        "--span-path", span_path,
    ]
    if not args.all_scenarios:
        render_cmd.append("--cross-domain-only")
    mode = "所有场景" if args.all_scenarios else "仅跨模块"
    _run_cmd(
        render_cmd,
        f"阶段 4/4：分发跨模块场景到各主题下的 per-flow wiki（{mode}）→ {themes_out_dir}/",
    )

    # ---------- 完成 ----------
    print()
    print("=" * 72)
    print("✅ 生成完成")
    print("=" * 72)
    print(f"   📁 {flows_out_dir}/                  ← 原始 per-flow wiki")
    print(f"   📁 {themes_out_dir}/")
    print(f"      _index.meta.json                  ← 主题索引")
    print(f"      <主题>/<domain>.meta.json         ← 原 per-flow wiki + 追加「跨模块业务流」章节")
    print()


if __name__ == "__main__":
    main()
