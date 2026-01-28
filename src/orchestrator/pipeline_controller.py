import logging
import re
from typing import Dict, List, Any, Optional
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
        self.logger = logging.getLogger(__name__)

    def generate_skeleton(self, context: StandardizedContext, exercise_type: str) -> ExerciseSkeleton:
        """
        步骤 1: 生成文本骨架。
        """
        context_dict = context.model_dump()
        self.logger.info(f"Generating text skeleton for type: {exercise_type}")
        generated_data = self.text_service.generate(context_dict, exercise_type)
        return self._parse_skeleton(generated_data, exercise_type)

    def hydrate_assets(self, skeleton: ExerciseSkeleton) -> ExerciseSkeleton:
        """
        步骤 2: 生成并填充资源（幂等）。
        """
        self.logger.info(f"Hydrating {len(skeleton.asset_specs)} assets")
        for spec in skeleton.asset_specs:
            # 幂等性检查
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
        编排完整的生成流水线（旧版封装）。
        """
        skeleton = self.generate_skeleton(context, exercise_type)
        self.hydrate_assets(skeleton)
        return skeleton.model_dump()

    def _parse_skeleton(self, data: Dict[str, Any], exercise_type: str) -> ExerciseSkeleton:
        """
        将各种 LLM 输出适配为严格的 ExerciseSkeleton。
        通过将旧版 schema 转换为 AssetSpecs 来处理它们。
        """
        # 提取公共字段
        content = data.get("content", {})
        # 尝试找到合理的标题/说明
        title = content.get("question") or content.get("statement") or content.get("text") or "Untitled Exercise"
        instructions = "Please complete the exercise." 
        
        items = []
        asset_specs = []
        
        # 针对特定旧版类型的适配器，这些类型暗示了资源生成
        if exercise_type == "mcq_image":
            # 将旧版 mcq_image 结构映射到 Skeleton
            options = content.get("options", [])
            prompts = data.get("generation", {}).get("options_prompts", [])
            
            # 对于 MCQ，"item" 通常是问题对象本身
            items.append(content)
            
            # 为每个选项创建 AssetSpecs
            for idx, opt in enumerate(options):
                # 确保选项有 ID
                opt_id = opt.get("id", f"opt_{idx}")
                # 从并行数组获取 prompt 或使用回退值
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
            # 通用处理：假设整个内容是一个项目
            items.append(content)
            
            # 如果数据直接包含 'asset_specs' (新提示词风格)
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
        处理 asset_specs 并原地更新 items。
        已弃用：请改用 hydrate_assets。
        """
        self.hydrate_assets(skeleton)

    def _get_value_at_path(self, items: List[Dict], path: str) -> Any:
        """
        检索指定 JSON 路径处的值。
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
            self.logger.error(f"读取路径 {path} 时出错: {e}")
            return None

    def _update_item_at_path(self, items: List[Dict], path: str, value: str):
        """
        更新 items 列表中指定 JSON 路径处的值。
        支持的格式示例："items[0].options[0].image_url"
        """
        try:
            parts = path.split('.')
            root_part = parts[0]
            
            match = re.match(r"items\[(\d+)\]", root_part)
            if not match:
                self.logger.warning(f"路径必须以 items[i] 开头，当前为: {path}")
                return
            
            idx = int(match.group(1))
            if idx >= len(items):
                self.logger.warning(f"索引 {idx} 超出 items 范围")
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
