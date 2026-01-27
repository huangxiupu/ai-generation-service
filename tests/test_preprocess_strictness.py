import pytest
from pydantic import ValidationError
from src.orchestrator.context_engine import ContextEngine
from src.schemas.enums import SectionType, BlockType

def test_preprocess_strict_enums_validation():
    engine = ContextEngine()
    
    # Valid data
    valid_section = {"section_type": "vocabulary_scene", "content": {"conversation": []}}
    valid_book = {"title": "Test Book", "grade_level": "1A"}
    valid_unit = {"unit_id": 1, "learning_objectives": {}}
    
    context = engine.normalize(valid_section, valid_book, valid_unit)
    assert context.meta.section_type == SectionType.VOCABULARY_SCENE
    assert context.meta.grade_level == "1A" # Enum coercion works

    # Invalid Section Type
    invalid_section = {"section_type": "super_fun_activity", "content": {}}
    
    with pytest.raises(ValidationError) as excinfo:
        engine.normalize(invalid_section, valid_book, valid_unit)
    
    assert "Input should be 'vocabulary_scene'" in str(excinfo.value) or "Input should be" in str(excinfo.value)
    print("\nSuccessfully caught invalid SectionType!")

    # Invalid Grade Level
    invalid_book = {"title": "Test Book", "grade_level": "Grade 13"}
    
    with pytest.raises(ValidationError) as excinfo:
        engine.normalize(valid_section, invalid_book, valid_unit)
        
    assert "Input should be '1A'" in str(excinfo.value) or "Input should be" in str(excinfo.value)
    print("\nSuccessfully caught invalid GradeLevel!")

if __name__ == "__main__":
    test_preprocess_strict_enums_validation()
