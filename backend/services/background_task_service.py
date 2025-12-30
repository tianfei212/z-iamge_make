import concurrent.futures
import os
import uuid
import time
import logging
import threading
import queue
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class TaskStatus:
    job_id: str
    status: str  # "submitted", "processing", "running", "completed", "failed"
    total_tasks: int
    completed_tasks: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

# In-memory storage for task status
_TASK_STORE: Dict[str, TaskStatus] = {}
_STATUS_LOCK = threading.Lock()

# Job Queue for asynchronous processing
_JOB_QUEUE = queue.Queue()

# Thread pools
_DEFAULT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4)
_IMAGE_GEN_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=8)

def start_job_dispatcher():
    """Start the background thread that consumes jobs from the queue."""
    t = threading.Thread(target=_job_dispatcher_loop, daemon=True)
    t.start()

def submit_job_request(job_id: str, job_context: Dict[str, Any], task_generator_func: Callable, process_func: Callable) -> None:
    """
    Submit a job request to the queue. 
    The job will be processed asynchronously: Refine Prompt -> Generate Tasks -> Execute Tasks.
    """
    with _STATUS_LOCK:
        _TASK_STORE[job_id] = TaskStatus(
            job_id=job_id,
            status="submitted",
            total_tasks=job_context.get("count", 1)
        )
    
    _JOB_QUEUE.put({
        "job_id": job_id,
        "context": job_context,
        "generator": task_generator_func,
        "processor": process_func
    })

def _job_dispatcher_loop():
    """
    Consumer loop that processes jobs from the queue.
    """
    logger.info("Job Dispatcher started.")
    while True:
        try:
            item = _JOB_QUEUE.get()
            job_id = item["job_id"]
            context = item["context"]
            generator_func = item["generator"]
            process_func = item["processor"]
            
            _process_job_lifecycle(job_id, context, generator_func, process_func)
            
            _JOB_QUEUE.task_done()
        except Exception as e:
            logger.error(f"Error in job dispatcher: {e}")

def _process_job_lifecycle(job_id: str, context: Dict[str, Any], generator_func: Callable, process_func: Callable):
    """
    Handle the full lifecycle of a job: Refine -> Split -> Execute.
    """
    logger.info(f"Starting lifecycle for job {job_id}")
    
    # 1. Update Status to Processing (Refining)
    with _STATUS_LOCK:
        if job_id in _TASK_STORE:
            _TASK_STORE[job_id].status = "processing"

    try:
        # 2. Generate Tasks (This includes synchronous Qwen call for prompt refinement)
        tasks = generator_func(context)
        
        if not tasks:
            raise ValueError("No tasks generated")
            
        # Update total tasks count if changed (e.g. generator might return different count)
        with _STATUS_LOCK:
            if job_id in _TASK_STORE:
                _TASK_STORE[job_id].total_tasks = len(tasks)
                _TASK_STORE[job_id].status = "running"

        # 3. Execute Tasks (Parallel or Serial depending on config)
        from backend.config import load_settings
        s = load_settings()
        if bool(getattr(s, "enable_prompt_update_request", False)):
            _execute_tasks_serial(job_id, tasks, process_func, context, s)
        else:
            _execute_tasks_parallel(job_id, tasks, process_func, context)
        
    except Exception as e:
        logger.error(f"Job {job_id} failed during lifecycle: {e}")
        with _STATUS_LOCK:
            if job_id in _TASK_STORE:
                _TASK_STORE[job_id].status = "failed"
                _TASK_STORE[job_id].results = [{"status": "failed", "message": str(e)}]

