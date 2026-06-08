"""Java 方法分支静态分析 —— 为 §5 控制流规划阶段识别"直通查询"接口。

- 用 javalang 解析单个方法的 AST，统计 if/switch/for/while/try/do/ternary 分支节点
- branches ≤ PASSTHROUGH_THRESHOLD 视为直通查询候选
- 解析失败时返回 None，交给 LLM 按方法名启发式兜底
"""
from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("business_flow.branch_analyzer")

try:
    import javalang
except ImportError:
    javalang = None
    logger.warning(
        "javalang 未安装，AST 分支分析将完全失效；"
        "请 `pip install javalang==0.13.0`。"
    )


PASSTHROUGH_THRESHOLD = 0
"""方法分支数 ≤ 此阈值时视为直通查询。

取 0 意味着「只有完全无分支的方法才算直通」：
- 单个 null 校验、权限校验、try-catch 包裹等带 1 个分支的方法，仍被视为有业务逻辑
- 理由：这些场景即使分支很浅，也可能包含关键的业务判断（如 @PostMapping 的状态检查），
  宁可画一个简单图也不漏掉。如需更宽松，把阈值改回 1。
"""


_BRANCH_COUNTERS = {
    "IfStatement": "if",
    "SwitchStatement": "switch",
    "TryStatement": "try",
    "ForStatement": "for",
    "WhileStatement": "while",
    "DoStatement": "do",
    "TernaryExpression": "ternary",
}


def analyze_method(method_source: str) -> Optional[Dict]:
    """统计单个 Java 方法的分支结构。

    Args:
        method_source: 方法完整源码（含签名和方法体）

    Returns:
        {
            "branches": 总分支数,
            "detail": {"if": N, "switch": N, "try": N, "for": N, "while": N, "do": N, "ternary": N},
            "is_passthrough": bool,
        }
        解析失败或 javalang 不可用时返回 None。
    """
    if not method_source or javalang is None:
        return None

    # 单个方法源码无法直接被 javalang.parse.parse() 解析，需包裹在 dummy class 里
    wrapped = "public class _BranchProbe { " + method_source + " }"
    try:
        tree = javalang.parse.parse(wrapped)
    except Exception as e:
        logger.debug(f"[branch_analyzer] parse 失败: {type(e).__name__}: {e}")
        return None

    detail = {v: 0 for v in _BRANCH_COUNTERS.values()}
    for _path, node in tree:
        counter_key = _BRANCH_COUNTERS.get(type(node).__name__)
        if counter_key is not None:
            detail[counter_key] += 1

    total = sum(detail.values())
    return {
        "branches": total,
        "detail": detail,
        "is_passthrough": total <= PASSTHROUGH_THRESHOLD,
    }


async def analyze_entry_methods(
    neo4j,
    entry_methods: List[Dict],
) -> Dict[str, Dict]:
    """并发拉取方法源码并做 AST 分析。

    Args:
        neo4j: Neo4jInterface 实例
        entry_methods: [{"class": "...", "method": "...", ...}, ...]

    Returns:
        {"ClassName.methodName": {branches, detail, is_passthrough}, ...}
        未能解析的方法不会出现在结果中。
    """
    from business_flow.line_mapping import fetch_method_source

    if javalang is None:
        logger.warning(
            f"[branch_analyzer] javalang 不可用，跳过对 {len(entry_methods)} 个入口方法的 AST 分析"
        )
        return {}

    # 失败计数器（封在 list 里便于内层闭包修改）
    stats = {"no_source": 0, "parse_fail": 0, "ok": 0}

    async def _one(e: Dict):
        cls = (e.get("class") or "").strip()
        mth = (e.get("method") or "").strip()
        if not cls or not mth:
            return None
        try:
            mrow = await fetch_method_source(neo4j, cls, mth)
        except Exception as ex:
            logger.warning(f"[branch_analyzer] 查询 {cls}.{mth} 源码失败: {type(ex).__name__}: {ex}")
            stats["no_source"] += 1
            return None
        if not mrow or not mrow.get("method_source"):
            stats["no_source"] += 1
            return None
        src = mrow["method_source"]
        info = analyze_method(src)
        if info is None:
            stats["parse_fail"] += 1
            # 打印前 200 字便于人工排查到底哪类源码挂了
            preview = (src or "")[:200].replace("\n", " ⏎ ")
            logger.warning(
                f"[branch_analyzer] parse 失败 {cls}.{mth} (源码 {len(src)} chars): {preview}"
            )
            return None
        stats["ok"] += 1
        return (f"{cls}.{mth}", info)

    results = await asyncio.gather(*[_one(e) for e in entry_methods])
    logger.info(
        f"[branch_analyzer] 入口方法 AST 诊断: "
        f"成功={stats['ok']}, 无源码={stats['no_source']}, 解析失败={stats['parse_fail']}"
    )
    return {k: v for r in results if r for k, v in [r]}


