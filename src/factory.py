from typing import Dict, Optional
from src.config import config
from src.interfaces import AIProvider
from src.providers.openai_compatible import OpenAICompatibleProvider
from src.providers.aliyun_provider import AliyunProvider
from src.providers.modelscope_provider import ModelScopeProvider

class ProviderFactory:
    """
    根据配置创建和管理 AI Provider 实例的工厂。
    """
    _instances: Dict[str, AIProvider] = {}

    @classmethod
    def get_provider(cls, channel_name: str) -> AIProvider:
        """
        获取或创建指定渠道的 Provider 单例。
        
        Args:
            channel_name: config.CHANNELS 中定义的渠道名称。
            
        Returns:
            AIProvider 实例。
            
        Raises:
            ValueError: 如果渠道配置缺失或无效。
        """
        if channel_name in cls._instances:
            return cls._instances[channel_name]

        channel_config = config.CHANNELS.get(channel_name)
        if not channel_config:
            raise ValueError(f"配置文件中未定义渠道 '{channel_name}'。")

        provider_type = channel_config.get("type") # YAML 中使用 type 字段
        api_key = channel_config.get("api_key")
        base_url = channel_config.get("base_url")

        if not api_key:
             # 仅作为警告日志可能更好，但我们还没有设置日志记录器。
             # 我们继续执行，Provider 可能会稍后失败，或者依赖环境变量（如果库支持）。
             pass

        if provider_type == "openai":
            instance = OpenAICompatibleProvider(api_key=api_key, base_url=base_url)
        elif provider_type == "aliyun":
            instance = AliyunProvider(api_key=api_key)
        elif provider_type == "modelscope":
            instance = ModelScopeProvider(api_key=api_key, base_url=base_url)
        else:
            # 其他 Provider 类型的扩展点
            raise ValueError(f"渠道 '{channel_name}' 的提供商类型 '{provider_type}' 未知。")

        cls._instances[channel_name] = instance
        return instance