def _execute_tasks_parallel(job_id: str, tasks: List[Dict[str, Any]], process_func, context: Dict[str, Any]):
    """
    Execute list of tasks using appropriate executor.
    """
    logger.info(f"Executing job {job_id} with {len(tasks)} tasks")
    
    is_image_gen = False
    if tasks and isinstance(tasks[0], dict):
        service = tasks[0].get("service")
        if service in ["wan", "z_image"]:
            is_image_gen = True
    
    executor = _IMAGE_GEN_EXECUTOR if is_image_gen else _DEFAULT_EXECUTOR
    executor_name = "ImageGen" if is_image_gen else "Default"
    logger.info(f"Job {job_id} using {executor_name} Executor")
    
    futures = []
    for i, task_params in enumerate(tasks):
        futures.append(executor.submit(_process_single_task_wrapper, job_id, i, task_params, process_func))
    
    concurrent.futures.wait(futures)
    
    # Collect results
    results = []
    completed_count = 0
    
    for f in futures:
        try:
            res = f.result()
            if isinstance(res, dict) and res.get("status") == "success" and res.get("url"):
                results.append(res)
                completed_count += 1
            else:
                results.append(res)
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            results.append({"status": "failed", "message": str(e)})

    # Update final status
    with _STATUS_LOCK:
        if job_id in _TASK_STORE:
            task_status = _TASK_STORE[job_id]
            task_status.results = results
            task_status.completed_tasks = len(tasks)
            task_status.status = "completed"
 
    logger.info(f"Job {job_id} completed. Success: {completed_count}/{len(tasks)}")
    try:
        # Assemble record items and meta
        from backend.services.record_service import RecordService
        # Prefer refined prompts from first task
        refined_pos = None
        refined_neg = None
        if tasks:
            t0 = tasks[0]
            service0 = t0.get("service")
            refined_pos = t0.get("refined_positive") or t0.get("prompt")
            refined_neg = t0.get("refined_negative") or t0.get("negative_prompt") or ""
            refined_pos_zh = t0.get("refined_positive_zh")
            refined_neg_zh = t0.get("refined_negative_zh")
        # resolve model name
        from backend.config import load_settings
        settings = load_settings()
        default_model = ""
        if tasks:
            if service0 == "wan":
                default_model = settings.models.get("wan", "wan2.6-t2i")
            elif service0 == "z_image":
                default_model = settings.models.get("z_image", "z-image-turbo")
        model_name = tasks[0].get("model") if tasks else ""
        if not model_name:
            model_name = default_model
        items = []
        from backend.utils import decode_image_id, encode_image_id, safe_dir_name, safe_join
        out_dir = load_settings().output_dir
        for t, r in zip(tasks, results):
            if not isinstance(r, dict) or r.get("status") != "success":
                continue
            rel_url = r.get("originalUrl") or r.get("url")
            saved_path = r.get("saved_path")
            abs_path = saved_path
            if (not abs_path) and isinstance(rel_url, str) and rel_url.startswith("/api/images/"):
                try:
                    # extract image_id
                    parts = rel_url.split("/")
                    image_id = parts[3] if len(parts) >= 4 else ""
                    rel = decode_image_id(image_id)
                    if rel:
                        path_calc = safe_join(out_dir, rel)
                        if path_calc:
                            abs_path = path_calc
                except Exception:
                    pass
            if rel_url and abs_path:
                items.append({
                    "seed": t.get("seed"),
                    "temperature": t.get("temperature"),
                    "top_p": t.get("top_p"),
                    "relative_url": rel_url,
                    "absolute_path": abs_path,
                })
        if not items:
            try:
                # Fallback: scan output directory for latest files in category
                cat = safe_dir_name(context.get("category", "default"))
                cat_dir = os.path.join(os.path.abspath(out_dir), cat)
                if os.path.isdir(cat_dir):
                    files = [
                        os.path.join(cat_dir, f)
                        for f in os.listdir(cat_dir)
                        if os.path.isfile(os.path.join(cat_dir, f)) and not f.startswith(".")
                    ]
                    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                    take = min(len(tasks), len(files))
                    for i in range(take):
                        p = files[i]
                        rel = f"{cat}/{os.path.basename(p)}"
                        image_id = encode_image_id(rel)
                        rel_url = f"/api/images/{image_id}/raw"
                        items.append({
                            "seed": tasks[i].get("seed"),
                            "temperature": tasks[i].get("temperature"),
                            "top_p": tasks[i].get("top_p"),
                            "relative_url": rel_url,
                            "absolute_path": p,
                        })
            except Exception as e:
                logger.error(f"fallback collect images failed for job {job_id}: {e}")
        job_meta = {
            "user_id": context.get("user_id"),
            "session_id": context.get("session_id"),
            "created_at": context.get("created_at"),
            "prompt": context.get("prompt"),
            "category": context.get("category"),
            "refined_positive": refined_pos or "",
            "refined_negative": refined_neg or "",
            "refined_positive_zh": refined_pos_zh,
            "refined_negative_zh": refined_neg_zh,
            "aspect_ratio": context.get("aspect_ratio"),
            "resolution": context.get("resolution"),
            "count": context.get("count", len(tasks)),
            "model": model_name,
        }
        logger.info(f"Job {job_id} record items collected: {len(items)}")
        RecordService.instance().add_record(job_meta, items, job_id=job_id)
    except Exception as e:
        logger.error(f"record write failed for job {job_id}: {e}")

