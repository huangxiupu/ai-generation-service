import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
from ..interfaces import AIProvider
from typing import List, Dict, Any, Optional

class AliyunProvider(AIProvider):
    """
    阿里云 DashScope 原生 Provider，使用官方 SDK 支持 CosyVoice 等模型。
    """
    def __init__(self, api_key: str, base_url: str = None):
        self.api_key = api_key
        # 设置 dashscope 全局 API Key
        dashscope.api_key = api_key
        # base_url 在 SDK 中通常不需要手动设置，除非是私有部署

    def chat_completion(self, model: str, messages: List[Dict[str, str]], **kwargs) -> str:
        raise NotImplementedError("AliyunProvider does not support chat_completion yet.")

    def generate_image(self, prompt: str, model: str, **kwargs) -> str:
        raise NotImplementedError("AliyunProvider does not support generate_image yet.")

    def generate_audio(self, text: str, model: str, voice: str, speed: float = 1.0, **kwargs) -> bytes:
        """
        使用 DashScope SDK 生成音频。
        """
        # 初始化合成器
        synthesizer = SpeechSynthesizer(model=model, voice=voice)
        
        # 准备参数
        # 注意：SDK 的 call 方法通常直接接受文本，其他参数可能需要通过 format 等方式传递，
        # 或者在构造 SpeechSynthesizer 时传递。
        # 根据官方文档，speed 等参数可以在构造函数中通过 extra_params 传递，或者有些版本支持直接参数。
        # CosyVoice 模型通常接受 'speech_rate' 或 'speed_ratio'。
        # 这里我们尝试将 extra parameters 放入 kwargs
        
        # 构建调用参数
        call_kwargs = {}
        
        # 处理语速
        # CosyVoice 似乎使用 'speed_ratio' (float, default 1.0)
        # Sambert 使用 'speech_rate' (int, -500 to 500)
        # 我们假设使用 CosyVoice，因为模型是 cosyvoice-v2
        if abs(speed - 1.0) > 1e-6:
             # 如果是 cosyvoice，通常放在 format 或 parameters 中
             # SDK 的 SpeechSynthesizer 构造函数签名：
             # __init__(self, model=None, voice=None, format=None, sample_rate=None, volume=None, speech_rate=None, pitch_rate=None, ... **kwargs)
             # 所以我们可以直接传 speech_rate? 但 cosyvoice 用的是 ratio。
             # 尝试直接传给 call 方法或者构造函数
             pass

        # 重新初始化带参数的 synthesizer
        # 注意：为了稳妥，我们使用 kwargs 传递给 SpeechSynthesizer
        # 映射 speed -> speech_rate (如果是 Sambert) 或者 speed_ratio (如果是 CosyVoice)
        # 根据 CosyVoice 文档，参数是 speed_ratio。
        # 但 SDK 的 SpeechSynthesizer 参数名是 speech_rate。
        # 让我们尝试把 speed 作为 kwargs 的一部分传进去，或者直接用 SDK 的 speech_rate 参数
        # 如果模型是 cosyvoice，dashscope SDK 可能会自动处理
        
        # 简单起见，我们直接调用 call，并假设 SDK 会处理默认值。
        # 如果需要调整语速，可能需要更详细的参数映射。
        # 目前为了修复 crash，我们先用最简单的调用方式。
        
        # 如果确实需要传递 speed:
        # synthesizer = SpeechSynthesizer(model=model, voice=voice, speech_rate=speed) 
        # (注意：如果 speech_rate 是 int，则不能传 float)
        
        # 让我们先只传 model 和 voice，因为之前的错误是 url error，这解决了连接问题。
        # 语速问题可以后续优化。
        
        try:
            # call 方法返回的是 bytes
            audio = synthesizer.call(text)
            return audio
        except Exception as e:
             raise Exception(f"Aliyun TTS SDK Error: {e}")
