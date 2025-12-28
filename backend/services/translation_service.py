"""
/**
 * @file backend/services/translation_service.py
 * @description 中英互译服务（基于 Qwen）。
 */
"""

from __future__ import annotations

from typing import Optional

from backend.services.dashscope_client_service import DashScopeClient


def translate_zh_en(text: str, model: Optional[str] = None, client: Optional[DashScopeClient] = None):
    h = client or DashScopeClient()
    cleaned = (text or "").strip()
    if not cleaned:
        return {"status": "success", "output": ""}
    prompt = (
        "Translate the following text. If it is Chinese, translate to English. "
        "If it is English, translate to Chinese. Only return the translated text without any explanation: "
        f"\"{cleaned}\""
    )
    return h.call_qwen(prompt, model=model)

