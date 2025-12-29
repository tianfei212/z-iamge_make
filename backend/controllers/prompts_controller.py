from fastapi import APIRouter, HTTPException
from backend.services.prompt_service import list_prompts, upsert_prompt, delete_prompt

router = APIRouter()

@router.get("/api/prompts")
def get_prompts():
    return {"prompts": list_prompts()}

@router.post("/api/prompts")
def post_prompt(payload: dict):
    category = str(payload.get("category", "")).strip()
    prompt = str(payload.get("prompt", "")).strip()
    if not category:
        raise HTTPException(status_code=400, detail={"error": "category required"})
    upsert_prompt(category, prompt)
    return {"status": "ok"}

@router.put("/api/prompts/{category}")
def put_prompt(category: str, payload: dict):
    prompt = str(payload.get("prompt", "")).strip()
    if not category:
        raise HTTPException(status_code=400, detail={"error": "category required"})
    upsert_prompt(category, prompt)
    return {"status": "ok"}

@router.delete("/api/prompts/{category}")
def remove_prompt(category: str):
    if not category:
        raise HTTPException(status_code=400, detail={"error": "category required"})
    delete_prompt(category)
    return {"status": "ok"}

