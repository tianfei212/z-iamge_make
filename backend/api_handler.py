"""
/**
 * @file backend/api_handler.py
 * @description 兼容层：保留 APIHandler 名称与方法签名，内部转发到服务层实现。
 */
"""

from __future__ import annotations

from typing import Optional

from backend.config import Settings, load_settings
from backend.services.dashscope_client_service import DashScopeClient
from backend.utils import file_to_data_url


class APIHandler:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or load_settings()
        self.config = self.settings.raw
        self._client = DashScopeClient(settings=self.settings)

        self.dashscope_api_key = self._client.dashscope_api_key
        self.z_image_api_key = self._client.z_image_api_key
        self.wan_api_key = self._client.wan_api_key

    def file_to_data_url(self, file_path: str) -> str:
        return file_to_data_url(file_path)

    def call_qwen(self, prompt: str, model: Optional[str] = None):
        return self._client.call_qwen(prompt, model=model)

    def call_wan(
        self,
        prompt: str,
        model: Optional[str] = None,
        category: str = "default",
        size: str = "1024*1024",
        negative_prompt: str = "",
    ):
        return self._client.call_wan(
            prompt,
            model=model,
            category=category,
            size=size,
            negative_prompt=negative_prompt,
        )

    def call_z_image(self, prompt: str, category: str = "default", size: str = "1024*1024", prompt_extend: bool = False):
        return self._client.call_z_image(prompt, category=category, size=size, prompt_extend=prompt_extend)
