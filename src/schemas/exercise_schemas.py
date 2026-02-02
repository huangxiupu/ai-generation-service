from typing import List, Optional, Union, Dict, Any, Literal
from pydantic import BaseModel, Field
from .enums import GradeLevel, DifficultyLevel, ExerciseType, AssetType

# 基础模型：通用结构

class AssetSpec(BaseModel):
    """资源生成规格定义"""
    id: str
    target_path: str = Field(..., description="JSON path to inject the asset URL")
    type: AssetType
    prompt: Optional[str] = Field(None, description="Image generation prompt")
    content: Optional[str] = Field(None, description="Text content for TTS or audio generation")
    params: Optional[Dict[str, Any]] = Field(None, description="Additional parameters")

class BaseGrading(BaseModel):
    """所有练习的基础评分结构。"""
    explanation: Optional[str] = Field(None, description="正确答案的解析")

class BaseGeneration(BaseModel):
    """基础生成元数据。"""
    grade_levels: Optional[List[GradeLevel]] = Field(None, description="目标年级，例如 ['1A', '1B']")
    difficulty: DifficultyLevel = Field(..., description="难度等级")
    keywords: Optional[List[str]] = Field(None, description="本练习关注的关键词")
    asset_specs: Optional[List[AssetSpec]] = Field(None, description="资源生成规格列表")

class BaseExerciseContent(BaseModel):
    """具有通用音频支持 (ESL) 的基础内容结构。"""
    type: ExerciseType = Field(..., description="练习类型")
    instruction: Optional[str] = Field(None, description="给学生的指令文本")
    instruction_audio: Optional[str] = Field(None, description="指令文本的 TTS 音频 URL")
    question: Optional[str] = Field(None, description="主要问题文本")
    question_audio: Optional[str] = Field(None, description="问题文本的 TTS 音频 URL")
    hints: Optional[List[str]] = Field(None, description="给学生的提示")

# --- 类型 A：纯文本（支持音频） ---


# --- 类型 A：纯文本（支持音频） ---

class MCQTextOption(BaseModel):
    text: str
    audio_url: Optional[str] = Field(None, description="该选项的 TTS 音频")

class MCQTextContent(BaseExerciseContent):
    options: List[MCQTextOption]
    pass

class MCQTextGrading(BaseGrading):
    answer_key: int = Field(..., description="正确答案的 0 基索引")

class MCQTextExercise(BaseModel):
    content: MCQTextContent
    grading: MCQTextGrading
    generation: BaseGeneration


class TrueFalseContent(BaseExerciseContent):
    statement: str
    statement_audio: Optional[str] = Field(None, description="陈述句的 TTS 音频")

class TrueFalseGrading(BaseGrading):
    answer_key: bool

class TrueFalseExercise(BaseModel):
    content: TrueFalseContent
    grading: TrueFalseGrading
    generation: BaseGeneration


class FillInBlanksContent(BaseExerciseContent):
    text: str = Field(..., description="带有 {{blank}} 占位符的文本")
    text_audio: Optional[str] = Field(None, description="文本音频（空格处静音或发哔声）")
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
    answer_key: List[str] = Field(..., description="正确顺序的项目 ID 列表")
    correct_sentence: str
    correct_audio: Optional[str] = Field(None, description="完整正确句子的音频（用于强化学习）")

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
    answer_key: List[str] = Field(..., description="正确顺序的项目 ID 列表")

class SequenceOrderingExercise(BaseModel):
    content: SequenceOrderingContent
    grading: SequenceOrderingGrading
    generation: BaseGeneration


class ErrorCorrectionContent(BaseExerciseContent):
    incorrect_sentence: str
    incorrect_audio: Optional[str] = None

class ErrorCorrectionGrading(BaseGrading):
    answer_key: str = Field(..., description="修正后的句子")
    correct_audio: Optional[str] = Field(None, description="正确句子的音频")

class ErrorCorrectionExercise(BaseModel):
    content: ErrorCorrectionContent
    grading: ErrorCorrectionGrading
    generation: BaseGeneration


class TableCompletionContent(BaseExerciseContent):
    headers: List[str]
    rows: List[List[str]] = Field(..., description="带有 {{blank}} 占位符的行")

class TableCompletionGrading(BaseGrading):
    answer_key: List[str] = Field(..., description="按行优先顺序填充空格的答案")

class TableCompletionExercise(BaseModel):
    content: TableCompletionContent
    grading: TableCompletionGrading
    generation: BaseGeneration


class ShortAnswerContent(BaseExerciseContent):
    pass # 使用标准 question/question_audio

class ShortAnswerKey(BaseModel):
    keywords: List[str]
    model_answer: str

class ShortAnswerGrading(BaseGrading):
    answer_key: ShortAnswerKey = Field(..., description="参考答案和关键词")

class ShortAnswerExercise(BaseModel):
    content: ShortAnswerContent
    grading: ShortAnswerGrading
    generation: BaseGeneration


class WritingPromptContent(BaseExerciseContent):
    title: str
    prompt: str
    prompt_audio: Optional[str] = None
    min_words: Optional[int] = None

class WritingPromptKey(BaseModel):
    criteria: List[str]

class WritingPromptGrading(BaseGrading):
    answer_key: WritingPromptKey = Field(..., description="评分标准")

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


# --- 类型 B：文本 + 图像（视觉） ---

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
    pass

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
    pass

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

class RolePlayKey(BaseModel):
    criteria: List[str]

class RolePlayGrading(BaseGrading):
    answer_key: RolePlayKey

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
    voice_id: Optional[str] = Field(None, description="Generic voice role ('narrator', 'male', 'female'). Provider-specific IDs are forbidden.")

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
    voice_id: Optional[str] = Field(None, description="Generic voice role ('narrator', 'male', 'female'). Provider-specific IDs are forbidden.")

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
    ExerciseType.MCQ_TEXT: MCQTextExercise,
    ExerciseType.MCQ_IMAGE: MCQImageExercise,
    ExerciseType.TRUE_FALSE: TrueFalseExercise,
    ExerciseType.FILL_IN_BLANKS: FillInBlanksExercise,
    ExerciseType.SENTENCE_ORDERING: SentenceOrderingExercise,
    ExerciseType.SEQUENCE_ORDERING: SequenceOrderingExercise,
    ExerciseType.ERROR_CORRECTION: ErrorCorrectionExercise,
    ExerciseType.TABLE_COMPLETION: TableCompletionExercise,
    ExerciseType.SHORT_ANSWER: ShortAnswerExercise,
    ExerciseType.WRITING_PROMPT: WritingPromptExercise,
    ExerciseType.CATEGORIZATION: CategorizationExercise,
    ExerciseType.MATCHING: MatchingExercise,
    ExerciseType.ROLE_PLAY_PROMPT: RolePlayExercise,
    ExerciseType.TEXT_SHADOWING: TextShadowingExercise,
    ExerciseType.LISTENING_COMPREHENSION: ListeningComprehensionExercise,
    ExerciseType.PHONICS_PRACTICE: PhonicsPracticeExercise,
}

# Helper to get JSON Schema
SCHEMAS = {k: v.model_json_schema() for k, v in EXERCISE_MODELS.items()}
