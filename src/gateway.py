from src.config import config
from src.services.text_gen import RealTextGenService, MockTextGenService
from src.services.image_gen import RealImageGenService, MockImageGenService
from src.services.audio_gen import RealAudioGenService, MockAudioGenService

class AIServiceGateway:
    def __init__(self):
        if config.ENABLE_MOCK:
            print("正在以 MOCK 模式初始化 AIServiceGateway")
            self.text_service = MockTextGenService()
            self.image_service = MockImageGenService()
            self.audio_service = MockAudioGenService()
        else:
            print("正在以 REAL 模式初始化 AIServiceGateway")
            self.text_service = RealTextGenService()
            self.image_service = RealImageGenService()
            self.audio_service = RealAudioGenService()
        
    def generate_text(self, context: dict, exercise_type: str, config: dict = None):
        """
        生成练习的结构化文本内容。
        """
        return self.text_service.generate(context, exercise_type, config)
        
    def generate_image(self, prompt: str, style: str = "textbook_illustration"):
        """
        生成图片 URL。
        """
        return self.image_service.generate(prompt, style)
        
    def generate_audio(self, text: str, voice_id: str = "tongtong", speed: float = 1.0):
        """
        生成音频 URL。
        """
        return self.audio_service.generate(text, voice_id, speed)
