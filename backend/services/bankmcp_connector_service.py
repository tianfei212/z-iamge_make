"""
/**
 * @file backend/services/bankmcp_connector_service.py
 * @description bankmcp 连接器服务：Qwen/Wan/Z-Image 与中英互译。
 */
"""

from __future__ import annotations

from typing import Optional

from backend.services.dashscope_client_service import DashScopeClient
from backend.services.translation_service import translate_zh_en as _translate_zh_en


def connect_qwen(prompt: str, model: Optional[str] = None, client: Optional[DashScopeClient] = None):
    c = client or DashScopeClient()
    return c.call_qwen(prompt, model=model)


def connect_wan(
    prompt: str,
    model: Optional[str] = None,
    category: str = "default",
    size: str = "1024*1024",
    negative_prompt: str = "",
    client: Optional[DashScopeClient] = None,
):
    c = client or DashScopeClient()
    return c.call_wan(
        prompt,
        model=model,
        category=category,
        size=size,
        negative_prompt=negative_prompt,
    )


def connect_z_image(
    prompt: str,
    category: str = "default",
    size: str = "1024*1024",
    prompt_extend: bool = False,
    client: Optional[DashScopeClient] = None,
):
    c = client or DashScopeClient()
    return c.call_z_image(prompt, category=category, size=size, prompt_extend=prompt_extend)


def translate_zh_en(text: str, model: Optional[str] = None, client: Optional[DashScopeClient] = None):
    return _translate_zh_en(text, model=model, client=client)

