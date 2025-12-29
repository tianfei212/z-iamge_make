from __future__ import annotations

import re
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from backend.config import load_settings
import os
import datetime


QUALITY_ENUM = {"360p", "720p", "1080p", "1K", "2K", "4K", "HD"}
RATIO_PATTERN = re.compile(r"^\d{1,3}:\d{1,3}$")


class GeneratedItem(BaseModel):
    seed: str = Field(..., alias="随机种子")
    temperature: float = Field(..., alias="热度值")
    top_p: float = Field(..., alias="top值")
    relative_url: str = Field(..., alias="相对url路径")
    absolute_path: str = Field(..., alias="存储绝对路径")

    @validator("seed")
    def _seed_str(cls, v):
        return str(v).strip()

    @validator("temperature")
    def _temp_range(cls, v):
        settings = load_settings()
        rng = settings.parameters.get("temperature_range", [1.0, 1.0])
        if not isinstance(rng, list) or len(rng) != 2:
            return v
        lo, hi = float(rng[0]), float(rng[1])
        if not (lo <= float(v) <= hi):
            raise ValueError("热度值超出范围")
        return float(v)

    @validator("top_p")
    def _top_range(cls, v):
        settings = load_settings()
        rng = settings.parameters.get("top_p_range", [0.8, 0.8])
        if not isinstance(rng, list) or len(rng) != 2:
            return v
        lo, hi = float(rng[0]), float(rng[1])
        if not (lo <= float(v) <= hi):
            raise ValueError("top值超出范围")
        return float(v)

    @validator("relative_url")
    def _relative_url_fmt(cls, v):
        v = v.strip()
        if not v.startswith("/api/images/") or not (v.endswith("/raw") or v.endswith("/thumb")):
            raise ValueError("相对url路径格式不合法")
        return v

    @validator("absolute_path")
    def _absolute_path_fmt(cls, v):
        v = v.strip()
        if not os.path.isabs(v):
            raise ValueError("存储绝对路径必须为绝对路径")
        return v


class RecordEntry(BaseModel):
    user_id: Optional[str] = Field(None, alias="用户ID")
    session_id: Optional[str] = Field(None, alias="SessionID")
    created_at: str = Field(..., alias="创建时间")
    base_prompt: str = Field(..., alias="通用基础提示词")
    category_prompt: str = Field(..., alias="分类描述提示词")
    refined_positive: str = Field(..., alias="优化后正向提示词")
    refined_negative: Optional[str] = Field("", alias="优化后反向提示词")
    aspect_ratio: str = Field(..., alias="比例")
    quality: str = Field(..., alias="画质")
    count: int = Field(..., alias="数量", ge=1)
    model_name: str = Field(..., alias="模型名称")
    items: List[GeneratedItem] = Field(default_factory=list, alias="生成记录")

    @validator("user_id", "session_id", pre=True, always=True)
    def _default_ids(cls, v):
        if v is None or str(v).strip() == "":
            return "-1"
        return str(v).strip()

    @validator("created_at", pre=True, always=True)
    def _ts_fmt(cls, v):
        if v:
            s = str(v)
            if re.fullmatch(r"^\d{10}$", s):
                return s
        # 默认使用服务端 UTC 小时戳
        return datetime.datetime.utcnow().strftime("%Y%m%d%H")

    @validator("base_prompt", "category_prompt", "refined_positive", "model_name")
    def _non_empty(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("必填字段不能为空")
        return v.strip()

    @validator("aspect_ratio")
    def _ratio_fmt(cls, v):
        v = v.strip()
        if not RATIO_PATTERN.fullmatch(v):
            raise ValueError("比例格式不合法")
        return v

    @validator("quality")
    def _quality_enum(cls, v):
        v = v.strip()
        settings = load_settings()
        allowed = set(settings.parameters.get("quality_enum", list(QUALITY_ENUM)))
        if v not in allowed:
            raise ValueError("画质枚举值不合法")
        return v
