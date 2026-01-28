import os
import uuid
import httpx
from src.config import config
from src.factory import ProviderFactory

class RealImageGenService:
    def __init__(self):
        self.provider = ProviderFactory.get_provider(config.CHANNEL_IMAGE)
        
    def generate(self, prompt: str, reference_style: str = "textbook_illustration") -> str:
        """
        根据提示词生成图片，下载并返回本地相对路径。
        """
        enhanced_prompt = self._enhance_prompt(prompt, reference_style)
        
        # 使用配置的模型生成图片 URL
        image_url = self.provider.generate_image(
            prompt=enhanced_prompt,
            model=config.MODEL_IMAGE
        )

        try:
            # 下载图片
            with httpx.Client() as client:
                response = client.get(image_url)
                response.raise_for_status()
                image_content = response.content
            
            # 生成唯一文件名
            filename = f"generated_image_{uuid.uuid4()}.png"
            
            # 确保 static/images 目录存在
            output_dir = os.path.join(config.BASE_DIR, "static", "images")
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = os.path.join(output_dir, filename)
            
            # 保存图片
            with open(output_path, "wb") as f:
                f.write(image_content)
            
            # 返回相对路径
            return f"/static/images/{filename}"
            
        except Exception as e:
            print(f"处理图像生成结果时出错: {e}")
            raise e

    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """
        添加风格关键词到提示词中，以保持一致性。
        """
        style_keywords = {
            "textbook_illustration": "cartoon style, flat illustration, vector art, white background, suitable for children education, high definition",
            "realistic": "realistic photo, high quality, 4k, clear background"
        }
        
        style_suffix = style_keywords.get(style, style_keywords["textbook_illustration"])
        return f"{prompt}, {style_suffix}"

class MockImageGenService:
    def generate(self, prompt: str, reference_style: str = "textbook_illustration") -> str:
        """
        返回模拟的图片 URL。
        """
        return "https://placehold.co/1024x1024.png?text=Mock+Image"
