import pytest
import json
from src.schemas.enums import SectionType, BlockType, ExerciseType, GradeLevel
from src.schemas.orchestration import StandardizedContext, MetaInfo, NormalizedContent
from src.schemas.exercise_schemas import MCQTextExercise, BaseGeneration
from src.utils.validation import SchemaValidator

def test_enums_exist_and_have_values():
    assert SectionType.VOCABULARY_SCENE == "vocabulary_scene"
    assert BlockType.CONVERSATION == "conversation"
    assert ExerciseType.MCQ_TEXT == "mcq_text"
    assert GradeLevel.G1A == "1A"

def test_standardized_context_validation():
    # Test valid data
    valid_data = {
        "meta": {
            "book_id": "test_book",
            "grade_level": "1A", # Should accept string value of enum
            "unit_id": 1,
            "section_type": "vocabulary_scene"
        },
        "pedagogical_goals": {},
        "normalized_content": {
            "blocks": [
                {
                    "semantic_type": "conversation",
                    "payload": {"turns": []}
                }
            ]
        }
    }
    context = StandardizedContext.model_validate(valid_data)
    assert context.meta.section_type == SectionType.VOCABULARY_SCENE
    assert context.meta.grade_level == GradeLevel.G1A
    assert context.normalized_content.blocks[0].semantic_type == BlockType.CONVERSATION

def test_repair_json():
    # Test markdown stripping
    malformed = """
    Here is the JSON:
    ```json
    {"key": "value"}
    ```
    """
    repaired = SchemaValidator.repair_json(malformed)
    assert repaired == {"key": "value"}

    # Test trailing comma
    malformed_comma = '{"key": "value",}'
    repaired_comma = SchemaValidator.repair_json(malformed_comma)
    assert repaired_comma == {"key": "value"}
    
    malformed_list_comma = '["value",]'
    repaired_list_comma = SchemaValidator.repair_json(malformed_list_comma)
    assert repaired_list_comma == ["value"]

def test_validate_model_success():
    data = {
        "content": {
            "options": ["A", "B"]
        },
        "grading": {
            "answer_key": 0
        },
        "generation": {
            "grade_levels": ["1A"]
        }
    }
    model = SchemaValidator.validate_model(data, ExerciseType.MCQ_TEXT)
    assert isinstance(model, MCQTextExercise)
    assert model.generation.grade_levels[0] == GradeLevel.G1A

def test_validate_model_failure():
    # Missing required field
    data = {
        "content": {}
    }
    with pytest.raises(ValueError, match="Validation failed"):
        SchemaValidator.validate_model(data, ExerciseType.MCQ_TEXT)
