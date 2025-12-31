"""Mermaid 图表验证和修复模块"""
import re
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class MermaidValidator:
    """Mermaid 图表验证器和自动修复器"""
    
    # 常见的 Mermaid 语法错误模式
    ERROR_PATTERNS = {
        "missing_diagram_type": r"^(?!sequenceDiagram|graph|flowchart|classDiagram|stateDiagram|erDiagram|gantt|pie|journey)",
        "cypher_style_arrow": r"-\s*\[:[^\]]+\]\s*->",
        "wrong_arrow_spacing": r"\S(-->|==>|-\.->|---)\S",
        "unquoted_special_chars": r"(?<!\")[\u4e00-\u9fa5]+(?!\")",  # 未引号包裹的中文
        "multiple_blank_lines": r"\n{4,}",
    }
    
    def __init__(self):
        """初始化验证器"""
        self.validation_rules = [
            self._check_diagram_type,
            self._check_arrow_syntax,
            self._check_node_syntax,
            self._check_subgraph_syntax,
        ]
    
    def validate_and_fix(self, mermaid_code: str, diagram_type: str = None) -> Tuple[bool, str, List[str]]:
        """
        验证并修复 Mermaid 代码
        
        Args:
            mermaid_code: 原始 Mermaid 代码
            diagram_type: 期望的图表类型（sequenceDiagram/graph/flowchart）
            
        Returns:
            (is_valid, fixed_code, warnings)
        """
        if not mermaid_code or not mermaid_code.strip():
            return False, mermaid_code, ["代码为空"]
        
        warnings = []
        fixed_code = mermaid_code.strip()
        
        # 第一步：基础清理
        fixed_code = self._basic_cleanup(fixed_code)
        
        # 第二步：修复图表类型声明
        fixed_code, type_warnings = self._fix_diagram_type(fixed_code, diagram_type)
        warnings.extend(type_warnings)
        
        # 第三步：删除重复的图表类型声明
        fixed_code, dup_warnings = self._remove_duplicate_diagram_types(fixed_code)
        warnings.extend(dup_warnings)
        
        # 第四步：修复箭头语法
        fixed_code, arrow_warnings = self._fix_arrow_syntax(fixed_code)
        warnings.extend(arrow_warnings)
        
        # 第五步：修复节点语法
        fixed_code, node_warnings = self._fix_node_syntax(fixed_code)
        warnings.extend(node_warnings)
        
        # 第六步：修复特殊字符
        fixed_code, char_warnings = self._fix_special_characters(fixed_code)
        warnings.extend(char_warnings)
        
        # 第七步：清理多余空行
        fixed_code = self._cleanup_blank_lines(fixed_code)
        
        # 第八步：验证基本结构
        is_valid, structure_warnings = self._validate_structure(fixed_code)
        warnings.extend(structure_warnings)
        
        if warnings:
            logger.warning(f"Mermaid 代码存在 {len(warnings)} 个问题，已自动修复")
            for w in warnings:
                logger.debug(f"  - {w}")
        
        return is_valid, fixed_code, warnings
    
    def _basic_cleanup(self, code: str) -> str:
        """基础清理：去除多余的 markdown 代码块标记"""
        # 去除开头和结尾的 ```mermaid 或 ```
        code = re.sub(r"^```(?:mermaid)?\s*\n?", "", code.strip())
        code = re.sub(r"\n?```\s*$", "", code.strip())
        
        # 统一换行符
        code = code.replace("\r\n", "\n")
        
        return code.strip()
    
    def _fix_diagram_type(self, code: str, expected_type: str = None) -> Tuple[str, List[str]]:
        """修复图表类型声明"""
        warnings = []
        lines = code.split("\n")
        
        if not lines:
            return code, warnings
        
        first_line = lines[0].strip()
        
        # 检查第一行是否是注释（标题注释）
        if first_line.startswith('%%'):
            # 如果第一行是注释，检查第二行是否是图表类型
            if len(lines) < 2:
                # 只有注释行，需要添加图表类型
                if expected_type:
                    lines.append(expected_type)
                    warnings.append(f"在注释行后添加图表类型: {expected_type}")
                else:
                    lines.append("graph TD")
                    warnings.append("在注释行后添加默认图表类型: graph TD")
                return "\n".join(lines), warnings
            
            # 检查第二行是否是有效的图表类型
            second_line = lines[1].strip()
            valid_types = ["sequenceDiagram", "graph TD", "graph LR", "graph BT", "graph RL", 
                          "flowchart TD", "flowchart LR", "flowchart BT", "flowchart RL"]
            
            if second_line not in valid_types and not second_line.startswith("graph ") and not second_line.startswith("flowchart "):
                # 第二行不是有效的图表类型，需要插入
                if expected_type:
                    lines.insert(1, expected_type)
                    warnings.append(f"在注释行后插入图表类型: {expected_type}")
                else:
                    lines.insert(1, "graph TD")
                    warnings.append("在注释行后插入默认图表类型: graph TD")
            
            return "\n".join(lines), warnings
        
        # 第一行不是注释，检查是否是有效的图表类型
        valid_types = ["sequenceDiagram", "graph TD", "graph LR", "graph BT", "graph RL", 
                      "flowchart TD", "flowchart LR", "flowchart BT", "flowchart RL"]
        
        if first_line not in valid_types:
            # 尝试修复
            if first_line == "graph":
                lines[0] = "graph TD"
                warnings.append("修复: 'graph' -> 'graph TD'")
            elif first_line == "flowchart":
                lines[0] = "flowchart TD"
                warnings.append("修复: 'flowchart' -> 'flowchart TD'")
            elif first_line.startswith("graph ") or first_line.startswith("flowchart "):
                # 保持原有方向
                pass
            elif expected_type:
                # 如果指定了期望类型，添加到开头
                lines.insert(0, expected_type)
                warnings.append(f"添加图表类型声明: {expected_type}")
            else:
                # 默认添加 graph TD
                lines.insert(0, "graph TD")
                warnings.append("添加默认图表类型: graph TD")
        
        return "\n".join(lines), warnings
    
    def _remove_duplicate_diagram_types(self, code: str) -> Tuple[str, List[str]]:
        """Remove duplicate diagram type declarations (e.g., duplicate 'flowchart TD' lines)"""
        warnings = []
        lines = code.split("\n")
        
        if len(lines) < 2:
            return code, warnings
        
        # Find the first non-comment line
        first_non_comment_idx = 0
        for i, line in enumerate(lines):
            if not line.strip().startswith('%%'):
                first_non_comment_idx = i
                break
        
        # Check if this is a diagram type declaration
        diagram_types = ["sequenceDiagram", "graph", "flowchart", "classDiagram", "stateDiagram", "erDiagram", "gantt", "pie", "journey"]
        first_line = lines[first_non_comment_idx].strip()
        
        is_diagram_type = any(first_line.startswith(dt) for dt in diagram_types)
        
        if is_diagram_type:
            # Look for duplicate diagram type declarations after the first one
            cleaned_lines = lines[:first_non_comment_idx + 1]
            found_duplicate = False
            
            for i in range(first_non_comment_idx + 1, len(lines)):
                line = lines[i].strip()
                # Skip empty lines
                if not line:
                    cleaned_lines.append(lines[i])
                    continue
                
                # Check if this line is also a diagram type declaration
                is_dup = any(line.startswith(dt) for dt in diagram_types)
                
                if is_dup:
                    warnings.append(f"删除重复的图表类型声明: {line}")
                    found_duplicate = True
                    # Skip this line
                else:
                    # Keep this line
                    cleaned_lines.append(lines[i])
            
            if found_duplicate:
                return "\n".join(cleaned_lines), warnings
        
        return code, warnings
    
    def _fix_arrow_syntax(self, code: str) -> Tuple[str, List[str]]:
        """修复箭头语法"""
        warnings = []
        original_code = code
        
        # 获取图表类型（考虑第一行可能是注释）
        lines = code.split('\n') if code else []
        diagram_type_line = ""
        
        if lines:
            first_line = lines[0].strip()
            if first_line.startswith('%%'):
                # 第一行是注释，获取第二行作为图表类型
                diagram_type_line = lines[1].strip() if len(lines) > 1 else ""
            else:
                # 第一行就是图表类型
                diagram_type_line = first_line
        
        # 0. 序列图（sequenceDiagram）的特殊处理
        if diagram_type_line.startswith('sequenceDiagram'):
            # 序列图使用不同的箭头语法，需要特殊处理
            code, seq_warnings = self._fix_sequence_diagram_syntax(code)
            warnings.extend(seq_warnings)
            return code, warnings
        
        # 1. 修复 Cypher 风格的箭头：-[:label]-> 统一转为无标签箭头
        cypher_pattern = r'-\s*\[:([^\]]+)\]\s*->'
        if re.search(cypher_pattern, code):
            # 统一移除标签，避免解析错误
            code = re.sub(cypher_pattern, r' --> ', code)
            warnings.append("修复: Cypher 风格箭头 -[:label]-> 移除标签转为 -->")
        
        # 2. graph TD 中移除所有箭头标签（推荐无标签箭头，避免解析错误）
        if diagram_type_line.startswith('graph'):
            # 移除 -- "文本" --> 格式的标签
            graph_arrow_pattern1 = r'--[ \t]*"([^"]*)"[ \t]*-->'
            if re.search(graph_arrow_pattern1, code):
                code = re.sub(graph_arrow_pattern1, r' --> ', code)
                warnings.append('修复: graph 中移除箭头标签 -- "text" --> 改为 -->')
            
            # 移除 == "文本" ==> 格式的标签
            graph_arrow_pattern2 = r'==[ \t]*"([^"]*)"[ \t]*==>'
            if re.search(graph_arrow_pattern2, code):
                code = re.sub(graph_arrow_pattern2, r' ==> ', code)
                warnings.append('修复: graph 中移除箭头标签 == "text" ==> 改为 ==>')
            
            # 移除 -. "文本" .-> 格式的标签（虚线箭头）
            graph_arrow_pattern3 = r'-\.[ \t]*"([^"]*)"[ \t]*\.->'
            if re.search(graph_arrow_pattern3, code):
                code = re.sub(graph_arrow_pattern3, r' -.-> ', code)
                warnings.append('修复: graph 中移除虚线箭头标签 -. "text" .-> 改为 -.->')
            
            # 移除 -->|文本| 格式的标签（不完整或有特殊字符）
            graph_arrow_pattern4 = r'-->[ \t]*\|([^|]*)\|'
            if re.search(graph_arrow_pattern4, code):
                code = re.sub(graph_arrow_pattern4, r' --> ', code)
                warnings.append('修复: graph 中移除箭头标签 -->|text| 改为 -->')
            
            # 修复不完整的箭头标签：-->| 但没有闭合（最常见的错误）
            # 匹配：箭头后面有 | 但行尾没有闭合的 |
            incomplete_label_pattern = r'(-->|==>|-\.->)[ \t]*\|([^|\n]*)$'
            if re.search(incomplete_label_pattern, code, re.MULTILINE):
                code = re.sub(incomplete_label_pattern, r' \1 ', code, flags=re.MULTILINE)
                warnings.append('修复: graph 中修复不完整的箭头标签 -->| 改为 -->')
        
        # 3. flowchart 中移除所有箭头标签（避免中文解析错误）
        if diagram_type_line.startswith('flowchart'):
            # 移除 -- "文本" --> 格式的标签（不匹配换行符）
            flowchart_arrow_pattern1 = r'--[ \t]*"([^"]+)"[ \t]*-->'
            if re.search(flowchart_arrow_pattern1, code):
                code = re.sub(flowchart_arrow_pattern1, r' --> ', code)
                warnings.append('修复: flowchart 中移除箭头标签 -- "text" -->')
            
            # 移除 -->|文本| 格式的标签（不匹配换行符）
            flowchart_arrow_pattern2 = r'-->[ \t]*\|([^|]+)\|[ \t]*'
            if re.search(flowchart_arrow_pattern2, code):
                code = re.sub(flowchart_arrow_pattern2, r' --> ', code)
                warnings.append('修复: flowchart 中移除箭头标签 -->|text|')
            
            # 移除 --|文本|--> 格式的标签（不匹配换行符）
            flowchart_arrow_pattern3 = r'--[ \t]*\|([^|]+)\|[ \t]*-->'
            if re.search(flowchart_arrow_pattern3, code):
                code = re.sub(flowchart_arrow_pattern3, r' --> ', code)
                warnings.append('修复: flowchart 中移除箭头标签 --|text|-->')
        
        # 3. 统一箭头两侧空格
        arrow_patterns = [
            (r'(\S)(-->)(\S)', r'\1 \2 \3'),  # A-->B 转为 A --> B
            (r'(\S)(==>)(\S)', r'\1 \2 \3'),  # A==>B 转为 A ==> B
            (r'(\S)(-\.->)(\S)', r'\1 \2 \3'),  # A.->B 转为 A -.-> B
        ]
        
        arrow_space_fixed = False
        for pattern, replacement in arrow_patterns:
            if re.search(pattern, code):
                code = re.sub(pattern, replacement, code)
                arrow_space_fixed = True
        
        # 4. 修复 flowchart 中箭头标签后直接跟节点定义的问题
        # 例如：A -->|text| B["label"] 应该先定义 B["label"]，然后 A -->|text| B
        # 这个比较复杂，暂时只检测并警告
        
        if arrow_space_fixed and not any("箭头" in w for w in warnings):
            warnings.append("修复: 统一箭头空格")
        
        return code, warnings
    
    def _fix_sequence_diagram_syntax(self, code: str) -> Tuple[str, List[str]]:
        """修复序列图（sequenceDiagram）的语法问题"""
        warnings = []
        lines = code.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # 跳过空行和第一行（图表类型声明）
            if not stripped or i == 0:
                fixed_lines.append(line)
                continue
            
            # 跳过注释
            if stripped.startswith('%%'):
                fixed_lines.append(line)
                continue
            
            # 处理 participant 声明
            if stripped.startswith('participant '):
                # 清理参与者名称：移除特殊字符，只保留字母数字下划线
                fixed_line = self._fix_sequence_participant(stripped)
                if fixed_line != stripped:
                    warnings.append(f"修复: 参与者声明 - {stripped[:50]}")
                fixed_lines.append(fixed_line)
                continue
            
            # 处理箭头语法（sequenceDiagram 的箭头）
            if '->>' in stripped or '-->>' in stripped or '->>+' in stripped or '->>-' in stripped:
                # sequenceDiagram 的标准箭头
                fixed_line = self._fix_sequence_arrow(stripped)
                if fixed_line != stripped:
                    warnings.append(f"修复: 序列图箭头 - {stripped[:50]}")
                fixed_lines.append(fixed_line)
                continue
            
            # 保持其他行不变
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines), warnings
    
    def _fix_sequence_participant(self, line: str) -> str:
        """修复序列图参与者声明"""
        # participant ClassName as 显示名称
        # 或者 participant ClassName
        
        if ' as ' in line:
            # 格式：participant ID as Display Name
            parts = line.split(' as ', 1)
            if len(parts) == 2:
                prefix = parts[0]  # "participant ClassName"
                display_name = parts[1].strip()
                
                # 清理 participant ID（只保留字母、数字、下划线）
                participant_id = prefix.replace('participant ', '').strip()
                clean_id = re.sub(r'[^\w]', '_', participant_id)
                
                return f"participant {clean_id} as {display_name}"
        else:
            # 格式：participant ClassName
            participant_name = line.replace('participant ', '').strip()
            # 清理名称：只保留字母、数字、下划线
            clean_name = re.sub(r'[^\w]', '_', participant_name)
            return f"participant {clean_name}"
        
        return line
    
    def _fix_sequence_arrow(self, line: str) -> str:
        """修复序列图箭头语法"""
        # 序列图箭头格式：ParticipantA ->> ParticipantB: methodName
        # 常见问题：
        # 1. 冒号后的方法名包含特殊字符
        # 2. 参与者名称包含特殊字符
        # 3. 箭头空格不规范
        
        # 匹配序列图箭头：A ->> B: message
        # 支持：->>, -->>, ->>+, -->>+, ->>-, -->>-
        arrow_pattern = r'^(\w+)\s*(->>|-->>|->>\+|-->>\+|->>-|-->>-)\s*(\w+)\s*:\s*(.+)$'
        match = re.match(arrow_pattern, line.strip())
        
        if match:
            from_participant = match.group(1)
            arrow = match.group(2)
            to_participant = match.group(3)
            message = match.group(4).strip()
            
            # 清理参与者名称
            from_clean = re.sub(r'[^\w]', '_', from_participant)
            to_clean = re.sub(r'[^\w]', '_', to_participant)
            
            # 清理消息内容：移除可能导致解析错误的字符
            # 保留：字母、数字、中文、空格、括号、下划线
            message_clean = re.sub(r'[^\w\u4e00-\u9fa5\s()\[\]_,.]', '', message)
            
            return f"{from_clean} {arrow} {to_clean}: {message_clean}"
        
        return line
    
    def _fix_node_syntax(self, code: str) -> Tuple[str, List[str]]:
        """修复节点语法"""
        warnings = []
        
        # 检测并修复常见的节点定义问题
        # 例如：确保特殊形状语法正确
        
        # 1. 检查六边形节点：应该是 {{text}} 而不是 {text}
        if re.search(r'(?<!\{)\{(?!\{)[^\}]+\}(?!\})', code):
            code = re.sub(r'(?<!\{)\{([^\}]+)\}(?!\})', r'{{\1}}', code)
            warnings.append("修复: 单花括号 {text} 转为双花括号 {{text}}（六边形节点）")
        
        # 2. 修复节点ID中的下划线和可能的保留字
        first_line = code.split('\n')[0].strip() if code else ""
        if first_line.startswith('flowchart') or first_line.startswith('graph'):
            code, node_warnings = self._fix_flowchart_node_ids(code)
            warnings.extend(node_warnings)
        
        return code, warnings
    
    def _fix_flowchart_node_ids(self, code: str) -> Tuple[str, List[str]]:
        """修复 flowchart/graph 中的节点ID命名问题"""
        warnings = []
        original_code = code
        
        # 1. 修复下划线+数字的组合（最常见的错误）
        # 例如：method_11 → method11, file_1 → file1
        underscore_number_pattern = r'\b(file|block|class|method|node)_(\d+)\b'
        if re.search(underscore_number_pattern, code):
            code = re.sub(underscore_number_pattern, r'\g<1>\g<2>', code)
            warnings.append("修复: 下划线+数字组合 (如 method_11 → method11)")
        
        # 2. 常见的有问题的保留字节点ID
        problematic_ids = {
            r'\bend_node\b': 'endNode',
            r'\bstart_node\b': 'startNode',
            r'\bcall\b(?![a-zA-Z])': 'callMethod',  # 避免匹配 callback
            r'\bend\b(?![a-zA-Z])': 'endNode',
            r'\bstart\b(?![a-zA-Z])': 'startNode',
            r'\bprocess\b(?![a-zA-Z])': 'processStep',
            r'\bcheck\b(?![a-zA-Z])': 'checkNode',
        }
        
        for pattern, replacement in problematic_ids.items():
            # 只替换作为节点ID的情况（在行首或箭头后）
            # 匹配模式：行首空格 + ID 或 --> ID 或 ==> ID
            # 注意：行首用 ^，后面用捕获组，避免在行首添加多余空格
            node_pattern = r'(^|\s+|-->|==>|-\.->|--)\s*' + pattern
            
            if re.search(node_pattern, code, re.MULTILINE):
                # 如果匹配到的是行首（空字符串）或已有空格，只添加replacement；如果是箭头，添加空格+replacement
                def replace_func(m):
                    prefix = m.group(1)
                    if prefix == '' or prefix.isspace():
                        return prefix + replacement
                    else:
                        # 箭头后面需要添加空格
                        return prefix + ' ' + replacement
                
                code = re.sub(node_pattern, replace_func, code, flags=re.MULTILINE)
                warnings.append(f"修复: 节点ID {pattern} → {replacement}")
        
        if code != original_code:
            # 清理可能产生的多余空格
            code = re.sub(r'  +', ' ', code)
        
        return code, warnings
    
    def _fix_special_characters(self, code: str) -> Tuple[str, List[str]]:
        """修复特殊字符（如中文、空格等）"""
        warnings = []
        lines = code.split("\n")
        fixed_lines = []
        
        for line in lines:
            # 跳过图表类型声明行
            if line.strip() in ["sequenceDiagram", "graph TD", "graph LR", "flowchart TD", "flowchart LR"]:
                fixed_lines.append(line)
                continue
            
            # 修复六边形节点中包含中文和空格的情况
            # 例如：nodeId{{"类 Class"}} 会导致解析错误
            # 解决方案：如果 {{}} 内包含中文，改用 [] 矩形节点或去掉特殊字符
            
            # 检测 {{含中文}} 的模式
            hexagon_pattern = r'(\w+)\{\{([^}]*[\u4e00-\u9fa5][^}]*)\}\}'
            matches = list(re.finditer(hexagon_pattern, line))
            
            # 从后往前替换，避免位置偏移问题
            for match in reversed(matches):
                node_id = match.group(1)
                label = match.group(2)
                
                # 如果标签包含中文和空格，可能会有问题
                if re.search(r'[\u4e00-\u9fa5]', label) and ' ' in label:
                    # 改用矩形节点 [] 更稳定
                    old_text = match.group(0)
                    new_text = f'{node_id}["{label}"]'
                    start, end = match.span()
                    line = line[:start] + new_text + line[end:]
                    warnings.append(f'修复: 六边形节点 {old_text} 改为矩形节点 {new_text}（避免中文+空格解析错误）')
            
            fixed_lines.append(line)
        
        return "\n".join(fixed_lines), warnings
    
    def _cleanup_blank_lines(self, code: str) -> str:
        """清理多余的空行"""
        # 最多保留连续2个空行
        code = re.sub(r'\n{4,}', '\n\n\n', code)
        return code.strip()
    
    def _validate_structure(self, code: str) -> Tuple[bool, List[str]]:
        """验证基本结构"""
        warnings = []
        is_valid = True
        
        lines = [l.strip() for l in code.split("\n") if l.strip()]
        
        if not lines:
            return False, ["代码为空"]
        
        # 检查第一行
        first_line = lines[0]
        valid_starts = ["sequenceDiagram", "graph", "flowchart", "classDiagram", "stateDiagram"]
        if not any(first_line.startswith(s) for s in valid_starts):
            warnings.append(f"警告: 第一行应该是图表类型声明，当前: {first_line}")
            is_valid = False
        
        # 检查是否至少有一个节点或边的定义
        has_content = False
        for line in lines[1:]:
            if any(arrow in line for arrow in ["-->", "==>", "-.->", "---", "->>", "->>"]):
                has_content = True
                break
            if re.search(r'\w+\[.+\]|\w+\(.+\)|\w+\{\{.+\}\}', line):
                has_content = True
                break
        
        if not has_content:
            warnings.append("警告: 图表没有实际内容（节点或边）")
            is_valid = False
        
        return is_valid, warnings
    
    def _check_diagram_type(self, code: str) -> List[str]:
        """检查图表类型声明"""
        warnings = []
        first_line = code.split("\n")[0].strip()
        if not re.match(r'^(sequenceDiagram|graph\s+\w+|flowchart\s+\w+)', first_line):
            warnings.append(f"图表类型声明可能不正确: {first_line}")
        return warnings
    
    def _check_arrow_syntax(self, code: str) -> List[str]:
        """检查箭头语法"""
        warnings = []
        
        # 检查 Cypher 风格箭头
        if re.search(r'-\s*\[:[^\]]+\]\s*->', code):
            warnings.append("存在 Cypher 风格箭头 -[:label]->，应使用 -- \"label\" -->")
        
        # 检查箭头两侧是否有空格
        if re.search(r'\S(-->|==>|-\.->)\S', code):
            warnings.append("箭头两侧缺少空格")
        
        return warnings
    
    def _check_node_syntax(self, code: str) -> List[str]:
        """检查节点语法"""
        warnings = []
        
        # 检查未配对的括号
        open_brackets = code.count('[') + code.count('(') + code.count('{')
        close_brackets = code.count(']') + code.count(')') + code.count('}')
        if open_brackets != close_brackets:
            warnings.append(f"括号不匹配: 开括号 {open_brackets} 个, 闭括号 {close_brackets} 个")
        
        return warnings
    
    def _check_subgraph_syntax(self, code: str) -> List[str]:
        """检查 subgraph 语法"""
        warnings = []
        
        # 检查 subgraph 是否有对应的 end
        subgraph_count = len(re.findall(r'\bsubgraph\b', code))
        end_count = len(re.findall(r'\bend\b', code))
        
        if subgraph_count != end_count:
            warnings.append(f"subgraph 不匹配: {subgraph_count} 个 subgraph, {end_count} 个 end")
        
        return warnings


# 工具函数
def validate_mermaid(code: str, diagram_type: str = None) -> Tuple[bool, str, List[str]]:
    """
    验证并修复 Mermaid 代码的便捷函数
    
    Args:
        code: Mermaid 代码
        diagram_type: 期望的图表类型
        
    Returns:
        (is_valid, fixed_code, warnings)
    """
    validator = MermaidValidator()
    return validator.validate_and_fix(code, diagram_type)


if __name__ == "__main__":
    # 测试代码
    test_code = """
graph
    A[节点A] -[:contains]-> B[节点B]
    B-->C{判断}
    C ==>D((结果))
    
    
    
    E-->F
"""
    
    print("原始代码:")
    print(test_code)
    print("\n" + "="*60 + "\n")
    
    is_valid, fixed, warnings = validate_mermaid(test_code, "graph TD")
    
    print("修复后代码:")
    print(fixed)
    print("\n" + "="*60 + "\n")
    
    print(f"验证结果: {'通过' if is_valid else '失败'}")
    if warnings:
        print("\n警告信息:")
        for w in warnings:
            print(f"  - {w}")

