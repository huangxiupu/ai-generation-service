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
    The Context Engine is responsible for transforming raw textbook JSON data
    into a StandardizedContext that is predictable for downstream generation tasks.

    Architecture Note - SectionType vs BlockType:
    ---------------------------------------------
    We intentionally decouple `SectionType` (Source Domain) from `BlockType` (Target Domain).
    - SectionType reflects the pedagogical intent and layout of the textbook (e.g., Vocabulary Scene, Narrative).
    - BlockType reflects the atomic data structure for AI processing (e.g., Conversation, Vocabulary List).
    
    Mapping Strategy:
    - A single Section (e.g., VOCABULARY_SCENE) is often decomposed into multiple Blocks 
      (e.g., CONVERSATION + VOCABULARY_LIST + SPATIAL_MAP).
    - This allows for flexible re-use of atomic structures across different pedagogical contexts.
    """
    def __init__(self, text_gen_service: Optional[BaseTextGenService] = None):
        self.text_gen_service = text_gen_service

    def normalize(self, section_data: Dict[str, Any], book_meta: Dict[str, Any], unit_meta: Dict[str, Any], section_id: Optional[str] = None) -> ContextProcessingResult:
        """
        Main entry point to normalize raw section data into StandardizedContext and recommend exercises.
        
        Args:
            section_data: The JSON dict for a specific section.
            book_meta: The JSON dict for the book metadata.
            unit_meta: The JSON dict for the unit metadata.
            section_id: Optional database ID for the section.
        """
        # Level 1: Deterministic Metadata Extraction
        meta = self._extract_meta(section_data, book_meta, unit_meta, section_id)
        
        # Level 2: Robust Objective Extraction
        # Objectives are usually at the Unit level
        goals = self._extract_objectives(unit_meta.get("learning_objectives", {}))
        
        # Level 3: Semantic Content Processing & Recommendation
        # This extracts content into semantic blocks and recommends exercises.
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
            section_id=section_id,
            book_id=book.get("title", "unknown"), # In real app, might map title to ID
            grade_level=book.get("grade_level", "unknown"),
            unit_id=unit.get("unit_id", 0),
            section_type=section.get("section_type", SectionType.UNKNOWN)
        )

    def _extract_objectives(self, objectives: Dict[str, Any]) -> PedagogicalGoals:
        # Robust extraction with default empty lists
        return PedagogicalGoals(
            vocabulary=objectives.get("vocabulary_focus", []),
            grammar=objectives.get("grammar_focus", []),
            phonics=objectives.get("phonics_focus", [])
        )

    def _process_content_with_llm(self, section_data: Dict[str, Any], book_meta: Dict[str, Any], unit_meta: Dict[str, Any]) -> tuple[NormalizedContent, List[ExerciseRecommendation]]:
        """
        Uses LLM to normalize content and generate recommendations.
        """
        llm_context = {
            "section_type": section_data.get("section_type"),
            "content": section_data.get("content"),
            "visual_context": section_data.get("visual_context"),
            "book_meta": book_meta,
            "unit_meta": unit_meta
        }
        
        try:
            llm_result = self.text_gen_service.normalize_context(llm_context)
            
            blocks = []
            for b in llm_result.get("blocks", []):
                # Ensure semantic_type is valid or map/fallback
                try:
                    blocks.append(Block(semantic_type=b["semantic_type"], payload=b["payload"]))
                except Exception:
                    # Fallback for invalid block structure
                    blocks.append(Block(semantic_type=BlockType.GENERIC, payload=b))

            normalized_content = NormalizedContent(
                summary=llm_result.get("summary", ""),
                visual_scene=llm_result.get("visual_scene", ""),
                blocks=blocks
            )
            
            recommendations = []
            for r in llm_result.get("recommendations", []):
                try:
                    recommendations.append(ExerciseRecommendation(**r))
                except Exception:
                    continue
                    
            return normalized_content, recommendations
            
        except Exception as e:
            print(f"LLM Normalization failed: {e}. Falling back to heuristic.")
            return self._process_content_heuristic(section_data), []

    def _process_content_heuristic(self, section_data: Dict[str, Any]) -> NormalizedContent:
        """
        Transforms section content into normalized blocks using heuristics.
        """
        raw_content = section_data.get("content", {})
        visual_context = section_data.get("visual_context", "")
        
        blocks = []
        
        # Heuristic mapping for Level 3 (Simplified for implementation)
        
        # 1. Conversation / Dialogue
        if "conversation" in raw_content:
            blocks.append(Block(semantic_type=BlockType.CONVERSATION, payload={"turns": raw_content["conversation"]}))
        elif "dialogue" in raw_content:
            blocks.append(Block(semantic_type=BlockType.CONVERSATION, payload={"turns": raw_content["dialogue"]}))
             
        # 2. Vocabulary List
        if "vocabulary_items" in raw_content:
            blocks.append(Block(semantic_type=BlockType.VOCABULARY_LIST, payload={"items": raw_content["vocabulary_items"]}))
            
        # 3. Phonics
        if "sound" in raw_content:
            blocks.append(Block(semantic_type=BlockType.PHONICS_RULE, payload={
                "target_sound": raw_content.get("sound"),
                "words": raw_content.get("words", [])
            }))
        elif "sounds" in raw_content:
             blocks.append(Block(semantic_type=BlockType.PHONICS_RULE, payload={
                "sounds": raw_content.get("sounds")
            }))
            
        # 4. Fallback / Generic
        # If specific structures aren't found, wrap the whole content
        if not blocks:
            blocks.append(Block(semantic_type=BlockType.GENERIC, payload=raw_content))

        return NormalizedContent(
            summary=f"Content derived from {section_data.get('section_type', 'unknown')} section.",
            visual_scene=visual_context,
            blocks=blocks
        )
