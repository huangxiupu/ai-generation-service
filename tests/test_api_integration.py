import pytest
from fastapi.testclient import TestClient
from src.main import app, gateway, controller
from src.services.text_gen import MockTextGenService
from src.services.image_gen import MockImageGenService
from src.services.audio_gen import MockAudioGenService
import uuid

client = TestClient(app)

SECTION_ID = "01c55a99-a0be-4b51-8c34-f4270a04dab0"

def setup_mock_services():
    print("Setting up MOCK services for test...")
    mock_text = MockTextGenService()
    mock_image = MockImageGenService()
    mock_audio = MockAudioGenService()
    
    # Patch Gateway
    gateway.text_service = mock_text
    gateway.image_service = mock_image
    gateway.audio_service = mock_audio
    
    # Patch Controller
    controller.text_service = mock_text
    controller.image_service = mock_image
    controller.audio_service = mock_audio

def setup_exercise_type():
    # Ensure mcq_text exists
    code = "mcq_text"
    try:
        resp = gateway.db.table("exercise_types").select("*").eq("code", code).execute()
        if not resp.data:
            print(f"Inserting {code} type...")
            gateway.db.table("exercise_types").insert({
                "code": code,
                "name": "Multiple Choice Text",
                "description": "Select the correct option",
                "structure_schema": {},
                "prompt_template": "default"
            }).execute()
    except Exception as e:
        print(f"DB Setup Warning: {e}")

def test_generate_exercise_flow():
    # Setup
    setup_mock_services()
    setup_exercise_type()
    
    # Request
    payload = {
        "section_id": SECTION_ID,
        "exercise_type": "mcq_text",
        "exercise_num": 2
    }
    
    print(f"Sending request to /api/generate_exercise with payload: {payload}")
    response = client.post("/api/generate_exercise", json=payload)
    
    # Verify API Response
    if response.status_code != 200:
        print(f"Error Response: {response.text}")
    
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    
    # Verify DB Content
    for record in data:
        print(f"Record ID: {record.get('id')}, Status: {record.get('status')}")
        assert record["section_id"] == SECTION_ID
        # With Mock services, it should be pending (success)
        assert record["status"] == "pending"
        assert "content" in record
        assert "batch_id" in record
        
        # Verify Content has items
        content = record["content"]
        assert "items" in content
        assert len(content["items"]) > 0

    print("\nIntegration Test Passed!")
    print(f"Generated {len(data)} exercises.")

if __name__ == "__main__":
    try:
        test_generate_exercise_flow()
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
