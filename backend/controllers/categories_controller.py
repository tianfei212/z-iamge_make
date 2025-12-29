from fastapi import APIRouter, HTTPException
from backend.services.category_service import list_categories, create_category, delete_category

router = APIRouter()

@router.get("/api/categories")
def get_categories():
    return {"categories": list_categories()}

@router.post("/api/categories")
def post_category(payload: dict):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail={"error": "name required"})
    create_category(name)
    return {"status": "ok"}

@router.delete("/api/categories/{name}")
def remove_category(name: str):
    if not name:
        raise HTTPException(status_code=400, detail={"error": "name required"})
    delete_category(name)
    return {"status": "ok"}