def _execute_tasks_serial(job_id: str, tasks: List[Dict[str, Any]], process_func, context: Dict[str, Any], settings):
    """
    Execute tasks strictly one by one with dependency on previous refined prompt.
    Ensures two or more Qwen requests appear in logs when inheritance is enabled.
    """
    logger.info(f"Executing job {job_id} in SERIAL mode with {len(tasks)} tasks")
    results = []
    completed_count = 0
    try:
        from backend.services.dashscope_client_service import DashScopeClient
        client = DashScopeClient(settings=settings)
        default_style = settings.prompts.get("default_style", "")
        default_negative = settings.prompts.get("default_negative_prompt", "")
        current_negative = context.get("negative_prompt") or default_negative
        role = settings.role
        for i, t in enumerate(tasks):
            if i >= 1:
                # Build next prompt based on previous refined positive
                prev_pos = tasks[i-1].get("refined_positive") or tasks[i-1].get("prompt") or context.get("prompt")
                delta_ratio = float(getattr(settings, "prompt_delta_ratio", 0.1))
                print(f"[serial_chain] job={job_id} step={i} base_prev_pos={str(prev_pos)[:120]} delta_ratio={delta_ratio}")
                refined2 = client.refine_prompt_with_delta(
                    base_positive=prev_pos or "",
                    category=context.get("category", ""),
                    default_style=default_style,
                    default_negative_prompt=current_negative,
                    role=role,
                    change_ratio=delta_ratio
                )
                t["prompt"] = refined2["positive_prompt"]
                t["negative_prompt"] = refined2["negative_prompt"]
                t["refined_positive"] = refined2["positive_prompt"]
                t["refined_negative"] = refined2["negative_prompt"]
                t["refined_positive_zh"] = refined2.get("positive_prompt_zh")
                t["refined_negative_zh"] = refined2.get("negative_prompt_zh")
                t["inherited_prompt"] = True
                t["delta_ratio"] = delta_ratio
            # Execute
            res = process_func(t)
            results.append(res)
            completed_count += 1
            with _STATUS_LOCK:
                if job_id in _TASK_STORE:
                    _TASK_STORE[job_id].completed_tasks += 1
        logger.info(f"Job {job_id} SERIAL completed. Success: {sum(1 for r in results if isinstance(r, dict) and r.get('status')=='success')}/{len(tasks)}")
    except Exception as e:
        logger.error(f"Serial execution failed for job {job_id}: {e}")
        results.append({"status": "failed", "message": str(e)})
    # Update final status
    with _STATUS_LOCK:
        if job_id in _TASK_STORE:
            task_status = _TASK_STORE[job_id]
            task_status.results = results
            task_status.completed_tasks = len(tasks)
            task_status.status = "completed"
    # Persist record
    try:
        from backend.services.record_service import RecordService
        from backend.config import load_settings
        from backend.utils import decode_image_id, encode_image_id, safe_dir_name, safe_join
        out_dir = load_settings().output_dir
        refined_pos = tasks[0].get("refined_positive") or tasks[0].get("prompt")
        refined_neg = tasks[0].get("refined_negative") or tasks[0].get("negative_prompt") or ""
        refined_pos_zh = tasks[0].get("refined_positive_zh")
        refined_neg_zh = tasks[0].get("refined_negative_zh")
        # Collect items same as parallel
        items = []
        for t, r in zip(tasks, results):
            if not isinstance(r, dict) or r.get("status") != "success":
                continue
            rel_url = r.get("originalUrl") or r.get("url")
            saved_path = r.get("saved_path")
            abs_path = saved_path
            if (not abs_path) and isinstance(rel_url, str) and rel_url.startswith("/api/images/"):
                try:
                    parts = rel_url.split("/")
                    image_id = parts[3] if len(parts) >= 4 else ""
                    rel = decode_image_id(image_id)
                    if rel:
                        path_calc = safe_join(out_dir, rel)
                        if path_calc:
                            abs_path = path_calc
                except Exception:
                    pass
            if rel_url and abs_path:
                items.append({
                    "seed": t.get("seed"),
                    "temperature": t.get("temperature"),
                    "top_p": t.get("top_p"),
                    "relative_url": rel_url,
                    "absolute_path": abs_path,
                })
        job_meta = {
            "user_id": context.get("user_id"),
            "session_id": context.get("session_id"),
            "created_at": context.get("created_at"),
            "prompt": context.get("prompt"),
            "category": context.get("category"),
            "refined_positive": refined_pos or "",
            "refined_negative": refined_neg or "",
            "refined_positive_zh": refined_pos_zh,
            "refined_negative_zh": refined_neg_zh,
            "aspect_ratio": context.get("aspect_ratio"),
            "resolution": context.get("resolution"),
            "count": context.get("count", len(tasks)),
            "model": tasks[0].get("model") or "",
        }
        RecordService.instance().add_record(job_meta, items, job_id=job_id)
    except Exception as e:
        logger.error(f"record write failed for job {job_id} (serial): {e}")

