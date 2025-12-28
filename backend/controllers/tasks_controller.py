from fastapi import APIRouter, HTTPException
from backend.services.background_task_service import get_job_status

router = APIRouter()

@router.get("/api/tasks/group/{job_id}")
def get_group_status(job_id: str):
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status
