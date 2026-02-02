from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
import asyncio
import contextlib
from src.gateway import AIServiceGateway
from src.orchestrator.pipeline_controller import PipelineController
from src.schemas.enums import ExerciseGenerationStatus

# 定义任务类型
class Task:
    def __init__(self, task_type: str, data: dict):
        self.task_type = task_type
        self.data = data

# 全局异步队列
task_queue = asyncio.Queue()

async def task_worker():
    """
    异步任务工作协程，从队列中顺序提取任务执行。
    通过顺序执行（单 Worker）来防止 LLM API 限流。
    """
    print("[Worker] 任务工作协程已启动")
    while True:
        task = await task_queue.get()
        try:
            print(f"[Worker] 开始处理任务: {task.task_type}, 数据: {task.data}")
            
            if task.task_type == "preprocess":
                # 使用 to_thread 运行同步的预处理函数
                await asyncio.to_thread(process_preprocessing_task, task.data["section_id"])
            
            elif task.task_type == "generate":
                # 使用 to_thread 运行同步的生成函数
                await asyncio.to_thread(
                    process_generation_task,
                    task.data["section_id"],
                    task.data["types"],
                    task.data["count"],
                    task.data["batch_id"]
                )
            
            print(f"[Worker] 任务完成: {task.task_type}")
            
            # 任务之间添加微小延时，进一步降低限流风险
            await asyncio.sleep(0.5)
            
        except Exception as e:
            print(f"[Worker] 处理任务时出错 ({task.task_type}): {e}")
            import traceback
            traceback.print_exc()
        finally:
            task_queue.task_done()

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时开启后台 Worker
    worker_task = asyncio.create_task(task_worker())
    print("应用启动：Worker 已在后台运行")
    yield
    # 关闭时取消 Worker
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        print("应用关闭：Worker 已取消")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def process_preprocessing_task(section_id: str):
    """
    后台执行预处理任务
    """
    try:
        print(f"[BackgroundTask] 开始预处理章节: {section_id}")
        gateway.preprocess_section(section_id)
        print(f"[BackgroundTask] 预处理完成: {section_id}")
    except Exception as e:
        print(f"[BackgroundTask] 预处理失败 ({section_id}): {e}")
        import traceback
        traceback.print_exc()

@app.post("/api/preprocess")
async def preprocess_section_endpoint(request: PreprocessRequest):
    print(f"收到预处理请求 (队列化): section_id={request.section_id}")
    try:
        # 将任务放入异步队列
        await task_queue.put(Task("preprocess", {"section_id": request.section_id}))
        
        return {
            "status": "accepted", 
            "message": "预处理任务已加入队列", 
            "section_id": request.section_id
        }
    except Exception as e:
        print(f"提交预处理任务失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

def process_generation_task(section_id: str, types: List[str], count: int, batch_id: str):
    try:
        print(f"Starting background generation for section {section_id}, types: {types}, count: {count}")
        
        # 1. 尝试获取已有的预处理结果，如果没有则运行预处理
        context = gateway.get_preprocessed_context(section_id)
        if context:
            print(f"[Generation] 使用已有的预处理结果: {section_id}")
        else:
            print(f"[Generation] 未找到预处理结果，开始运行预处理: {section_id}")
            context = gateway.preprocess_section(section_id)
        
        print(f"[Generation] 上下文准备就绪，开始生成 {len(types)} 种类型的题目...")
        
        # 1.5 获取推荐理由 (Reasons)
        reasons_map = {}
        try:
            rec_resp = gateway.db.table("section_exercise_recommendations").select("recommended_types").eq("section_id", section_id).single().execute()
            if rec_resp.data and rec_resp.data.get('recommended_types'):
                rec_list = rec_resp.data['recommended_types']
                if isinstance(rec_list, list):
                    type_id_to_reason = {}
                    type_ids = []
                    for item in rec_list:
                        if isinstance(item, dict) and 'type_id' in item:
                            tid = item['type_id']
                            type_ids.append(tid)
                            type_id_to_reason[tid] = item.get('reason', '')
                    
                    if type_ids:
                        types_info_resp = gateway.db.table("exercise_types").select("id", "code").in_("id", type_ids).execute()
                        if types_info_resp.data:
                            for t in types_info_resp.data:
                                code = t['code']
                                tid = t['id']
                                if tid in type_id_to_reason:
                                    reasons_map[code] = type_id_to_reason[tid]
        except Exception as e:
            print(f"[Generation] 获取推荐理由失败: {e}")

        # 2. 遍历每个类型
        for ex_type in types:
            try:
                # 获取类型 ID
                type_resp = gateway.db.table("exercise_types").select("id").eq("code", ex_type).single().execute()
                if not type_resp.data:
                    print(f"未找到练习类型: {ex_type}")
                    continue
                
                type_id = type_resp.data['id']
                reason = reasons_map.get(ex_type)
                
                # 3. 循环生成指定数量
                for _ in range(count):
                    try:
                        # 步骤 1: 生成骨架
                        skeleton = controller.generate_skeleton(context, ex_type, reason=reason)
                        
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
async def generate_exercise_endpoint(request: GenerateExerciseRequest):
    try:
        target_types = []
        
        # 确定目标类型
        if request.use_recommendations:
            # 从数据库获取推荐
            rec_resp = gateway.db.table("section_exercise_recommendations").select("recommended_types").eq("section_id", request.section_id).single().execute()
            if rec_resp.data and rec_resp.data.get('recommended_types'):
                rec_list = rec_resp.data['recommended_types']
                
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
        
        if request.exercise_types:
            for t in request.exercise_types:
                if t not in target_types:
                    target_types.append(t)
        
        if not target_types:
            raise HTTPException(status_code=400, detail="未指定练习类型，且未找到推荐类型")
            
        batch_id = str(uuid.uuid4())
        
        # 将任务放入异步队列
        await task_queue.put(Task("generate", {
            "section_id": request.section_id,
            "types": target_types,
            "count": request.exercise_num,
            "batch_id": batch_id
        }))
        
        return {"status": "accepted", "batch_id": batch_id, "message": "任务已加入队列等待处理", "target_types": target_types}

    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
