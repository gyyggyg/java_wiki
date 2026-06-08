"""构造"类上下文"文本，送给 §2 / §3 的 LLM。

三级降级：
  1. full source_code（在阈值内直接用）
  2. skeleton（压缩成类声明 + 字段 + 方法签名）
  3. skeleton + 按注解优先级裁剪
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger("business_flow.class_context")

DEFAULT_MAX_CHARS = 120_000
PRIORITY_ANNOTATIONS = (
    "@RestController", "@Controller", "@Service", "@Component",
    "@Configuration", "@Aspect", "@RabbitListener", "@Scheduled",
    "@Repository", "@FeignClient",
)


# ---------------- 源码骨架抽取（独立版，不依赖 category_wiki） ----------------

def extract_class_summary(source_code: str) -> str:
    """从 Java 源码提取骨架：类声明 + 字段列表 + 方法签名列表。"""
    if not source_code:
        return source_code

    lines = source_code.split("\n")
    class_decl = ""
    is_enum = False
    enum_constants: List[str] = []
    fields: List[str] = []
    methods: List[str] = []
    brace_depth = 0
    in_method = False
    method_brace_start = 0
    enum_section = True

    keep_mods = {"public", "private", "protected", "static", "abstract"}

    for line in lines:
        stripped = line.strip()
        open_c = line.count("{")
        close_c = line.count("}")

        if in_method:
            brace_depth += open_c - close_c
            if brace_depth <= method_brace_start:
                in_method = False
            continue

        if not stripped or stripped.startswith("//") or stripped.startswith("/*") \
                or stripped.startswith("*") or stripped.startswith("package ") \
                or stripped.startswith("import ") or stripped.startswith("@"):
            continue

        # 类声明
        if not class_decl:
            m = re.match(r"^(public\s+|protected\s+|private\s+|\s+)?"
                         r"(?:abstract\s+|final\s+|static\s+)*(class|interface|enum|record)\s+(\w+)", stripped)
            if m:
                is_enum = m.group(2) == "enum"
                class_decl = stripped.rstrip("{").strip()
                # 去掉注解参数里的多余换行
                if class_decl.endswith(","):
                    class_decl = class_decl[:-1]
                continue

        # 方法签名
        method_match = re.match(
            r"^((?:public|private|protected|static|final|abstract|synchronized|default|native)\s+)*"
            r"(?:<[^>]+>\s+)?"  # 泛型
            r"([\w<>\[\],\s\.]+)\s+"  # 返回类型
            r"(\w+)\s*\(([^)]*)\)",
            stripped,
        )
        if method_match and "=" not in stripped.split("(")[0]:
            mods = method_match.group(1) or ""
            ret_type = method_match.group(2).strip()
            name = method_match.group(3)
            params = method_match.group(4).strip()
            keep = [m for m in mods.split() if m in keep_mods]
            sig = f"{' '.join(keep)} {name}({params}):{ret_type}".strip()
            methods.append(sig)
            if "{" in stripped:
                in_method = True
                brace_depth = stripped.count("{") - stripped.count("}")
                method_brace_start = brace_depth - 1
            continue

        # 字段
        field_match = re.match(
            r"^((?:public|private|protected|static|final|volatile|transient)\s+)*"
            r"([\w<>\[\],\s\.]+)\s+(\w+)\s*[=;]",
            stripped,
        )
        if field_match and "(" not in stripped:
            mods = field_match.group(1) or ""
            keep = [m for m in mods.split() if m in keep_mods]
            fields.append(f"{' '.join(keep)} {field_match.group(2).strip()} {field_match.group(3)}".strip())
            enum_section = False
            continue

        # 枚举常量
        if is_enum and enum_section:
            ec = re.match(r"^(\w+)\s*(?:\(.*\))?\s*[,;]?$", stripped)
            if ec and ec.group(1).isupper():
                enum_constants.append(ec.group(1))
                if stripped.endswith(";"):
                    enum_section = False

    out = []
    if class_decl:
        out.append(class_decl)
    if enum_constants:
        out.append(f"constants: {', '.join(enum_constants)}")
    if fields:
        out.append(f"fields: {', '.join(fields)}")
    if methods:
        out.append(f"methods: {', '.join(methods)}")
    return "\n".join(out) if out else source_code[:800]


# ---------------- 上下文构造（主逻辑） ----------------

def _has_priority_annotation(source_code: str) -> bool:
    if not source_code:
        return False
    head = source_code[:800]
    return any(ann in head for ann in PRIORITY_ANNOTATIONS)


def _format_one(row: Dict, use_skeleton: bool) -> str:
    class_id = row.get("class_id")
    name = row.get("name") or "?"
    labels = row.get("labels") or []
    label_str = "/".join(l for l in labels if l in ("Class", "Interface", "Enum", "Record")) or "Entity"
    se_what = (row.get("se_what") or "").strip().replace("\n", " ")[:400]
    file_name = row.get("file_name") or "-"
    source = row.get("source_code") or ""

    if use_skeleton and source:
        try:
            source = extract_class_summary(source)
        except Exception:
            source = source[:800] + ("\n// ... (truncated)" if len(source) > 800 else "")

    return (
        f"### {label_str} {name} (class_id={class_id})\n"
        f"- file: `{file_name}`\n"
        f"- SE_What: {se_what if se_what else '(无)'}\n"
        f"- 源码{'（骨架）' if use_skeleton else ''}:\n"
        f"```java\n{source}\n```\n"
    )


def _build(rows: List[Dict], use_skeleton: bool) -> str:
    return "\n".join(_format_one(r, use_skeleton) for r in rows)


def build_class_context_text(rows: List[Dict], max_chars: int = DEFAULT_MAX_CHARS,
                              prefer_full: bool = True) -> Dict:
    """返回 {text, mode, char_count, class_count, dropped_count}"""
    if not rows:
        return {"text": "(该分类下未获取到任何类的源码)",
                "mode": "empty", "char_count": 0, "class_count": 0, "dropped_count": 0}

    # 1) full source
    if prefer_full:
        full_text = _build(rows, use_skeleton=False)
        if len(full_text) <= max_chars:
            return {"text": full_text, "mode": "full",
                    "char_count": len(full_text), "class_count": len(rows), "dropped_count": 0}
        logger.info(f"[class_context] full 源码 {len(full_text)} 字符超阈值 {max_chars}，降级 skeleton")

    # 2) skeleton 全量
    skel_text = _build(rows, use_skeleton=True)
    if len(skel_text) <= max_chars:
        return {"text": skel_text, "mode": "skeleton",
                "char_count": len(skel_text), "class_count": len(rows), "dropped_count": 0}
    logger.info(f"[class_context] skeleton {len(skel_text)} 字符仍超 {max_chars}，按注解优先级裁剪")

    # 3) skeleton + 注解优先级裁剪
    priority_rows = [r for r in rows if _has_priority_annotation(r.get("source_code") or "")]
    other_rows = [r for r in rows if r not in priority_rows]
    kept = list(priority_rows)
    budget = max_chars - len(_build(kept, use_skeleton=True))
    for r in other_rows:
        chunk = _format_one(r, use_skeleton=True)
        if len(chunk) <= budget:
            kept.append(r)
            budget -= len(chunk)
        if budget <= 2000:
            break
    dropped = len(rows) - len(kept)
    text = _build(kept, use_skeleton=True)
    logger.info(f"[class_context] 裁剪后 {len(kept)}/{len(rows)} 类, {len(text)} 字符, 丢弃 {dropped}")
    return {"text": text, "mode": "skeleton_filtered",
            "char_count": len(text), "class_count": len(kept), "dropped_count": dropped}
