"""
/**
 * @file backend/models/__init__.py
 * @description 数据模型导出。
 */
"""

from .generate_request_model import GenerateRequest
from .translate_request_model import TranslateRequest

__all__ = ["GenerateRequest", "TranslateRequest"]

