from openai import OpenAI
from typing import List, Dict, Any, Optional
from ..interfaces import AIProvider

class OpenAICompatibleProvider(AIProvider):
    """
    OpenAI 兼容 API 的通用提供商。
    支持智谱、阿里云、SiliconFlow、OpenRouter 等。
    """
    
    def __init__(self, api_key: str, base_url: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def chat_completion(self, 
                        model: str, 
                        messages: List[Dict[str, str]], 
                        temperature: float = 1.0, 
                        max_tokens: Optional[int] = None,
                        **kwargs) -> str:
        
        # 如果需要，过滤掉不支持的 kwargs，或者直接传递
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        return response.choices[0].message.content

    def generate_image(self, 
                       prompt: str, 
                       model: str, 
                       size: str = "1024x1024", 
                       style: Optional[str] = None,
                       **kwargs) -> str:
        
        # 注意：'style' 参数可能并非所有提供商都支持，或者映射到不同的字段。
        # OpenAI DALL-E 3 支持 'style' ('vivid' 或 'natural')。
        # 如果提供商不支持，我们可能需要过滤它或将其附加到提示词中。
        
        # 为了兼容性，如果提供了 style 但不在 kwargs 中，如果模型是 dall-e-3，我们尝试传递它
        # 否则，我们可能将其附加到提示词中。
        # 目前，如果底层客户端验证支持，我们在 kwargs 中传递它，
        # 或者依赖调用者将其放入提示词中。
        
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
            # 回退：某些提供商可能不支持 'style' 或其他参数。
            # 如果错误提到 'style'，是否在没有它的情况下重试？
            # 目前，让错误传播或让调用者处理它。
            raise e

    def generate_audio(self, 
                       text: str, 
                       model: str, 
                       voice: str, 
                       speed: float = 1.0, 
                       **kwargs) -> bytes:
        
        response = self.client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            speed=speed,
            **kwargs
        )
        
        # OpenAI python 客户端返回一个可以流式传输或读取的响应对象。
        # .content 给出字节。
        return response.content
