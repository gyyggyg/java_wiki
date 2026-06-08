"""从类源码里检测「可能是业务状态字段」的候选 + 收集引用片段。

为 §7 业务状态流转图提供纯 Python 的输入预处理：
- 过滤 Entity 类（@TableName / @Entity 注解）
- 按字段名模式挑候选字段
- 正则扫描整个业务流 scope 里的类源码，找 setter/getter/直接比较的引用点

不调 LLM，不查 Neo4j。结果交给 Claude 去识别状态集和转移关系。
"""
from __future__ import annotations
import logging
import re
from typing import Dict, List, Optional

try:
    import javalang
except ImportError:
    javalang = None  # 没装 javalang 时自动退回正则

logger = logging.getLogger("business_flow.claude.state_field_detector")


# 候选字段名模式（大小写不敏感；匹配整个字段名 —— 不能只是子串）
_STATE_FIELD_PATTERNS = [
    re.compile(r"^(status|state|phase|stage|kind|result|level)$", re.IGNORECASE),
    re.compile(r"^is[A-Z]\w*$"),                 # isShow / isDelete / isPublished
    re.compile(r"^\w+(Status|State|Type|Phase|Flag|Kind)$"),  # orderStatus, deleteFlag, articleType
    re.compile(r"^(has|can|should|need)[A-Z]\w*$"),  # hasAudit / canRefund ...
]

# Entity 判定：类源码含以下任一注解视为数据实体
_ENTITY_ANNOTATIONS = (
    "@TableName",   # MyBatis-Plus
    "@Entity",      # JPA
    "@Table",       # JPA
    "@Document",    # Mongo
    "@Data",        # Lombok —— 不够精确但能涵盖大量 POJO
)

# 排除名单：即使匹配模式也不画状态机的字段名（通用污染字段）
_EXCLUDE_FIELD_NAMES = {
    "id", "createTime", "updateTime", "createBy", "updateBy",
    "createdAt", "updatedAt", "gmtCreate", "gmtModified",
    "version", "remark", "description", "name", "title", "content",
    "timestamp", "time", "date", "dateType",
}

# 非 Entity 类名后缀（即使源码里有 @Data 也不纳入候选，避免把 DTO 当 Entity）
_NON_ENTITY_SUFFIXES = (
    "DTO", "VO", "Param", "Request", "Response", "Result",
    "Query", "Wrapper", "Example", "Criteria",
    "Config", "Handler", "Listener", "Filter", "Util", "Helper",
)


def is_entity_class(row: Dict) -> bool:
    """判断一个类是否是 Entity（数据实体）"""
    name = (row.get("name") or row.get("class_name") or "").strip()
    src = row.get("source_code") or ""
    if not name or not src:
        return False
    # 名字后缀排除
    for suf in _NON_ENTITY_SUFFIXES:
        if name.endswith(suf):
            return False
    # 源码含 Entity 注解
    for anno in _ENTITY_ANNOTATIONS:
        if anno in src:
            return True
    return False


def _is_state_field_name(field_name: str) -> bool:
    if not field_name:
        return False
    if field_name in _EXCLUDE_FIELD_NAMES:
        return False
    return any(p.search(field_name) for p in _STATE_FIELD_PATTERNS)


# ============== javalang AST 版（主路径） ==============

def _extract_fields_via_javalang(src: str) -> Optional[List[Dict]]:
    """用 javalang AST 精确抽字段。解析失败时返回 None。

    比正则稳健得多：能处理任意数量的注解、嵌套泛型、复杂字段初始化等。
    """
    if javalang is None:
        return None
    # 尝试两种解析路径：完整编译单元 / 包在 dummy 类里
    tree = None
    for wrapped in (src, f"public class _Probe {{ {src} }}"):
        try:
            tree = javalang.parse.parse(wrapped)
            break
        except Exception:
            continue
    if tree is None:
        return None

    fields: List[Dict] = []
    for _path, node in tree.filter(javalang.tree.FieldDeclaration):
        # javalang 把 type 的可读名字放在 node.type.name（含 `?` 泛型时是 BasicType/ReferenceType）
        try:
            type_name = node.type.name
        except AttributeError:
            type_name = str(node.type)
        # type 参数化（Integer vs List<Integer>）
        type_args = getattr(node.type, "arguments", None)
        if type_args:
            try:
                inner = ", ".join(
                    (a.type.name if getattr(a, "type", None) else "?")
                    for a in type_args
                )
                type_name = f"{type_name}<{inner}>"
            except Exception:
                pass
        # javadoc 在 node.documentation（javalang 已去掉 /** 包装）
        jdoc = (node.documentation or "").strip().replace("\n", " ").replace("*", "").strip()
        for decl in node.declarators:
            fields.append({
                "name": decl.name,
                "type": type_name,
                "javadoc": jdoc[:200],
            })
    return fields


