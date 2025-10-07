import os
from typing import Any, Dict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from interfaces.simple_validate_mermaid import SimpleMermaidValidator
from chains.prompts.concept_prompt import CONCEPT_PROMPT
from chains.common_chains import ChainFactory
from interfaces.llm_interface import LLMInterface
from interfaces.data_master import get_file
from typing_extensions import TypedDict

class ConceptDocState(TypedDict, total=False):
    readme_content: str
    concept_doc: str

def build_concept_doc_app(llm: LLMInterface):
    concept_chain = ChainFactory.create_generic_chain(llm, CONCEPT_PROMPT)

    async def read_readme(state: ConceptDocState) -> ConceptDocState:
        try:
            code_root = os.environ.get("SOURCE_CODE_ROOT")
            if not code_root:
                raise RuntimeError("缺少环境变量：SOURCE_CODE_ROOT")
            try:
                readme_abs_md = os.path.join(code_root, "README.md")
                readme_content = get_file(readme_abs_md)
            except Exception:
                readme_abs = os.path.join(code_root, "README")
                readme_content = get_file(readme_abs)
        except Exception as e:
            print(f"警告: 读取 README 文件失败 - {e}")
            readme_content = "项目 README 文件缺失。"
        return {"readme_content": readme_content}

    async def gen_concept(state: ConceptDocState) -> ConceptDocState:
        validator = SimpleMermaidValidator()
        result = await concept_chain.ainvoke({
            "readme_content": state["readme_content"],
        })
        result_validate = validator.validate_file(result)
        while not result_validate["result"]:
            error = result_validate["errors"]
            error_msg = f"注意: 如果需要生成mermaid语句, 在生成mermaid语句时需要规避的问题例如:{error}"
            input = state["readme_content"] + str(error_msg)
            result = await concept_chain.ainvoke({
                "readme_content": input,
            })
            result_validate = validator.validate_file(result)
            print(result_validate["result"])
        return {"concept_doc": result}

    async def save_doc(state: ConceptDocState) -> ConceptDocState:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        md_root = os.getenv("MD_OUTPUT_ROOT", os.path.join(base_dir, "md_files"))
        output_filename = os.path.join(md_root, "doc_Core_Concepts_Analysis.md")
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(state["concept_doc"])
        return {"output_filename": output_filename}

    graph = StateGraph(ConceptDocState)
    graph.add_node("read_readme", read_readme)
    graph.add_node("gen_concept", gen_concept)
    graph.add_node("save_doc", save_doc)

    graph.set_entry_point("read_readme")
    graph.add_edge("read_readme", "gen_concept")
    graph.add_edge("gen_concept", "save_doc")
    graph.add_edge("save_doc", END)

    app = graph.compile(checkpointer=MemorySaver())
    return app


if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    
    from interfaces.llm_interface import LLMInterface
    
    async def main():
        print("=== 独立运行概念文档生成应用 ===")
        
        # 初始化LLM
        llm = LLMInterface(
            model_name="gpt-4.1-2025-04-14",
            provider="openai"
        )
        
        # 构建应用
        app = build_concept_doc_app(llm)
        print("✓ 应用构建成功")
        
        # 运行应用
        result = await app.ainvoke(
            {}, 
            config={"configurable": {"thread_id": "standalone-concept"}}
        )
        
    
    
    # 运行主函数
    asyncio.run(main())
