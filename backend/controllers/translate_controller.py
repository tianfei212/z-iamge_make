"""
/**
 * @file backend/controllers/translate_controller.py
 * @description 翻译控制器（中英互译）。
 */
"""

from fastapi import APIRouter, HTTPException

from backend.models.translate_request_model import TranslateRequest
from backend.services import translate_zh_en


router = APIRouter()


@router.post("/api/translate")
def translate(req: TranslateRequest):
    result = translate_zh_en(req.text, model=req.model)
    if isinstance(result, dict):
        if result.get("status") == "success":
            return result
        
        # Propagate error code if available
        code = result.get("code", 500)
        # Ensure code is a valid HTTP status code
        status_code = code if isinstance(code, int) and 100 <= code <= 599 else 500
        
        print(f"Translation failed: {result}")
        raise HTTPException(status_code=status_code, detail=result)
        
    raise HTTPException(status_code=500, detail={"status": "error", "message": "Unknown error", "result": str(result)})