def format_branch_hint(branch_analysis: Dict[str, Dict]) -> str:
    """把分析结果格式化成 prompt 用的 Markdown 表格。"""
    if not branch_analysis:
        return "(未能对任何入口方法完成 AST 分析，请按方法名启发式判断)"
    lines = [
        "| 入口方法 | 分支总数 | if | switch | try | loop | 静态判定 |",
        "|---|---|---|---|---|---|---|",
    ]
    for method, info in branch_analysis.items():
        d = info["detail"]
        loop = d["for"] + d["while"] + d["do"]
        verdict = "**直通查询**" if info["is_passthrough"] else "含业务逻辑"
        lines.append(
            f"| `{method}` | {info['branches']} | {d['if']} | {d['switch']} | {d['try']} | {loop} | {verdict} |"
        )
    return "\n".join(lines)


# ============================================================
# Service 层扫描：直接从 class_rows 的 source_code 里抽 public 方法 + 数分支
# （不查 Neo4j，纯 javalang，速度快；给 §5 规划阶段识别"值得画的 ServiceImpl 方法"）
# ============================================================

import re as _re

_PUBLIC_METHOD_RE = _re.compile(
    r"""(?:@\w+(?:\([^)]*\))?\s*)*            # 0 或多个注解
         public\s+
         (?!class|interface|enum|record)       # 排除嵌套类声明
         (?:static\s+|final\s+)*
         [\w<>\[\],?&\s\.]+?\s+                # 返回类型
         (?P<name>\w+)\s*
         \([^)]*\)\s*
         (?:throws\s+[\w\s,\.]+)?\s*
         \{""",
    _re.VERBOSE | _re.DOTALL,
)


def _extract_public_methods_from_class_source(src: str) -> List[Dict[str, str]]:
    """从 ServiceImpl 类源码里抽出 public 方法 {name, source}。

    用简单的大括号配对定位方法体。抽不干净时损失覆盖率不影响主流程。
    """
    out: List[Dict[str, str]] = []
    if not src:
        return out
    # 找方法头 + 定位到 `{`，然后配对大括号找结束
    for m in _PUBLIC_METHOD_RE.finditer(src):
        name = m.group("name")
        open_brace = m.end() - 1  # `{`
        depth = 1
        i = open_brace + 1
        while i < len(src) and depth > 0:
            c = src[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            i += 1
        if depth != 0:
            continue
        body = src[m.start():i]
        out.append({"name": name, "source": body})
    return out


def analyze_serviceimpl_methods(
    class_rows: List[Dict],
    min_branches: int = 2,
    max_methods_per_class: int = 10,
) -> Dict[str, Dict]:
    """扫所有 *ServiceImpl 类里的 public 方法，对每个方法跑 AST 分支分析。

    与 analyze_entry_methods 的区别：
    - 输入不是 Neo4j 查询结果，而是 class_rows（已有 source_code）
    - 目标是 Service 层而非 Controller 入口
    - 只返回 branches >= min_branches 的"值得画 CFG"的方法

    Returns:
        {"ServiceImpl.methodName": {branches, detail, is_passthrough, class_id}}
        键是 "ClassName.methodName"，值比 analyze_entry_methods 多一个 class_id。
    """
    if javalang is None:
        logger.warning("[branch_analyzer] javalang 不可用，跳过 ServiceImpl 分支扫描")
        return {}

    serviceimpl_rows = [
        r for r in class_rows
        if (r.get("name") or r.get("class_name") or "").endswith("ServiceImpl")
    ]
    logger.info(f"[branch_analyzer] 扫 {len(serviceimpl_rows)} 个 *ServiceImpl 类")

    result: Dict[str, Dict] = {}
    stats = {"methods_total": 0, "methods_complex": 0, "parse_fail": 0}

    for row in serviceimpl_rows:
        cls = (row.get("name") or row.get("class_name") or "").strip()
        cid = str(row.get("class_id") or row.get("nodeId") or "")
        src = row.get("source_code") or ""
        methods = _extract_public_methods_from_class_source(src)[:max_methods_per_class]
        stats["methods_total"] += len(methods)
        for mth in methods:
            info = analyze_method(mth["source"])
            if info is None:
                stats["parse_fail"] += 1
                continue
            if info["branches"] < min_branches:
                continue
            stats["methods_complex"] += 1
            result[f"{cls}.{mth['name']}"] = {
                **info,
                "class_id": cid,
            }

    logger.info(
        f"[branch_analyzer] ServiceImpl 扫描: {stats['methods_total']} 方法中 "
        f"{stats['methods_complex']} 个 branches >= {min_branches}, "
        f"{stats['parse_fail']} 个解析失败"
    )
    return result


def format_serviceimpl_branch_hint(service_analysis: Dict[str, Dict]) -> str:
    """把 ServiceImpl 分支分析格式化为 prompt 表格。"""
    if not service_analysis:
        return "(未检测到分支数 ≥ 2 的 ServiceImpl 方法)"
    lines = [
        "| Service 方法 | 分支总数 | if | switch | try | loop |",
        "|---|---|---|---|---|---|",
    ]
    # 按分支数降序
    sorted_items = sorted(
        service_analysis.items(), key=lambda kv: kv[1]["branches"], reverse=True,
    )
    for method, info in sorted_items:
        d = info["detail"]
        loop = d["for"] + d["while"] + d["do"]
        lines.append(
            f"| `{method}` | {info['branches']} | {d['if']} | {d['switch']} | {d['try']} | {loop} |"
        )
    return "\n".join(lines)
