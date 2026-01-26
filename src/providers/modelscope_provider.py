import time
import requests
from typing import Optional, List, Dict, Any
from ..interfaces import AIProvider
from .openai_compatible import OpenAICompatibleProvider

class ModelScopeProvider(OpenAICompatibleProvider):
    """
    ModelScope Provider specialized for async image generation.
    Inherits from OpenAICompatibleProvider for chat capabilities.
    """
    def __init__(self, api_key: str, base_url: str):
        super().__init__(api_key, base_url)
        self.api_key = api_key
        # Ensure base_url ends with slash for easy concatenation
        self.base_url = base_url if base_url.endswith('/') else f"{base_url}/"

    def generate_image(self, 
                       prompt: str, 
                       model: str, 
                       size: str = "1024x1024", 
                       style: Optional[str] = None,
                       **kwargs) -> str:
        
        # 1. Submit Async Task
        # Endpoint: v1/images/generations (standard OpenAI path)
        submit_url = f"{self.base_url}images/generations"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-ModelScope-Async-Mode": "true"  # Required for async mode
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": 1
        }
        if style:
            payload["style"] = style
        
        # Merge kwargs
        payload.update(kwargs)

        print(f"[ModelScope] Submitting async image generation task for model {model}...")
        
        try:
            response = requests.post(submit_url, headers=headers, json=payload, timeout=30)
            
            # Check for immediate errors
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json
                except:
                    pass
                raise Exception(f"ModelScope submission failed (Status {response.status_code}): {error_detail}")
                
            data = response.json()
            print(f"[ModelScope] Submission response: {data}")
        except Exception as e:
            raise Exception(f"ModelScope async submission request failed: {e}")

        # Extract Task ID
        # Response format is typically: {"request_id": "...", "id": "task_id_..."} or similar
        task_id = data.get("id") or data.get("task_id")
        
        if not task_id:
            # Debug: print keys
            print(f"[ModelScope] Warning: Response keys: {list(data.keys())}")
            # If 'id' is missing but 'request_id' exists, maybe try request_id? 
            # But usually 'id' is the task id.
            raise Exception(f"Could not extract task_id from ModelScope response: {data}")
        
        print(f"[ModelScope] Task submitted. Task ID: {task_id}")

        # Wait a bit before first poll to ensure task is registered
        time.sleep(5)

        # 2. Poll for Result
        task_url = f"{self.base_url}tasks/{task_id}"
        
        start_time = time.time()
        timeout = 300 # 5 minutes
        poll_interval = 3 # seconds

        while time.time() - start_time < timeout:
            try:
                # Polling headers (auth only + Task Type)
                poll_headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-ModelScope-Task-Type": "image_generation"
                }
                print(f"[ModelScope] Polling task {task_id} at {task_url}...")
                print(poll_headers)
                poll_resp = requests.get(task_url, headers=poll_headers)
                poll_resp.raise_for_status()

                if poll_resp.status_code != 200:
                    print(f"[ModelScope] Polling failed (Status {poll_resp.status_code}). Retrying...")
                    time.sleep(poll_interval)
                    continue

                poll_data = poll_resp.json()
                
                # Check status
                # Possible statuses: "PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELED"
                status = poll_data.get("task_status")
                
                # If task_status is missing, check 'status' (OpenAI style?) or inference style
                if not status:
                    status = poll_data.get("status")
                
                if status == "SUCCEEDED":
                    print(f"[ModelScope] Task SUCCEEDED.")
                    # Extract URL
                    # Example says data["output_images"][0]
                    # Try output_images first
                    if "output_images" in poll_data and poll_data["output_images"]:
                        return poll_data["output_images"][0]

                    # Try 'results' (ModelScope Inference) or 'output'
                    results = poll_data.get("results")
                    if not results:
                        results = poll_data.get("output") # Sometimes output contains the result
                    
                    url = None
                    if results:
                        if isinstance(results, list) and len(results) > 0:
                            item = results[0]
                            if isinstance(item, dict):
                                url = item.get("url") # {"url": "..."}
                            elif isinstance(item, str):
                                url = item # ["http://..."]
                        elif isinstance(results, dict):
                            url = results.get("url")
                    
                    if url:
                        return url
                    
                    # Fallback: check OpenAI 'data' style if they mimicked it in the task result
                    if "data" in poll_data and isinstance(poll_data["data"], list):
                         url = poll_data["data"][0].get("url")
                         if url: return url

                    raise Exception(f"Task succeeded but no image URL found. Response: {poll_data}")
                
                elif status == "FAILED":
                      # Task failed definitively, do not retry
                      print(f"[ModelScope] Task FAILED. Full response: {poll_data}")
                      message = poll_data.get("message")
                      if not message and "errors" in poll_data:
                          message = poll_data["errors"].get("message")
                      if not message:
                          message = poll_data.get("error", "Unknown error")
                          
                      # Special handling for 'task not found' which might be race condition?
                      # If message contains "task not found", we retry for a while.
                      if "task not found" in str(message).lower():
                          print(f"[ModelScope] Task not found at {task_url}. Retrying... ({time.time() - start_time:.1f}s elapsed)")
                          
                          # Switch URL if persistent failure?
                          if (time.time() - start_time) > 10:
                              # Re-define fallback URLs locally to avoid scope issues
                              base_no_v1 = self.base_url.replace("/v1/", "/")
                              fallback_1 = f"{base_no_v1}tasks/{task_id}"
                              fallback_2 = f"{base_no_v1}api-inference/v1/tasks/{task_id}"
                              
                              if task_url == f"{self.base_url}tasks/{task_id}":
                                  print(f"[ModelScope] Switching to fallback URL 1: {fallback_1}")
                                  task_url = fallback_1
                              elif task_url == fallback_1:
                                  print(f"[ModelScope] Switching to fallback URL 2: {fallback_2}")
                                  task_url = fallback_2
                          
                          time.sleep(poll_interval)
                          continue

                      raise RuntimeError(f"ModelScope task failed: {message}")
                
                elif status in ["PENDING", "RUNNING", "QUEUED"]:
                    # print(f"[ModelScope] Task status: {status}...")
                    time.sleep(poll_interval)
                else:
                    print(f"[ModelScope] Unknown status: {status}. Response: {poll_data}")
                    time.sleep(poll_interval)
                
            except RuntimeError as e:
                # Fatal error, re-raise
                raise e
            except Exception as e:
                print(f"[ModelScope] Polling exception (will retry): {e}")
                time.sleep(poll_interval)
        
        raise Exception("ModelScope image generation timed out after 120 seconds.")
