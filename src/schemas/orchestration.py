from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field
from .enums import SectionType, BlockType, AssetType, GradeLevel, ExerciseType

# --- Standardized Context Models ---

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
    vocabulary: List[str] = Field(default_factory=list)
    grammar: List[str] = Field(default_factory=list)
    phonics: List[str] = Field(default_factory=list)

class Block(BaseModel):
    semantic_type: BlockType
    payload: Dict[str, Any]

class NormalizedContent(BaseModel):
    summary: str = ""
    visual_scene: str = ""
    blocks: List[Block] = Field(default_factory=list)

class StandardizedContext(BaseModel):
    meta: MetaInfo
    pedagogical_goals: PedagogicalGoals
    normalized_content: NormalizedContent

class ExerciseRecommendation(BaseModel):
    exercise_type: ExerciseType
    reason: str
    suggested_difficulty: str = "Medium"

class ContextProcessingResult(BaseModel):
    standardized_context: StandardizedContext
    recommendations: List[ExerciseRecommendation] = Field(default_factory=list)

# --- Exercise Generation Models ---

class AssetSpec(BaseModel):
    id: str
    target_path: str  # JSON Path, e.g., "items[0].options[0].image_url"
    type: AssetType
    prompt: Optional[str] = None  # for Image
    content: Optional[str] = None # for Audio
    params: Dict[str, Any] = Field(default_factory=dict)

class ExerciseSkeleton(BaseModel):
    title: str
    instructions: str
    items: List[Dict[str, Any]]
    asset_specs: List[AssetSpec] = Field(default_factory=list)
