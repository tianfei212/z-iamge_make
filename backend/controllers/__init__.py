"""
/**
 * @file backend/controllers/__init__.py
 * @description 控制器（路由）导出。
 */
"""

from .generate_controller import router as generate_router
from .health_controller import router as health_router
from .images_controller import router as images_router
from .models_controller import router as models_router
from .translate_controller import router as translate_router
from .tasks_controller import router as tasks_router
from .download_controller import router as download_router
from .db_controller import router as db_router

__all__ = [
    "generate_router",
    "health_router",
    "images_router",
    "models_router",
    "translate_router",
    "tasks_router",
    "download_router",
    "db_router",
]
