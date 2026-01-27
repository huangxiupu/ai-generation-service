from typing import List, Optional, Union, Dict, Any, Literal
from pydantic import BaseModel, Field

# Base Models for Common Structure

class BaseGrading(BaseModel):
    """Base grading structure for all exercises."""
    explanation: Optional[str] = Field(None, description="Explanation for the correct answer")

class BaseGeneration(BaseModel):
    """Base generation metadata."""
    grade_levels: Optional[List[str]] = Field(None, description="Target grade levels, e.g., ['1A', '1B']")
    difficulty: Optional[str] = Field(None, description="Difficulty level")
    keywords: Optional[List[str]] = Field(None, description="Keywords focused in this exercise")

class BaseExerciseContent(BaseModel):
    """Base content structure with Universal Audio Support (ESL)."""
    instruction: Optional[str] = Field(None, description="Instruction text for the student")
    instruction_audio: Optional[str] = Field(None, description="URL for the instruction TTS audio")
    question: Optional[str] = Field(None, description="Main question text")
    question_audio: Optional[str] = Field(None, description="URL for the question TTS audio")
    hints: Optional[List[str]] = Field(None, description="Hints for the student")

# --- Type A: Text-Only (with Audio Support) ---

class MCQTextOption(BaseModel):
    text: str
    audio_url: Optional[str] = Field(None, description="TTS audio for this option")

class MCQTextContent(BaseExerciseContent):
    options: List[str]  # Simplified for text-only, or use MCQTextOption if we want audio per option
    # Note: To support audio per option in simple text MCQ, we might want a complex object or just rely on main text.
    # The sample showed simple strings. Let's stick to strings for simple mcq_text options unless specified.
    # However, ESL expert says "options audio helpful". Let's support both or stick to simple for now and upgrade if needed.
    # Actually, let's keep options as List[str] to match sample, but maybe add "options_audio" list?
    # Better: List[Dict] is more flexible. Let's allow options to be objects in a separate type or just upgrade this.
    # The sample had: "options": ["Red", "Blue"]
    # Let's keep it simple for mcq_text but add a note.
    pass

class MCQTextGrading(BaseGrading):
    answer_key: int = Field(..., description="0-based index of correct answer")

class MCQTextExercise(BaseModel):
    content: MCQTextContent
    grading: MCQTextGrading
    generation: BaseGeneration


class TrueFalseContent(BaseExerciseContent):
    statement: str
    statement_audio: Optional[str] = Field(None, description="TTS audio for the statement")

class TrueFalseGrading(BaseGrading):
    answer_key: bool

class TrueFalseExercise(BaseModel):
    content: TrueFalseContent
    grading: TrueFalseGrading
    generation: BaseGeneration


class FillInBlanksContent(BaseExerciseContent):
    text: str = Field(..., description="Text with {{blank}} placeholders")
    text_audio: Optional[str] = Field(None, description="Audio of the text (with silence/beep for blanks)")
    original_text: str
    word_bank: Optional[List[str]] = None

class FillInBlanksGrading(BaseGrading):
    answer_key: List[str]

class FillInBlanksExercise(BaseModel):
    content: FillInBlanksContent
    grading: FillInBlanksGrading
    generation: BaseGeneration


class SentenceOrderingItem(BaseModel):
    id: str
    text: str
    audio_url: Optional[str] = None

class SentenceOrderingContent(BaseExerciseContent):
    scrambled_items: List[SentenceOrderingItem]

class SentenceOrderingGrading(BaseGrading):
    answer_key: List[str] = Field(..., description="List of item IDs in correct order")
    correct_sentence: str
    correct_audio: Optional[str] = Field(None, description="Audio of the full correct sentence (Reinforcement)")

class SentenceOrderingExercise(BaseModel):
    content: SentenceOrderingContent
    grading: SentenceOrderingGrading
    generation: BaseGeneration


class SequenceOrderingItem(BaseModel):
    id: str
    content: str
    audio_url: Optional[str] = None

class SequenceOrderingContent(BaseExerciseContent):
    items: List[SequenceOrderingItem]

class SequenceOrderingGrading(BaseGrading):
    answer_key: List[str] = Field(..., description="List of item IDs in correct order")

class SequenceOrderingExercise(BaseModel):
    content: SequenceOrderingContent
    grading: SequenceOrderingGrading
    generation: BaseGeneration


class ErrorCorrectionContent(BaseExerciseContent):
    incorrect_sentence: str
    incorrect_audio: Optional[str] = None

class ErrorCorrectionGrading(BaseGrading):
    answer_key: str = Field(..., description="Corrected sentence")
    correct_audio: Optional[str] = Field(None, description="Audio of the correct sentence")

class ErrorCorrectionExercise(BaseModel):
    content: ErrorCorrectionContent
    grading: ErrorCorrectionGrading
    generation: BaseGeneration


class TableCompletionContent(BaseExerciseContent):
    headers: List[str]
    rows: List[List[str]] = Field(..., description="Rows with {{blank}} placeholders")

class TableCompletionGrading(BaseGrading):
    answer_key: List[str] = Field(..., description="Answers filling the blanks in row-major order")

class TableCompletionExercise(BaseModel):
    content: TableCompletionContent
    grading: TableCompletionGrading
    generation: BaseGeneration


class ShortAnswerContent(BaseExerciseContent):
    pass # Uses standard question/question_audio

class ShortAnswerGrading(BaseGrading):
    answer_key: Dict[str, Any] = Field(..., description="Reference answer and keywords")

