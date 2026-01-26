import json
from src.config import config
from src.factory import ProviderFactory
from src.utils.prompt_registry import PromptRegistry
from src.utils.validation import SchemaValidator
from src.utils.error_handling import retry_on_api_error, repair_and_parse_json, JSONParseError
from src.schemas.exercise_schemas import SCHEMAS

class RealTextGenService:
    def __init__(self):
        self.provider = ProviderFactory.get_provider(config.CHANNEL_TEXT)
        self.prompt_registry = PromptRegistry()
        self.validator = SchemaValidator()

    @retry_on_api_error
    def generate(self, context: dict, exercise_type: str, generation_config: dict = None):
        """
        使用 LLM 生成练习题内容。
        """
        if generation_config is None:
            generation_config = {}
            
        model = generation_config.get("model", config.MODEL_TEXT)
        
        # 1. 准备提示词 (Prompts)
        system_prompt = self.prompt_registry.get_system_prompt()
        
        # 将 schema 注入到用户 prompt 上下文中
        schema_json = json.dumps(SCHEMAS.get(exercise_type, {}), indent=2)
        context['schema_json'] = schema_json
        
        user_prompt_template = f"user_prompts/{exercise_type}.j2"
        user_prompt = self.prompt_registry.render(user_prompt_template, **context)
        
        # 2. 调用 LLM
        content = self.provider.chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=generation_config.get("temperature", config.DEFAULT_TEMPERATURE),
            timeout=config.API_TIMEOUT
        )
        
        # 3. 解析和修复 JSON
        try:
            data = repair_and_parse_json(content)
        except JSONParseError as e:
            # 如果修复失败，我们可能希望抛出异常以触发重试，或者记录日志并失败。
            # retry 装饰器会处理异常。
            raise e
            
        # 4. 验证 Schema
        self.validator.validate(data, exercise_type)
        
        return data

class MockTextGenService:
    def generate(self, context: dict, exercise_type: str, generation_config: dict = None):
        """
        返回用于测试的模拟数据。
        """
        if exercise_type == "mcq_text":
            return {
                "content": {
                    "question": "MOCK: What is the capital of France?",
                    "options": ["Paris", "London", "Berlin", "Madrid"],
                    "hints": ["It starts with P"]
                },
                "grading": {
                    "answer_key": 0,
                    "explanation": "Paris is the capital of France."
                },
                "generation": {
                    "grade_levels": ["1A"],
                    "difficulty": "easy",
                    "keywords": ["mock", "geography"]
                }
            }
        elif exercise_type == "mcq_image":
            return {
                "content": {
                    "question": "MOCK: Which image shows a cat?",
                    "options": [
                        {"id": "opt1", "image_url": "https://placehold.co/200x200?text=Cat", "caption": "A cat"},
                        {"id": "opt2", "image_url": "https://placehold.co/200x200?text=Dog", "caption": "A dog"}
                    ],
                    "hints": ["Meow"]
                },
                "grading": {
                    "answer_key": 0,
                    "explanation": "Option 1 is a cat."
                },
                "generation": {
                    "grade_levels": ["1A"],
                    "options_prompts": ["cute cat illustration", "cute dog illustration"]
                }
            }
        elif exercise_type == "true_false":
            return {
                "content": {
                    "statement": "MOCK: The sky is blue.",
                    "hints": ["Look up"]
                },
                "grading": {
                    "answer_key": True,
                    "explanation": "The sky appears blue due to Rayleigh scattering."
                },
                "generation": {
                    "grade_levels": ["1A"]
                }
            }
        elif exercise_type == "fill_in_blanks":
            return {
                "content": {
                    "text": "MOCK: The {{blank}} is shining.",
                    "original_text": "The sun is shining.",
                    "word_bank": ["sun", "moon", "star"],
                    "hints": ["Daytime star"]
                },
                "grading": {
                    "answer_key": ["sun"]
                },
                "generation": {
                    "grade_levels": ["1A"]
                }
            }
        else:
            # 未知类型的回退
            return {
                "error": f"Mock data for {exercise_type} not implemented",
                "content": {},
                "grading": {"answer_key": None}
            }