# Deprecated: Old submit_job for compatibility if needed, but we will replace usages
def submit_job(job_id: str, tasks: List[Dict[str, Any]], process_func) -> None:
    """Legacy submit, wraps into new flow"""
    # Create a dummy generator that just returns the tasks
    submit_job_request(job_id, {"count": len(tasks)}, lambda _: tasks, process_func)

# ... _process_single_task_wrapper and get_job_status remain same ...

def _process_single_task_wrapper(job_id: str, index: int, task_params: Dict[str, Any], process_func):
    try:
        # Execute the task
        result = process_func(task_params)
        return result
    except Exception as e:
        logger.error(f"Task failed in job {job_id}: {e}")
        return {"status": "failed", "message": str(e)}
    finally:
        # Update progress after task is done (success or fail)
        with _STATUS_LOCK:
            if job_id in _TASK_STORE:
                _TASK_STORE[job_id].completed_tasks += 1

def get_job_status(job_id: str) -> Dict[str, Any]:
    with _STATUS_LOCK:
        task = _TASK_STORE.get(job_id)
        if not task:
            return None
        
        # Clone data to avoid race conditions during read? 
        # For simple fields it's fine, results list reference is ok.
        return {
            "job_id": task.job_id,
            "ready": task.status in ["completed", "failed"],
            "status": task.status,
            "progress": {
                "total": task.total_tasks,
                "completed": task.completed_tasks,
                "percent": int((task.completed_tasks / task.total_tasks) * 100) if task.total_tasks > 0 else 0
            },
            "results": task.results
        }
