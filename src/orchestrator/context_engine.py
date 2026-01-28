import json
from typing import Dict, Any, Optional, List
from ..schemas.orchestration import (
    StandardizedContext, MetaInfo, PedagogicalGoals, 
    NormalizedContent, Block, ContextProcessingResult, ExerciseRecommendation
)
from ..schemas.enums import SectionType, BlockType

# Assuming BaseTextGenService is defined in src.services.text_gen
# If not, we might need to adjust the import or type hint.
try:
    from ..services.text_gen import BaseTextGenService
except ImportError:
    BaseTextGenService = Any

class ContextEngine:
    """
    上下文引擎负责将教材的原始 JSON 数据转换为下游生成任务可预测的 StandardizedContext。

    架构说明 - SectionType 与 BlockType：
    ---------------------------------------------
    我们刻意将 `SectionType`（源领域）与 `BlockType`（目标领域）解耦。
    - SectionType 反映了教材的教学意图和布局（例如：词汇场景、叙述）。
    - BlockType 反映了 AI 处理的原子数据结构（例如：对话、词汇列表）。
    
    映射策略：
    - 单个 Section（例如：VOCABULARY_SCENE）通常被分解为多个 Block
      （例如：CONVERSATION + VOCABULARY_LIST + SPATIAL_MAP）。
    - 这允许在不同的教学背景下灵活复用原子结构。
    """
    def __init__(self, text_gen_service: Optional[BaseTextGenService] = None):
        self.text_gen_service = text_gen_service

    def normalize(self, section_data: Dict[str, Any], book_meta: Dict[str, Any], unit_meta: Dict[str, Any], section_id: Optional[str] = None) -> ContextProcessingResult:
        """
        标准化原始章节数据为 StandardizedContext 并推荐练习的主要入口点。
        
        参数:
            section_data: 特定章节的 JSON 字典。
            book_meta: 书籍元数据的 JSON 字典。
            unit_meta: 单元元数据的 JSON 字典。
            section_id: 章节的可选数据库 ID。
        """
        # 第一层：确定性的元数据提取
        meta = self._extract_meta(section_data, book_meta, unit_meta, section_id)
        
        # 第二层：鲁棒的目标提取
        # 教学目标通常在单元层级
        goals = self._extract_objectives(unit_meta.get("learning_objectives", {}))
        
        # 第三层：语义内容处理与推荐
        # 这会将内容提取为语义块并推荐练习。
        if self.text_gen_service:
            normalized_content, recommendations = self._process_content_with_llm(section_data, book_meta, unit_meta)
        else:
            normalized_content = self._process_content_heuristic(section_data)
            recommendations = []

        standardized_context = StandardizedContext(
            meta=meta,
            pedagogical_goals=goals,
            normalized_content=normalized_content
        )

        return ContextProcessingResult(
            standardized_context=standardized_context,
            recommendations=recommendations
        )

    def _extract_meta(self, section: Dict[str, Any], book: Dict[str, Any], unit: Dict[str, Any], section_id: Optional[str] = None) -> MetaInfo:
        return MetaInfo(
            book_title=book.get("title", "unknown"),
            unit_number=unit.get("unit_number", 0),
            unit_title=unit.get("title", ""),
            section_id=section_id,
            section_title=section.get("title", ""),
            section_code=section.get("section_code", ""),
            grade_level=book.get("grade_level"),
            section_type=section.get("section_type", SectionType.UNKNOWN)
        )

    def _extract_objectives(self, objectives: Dict[str, Any]) -> PedagogicalGoals:
        # 鲁棒提取，默认空列表
        return PedagogicalGoals(
            vocabulary=objectives.get("vocabulary_focus", []),
            grammar=objectives.get("grammar_focus", []),
            phonics=objectives.get("phonics_focus", [])
        )

    def _process_content_with_llm(self, section_data: Dict[str, Any], book_meta: Dict[str, Any], unit_meta: Dict[str, Any]) -> tuple[NormalizedContent, List[ExerciseRecommendation]]:
        """
        使用 LLM 标准化内容并生成推荐。
        """
        print(f"[ContextEngine] 准备 LLM 请求数据...")
        llm_context = {
            "section_type": section_data.get("section_type"),
            "content": section_data.get("content"),
            "visual_context": section_data.get("visual_context"),
            "book_meta": book_meta,
            "unit_meta": unit_meta
        }
        print(f"[ContextEngine] LLM Input Context:\n{json.dumps(llm_context, ensure_ascii=False, indent=2)}")
        
        print(f"[ContextEngine] 正在调用 text_gen_service.normalize_context...")
        raw_result = self.text_gen_service.normalize_context(llm_context)
        print(f"[ContextEngine] LLM 返回原始结果:\n{json.dumps(raw_result, ensure_ascii=False, indent=2)}")
        
        # 解析 LLM 返回的 JSON
        print(f"[ContextEngine] 正在解析 LLM 结果为模型对象...")
        
        # 修正：LLM 输出是扁平结构，直接包含 summary/visual_scene/blocks，而不是嵌套在 normalized_content 下
        # 旧逻辑: normalized_content = NormalizedContent(**raw_result.get("normalized_content", {}))
        
        normalized_content = NormalizedContent(
            summary=raw_result.get("summary", ""),
            visual_scene=raw_result.get("visual_scene", ""),
            blocks=raw_result.get("blocks", [])
        )
        
        recommendations = []
        for rec_data in raw_result.get("recommendations", []):
            recommendations.append(ExerciseRecommendation(**rec_data))
        
        print(f"[ContextEngine] 解析完成，包含 {len(recommendations)} 条推荐")
        return normalized_content, recommendations

    def _process_content_heuristic(self, section_data: Dict[str, Any]) -> NormalizedContent:
        """
        使用启发式方法将章节内容转换为标准化块。
        """
        raw_content = section_data.get("content", {})
        visual_context = section_data.get("visual_context", "")
        
        blocks = []
        
        # 第三层的启发式映射（实现简化版）
        
        # 1. 会话 / 对话
        if "conversation" in raw_content:
            blocks.append(Block(semantic_type=BlockType.CONVERSATION, payload={"turns": raw_content["conversation"]}))
        elif "dialogue" in raw_content:
            blocks.append(Block(semantic_type=BlockType.CONVERSATION, payload={"turns": raw_content["dialogue"]}))
             
        # 2. 词汇列表
        if "vocabulary_items" in raw_content:
            blocks.append(Block(semantic_type=BlockType.VOCABULARY_LIST, payload={"items": raw_content["vocabulary_items"]}))
            
        # 3. 语音 (Phonics)
        if "sound" in raw_content:
            blocks.append(Block(semantic_type=BlockType.PHONICS_RULE, payload={
                "target_sound": raw_content.get("sound"),
                "words": raw_content.get("words", [])
            }))
        elif "sounds" in raw_content:
             blocks.append(Block(semantic_type=BlockType.PHONICS_RULE, payload={
                "sounds": raw_content.get("sounds")
            }))
            
        # 4. 回退 / 通用
        # 如果未找到特定结构，则包装整个内容
        if not blocks:
            blocks.append(Block(semantic_type=BlockType.GENERIC, payload=raw_content))

        return NormalizedContent(
            summary=f"Content derived from {section_data.get('section_type', 'unknown')} section.",
            visual_scene=visual_context,
            blocks=blocks
        )
