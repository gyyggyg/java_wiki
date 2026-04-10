"""
LLM接口

提供层级化模块生成所需的语言模型调用功能
"""

import os
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

# 导入时自动加载 .env，保证单独运行 graph/*.py、workflows/*.py 等调试入口时
# 也能读到 LLM_MODEL / LLM_PROVIDER / OPENAI_API_KEY / BASE_URL 等配置。
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 全局 fallback 默认值（当 .env 与调用方都没指定时使用）
_DEFAULT_MODEL = "gpt-5-mini"
_DEFAULT_PROVIDER = "openai"

# chain 级别的 transient error 重试配置
_LLM_CHAIN_MAX_RETRIES = int(os.environ.get("LLM_CHAIN_MAX_RETRIES", "4"))


def _build_retry_exceptions():
    """构建需要在 chain 级别自动重试的 transient error 类型列表。

    包含两类常见的可恢复错误：
    1. openai SDK 的 APIConnectionError / APITimeoutError —— 真正的网络/超时问题
    2. openai SDK 的 BadRequestError —— 本地 LLM 网关反向代理流式响应时，
       上游偶发"流式传输中断"会以 HTTP 400 的形式返回（本质上是 transient），
       需要重试以避免整条 chain 因为一次闪断而失败
    """
    exceptions = []
    try:
        from openai import APIConnectionError, APITimeoutError, BadRequestError
        exceptions.extend([APIConnectionError, APITimeoutError, BadRequestError])
    except ImportError:
        pass
    try:
        from httpx import RemoteProtocolError, ReadError, ConnectError
        exceptions.extend([RemoteProtocolError, ReadError, ConnectError])
    except ImportError:
        pass
    return tuple(exceptions) if exceptions else (Exception,)


class LLMInterface:
    """LLM接口封装，专门用于层级化模块生成"""

    def __init__(self,
                 model_name: Optional[str] = None,
                 provider: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 16000,
                 retry_count: int = 3,
                 **model_kwargs):
        """初始化LLM接口

        优先级：显式参数 > .env 中的 LLM_MODEL/LLM_PROVIDER > 硬编码 fallback。

        Args:
            model_name: 模型名称。None 时从 env LLM_MODEL 读取，再 fallback 到 "gpt-5-mini"
            provider: 提供商 (openai, claude, google)。None 时从 env LLM_PROVIDER 读取，再 fallback 到 "openai"
            temperature: 温度参数
            max_tokens: 最大令牌数
            retry_count: 重试次数
            **model_kwargs: 其他模型参数
        """
        resolved_model = model_name or os.environ.get("LLM_MODEL") or _DEFAULT_MODEL
        resolved_provider = provider or os.environ.get("LLM_PROVIDER") or _DEFAULT_PROVIDER

        self.model_kwargs = {
            "model_name": resolved_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **model_kwargs
        }
        self.provider = resolved_provider.lower()
        self.retry_count = retry_count
        self._initialize_llm()

    def _initialize_llm(self):
        """初始化LLM模型"""
        if self.provider == "openai":
            # 优先使用调用方显式传入的 base_url/api_key，其次才读环境变量，
            # 支持 OpenAI 兼容网关（如 .env 中的 BASE_URL + OPENAI_API_KEY）
            openai_kwargs = self.model_kwargs.copy()
            base_url = (
                openai_kwargs.pop("base_url", None)
                or openai_kwargs.pop("openai_api_base", None)
                or os.environ.get("OPENAI_BASE_URL")
                or os.environ.get("BASE_URL")
            )
            if base_url:
                openai_kwargs["base_url"] = base_url
            api_key = (
                openai_kwargs.pop("api_key", None)
                or openai_kwargs.pop("openai_api_key", None)
                or os.environ.get("OPENAI_API_KEY")
            )
            if api_key:
                openai_kwargs["api_key"] = api_key
            self.llm = ChatOpenAI(**openai_kwargs)
        elif self.provider == "claude":
            self.llm = ChatAnthropic(**self.model_kwargs)
        elif self.provider == "google":
            # Google模型使用 'model' 参数，而不是 'model_name'
            google_kwargs = self.model_kwargs.copy()
            if 'model_name' in google_kwargs:
                google_kwargs['model'] = google_kwargs.pop('model_name')
            self.llm = ChatGoogleGenerativeAI(**google_kwargs)
        else:
            # 默认使用OpenAI（同样的 base_url / api_key 处理）
            openai_kwargs = self.model_kwargs.copy()
            base_url = (
                openai_kwargs.pop("base_url", None)
                or openai_kwargs.pop("openai_api_base", None)
                or os.environ.get("OPENAI_BASE_URL")
                or os.environ.get("BASE_URL")
            )
            if base_url:
                openai_kwargs["base_url"] = base_url
            api_key = (
                openai_kwargs.pop("api_key", None)
                or openai_kwargs.pop("openai_api_key", None)
                or os.environ.get("OPENAI_API_KEY")
            )
            if api_key:
                openai_kwargs["api_key"] = api_key
            self.llm = ChatOpenAI(**openai_kwargs)

        # 给 llm 包一层 chain 级的 transient error 重试，
        # 以应对本地 LLM 网关反向代理流式响应时偶发的"流式传输中断"（会以 HTTP 400 抛出）。
        # 所有通过 `prompt | self.llm | parser` 构造的 chain 都自动享有重试能力。
        retry_exceptions = _build_retry_exceptions()
        if retry_exceptions:
            self.llm = self.llm.with_retry(
                retry_if_exception_type=retry_exceptions,
                stop_after_attempt=_LLM_CHAIN_MAX_RETRIES,
                wait_exponential_jitter=True,
            )

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

    def get_json_llm(self):
        """返回强制JSON输出的LLM实例。
        OpenAI/兼容接口使用 response_format JSON mode；其他provider原样返回。
        """
        if self.provider == "openai":
            return self.llm.bind(response_format={"type": "json_object"})
        return self.llm

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
