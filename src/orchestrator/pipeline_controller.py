import re
from typing import Dict, List, Any, Optional
from src.utils.logger import app_logger
from ..schemas.orchestration import StandardizedContext, ExerciseSkeleton, AssetSpec

class PipelineController:
    """
    协调生成过程：
    1. TextGenService -> 骨架和资源规范 (Skeleton & AssetSpecs)
    2. ImageGenService/AudioGenService -> 资源 (Assets)
    3. 装配 -> 最终结果
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

    def generate_skeleton(self, context: StandardizedContext, exercise_type: str, reason: Optional[str] = None) -> ExerciseSkeleton:
        """
        步骤 1: 生成文本骨架。
        """
        context_dict = context.model_dump()
        if reason:
            context_dict['reason'] = reason
            
        app_logger.info(f"Generating text skeleton for type: {exercise_type}")
        generated_data = self.text_service.generate(context_dict, exercise_type)
        return self._parse_skeleton(generated_data, exercise_type)

    def hydrate_assets(self, skeleton: ExerciseSkeleton) -> ExerciseSkeleton:
        """
        步骤 2: 生成并填充资源（幂等）。
        """
        specs_data = (skeleton.generation or {}).get("asset_specs", [])
        asset_specs = []
        for spec_data in specs_data:
            try:
                if isinstance(spec_data, dict):
                    asset_specs.append(AssetSpec(**spec_data))
                else:
                    asset_specs.append(spec_data)
            except Exception as e:
                app_logger.warning(f"Invalid asset spec in hydration: {e}")

        app_logger.info(f"Hydrating {len(asset_specs)} assets")
        for spec in asset_specs:
            # Determine root dictionary based on path prefix
            root_dict = None
            sub_path = spec.target_path
            
            if spec.target_path.startswith("content."):
                root_dict = skeleton.content
                sub_path = spec.target_path[8:] # len("content.")
            elif spec.target_path.startswith("items[0]."): # Backward compatibility
                root_dict = skeleton.content
                sub_path = spec.target_path[9:] # len("items[0].")
            
            if root_dict is None:
                app_logger.warning(f"Unsupported path root in {spec.target_path}. Skipping.")
                continue

            # Strict Validation: Check if path exists
            if not self._check_path_exists(root_dict, sub_path):
                app_logger.error(f"Target path '{sub_path}' not found in structure. Skipping asset {spec.id}.")
                continue

            # Idempotency check
            existing_val = self._get_value_at_path(root_dict, sub_path)
            if existing_val and isinstance(existing_val, str) and existing_val.startswith("http"):
                 app_logger.info(f"Asset {spec.id} already exists, skipping.")
                 continue

            url = ""
            try:
                app_logger.info(f"Generating asset {spec.id} ({spec.type}) for path {spec.target_path}")
                if spec.type == "image":
                    if spec.prompt:
                        url = self.image_service.generate(spec.prompt, **spec.params)
                elif spec.type == "audio":
                    if spec.content:
                        url = self.audio_service.generate(spec.content, **spec.params)
            except Exception as e:
                app_logger.error(f"Failed to generate asset {spec.id}: {e}")
                continue 
            
            if url:
                self._update_value_at_path(root_dict, sub_path, url)
        
        return skeleton

    def generate_exercise(self, context: StandardizedContext, exercise_type: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        编排完整的生成流水线（旧版封装）。
        """
        skeleton = self.generate_skeleton(context, exercise_type, reason=reason)
        self.hydrate_assets(skeleton)
        return skeleton.model_dump()

    def _parse_skeleton(self, data: Dict[str, Any], exercise_type: str) -> ExerciseSkeleton:
        """
        将各种 LLM 输出适配为严格的 ExerciseSkeleton。
        """
        # 提取公共字段
        content = data.get("content") or {}
        grading = data.get("grading") or {}
        generation = data.get("generation") or {}

        # 注入题型字段到 content
        content["type"] = exercise_type

        # Ensure difficulty is present (required field)
        if "difficulty" not in generation or not generation["difficulty"]:
            generation["difficulty"] = data.get("difficulty", "Medium")

        # 统一资源规范到 generation.asset_specs
        specs_data = generation.get("asset_specs") or []
        if not isinstance(specs_data, list):
            specs_data = []
            
        # 兼容性：如果根节点有，也合并
        if "asset_specs" in data and isinstance(data["asset_specs"], list):
            # 避免重复
            existing_ids = {s.get("id") if isinstance(s, dict) else getattr(s, "id", None) for s in specs_data}
            for spec in data["asset_specs"]:
                spec_id = spec.get("id") if isinstance(spec, dict) else getattr(spec, "id", None)
                if spec_id not in existing_ids:
                    specs_data.append(spec)
        
        generation["asset_specs"] = specs_data
                    
        return ExerciseSkeleton(
            content=content,
            grading=grading,
            generation=generation
        )

    def _generate_assets(self, skeleton: ExerciseSkeleton):
        """
        处理 asset_specs 并原地更新 items。
        已弃用：请改用 hydrate_assets。
        """
        self.hydrate_assets(skeleton)

    def _check_path_exists(self, root: Dict, path: str) -> bool:
        """
        检查路径是否存在（Strict Validation）。
        """
        try:
            current = root
            parts = path.split('.')
            
            for part in parts:
                list_match = re.match(r"(\w+)\[(\d+)\]", part)
                if list_match:
                    key = list_match.group(1)
                    idx = int(list_match.group(2))
                    
                    if key not in current:
                        return False
                    if not isinstance(current[key], list) or idx >= len(current[key]):
                        return False
                    current = current[key][idx]
                else:
                    if part not in current:
                        return False
                    current = current[part]
            return True
        except Exception:
            return False

    def _get_value_at_path(self, root: Dict, path: str) -> Any:
        """
        检索指定 JSON 路径处的值。
        """
        try:
            current = root
            parts = path.split('.')
            
            for part in parts:
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
            app_logger.error(f"读取路径 {path} 时出错: {e}")
            return None

    def _update_value_at_path(self, root: Dict, path: str, value: str):
        """
        更新 root 字典中指定 JSON 路径处的值。
        路径必须已存在 (Strict Mode)。
        """
        try:
            parts = path.split('.')
            current = root
            
            for i, part in enumerate(parts):
                is_last = (i == len(parts) - 1)
                
                list_match = re.match(r"(\w+)\[(\d+)\]", part)
                
                if list_match:
                    key = list_match.group(1)
                    idx = int(list_match.group(2))
                    
                    if key not in current:
                        app_logger.warning(f"Key {key} not found")
                        return
                    if not isinstance(current[key], list) or idx >= len(current[key]):
                        app_logger.warning(f"Invalid list access {part}")
                        return
                        
                    if is_last:
                        current[key][idx] = value
                    else:
                        current = current[key][idx]
                else:
                    if is_last:
                        if part in current:
                            current[part] = value
                        else:
                            app_logger.warning(f"Key {part} not found (Strict Mode)")
                    else:
                        if part not in current:
                            app_logger.warning(f"Key {part} not found")
                            return
                        current = current[part]
                        
        except Exception as e:
            app_logger.error(f"Error updating path {path}: {e}")
