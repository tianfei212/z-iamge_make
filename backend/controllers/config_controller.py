from fastapi import APIRouter, HTTPException
from backend.services.settings_service import get_global_settings, update_global_settings
from backend.services.runtime_config_service import get_runtime_config
from backend.services.category_service import create_category, list_categories
from backend.services.prompt_service import upsert_prompt, list_prompts
from backend.config.settings import load_settings, reload_settings, CONFIG_LOCAL_PATH
from backend.services.model_service import list_models, get_model_id_by_model_name, update_model, update_limit_by_model_name
from typing import Dict, Any
import os
import json

router = APIRouter()

@router.get("/api/config/runtime")
def get_runtime():
    return get_runtime_config()

@router.get("/api/config/global")
def get_global():
    return get_global_settings()

@router.put("/api/config/global")
def put_global(payload: dict):
    update_global_settings(payload or {})
    return {"status": "ok"}

@router.get("/api/config/limits")
def get_limits():
    limits: Dict[str, int] = {}
    try:
        for m in list_models():
            if m.get("model_name"):
                limits[m["model_name"]] = int(m.get("max_limit") or 0)
    except Exception:
        pass
    if not limits:
        limits = {"wan2.6-t2i": 2, "z-image-turbo": 4}
    return {"model_limits": limits}

@router.post("/api/config/update")
def update_all(payload: dict):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail={"error": "invalid payload"})
    global_cfg = payload.get("global") or {}
    categories = payload.get("categories") or []
    prompts = payload.get("prompts") or {}
    model_limits = payload.get("model_limits") or {}
    try:
        update_global_settings({
            "common_subject": str(global_cfg.get("common_subject", "") or ""),
            "global_style": str(global_cfg.get("global_style", "") or ""),
            "negative_prompt": str(global_cfg.get("negative_prompt", "") or "")
        })
        if isinstance(categories, list):
            for name in categories:
                if not isinstance(name, str):
                    continue
                if name.strip():
                    create_category(name.strip())
        if isinstance(prompts, dict):
            for cat, pr in prompts.items():
                upsert_prompt(str(cat), str(pr or ""))
        # persist model limits to database
        if isinstance(model_limits, dict):
            for model_name, v in model_limits.items():
                try:
                    update_limit_by_model_name(str(model_name), int(v))
                except Exception:
                    pass
        # return merged view
        return {
            "status": "ok",
            "global": get_global_settings(),
            "categories": list_categories(),
            "prompts": list_prompts(),
            "model_limits": get_limits().get("model_limits", {}),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"update failed: {e}"})

@router.post("/api/config/reload")
def force_reload():
    reload_settings()
    return {"status": "ok", "runtime": get_runtime_config()}

@router.get("/api/config/flags")
def get_flags():
    s = load_settings()
    return {"enable_prompt_update_request": bool(getattr(s, "enable_prompt_update_request", False))}

@router.put("/api/config/flags")
def put_flags(payload: dict):
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail={"error": "invalid payload"})
    val = bool(payload.get("enable_prompt_update_request", False))
    try:
        data: Dict[str, Any] = {}
        if os.path.exists(CONFIG_LOCAL_PATH):
            try:
                with open(CONFIG_LOCAL_PATH, "r") as f:
                    raw = json.load(f)
                    if isinstance(raw, dict):
                        data = raw
            except Exception:
                data = {}
        data["enable_prompt_update_request"] = val
        os.makedirs(os.path.dirname(CONFIG_LOCAL_PATH), exist_ok=True)
        with open(CONFIG_LOCAL_PATH, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        reload_settings()
        return {"status": "ok", "enable_prompt_update_request": val}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"save flags failed: {e}"})
