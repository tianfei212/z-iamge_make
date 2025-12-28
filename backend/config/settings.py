"""
/**
 * @file backend/config/settings.py
 * @description 后端配置加载与合并（config.json + config.local.json）。
 */
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "config.json")
CONFIG_LOCAL_PATH = os.path.join(REPO_ROOT, "config.local.json")
CONFIG_EXAMPLE_PATH = os.path.join(REPO_ROOT, "config.example.json")


def _load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r") as f:
            value = json.load(f)
            return value if isinstance(value, dict) else {}
    except FileNotFoundError:
        return {}


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _merge_dicts(base[key], value)
        else:
            base[key] = value
    return base


@dataclass(frozen=True)
class Settings:
    raw: Dict[str, Any]

    @property
    def endpoints(self) -> Dict[str, str]:
        value = self.raw.get("endpoints", {})
        return value if isinstance(value, dict) else {}

    @property
    def models(self) -> Dict[str, str]:
        value = self.raw.get("models", {})
        return value if isinstance(value, dict) else {}

    @property
    def api_keys(self) -> Dict[str, str]:
        value = self.raw.get("api_keys", {})
        return value if isinstance(value, dict) else {}

    @property
    def output_dir(self) -> str:
        storage = self.raw.get("storage", {})
        if isinstance(storage, dict) and isinstance(storage.get("output_dir"), str) and storage["output_dir"]:
            return storage["output_dir"]
        return "outputs"

    @property
    def prompts(self) -> Dict[str, str]:
        value = self.raw.get("prompts", {})
        return value if isinstance(value, dict) else {}
    
    @property
    def role(self) -> str:
        return self.prompts.get("role", "")

    @property
    def parameters(self) -> Dict[str, Any]:
        value = self.raw.get("parameters", {})
        return value if isinstance(value, dict) else {}

    def resolve_dashscope_key(self) -> Optional[str]:
        return (
            os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("DASHSCOPE_APIKEY")
            or (self.api_keys.get("dashscope") if isinstance(self.api_keys.get("dashscope"), str) else None)
        )

    def resolve_wan_key(self) -> Optional[str]:
        return os.getenv("WAN_API_KEY") or (self.api_keys.get("wan") if isinstance(self.api_keys.get("wan"), str) else None)

    def resolve_z_image_key(self) -> Optional[str]:
        return os.getenv("Z_IMAGE_API_KEY") or (
            self.api_keys.get("z_image") if isinstance(self.api_keys.get("z_image"), str) else None
        )


import time
import logging
import threading
import hashlib
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("config_loader")

_CACHED_SETTINGS = None
_LAST_LOAD_TIME = 0
_CONFIG_HASH = ""
_SETTINGS_LOCK = threading.Lock()

def get_file_mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0

def _deep_diff(d1: Dict[str, Any], d2: Dict[str, Any], path="") -> list:
    diffs = []
    for k in set(d1.keys()) | set(d2.keys()):
        p = f"{path}.{k}" if path else k
        if k not in d1:
            diffs.append(f"Added: {p}")
        elif k not in d2:
            diffs.append(f"Removed: {p}")
        elif isinstance(d1[k], dict) and isinstance(d2[k], dict):
            diffs.extend(_deep_diff(d1[k], d2[k], p))
        elif d1[k] != d2[k]:
            diffs.append(f"Changed: {p} ({d1[k]} -> {d2[k]})")
    return diffs

def reload_settings(
    base_path: str = CONFIG_PATH,
    local_path: str = CONFIG_LOCAL_PATH,
    example_path: str = CONFIG_EXAMPLE_PATH,
) -> Settings:
    global _CACHED_SETTINGS, _LAST_LOAD_TIME, _CONFIG_HASH
    
    with _SETTINGS_LOCK:
        now = time.time()
        # Debounce: 500ms
        if _CACHED_SETTINGS and (now - _LAST_LOAD_TIME < 0.5):
            return _CACHED_SETTINGS

        try:
            # 1. Load
            base_cfg = _load_json(base_path)
            if not base_cfg and os.path.exists(base_path):
                pass

            if not base_cfg.get("endpoints") and os.path.exists(example_path):
                base_cfg = _load_json(example_path)
            
            local_cfg = _load_json(local_path)
            merged = _merge_dicts(base_cfg, local_cfg)
            
            if not isinstance(merged, dict):
                 raise ValueError("Config root must be a dictionary")
            
            # 2. Hash Check
            # Sort keys to ensure consistent hash for same content
            new_hash = hashlib.md5(json.dumps(merged, sort_keys=True).encode("utf-8")).hexdigest()
            
            if _CACHED_SETTINGS and new_hash == _CONFIG_HASH:
                _LAST_LOAD_TIME = now
                return _CACHED_SETTINGS

            # 3. Log Changes
            is_reload = _CACHED_SETTINGS is not None
            if is_reload:
                diffs = _deep_diff(_CACHED_SETTINGS.raw, merged)
                if diffs:
                    logger.info(f"Config changes detected: {'; '.join(diffs)}")
            
            # 4. Update
            _CACHED_SETTINGS = Settings(raw=merged)
            _CONFIG_HASH = new_hash
            _LAST_LOAD_TIME = now
            
            if is_reload:
                 logger.info("Configuration reloaded successfully.")

        except Exception as e:
            logger.error(f"Failed to reload config: {e}. Keeping old config.")
            if not _CACHED_SETTINGS:
                logger.warning("Initializing with empty settings due to load failure.")
                _CACHED_SETTINGS = Settings(raw={})
                
    return _CACHED_SETTINGS

def load_settings() -> Settings:
    """
    Get current settings. Lazy loads on first call.
    Subsequent reloads are handled by the file watcher calling reload_settings().
    """
    if _CACHED_SETTINGS is None:
        return reload_settings()
    return _CACHED_SETTINGS
