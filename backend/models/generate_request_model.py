"""
/**
 * @file backend/models/generate_request_model.py
 * @description 生成请求模型（Pydantic）。
 * @note 按照项目要求，本文件提供 CRUD 方法（以内存存储实现）。
 */
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


_STORE: Dict[str, Dict[str, Any]] = {}


class GenerateRequest(BaseModel):
    service: str = Field(..., pattern="^(wan|z_image|qwen)$")
    prompt: str
    model: Optional[str] = None
    category: str = "default"
    size: str = "1024*1024"
    resolution: Optional[str] = "1K"  # 新增画质参数
    aspect_ratio: Optional[str] = "16:9"  # 新增比例参数 (用于日志或文件名)
    negative_prompt: str = ""
    prompt_extend: bool = False
    count: int = Field(1, ge=1, le=50)

    @staticmethod
    def create(key: str, value: Dict[str, Any]) -> None:
        _STORE[key] = dict(value)

    @staticmethod
    def read(key: str) -> Optional[Dict[str, Any]]:
        return _STORE.get(key)

    @staticmethod
    def update(key: str, value: Dict[str, Any]) -> None:
        if key not in _STORE:
            _STORE[key] = {}
        _STORE[key].update(dict(value))

    @staticmethod
    def delete(key: str) -> None:
        _STORE.pop(key, None)
