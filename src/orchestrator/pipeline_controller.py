import logging
import re
from typing import Dict, List, Any, Optional
from ..schemas.orchestration import StandardizedContext, ExerciseSkeleton, AssetSpec

class PipelineController:
    """
    Coordinates the generation process:
    1. TextGenService -> Skeleton & AssetSpecs
    2. ImageGenService/AudioGenService -> Assets
    3. Assembly -> Final Result
    """
    def __init__(
        self, 
        text_service: Any, 
        image_service: Any, 
        audio_service: Any
    ):
        self.text_service = text_service
        self.image_service = image_service
        self.audio_service = audio_service
        self.logger = logging.getLogger(__name__)

    def generate_skeleton(self, context: StandardizedContext, exercise_type: str) -> ExerciseSkeleton:
        """
        Step 1: Generate text skeleton.
        """
        context_dict = context.model_dump()
        self.logger.info(f"Generating text skeleton for type: {exercise_type}")
        generated_data = self.text_service.generate(context_dict, exercise_type)
        return self._parse_skeleton(generated_data, exercise_type)

    def hydrate_assets(self, skeleton: ExerciseSkeleton) -> ExerciseSkeleton:
        """
        Step 2: Generate and fill assets (Idempotent).
        """
        self.logger.info(f"Hydrating {len(skeleton.asset_specs)} assets")
        for spec in skeleton.asset_specs:
            # Idempotency check
            existing_val = self._get_value_at_path(skeleton.items, spec.target_path)
            if existing_val and isinstance(existing_val, str) and existing_val.startswith("http"):
                 self.logger.info(f"Asset {spec.id} already exists, skipping.")
                 continue

            url = ""
            try:
                self.logger.info(f"Generating asset {spec.id} ({spec.type})")
                if spec.type == "image":
                    if spec.prompt:
                        url = self.image_service.generate(spec.prompt, **spec.params)
                elif spec.type == "audio":
                    if spec.content:
                        url = self.audio_service.generate(spec.content, **spec.params)
            except Exception as e:
                self.logger.error(f"Failed to generate asset {spec.id}: {e}")
                continue 
            
            if url:
                self._update_item_at_path(skeleton.items, spec.target_path, url)
        
        return skeleton

    def generate_exercise(self, context: StandardizedContext, exercise_type: str) -> Dict[str, Any]:
        """
        Orchestrates the full generation pipeline (Legacy Wrapper).
        """
        skeleton = self.generate_skeleton(context, exercise_type)
        self.hydrate_assets(skeleton)
        return skeleton.model_dump()

    def _parse_skeleton(self, data: Dict[str, Any], exercise_type: str) -> ExerciseSkeleton:
        """
        Adapt varied LLM outputs into a strict ExerciseSkeleton.
        Handles legacy schemas by converting them to AssetSpecs.
        """
        # Extract common fields
        content = data.get("content", {})
        # Try to find a reasonable title/instruction
        title = content.get("question") or content.get("statement") or content.get("text") or "Untitled Exercise"
        instructions = "Please complete the exercise." 
        
        items = []
        asset_specs = []
        
        # Adapter for specific legacy types that imply asset generation
        if exercise_type == "mcq_image":
            # Map legacy mcq_image structure to Skeleton
            options = content.get("options", [])
            prompts = data.get("generation", {}).get("options_prompts", [])
            
            # For MCQ, the "item" is usually the question object itself
            items.append(content)
            
            # Create AssetSpecs for each option
            for idx, opt in enumerate(options):
                # Ensure options have IDs
                opt_id = opt.get("id", f"opt_{idx}")
                # Get prompt from parallel array or fallback
                prompt = prompts[idx] if idx < len(prompts) else f"Illustration for {opt.get('caption', 'option')}"
                
                spec = AssetSpec(
                    id=f"img_{opt_id}",
                    target_path=f"items[0].options[{idx}].image_url",
                    type="image",
                    prompt=prompt,
                    params={"reference_style": "textbook_illustration"}
                )
                asset_specs.append(spec)
                
        else:
            # Generic handling: Assume the whole content is one item
            items.append(content)
            
            # If data has 'asset_specs' directly (New Prompt Style)
            if "asset_specs" in data:
                for spec_data in data["asset_specs"]:
                    asset_specs.append(AssetSpec(**spec_data))
                    
        return ExerciseSkeleton(
            title=title,
            instructions=instructions,
            items=items,
            asset_specs=asset_specs
        )

    def _generate_assets(self, skeleton: ExerciseSkeleton):
        """
        Process asset_specs and update items in place.
        Deprecated: Use hydrate_assets instead.
        """
        self.hydrate_assets(skeleton)

    def _get_value_at_path(self, items: List[Dict], path: str) -> Any:
        """
        Retrieves the value at the specified JSON path.
        """
        try:
            parts = path.split('.')
            root_part = parts[0]
            
            match = re.match(r"items\[(\d+)\]", root_part)
            if not match:
                return None
            
            idx = int(match.group(1))
            if idx >= len(items):
                return None
            
            current = items[idx]
            
            for part in parts[1:]:
                list_match = re.match(r"(\w+)\[(\d+)\]", part)
                if list_match:
                    key = list_match.group(1)
                    idx = int(list_match.group(2))
                    
                    if key not in current:
                        return None
                    if not isinstance(current[key], list) or idx >= len(current[key]):
                        return None
                    
                    current = current[key][idx]
                else:
                    if part not in current:
                        return None
                    current = current[part]
            
            return current
            
        except Exception as e:
            self.logger.error(f"Error reading path {path}: {e}")
            return None

    def _update_item_at_path(self, items: List[Dict], path: str, value: str):
        """
        Updates the value at the specified JSON path within the items list.
        Supported format example: "items[0].options[0].image_url"
        """
        try:
            parts = path.split('.')
            root_part = parts[0]
            
            match = re.match(r"items\[(\d+)\]", root_part)
            if not match:
                self.logger.warning(f"Path must start with items[i], got: {path}")
                return
            
            idx = int(match.group(1))
            if idx >= len(items):
                self.logger.warning(f"Index {idx} out of range for items")
                return
            
            current = items[idx]
            
            for i, part in enumerate(parts[1:]):
                is_last = (i == len(parts) - 2)
                
                list_match = re.match(r"(\w+)\[(\d+)\]", part)
                
                if list_match:
                    key = list_match.group(1)
                    idx = int(list_match.group(2))
                    
                    if key not in current:
                        self.logger.warning(f"Key {key} not found")
                        return
                    if not isinstance(current[key], list) or idx >= len(current[key]):
                        self.logger.warning(f"Invalid list access {part}")
                        return
                        
                    if is_last:
                        current[key][idx] = value # This might be wrong if we target a property of the object at index
                        # Wait, logic in original code was:
                        # current = current[key][idx]
                        # which meant it traversed INTO the object.
                        # BUT if is_last is true, we want to SET the value?
                        # Re-reading original code:
                        # if is_last: current = current[key][idx] 
                        # This implies the original code logic was flawed or I misunderstood.
                        # Original:
                        # if is_last: current = current[key][idx] else: current = current[key][idx]
                        # Then loops ended.
                        # Wait, original code:
                        # if is_last: current[part] = value (in else block)
                        
                        # Let's stick to the structure that works for .image_url
                        # parts: items[0], options[0], image_url
                        # i=0 (options[0]): is_last=True.
                        # list_match matches options[0].
                        # current becomes option object.
                        # Loop continues? No, is_last is checking if it's the second to last part.
                        # len(parts)=3. parts[1:] = [options[0], image_url].
                        # i=0: part=options[0]. len=3. len-2=1. i=0 != 1. is_last=False.
                        # current = current['options'][0]
                        # i=1: part=image_url. is_last=True.
                        # else (dict access): is_last=True -> current['image_url'] = value.
                        
                        # My re-implementation of _update_item_at_path needs to match original logic exactly.
                        current = current[key][idx]
                    else:
                        current = current[key][idx]
                else:
                    if is_last:
                        current[part] = value
                    else:
                        if part not in current:
                            self.logger.warning(f"Key {part} not found")
                            return
                        current = current[part]
                        
        except Exception as e:
            self.logger.error(f"Error updating path {path}: {e}")
