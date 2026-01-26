import os
import re
import yaml
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def load_yaml_config(file_path):
    """
    加载 YAML 配置文件并解析环境变量占位符 ${VAR_NAME}
    """
    pattern = re.compile(r'\$\{([^}^{]+)\}')
    
    def env_var_constructor(loader, node):
        value = loader.construct_scalar(node)
        match = pattern.match(value)
        if match:
            env_var = match.group(1)
            return os.environ.get(env_var, '')
        return value

    # 添加隐式解析器以处理 ${VAR} 格式
    yaml.add_implicit_resolver('!env', pattern, None, yaml.SafeLoader)
    yaml.add_constructor('!env', env_var_constructor, yaml.SafeLoader)

    with open(file_path, 'r', encoding='utf-8') as f:
        # 预处理内容，手动替换环境变量（因为 PyYAML 默认不支持隐式标签构造函数用于所有标量）
        content = f.read()
        def replace_env(match):
            env_name = match.group(1)
            return os.environ.get(env_name, '')
        
        expanded_content = pattern.sub(replace_env, content)
        return yaml.safe_load(expanded_content)

class Config:
    # 路径
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
    CONFIG_FILE = os.path.join(os.path.dirname(__file__), "ai_config.yaml")

    def __init__(self):
        # 加载 YAML 配置
        self.yaml_config = {}
        if os.path.exists(self.CONFIG_FILE):
            try:
                self.yaml_config = load_yaml_config(self.CONFIG_FILE)
            except Exception as e:
                print(f"Warning: Failed to load ai_config.yaml: {e}")
        
        # 基础设置
        self.ENABLE_MOCK = os.getenv("ENABLE_MOCK", "False").lower() == "true"
        self.DEFAULT_TEMPERATURE = 1.0
        self.MAX_RETRIES = 2
        self.API_TIMEOUT = 60.0

    @property
    def CHANNELS(self):
        return self.yaml_config.get("providers", {})

    @property
    def ROUTES(self):
        return self.yaml_config.get("routes", {})

    @property
    def CHANNEL_TEXT(self):
        return self.ROUTES.get("text", {}).get("provider", "zhipu")

    @property
    def CHANNEL_IMAGE(self):
        return self.ROUTES.get("image", {}).get("provider", "zhipu")

    @property
    def CHANNEL_AUDIO(self):
        return self.ROUTES.get("audio", {}).get("provider", "zhipu")

    @property
    def MODEL_TEXT(self):
        return self.ROUTES.get("text", {}).get("model", "glm-4")
        
    @property
    def MODEL_IMAGE(self):
        return self.ROUTES.get("image", {}).get("model", "cogview-3")
        
    @property
    def MODEL_AUDIO(self):
        return self.ROUTES.get("audio", {}).get("model", "glm-tts")

    # 兼容旧代码的 API Key 属性 (如果需要)
    @property
    def ZHIPU_API_KEY(self):
        return self.CHANNELS.get("zhipu", {}).get("api_key")

    def get_voice_id(self, role: str, channel: str) -> str:
        """
        根据业务角色和渠道获取实际的厂商 Voice ID。
        逻辑：
        1. 检查 routes.audio.voice_map_override (路由级别的特定覆盖)
        2. 检查 providers.{channel}.voice_map (提供商级别的默认映射)
        3. 回退到 role 本身
        """
        # 1. 检查路由级别的覆盖
        audio_route = self.ROUTES.get("audio", {})
        override_map = audio_route.get("voice_map_override", {})
        if role in override_map:
            return override_map[role]

        # 2. 检查提供商级别的映射
        provider_config = self.CHANNELS.get(channel, {})
        voice_map = provider_config.get("voice_map", {})
        if role in voice_map:
            return voice_map[role]

        # 3. 回退
        return role

config = Config()
