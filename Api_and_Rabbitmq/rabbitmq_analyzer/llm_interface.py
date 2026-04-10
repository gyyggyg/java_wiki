"""
简单的 LLM 接口实现
支持 OpenAI API 和兼容的服务
"""

import json
import os
from typing import Dict, Any, Optional
import httpx


class LLMInterface:
    """轻量级 LLM 接口，支持 OpenAI API"""

    def __init__(self,
                 model_name: str = "gpt-4o-mini",
                 provider: str = "openai",
                 temperature: float = 0.1,
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None):
        """
        初始化 LLM 接口

        Args:
            model_name: 模型名称
            provider: 提供商 (openai, deepseek, 或其他兼容 OpenAI API 的服务)
            temperature: 温度参数
            api_key: API 密钥，如果不提供则从环境变量读取
            base_url: API 基础 URL，如果不提供则使用默认值
        """
        self.model_name = model_name
        self.provider = provider
        self.temperature = temperature

        # 设置 API 密钥
        if api_key:
            self.api_key = api_key
        elif provider == "openai":
            self.api_key = os.environ.get("OPENAI_API_KEY")
        elif provider == "deepseek":
            self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        else:
            self.api_key = os.environ.get("LLM_API_KEY")

        if not self.api_key:
            raise ValueError(f"API key not found for provider: {provider}")

        # 设置 API 基础 URL
        if base_url:
            self.base_url = base_url
        elif provider == "deepseek":
            self.base_url = "https://api.deepseek.com"
        else:
            self.base_url = "https://api.zhec.moe/v1"

        # 创建 HTTP 客户端
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=60.0
        )

    async def structured_generate(self,
                                   system_prompt: str,
                                   user_prompt: str,
                                   output_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成结构化输出（JSON 格式）

        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            output_schema: 输出 JSON schema（这里简化处理，主要是提示 LLM 返回 JSON）

        Returns:
            解析后的 JSON 对象
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # 构建请求
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"}  # 强制 JSON 输出
        }

        try:
            # 发送请求
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()

            # 解析响应
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # 解析 JSON
            return json.loads(content)

        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {e}")
        except Exception as e:
            raise Exception(f"LLM request failed: [{type(e).__name__}] {e!r}")

    async def generate(self,
                      system_prompt: str,
                      user_prompt: str) -> str:
        """
        生成普通文本输出

        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示

        Returns:
            生成的文本
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature
        }

        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"LLM request failed: [{type(e).__name__}] {e!r}")

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()
