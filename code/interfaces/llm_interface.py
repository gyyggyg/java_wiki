"""LLM 调用接口封装（集成 Mermaid 验证）"""
import os
import logging
from typing import Dict, Any, Optional, List
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from .mermaid_validator import MermaidValidator

logger = logging.getLogger(__name__)


# 优先从项目根或当前目录自动加载 .env（如果存在）
try:
    from dotenv import load_dotenv, find_dotenv
    _DOTENV_PATH = find_dotenv(usecwd=True)
    if _DOTENV_PATH:
        load_dotenv(_DOTENV_PATH, override=False)
        logger.info(f"📄 已加载 .env: {_DOTENV_PATH}")
    else:
        logger.debug("未发现 .env 文件，跳过加载")
except Exception as _e:
    logger.debug(f"加载 .env 失败: {_e}")


class LLMInterface:
    """LLM 调用接口，封装常用的 LLM 操作"""
    
    def __init__(
        self,
        model: str = None,
        temperature: float = None,
        api_key: str = None,
        enable_mermaid_validation: bool = True
    ):
        """
        初始化 LLM 接口
        
        Args:
            model: 模型名称，默认从环境变量或 .env 读取
            temperature: 温度参数，默认从环境变量或 .env 读取
            api_key: API Key，默认从环境变量或 .env 读取
            enable_mermaid_validation: 是否启用 Mermaid 自动验证和修复
        """
        # 仅从环境变量/.env读取
        self.model = model or os.getenv("LLM_MODEL", "gpt-4.1")
        self.temperature = temperature or float(os.getenv("LLM_TEMPERATURE", "0.3"))
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.enable_mermaid_validation = enable_mermaid_validation
        
        # 初始化 Mermaid 验证器
        if self.enable_mermaid_validation:
            self.mermaid_validator = MermaidValidator()
            logger.info("🔧 已启用 Mermaid 自动验证和修复")
        
        # 若环境变量存在但为空，尝试强制覆盖加载 .env
        if not self.api_key:
            try:
                from dotenv import load_dotenv, find_dotenv
                _p = find_dotenv(usecwd=True)
                if _p:
                    load_dotenv(_p, override=True)
                    self.api_key = os.getenv("OPENAI_API_KEY")
            except Exception:
                pass
        
        if not self.api_key:
            raise RuntimeError(
                "未检测到 OPENAI_API_KEY。请在环境变量或 .env 中配置 OPENAI_API_KEY 后重试。"
            )
        
        self.llm = ChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            api_key=self.api_key
        )
        logger.info(f"🤖 初始化 LLM: {self.model} (温度={self.temperature})")
    
    # 不再支持从 config.json 读取配置
    
    def invoke(self, prompt: str, system_message: str = None) -> str:
        """
        调用 LLM
        
        Args:
            prompt: 提示词
            system_message: 可选的系统消息
            
        Returns:
            LLM 响应文本
        """
        messages = []
        
        if system_message:
            messages.append(SystemMessage(content=system_message))
        
        messages.append(HumanMessage(content=prompt))
        
        logger.debug(f"📤 调用 LLM")
        response = self.llm.invoke(messages)
        
        return response.content
    
    def invoke_with_template(
        self, 
        template: str, 
        variables: Dict[str, Any],
        system_message: str = None,
        expected_diagram_type: str = None
    ) -> str:
        """
        使用模板调用 LLM，自动验证和修复 Mermaid 代码
        
        Args:
            template: 提示词模板
            variables: 模板变量字典
            system_message: 可选的系统消息
            expected_diagram_type: 期望的图表类型（用于验证）
            
        Returns:
            LLM 响应文本（已验证和修复的 Mermaid 代码）
        """
        messages = []
        
        # 添加系统消息
        if system_message:
            messages.append(SystemMessage(content=system_message))
        
        # 格式化用户消息
        prompt = ChatPromptTemplate.from_template(template)
        formatted_messages = prompt.format_messages(**variables)
        messages.extend(formatted_messages)
        
        # 调用 LLM
        logger.debug(f"📤 调用 LLM，变量: {list(variables.keys())}")
        response = self.llm.invoke(messages)
        
        content = response.content
        
        # 如果启用了 Mermaid 验证，进行验证和修复
        if self.enable_mermaid_validation and expected_diagram_type:
            content = self._validate_and_fix_mermaid(content, expected_diagram_type)
        
        return content
    
    async def ainvoke_with_template(
        self,
        template: str,
        variables: Dict[str, Any],
        system_message: str = None
    ) -> str:
        """
        使用模板异步调用 LLM（单条）
        """
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        prompt = ChatPromptTemplate.from_template(template)
        formatted_messages = prompt.format_messages(**variables)
        messages.extend(formatted_messages)
        response = await self.llm.ainvoke(messages)
        return response.content

    async def abatch_with_template(
        self,
        template: str,
        variables_list: List[Dict[str, Any]],
        system_message: str = None,
        concurrency: int = 5,
        expected_diagram_type: str = None
    ) -> List[str]:
        """
        使用模板批量异步调用 LLM，带并发度限制。
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def _worker(vars_: Dict[str, Any]) -> str:
            async with semaphore:
                content = await self.ainvoke_with_template(
                    template=template,
                    variables=vars_,
                    system_message=system_message,
                )
                
                # 如果启用了 Mermaid 验证，进行验证和修复
                if self.enable_mermaid_validation and expected_diagram_type:
                    content = self._validate_and_fix_mermaid(content, expected_diagram_type)
                
                return content

        tasks = [asyncio.create_task(_worker(v)) for v in variables_list]
        return await asyncio.gather(*tasks)
    
    @staticmethod
    def clean_mermaid_code(code: str) -> str:
        """
        简单清理 Mermaid 代码（保留用于向后兼容）
        
        注意：推荐使用 MermaidValidator 进行完整的验证和修复
        
        Args:
            code: 原始代码
            
        Returns:
            清理后的代码
        """
        import re
        
        if not code:
            return code
        
        # 移除 markdown 代码块标记
        code = code.strip()
        code = re.sub(r"^```(?:mermaid)?\s*\n?", "", code.strip())
        code = re.sub(r"\n?```\s*$", "", code.strip())
        
        return code.strip()
    
    def _validate_and_fix_mermaid(self, code: str, diagram_type: str = None) -> str:
        """
        验证并修复 Mermaid 代码
        
        Args:
            code: 原始 Mermaid 代码
            diagram_type: 期望的图表类型
            
        Returns:
            修复后的 Mermaid 代码
        """
        # 使用验证器进行验证和修复（内部已包含基本清理）
        is_valid, fixed_code, warnings = self.mermaid_validator.validate_and_fix(code, diagram_type)
        
        if warnings:
            logger.warning(f"Mermaid 代码修复: {len(warnings)} 个问题")
            for warning in warnings[:5]:  # 只显示前5个警告
                logger.debug(f"  - {warning}")
            if len(warnings) > 5:
                logger.debug(f"  ... 还有 {len(warnings) - 5} 个警告")
        
        if not is_valid:
            logger.error("⚠️ Mermaid 代码验证失败，但已尽力修复")
        
        return fixed_code