import jsonschema
from jsonschema import validate
from src.schemas.exercise_schemas import SCHEMAS

class SchemaValidator:
    @staticmethod
    def validate(data: dict, exercise_type: str):
        """
        Validate the data against the schema for the given exercise_type.
        Raises jsonschema.exceptions.ValidationError if invalid.
        """
        schema = SCHEMAS.get(exercise_type)
        if not schema:
            raise ValueError(f"No schema found for exercise type: {exercise_type}")
            
        validate(instance=data, schema=schema)
        return True
