"""
/**
 * @file backend/services/dashscope_client_service.py
 * @description DashScope 调用封装：Qwen / Wan / Z-Image。
 */
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import requests

from backend.config import Settings, load_settings
from backend.utils import file_to_data_url, guess_extension, safe_dir_name


import threading

class DashScopeClient:
    def __init__(self, settings: Optional[Settings] = None):
        # We don't hold onto settings anymore, we fetch it dynamically
        self._initial_settings = settings 
        # Simple memory cache for prompt refinement: 
        # Key: (prompt, category, default_style, default_negative, role)
        # Value: (positive, negative, timestamp)
        self._prompt_cache = {}
        self._cache_lock = threading.Lock()

    @property
    def settings(self) -> Settings:
        return self._initial_settings or load_settings()
        
    @property
    def output_dir(self) -> str:
        return self.settings.output_dir

    @property
    def dashscope_api_key(self) -> Optional[str]:
        return self.settings.resolve_dashscope_key()
        
    @property
    def z_image_api_key(self) -> Optional[str]:
        return self.settings.resolve_z_image_key()
        
    @property
    def wan_api_key(self) -> Optional[str]:
        return self.settings.resolve_wan_key()

    def _ensure_output_dir(self, category: str) -> str:
        base = os.path.abspath(self.output_dir)
        category_dir = os.path.join(base, safe_dir_name(category))
        os.makedirs(category_dir, exist_ok=True)
        return category_dir

    def _get_headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        key = api_key or self.dashscope_api_key
        if not key:
            raise ValueError("Missing API key. Set DASHSCOPE_API_KEY or config.local.json")
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def _download_to_file(self, url: str, category: str, prefix: str, resolution: str = "") -> str:
        category_dir = self._ensure_output_dir(category)
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        ext = guess_extension(url, resp.headers.get("Content-Type"))
        
        # 生成的文件命名规则：模型_yyyymmddhh24miss_ms_画质.类型（确保并发唯一）
        # prefix 传入的通常是模型类型 (wan 或 z_image)
        res_suffix = f"_{resolution}" if resolution else ""
        ts = time.time()
        timestamp_str = time.strftime("%Y%m%d%H%M%S", time.localtime(ts))
        ms = int((ts - int(ts)) * 1000)
        filename = f"{prefix}_{timestamp_str}_{ms:03d}{res_suffix}{ext}"
        
        out_path = os.path.join(category_dir, filename)
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
        
        # 自动生成缩略图（如果需要，此处可以调用生成逻辑，但目前 images_controller 是 lazy 生成）
        # 这里仅确保文件已保存
        return out_path

    def _extract_first_result_url(self, data: Any) -> Optional[str]:
        if not isinstance(data, dict):
            return None
        output = data.get("output")
        if not isinstance(output, dict):
            return None

        results = output.get("results")
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                for key in ("url", "image", "video_url", "video"):
                    value = first.get(key)
                    if isinstance(value, str) and value:
                        return value
                    if isinstance(value, dict) and isinstance(value.get("url"), str) and value.get("url"):
                        return value.get("url")

        choices = output.get("choices")
        if isinstance(choices, list) and choices:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, list):
                        for part in content:
                            if not isinstance(part, dict):
                                continue
                            image = part.get("image")
                            if isinstance(image, str) and image:
                                return image
                            image_url = part.get("image_url")
                            if isinstance(image_url, dict) and isinstance(image_url.get("url"), str) and image_url.get("url"):
                                return image_url.get("url")
                            url = part.get("url")
                            if isinstance(url, str) and url:
                                return url
                            video_url = part.get("video_url")
                            if isinstance(video_url, str) and video_url:
                                return video_url
                            video = part.get("video")
                            if isinstance(video, str) and video:
                                return video

        return None

    def refine_prompt(self, prompt: str, category: str, default_style: str, default_negative_prompt: str, role: str) -> Dict[str, str]:
        """
        Uses Qwen to refine the prompt and generate a negative prompt.
        Uses in-memory cache to avoid redundant calls.
        """
        # Check Cache
        cache_key = (prompt, category, default_style, default_negative_prompt, role or "")
        now = time.time()
        
        with self._cache_lock:
            if cache_key in self._prompt_cache:
                pos, neg, ts = self._prompt_cache[cache_key]
                # Cache valid for 1 hour (3600s)
                if now - ts < 3600:
                    print(f"[Refine] Cache Hit for prompt: {prompt[:30]}...")
                    return {"positive_prompt": pos, "negative_prompt": neg}
                else:
                    del self._prompt_cache[cache_key]

        # Construct the instruction for Qwen
        instruction = f"""
{role}

