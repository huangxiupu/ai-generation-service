import logging
import re
from typing import Dict, List, Any
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

    def generate_exercise(self, context: StandardizedContext, exercise_type: str) -> Dict[str, Any]:
        """
        Orchestrates the generation pipeline.
        """
        # Step 1: Text Generation
        # Convert Pydantic model to dict for Jinja2 rendering
        context_dict = context.model_dump()
        
        # Call TextGenService
        self.logger.info(f"Generating text skeleton for type: {exercise_type}")
        generated_data = self.text_service.generate(context_dict, exercise_type)
        
        # Parse into ExerciseSkeleton (handling potential schema mismatches)
        skeleton = self._parse_skeleton(generated_data, exercise_type)
        
        # Step 2: Asset Generation
        self.logger.info(f"Generating {len(skeleton.asset_specs)} assets")
        self._generate_assets(skeleton)
        
        # Step 3: Assembly
        # The skeleton items are already updated in-place during asset generation
        # Convert back to dict for response
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
        """
        for spec in skeleton.asset_specs:
            url = ""
            try:
                self.logger.info(f"Generating asset {spec.id} ({spec.type})")
                if spec.type == "image":
                    # Use prompt if available
                    if spec.prompt:
                        url = self.image_service.generate(spec.prompt, **spec.params)
                elif spec.type == "audio":
                    if spec.content:
                        url = self.audio_service.generate(spec.content, **spec.params)
            except Exception as e:
                self.logger.error(f"Failed to generate asset {spec.id}: {e}")
                # Could set a placeholder error image/audio here
                continue 
            
            if url:
                self._update_item_at_path(skeleton.items, spec.target_path, url)

    def _update_item_at_path(self, items: List[Dict], path: str, value: str):
        """
        Updates the value at the specified JSON path within the items list.
        Supported format example: "items[0].options[0].image_url"
        """
        # Simple path parser
        # Remove "items" prefix if present as we are rooting at 'items' list
        # We expect path to start with items[...]
        
        try:
            parts = path.split('.')
            root_part = parts[0]
            
            # Check if root is items[i]
            match = re.match(r"items\[(\d+)\]", root_part)
            if not match:
                self.logger.warning(f"Path must start with items[i], got: {path}")
                return
            
            idx = int(match.group(1))
            if idx >= len(items):
                self.logger.warning(f"Index {idx} out of range for items")
                return
            
            current = items[idx]
            
            # Iterate through intermediate parts
            for i, part in enumerate(parts[1:]):
                is_last = (i == len(parts) - 2) # -2 because we skipped root, so parts[1:] has N-1 elements
                
                # Check for list access: key[i]
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
                        # Cannot set value on a list item directly with this logic unless the path ends here?
                        # Wait, if path is ...options[0], then value replaces the object? 
                        # Usually path targets a field like .image_url
                        current = current[key][idx]
                    else:
                        current = current[key][idx]
                else:
                    # Dict access
                    if is_last:
                        current[part] = value
                    else:
                        if part not in current:
                            self.logger.warning(f"Key {part} not found")
                            return
                        current = current[part]
                        
        except Exception as e:
            self.logger.error(f"Error updating path {path}: {e}")
