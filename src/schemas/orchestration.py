from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field
from .enums import SectionType, BlockType, AssetType, GradeLevel, ExerciseType, DifficultyLevel

# --- 标准化上下文模型 (Standardized Context Models) ---

class MetaInfo(BaseModel):
    book_title: str
    unit_number: Union[int, str]
    unit_title: str
    section_id: Optional[str] = None
    section_title: str
    section_code: str
    grade_level: GradeLevel
    section_type: SectionType = SectionType.UNKNOWN

class PedagogicalGoals(BaseModel):
    vocabulary: List[str] = Field(default_factory=list, description="词汇目标")
    grammar: List[str] = Field(default_factory=list, description="语法目标")
    phonics: List[str] = Field(default_factory=list, description="语音目标")

class Block(BaseModel):
    semantic_type: BlockType
    payload: Union[Dict[str, Any], List[Any]]

class NormalizedContent(BaseModel):
    summary: str = Field("", description="内容摘要")
    visual_scene: str = Field("", description="视觉场景描述")
    blocks: List[Block] = Field(default_factory=list, description="语义内容块列表")

class StandardizedContext(BaseModel):
    meta: MetaInfo
    pedagogical_goals: PedagogicalGoals
    normalized_content: NormalizedContent

class ExerciseRecommendation(BaseModel):
    exercise_type: ExerciseType
    reason: str
    suggested_difficulty: DifficultyLevel = Field(DifficultyLevel.MEDIUM, description="建议难度等级")

class ContextProcessingResult(BaseModel):
    standardized_context: StandardizedContext
    recommendations: List[ExerciseRecommendation] = Field(default_factory=list)

# --- 练习生成模型 (Exercise Generation Models) ---

class AssetSpec(BaseModel):
    id: str
    target_path: str  # JSON 路径，例如 "items[0].options[0].image_url"
    type: AssetType
    prompt: Optional[str] = None  # 用于图像生成
    content: Optional[str] = None # 用于音频生成
    params: Dict[str, Any] = Field(default_factory=dict, description="生成参数")

class ExerciseSkeleton(BaseModel):
    title: str
    instructions: str
    items: List[Dict[str, Any]]
    grading: Optional[Dict[str, Any]] = None
    generation: Optional[Dict[str, Any]] = None
    asset_specs: List[AssetSpec] = Field(default_factory=list, description="待生成资源规范")
