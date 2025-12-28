"""
/**
 * @file backend/controllers/models_controller.py
 * @description 模型列表控制器。
 */
"""

from fastapi import APIRouter

from backend.services import list_available_models
from backend.config import load_settings


router = APIRouter()


@router.get("/api/models")
def list_models():
    return list_available_models()

@router.get("/api/config/prompts")
def get_prompt_config():
    settings = load_settings()
    return settings.prompts

