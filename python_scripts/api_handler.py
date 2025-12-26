import json
import os
import sys
import time
import argparse
import mimetypes
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
CONFIG_LOCAL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.local.json')
CONFIG_EXAMPLE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.example.json')

class APIHandler:
    def __init__(self, config_path=CONFIG_PATH):
        self.config = self._load_merged_config(config_path, CONFIG_LOCAL_PATH)
        self.dashscope_api_key = (
            os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("DASHSCOPE_APIKEY")
            or self.config.get('api_keys', {}).get('dashscope')
        )
        self.z_image_api_key = os.getenv("Z_IMAGE_API_KEY") or self.config.get('api_keys', {}).get('z_image')
        self.wan_api_key = os.getenv("WAN_API_KEY") or self.config.get('api_keys', {}).get('wan')
        self.output_dir = self.config.get('storage', {}).get('output_dir') or 'outputs'
        
    def _load_config(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"api_keys": {}, "models": {}, "endpoints": {}}

    def _merge_dicts(self, base, override):
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = self._merge_dicts(base[key], value)
            else:
                base[key] = value
        return base

    def _load_merged_config(self, base_path, local_path):
        base_config = self._load_config(base_path)
        if not base_config.get('endpoints') and os.path.exists(CONFIG_EXAMPLE_PATH):
            base_config = self._load_config(CONFIG_EXAMPLE_PATH)
        local_config = self._load_config(local_path)
        return self._merge_dicts(base_config, local_config)

    def _safe_dir_name(self, name):
        if not name:
            return "default"
        invalid = '<>:"/\\\\|?*'
        cleaned = ''.join('_' if c in invalid else c for c in name)
        cleaned = cleaned.strip().strip('.')
        return cleaned or "default"

    def _ensure_output_dir(self, category):
        base = os.path.abspath(self.output_dir)
        category_dir = os.path.join(base, self._safe_dir_name(category))
        os.makedirs(category_dir, exist_ok=True)
        return category_dir

    def _guess_extension(self, url, content_type):
        if content_type:
            ext = mimetypes.guess_extension(content_type.split(';')[0].strip())
            if ext:
                return ext
        if url:
            parsed = url.split('?')[0]
            _, ext = os.path.splitext(parsed)
            if ext and len(ext) <= 5:
                return ext
        return ".bin"

    def _download_to_file(self, url, category, prefix):
        category_dir = self._ensure_output_dir(category)
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        ext = self._guess_extension(url, resp.headers.get('Content-Type'))
        filename = f"{prefix}_{int(time.time() * 1000)}{ext}"
        out_path = os.path.join(category_dir, filename)
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
        return out_path

    def _get_headers(self, api_key=None):
        api_key = api_key or self.dashscope_api_key
        if not api_key:
            raise ValueError("Missing API key. Set DASHSCOPE_API_KEY or config.local.json")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def call_qwen(self, prompt, model=None):
        """
        Call Qwen model using OpenAI compatible endpoint.
        """
        endpoint = self.config['endpoints'].get('qwen')
        model = model or self.config['models'].get('qwen', 'qwen-max')
        
        print(f"Calling Qwen model: {model} at {endpoint}...")
        
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(endpoint, headers=self._get_headers(self.dashscope_api_key), json=payload)
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                return {"status": "success", "output": content}
            else:
                return {"status": "error", "code": response.status_code, "message": response.text}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def call_z_image(self, prompt, category="default"):
        """
        Call Z-Image model (using DashScope Multimodal Generation API).
        """
        endpoint = self.config['endpoints'].get('z_image')
        model = self.config['models'].get('z_image', 'qwen-image-plus')
        
        print(f"Calling Z-Image model: {model} at {endpoint}...")
        
        payload = {
            "model": model,
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "size": "1024*1024",
                "n": 1
            }
        }
        
        try:
            headers = self._get_headers(self.z_image_api_key or self.dashscope_api_key)
            headers["X-DashScope-Async"] = "enable"
            
            response = requests.post(endpoint, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if 'output' in data and 'task_status' in data['output']:
                    task_id = data['output']['task_id']
                    return self._wait_for_task(task_id, category=category, prefix="z_image")
                elif 'output' in data and 'results' in data['output']:
                    img_url = data['output']['results'][0]['url']
                    saved_path = self._download_to_file(img_url, category, "z_image")
                    return {"status": "success", "url": img_url, "saved_path": saved_path}
                else:
                     return {"status": "unknown_response", "data": data}
            else:
                return {"status": "error", "code": response.status_code, "message": response.text}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def call_wan(self, prompt, model=None, category="default"):
        """
        Call Wan model for video generation.
        """
        endpoint = self.config['endpoints'].get('wan')
        model = model or self.config['models'].get('wan', 'wan2.1-t2v-turbo')
        
        print(f"Calling Wan model: {model} at {endpoint}...")
        
        payload = {
            "model": model,
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "size": "1280*720",
                "n": 1
            }
        }
        
        try:
            headers = self._get_headers(self.wan_api_key or self.dashscope_api_key)
            headers["X-DashScope-Async"] = "enable"
            
            response = requests.post(endpoint, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if 'output' in data and 'task_id' in data['output']:
                    task_id = data['output']['task_id']
                    print(f"Task submitted: {task_id}")
                    return self._wait_for_task(task_id, category=category, prefix="wan")
                else:
                    return {"status": "unexpected_response", "data": data}
            else:
                return {"status": "error", "code": response.status_code, "message": response.text}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _wait_for_task(self, task_id, category="default", prefix="result"):
        print(f"Waiting for task {task_id} to complete...")
        task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        
        headers = self._get_headers(self.dashscope_api_key)
        
        start_time = time.time()
        timeout = 600
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(task_url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    task_status = data.get('output', {}).get('task_status')
                    
                    if task_status == 'SUCCEEDED':
                        if 'results' in data['output']:
                            result_url = data['output']['results'][0].get('url') or data['output']['results'][0].get('video_url')
                            saved_path = self._download_to_file(result_url, category, prefix)
                            return {"status": "success", "url": result_url, "saved_path": saved_path, "task_id": task_id}
                        elif 'video_url' in data['output']:
                             result_url = data['output']['video_url']
                             saved_path = self._download_to_file(result_url, category, prefix)
                             return {"status": "success", "url": result_url, "saved_path": saved_path, "task_id": task_id}
                        else:
                             return {"status": "success", "data": data['output'], "task_id": task_id}
                    
                    elif task_status in ['FAILED', 'CANCELED']:
                        return {"status": "failed", "message": data.get('output', {}).get('message'), "task_id": task_id}
                    
                    else:
                        print(f"Task status: {task_status}. Waiting...")
                        time.sleep(5)
                else:
                    return {"status": "error", "code": response.status_code, "message": response.text}
            except Exception as e:
                return {"status": "error", "message": str(e)}
                
        return {"status": "timeout", "task_id": task_id}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=["qwen", "wan", "z_image"])
    parser.add_argument("prompt")
    parser.add_argument("--category", default="default")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    
    handler = APIHandler()
    
    if args.service == "qwen":
        result = handler.call_qwen(args.prompt, model=args.model)
    elif args.service == "wan":
        result = handler.call_wan(args.prompt, model=args.model, category=args.category)
    else:
        result = handler.call_z_image(args.prompt, category=args.category)

    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
