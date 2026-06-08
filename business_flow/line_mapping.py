"""源码行号定位 + source_id 生成 —— 为 mermaid 图每个节点映射到文件行号。

参考 graph/id_generate.py 的 find_class_or_method_range 和 generate_uuid_4digits，
但不依赖 langchain / langgraph，独立可用。
"""

import logging
import re
import uuid
from typing import Dict, List, Optional, Set

logger = logging.getLogger("business_flow.line_mapping")


# ============================================================
# UUID 生成（8 位数字）
# ============================================================

def generate_source_id(existing: Optional[Set[str]] = None) -> str:
    """生成 8 位数字 source_id，避免与 existing 集合内碰撞。"""
    for _ in range(100):
        sid = str(uuid.uuid4().int)[:8]
        if existing is None or sid not in existing:
            if existing is not None:
                existing.add(sid)
            return sid
    # 极端兜底：12 位
    sid = str(uuid.uuid4().int)[:12]
    if existing is not None:
        existing.add(sid)
    return sid


# ============================================================
# 行号定位（从 full_code 里找 class/method 片段的行范围）
# ============================================================

def find_code_line_range(full_code: str, target_code: str, _name: str) -> List[str]:
    """在 full_code 中按片段首行匹配，算出 target_code 的行范围 ["start-end"]。"""
    if not full_code or not target_code:
        return []
    full_lines = full_code.split("\n")
    target_lines = target_code.strip().split("\n")

    first_non_anno = 0
    for idx, line in enumerate(target_lines):
        if not line.strip().startswith("@"):
            first_non_anno = idx
            break
    first_line = target_lines[first_non_anno].strip()
    if not first_line:
        return []

    start_line = None
    for i, line in enumerate(full_lines, 1):
        if first_line in line.strip():
            match = True
            for j in range(min(3, len(target_lines) - first_non_anno)):
                if i + j - 1 < len(full_lines):
                    t_idx = first_non_anno + j
                    if t_idx < len(target_lines) and target_lines[t_idx].strip():
                        if target_lines[t_idx].strip() not in full_lines[i + j - 1]:
                            match = False
                            break
            if match:
                start_line = i
                break
    if start_line is None:
        return []
    end_line = start_line + len(target_lines) - first_non_anno - 1
    return [f"{start_line}-{end_line}"]


def find_class_or_method_range(full_code: str, code_snippet: str, name: str) -> List[str]:
    """用正则匹配 class/method 声明行，然后找配对大括号确定结束行。

    返回 ["start-end"]。找不到时退回 find_code_line_range。
    """
    if not full_code or not name:
        return []
    lines = full_code.split("\n")
    class_pat = rf"(public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+|static\s+)*" \
                rf"(?:class|interface|enum|record)\s+{re.escape(name)}\b"
    method_pat = rf"(public|private|protected)?\s*[\w\<\>\[\]\,\s\.]+\s+{re.escape(name)}\s*\([^)]*\)\s*\{{"

    start_line = None
    for i, line in enumerate(lines, 1):
        if re.search(class_pat, line) or re.search(method_pat, line):
            start_line = i
            break
    if start_line is None:
        return find_code_line_range(full_code, code_snippet, name)

    # 配对大括号
    brace = 0
    in_str = False
    end_line = None
    for i in range(start_line - 1, len(lines)):
        line = lines[i]
        for ci, ch in enumerate(line):
            if ch == '"' and (ci == 0 or line[ci - 1] != "\\"):
                in_str = not in_str
            if not in_str:
                if ch == "{":
                    brace += 1
                elif ch == "}":
                    brace -= 1
                    if brace == 0:
                        end_line = i + 1
                        break
        if end_line:
            break
    if end_line is None:
        end_line = start_line + len((code_snippet or "").strip().split("\n")) - 1
    return [f"{start_line}-{end_line}"]


# ============================================================
# 源码行号标注（喂给 LLM 做 source_id 划分）
# ============================================================

def tag_code_lines(source_code: str, strip_annotations: bool = True) -> Dict[str, str]:
    """把源码转成 {"1": "line content", "2": ...} 的 dict，供 LLM 精确引用行号。

    strip_annotations=True 时跳过 @Anno 开头的行（与 four_chart.py 一致）。
    """
    lines = (source_code or "").split("\n")
    if strip_annotations:
        lines = [ln for ln in lines if not ln.strip().startswith("@")]
    return {str(i + 1): ln for i, ln in enumerate(lines)}


# ============================================================
# 行号范围文本解析与 offset 叠加
# ============================================================

def apply_offset_to_lines(raw: List, offset: int) -> List[str]:
    """把 LLM 返回的方法局部行号（可能是 ["8-10", "15"]）叠加 offset，
    转成文件级行号字符串列表。异常条目跳过并告警。
    """
    out: List[str] = []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        logger.warning(f"apply_offset: 期待 list 得到 {type(raw).__name__}: {raw}")
        return out
    for item in raw:
        s = str(item).strip()
        if not s:
            continue
        try:
            if "-" in s:
                a, b = s.split("-", 1)
                a, b = int(a), int(b)
                out.append(f"{a + offset}-{b + offset}")
            else:
                out.append(str(int(s) + offset))
        except (ValueError, IndexError):
            logger.warning(f"apply_offset: 行号解析失败 item='{item}'，跳过")
            continue
    return out


# ============================================================
# Neo4j 查询 —— 取方法源码 + 所在文件源码 + 所在类源码
# ============================================================

_PARAM_SIG_RE = re.compile(r"\s*\([^)]*\)\s*$")
_GENERIC_RE = re.compile(r"\s*<[^>]+>\s*$")


