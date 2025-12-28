"""
/**
 * @file backend/models/translate_request_model.py
 * @description 翻译请求模型（Pydantic）。
 * @note 按照项目要求，本文件提供 CRUD 方法（以内存存储实现）。
 */
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel


class TranslateRequest(BaseModel):
    text: str
    model: Optional[str] = None