# ============== 正则兜底版 ==============

_FIELD_DECL_RE = re.compile(
    r"""(?:/\*\*(?P<jdoc>[\s\S]*?)\*/\s*)?       # 可选 JavaDoc
         (?:@\w+(?:\s*\([^)]*\))?\s*)*           # 0 或多个注解（支持 `@X(y)`）
         (?P<mod>(?:public|private|protected)\s+) # 必须有访问修饰符（区分字段 vs 语句）
         (?:(?:static|final|volatile|transient)\s+)*
         (?P<type>[\w<>\[\],?&\s\.]+?)\s+
         (?P<name>\w+)\s*
         (?:=\s*[^;]+)?;""",
    re.VERBOSE | re.DOTALL,
)


def _extract_fields_via_regex(src: str) -> List[Dict]:
    fields: List[Dict] = []
    for m in _FIELD_DECL_RE.finditer(src):
        fname = (m.group("name") or "").strip()
        ftype = (m.group("type") or "").strip()
        jdoc = (m.group("jdoc") or "").strip().replace("\n", " ").replace("*", "").strip()
        if "(" in ftype or "{" in ftype:
            continue
        fields.append({"name": fname, "type": ftype, "javadoc": jdoc[:200]})
    return fields


def extract_fields_from_class(class_row: Dict) -> List[Dict]:
    """从 Entity 类源码里抽字段声明。优先 javalang AST，失败时回落到正则。"""
    src = class_row.get("source_code") or ""
    if not src:
        return []
    ast_fields = _extract_fields_via_javalang(src)
    if ast_fields is not None:
        return ast_fields
    return _extract_fields_via_regex(src)


def _collect_field_usages_in_source(
    field_name: str,
    all_class_rows: List[Dict],
    max_snippets_per_class: int = 6,
) -> List[Dict]:
    """在所有类源码里找对该字段的 setter/getter/直接比较。

    返回 [{class, class_id, snippet, kind}, ...]，kind ∈ {"assign", "compare", "mention"}
    """
    # 构造正则（字段首字母大写用于 setter/getter）
    capped = field_name[0].upper() + field_name[1:] if field_name else ""
    if not capped:
        return []

    # setter: .setXxx(value)
    set_re = re.compile(rf"\.set{re.escape(capped)}\s*\(([^)]*)\)")
    # getter comparison: .getXxx() <op> val
    get_cmp_re = re.compile(
        rf"\.get{re.escape(capped)}\s*\(\s*\)\s*(==|!=|>=|<=|>|<)\s*([^;\s)&|]+)"
    )
    # 直接字段访问（public/same-package）: .xxx <op> val
    direct_cmp_re = re.compile(
        rf"\.{re.escape(field_name)}\s*(==|!=|>=|<=|>|<)\s*([^;\s)&|]+)"
    )
    # 直接字段赋值: .xxx = val
    direct_assign_re = re.compile(rf"\.{re.escape(field_name)}\s*=\s*([^;]+);")

    results: List[Dict] = []
    for row in all_class_rows:
        cls_name = (row.get("name") or row.get("class_name") or "").strip()
        cls_id = str(row.get("class_id") or row.get("nodeId") or "")
        src = row.get("source_code") or ""
        if not cls_name or not src:
            continue
        # 本类的字段声明不算引用
        src_body = src
        per_class_snips = 0

        def add(kind: str, match_obj) -> bool:
            nonlocal per_class_snips
            if per_class_snips >= max_snippets_per_class:
                return False
            start = max(match_obj.start() - 30, 0)
            end = min(match_obj.end() + 30, len(src_body))
            ctx = src_body[start:end].replace("\n", " ").strip()
            results.append({
                "class": cls_name,
                "class_id": cls_id,
                "kind": kind,
                "snippet": ctx,
            })
            per_class_snips += 1
            return True

        for m in set_re.finditer(src_body):
            if not add("assign", m):
                break
        for m in get_cmp_re.finditer(src_body):
            if not add("compare", m):
                break
        for m in direct_cmp_re.finditer(src_body):
            if not add("compare", m):
                break
        for m in direct_assign_re.finditer(src_body):
            if not add("assign", m):
                break
    return results


