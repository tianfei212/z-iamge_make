"""
/**
 * @file backend/controllers/health_controller.py
 * @description 健康检查控制器。
 */
"""

from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
def health():
    from backend.config import load_settings
    import os

    settings = load_settings()
    
    # Check API keys
    api_keys_status = {
        "dashscope": bool(settings.resolve_dashscope_key()),
        "wan": bool(settings.resolve_wan_key()),
        "z_image": bool(settings.resolve_z_image_key()),
    }
    
    # Check output directory
    output_dir = settings.output_dir
    fs_status = {
        "output_dir_exists": os.path.isdir(output_dir),
        "output_dir_writable": os.access(output_dir, os.W_OK) if os.path.isdir(output_dir) else False
    }

    # Determine overall status
    is_healthy = all(api_keys_status.values()) and all(fs_status.values())

    return {
        "status": "ok" if is_healthy else "degraded",
        "checks": {
            "api_keys": api_keys_status,
            "filesystem": fs_status
        }
    }
