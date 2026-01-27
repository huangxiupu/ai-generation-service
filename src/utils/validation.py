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
        Attempts to repair malformed JSON strings common in LLM outputs.
        Handles:
        - Markdown code blocks (```json ... ```)
        - Trailing commas (simple cases)
        """
        if not isinstance(json_str, str):
            # If it's already a dict/list, return it
            return json_str
            
        # 1. Remove Markdown code blocks
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', json_str)
        if match:
            json_str = match.group(1)
            
        json_str = json_str.strip()
        
        # 2. Try parsing
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
            
        # 3. Try to fix trailing commas which are common: Remove ,] -> ] and ,} -> }
        json_str_fixed = re.sub(r',\s*([\]}])', r'\1', json_str)
        
        try:
            return json.loads(json_str_fixed)
        except json.JSONDecodeError:
             pass

        # If all fails, raise original error or custom error
        raise ValueError(f"Failed to parse JSON: {json_str[:100]}...")

    @staticmethod
    def validate_model(data: Union[Dict, str], exercise_type: Union[ExerciseType, str]) -> BaseModel:
        """
        Validate data against the Pydantic model for the given exercise_type.
        Supports automatic JSON repair if data is a string.
        """
        # Resolve ExerciseType enum if string passed
        if isinstance(exercise_type, str):
            try:
                exercise_type = ExerciseType(exercise_type)
            except ValueError:
                # If invalid enum value, might raise error or let EXERCISE_MODELS lookup fail
                pass

        model_class = EXERCISE_MODELS.get(exercise_type)
        
        if not model_class:
            raise ValueError(f"No schema found for exercise type: {exercise_type}")

        # Parse string if needed
        if isinstance(data, str):
            data = SchemaValidator.repair_json(data)

        # Validate
        try:
            return model_class.model_validate(data)
        except ValidationError as e:
            # Re-raise as ValueError to maintain interface consistency or expose detailed error
            raise ValueError(f"Validation failed for {exercise_type}: {e}")

    @staticmethod
    def validate(data: dict, exercise_type: str):
        """
        Legacy validation method.
        """
        SchemaValidator.validate_model(data, exercise_type)
        return True
