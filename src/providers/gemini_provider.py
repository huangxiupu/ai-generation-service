from .openai_compatible import OpenAICompatibleProvider

class GeminiProvider(OpenAICompatibleProvider):
    """
    Google Gemini Provider via OpenAI Compatible API.
    """
    def __init__(self, api_key: str, base_url: str = "http://127.0.0.1:8045/v1"):
        super().__init__(api_key=api_key, base_url=base_url)

    # Gemini specific overrides can be added here if needed
    # For now, base implementation is sufficient for chat
