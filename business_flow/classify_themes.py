"""LLM 驱动的业务主题分类器

读取 26 个 business flow 的元信息 + business_scenarios.json 里抽到的场景名，
让 LLM 把这些 domain 聚类为 8-12 个**业务主题**，输出 theme_mapping.json。

产出的 theme_mapping.json 人工可编辑：修改主题名 / 重分 domain 归属 / 增删主题。
随后由 render_scenarios_by_theme.py 按这个 mapping 组织 wiki 文件。

用法:
    python business_flow/classify_themes.py
    python business_flow/classify_themes.py --min-themes 8 --max-themes 12
    python business_flow/classify_themes.py --out business_flow/theme_mapping.json
"""
import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from interfaces.llm_interface import LLMInterface
from business_flow.llm_client import set_default_llm, invoke_llm_strict


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BF_DIR = os.path.join(PROJECT_ROOT, "business_flow")
SPAN_PATH = os.path.join(BF_DIR, "business_flows_with_span.json")
SCENARIOS_PATH = os.path.join(BF_DIR, "business_scenarios.json")
OUT_PATH = os.path.join(BF_DIR, "theme_mapping.json")


CLASSIFY_SYSTEM_TEMPLATE = """你是资深业务架构师。任务：把一个政务/社区 app 的 N 个业务域（domain）聚类为 {min_themes}-{max_themes} 个**业务主题**。

## 输入
每个 domain 包含：
- name: 业务域名字（中文）
- kind: 触发侧（用户端/运营端/大屏端/定时任务）
- description: 业务描述
- example_scenarios: 该域的典型场景名（最多 10 个）

## 输出要求
按**业务语义**把所有 domain 聚合为 {min_themes}-{max_themes} 个主题。每个主题：
- `name`: 4-8 字业务主题名（业务视角，非技术维度）
  - ✅ 好："登录认证"、"积分任务"、"社区治理"、"奖品兑换"
  - ❌ 坏："系统相关"、"其它"、"Controller 管理"
- `description`: 20-60 字，这个主题的业务范围
- `domains`: 归属的 domain 名字列表（**必须精确匹配输入的 name**）
- `reason`: 1-2 句为什么这些 domain 归一组

## 原则
1. **业务相关性 > 技术相似性** —— 用户视角是不是"同一块功能"
2. **互斥覆盖** —— 所有 domain 必须**恰好被覆盖一次**（不重复、不遗漏）
3. **规模均衡** —— 每个主题 1-5 个 domain 最佳，避免单域独占主题，也避免 10+ 堆一起
4. **命名清晰** —— 读者看了就知道是什么业务
5. **主题数** —— {min_themes}-{max_themes} 个

## 严格 JSON 输出（无围栏、无前言）
{{
  "themes": [
    {{
      "name": "登录认证",
      "description": "用户多渠道登录、身份绑定、个人资料管理",
      "domains": ["用户认证登录流", "用户个人中心流"],
      "reason": "围绕用户身份认证与个人信息，业务链路紧密"
    }}
  ]
}}
"""


def build_user_prompt(
    flows: List[Dict],
    scenarios_by_domain: Dict[str, List[str]],
) -> str:
    parts = [f"## 输入 domain 列表（共 {len(flows)} 个）", ""]
    for f in flows:
        name = f["name"]
        kind = f.get("kind", "?")
        desc = (f.get("description") or "")[:150]
        examples = scenarios_by_domain.get(name, [])[:10]
        parts.append(f"### {name}")
        parts.append(f"- kind: {kind}")
        parts.append(f"- description: {desc}")
        if examples:
            parts.append(f"- example_scenarios: {', '.join(examples)}")
        parts.append("")
    parts.append("---")
    parts.append("请按要求输出主题分类 JSON。")
    return "\n".join(parts)


def validate_mapping(
    result: Dict, all_domains: List[str],
    min_themes: int, max_themes: int,
) -> str:
    """校验 LLM 输出；返回 error message，空串表示 OK"""
    themes = result.get("themes")
    if not isinstance(themes, list) or not themes:
        return "themes 字段不是非空列表"
    if not (min_themes <= len(themes) <= max_themes):
        return f"主题数 {len(themes)} 不在 [{min_themes}, {max_themes}] 范围"

    covered: List[str] = []
    for i, t in enumerate(themes):
        name = t.get("name", "")
        if not isinstance(name, str) or not name.strip():
            return f"主题[{i}] name 缺失或非字符串"
        domains = t.get("domains") or []
        if not isinstance(domains, list) or not domains:
            return f"主题 '{name}' 的 domains 为空或非列表"
        if not t.get("description") or not t.get("reason"):
            return f"主题 '{name}' 缺少 description 或 reason"
        covered.extend(domains)

    input_set = set(all_domains)
    covered_set = set(covered)
    missing = input_set - covered_set
    extra = covered_set - input_set
    dup_names = [d for d in covered_set if covered.count(d) > 1]

    if missing:
        return f"未覆盖的 domain: {sorted(missing)}"
    if extra:
        return f"多余的 domain（不在输入里）: {sorted(extra)}"
    if dup_names:
        return f"重复出现的 domain: {sorted(dup_names)}"
    return ""


