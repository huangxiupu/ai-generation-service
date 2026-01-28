import time
import requests
from typing import Optional, List, Dict, Any
from ..interfaces import AIProvider
from .openai_compatible import OpenAICompatibleProvider

class ModelScopeProvider(OpenAICompatibleProvider):
    """
    专门用于异步图像生成的 ModelScope 提供商。
    继承自 OpenAICompatibleProvider 以获得对话功能。
    """
    def __init__(self, api_key: str, base_url: str):
        super().__init__(api_key, base_url)
        self.api_key = api_key
        # 确保 base_url 以斜杠结尾，以便于拼接
        self.base_url = base_url if base_url.endswith('/') else f"{base_url}/"

    def generate_image(self, 
                       prompt: str, 
                       model: str, 
                       size: str = "1024x1024", 
                       style: Optional[str] = None,
                       **kwargs) -> str:
        
        # 1. 提交异步任务
        # 端点：v1/images/generations (标准 OpenAI 路径)
        submit_url = f"{self.base_url}images/generations"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-ModelScope-Async-Mode": "true"  # 异步模式所需
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": 1
        }
        if style:
            payload["style"] = style
        
        # 合并 kwargs
        payload.update(kwargs)

        print(f"[ModelScope] 正在为模型 {model} 提交异步图像生成任务...")
        
        try:
            response = requests.post(submit_url, headers=headers, json=payload, timeout=30)
            
            # 检查即时错误
            if response.status_code != 200:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json
                except:
                    pass
                raise Exception(f"ModelScope 提交失败 (状态码 {response.status_code}): {error_detail}")
                
            data = response.json()
            print(f"[ModelScope] 提交响应: {data}")
        except Exception as e:
            raise Exception(f"ModelScope 异步提交请求失败: {e}")

        # 提取任务 ID
        # 响应格式通常为：{"request_id": "...", "id": "task_id_..."} 或类似格式
        task_id = data.get("id") or data.get("task_id")
        
        if not task_id:
            # 调试：打印键名
            print(f"[ModelScope] 警告: 响应键名: {list(data.keys())}")
            # 如果缺少 'id' 但存在 'request_id'，也许可以尝试使用 request_id？
            # 但通常 'id' 是任务 ID。
            raise Exception(f"无法从 ModelScope 响应中提取 task_id: {data}")
        
        print(f"[ModelScope] 任务已提交。任务 ID: {task_id}")

        # 在第一次轮询前等待片刻，以确保任务已注册
        time.sleep(5)

        # 2. 轮询结果
        task_url = f"{self.base_url}tasks/{task_id}"
        
        start_time = time.time()
        timeout = 300 # 5 分钟
        poll_interval = 3 # 秒

        while time.time() - start_time < timeout:
            try:
                # 轮询请求头（仅认证 + 任务类型）
                poll_headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-ModelScope-Task-Type": "image_generation"
                }
                print(f"[ModelScope] 正在 {task_url} 轮询任务 {task_id}...")
                print(poll_headers)
                poll_resp = requests.get(task_url, headers=poll_headers)
                poll_resp.raise_for_status()

                if poll_resp.status_code != 200:
                    print(f"[ModelScope] 轮询失败 (状态码 {poll_resp.status_code})。正在重试...")
                    time.sleep(poll_interval)
                    continue

                poll_data = poll_resp.json()
                
                # 检查状态
                # 可能的状态："PENDING", "RUNNING", "SUCCEEDED", "FAILED", "CANCELED"
                status = poll_data.get("task_status")
                
                # 如果缺少 task_status，检查 'status'（OpenAI 风格？）或推理风格
                if not status:
                    status = poll_data.get("status")
                
                if status == "SUCCEEDED":
                    print(f"[ModelScope] 任务成功。")
                    # 提取 URL
                    # 示例说明 data["output_images"][0]
                    # 先尝试 output_images
                    if "output_images" in poll_data and poll_data["output_images"]:
                        return poll_data["output_images"][0]

                    # 尝试 'results' (ModelScope 推理) 或 'output'
                    results = poll_data.get("results")
                    if not results:
                        results = poll_data.get("output") # 有时 output 包含结果
                    
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
                    
                    # 回退：检查 OpenAI 'data' 风格，如果他们在任务结果中模仿了它
                    if "data" in poll_data and isinstance(poll_data["data"], list):
                         url = poll_data["data"][0].get("url")
                         if url: return url

                    raise Exception(f"任务成功但未找到图像 URL。响应: {poll_data}")
                
                elif status == "FAILED":
                      # 任务明确失败，不再重试
                      print(f"[ModelScope] 任务失败。完整响应: {poll_data}")
                      message = poll_data.get("message")
                      if not message and "errors" in poll_data:
                          message = poll_data["errors"].get("message")
                      if not message:
                          message = poll_data.get("error", "未知错误")
                          
                      # 针对 'task not found' 的特殊处理，这可能是竞争条件？
                      # 如果消息包含 "task not found"，我们将重试一段时间。
                      if "task not found" in str(message).lower():
                          print(f"[ModelScope] 在 {task_url} 未找到任务。正在重试... (已用时 {time.time() - start_time:.1f}s)")
                          
                          # 如果持续失败，切换 URL？
                          if (time.time() - start_time) > 10:
                              # 在本地重新定义回退 URL 以避免作用域问题
                              base_no_v1 = self.base_url.replace("/v1/", "/")
                              fallback_1 = f"{base_no_v1}tasks/{task_id}"
                              fallback_2 = f"{base_no_v1}api-inference/v1/tasks/{task_id}"
                              
                              if task_url == f"{self.base_url}tasks/{task_id}":
                                  print(f"[ModelScope] 切换到回退 URL 1: {fallback_1}")
                                  task_url = fallback_1
                              elif task_url == fallback_1:
                                  print(f"[ModelScope] 切换到回退 URL 2: {fallback_2}")
                                  task_url = fallback_2
                          
                          time.sleep(poll_interval)
                          continue

                      raise RuntimeError(f"ModelScope 任务失败: {message}")
                
                elif status in ["PENDING", "RUNNING", "QUEUED"]:
                    # print(f"[ModelScope] 任务状态: {status}...")
                    time.sleep(poll_interval)
                else:
                    print(f"[ModelScope] 未知状态: {status}。响应: {poll_data}")
                    time.sleep(poll_interval)
                
            except RuntimeError as e:
                # 致命错误，重新抛出
                raise e
            except Exception as e:
                print(f"[ModelScope] 轮询异常 (将重试): {e}")
                time.sleep(poll_interval)
        
        raise Exception("ModelScope 图像生成在 120 秒后超时。")
