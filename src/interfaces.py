from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class AIProvider(ABC):
    """
    AI 服务提供商的抽象基类。
    标准化与不同 AI 模型（文本、图像、音频）的交互。
    """

    @abstractmethod
    def chat_completion(self, 
                        model: str, 
                        messages: List[Dict[str, str]], 
                        temperature: float = 1.0, 
                        max_tokens: Optional[int] = None,
                        **kwargs) -> str:
        """
        使用聊天模型生成文本补全。
        
        Args:
            model: 模型标识符 (例如 'glm-4', 'gpt-4')。
            messages: 消息字典列表 (例如 [{'role': 'user', 'content': '...'}]).
            temperature: 采样温度。
            max_tokens: 最大生成 token 数。
            **kwargs: 其他特定于提供商的参数。
            
        Returns:
            生成的文本内容。
        """
        pass

    @abstractmethod
    def generate_image(self, 
                       prompt: str, 
                       model: str, 
                       size: str = "1024x1024", 
                       style: Optional[str] = None,
                       **kwargs) -> str:
        """
        根据文本提示生成图像。
        
        Args:
            prompt: 图像描述。
            model: 模型标识符 (例如 'cogview-3', 'dall-e-3')。
            size: 图像尺寸 (例如 '1024x1024')。
            style: 可选的风格参数 (例如 'vivid', 'natural')。
            **kwargs: 其他特定于提供商的参数。
            
        Returns:
            生成图像的 URL。
        """
        pass

    @abstractmethod
    def generate_audio(self, 
                       text: str, 
                       model: str, 
                       voice: str, 
                       speed: float = 1.0, 
                       **kwargs) -> Any:
        """
        将文本转换为音频 (TTS)。
        
        Args:
            text: 要转换的文本。
            model: 模型标识符 (例如 'glm-tts', 'tts-1')。
            voice: 声音标识符。
            speed: 播放速度。
            **kwargs: 其他特定于提供商的参数。
            
        Returns:
            音频内容 (bytes) 或 URL/文件路径，取决于实现。
            理想情况下返回 bytes 或流，以便服务层处理。
        """
        pass