class ShortAnswerExercise(BaseModel):
    content: ShortAnswerContent
    grading: ShortAnswerGrading
    generation: BaseGeneration


class WritingPromptContent(BaseExerciseContent):
    title: str
    prompt: str
    prompt_audio: Optional[str] = None
    min_words: Optional[int] = None

class WritingPromptGrading(BaseGrading):
    answer_key: Dict[str, Any] = Field(..., description="Rubric")

class WritingPromptExercise(BaseModel):
    content: WritingPromptContent
    grading: WritingPromptGrading
    generation: BaseGeneration


class CategorizationCategory(BaseModel):
    id: str
    name: str
    audio_url: Optional[str] = None

class CategorizationItem(BaseModel):
    id: str
    text: str
    audio_url: Optional[str] = None

class CategorizationContent(BaseExerciseContent):
    categories: List[CategorizationCategory]
    items: List[CategorizationItem]

class CategorizationAnswer(BaseModel):
    item_id: str
    category_id: str

class CategorizationGrading(BaseGrading):
    answer_key: List[CategorizationAnswer]

class CategorizationExercise(BaseModel):
    content: CategorizationContent
    grading: CategorizationGrading
    generation: BaseGeneration


# --- Type B: Text + Image (Visual) ---

class MCQImageOption(BaseModel):
    id: str
    image_url: str
    caption: Optional[str] = None
    audio_url: Optional[str] = Field(None, description="Audio for the caption")

class MCQImageContent(BaseExerciseContent):
    options: List[MCQImageOption]

class MCQImageGrading(BaseGrading):
    answer_key: int

class MCQImageGeneration(BaseGeneration):
    options_prompts: Optional[List[str]] = None

class MCQImageExercise(BaseModel):
    content: MCQImageContent
    grading: MCQImageGrading
    generation: MCQImageGeneration


class MatchingItem(BaseModel):
    id: str
    text: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None # Pronunciation

class MatchingContent(BaseExerciseContent):
    left_items: List[MatchingItem]
    right_items: List[MatchingItem]

class MatchingPair(BaseModel):
    left_id: str
    right_id: str

class MatchingGrading(BaseGrading):
    answer_key: List[MatchingPair]

class MatchingGeneration(BaseGeneration):
    left_prompts: Optional[List[str]] = None
    right_prompts: Optional[List[str]] = None

class MatchingExercise(BaseModel):
    content: MatchingContent
    grading: MatchingGrading
    generation: MatchingGeneration


# --- Type C: Text + Audio (Core Audio) ---

class RolePlayContent(BaseExerciseContent):
    scenario: str
    scenario_audio: Optional[str] = Field(None, description="Audio describing the scenario or background ambience")
    roles: List[str]
    task: str
    useful_expressions: Optional[List[str]] = None

class RolePlayGrading(BaseGrading):
    answer_key: Dict[str, Any] # Rubric

class RolePlayExercise(BaseModel):
    content: RolePlayContent
    grading: RolePlayGrading
    generation: BaseGeneration


class TextShadowingSegment(BaseModel):
    text: str
    translation: Optional[str] = None
    audio_url: str = Field(..., description="The model audio for shadowing")
    timings: Optional[Dict[str, float]] = None

class TextShadowingContent(BaseExerciseContent):
    segments: List[TextShadowingSegment]

class TextShadowingGeneration(BaseGeneration):
    tts_text: Optional[str] = None
    voice_id: Optional[str] = None

class TextShadowingExercise(BaseModel):
    content: TextShadowingContent
    grading: BaseGrading # Usually null or N/A
    generation: TextShadowingGeneration


class ListeningComprehensionContent(BaseExerciseContent):
    audio_url: str = Field(..., description="The main listening audio file")
    options: List[str]

class ListeningComprehensionGrading(BaseGrading):
    answer_key: int

class ListeningComprehensionGeneration(BaseGeneration):
    audio_script: str
    voice_id: Optional[str] = None

class ListeningComprehensionExercise(BaseModel):
    content: ListeningComprehensionContent
    grading: ListeningComprehensionGrading
    generation: ListeningComprehensionGeneration


class PhonicsPracticeContent(BaseExerciseContent):
    word: str
    audio_url: str = Field(..., description="Pronunciation of the word")
    phonemes: List[str]

class PhonicsPracticeGrading(BaseGrading):
    answer_key: List[str]

class PhonicsPracticeGeneration(BaseGeneration):
    tts_text: Optional[str] = None

class PhonicsPracticeExercise(BaseModel):
    content: PhonicsPracticeContent
    grading: PhonicsPracticeGrading
    generation: PhonicsPracticeGeneration


# --- Registry ---

EXERCISE_MODELS = {
    "mcq_text": MCQTextExercise,
    "mcq_image": MCQImageExercise,
    "true_false": TrueFalseExercise,
    "fill_in_blanks": FillInBlanksExercise,
    "sentence_ordering": SentenceOrderingExercise,
    "sequence_ordering": SequenceOrderingExercise,
    "error_correction": ErrorCorrectionExercise,
    "table_completion": TableCompletionExercise,
    "short_answer": ShortAnswerExercise,
    "writing_prompt": WritingPromptExercise,
    "categorization": CategorizationExercise,
    "matching": MatchingExercise,
    "role_play_prompt": RolePlayExercise,
    "text_shadowing": TextShadowingExercise,
    "listening_comprehension": ListeningComprehensionExercise,
    "phonics_practice": PhonicsPracticeExercise,
}

# Helper to get JSON Schema
SCHEMAS = {k: v.model_json_schema() for k, v in EXERCISE_MODELS.items()}
