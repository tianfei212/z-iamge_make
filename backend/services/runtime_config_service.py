from typing import Dict, Any, List
import backend.config.settings as cfg_settings
from backend.services.model_service import list_models as db_list_models
from backend.services.category_service import list_categories as db_list_categories
from backend.services.prompt_service import list_prompts as db_list_prompts
from backend.services.settings_service import get_global_settings as db_get_global
from backend.services.model_registry_service import list_available_models as cfg_list_available_models

def _cfg_models(settings) -> List[Dict[str, Any]]:
    raw = settings.raw
    lst = raw.get("models_list")
    if isinstance(lst, list) and lst:
        return [
            {
                "id": m.get("id"),
                "name": m.get("name"),
                "provider": m.get("provider"),
                "model_name": m.get("model_name"),
                "description": m.get("description"),
                "enabled": 1 if m.get("enabled", 1) else 0,
            }
            for m in lst
            if isinstance(m, dict)
        ]
    cfg = cfg_list_available_models(settings).get("models", [])
    return [
        {
            "id": m.get("id"),
            "name": m.get("name"),
            "provider": m.get("provider"),
            "model_name": m.get("modelName"),
            "description": m.get("description"),
            "enabled": 1,
        }
        for m in cfg
    ]

def _cfg_categories(settings) -> List[str]:
    raw = settings.raw
    arr = raw.get("categories")
    if isinstance(arr, list) and arr:
        return [str(x) for x in arr]
    return []

def _cfg_prompts(settings) -> Dict[str, str]:
    raw = settings.raw
    m = raw.get("prompts_map")
    if isinstance(m, dict) and m:
        return {str(k): str(v) for k, v in m.items()}
    return {}

def _cfg_global(settings) -> Dict[str, Any]:
    raw = settings.raw
    g = raw.get("global")
    if isinstance(g, dict) and g:
        return {
            "common_subject": str(g.get("common_subject", "") or ""),
            "global_style": str(g.get("global_style", "") or ""),
            "negative_prompt": str(g.get("negative_prompt", "") or ""),
        }
    p = settings.prompts
    return {
        "common_subject": "",
        "global_style": str(p.get("default_style", "") or ""),
        "negative_prompt": str(p.get("default_negative_prompt", "") or ""),
    }

def get_runtime_config() -> Dict[str, Any]:
    s = cfg_settings.load_settings()
    mode = s.operation_mode
    if mode == "database":
        try:
            models = db_list_models()
            categories = db_list_categories()
            prompts = db_list_prompts()
            global_cfg = db_get_global()
            if not models and not categories and not prompts and not any(global_cfg.values()):
                return {
                    "models": _cfg_models(s),
                    "categories": _cfg_categories(s),
                    "prompts": _cfg_prompts(s),
                    "global": _cfg_global(s),
                    "source": "config_file",
                }
            return {
                "models": models,
                "categories": categories,
                "prompts": prompts,
                "global": global_cfg,
                "source": "database",
            }
        except Exception:
            return {
                "models": _cfg_models(s),
                "categories": _cfg_categories(s),
                "prompts": _cfg_prompts(s),
                "global": _cfg_global(s),
                "source": "config_file",
            }
    return {
        "models": _cfg_models(s),
        "categories": _cfg_categories(s),
        "prompts": _cfg_prompts(s),
        "global": _cfg_global(s),
        "source": "config_file",
    }
