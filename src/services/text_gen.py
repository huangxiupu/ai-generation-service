import json
from typing import Protocol, Dict, Any, Optional
from src.config import config
from src.factory import ProviderFactory
from src.utils.logger import app_logger
from src.utils.prompt_registry import PromptRegistry
from src.utils.validation import SchemaValidator
from src.utils.error_handling import retry_on_api_error, repair_and_parse_json, JSONParseError
from src.schemas.exercise_schemas import SCHEMAS
from src.schemas.enums import GradeLevel, DifficultyLevel, AssetType, BlockType, ExerciseType

class BaseTextGenService(Protocol):
    def generate(self, context: dict, exercise_type: str, generation_config: dict = None) -> Dict[str, Any]:
        ...
    
    def normalize_context(self, context: dict) -> Dict[str, Any]:
        ...

class RealTextGenService:
    def __init__(self):
        self.provider = ProviderFactory.get_provider(config.CHANNEL_TEXT)
        self.prompt_registry = PromptRegistry()
        self.validator = SchemaValidator()

    def _get_enum_definitions(self) -> str:
        """
        获取枚举定义的字符串描述，以便注入到提示词中。
        """
        enums = [GradeLevel, DifficultyLevel, AssetType, BlockType, ExerciseType]
        lines = []
        for enum_cls in enums:
            name = enum_cls.__name__
            values = [f"'{v.value}'" for v in enum_cls]
            lines.append(f"- {name}: {', '.join(values)}")
        return "\n".join(lines)

    @retry_on_api_error
    def generate(self, context: dict, exercise_type: str, generation_config: dict = None):
        """
        使用 LLM 生成练习题内容。
        """
        app_logger.info(f"Starting exercise generation for type: {exercise_type}")
        if generation_config is None:
            generation_config = {}
            
        model = generation_config.get("model", config.MODEL_TEXT)
        
        # 1. 准备提示词 (Prompts)
        system_prompt = self.prompt_registry.get_system_prompt()
        
        # 将 schema 注入到用户 prompt 上下文中
        schema_json = json.dumps(SCHEMAS.get(exercise_type, {}), indent=2, ensure_ascii=False)
        context['schema_json'] = schema_json
        context['enum_definitions'] = self._get_enum_definitions()
        
        user_prompt_template = f"user_prompts/{exercise_type}.j2"
        user_prompt = self.prompt_registry.render(user_prompt_template, context=context, **context)
        
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

    @retry_on_api_error
    def normalize_context(self, context: dict) -> Dict[str, Any]:
        """
        使用 LLM 标准化 Section 内容并生成练习推荐。
        """
        app_logger.info("Starting context normalization")
        model = config.MODEL_TEXT
        
        # 1. 准备提示词
        # 使用基础系统提示词
        system_prompt = self.prompt_registry.get_system_prompt()
        
        # 渲染用户提示词
        user_prompt_template = "user_prompts/context_normalization.j2"
        context['enum_definitions'] = self._get_enum_definitions()
        user_prompt = self.prompt_registry.render(user_prompt_template, **context)
        
        # 2. 调用 LLM
        content = self.provider.chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2, # 使用较低温度以保证确定性
            timeout=config.API_TIMEOUT
        )
        
        # 3. 解析 JSON
        try:
            data = repair_and_parse_json(content)
        except JSONParseError as e:
            raise e
            
        # 4. 验证内容有效性
        # 如果 blocks 为空且 summary 为空，视为预处理失败
        if not data.get("blocks") and not data.get("summary"):
             raise ValueError("预处理失败：LLM 返回了空的内容（无摘要且无内容块），请重试。")

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
            # 未知类型的回退处理
            return {
                "error": f"尚未实现 {exercise_type} 的模拟数据",
                "content": {},
                "grading": {"answer_key": None}
            }

    def normalize_context(self, context: dict) -> Dict[str, Any]:
        """
        返回用于测试的模拟标准化数据。
        """
        return {
            "summary": "章节内容的模拟摘要。",
            "visual_scene": "模拟视觉描述。",
            "blocks": [
                {
                    "semantic_type": "conversation",
                    "payload": {
                        "turns": [
                            {"speaker": "A", "text": "Hello"},
                            {"speaker": "B", "text": "Hi there"}
                        ]
                    }
                }
            ],
            "recommendations": [
                {
                    "exercise_type": "mcq_text",
                    "reason": "有助于检查对对话的理解。",
                }
            ]
        }
