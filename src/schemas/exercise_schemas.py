
# This file contains the JSON schemas for exercise validation.
# Extracted from seed_exercise_types.sql

SCHEMAS = {
    "mcq_text": {
        "type": "object",
        "properties": {
            "content": {
                "type": "object",
                "properties": {
                    "hints": { "type": "array", "items": { "type": "string" }, "title": "Hints" },
                    "question": { "type": "string", "title": "Question Text" },
                    "options": {
                        "type": "array",
                        "items": { "type": "string" },
                        "title": "Options",
                        "minItems": 2
                    }
                },
                "required": ["question", "options"]
            },
            "grading": {
                "type": "object",
                "properties": {
                    "answer_key": { "type": "integer", "title": "Index of Correct Answer (0-based)" },
                    "explanation": { "type": "string", "title": "Explanation" }
                },
                "required": ["answer_key"]
            },
            "generation": {
                "type": "object",
                "properties": {
                    "grade_levels": { 
                        "type": "array", 
                        "items": { "type": "string", "enum": ["1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B", "5A", "5B", "6A", "6B"] },
                        "title": "Target Grade Levels"
                    },
                    "difficulty": { "type": "string" },
                    "keywords": { "type": "array", "items": { "type": "string" } }
                }
            }
        },
        "required": ["content", "grading"]
    },
    "mcq_image": {
        "type": "object",
        "properties": {
            "content": {
                "type": "object",
                "properties": {
                    "hints": { "type": "array", "items": { "type": "string" }, "title": "Hints" },
                    "question": { "type": "string", "title": "Question/Word" },
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": { "type": "string" },
                                "image_url": { "type": "string" },
                                "caption": { "type": "string" }
                            },
                            "required": ["id", "image_url"]
                        },
                        "minItems": 2
                    }
                },
                "required": ["question", "options"]
            },
            "grading": {
                "type": "object",
                "properties": {
                    "answer_key": { "type": "integer", "title": "Index of Correct Answer (0-based)" },
                    "explanation": { "type": "string" }
                },
                "required": ["answer_key"]
            },
            "generation": {
                "type": "object",
                "properties": {
                    "grade_levels": { 
                        "type": "array", 
                        "items": { "type": "string", "enum": ["1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B", "5A", "5B", "6A", "6B"] }
                    },
                    "options_prompts": {
                        "type": "array",
                        "items": { "type": "string", "description": "Image generation prompts for each option" }
                    }
                }
            }
        },
        "required": ["content", "grading"]
    },
    "true_false": {
        "type": "object",
        "properties": {
            "content": {
                "type": "object",
                "properties": {
                    "hints": { "type": "array", "items": { "type": "string" }, "title": "Hints" },
                    "statement": { "type": "string", "title": "Statement" }
                },
                "required": ["statement"]
            },
            "grading": {
                "type": "object",
                "properties": {
                    "answer_key": { "type": "boolean", "title": "Is True?" },
                    "explanation": { "type": "string" }
                },
                "required": ["answer_key"]
            },
            "generation": {
                "type": "object",
                "properties": {
                    "grade_levels": { 
                        "type": "array", 
                        "items": { "type": "string", "enum": ["1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B", "5A", "5B", "6A", "6B"] }
                    }
                }
            }
        },
        "required": ["content", "grading"]
    },
    "fill_in_blanks": {
        "type": "object",
        "properties": {
            "content": {
                "type": "object",
                "properties": {
                    "hints": { "type": "array", "items": { "type": "string" }, "title": "Hints" },
                    "text": { "type": "string", "title": "Text with {{blank}} placeholders" },
                    "original_text": { "type": "string", "title": "Original text before blanks" },
                    "word_bank": {
                        "type": "array",
                        "items": { "type": "string" },
                        "title": "Word Bank (Optional distractors)"
                    }
                },
                "required": ["text"]
            },
            "grading": {
                "type": "object",
                "properties": {
                    "answer_key": {
                        "type": "array",
                        "items": { "type": "string" },
                        "title": "Correct Answers (in order)"
                    }
                },
                "required": ["answer_key"]
            },
            "generation": {
                "type": "object",
                "properties": {
                    "grade_levels": { 
                        "type": "array", 
                        "items": { "type": "string", "enum": ["1A", "1B", "2A", "2B", "3A", "3B", "4A", "4B", "5A", "5B", "6A", "6B"] }
                    }
                }
            }
        },
        "required": ["content", "grading"]
    }
    # Add other schemas as needed...
}