def detect_state_field_candidates(
    all_class_rows: List[Dict],
    min_usages: int = 1,
    max_candidates: int = 8,
) -> List[Dict]:
    """在整个业务流 scope 里检测可能是业务状态机的候选字段。

    Args:
        all_class_rows: 来自 fetch_classes_full_context 的结果
        min_usages: 字段至少在多少处被 set/compare 才算候选（默认 1 —— 即便只有 1 处
            引用也可能是真状态机；由后续 LLM 进一步判定）
        max_candidates: 最多返回几个候选

    Returns:
        候选字段列表（见下文结构）
    """
    # 1. 挑 Entity 类
    entity_rows = [r for r in all_class_rows if is_entity_class(r)]
    logger.info(
        f"[state_detector] 共 {len(all_class_rows)} 个类，识别出 {len(entity_rows)} 个 Entity 类"
    )
    if entity_rows:
        logger.debug(
            f"[state_detector] Entity 类: {[r.get('name') or r.get('class_name') for r in entity_rows[:20]]}"
        )

    # 统计各环节过滤情况
    stat_total_fields = 0
    stat_state_named = 0
    stat_passed_usage = 0

    candidates: List[Dict] = []
    for row in entity_rows:
        owner_cls = (row.get("name") or row.get("class_name") or "").strip()
        owner_cid = str(row.get("class_id") or row.get("nodeId") or "")
        fields = extract_fields_from_class(row)
        stat_total_fields += len(fields)

        per_class_state_fields: List[str] = []
        for f in fields:
            fname = f["name"]
            if not _is_state_field_name(fname):
                continue
            stat_state_named += 1
            per_class_state_fields.append(fname)
            usages = _collect_field_usages_in_source(fname, all_class_rows)
            if len(usages) < min_usages:
                logger.debug(
                    f"[state_detector] {owner_cls}.{fname} 匹配状态字段名但引用数不足 "
                    f"({len(usages)} < {min_usages})，过滤"
                )
                continue
            stat_passed_usage += 1
            candidates.append({
                "owner_class": owner_cls,
                "owner_class_id": owner_cid,
                "field_name": fname,
                "field_type": f["type"],
                "field_javadoc": f["javadoc"],
                "usages": usages,
                "usage_count": len(usages),
            })

        if per_class_state_fields:
            logger.debug(
                f"[state_detector] {owner_cls} 字段数={len(fields)}, "
                f"状态字段={per_class_state_fields}"
            )
        elif fields:
            logger.debug(
                f"[state_detector] {owner_cls} 字段数={len(fields)}，无状态命名模式字段 "
                f"(样例 {[f['name'] for f in fields[:8]]})"
            )

    # 按 usage_count 降序，取 top N
    candidates.sort(key=lambda x: x["usage_count"], reverse=True)
    logger.info(
        f"[state_detector] 字段漏斗: {stat_total_fields} 总字段 → "
        f"{stat_state_named} 状态命名模式 → {stat_passed_usage} 有 ≥{min_usages} 处引用 "
        f"→ 返回前 {min(max_candidates, len(candidates))} 个候选"
    )
    if not candidates and stat_total_fields > 0:
        logger.warning(
            f"[state_detector] 14 个 Entity 但 0 候选：可能本业务流确实无状态机，"
            f"或状态字段命名不匹配常见模式（如 isXxx/*Status/*Flag）"
        )
    return candidates[:max_candidates]


def format_candidates_for_prompt(candidates: List[Dict]) -> str:
    """把候选清单格式化成 prompt 可读文本。"""
    if not candidates:
        return "(未检测到符合模式的状态字段候选)"
    lines: List[str] = []
    for i, cand in enumerate(candidates, 1):
        lines.append(f"### 候选 {i}: `{cand['owner_class']}.{cand['field_name']}`")
        lines.append(f"- 字段类型: `{cand['field_type']}`")
        lines.append(f"- owner_class_id: {cand['owner_class_id']}")
        if cand.get("field_javadoc"):
            lines.append(f"- JavaDoc 注释: {cand['field_javadoc']}")
        lines.append(f"- 引用点（{cand['usage_count']} 处）:")
        for u in cand["usages"][:10]:
            k = {"assign": "赋值", "compare": "比较", "mention": "提及"}.get(u["kind"], u["kind"])
            lines.append(f"    - [{k}] `{u['class']}` (class_id={u['class_id']}): `{u['snippet']}`")
        lines.append("")
    return "\n".join(lines)
