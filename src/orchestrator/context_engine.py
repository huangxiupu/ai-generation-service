import json
from typing import Dict, Any, Optional, List
from ..schemas.orchestration import (
    StandardizedContext, MetaInfo, PedagogicalGoals, 
    NormalizedContent, Block
)
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
    """
    def __init__(self, text_gen_service: Optional[BaseTextGenService] = None):
        self.text_gen_service = text_gen_service

    def normalize(self, section_data: Dict[str, Any], book_meta: Dict[str, Any], unit_meta: Dict[str, Any]) -> StandardizedContext:
        """
        Main entry point to normalize raw section data into StandardizedContext.
        
        Args:
            section_data: The JSON dict for a specific section.
            book_meta: The JSON dict for the book metadata.
            unit_meta: The JSON dict for the unit metadata.
        """
        # Level 1: Deterministic Metadata Extraction
        meta = self._extract_meta(section_data, book_meta, unit_meta)
        
        # Level 2: Robust Objective Extraction
        # Objectives are usually at the Unit level
        goals = self._extract_objectives(unit_meta.get("learning_objectives", {}))
        
        # Level 3: Semantic Content Processing
        # This extracts content into semantic blocks and cleans up noise.
        normalized_content = self._process_content(section_data)

        return StandardizedContext(
            meta=meta,
            pedagogical_goals=goals,
            normalized_content=normalized_content
        )

    def _extract_meta(self, section: Dict[str, Any], book: Dict[str, Any], unit: Dict[str, Any]) -> MetaInfo:
        return MetaInfo(
            book_id=book.get("title", "unknown"), # In real app, might map title to ID
            grade_level=book.get("grade_level", "unknown"),
            unit_id=unit.get("unit_id", 0),
            section_type=section.get("section_type", "unknown")
        )

    def _extract_objectives(self, objectives: Dict[str, Any]) -> PedagogicalGoals:
        # Robust extraction with default empty lists
        return PedagogicalGoals(
            vocabulary=objectives.get("vocabulary_focus", []),
            grammar=objectives.get("grammar_focus", []),
            phonics=objectives.get("phonics_focus", [])
        )

    def _process_content(self, section_data: Dict[str, Any]) -> NormalizedContent:
        """
        Transforms section content into normalized blocks.
        """
        raw_content = section_data.get("content", {})
        visual_context = section_data.get("visual_context", "")
        
        # TODO: In a production environment, we would use self.text_gen_service
        # to call an LLM to semantically parse and normalize this content.
        # e.g., self.text_gen_service.normalize_context(raw_content, visual_context)
        
        blocks = []
        
        # Heuristic mapping for Level 3 (Simplified for implementation)
        
        # 1. Conversation / Dialogue
        if "conversation" in raw_content:
            blocks.append(Block(semantic_type="conversation", payload={"turns": raw_content["conversation"]}))
        elif "dialogue" in raw_content:
             blocks.append(Block(semantic_type="conversation", payload={"turns": raw_content["dialogue"]}))
             
        # 2. Vocabulary List
        if "vocabulary_items" in raw_content:
            blocks.append(Block(semantic_type="vocabulary_list", payload={"items": raw_content["vocabulary_items"]}))
            
        # 3. Phonics
        if "sound" in raw_content:
            blocks.append(Block(semantic_type="phonics_rule", payload={
                "target_sound": raw_content.get("sound"),
                "words": raw_content.get("words", [])
            }))
        elif "sounds" in raw_content:
             blocks.append(Block(semantic_type="phonics_rule", payload={
                "sounds": raw_content.get("sounds")
            }))
            
        # 4. Fallback / Generic
        # If specific structures aren't found, wrap the whole content
        if not blocks:
            blocks.append(Block(semantic_type="generic", payload=raw_content))

        return NormalizedContent(
            summary=f"Content derived from {section_data.get('section_type', 'unknown')} section.",
            visual_scene=visual_context,
            blocks=blocks
        )
