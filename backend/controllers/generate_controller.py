"""
/**
 * @file backend/controllers/generate_controller.py
 * @description 生成控制器（统一生成接口）。
 */
"""

from fastapi import APIRouter, HTTPException, Request
import uuid
import random
from backend.models.generate_request_model import GenerateRequest
from backend.services import DashScopeClient
from backend.services.background_task_service import submit_job_request
from backend.config import load_settings
from backend.utils.validators import is_valid_uuid
import uuid

router = APIRouter()
client = DashScopeClient()

def _task_generator(context: dict):
    """
    Generator function that runs in background thread.
    Refines prompt using Qwen (with caching) and generates list of tasks.
    """
    req_prompt = context.get("prompt")
    req_category = context.get("category")
    req_negative_prompt = context.get("negative_prompt")
    req_count = context.get("count", 1)
    
    # Load generation parameters from settings (fresh load in background)
    settings = load_settings()
    params_cfg = settings.parameters
    
    # Default ranges
    temp_min, temp_max = params_cfg.get("temperature_range", [1.0, 1.0])
    top_p_min, top_p_max = params_cfg.get("top_p_range", [0.8, 0.8])
    
    # 1. Refine Prompt with Qwen (once per job, or per-image if enabled)
    role = settings.role
    default_style = settings.prompts.get("default_style", "")
    default_negative = settings.prompts.get("default_negative_prompt", "")
    
    current_negative = req_negative_prompt if req_negative_prompt else default_negative
    
    print(f"Refining prompt in background... (Role configured: {bool(role)})")
    refined = client.refine_prompt(
        prompt=req_prompt,
        category=req_category,
        default_style=default_style,
        default_negative_prompt=current_negative,
        role=role
    )
    final_positive_prompt = refined["positive_prompt"]
    final_negative_prompt = refined["negative_prompt"]
    final_positive_prompt_zh = refined.get("positive_prompt_zh")
    final_negative_prompt_zh = refined.get("negative_prompt_zh")
    print(f"Refined Positive: {final_positive_prompt[:50]}...")
    
    # 2. Generate Tasks
    tasks = []
    inherit_enabled = bool(settings.enable_prompt_update_request)
    delta_ratio = float(getattr(settings, "prompt_delta_ratio", 0.1))
    prev_positive = final_positive_prompt
    for idx in range(req_count):
        if inherit_enabled and idx >= 1:
            # Variant: ~10% adjustments based on previous positive prompt
            refined2 = client.refine_prompt_with_delta(
                base_positive=prev_positive,
                category=req_category,
                default_style=default_style,
                default_negative_prompt=current_negative,
                role=role,
                change_ratio=delta_ratio
            )
            final_positive_prompt = refined2["positive_prompt"]
            final_negative_prompt = refined2["negative_prompt"]
            final_positive_prompt_zh = refined2.get("positive_prompt_zh")
            final_negative_prompt_zh = refined2.get("negative_prompt_zh")
            prev_positive = final_positive_prompt
        seed = random.randint(0, 4294967295)
        temperature = random.uniform(temp_min, temp_max)
        top_p = random.uniform(top_p_min, top_p_max)
        
        task_params = {
            "service": context.get("service"),
            "prompt": final_positive_prompt,
            "model": context.get("model"),
            "category": req_category,
            "size": context.get("size"),
            "negative_prompt": final_negative_prompt,
            "prompt_extend": context.get("prompt_extend"),
            "resolution": context.get("resolution"),
            "aspect_ratio": context.get("aspect_ratio"),
            "seed": seed,
            "temperature": temperature,
            "top_p": top_p,
            "refined_positive": final_positive_prompt,
            "refined_negative": final_negative_prompt,
            "refined_positive_zh": final_positive_prompt_zh,
            "refined_negative_zh": final_negative_prompt_zh,
        }
        if inherit_enabled and idx >= 1:
            task_params["inherited_prompt"] = True
            task_params["delta_ratio"] = delta_ratio
        tasks.append(task_params)
    return tasks

def _process_single_image(params):
    """
    Worker function to process a single image generation request.
    """
    service = params.get("service")
    resolution = params.get("resolution", "1K")
    prompt = params.get("prompt")
    
    if service == "z_image":
        result = client.call_z_image(
            prompt=prompt,
            category=params.get("category", "default"),
            size=params.get("size", "1024*1024"),
            prompt_extend=params.get("prompt_extend", False),
            resolution=resolution,
            seed=params.get("seed"),
            temperature=params.get("temperature"),
            top_p=params.get("top_p"),
        )
    else:
        result = client.call_wan(
            prompt=prompt,
            model=params.get("model"),
            category=params.get("category", "default"),
            size=params.get("size", "1024*1024"),
            negative_prompt=params.get("negative_prompt", ""),
            resolution=resolution,
            seed=params.get("seed"),
            temperature=params.get("temperature"),
            top_p=params.get("top_p"),
        )
    return client.to_data_url_if_local(result)


@router.post("/api/generate")
def generate(req: GenerateRequest, request: Request):
    # Log the incoming request
    print(f"Generate Request: Prompt='{req.prompt}', Count={req.count}, Service={req.service}...")

    # Qwen text generation is still synchronous (direct call)
    if req.service == "qwen":
        return client.call_qwen(req.prompt, model=req.model)

    # Prepare Context for Background Job
    job_context = req.dict()
    # Create job_id first
    job_id = str(uuid.uuid4())
    # Attach user/session info and meta for record service
    user_id = request.headers.get("X-User-ID", "-1")
    session_id_hdr = request.headers.get("X-Session-ID", None)
    if session_id_hdr and is_valid_uuid(session_id_hdr):
        session_id = session_id_hdr
    else:
        ns = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
        name = f"{user_id or '-1'}:{job_id}"
        session_id = str(uuid.uuid5(ns, name))
    import datetime
    created_at = datetime.datetime.utcnow().strftime("%Y%m%d%H")
    job_context.update({
        "user_id": user_id or "-1",
        "session_id": session_id,
        "created_at": created_at,
        "base_prompt": req.prompt,
        "category_prompt": req.category,
        "aspect_ratio": req.aspect_ratio,
        "resolution": req.resolution,
        "model_name": req.model or "",
    })
    
    # Submit Job Request (Non-blocking)
    submit_job_request(job_id, job_context, _task_generator, _process_single_image)
    
    return {
        "status": "submitted",
        "job_id": job_id,
        "task_count": req.count,
        "message": "Job submitted to background queue."
    }
