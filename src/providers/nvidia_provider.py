from .openai_compatible import OpenAICompatibleProvider

class NvidiaProvider(OpenAICompatibleProvider):
    """
    NVIDIA NIM (Build NVIDIA) 提供商。
    继承自 OpenAICompatibleProvider，因为其 API 与 OpenAI 兼容。
    """
    def __init__(self, api_key: str, base_url: str = "https://integrate.api.nvidia.com/v1"):
        super().__init__(api_key=api_key, base_url=base_url)
