"""
/**
 * @file backend/utils/file_utils.py
 * @description 文件处理工具：目录命名、扩展名推断、DataURL 编码。
 */
"""

from __future__ import annotations

import base64
import mimetypes
import os
from typing import Optional


def safe_dir_name(name: str) -> str:
    value = (name or "").strip()
    if not value:
        return "default"
    invalid = '<>:"/\\\\|?*'
    cleaned = "".join("_" if c in invalid else c for c in value)
    cleaned = cleaned.strip().strip(".")
    return cleaned or "default"


def guess_extension(url: Optional[str], content_type: Optional[str]) -> str:
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext
    if url:
        parsed = url.split("?")[0]
        _, ext = os.path.splitext(parsed)
        if ext and len(ext) <= 5:
            return ext
    return ".bin"


def file_to_data_url(file_path: str) -> str:
    mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def encode_image_id(rel_path: str) -> str:
    value = (rel_path or "").lstrip("/").replace("\\", "/")
    encoded = base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def decode_image_id(image_id: str) -> Optional[str]:
    value = (image_id or "").strip()
    if not value:
        return None
    pad = "=" * ((4 - (len(value) % 4)) % 4)
    try:
        decoded = base64.urlsafe_b64decode((value + pad).encode("ascii")).decode("utf-8")
    except Exception:
        return None
    decoded = decoded.lstrip("/").replace("\\", "/")
    if not decoded or decoded.startswith("../") or "/../" in decoded:
        return None
    return decoded


def safe_join(base_dir: str, rel_path: str) -> Optional[str]:
    base = os.path.abspath(base_dir)
    rel = (rel_path or "").lstrip("/").replace("\\", "/")
    target = os.path.abspath(os.path.join(base, rel))
    try:
        common = os.path.commonpath([base, target])
    except Exception:
        return None
    if common != base:
        return None
    return target
