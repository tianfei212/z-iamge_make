"""
/**
 * @file backend/services/model_registry_service.py
 * @description 模型列表服务：从配置读取可用模型信息。
 */
"""

from __future__ import annotations

from typing import Dict, List

from backend.config import Settings, load_settings


def list_available_models(settings: Settings | None = None) -> Dict[str, List[dict]]:
    s = settings or load_settings()
    
    # 默认模型列表，作为后备
    default_models = [
        {
            "id": "aliyun-wan2.6",
            "name": "Aliyun Wan2.6",
            "provider": "aliyun",
            "modelName": "wan2.6-t2i",
            "description": "Bailian Multimodal Generation",
        },
        {
            "id": "aliyun-z-image-turbo",
            "name": "Aliyun Z-Image Turbo",
            "provider": "aliyun",
            "modelName": "z-image-turbo",
            "description": "Bailian Multimodal Generation",
        },
        {
            "id": "aliyun-qwen",
            "name": "Aliyun Qwen",
            "provider": "aliyun",
            "modelName": "qwen-max",
            "description": "DashScope Compatible Mode",
        },
    ]

    # 从配置中加载模型定义（如果有）
    # 这里假设 settings.models 只是简单的 key-value 映射 (alias -> real_name)
    # 为了支持更高级的配置驱动，我们保留原有的映射逻辑，但允许从配置覆盖 modelName
    
    models = []
    for m in default_models:
        # 尝试从 settings.models 中查找对应的 modelName
        # key 映射规则：aliyun-wan2.6 -> wan, aliyun-z-image-turbo -> z_image, aliyun-qwen -> qwen
        config_key = ""
        if "wan" in m["id"]:
            config_key = "wan"
        elif "z-image" in m["id"]:
            config_key = "z_image"
        elif "qwen" in m["id"]:
            config_key = "qwen"
            
        if config_key and config_key in s.models:
             m["modelName"] = s.models[config_key]
        
        models.append(m)

    return {"models": models}

