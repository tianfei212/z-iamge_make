import concurrent.futures
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

        # 3. Execute Tasks in Parallel
        _execute_tasks_parallel(job_id, tasks, process_func)
        
    except Exception as e:
        logger.error(f"Job {job_id} failed during lifecycle: {e}")
        with _STATUS_LOCK:
            if job_id in _TASK_STORE:
                _TASK_STORE[job_id].status = "failed"
                _TASK_STORE[job_id].results = [{"status": "failed", "message": str(e)}]

def _execute_tasks_parallel(job_id: str, tasks: List[Dict[str, Any]], process_func):
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
