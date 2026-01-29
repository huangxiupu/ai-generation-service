import sys
import os
import json
import unittest
from typing import Dict, Any

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.orchestrator.context_engine import ContextEngine
from src.orchestrator.pipeline_controller import PipelineController
from src.services.text_gen import MockTextGenService
from src.services.image_gen import MockImageGenService
from src.services.audio_gen import MockAudioGenService

class TestOrchestrationFlow(unittest.TestCase):
    def setUp(self):
        self.text_service = MockTextGenService()
        self.image_service = MockImageGenService()
        self.audio_service = MockAudioGenService()
        
        self.context_engine = ContextEngine(text_gen_service=self.text_service)
        self.controller = PipelineController(
            text_service=self.text_service,
            image_service=self.image_service,
            audio_service=self.audio_service
        )

    def test_end_to_end_mcq_image(self):
        # 1. Prepare Mock Data
        book_meta = {"title": "Test Book", "grade_level": "1A"}
        unit_meta = {
            "unit_id": 1, 
            "learning_objectives": {
                "vocabulary_focus": ["cat", "dog"],
                "grammar_focus": ["It is a..."]
            }
        }
        section_data = {
            "section_type": "vocabulary_scene",
            "visual_context": "A pet shop scene.",
            "content": {
                "vocabulary_items": [{"word": "cat"}, {"word": "dog"}]
            }
        }

        # 2. Normalize Context
        print("\n--- Step 1: Normalizing Context ---")
        processing_result = self.context_engine.normalize(section_data, book_meta, unit_meta)
        context = processing_result.standardized_context
        print(f"Normalized Context: {context.model_dump_json(indent=2)}")
        
        self.assertEqual(context.meta.grade_level, "1A")
        self.assertEqual(len(context.pedagogical_goals.vocabulary), 2)
        self.assertEqual(context.normalized_content.visual_scene, "A pet shop scene.")

        # 3. Generate Exercise
        print("\n--- Step 2: Generating Exercise (MCQ Image) ---")
        # MockTextGenService returns a specific structure for 'mcq_image'
        # which our controller should parse and then trigger image generation.
        result = self.controller.generate_exercise(context, "mcq_image")
        
        print(f"Final Result: {json.dumps(result, indent=2)}")
        
        # 4. Verification
        items = result["items"]
        self.assertTrue(len(items) > 0)
        
        # Check if image URLs were injected
        # In MockImageGenService, it returns "https://placehold.co/1024x1024.png?text=Mock+Image"
        # In MockTextGenService, it returns "https://placehold.co/200x200?text=Cat"
        # PipelineController should have updated items[0].options[0].image_url
        
        first_option = items[0]["options"][0]
        self.assertIn("image_url", first_option)
        print(f"Option 1 Image URL: {first_option['image_url']}")
        
        # We expect the URL to be from the ImageGenService (1024x1024) not TextGenService (200x200)
        self.assertIn("1024x1024", first_option["image_url"])
        
        # Check if asset specs were processed
        asset_specs = result["asset_specs"]
        self.assertTrue(len(asset_specs) > 0)
        self.assertEqual(asset_specs[0]["type"], "image")

if __name__ == "__main__":
    unittest.main()
