"""
/**
 * @file backend/bankmcp/connectors.py
 * @description 兼容层：对外保留 bankmcp 连接函数，内部转发到 services。
 */
"""

from __future__ import annotations

from typing import Optional

from backend.api_handler import APIHandler
from backend.services.bankmcp_connector_service import (
    connect_qwen as _connect_qwen,
    connect_wan as _connect_wan,
    connect_z_image as _connect_z_image,
    translate_zh_en as _translate_zh_en,
)
from backend.services.dashscope_client_service import DashScopeClient


def connect_qwen(
    prompt: str,
    model: Optional[str] = None,
    handler: Optional[APIHandler] = None,
    client: Optional[DashScopeClient] = None,
):
    if client is None and handler is not None:
        client = handler._client
    return _connect_qwen(prompt, model=model, client=client)


def translate_zh_en(
    text: str,
    model: Optional[str] = None,
    handler: Optional[APIHandler] = None,
    client: Optional[DashScopeClient] = None,
):
    if client is None and handler is not None:
        client = handler._client
    return _translate_zh_en(text, model=model, client=client)


def connect_wan(
    prompt: str,
    model: Optional[str] = None,
    category: str = "default",
    size: str = "1024*1024",
    negative_prompt: str = "",
    handler: Optional[APIHandler] = None,
    client: Optional[DashScopeClient] = None,
):
    if client is None and handler is not None:
        client = handler._client
    return _connect_wan(
        prompt,
        model=model,
        category=category,
        size=size,
        negative_prompt=negative_prompt,
        client=client,
    )


def connect_z_image(
    prompt: str,
    category: str = "default",
    size: str = "1024*1024",
    prompt_extend: bool = False,
    handler: Optional[APIHandler] = None,
    client: Optional[DashScopeClient] = None,
):
    if client is None and handler is not None:
        client = handler._client
    return _connect_z_image(prompt, category=category, size=size, prompt_extend=prompt_extend, client=client)
