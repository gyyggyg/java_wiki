"""
LLM接口

提供层级化模块生成所需的语言模型调用功能
"""

from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage


class LLMInterface:
    """LLM接口封装，专门用于层级化模块生成"""

    def __init__(self,
                 model_name: str = "gpt-4o-mini",
                 provider: str = "openai",
                 temperature: float = 0.7,
                 max_tokens: int = 16000,
                 retry_count: int = 3,
                 **model_kwargs):
        """初始化LLM接口

        Args:
            model_name: 模型名称
            provider: 提供商 (openai, claude, google)
            temperature: 温度参数
            max_tokens: 最大令牌数
            retry_count: 重试次数
            **model_kwargs: 其他模型参数
        """
        self.model_kwargs = {
            "model_name": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **model_kwargs
        }
        self.provider = provider.lower()
        self.retry_count = retry_count
        self._initialize_llm()

    def _initialize_llm(self):
        """初始化LLM模型"""
        if self.provider == "openai":
            self.llm = ChatOpenAI(**self.model_kwargs)
        elif self.provider == "claude":
            self.llm = ChatAnthropic(**self.model_kwargs)
        elif self.provider == "google":
            # Google模型使用 'model' 参数，而不是 'model_name'
            google_kwargs = self.model_kwargs.copy()
            if 'model_name' in google_kwargs:
                google_kwargs['model'] = google_kwargs.pop('model_name')
            self.llm = ChatGoogleGenerativeAI(**google_kwargs)
        else:
            # 默认使用OpenAI
            self.llm = ChatOpenAI(**self.model_kwargs)

    async def generate_with_retry(self,
                                 system_prompt: str,
                                 user_prompt: str,
                                 retry_count: Optional[int] = None) -> str:
        """调用LLM并自动重试

        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            retry_count: 重试次数

        Returns:
            生成的文本
        """
        retries = retry_count if retry_count is not None else self.retry_count
        last_error = None

        for attempt in range(retries + 1):
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                response = await self.llm.agenerate([messages])
                return response.generations[0][0].text
            except Exception as e:
                last_error = e
                print(f"LLM调用失败 (尝试 {attempt + 1}/{retries + 1}): {e}")
                if attempt < retries:
                    # 简单的延迟重试
                    import asyncio
                    await asyncio.sleep(1)

        # 所有重试都失败
        raise last_error or Exception(f"LLM调用失败，重试 {retries} 次后仍然失败")

#     async def generate_module_summary(self, module_name: str, module_explanation: str) -> str:
#         """生成模块总结

#         Args:
#             module_name: 模块名称
#             module_explanation: 模块解释

#         Returns:
#             生成的模块总结
#         """
#         system_prompt = "你是一个专业的软件架构分析师。"

#         user_prompt = f"""这是代码中一个模块或函数'{module_name}'的解释：'{module_explanation}'。

# 请你总结这个模块/函数的作用，并清晰地列出它的主要职责。

# 要求：
# - 回答要简洁明了，重点突出
# - 使用中文回答
# - 突出模块的核心功能和职责
# - 长度控制在200字以内
# - 使用markdown格式，包含适当的段落和列表"""

#         return await self.generate_with_retry(system_prompt, user_prompt)

#     async def test_connection(self) -> bool:
#         """测试LLM连接

#         Returns:
#             连接是否成功
#         """
#         try:
#             test_prompt = "请回答：1+1等于几？"
#             response = await self.generate_with_retry(
#                 "你是一个助手。",
#                 test_prompt
#             )
#             return len(response.strip()) > 0
#         except Exception:
#             return False

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息

        Returns:
            模型信息字典
        """
        return {
            "provider": self.provider,
            "model_name": self.model_kwargs.get("model_name", "unknown"),
            "temperature": self.model_kwargs.get("temperature", 0.7),
            "max_tokens": self.model_kwargs.get("max_tokens", 16000),
            "retry_count": self.retry_count
        }
