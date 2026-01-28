from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import uuid
from src.gateway import AIServiceGateway
from src.orchestrator.pipeline_controller import PipelineController
from src.schemas.enums import ExerciseGenerationStatus

app = FastAPI()
gateway = AIServiceGateway()
controller = PipelineController(
    text_service=gateway.text_service,
    image_service=gateway.image_service,
    audio_service=gateway.audio_service
)

class PreprocessRequest(BaseModel):
    section_id: str

class GenerateExerciseRequest(BaseModel):
    section_id: str
    exercise_type: str
    exercise_num: int = 1

@app.post("/api/preprocess")
async def preprocess_section_endpoint(request: PreprocessRequest):
    try:
        result = gateway.preprocess_section(
            request.section_id
        )
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate_exercise")
async def generate_exercise_endpoint(request: GenerateExerciseRequest):
    try:
        # 1. 预处理 / 获取上下文
        # 检查预处理是否存在？gateway.preprocess_section 会在存在时更新。
        # 我们可以直接调用它以确保安全，并确保我们拥有上下文对象。
        context = gateway.preprocess_section(request.section_id)
        
        # 2. 解析练习类型 ID
        # 我们需要查询数据库中的 exercise_types 表。
        # 使用 gateway.db
        type_resp = gateway.db.table("exercise_types").select("id").eq("code", request.exercise_type).single().execute()
        if not type_resp.data:
            # 如果未找到练习类型，记录警告并报错
            raise HTTPException(status_code=400, detail=f"未找到练习类型: {request.exercise_type}")
        
        type_id = type_resp.data['id']
        batch_id = str(uuid.uuid4())
        results = []

        # 3. 循环生成
        for _ in range(request.exercise_num):
            # 步骤 1: 生成骨架
            try:
                skeleton = controller.generate_skeleton(context, request.exercise_type)
                
                # 插入初始记录
                record_data = {
                    "section_id": request.section_id,
                    "exercise_type_id": type_id,
                    "content": skeleton.model_dump(),
                    "status": ExerciseGenerationStatus.GENERATING,
                    "batch_id": batch_id
                }
                insert_resp = gateway.db.table("generated_exercises").insert(record_data).execute()
                if not insert_resp.data:
                    raise Exception("插入初始记录失败")
                
                record_id = insert_resp.data[0]['id']
                current_record = insert_resp.data[0]
                
                # 步骤 2: 填充资源
                try:
                    final_skeleton = controller.hydrate_assets(skeleton)
                    
                    # 更新记录 (成功)
                    update_data = {
                        "content": final_skeleton.model_dump(),
                        "status": ExerciseGenerationStatus.PENDING
                    }
                    # 如果有顶级预览图，提取图片 URL？
                    # Schema 中有 image_url。也许是第一张图？
                    if final_skeleton.asset_specs:
                        # 查找第一个图片资源
                        for spec in final_skeleton.asset_specs:
                            if spec.type == "image":
                                # 使用路径从 items 中提取 URL？
                                # 或者直接依赖内容。
                                # 除非有要求，否则暂时跳过填充顶级 image_url。
                                pass

                    update_resp = gateway.db.table("generated_exercises").update(update_data).eq("id", record_id).execute()
                    current_record = update_resp.data[0]
                    
                except Exception as e:
                    # 更新记录 (失败)
                    print(f"资源生成失败 {record_id}: {e}")
                    fail_data = {
                        "status": ExerciseGenerationStatus.GENERATION_FAILED
                        # 内容保持为骨架
                    }
                    update_resp = gateway.db.table("generated_exercises").update(fail_data).eq("id", record_id).execute()
                    current_record = update_resp.data[0]
                
                results.append(current_record)

            except Exception as e:
                print(f"骨架生成失败: {e}")
                # 如果骨架生成失败，我们选择跳过此迭代并继续。
                continue

        return results

    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok"}
