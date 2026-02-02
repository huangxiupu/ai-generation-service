import os
import uuid
from src.config import config
from src.factory import ProviderFactory

class RealAudioGenService:
    def __init__(self):
        self.provider = ProviderFactory.get_provider(config.CHANNEL_AUDIO)
        
    def generate(self, text: str, voice_id: str = None, speed: float = 1.0, **kwargs) -> str:
        """
        使用配置的 TTS 提供商为给定文本生成音频。
        返回生成文件的本地路径/URL。
        """
        try:
            # 如果没有提供 voice_id，尝试从 kwargs 中的 gender 推断
            if voice_id is None:
                gender = kwargs.get("gender")
                if gender == "female":
                    voice_id = "female"
                elif gender == "male":
                    voice_id = "male"
                else:
                    voice_id = "narrator"

            # 获取映射后的真实 Voice ID
            actual_voice_id = config.get_voice_id(voice_id, config.CHANNEL_AUDIO)
            
            # 使用配置中的模型
            audio_content = self.provider.generate_audio(
                text=text,
                model=config.MODEL_AUDIO,
                voice=actual_voice_id,
                speed=speed,
                **kwargs
            )
            
            # 生成唯一文件名
            filename = f"generated_audio_{uuid.uuid4()}.mp3"
            # 确保 static 目录存在
            output_dir = os.path.join(config.BASE_DIR, "static", "audio")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)
            
            # 保存二进制内容
            with open(output_path, "wb") as f:
                f.write(audio_content)
                
            # 返回相对 URL 路径（假设有 Web 服务器提供服务）
            return f"/static/audio/{filename}"
            
        except Exception as e:
            # 记录错误并重新引发或优雅处理
            print(f"生成音频时出错: {e}")
            raise e

class MockAudioGenService:
    def generate(self, text: str, voice_id: str = None, speed: float = 1.0, **kwargs) -> str:
        """
        返回模拟的音频 URL。
        """
        if voice_id is None:
            gender = kwargs.get("gender")
            if gender == "female":
                voice_id = "female"
            elif gender == "male":
                voice_id = "male"
            else:
                voice_id = "narrator"

        voice_map = {
            "narrator": "tongtong",
            "male": "chuichui",
            "female": "xiaochen"
        }
        
        actual_voice = voice_map.get(voice_id, voice_id)
        
        # 模拟 API 响应
        return f"https://api.bigmodel.cn/tts/mock-audio-{actual_voice}.mp3"
