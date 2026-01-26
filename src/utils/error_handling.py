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
    Attempt to repair and parse a JSON string.
    """
    try:
        # First try standard parse
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            # Try repair
            repaired_str = repair_json(json_str)
            return json.loads(repaired_str)
        except Exception as e:
            raise JSONParseError(f"Failed to repair JSON: {str(e)}")

# Retry decorator configuration
# Retry up to 2 times (total 3 attempts) with exponential backoff
retry_on_api_error = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception) # Narrow this down in production to specific API errors
)