def normalize_method_identifier(text: str) -> str:
    """把形如 `foo(Param1, Param2)` / `foo<T>` 规整成 `foo`。

    planner 偶尔输出带参数签名的方法名以区分重载，但 Neo4j 里 Method.name
    不含签名；这里统一去掉参数括号和泛型尾巴。
    """
    if not text:
        return text
    s = text.strip()
    s = _PARAM_SIG_RE.sub("", s)
    s = _GENERIC_RE.sub("", s)
    return s.strip()


async def fetch_method_source(neo4j, class_name: str, method_name: str,
                               param_hint: Optional[str] = None) -> Optional[Dict]:
    """按 class_name + method_name 查方法源码 + 所在类/文件源码。

    - 输入会先做归一化（剥掉 `(param)` 签名和 `<T>` 泛型）
    - `param_hint` 非空时：用于重载消歧，优先挑 `method_source` 里包含该串的那个重载
      （典型用法：planner 输出 `foo(OmsMoneyInfoParam)`，我们把 `OmsMoneyInfoParam`
      作为 hint 穿透到查询；如果不给，默认挑 source_code 最长的）
    - 若 (class, method) 精确匹配失败，退回到"仅按 method_name 在任意类"匹配一次，
      仍失败再返回 None

    返回 dict: {method_id, method_name, method_source, class_id, class_name,
               class_source, file_name, file_source}
    """
    class_name = (class_name or "").strip()
    method_name = normalize_method_identifier(method_name or "")
    param_hint = (param_hint or "").strip() or None
    if not class_name or not method_name:
        return None

    query = """
    MATCH (c) WHERE (c:Class OR c:Interface OR c:Enum OR c:Record) AND c.name = $class_name
    MATCH (c)-[:DECLARES]->(m:Method) WHERE m.name = $method_name
    OPTIONAL MATCH (f:File)-[:DECLARES]->(c)
    RETURN m.nodeId AS method_id,
           m.name AS method_name,
           m.source_code AS method_source,
           c.nodeId AS class_id,
           c.name AS class_name,
           c.source_code AS class_source,
           f.name AS file_name,
           f.source_code AS file_source
    """
    rows = await neo4j.execute_query(query, {"class_name": class_name, "method_name": method_name})

    # 兜底：(class, method) 失败时，仅按 method_name 在任意类搜
    if not rows:
        logger.warning(
            f"[fetch_method_source] 精确匹配失败 class={class_name} method={method_name}，"
            f"回退到仅按 method_name 搜索"
        )
        fallback_query = """
        MATCH (m:Method) WHERE m.name = $method_name
        MATCH (c)-[:DECLARES]->(m)
        WHERE c:Class OR c:Interface OR c:Enum OR c:Record
        OPTIONAL MATCH (f:File)-[:DECLARES]->(c)
        RETURN m.nodeId AS method_id,
               m.name AS method_name,
               m.source_code AS method_source,
               c.nodeId AS class_id,
               c.name AS class_name,
               c.source_code AS class_source,
               f.name AS file_name,
               f.source_code AS file_source
        LIMIT 10
        """
        rows = await neo4j.execute_query(fallback_query, {"method_name": method_name})
        if rows:
            logger.info(
                f"[fetch_method_source] 回退命中 {len(rows)} 条，命中的类: "
                f"{[r.get('class_name') for r in rows]}"
            )

    if not rows:
        return None

    # 重载消歧：先按 param_hint 过滤；未命中再降级到"最长"
    if param_hint:
        matching = [r for r in rows if param_hint in (r.get("method_source") or "")]
        if matching:
            matching.sort(key=lambda r: len(r.get("method_source") or ""), reverse=True)
            logger.info(
                f"[fetch_method_source] 按 param_hint={param_hint!r} 命中 "
                f"{len(matching)}/{len(rows)} 个重载"
            )
            return matching[0]
        logger.warning(
            f"[fetch_method_source] param_hint={param_hint!r} 未在任何重载的 source_code "
            f"中找到，退回最长重载"
        )
    rows.sort(key=lambda r: len(r.get("method_source") or ""), reverse=True)
    return rows[0]


async def fetch_file_source_for_classes(neo4j, class_ids: List[str]) -> Dict[str, Dict]:
    """批量查类及所在文件的源码。

    返回 {class_id: {class_name, class_source, file_name, file_source}}
    """
    if not class_ids:
        return {}
    ids_int: List[int] = []
    for s in class_ids:
        try:
            ids_int.append(int(s))
        except (TypeError, ValueError):
            continue
    if not ids_int:
        return {}
    query = """
    MATCH (c) WHERE c.nodeId IN $ids
      AND (c:Class OR c:Interface OR c:Enum OR c:Record)
    OPTIONAL MATCH (f:File)-[:DECLARES]->(c)
    RETURN c.nodeId AS class_id,
           c.name AS class_name,
           c.source_code AS class_source,
           f.name AS file_name,
           f.source_code AS file_source
    """
    rows = await neo4j.execute_query(query, {"ids": list(set(ids_int))})
    return {
        str(r["class_id"]): {
            "class_name": r.get("class_name") or "",
            "class_source": r.get("class_source") or "",
            "file_name": r.get("file_name") or "",
            "file_source": r.get("file_source") or "",
        }
        for r in rows
    }


# ============================================================
# 通用：mapping 值归一化 (与 four_chart.py _normalize_mapping_value 一致)
# ============================================================

def normalize_mapping_value(v) -> str:
    """把 LLM 偶尔返回的 list/int 规整为 str"""
    if isinstance(v, list):
        return str(v[0]) if v else ""
    if isinstance(v, (int, float)):
        return str(v)
    return str(v) if v is not None else ""
