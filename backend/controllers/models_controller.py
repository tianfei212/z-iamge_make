"""
/**
 * @file backend/controllers/models_controller.py
 * @description 模型列表控制器。
 */
"""

from fastapi import APIRouter, HTTPException

from backend.services import list_available_models
from backend.config import load_settings
from backend.services.model_service import list_models as db_list_models, create_model, update_model, delete_model, update_limit_by_model_name
from backend.services.runtime_config_service import get_runtime_config
from typing import Dict, Any


router = APIRouter()


@router.get("/api/models")
def list_models():
    cfg = get_runtime_config()
    models = cfg.get("models") or []
    return {"models": models}

@router.get("/api/config/prompts")
def get_prompt_config():
    settings = load_settings()
    return settings.prompts

@router.post("/api/models")
def post_model(payload: dict):
    for k in ["id", "name", "provider", "model_name"]:
        if not str(payload.get(k, "")).strip():
            raise HTTPException(status_code=400, detail={"error": f"{k} required"})
    create_model(payload)
    return {"status": "ok"}

@router.put("/api/models/{model_id}")
def put_model(model_id: str, payload: dict):
    if not model_id:
        raise HTTPException(status_code=400, detail={"error": "id required"})
    update_model(model_id, payload or {})
    return {"status": "ok"}

@router.delete("/api/models/{model_id}")
def remove_model(model_id: str):
    if not model_id:
        raise HTTPException(status_code=400, detail={"error": "id required"})
    delete_model(model_id)
    return {"status": "ok"}

# Compatibility aliases for environments missing config_controller
@router.get("/api/config/limits")
def compat_get_limits():
    limits: Dict[str, int] = {}
    try:
        for m in db_list_models():
            if m.get("model_name"):
                limits[m["model_name"]] = int(m.get("max_limit") or 0)
    except Exception:
        pass
    if not limits:
        limits = {"wan2.6-t2i": 2, "z-image-turbo": 4}
    return {"model_limits": limits}

@router.post("/api/config/update")
def compat_update_all(payload: dict):
    model_limits = payload.get("model_limits") or {}
    if isinstance(model_limits, dict):
        for model_name, v in model_limits.items():
            try:
                update_limit_by_model_name(str(model_name), int(v))
            except Exception:
                pass
    cfg = get_runtime_config()
    return {
        "status": "ok",
        "global": cfg.get("global"),
        "categories": cfg.get("categories") or [],
        "prompts": cfg.get("prompts") or {},
        "model_limits": compat_get_limits().get("model_limits", {}),
    }
