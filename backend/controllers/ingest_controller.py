from typing import Optional
from fastapi import APIRouter, HTTPException, Query
import os
from backend.services.ingest_service import IngestService

router = APIRouter()
svc = IngestService()


@router.post("/api/ingest/raw", tags=["Ingest"])
def ingest_raw(date: Optional[str] = Query(None)):
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")
    path = os.path.join(base, f"{date}.json") if date else None
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Raw file not found")
    res = svc.ingest_file(path)
    return res

