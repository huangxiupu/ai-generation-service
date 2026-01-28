import logging
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from json_repair import repair_json

logger = logging.getLogger(__name__)

class JSONParseError(Exception):
    pass

class SensitiveContentError(Exception):
    pass

def repair_and_parse_json(json_str: str) -> dict:
    """
    尝试修复并解析 JSON 字符串。
    """
    try:
        # 首先尝试标准解析
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            # 尝试修复
            repaired_str = repair_json(json_str)
            return json.loads(repaired_str)
        except Exception as e:
            raise JSONParseError(f"无法修复 JSON: {str(e)}")

# 重试装饰器配置
# 指数回退，最多重试 2 次（总共 3 次尝试）
retry_on_api_error = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception) # 在生产环境中应将其缩小为特定的 API 错误
)
