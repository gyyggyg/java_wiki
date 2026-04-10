import os
import re
import json
import time
import urllib.request
from neo4j import GraphDatabase
from concurrent.futures import ThreadPoolExecutor, as_completed

# 单独运行时加载 .env，与 run_all.py 入口保持一致
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configuration — 兼容 WIKI_NEO4J_* 与 NEO4J_* 两种命名
NEO4J_URI = os.environ.get("NEO4J_URI") or os.environ.get("WIKI_NEO4J_URI", "bolt://localhost:7689")
NEO4J_USER = os.environ.get("NEO4J_USER") or os.environ.get("WIKI_NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD") or os.environ.get("WIKI_NEO4J_PASSWORD", "")

# LLM Configuration — 兼容 OPENAI_API_KEY / BASE_URL 两种命名
ENABLE_LLM = True
LLM_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL") or os.environ.get("BASE_URL", "https://api.zhec.moe/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-5-mini")

# Performance Configuration
MAX_WORKERS_LLM = 3  # Reduced to avoid connection reset
MAX_WORKERS_DB = 3   # Control concurrency for Neo4j queries
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "120"))  # 单次 LLM 调用超时（秒），默认 120

# File path root prefix (neo4j中的路径不包括根目录，此处添加根目录前缀)
ROOT_PREFIX = os.environ.get("ROOT_PREFIX", "mall")

