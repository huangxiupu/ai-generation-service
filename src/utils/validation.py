import json
import re
from typing import Dict, Any, Type, Union
from pydantic import BaseModel, ValidationError
from src.schemas.exercise_schemas import EXERCISE_MODELS
from src.schemas.enums import ExerciseType

class SchemaValidator:
    
    @staticmethod
    def repair_json(json_str: str) -> Dict[str, Any]:
        """
        尝试修复 LLM 输出中常见的格式错误的 JSON 字符串。
        处理情况：
        - Markdown 代码块 (```json ... ```)
        - 尾随逗号（简单情况）
        """
        if not isinstance(json_str, str):
            # 如果已经是字典或列表，直接返回
            return json_str
            
        # 1. 移除 Markdown 代码块
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_str)
        if match:
            json_str = match.group(1)
            
        json_str = json_str.strip()
        
        # 2. 尝试解析
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
            
        # 3. 尝试修复常见的尾随逗号：移除 ,] -> ] 和 ,} -> }
        json_str_fixed = re.sub(r',\s*([\]}])', r'\1', json_str)
        
        try:
            return json.loads(json_str_fixed)
        except json.JSONDecodeError:
             pass

        # 如果全部失败，抛出原始错误或自定义错误
        raise ValueError(f"无法解析 JSON: {json_str[:100]}...")

    @staticmethod
    def validate_model(data: Union[Dict, str], exercise_type: Union[ExerciseType, str]) -> BaseModel:
        """
        根据给定 exercise_type 的 Pydantic 模型验证数据。
        如果数据是字符串，支持自动 JSON 修复。
        """
        # 如果传入的是字符串，解析 ExerciseType 枚举
        if isinstance(exercise_type, str):
            try:
                exercise_type = ExerciseType(exercise_type)
            except ValueError:
                # 如果是无效的枚举值，可能会抛出错误或让 EXERCISE_MODELS 查找失败
                pass

        model_class = EXERCISE_MODELS.get(exercise_type)
        
        if not model_class:
            raise ValueError(f"未找到练习类型对应的 schema: {exercise_type}")

        # 如果需要，解析字符串
        if isinstance(data, str):
            data = SchemaValidator.repair_json(data)

        # 验证
        try:
            return model_class.model_validate(data)
        except ValidationError as e:
            # 重新抛出为 ValueError 以保持接口一致性或暴露详细错误
            raise ValueError(f"验证失败 ({exercise_type}): {e}")

    @staticmethod
    def validate(data: dict, exercise_type: str):
        """
        旧版验证方法。
        """
        SchemaValidator.validate_model(data, exercise_type)
        return True
