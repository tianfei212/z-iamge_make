from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.db_service import DBService
from backend.utils.validators import (
    is_valid_ratio,
    is_valid_quality,
    is_valid_url,
    is_absolute_path,
)

router = APIRouter()
svc = DBService()


class RecordCreate(BaseModel):
    job_id: str
    user_id: str
    session_id: str
    created_at: str
    base_prompt: str
    category_prompt: str
    aspect_ratio: str
    quality: str
    count: int
    model_name: str
    status: str = "submitted"

    def validate_custom(self):
        if not is_valid_ratio(self.aspect_ratio):
            raise HTTPException(status_code=422, detail="比例格式不合法")
        if not is_valid_quality(self.quality, {"360p", "720p", "1080p", "1K", "2K", "4K", "HD"}):
            raise HTTPException(status_code=422, detail="画质枚举值不合法")
        if self.count < 1:
            raise HTTPException(status_code=422, detail="数量必须>=1")


class RecordUpdate(BaseModel):
    base_prompt: Optional[str] = None
    category_prompt: Optional[str] = None
    refined_positive: Optional[str] = None
    refined_negative: Optional[str] = None
    aspect_ratio: Optional[str] = None
    quality: Optional[str] = None
    count: Optional[int] = None
    model_name: Optional[str] = None
    status: Optional[str] = None


class ItemCreate(BaseModel):
    seed: str
    temperature: float
    top_p: float
    relative_url: str
    absolute_path: str

    def validate_custom(self):
        if not (self.temperature >= 0.0):
            raise HTTPException(status_code=422, detail="热度值非法")
        if not (self.top_p >= 0.0):
            raise HTTPException(status_code=422, detail="top值非法")
        if not is_valid_url(self.relative_url) and not self.relative_url.startswith("/api/images/"):
            raise HTTPException(status_code=422, detail="相对url路径格式不合法")
        if not is_absolute_path(self.absolute_path):
            raise HTTPException(status_code=422, detail="存储绝对路径必须为绝对路径")

class ItemsBatch(BaseModel):
    items: List[ItemCreate] = Field(default_factory=list)


@router.post("/api/records", tags=["Records"])
def create_record(body: RecordCreate):
    body.validate_custom()
    rec = svc.create_record(body.dict())
    return {"record": rec}


@router.get("/api/records", tags=["Records"])
def list_records(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    created_at: Optional[str] = None,
    category_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    status: Optional[str] = None,
):
    filters = {
        "created_at": created_at,
        "category_prompt": category_prompt,
        "model_name": model_name,
        "status": status,
    }
    rows = svc.list_records(limit, offset, filters)
    return {"records": rows, "paging": {"limit": limit, "offset": offset, "count": len(rows)}}


@router.get("/api/records/{id}", tags=["Records"])
def get_record(id: int):
    rec = svc.get_record(id)
    if not rec:
        raise HTTPException(status_code=404, detail="Not found")
    return {"record": rec}


@router.put("/api/records/{id}", tags=["Records"])
def update_record(id: int, body: RecordUpdate):
    patch = {k: v for k, v in body.dict().items() if v is not None}
    if not patch:
        return {"record": svc.get_record(id)}
    rec = svc.update_record(id, patch)
    return {"record": rec}

@router.put("/api/records/by-job/{job_id}", tags=["Records"])
def update_record_by_job(job_id: str, body: RecordUpdate):
    patch = {k: v for k, v in body.dict().items() if v is not None}
    rec = svc.update_record_by_job(job_id, patch)
    if rec is None:
        raise HTTPException(status_code=404, detail="Not found")
    return {"record": rec}


@router.delete("/api/records/{id}", tags=["Records"])
def delete_record(id: int):
    svc.delete_record(id)
    return {"status": "ok"}


@router.post("/api/records/{id}/items", tags=["Items"])
def create_item(id: int, body: ItemCreate):
    body.validate_custom()
    item = svc.add_item(id, body.dict())
    return {"item": item}

@router.post("/api/records/{id}/items/batch", tags=["Items"])
def create_items_batch(id: int, body: ItemsBatch):
    payloads = []
    for it in body.items:
        it.validate_custom()
        payloads.append(it.dict())
    rows = svc.add_items(id, payloads)
    # normalize item_count to actual count
    try:
        cnt = svc.get_items_count(id)
        svc.update_record(id, {"item_count": cnt})
    except Exception:
        pass
    return {"items": rows, "count": len(rows)}

@router.get("/api/records/{id}/validate", tags=["Records"])
def validate_record(id: int):
    return svc.validate_record_integrity(id)


@router.get("/api/records/{id}/items", tags=["Items"])
def list_items(id: int, limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    rows = svc.list_items(id, limit, offset)
    return {"items": rows, "paging": {"limit": limit, "offset": offset, "count": len(rows)}}


@router.get("/api/records/{id}/items/{item_id}", tags=["Items"])
def get_item(id: int, item_id: int):
    row = svc.get_item(id, item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return {"item": row}


@router.put("/api/records/{id}/items/{item_id}", tags=["Items"])
def update_item(id: int, item_id: int, body: ItemCreate):
    patch = {k: v for k, v in body.dict().items() if v is not None}
    if not patch:
        return {"item": svc.get_item(id, item_id)}
    row = svc.update_item(id, item_id, patch)
    return {"item": row}


@router.delete("/api/records/{id}/items/{item_id}", tags=["Items"])
def delete_item(id: int, item_id: int):
    svc.delete_item(id, item_id)
    return {"status": "ok"}