Input Data:
- Category: {category}
- User Prompt: {prompt}
- Preferred Style: {default_style}
- Default Negative Prompt: {default_negative_prompt}

Task:
1. Analyze the User Prompt and Category.
2. Expand it into a rich, detailed English prompt (Positive Prompt) incorporating the Preferred Style if appropriate.
3. Create a strong Negative Prompt to ensure quality.

Output Format (Strict JSON):
{{
  "positive_prompt": "...",
  "negative_prompt": "..."
}}
"""
        try:
            # Reuse call_qwen
            result = self.call_qwen(instruction)
            if result.get("status") == "success":
                content = result.get("output", "")
                # Try to parse JSON from content
                # Qwen might wrap JSON in markdown code blocks ```json ... ```
                import json
                import re
                
                # Strip markdown code blocks if present
                json_str = content
                match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if match:
                    json_str = match.group(1)
                elif re.search(r'```\s*(.*?)\s*```', content, re.DOTALL):
                     match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
                     if match:
                        json_str = match.group(1)

                try:
                    data = json.loads(json_str)
                    pos = data.get("positive_prompt")
                    neg = data.get("negative_prompt")
                    if pos and neg:
                        # Update Cache
                        with self._cache_lock:
                            self._prompt_cache[cache_key] = (pos, neg, now)
                            
                        return {"positive_prompt": pos, "negative_prompt": neg}
                except json.JSONDecodeError:
                    print(f"[Refine] JSON parse failed: {json_str}")
                    pass
            
            print(f"[Refine] Qwen failed or invalid output. Using original.")
            return {"positive_prompt": prompt, "negative_prompt": default_negative_prompt}
            
        except Exception as e:
            print(f"[Refine] Error: {e}")
            return {"positive_prompt": prompt, "negative_prompt": default_negative_prompt}

    def call_qwen(self, prompt: str, model: Optional[str] = None):
        endpoint = self.settings.endpoints.get("qwen")
        model_name = model or self.settings.models.get("qwen", "qwen-max")
        payload = {"model": model_name, "messages": [{"role": "user", "content": prompt}]}
        try:
            response = requests.post(endpoint, headers=self._get_headers(self.dashscope_api_key), json=payload)
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return {"status": "success", "output": content}
            return {"status": "error", "code": response.status_code, "message": response.text}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def call_z_image(self, prompt: str, category: str = "default", size: str = "1024*1024", prompt_extend: bool = False, resolution: str = "", seed: Optional[int] = None, temperature: Optional[float] = None, top_p: Optional[float] = None):
        endpoint = self.settings.endpoints.get("z_image")
        model_name = self.settings.models.get("z_image", "z-image-turbo")

        parsed_size = None
        if isinstance(size, str):
            parts = size.lower().split("*")
            if len(parts) == 2:
                try:
                    w = int(parts[0].strip())
                    h = int(parts[1].strip())
                    if w > 0 and h > 0 and (w * h) >= (512 * 512) and (w * h) <= (2048 * 2048):
                        parsed_size = f"{w}*{h}"
                except ValueError:
                    parsed_size = None
        resolved_size = parsed_size or "1024*1024"

        payload = {
            "model": model_name,
            "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
            "parameters": {"prompt_extend": bool(prompt_extend), "size": resolved_size},
        }
        
        if seed is not None:
            payload["parameters"]["seed"] = seed
        if temperature is not None:
            payload["parameters"]["temperature"] = temperature
        if top_p is not None:
            payload["parameters"]["top_p"] = top_p
        
        print(f"[{model_name}] Final Prompt: {prompt}")
        if seed is not None:
            print(f"[{model_name}] Seed: {seed}")
        if temperature is not None:
            print(f"[{model_name}] Temperature: {temperature}")
        if top_p is not None:
            print(f"[{model_name}] Top P: {top_p}")

        try:
            headers = self._get_headers(self.z_image_api_key or self.dashscope_api_key)
            response = requests.post(endpoint, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data.get("output"), dict) and data["output"].get("task_id"):
                    task_id = data["output"]["task_id"]
                    return self._wait_for_task(task_id, category=category, prefix="z_image", resolution=resolution)
                url = self._extract_first_result_url(data)
                if url:
                    saved_path = self._download_to_file(url, category, "z_image", resolution=resolution)
                    return {"status": "success", "url": url, "saved_path": saved_path}
                return {"status": "unknown_response", "data": data}
            return {"status": "error", "code": response.status_code, "message": response.text}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def call_wan(
        self,
        prompt: str,
        model: Optional[str] = None,
        category: str = "default",
        size: str = "1024*1024",
        negative_prompt: str = "",
        resolution: str = "",
        seed: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ):
        endpoint = self.settings.endpoints.get("wan") or self.settings.endpoints.get("wan_image")
        model_name = model or self.settings.models.get("wan", "wan2.6-t2i")

        payload: Dict[str, Any] = {
            "model": model_name,
            "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
            "parameters": {"size": size, "n": 1, "prompt_extend": True, "watermark": False},
        }
        if negative_prompt:
            payload["parameters"]["negative_prompt"] = negative_prompt
            
        if seed is not None:
            payload["parameters"]["seed"] = seed
        if temperature is not None:
            payload["parameters"]["temperature"] = temperature
        if top_p is not None:
            payload["parameters"]["top_p"] = top_p
            
        print(f"[{model_name}] Final Prompt: {prompt}")
        if negative_prompt:
            print(f"[{model_name}] Negative Prompt: {negative_prompt}")
        if seed is not None:
            print(f"[{model_name}] Seed: {seed}")
        if temperature is not None:
            print(f"[{model_name}] Temperature: {temperature}")
        if top_p is not None:
            print(f"[{model_name}] Top P: {top_p}")

        try:
            headers = self._get_headers(self.wan_api_key or self.dashscope_api_key)
            response = requests.post(endpoint, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data.get("output"), dict) and data["output"].get("task_id"):
                    task_id = data["output"]["task_id"]
                    return self._wait_for_task(task_id, category=category, prefix="wan", resolution=resolution)
                url = self._extract_first_result_url(data)
                if url:
                    saved_path = self._download_to_file(url, category, "wan", resolution=resolution)
                    return {"status": "success", "url": url, "saved_path": saved_path}
                return {"status": "unexpected_response", "data": data}
            return {"status": "error", "code": response.status_code, "message": response.text}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _wait_for_task(self, task_id: str, category: str = "default", prefix: str = "result", resolution: str = ""):
        task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        headers = self._get_headers(self.dashscope_api_key)
        start_time = time.time()
        timeout = 600

        while time.time() - start_time < timeout:
            try:
                response = requests.get(task_url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    task_status = data.get("output", {}).get("task_status")
                    if task_status == "SUCCEEDED":
                        if "results" in data["output"]:
                            result_url = data["output"]["results"][0].get("url") or data["output"]["results"][0].get(
                                "video_url"
                            )
                            saved_path = self._download_to_file(result_url, category, prefix, resolution=resolution)
                            return {"status": "success", "url": result_url, "saved_path": saved_path, "task_id": task_id}
                        if "video_url" in data["output"]:
                            result_url = data["output"]["video_url"]
                            saved_path = self._download_to_file(result_url, category, prefix, resolution=resolution)
                            return {"status": "success", "url": result_url, "saved_path": saved_path, "task_id": task_id}
                        return {"status": "success", "data": data["output"], "task_id": task_id}
                    if task_status in ["FAILED", "CANCELED"]:
                        return {"status": "failed", "message": data.get("output", {}).get("message"), "task_id": task_id}
                    time.sleep(5)
                else:
                    return {"status": "error", "code": response.status_code, "message": response.text}
            except Exception as e:
                return {"status": "error", "message": str(e)}

        return {"status": "timeout", "task_id": task_id}

    def to_data_url_if_local(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(result, dict) or result.get("status") != "success":
            return result
        saved_path = result.get("saved_path")
        
        # 将缩略图传给前端 (实际上这里返回的是原图的 path，前端通过 /api/images/{id}/thumb 访问)
        # 为了适配前端需求，我们构造符合前端 ImageItem 格式的 URL
        if isinstance(saved_path, str) and saved_path and os.path.exists(saved_path):
            from backend.utils import encode_image_id
             
            # 计算相对路径，用于生成 ID
            # saved_path: .../outputs/category/filename.ext
            # output_dir: .../outputs
             
            # 简单起见，这里假设 saved_path 就在 output_dir 下
            try:
                rel_path = os.path.relpath(saved_path, self.output_dir)
                image_id = encode_image_id(rel_path)
                 
                # 返回前端可用的 URL
                return {
                    "status": "success",
                    "url": f"/api/images/{image_id}/thumb",
                    "originalUrl": f"/api/images/{image_id}/raw",
                    "saved_path": saved_path
                }
            except ValueError:
                pass

        # Fallback to data URL if relpath fails (should not happen if logic is correct)
        if isinstance(saved_path, str) and saved_path and os.path.exists(saved_path):
            return {"status": "success", "url": file_to_data_url(saved_path), "saved_path": saved_path}
            
        url = result.get("url")
        if isinstance(url, str) and url:
            return {"status": "success", "url": url}
        return result