async def main():
    parser = argparse.ArgumentParser(description="LLM 驱动的业务主题分类器")
    parser.add_argument("--span-path", default=SPAN_PATH)
    parser.add_argument("--scenarios-path", default=SCENARIOS_PATH)
    parser.add_argument("--out", default=OUT_PATH)
    parser.add_argument("--min-themes", type=int, default=8)
    parser.add_argument("--max-themes", type=int, default=12)
    parser.add_argument("--retry", type=int, default=3,
                        help="校验失败后的外层重试次数（LLM 自身还有内部重试）")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    logger = logging.getLogger("classify_themes")

    # 1. 读 domains
    if not os.path.isfile(args.span_path):
        logger.error(f"span 文件不存在: {args.span_path}")
        sys.exit(1)
    with open(args.span_path, encoding="utf-8") as f:
        flows = json.load(f)["flows"]
    all_domain_names = [f["name"] for f in flows]
    logger.info(f"加载 {len(all_domain_names)} 个 domain")

    # 2. 按 domain 聚合 scenario_names 作为分类辅助信息
    scenarios_by_domain: Dict[str, List[str]] = {}
    if os.path.isfile(args.scenarios_path):
        with open(args.scenarios_path, encoding="utf-8") as f:
            sdata = json.load(f)
        for entry in sdata.get("per_entry_scenarios", []):
            dom = entry.get("domain")
            if not dom:
                continue
            for s in entry.get("scenarios", []):
                name = s.get("scenario_name", "")
                if name:
                    scenarios_by_domain.setdefault(dom, []).append(name)
        logger.info(
            f"从 scenarios 聚合: {len(scenarios_by_domain)}/{len(all_domain_names)} "
            f"domain 有场景名，总 {sum(len(v) for v in scenarios_by_domain.values())} 个场景名"
        )
    else:
        logger.warning(f"scenarios 文件不存在: {args.scenarios_path}，LLM 将仅基于 description 分类")

    # 3. LLM 调用 + 校验循环
    llm = LLMInterface()
    set_default_llm(llm)
    logger.info(
        f"LLM: provider={llm.provider} "
        f"model={llm.model_kwargs.get('model_name') or llm.model_kwargs.get('model')}"
    )

    system = CLASSIFY_SYSTEM_TEMPLATE.format(
        min_themes=args.min_themes, max_themes=args.max_themes,
    )
    base_user = build_user_prompt(flows, scenarios_by_domain)

    last_err = ""
    for attempt in range(args.retry):
        user = base_user
        if last_err:
            user = user + (
                f"\n\n---\n**上次尝试不符合要求**：{last_err}\n"
                f"请严格修正，重新输出完整的 JSON（不要引用或增量，要完整 themes 数组）。"
            )
        try:
            result, _ = await invoke_llm_strict(
                system_prompt=system,
                user_prompt=user,
                required_keys=["themes"],
                label=f"classify#{attempt+1}",
            )
        except Exception as e:
            last_err = f"LLM 调用异常: {type(e).__name__}: {e}"
            logger.warning(f"[attempt {attempt+1}] {last_err}")
            continue

        err = validate_mapping(result, all_domain_names, args.min_themes, args.max_themes)
        if err:
            last_err = err
            logger.warning(f"[attempt {attempt+1}] 校验失败: {err}")
            continue

        logger.info(f"分类成功，产出 {len(result['themes'])} 个主题:")
        for t in result["themes"]:
            logger.info(
                f"  - {t['name']} ({len(t['domains'])} 个 domain): "
                f"{', '.join(t['domains'])}"
            )

        out = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "llm_model": llm.model_kwargs.get("model_name") or llm.model_kwargs.get("model"),
            "input_summary": {
                "total_domains": len(all_domain_names),
                "domains_with_scenarios": len(scenarios_by_domain),
                "total_scenarios": sum(len(v) for v in scenarios_by_domain.values()),
            },
            "themes": result["themes"],
            "_note": "人工可编辑：调整主题名、重分 domain 归属；下游 render_scenarios_by_theme 按本文件运行。",
        }
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        logger.info(f"写入 {args.out}")
        return

    logger.error(
        f"经过 {args.retry} 次重试仍未通过校验。最后错误: {last_err}\n"
        f"建议：手动检查 LLM 输出，或放宽 --min-themes / --max-themes 限制。"
    )
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
