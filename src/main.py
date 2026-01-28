from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
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
    exercise_types: Optional[List[str]] = None
    use_recommendations: bool = False
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

def process_generation_task(section_id: str, types: List[str], count: int, batch_id: str):
    try:
        print(f"Starting background generation for section {section_id}, types: {types}, count: {count}")
        # 1. 预处理 / 获取上下文
        context = gateway.preprocess_section(section_id)
        
        # 2. 遍历每个类型
        for ex_type in types:
            try:
                # 获取类型 ID
                type_resp = gateway.db.table("exercise_types").select("id").eq("code", ex_type).single().execute()
                if not type_resp.data:
                    print(f"未找到练习类型: {ex_type}")
                    continue
                
                type_id = type_resp.data['id']
                
                # 3. 循环生成指定数量
                for _ in range(count):
                    try:
                        # 步骤 1: 生成骨架
                        skeleton = controller.generate_skeleton(context, ex_type)
                        
                        # Extract difficulty
                        difficulty_val = skeleton.generation.get("difficulty", "Medium") if skeleton.generation else "Medium"

                        # 插入初始记录
                        record_data = {
                            "section_id": section_id,
                            "exercise_type_id": type_id,
                            "content": skeleton.model_dump(),
                            "difficulty": difficulty_val,
                            "status": ExerciseGenerationStatus.GENERATING,
                            "batch_id": batch_id
                        }
                        insert_resp = gateway.db.table("generated_exercises").insert(record_data).execute()
                        if not insert_resp.data:
                            print("插入初始记录失败")
                            continue
                        
                        record_id = insert_resp.data[0]['id']
                        
                        # 步骤 2: 填充资源
                        try:
                            final_skeleton = controller.hydrate_assets(skeleton)
                            
                            # 更新记录 (成功)
                            update_data = {
                                "content": final_skeleton.model_dump(),
                                "status": ExerciseGenerationStatus.PENDING
                            }
                            gateway.db.table("generated_exercises").update(update_data).eq("id", record_id).execute()
                            
                        except Exception as e:
                            # 更新记录 (失败)
                            print(f"资源生成失败 {record_id}: {e}")
                            fail_data = {
                                "status": ExerciseGenerationStatus.GENERATION_FAILED
                            }
                            gateway.db.table("generated_exercises").update(fail_data).eq("id", record_id).execute()
                            
                    except Exception as e:
                        print(f"骨架生成失败 ({ex_type}): {e}")
                        continue
            except Exception as e:
                print(f"处理类型失败 ({ex_type}): {e}")
                continue
                
        print(f"Batch {batch_id} completed.")
        
    except Exception as e:
        print(f"后台任务失败: {e}")
        import traceback
        traceback.print_exc()

@app.post("/api/generate_exercise")
async def generate_exercise_endpoint(request: GenerateExerciseRequest, background_tasks: BackgroundTasks):
    try:
        target_types = []
        
        # 确定目标类型
        if request.use_recommendations:
            # 从数据库获取推荐
            rec_resp = gateway.db.table("section_exercise_recommendations").select("recommended_types").eq("section_id", request.section_id).single().execute()
            if rec_resp.data and rec_resp.data.get('recommended_types'):
                # recommended_types 是包含 type_id 的列表
                # 我们需要将其转换为 codes
                rec_list = rec_resp.data['recommended_types'] # Assuming list of dicts or objects
                # 假设结构是 [{"type_id": "...", ...}, ...] 或只是 ID 列表？
                # 根据 schema.sql: recommended_types jsonb
                # 我们需要查看它是如何存储的。假设是对象列表。
                
                type_ids = []
                if isinstance(rec_list, list):
                    for item in rec_list:
                        if isinstance(item, dict) and 'type_id' in item:
                            type_ids.append(item['type_id'])
                        elif isinstance(item, str):
                            type_ids.append(item)
                
                if type_ids:
                    # 查询这些 ID 对应的 code
                    types_resp = gateway.db.table("exercise_types").select("code").in_("id", type_ids).execute()
                    if types_resp.data:
                        target_types = [t['code'] for t in types_resp.data]
        
        # 如果指定了 explicit types，则合并（或者如果 auto 没找到，则只用 explicit）
        # 这里策略：如果 explicit 存在，优先使用 explicit。
        # 如果 use_recommendations 为 True，则追加推荐的。
        if request.exercise_types:
            for t in request.exercise_types:
                if t not in target_types:
                    target_types.append(t)
        
        # 兼容旧请求：如果有 exercise_type 字段（但在新 model 中已移除，但我们可以检查 request body 如果是 dict）
        # 由于我们更新了 Model，旧字段如果不传会报错吗？
        # 我们已经移除了 exercise_type 字段。
        # 为了兼容，如果前端还在传旧字段... 前端是我们控制的，所以我们可以确保前端传新的。
        
        if not target_types:
            raise HTTPException(status_code=400, detail="未指定练习类型，且未找到推荐类型")
            
        batch_id = str(uuid.uuid4())
        
        # 添加后台任务
        background_tasks.add_task(
            process_generation_task, 
            request.section_id, 
            target_types, 
            request.exercise_num, 
            batch_id
        )
        
        return {"status": "accepted", "batch_id": batch_id, "message": "任务已提交后台处理", "target_types": target_types}

    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok"}