class LLMClient:
    """Handles interaction with Real LLM for grouping and content generation."""
    
    def __init__(self, enable_real_calls=True):
        self.enable_real_calls = enable_real_calls
        self.enabled = enable_real_calls # Alias for convenience
        self.api_key = LLM_API_KEY
        self.base_url = LLM_BASE_URL.rstrip('/')
        
        if self.enable_real_calls and not self.api_key:
            print("⚠️ WARNING: ENABLE_LLM is True but LLM_API_KEY is not set.")

    def _call_llm(self, system_prompt, user_prompt, temperature=0.2):
        """Generic OpenAI-compatible API caller using standard library"""
        if not self.enable_real_calls or not self.api_key:
            return ""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }

        retry_count = 3
        for attempt in range(retry_count):
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/chat/completions",
                    data=json.dumps(payload).encode('utf-8'),
                    headers=headers,
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    msg = result['choices'][0]['message']['content']
                    # Clean up potential markdown fences
                    msg = re.sub(r'^```\w*\n', '', msg)
                    msg = re.sub(r'\n```$', '', msg)
                    return msg.strip()
            except Exception as e:
                print(f"⚠️ [LLM Attempt {attempt+1} Failed] {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 * (attempt + 1)) # Exponential backoff
                else:
                    print(f"❌ [LLM Error] Final failure after {retry_count} attempts.")
                    return ""

    def _json_from_text(self, text):
        if not text:
            return ""
        text = text.strip()
        text = re.sub(r'^```(?:json)?\\n', '', text)
        text = re.sub(r'\\n```$', '', text)
        start_obj = text.find('{')
        start_arr = text.find('[')
        if start_obj == -1 and start_arr == -1:
            return ""
        if start_arr == -1 or (start_obj != -1 and start_obj < start_arr):
            start = start_obj
            end = text.rfind('}')
        else:
            start = start_arr
            end = text.rfind(']')
        if start == -1 or end == -1 or end <= start:
            return ""
        snippet = text[start:end + 1]
        try:
            obj = json.loads(snippet)
        except Exception:
            return ""
        return json.dumps(obj, ensure_ascii=False, indent=2)

    def group_controllers(self, controllers_metadata):
        """
        Step 1: Ask LLM to group controllers into modules.
        Input: List of dicts {name, description, url}
        Output: Dict { "ModuleName": ["Controller1", "Controller2"] }
        """
        if not self.enable_real_calls:
            return {"AllControllers": [c['name'] for c in controllers_metadata]}

        print("🤖 Asking LLM to group controllers...")
        
        # Prepare context
        simplified_list = []
        for c in controllers_metadata:
            desc = c.get('llm_description') or c.get('description', '')
            simplified_list.append({
                "class": c['name'],
                "desc": desc[:100] # Truncate to save tokens
            })
            
        system = """You are a huge software architecture expert. 
Your task is to group the provided list of Spring Boot Controllers into logical business modules (e.g., 'ProductManagement', 'OrderManagement', 'UserManagement').
Rules:
1. Return strictly JSON format: {"ModuleName": ["ControllerName1", "ControllerName2"]}.
2. Use Chinese for Module Names (suffix with 'API', e.g., '商品管理API').
3. No Markdown code fence. Just raw JSON.
"""
        
        user = f"Here is the list of controllers:\n{json.dumps(simplified_list, ensure_ascii=False, indent=2)}"
        
        response = self._call_llm(system, user, temperature=0.1)
        
        # Clean response if it contains markdown code blocks
        response = re.sub(r'```json', '', response)
        response = re.sub(r'```', '', response).strip()
        
        try:
            groups = json.loads(response)
            # Map back to full controller objects
            controller_map = {c['name']: c for c in controllers_metadata}
            
            final_groups = {}
            for module, c_names in groups.items():
                final_groups[module] = []
                for name in c_names:
                    if name in controller_map:
                        final_groups[module].append(controller_map[name])
            
            print(f"✅ LLM Grouping done: {list(final_groups.keys())}")
            return final_groups
        except Exception as e:
            print(f"❌ Failed to parse LLM grouping response: {e}\nResponse: {response}")
            # Fallback: put everything in one group
            return {"UncategorizedAPI": controllers_metadata}

    def generate_module_intro(self, module_name, context_data):
        """
        Step 2: Generate introduction and architecture overview.
        """
        print(f"🤖 Generating intro for {module_name}...")
        
        system = """You are a technical writer for an enterprise API documentation.
Write a professional 'Introduction' and 'Architecture Overview' for the given module.
1. Return in Markdown format.
2. Use professional Chinese.
3. Be concise but comprehensive.
4. Input context includes the descriptions (SE_What) and design intents (SE_Why) of the controllers in this module.
5. Do NOT output the Module Name as a Title (#). Start with Level 2 headers (## 简介, ## 架构概述).
"""
        user = f"Module Name: {module_name}\n\nComponents Context:\n{json.dumps(context_data, ensure_ascii=False, indent=2)}"
        
        return self._call_llm(system, user, temperature=0.3)

    def generate_arch_analysis(self, module_name, context_data):
        """
        Step 3: Generate performance and troubleshooting sections.
        """
        print(f"🤖 Generating architecture analysis for {module_name}...")
        
        system = """You are a software architect.
Analyze the provided module components and write a section in Markdown (Chinese):
1. ## 性能与故障排查: Potential bottlenecks (e.g. database hits, batch ops) and optimization advice; Common issues.
"""
        user = f"Module Name: {module_name}\n\nComponents:\n{json.dumps(context_data, ensure_ascii=False, indent=2)}"
        
        return self._call_llm(system, user, temperature=0.4)

    def generate_method_examples(self, method_name, params, return_type, method_desc="", design_intent="", http_method="GET", prebuilt_request_example="", response_only=False):
        """
        Ask LLM to generate JSON request/response examples and assemble Markdown blocks.
        """
        if not self.enabled:
            return ""
        user = f"Method: {method_name}\\nParameters: {params}\\nReturn Type: {return_type}\\nMethod Context: {method_desc} - {design_intent}"

        request_block = ""
        response_block = ""

        if prebuilt_request_example:
            request_block = prebuilt_request_example
        elif not response_only and http_method != "GET":
            req_system = f"""You are an API technical writer. Generate a JSON request body only for the provided Java API method.
Requirements:
1. Output valid JSON only. No markdown, no code fences, no extra text.
2. HTTP Method is {http_method}. If the method should not have a body, return an empty JSON object {{}}.
3. Use realistic dummy data matching the Method Context.
4. Do not use escaped newline sequences like \\n in the output.
"""
            req_text = self._call_llm(req_system, user, temperature=0.2)
            req_json = self._json_from_text(req_text)
            if req_json:
                request_block = f"### 请求示例\n```json\n{req_json}\n```"

        resp_system = f"""You are an API technical writer. Generate a JSON response body only for the provided Java API method.
Requirements:
1. Output valid JSON only. No markdown, no code fences, no extra text.
2. Return Type is {return_type}.
   - If 'void': Wrap the response in a standard CommonResult structure (code: 200, message: "OK", data: null).
   - If 'CommonResult': Generate the standard structure.
   - If the return type is String or CommonResult<String>: data MUST be a plain string value (e.g. "success"), never a JSON stringified object.
3. Use realistic dummy data matching the Method Context (e.g. if context says Alipay, do not use WeChat).
4. Do not use escaped newline sequences like \\n in the output.
"""
        resp_text = self._call_llm(resp_system, user, temperature=0.2)
        resp_json = self._json_from_text(resp_text)
        if resp_json:
            response_block = f"### 响应示例\n```json\n{resp_json}\n```"

        return "\n".join([b for b in [request_block, response_block] if b]).strip()


class StrictApiDocGenerator:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.llm = LLMClient(ENABLE_LLM)

    def close(self):
        self.driver.close()

    def generate_all(self, output_dir="output_wiki_v8"):
        """Refactored Main Entry: Group -> Render -> Write"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 1. Gather Metadata
        all_controllers = self._get_all_controllers_metadata()
        print(f"Collected metadata for {len(all_controllers)} controllers.")

        # 2. AI Grouping
        grouped_modules = self._group_controllers_with_module(all_controllers)

        # 3. Render Each Module Parallelly
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_DB) as executor:
            future_to_module = {}
            for module_name, controllers in grouped_modules.items():
                if not controllers: continue
                print(f"Scheduling module rendering: {module_name}...")
                future_to_module[executor.submit(self._render_and_save_module, module_name, controllers, output_dir)] = module_name

            for future in as_completed(future_to_module):
                m_name = future_to_module[future]
                try:
                    future.result()
                    print(f"✅ Module completed: {m_name}")
                except Exception as e:
                    print(f"❌ Error rendering module {m_name}: {e}")

    def _render_and_save_module(self, module_name, controllers, output_dir):
        """Helper to render a full module and write to disk as .meta.json"""
        print(f"Rendering module: {module_name} ({len(controllers)} controllers)...")

        # 3.1 Fetch full data for these controllers in parallel
        full_controller_data = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS_DB) as executor:
            future_to_c = {executor.submit(self._process_controller_data, c_meta): i for i, c_meta in enumerate(controllers)}

            # Temporary list to maintain order
            results = [None] * len(controllers)
            for future in as_completed(future_to_c):
                idx = future_to_c[future]
                results[idx] = future.result()
            full_controller_data = results

        # 3.2 Render structured wiki data
        wiki_data = self._render_module_doc(module_name, full_controller_data)

        # 3.3 Write .meta.json file
        safe_name = module_name.replace(" ", "_").replace("/", "-")
        filepath = os.path.join(output_dir, f"{safe_name}.meta.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(wiki_data, f, ensure_ascii=False, indent=4)
        print(f"Saved: {filepath}")

    def _get_all_controllers_metadata(self):
        """Fetch lightweight metadata for LLM grouping, including class_id and file path from File node"""
        query = """
        MATCH (c:Class)
        WHERE (c.modifiers CONTAINS '@RestController'
               OR (c.modifiers CONTAINS '@Controller' AND NOT c.modifiers CONTAINS '@ControllerAdvice'))
        OPTIONAL MATCH (f:File)-[:DECLARES]->(c)
        RETURN c.name as name,
               c.modifiers as modifiers,
               c.SE_What as description,
               c.SE_Why as design_intent,
               c.fully_qualified_name as fully_qualified_name,
               id(c) as class_id,
               f.name as file_name
        ORDER BY c.name
        """
        with self.driver.session() as session:
            return [record.data() for record in session.run(query)]

    def _process_controller_data(self, meta):
        """Fetch strict technical details for a single controller (Methods, Params, Trace)"""
        name = meta['name']
        base_url = self._extract_url_regex(meta['modifiers'])
        if not base_url: base_url = "/" # Default to root if missing class-level mapping
        is_rest = '@RestController' in meta['modifiers']
        source_path = meta.get("source_path") or self._find_source_path(meta.get('fully_qualified_name'), name)
        module_root = meta.get("module_root") or self._extract_module_root(source_path)

        # 1. Methods & Traces
        methods = self._get_methods_strict_with_source(name)
        
        # 2. Dependencies
        dependencies = self._get_dependencies(name)

        # 3. DTOs
        all_inner_types = set()
        param_types = set()
        for m in methods:
            full_sig, inner_type = self._parse_generics_from_source(m['source_code'])
            if full_sig == "Unknown": full_sig = "Object"
            m['display_return_type'] = full_sig
            if inner_type and inner_type not in ["void", "String", "Integer", "Long", "Boolean", "Object", "Unknown"]:
                all_inner_types.add(inner_type)
            params_list = self._parse_method_params(m.get('params_str', '()'))
            for p in params_list:
                p_type = p.get("type")
                if p_type and p_type not in ["void", "String", "Integer", "Long", "Boolean", "Object", "Unknown"]:
                    param_types.add(p_type)
        dtos = self._collect_dtos_real(list(all_inner_types | param_types))

        return {
            "meta": meta,
            "base_url": base_url,
            "is_rest_controller": is_rest,
            "source_path": source_path,
            "module_root": module_root,
            "dependencies": dependencies,
            "methods": methods,
            "dtos": dtos
        }

    def _get_file_path_with_root(self, file_name):
        """给 Neo4j 中的文件路径添加根目录前缀"""
        if not file_name:
            return ""
        if ROOT_PREFIX and not file_name.startswith(ROOT_PREFIX + "/"):
            return f"{ROOT_PREFIX}/{file_name}"
        return file_name

    def _render_module_doc(self, module_name, controllers_data):
        """Returns structured wiki data: {"wiki": [...], "source_id_list": [...]}"""

        wiki_entries = []
        source_id_map = {}  # source_id_str -> {"source_id": str, "name": str, "lines": []}

        def register_source(node_id, file_name, lines=None):
            """Register a source file entry, returns source_id string"""
            if node_id is None:
                return None
            sid = str(node_id)
            full_path = self._get_file_path_with_root(file_name)
            if sid not in source_id_map:
                source_id_map[sid] = {"source_id": sid, "name": full_path, "lines": lines or []}
            elif lines:
                for l in lines:
                    if l not in source_id_map[sid]["lines"]:
                        source_id_map[sid]["lines"].append(l)
            return sid

        # ================================================================
        # 1. LLM Context Preparation
        # ================================================================
        context = []
        for c in controllers_data:
            context.append({
                "name": c['meta']['name'],
                "desc": c['meta'].get('description'),
                "why": c['meta'].get('design_intent')
            })

        # 2. Invoke LLM for High-Level Content in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            f_intro = executor.submit(self.llm.generate_module_intro, module_name, context)
            f_arch = executor.submit(self.llm.generate_arch_analysis, module_name, context)
            intro_text = f_intro.result()
            arch_text = f_arch.result()

        # ================================================================
        # Section 1: Module overview + intro + sys info
        # ================================================================
        section_num = 1
        overview_parts = []
        overview_parts.append(f"## {section_num}. 模块功能概述\n")

        # Sys info (integration guide)
        overview_parts.append(self._render_sys_info(controllers_data))

        # LLM intro
        if intro_text:
            overview_parts.append(intro_text.strip())
        else:
            overview_parts.append("*(模块简介生成失败)*")

        # Collect all class IDs for this module
        overview_neo4j_id = {}
        overview_source_ids = []
        for idx, c in enumerate(controllers_data):
            class_id = c['meta'].get('class_id')
            file_name = c['meta'].get('file_name')
            if class_id is not None:
                overview_neo4j_id[f"{section_num}.{idx+1}"] = class_id
                sid = register_source(class_id, file_name)
                if sid and sid not in overview_source_ids:
                    overview_source_ids.append(sid)

        wiki_entries.append({
            "markdown": "\n".join(overview_parts),
            "neo4j_id": overview_neo4j_id,
            "source_id": overview_source_ids
        })

        # ================================================================
        # Section 2: 核心组件介绍 (per controller details)
        # ================================================================
        section_num = 2
        component_parts = []
        component_neo4j_id = {}
        component_source_ids = []

        component_parts.append(f"## {section_num}. 核心组件介绍\n")

        for c_idx, c_data in enumerate(controllers_data, 1):
            c_name = c_data['meta']['name']
            class_id = c_data['meta'].get('class_id')
            file_name = c_data['meta'].get('file_name')
            full_path = self._get_file_path_with_root(file_name)
            desc = c_data['meta'].get('description', '暂无描述')
            why = c_data['meta'].get('design_intent', '')

            sub_label = f"{section_num}.{c_idx}"
            component_parts.append(f"### {sub_label} {c_name}(Class)\n")
            if full_path:
                component_parts.append(f"{c_name}属于文件{full_path}\n")

            component_parts.append(f"- **主要职责**\n  - {desc}\n")

            if c_data.get('meta', {}).get('design_intent'):
                component_parts.append(f"- **设计意图**\n  - {why}\n")

            component_parts.append(f"- **基础路径**: `{c_data['base_url']}`\n")

            # Register neo4j_id and source
            if class_id is not None:
                component_neo4j_id[sub_label] = [class_id]
                sid = register_source(class_id, file_name)
                if sid and sid not in component_source_ids:
                    component_source_ids.append(sid)

        wiki_entries.append({
            "markdown": "\n".join(component_parts),
            "neo4j_id": component_neo4j_id,
            "source_id": component_source_ids
        })

        # ================================================================
        # Section 3: 核心组件架构图 (mermaid class diagram)
        # ================================================================
        section_num = 3
        diagram_content = self._render_module_class_diagram(controllers_data)
        diagram_md = f"## {section_num}. 核心组件架构\n{diagram_content}"

        # Build mapping: class name -> class_id
        diagram_mapping = {}
        for c_data in controllers_data:
            c_name = c_data['meta']['name']
            class_id = c_data['meta'].get('class_id')
            if class_id is not None:
                diagram_mapping[c_name] = str(class_id)

        wiki_entries.append({
            "mermaid": diagram_md,
            "mapping": diagram_mapping
        })

        # ================================================================
        # Section 4: 详细组件分析 (per controller methods)
        # ================================================================
        section_num = 4
        # Section header
        wiki_entries.append({
            "markdown": f"## {section_num}. 详细组件分析\n",
            "neo4j_id": {},
            "source_id": []
        })

        for c_idx, c_data in enumerate(controllers_data, 1):
            c_name = c_data['meta']['name']
            class_id = c_data['meta'].get('class_id')
            file_name = c_data['meta'].get('file_name')

            if not c_data['methods']:
                wiki_entries.append({
                    "markdown": f"### {section_num}.{c_idx} {c_name}\n\n*暂无公开接口*\n",
                    "neo4j_id": {f"{section_num}.{c_idx}": [class_id] if class_id else []},
                    "source_id": [str(class_id)] if class_id else []
                })
                continue

            # Parallelize method rendering
            method_results = [None] * len(c_data['methods'])
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_LLM) as executor:
                future_to_m = {}
                for i, m in enumerate(c_data['methods'], 1):
                    future_to_m[executor.submit(
                        self._render_method,
                        m,
                        i,
                        c_data['base_url'],
                        c_data['is_rest_controller'],
                        c_name,
                        c_data.get('dtos', {})
                    )] = i - 1
                for future in as_completed(future_to_m):
                    idx = future_to_m[future]
                    method_results[idx] = future.result()

            # Assemble controller methods as one markdown entry
            method_md_parts = [f"### {section_num}.{c_idx} {c_name} 接口分析\n"]
            method_neo4j_id = {}
            method_source_ids = []

            if class_id is not None:
                sid = register_source(class_id, file_name)
                if sid and sid not in method_source_ids:
                    method_source_ids.append(sid)

            for m_idx, mr in enumerate(method_results):
                if mr is None:
                    continue
                method_md_parts.append(mr["markdown"])

                # Track method neo4j id
                m_id = mr.get("method_id")
                m_class_id = mr.get("class_id")
                sub_label = f"{section_num}.{c_idx}.{m_idx+1}"
                ids = []
                if m_class_id is not None:
                    ids.append(m_class_id)
                if m_id is not None:
                    ids.append(m_id)
                if ids:
                    method_neo4j_id[sub_label] = ids

                # Register source
                m_file = mr.get("file_name")
                if m_id is not None:
                    register_source(m_id, m_file)
                    if str(m_id) not in method_source_ids:
                        method_source_ids.append(str(m_id))

            wiki_entries.append({
                "markdown": "\n".join(method_md_parts),
                "neo4j_id": method_neo4j_id,
                "source_id": method_source_ids
            })

            # Add mermaid entries for methods that have sequence diagrams
            for m_idx, mr in enumerate(method_results):
                if mr is None or mr.get("mermaid") is None:
                    continue
                m_id = mr.get("method_id")
                mapping = {}
                if m_id is not None:
                    mapping[f"{c_name}.{c_data['methods'][m_idx]['name']}"] = str(m_id)
                wiki_entries.append({
                    "mermaid": mr["mermaid"],
                    "mapping": mapping
                })

            # DTOs as mermaid entry
            if c_data['dtos']:
                dto_diagram = self._render_dto_diagram(c_data['dtos'])
                if dto_diagram:
                    dto_md = f"#### {c_name} 数据模型\n{dto_diagram}"
                    wiki_entries.append({
                        "mermaid": dto_md,
                        "mapping": {}
                    })

        # ================================================================
        # Section 5: 性能与故障排查 (LLM arch analysis)
        # ================================================================
        if arch_text:
            section_num = 5
            wiki_entries.append({
                "markdown": arch_text.strip(),
                "neo4j_id": {},
                "source_id": []
            })

        # ================================================================
        # Section 6: 结论
        # ================================================================
        wiki_entries.append({
            "markdown": f"## 结论\n\n本项目中的 {module_name} 模块提供了完整的业务能力支撑，结构清晰，扩展性强。",
            "neo4j_id": {},
            "source_id": []
        })

        return {
            "wiki": wiki_entries,
            "source_id_list": list(source_id_map.values())
        }

    def _render_sys_info(self, controllers_data):
        """
        Renders the standard Integration Guide section (Auth, CommonResult).
        """
        ignore_urls = self._extract_module_ignore_urls(controllers_data)
        auth_lines = [
            "## 基础调用指南",
            "",
            "### 1. 认证授权 (Authentication)",
            "多数接口通过 **JWT** 进行安全认证。请在 HTTP Header 中添加：",
            "```http",
            "Authorization: Bearer <your_token>",
            "```"
        ]
        if ignore_urls:
            auth_lines.append("")
            auth_lines.append("以下路径检测为免认证或白名单（可能按模块生效）：")
            for url in ignore_urls:
                auth_lines.append(f"- `{url}`")
        else:
            auth_lines.append("")
            auth_lines.append("未检测到白名单配置，默认视为全部接口需认证。")

        auth_lines.append("""

### 2. 标准响应结构 (CommonResult)
统一使用 `CommonResult<T>` 泛型类返回数据：
```json
{
  "code": 200,      // 200: 成功, 401: 未登录, 403: 无权限, 500: 失败
  "message": "操作成功",
  "data": { ... }   // 具体业务数据
}
```
""")
        return "\n".join(auth_lines)

    def _extract_javadoc_params(self, source_code):
        """
        Extracts @param descriptions from source code.
        Returns: dict { param_name: description }
        """
        if not source_code: return {}
        javadoc_map = {}
        # Simple regex to find blocks like: @param paramName description text
        # Multiline matching might be needed but simple single line is good start
        pattern = r'@param\s+(\w+)\s+(.+)'
        matches = re.findall(pattern, source_code)
        for name, desc in matches:
            javadoc_map[name] = desc.strip()
        return javadoc_map

    def _render_module_class_diagram(self, controllers_data):
        """Generate a high-level class diagram for the whole module"""
        lines = ["```mermaid", "classDiagram"]
        
        seen_classes = set()
        relationships = set()

        for c in controllers_data:
            c_name = c['meta']['name']
            if c_name not in seen_classes:
                lines.append(f"class {c_name} {{")
                lines.append(f"    +BaseUrl: {c['base_url']}")
                lines.append("}")
                seen_classes.add(c_name)
            
            for dep in c['dependencies']:
                t_name = dep['type_name']
                if t_name not in seen_classes:
                    stereotype = "<<Interface>>" if dep['is_interface'] else ""
                    lines.append(f"class {t_name} {{")
                    if stereotype: lines.append(f"    {stereotype}")
                    lines.append("}")
                    seen_classes.add(t_name)
                
                rel = f"{c_name} ..> {t_name}"
                if rel not in relationships:
                    lines.append(rel)
                    relationships.add(rel)
        
        lines.append("```\n")
        return "\n".join(lines)

    # --- Existing strict logic (unchanged) ---

    def _get_methods_strict_with_source(self, controller_name):
        query = """
        MATCH (c:Class {name: $name})-[:DECLARES]->(m:Method)
        WHERE m.modifiers CONTAINS 'Mapping'
        OPTIONAL MATCH (f:File)-[:DECLARES]->(c)
        RETURN m.name as name,
               m.modifiers as modifiers,
               m.SE_What as what,
               m.SE_Why as why,
               m.SE_How as how,
               m.parameters as params_str,
               m.source_code as source_code,
               elementId(m) as method_node_id,
               id(m) as legacy_id,
               id(c) as class_id,
               f.name as file_name
        ORDER BY m.name
        """
        with self.driver.session() as session:
            methods = []
            for record in session.run(query, name=controller_name):
                method_data = record.data()
                methods.append(method_data)

            # Process traces strictly after gathering basic info
            for m in methods:
                 m['trace'] = self._get_method_trace(
                    m['legacy_id'],
                    m['params_str'],
                    parent_source_code=m['source_code']
                )
            return methods

    def _get_dependencies(self, controller_name):
        query = """
        MATCH (c:Class {name: $name})-[:DECLARES]->(f:Field)
        WHERE NOT f.type STARTS WITH 'java.'
          AND NOT f.type STARTS WITH 'javax.'
          AND NOT f.type STARTS WITH 'org.slf4j.'
          AND NOT f.type STARTS WITH 'org.apache.'
          AND NOT f.name = 'log'
        OPTIONAL MATCH (f)-[:HAS_TYPE]->(t)
        RETURN f.name as field_name, 
               f.type as type_attr, 
               labels(t) as labels
        """
        deps = []
        with self.driver.session() as session:
            results = session.run(query, name=controller_name)
            for r in results:
                raw_type = r['type_attr']
                short_type = raw_type.split('.')[-1] if raw_type else "Unknown"
                if short_type in {"String", "Long", "Integer", "Boolean", "Object", "List", "Map"}:
                    continue
                is_interface = False
                if r['labels'] and 'Interface' in r['labels']:
                    is_interface = True
                deps.append({
                    "field_name": r['field_name'],
                    "type_name": short_type,
                    "is_interface": is_interface
                })
        return deps

    def _get_method_trace(self, method_node_id, params_str, parent_source_code=None, depth=2):
        if depth < 0: return []
        
        # NOTE: Still using id() for compatibility with existing DB state visualization
        # To fix deprecation, we should migrate to elementId, but 'method_node_id' here represents native ID.
        query = """
        MATCH (m:Method) WHERE id(m) = $id
        MATCH (m)-[:CALLS]->(t:Method)
        OPTIONAL MATCH (t)<-[:DECLARES]-(i:Interface)<-[:IMPLEMENTS]-(c:Class)-[:DECLARES]->(impl:Method)
        WHERE t.name = impl.name 
          AND (t.parameters = impl.parameters OR impl.parameters IS NULL)
        WITH coalesce(impl, t) as real_target
        MATCH (owner)-[:DECLARES]->(real_target)
        RETURN real_target.name as method, 
               owner.name as owner, 
               labels(owner)[0] as type, 
               id(real_target) as next_id,
               real_target.parameters as next_params,
               real_target.source_code as next_source
        LIMIT 20
        """
        steps = []
        with self.driver.session() as session:
            records = session.run(query, id=method_node_id)
            for r in records:
                step = {
                    "method": r["method"],
                    "owner": r["owner"],
                    "type": r["type"],
                    "next_id": r["next_id"],
                    "next_source": r["next_source"],
                    "next_params": r["next_params"],
                    "is_synthetic": False
                }
                steps.append(step)

        if parent_source_code:
            if re.search(r'PageHelper\s*\.\s*startPage', parent_source_code):
                steps.append({
                    "method": "startPage",
                    "owner": "com.github.pagehelper.PageHelper",
                    "type": "Class",
                    "is_synthetic": True
                })

        if parent_source_code and steps:
            def find_index(step):
                m_name = step['method']
                idx = parent_source_code.find(f".{m_name}(")
                if idx == -1: idx = parent_source_code.find(f"{m_name}(")
                return idx if idx != -1 else 999999
            steps.sort(key=find_index)

        final_trace = []
        for step in steps:
            current_node = {
                "method": step["method"],
                "owner": step["owner"],
                "type": step["type"]
            }
            if not step['is_synthetic'] and step['type'] == 'Class' and depth > 0:
                 current_node["sub_trace"] = self._get_method_trace(
                     step["next_id"], 
                     step["next_params"], 
                     parent_source_code=step["next_source"],
                     depth=depth - 1
                 )
            final_trace.append(current_node)
        return final_trace

    def _collect_dtos_real(self, type_names):
        if not type_names: return {}
        dto_map = {}
        visited = set()
        with self.driver.session() as session:
            def collect(dtype):
                if dtype in visited:
                    return
                visited.add(dtype)
                query = """
                MATCH (c:Class {name: $name})
                OPTIONAL MATCH (c)-[:DECLARES]->(f:Field)
                RETURN c.source_code as source_code, collect({field: f.name, type: f.type}) as fields
                """
                record = session.run(query, name=dtype).single()
                if not record:
                    return
                fields = [f for f in record["fields"] if f.get("field")]
                source_code = record["source_code"] or ""
                extend_match = re.search(r'extends\s+(\w+)', source_code)
                if extend_match:
                    base_name = extend_match.group(1)
                    collect(base_name)
                    base_fields = dto_map.get(base_name, [])
                    merged = base_fields + [f for f in fields if f not in base_fields]
                    dto_map[dtype] = merged
                elif fields:
                    dto_map[dtype] = fields
            for dtype in type_names:
                collect(dtype)
        return dto_map

    def _build_json_from_dto(self, dto_name, dto_map):
        if not dto_name or dto_name not in dto_map:
            return None
        result = {}
        for f in dto_map[dto_name]:
            ftype = (f.get("type") or "String").split('.')[-1]
            if ftype.startswith("List") or ftype.startswith("Set"):
                result[f["field"]] = []
            else:
                result[f["field"]] = self._dummy_value_for_type(ftype)
        return result

    def _find_source_path(self, fqcn, class_name):
        if fqcn:
            rel_path = fqcn.replace(".", os.sep) + ".java"
            for root, _, files in os.walk("."):
                if not files:
                    continue
                for f in files:
                    if f == os.path.basename(rel_path):
                        candidate = os.path.join(root, f)
                        if candidate.endswith(rel_path):
                            return os.path.normpath(candidate)
        if class_name:
            target = f"{class_name}.java"
            for root, _, files in os.walk("."):
                if target in files:
                    return os.path.normpath(os.path.join(root, target))
        return ""

    def _extract_module_root(self, source_path):
        if not source_path:
            return ""
        parts = os.path.normpath(source_path).split(os.sep)
        if "src" in parts:
            idx = parts.index("src")
            if idx > 0:
                return os.sep.join(parts[:idx])
        return ""

    def _group_controllers_with_module(self, controllers_metadata):
        for c in controllers_metadata:
            source_path = self._find_source_path(c.get("fully_qualified_name"), c.get("name"))
            module_root = self._extract_module_root(source_path)
            c["source_path"] = source_path
            c["module_root"] = module_root
            c["module_name"] = os.path.basename(module_root) if module_root else ""
            if c.get("module_name"):
                desc = c.get("description") or ""
                c["llm_description"] = f"{desc} [Module: {c['module_name']}]".strip()
        if self.llm.enabled:
            return self.llm.group_controllers(controllers_metadata)
        module_groups = {}
        for c in controllers_metadata:
            module_name = c.get("module_name") or "Uncategorized"
            module_groups.setdefault(module_name, []).append(c)
        return {f"{k} API": v for k, v in module_groups.items()}

    def _extract_module_ignore_urls(self, controllers_data):
        urls = []
        module_roots = {c.get("module_root") for c in controllers_data if c.get("module_root")}
        for root in module_roots:
            for config_path in self._find_application_ymls(root):
                urls.extend(self._parse_secure_ignored_urls(config_path))
        seen = set()
        deduped = []
        for u in urls:
            if u not in seen:
                deduped.append(u)
                seen.add(u)
        return deduped

    def _find_application_ymls(self, module_root):
        candidates = []
        resources_dir = os.path.join(module_root, "src", "main", "resources")
        for base in [resources_dir, os.path.join(resources_dir, "config")]:
            if os.path.isdir(base):
                for f in os.listdir(base):
                    if f.startswith("application") and (f.endswith(".yml") or f.endswith(".yaml")):
                        candidates.append(os.path.join(base, f))
        return candidates

    def _parse_secure_ignored_urls(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return []
        urls = []
        in_secure = False
        in_ignored = False
        in_urls = False
        secure_indent = None
        ignored_indent = None
        urls_indent = None
        for line in lines:
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            if re.match(r'^\s*secure:\s*$', line):
                in_secure = True
                secure_indent = indent
                continue
            if in_secure and indent <= secure_indent and not re.match(r'^\s*secure:\s*$', line):
                in_secure = False
                in_ignored = False
                in_urls = False
            if in_secure and re.match(r'^\s*ignored:\s*$', line):
                in_ignored = True
                ignored_indent = indent
                continue
            if in_ignored and indent <= ignored_indent and not re.match(r'^\s*ignored:\s*$', line):
                in_ignored = False
                in_urls = False
            if in_ignored and re.match(r'^\s*urls:\s*$', line):
                in_urls = True
                urls_indent = indent
                continue
            if in_urls and indent <= urls_indent and not re.match(r'^\s*urls:\s*$', line):
                in_urls = False
            if in_urls:
                m = re.match(r'^\s*-\s*(.+)$', line)
                if m:
                    urls.append(m.group(1).strip())
        return urls

    def _extract_url_regex(self, text):
        if not text: return ""
        pattern = r'(?:Mapping|GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\s*\(\s*(?:(?:value|path)\s*=\s*)?"([^"]+)"'
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        return ""

    def _extract_http_method_regex(self, modifiers):
        if '@PostMapping' in modifiers: return "POST"
        if '@GetMapping' in modifiers: return "GET"
        if '@PutMapping' in modifiers: return "PUT"
        if '@DeleteMapping' in modifiers: return "DELETE"
        if '@PatchMapping' in modifiers: return "PATCH"
        match = re.search(r'RequestMethod\.([A-Z]+)', modifiers)
        if match: return match.group(1)
        return "ALL/GET"

    def _parse_generics_from_source(self, source_code):
        if not source_code: return "Unknown", None
        match = re.search(r'public\s+(?:static\s+)?([<>\w\s\.,]+)\s+\w+\(', source_code)
        if not match: return "Unknown", None
        raw_type = match.group(1).strip()
        full_sig = raw_type 
        current = raw_type
        while True:
            m_gen = re.search(r'^\w+(?:[\.\w]+)?\s*<\s*(.+)\s*>$', current)
            if m_gen: current = m_gen.group(1)
            else: break
        inner_type = current
        if "." in inner_type: inner_type = inner_type.split('.')[-1]
        return raw_type, inner_type

    def _parse_method_params(self, params_str, javadoc_map=None):

        if not params_str or params_str == "()": return []
        content = params_str.strip()[1:-1]
        if not content: return []
        args = []
        depth = 0
        current_arg = []
        for char in content:
            if char == '(': depth += 1
            if char == ')': depth -= 1
            if char == ',' and depth == 0:
                args.append("".join(current_arg).strip())
                current_arg = []
            else:
                current_arg.append(char)
        if current_arg: args.append("".join(current_arg).strip())
        parsed_args = []
        for arg in args:
            item = {
                "name": "unknown",
                "type": "unknown",
                "required": "false", 
                "has_annotation": False,
                "description": "",
                "in": "unknown"
            }
            if "defaultValue" in arg:
                item["default"] = re.search(r'defaultValue\s*=\s*"([^"]+)"', arg).group(1)
            if "@RequestParam" in arg:
                item["has_annotation"] = True
                item["in"] = "query"
                if "required = false" in arg or "required=false" in arg:
                    item["required"] = "false"
                elif "defaultValue" in arg:
                    item["required"] = "false"
                else:
                    item["required"] = "true" 
            if "@PathVariable" in arg:
                item["has_annotation"] = True
                item["required"] = "true" 
                item["in"] = "path"
            if "@RequestBody" in arg:
                item["has_annotation"] = True
                item["required"] = "true"
                item["in"] = "body"
            clean_arg = re.sub(r'@\w+(?:\([^)]*\))?', '', arg).strip()
            parts = clean_arg.split()
            if len(parts) >= 2:
                item["type"] = parts[-2]
                item["name"] = parts[-1]
            elif len(parts) == 1:
                item["name"] = parts[0]
            if "." in item["type"]:
                item["type"] = item["type"].split('.')[-1]
            ignored_types = {"HttpServletRequest", "HttpServletResponse", "HttpSession", "Model", "ModelMap", "BindingResult", "Principal"}
            if item["type"] in ignored_types:
                continue
            
            # Enrich with Javadoc
            if javadoc_map and item["name"] in javadoc_map:
                item["description"] = javadoc_map[item["name"]]
                
            parsed_args.append(item)
        return parsed_args

    def _dummy_value_for_type(self, type_name):
        mapping = {
            "String": "string",
            "Long": 1,
            "Integer": 1,
            "int": 1,
            "long": 1,
            "Boolean": True,
            "boolean": True,
            "Double": 1.0,
            "double": 1.0,
            "Float": 1.0,
            "float": 1.0,
            "BigDecimal": 1.0
        }
        return mapping.get(type_name, "string")

    def _build_get_request_example(self, full_url, params_list, dto_map=None):
        if not params_list:
            return ""
        dto_map = dto_map or {}
        path_url = full_url
        query_pairs = []
        for p in params_list:
            if p.get("in") == "path":
                value = self._dummy_value_for_type(p.get("type", "String"))
                path_url = path_url.replace(f"{{{p['name']}}}", str(value))
            elif p.get("in") == "query":
                value = self._dummy_value_for_type(p.get("type", "String"))
                query_pairs.append(f"{p['name']}={value}")
            elif p.get("in") == "unknown":
                p_type = p.get("type")
                if p_type in dto_map:
                    for f in dto_map[p_type]:
                        value = self._dummy_value_for_type(f.get("type", "String").split('.')[-1])
                        query_pairs.append(f"{f['field']}={value}")
                else:
                    value = self._dummy_value_for_type(p.get("type", "String"))
                    query_pairs.append(f"{p['name']}={value}")
        query_str = "&".join(query_pairs)
        if query_str:
            return f"### 请求示例\n```text\nGET {path_url}?{query_str}\n```"
        return f"### 请求示例\n```text\nGET {path_url}\n```"

    def _render_method(self, method, index, base_url, is_rest_controller, controller_name="", dto_map=None):
        """Returns dict: {"markdown": str, "mermaid": str or None, "method_id": int}"""
        sub_url = self._extract_url_regex(method['modifiers'])

        # Clean merge of urls
        b = base_url.strip('/')
        s = sub_url.strip('/')
        full_url = f"/{b}/{s}".replace('//', '/')

        http_method = self._extract_http_method_regex(method['modifiers'])
        api_desc = method.get('what', 'No description')
        has_response_body = '@ResponseBody' in method['modifiers']
        is_json_api = is_rest_controller or has_response_body
        match_swag = re.search(r'@ApiOperation\s*\(\s*(?:value\s*=\s*)?"([^"]+)"', method['modifiers'])
        if match_swag: api_desc = match_swag.group(1)

        block = []
        title = api_desc if api_desc and api_desc != 'No description' else method['name']
        block.append(f"#### {index}. {title} ({method['name']})")

        # Path Conflict Annotation
        display_url = full_url
        if "Portal" in controller_name and "/portal" not in full_url.lower():
            display_url += " (Portal)"

        block.append(f"- **URL**: `{display_url}`")
        block.append(f"- **方法**: `{http_method}`")
        block.append(f"- **概要**: {api_desc}")
        block.append(f"- **返回**: `{method.get('display_return_type', 'Void')}`")

        if not is_json_api and method.get('display_return_type') == "String":
            block.append(f"> [!WARNING] 缺少 `@ResponseBody`，返回的字符串可能会被当作 **视图名称** 解析。")

        if method.get('what') and method['what'] != api_desc:
            block.append(f"- **Description**: {method['what']}")
        if method.get('why'):
            block.append(f"\n**设计说明**:\n> {method['why']}")
        if method.get('how'):
            block.append(f"\n**实现逻辑**:\n{method['how']}")

        # Extract Javadoc params
        javadoc_map = self._extract_javadoc_params(method.get('source_code', ''))
        params_list = self._parse_method_params(method['params_str'], javadoc_map)
        if params_list:
            block.append("\n**参数**:")
            block.append("| 参数名 | 类型 | 必填 | 默认值 | 说明 |")
            block.append("| --- | --- | --- | --- | --- |")
            for p in params_list:
                req = p['required']
                default_val = p.get('default', '-')
                desc = p['description']
                block.append(f"| {p['name']} | `{p['type']}` | {req} | {default_val} | {desc} |")
        else:
            if method['params_str'] and method['params_str'] != "()":
                 block.append(f"\n**参数**: *(复杂对象或解析失败: `{method['params_str']}`)*")
            else:
                 block.append("\n**参数**: 无")

        # Build mermaid sequence diagram separately
        mermaid_block = None
        if method.get('trace'):
            mermaid_lines = []
            mermaid_lines.append(f"**逻辑流程**: {controller_name}.{method['name']}")
            mermaid_lines.append("```mermaid")
            mermaid_lines.append("sequenceDiagram")
            mermaid_lines.append("participant Client")
            mermaid_lines.append("participant Controller")

            participants = {"Controller"}

            def render_trace(current_name, trace_list):
                for step in trace_list:
                    target = step['owner']
                    target_short = target.split('.')[-1]
                    if target_short not in participants:
                        mermaid_lines.append(f"participant {target_short}")
                        participants.add(target_short)
                    mermaid_lines.append(f"{current_name}->>{target_short}: {step['method']}")
                    if 'sub_trace' in step and step['sub_trace']:
                        render_trace(target_short, step['sub_trace'])

            render_trace("Controller", method['trace'])
            mermaid_lines.append("```")
            mermaid_block = "\n".join(mermaid_lines)

        # LLM Generated Examples
        if self.llm.enabled and is_json_api:
            prebuilt_request = ""
            response_only = False
            if http_method == "GET":
                prebuilt_request = self._build_get_request_example(full_url, params_list, dto_map=dto_map)
            elif not params_list and (not method.get('params_str') or method.get('params_str') == "()"):
                response_only = True
            else:
                body_param = next((p for p in params_list if p.get("in") == "body"), None)
                if body_param and dto_map and body_param.get("type") in dto_map:
                    body_json = self._build_json_from_dto(body_param.get("type"), dto_map)
                    if body_json:
                        prebuilt_request = f"### 请求示例\n```json\n{json.dumps(body_json, ensure_ascii=False, indent=2)}\n```"
            examples = self.llm.generate_method_examples(
                method['name'],
                method.get('params_str', ''),
                method.get('display_return_type', 'Object'),
                method_desc=method.get('what', ''),
                design_intent=method.get('why', ''),
                http_method=http_method,
                prebuilt_request_example=prebuilt_request,
                response_only=response_only
            )
            if examples:
                block.append(examples)
        elif http_method == "GET":
            prebuilt_request = self._build_get_request_example(full_url, params_list, dto_map=dto_map)
            if prebuilt_request:
                block.append(prebuilt_request)

        return {
            "markdown": "\n".join(block),
            "mermaid": mermaid_block,
            "method_id": method.get('legacy_id'),
            "class_id": method.get('class_id'),
            "file_name": method.get('file_name'),
        }

    def _render_dto_diagram(self, dto_map):
        if not dto_map: return ""
        block = ["```mermaid", "classDiagram"]
        for name, fields in dto_map.items():
            block.append(f"class {name} {{")
            for f in fields:
                ftype = f['type'].split('.')[-1]
                block.append(f"  +{ftype} {f['field']}")
            block.append("}")
        block.append("```\n")
        return "\n".join(block)

if __name__ == "__main__":
    generator = StrictApiDocGenerator(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        generator.generate_all()
    finally:
        generator.close()
