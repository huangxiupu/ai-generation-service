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
        # 1. Preprocess / Get Context
        # Check if preprocessing exists? gateway.preprocess_section updates if exists.
        # We can just call it to be safe and ensure we have the context object.
        context = gateway.preprocess_section(request.section_id)
        
        # 2. Resolve Exercise Type ID
        # We need to query the DB for exercise_types table.
        # Using gateway.db
        type_resp = gateway.db.table("exercise_types").select("id").eq("code", request.exercise_type).single().execute()
        if not type_resp.data:
            # Fallback or Error? 
            # For integration test, maybe the table is empty?
            # I will log warning and maybe fail.
            raise HTTPException(status_code=400, detail=f"Exercise type {request.exercise_type} not found")
        
        type_id = type_resp.data['id']
        batch_id = str(uuid.uuid4())
        results = []

        # 3. Loop Generation
        for _ in range(request.exercise_num):
            # Step 1: Generate Skeleton
            try:
                skeleton = controller.generate_skeleton(context, request.exercise_type)
                
                # Insert Initial Record
                record_data = {
                    "section_id": request.section_id,
                    "exercise_type_id": type_id,
                    "content": skeleton.model_dump(),
                    "status": ExerciseGenerationStatus.GENERATING,
                    "batch_id": batch_id
                }
                insert_resp = gateway.db.table("generated_exercises").insert(record_data).execute()
                if not insert_resp.data:
                    raise Exception("Failed to insert initial record")
                
                record_id = insert_resp.data[0]['id']
                current_record = insert_resp.data[0]
                
                # Step 2: Hydrate Assets
                try:
                    final_skeleton = controller.hydrate_assets(skeleton)
                    
                    # Update Record (Success)
                    update_data = {
                        "content": final_skeleton.model_dump(),
                        "status": ExerciseGenerationStatus.PENDING
                    }
                    # Extract image url if any for top-level preview? 
                    # The schema has image_url. Maybe first image?
                    if final_skeleton.asset_specs:
                        # Find first image asset
                        for spec in final_skeleton.asset_specs:
                            if spec.type == "image":
                                # Extract URL from items using path?
                                # Or just rely on content.
                                # Let's skip filling top-level image_url for now unless requested.
                                pass

                    update_resp = gateway.db.table("generated_exercises").update(update_data).eq("id", record_id).execute()
                    current_record = update_resp.data[0]
                    
                except Exception as e:
                    # Update Record (Failed)
                    print(f"Asset generation failed for {record_id}: {e}")
                    fail_data = {
                        "status": ExerciseGenerationStatus.GENERATION_FAILED
                        # content remains skeleton
                    }
                    update_resp = gateway.db.table("generated_exercises").update(fail_data).eq("id", record_id).execute()
                    current_record = update_resp.data[0]
                
                results.append(current_record)

            except Exception as e:
                print(f"Skeleton generation failed: {e}")
                # If skeleton fails, we don't insert? Or insert failed record?
                # If we didn't insert, we can't return a record ID.
                # Just skip this iteration or return error info?
                # I'll log and continue.
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
