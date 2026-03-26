from ast import pattern
import re
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

# $env:PUPPETEER_EXECUTABLE_PATH="C:/Users/21598/AppData/Local/Google/Chrome/Application/chrome.exe"

class SimpleMermaidValidator:
    def __init__(self):
        # Mermaid保留字
        self.reserved_words = {'end', 'subgraph', 'class', 'click', 'style', 'classDef'}
        
        # 错误列表
        self.errors = []
        
        # 编译检查配置
        self.enable_compile_check = True
        self.mmdc_timeout_sec = 30
        
    def validate_file(self, file_content):
        """验证单个文件中的所有Mermaid图表"""
        # 每次校验前清空历史错误，避免错误信息累加
        self.errors = []
            
        # 提取所有Mermaid代码块
        mermaid_blocks = self._extract_mermaid_blocks(file_content)
        
        if not mermaid_blocks:
            return {"result": True, "errors": []}
        
        valid = True
        for i, block in enumerate(mermaid_blocks, 1):
            if not self._validate_mermaid_block(block, i):
                valid = False
        result = []
        if self.errors:
            pattern = r'^(.*?)(?=\s*\([A-Za-z]:\\|\s*\(file:///[A-Za-z]:/)'
            match = re.search(pattern, self.errors[0], re.MULTILINE | re.DOTALL)
            if match:
                result = match.group(1).strip()
            else:
                result = self.errors

        return {"result": valid, "errors": result}
    
    def _extract_mermaid_blocks(self, content):
        """提取文档中的所有Mermaid代码块"""
        pattern = r'```mermaid\n(.*?)\n```'
        blocks = re.findall(pattern, content, re.DOTALL)
        return blocks
    
    def _validate_mermaid_block(self, mermaid_code, block_num):
        """验证单个Mermaid代码块"""
        lines = mermaid_code.strip().split('\n')
        valid = True
        
        # # 检查基本结构
        # if not self._check_graph_declaration(lines):
        #     valid = False
            
        # # 检查节点定义
        # if not self._check_node_definitions(lines):
        #     valid = False
            
        # # 检查连接语法
        # if not self._check_connections(lines):
        #     valid = False
            
        # # 检查子图结构
        # if not self._check_subgraph_structure(lines):
        #     valid = False
            
        # # 如果静态检查已经失败，直接返回，不进行编译验证
        # if not valid:
        #     return False
            
        # 编译验证（仅在静态检查通过时才进行）
        if self.enable_compile_check:
            if not self.validate_block_compile(mermaid_code, block_num):
                valid = False
                
        return valid
    
    def _check_graph_declaration(self, lines):
        """检查图表声明"""
        if not lines or not lines[0].strip().startswith('graph '):
            self.errors.append("缺少 'graph TD' 或 'graph LR' 声明")
            return False
        return True
    
    def _check_node_definitions(self, lines):
        """检查节点定义"""
        valid = True
        node_pattern = r'^\s*(\w+)(\[.*?\]|\{.*?\}|\(.*?\))'
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('graph ') or line == 'end' or line.startswith('%%'):
                continue
                
            # 检查是否是节点定义
            match = re.match(node_pattern, line)
            if match:
                node_id = match.group(1)
                node_text = match.group(2)
                
                # 检查节点ID是否为保留字
                if node_id.lower() in self.reserved_words:
                    self.errors.append(f"节点ID '{node_id}' 是保留字")
                    valid = False
                    return valid
                
                # 检查节点文本是否用双引号
                if '[' in node_text and not ('"' in node_text):
                    self.errors.append(f"节点文本应使用双引号包裹")
                    valid = False
                    return valid
        return valid
    
    def _check_connections(self, lines):
        """检查连接语法"""
        valid = True
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # 跳过注释和非连接行
            if not line or line.startswith('%%') or line.startswith('graph ') or line == 'end':
                continue
            
            # 检查是否包含连接符
            has_connection = False
            if '-->' in line:
                has_connection = True
                # 检查错误的 --|"label"| 语法
                if '--|"' in line and not '-->|' in line:
                    self.errors.append(f"错误的连接语法，应使用 -->|\"标签\"| 而不是 --|\"标签\"|")
                    valid = False
                    return valid
                    
                # 检查不完整连接
                if line.endswith('-->'):
                    self.errors.append(f"连接语句不完整，以-->结尾")
                    valid = False
                    return valid
                elif '-->|' in line and not line.count('|') >= 2:
                    self.errors.append(f"连接语句不完整，标签格式错误")
                    valid = False
                    return valid
                
                # 检查空标签
                if '|""|' in line or '||' in line:
                    self.errors.append(f"禁止使用空边标签")
                    valid = False
                    return valid
                    
                # 检查边标签是否用双引号
                if '|' in line and '-->' in line:
                    # 检查错误的 -->| "标签" | 格式（标签外有空格）
                    if re.search(r'-->\|\s+"[^"]*"\s+\|', line):
                        self.errors.append(f"边标签格式错误，标签外不应有空格，应为 -->|\"标签\"|")
                        valid = False
                        return valid
                        
                    label_match = re.search(r'\|([^|]+)\|', line)
                    if label_match:
                        label_content = label_match.group(1).strip()
                        if not (label_content.startswith('"') and label_content.endswith('"')):
                            self.errors.append(f"边标签应使用双引号包裹")
                            valid = False
                            return valid
            
            # 检查其他错误的连接语法
            elif '--|' in line:
                self.errors.append(f"错误的连接语法，应使用 --> 而不是 --|")
                valid = False
                return valid
                        
        return valid
    
    def _check_subgraph_structure(self, lines):
        """检查子图结构"""
        valid = True
        subgraph_stack = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            if line.startswith('subgraph '):
                # 检查子图语法
                # 正确格式: subgraph ID["名称"] 或 subgraph "名称"
                if not (re.match(r'subgraph\s+\w+\[".*?"\]', line) or re.match(r'subgraph\s+".*?"', line)):
                    self.errors.append(f"子图语法错误，应为 'subgraph ID[\"名称\"]' 或 'subgraph \"名称\"'")
                    valid = False
                    return valid
                subgraph_stack.append(line_num)
                
            elif line == 'end':
                if not subgraph_stack:
                    self.errors.append(f"多余的 'end' 语句")
                    valid = False
                    return valid
                else:
                    subgraph_stack.pop()
                    
        # 检查未闭合的子图
        if subgraph_stack:
            self.errors.append(f"子图未正确闭合，缺少 {len(subgraph_stack)} 个 'end' 语句")
            valid = False
            return valid
            
        return valid
        # --------------- 编译校验 ---------------
    @staticmethod
    @staticmethod
    def sanitize_class_diagram(code: str) -> str:
        """清理classDiagram中导致mermaid解析器崩溃的各种语法问题。

        mermaid的ClassMember.parseMember在遇到以下情况时会抛出
        TypeError: Cannot read properties of undefined (reading 'startsWith'):
        1. 类定义内部的空行
        2. 成员行包含分号
        3. 成员行包含 // 注释
        4. 成员行包含修饰符关键字（如 public, private）
        5. 成员行中有多余的花括号
        6. 可变参数 Object... 语法
        7. 构造函数波浪号语法错误 ~ClassName()~
        """
        lines = code.split('\n')
        result = []
        inside_class_body = False
        brace_depth = 0

        for line in lines:
            stripped = line.strip()

            if inside_class_body:
                open_count = stripped.count('{')
                close_count = stripped.count('}')
                brace_depth += open_count - close_count

                if brace_depth <= 0:
                    inside_class_body = False
                    brace_depth = 0
                    result.append(line)
                    continue

                # 跳过类定义内部的空行
                if stripped == '':
                    continue

                # 跳过纯注释行
                if stripped.startswith('//') or stripped.startswith('%%'):
                    continue

                # 清理成员行
                member = stripped
                # 去掉行尾分号
                member = member.rstrip(';')
                # 去掉行内注释
                if '//' in member:
                    member = member[:member.index('//')].rstrip()
                # 去掉行内 %% 注释（但保留 <<interface>> 等标注行）
                if '%%' in member and '<<' not in member:
                    member = member[:member.index('%%')].rstrip()
                # 替换可变参数 Object... → Object[]
                member = re.sub(r'(\w+)\.\.\.', r'\1[]', member)
                # 去掉成员行中多余的花括号（不是开头/结尾的 { }）
                if member and not member.startswith('{') and not member.endswith('}'):
                    member = member.replace('{', '').replace('}', '')
                # 修复构造函数波浪号: ~ClassName()~ → ClassName()
                member = re.sub(r'^~(\w+)\((.*?)\)~$', r'\1(\2)', member)

                if member.strip():
                    # 保持原始缩进
                    indent = line[:len(line) - len(line.lstrip())]
                    result.append(indent + member)
            else:
                # 检测类定义开始（含 namespace 内的 class 定义）
                if re.match(r'^\s*class\s+', stripped) and '{' in stripped:
                    inside_class_body = True
                    brace_depth = stripped.count('{') - stripped.count('}')
                    if brace_depth <= 0:
                        inside_class_body = False
                        brace_depth = 0
                result.append(line)

        return '\n'.join(result)

    # Node.js 校验脚本路径（相对于项目根目录）
    _VALIDATE_SCRIPT = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts", "validate_mermaid.mjs"
    )

    def validate_block_compile(self, code, block_num):
        """使用 Node.js + mermaid.parse() 校验语法（无需 Chrome/Puppeteer）"""
        if not self.enable_compile_check:
            return True

        # 清理类图中导致解析崩溃的语法问题
        code = self.sanitize_class_diagram(code)

        node_cmd = shutil.which("node")
        if not node_cmd:
            self.errors.append("未找到 node 环境")
            return False

        if not os.path.exists(self._VALIDATE_SCRIPT):
            self.errors.append(f"未找到校验脚本: {self._VALIDATE_SCRIPT}")
            return False

        try:
            proc = subprocess.run(
                [node_cmd, self._VALIDATE_SCRIPT, "-"],
                input=code,
                capture_output=True,
                text=True,
                timeout=self.mmdc_timeout_sec,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode == 0 and proc.stdout.strip() == "OK":
                return True
            error_msg = proc.stderr.strip() or proc.stdout.strip() or "未知错误"
            self.errors.append(f"语法校验失败: {error_msg}")
            return False

        except subprocess.TimeoutExpired:
            self.errors.append("mermaid 语法校验超时")
            return False
        except Exception as e:
            error_msg = str(e)
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            self.errors.append(f"校验异常: {error_msg}")
            return False


if __name__ == "__main__":
    validator = SimpleMermaidValidator()
    
    file_content = """

```mermaid
graph TD

subgraph xstrtol_main["字符串到整数转换主流程 (lib/string_to_integer_conversion)"]
    xstrtol_entry["调用 xstrtol/xstrtoul/xstrtoimax/xstrtoumax"]
    check_base["检查基数是否合法 (0 <= base <= 36)"]
    check_sign["判断类型是否无符号且是否为负号"]
    sign_invalid{"无符号类型且输入为负号?"}
    set_errno["设置errno为0"]
    call_strtol["调用strtol族函数进行基本转换"]
    errno_check{"errno != 0 ?"}
    ret_overflow["返回溢出错误"]
    check_no_number{"*p == s ? 是否没有数字"}
    check_valid_suffix{"有有效后缀并且后缀有效?"}
    tmp_set1["设值为1（假定数字为1）"]
    ret_invalid["返回无效输入错误"]
    valid_suffixes_null{"valid_suffixes == NULL ?"}
    ret_ok1["返回 LONGINT_OK（允许任意后缀）"]
    check_suffix_end{"*p 末尾是否为非空字符?"}
    check_valid_suffix2{"后缀是否在 valid_suffixes 中?"}
    ret_invalid_suffix["返回无效后缀错误"]
    check_special_suffix{"valid_suffixes 包含 '0'?"}
    process_special_suffix["处理特殊后缀(B, iB, D)并调整base"]
    suffix_switch["根据后缀选择缩放方式"]
    call_bkm_scale["bkm_scale/bkm_scale_by_power 缩放"]
    overflow_check{"溢出?"}
    ret_overflow2["返回溢出错误"]
    ptr_inc["调整指针，跳过后缀"]
    ret_invalid_suffix2["返回无效后缀错误"]
    set_result["*val = tmp"]
    ret_ok["返回 LONGINT_OK"]
    xstrtol_entry --> check_base
    check_base --> check_sign
    check_sign --> sign_invalid
    sign_invalid -->| "是" | ret_invalid
    sign_invalid -->| "否" | set_errno
    set_errno --> call_strtol
    call_strtol --> errno_check
    errno_check -->| "是" | ret_overflow
    errno_check -->| "否" | check_no_number
    check_no_number -->| "是" | check_valid_suffix
    check_valid_suffix -->| "是"| tmp_set1
    tmp_set1 --> valid_suffixes_null
    check_valid_suffix -->| "否"| ret_invalid
    check_no_number -->| "否" | valid_suffixes_null
    valid_suffixes_null -->| "是"| set_result
    set_result --> ret_ok1
    valid_suffixes_null -->| "否"| check_suffix_end
    check_suffix_end -->| "否"| set_result
    set_result --> ret_ok
    check_suffix_end -->| "是"| check_valid_suffix2
    check_valid_suffix2 -->| "否"| ret_invalid_suffix
    check_valid_suffix2 -->| "是"| check_special_suffix
    check_special_suffix -->| "是"| process_special_suffix
    check_special_suffix -->| "否"| suffix_switch
    process_special_suffix --> suffix_switch
    suffix_switch --> call_bkm_scale
    call_bkm_scale --> overflow_check
    overflow_check -->| "是"| ret_overflow2
    overflow_check -->| "否"| ptr_inc
    ptr_inc --> set_result
end

subgraph xstrtoumax_main["xstrtoumax 封装流程 (lib/xstrtoumax.c)"]
    xstrtoumax_call["调用 xstrtoumax"]
    macro_define["宏定义 __strtol/类型/函数别名"]
    include_xstrtol["包含 xstrtol.c 并使用主流程函数"]
    xstrtoumax_call --> macro_define --> include_xstrtol
    include_xstrtol --> xstrtol_entry
end

subgraph timer_utils_main["高精度时间测量流程 (src/time_utilities)"]
    timer_start["调用 _TimerLap 获取起始时间"]
    timer_stop["调用 _TimerLap 获取结束时间"]
    interval_micro["调用 TimerInterval_MICRO 计算微秒间隔"]
    interval_second["调用 TimerInterval_SECOND 计算秒间隔"]
    micro2sec["调用 Mirco2Sec 进行微秒转秒"]
    micro2milli["调用 Mirco2Milli 进行微秒转毫秒"]
    timer_start --> timer_stop
    timer_stop --> interval_micro
    timer_stop --> interval_second
    interval_micro --> micro2sec
    interval_micro --> micro2milli
end
```

## 3. 核心数据结构解析

### 3.1 字符串到整数转换相关数据结构（lib/string_to_integer_conversion）


"""
    a = validator.validate_file(file_content)
    print(a)
