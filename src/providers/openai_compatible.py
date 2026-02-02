import requests
from openai import OpenAI
from typing import List, Dict, Any, Optional
import json
from ..interfaces import AIProvider
from ..utils.logger import llm_logger, format_llm_request, format_llm_response

class OpenAICompatibleProvider(AIProvider):
    """
    OpenAI 兼容 API 的通用提供商。
    支持智谱、阿里云、SiliconFlow、OpenRouter 等。
    """
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        # 检查是否为 Antigravity 代理，如果是则使用 requests 以避免 httpx 的 502 兼容性问题
        self.use_requests_fallback = "127.0.0.1:8045" in base_url
        
        if not self.use_requests_fallback:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            llm_logger.info(f"检测到 Antigravity 代理 ({base_url})，启用 requests 回退模式以避免 502 错误。")

    def _chat_completion_via_requests(self, 
                                     model: str, 
                                     messages: List[Dict[str, str]], 
                                     temperature: float = 1.0, 
                                     max_tokens: Optional[int] = None,
                                     **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def chat_completion(self, 
                        model: str, 
                        messages: List[Dict[str, str]], 
                        temperature: float = 1.0, 
                        max_tokens: Optional[int] = None,
                        **kwargs) -> str:
        
        # 记录输入日志
        llm_logger.info(format_llm_request(model, messages))
        
        try:
            if self.use_requests_fallback:
                content = self._chat_completion_via_requests(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            else:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                content = response.choices[0].message.content
                
            # 记录输出日志
            llm_logger.info(format_llm_response(content))
            return content
        except Exception as e:
            llm_logger.error(f"LLM Call Failed: {str(e)}")
            raise e

    def generate_image(self, 
                       prompt: str, 
                       model: str, 
                       size: str = "1024x1024", 
                       style: Optional[str] = None,
                       **kwargs) -> str:
        
        if self.use_requests_fallback:
            # Antigravity 目前可能不支持图像生成，如果需要可以实现类似逻辑
            raise NotImplementedError("Antigravity 代理模式暂不支持图像生成。")

        # 标准 OpenAI 图像生成
        params = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": 1,
            **kwargs
        }
        
        if style:
            params["style"] = style
            
        try:
            response = self.client.images.generate(**params)
            return response.data[0].url
        except Exception as e:
            raise e

    def generate_audio(self, 
                       text: str, 
                       model: str, 
                       voice: str, 
                       speed: float = 1.0, 
                       **kwargs) -> bytes:
        
        if self.use_requests_fallback:
            # Antigravity 目前可能不支持音频生成
            raise NotImplementedError("Antigravity 代理模式暂不支持音频生成。")

        response = self.client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            speed=speed,
            **kwargs
        )
        
        return response.content
