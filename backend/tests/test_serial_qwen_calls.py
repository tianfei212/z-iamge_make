import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services import background_task_service as bts
from backend.controllers import generate_controller as gc

# Fake Settings enabling inheritance and ratio
from backend.config.settings import Settings
class FakeSettings(Settings):
    def __init__(self):
        super().__init__(raw={
            "enable_prompt_update_request": True,
            "prompts": {
                "default_style": "photorealistic",
                "default_negative_prompt": "low quality"
            },
            "models": {"qwen": "qwen-max"},
            "parameters": {"prompt_delta_ratio": 0.05}
        })

# Patch DashScopeClient with counters
import backend.services.dashscope_client_service as dsc
CALLS = {"refine": 0, "delta": 0, "bases": []}

class FakeDashScopeClient(dsc.DashScopeClient):
    def __init__(self, settings=None):
        super().__init__(settings=settings)
    def refine_prompt(self, prompt: str, category: str, default_style: str, default_negative_prompt: str, role: str):
        CALLS["refine"] += 1
        return {"positive_prompt": "POS_BASE", "negative_prompt": "NEG_BASE"}
    def refine_prompt_with_delta(self, base_positive: str, category: str, default_style: str, default_negative_prompt: str, role: str, change_ratio: float = 0.1):
        CALLS["delta"] += 1
        CALLS["bases"].append(base_positive)
        return {"positive_prompt": base_positive + "_DELTA", "negative_prompt": "NEG_DELTA"}

# Override class symbol used by serial executor
dsc.DashScopeClient = FakeDashScopeClient

def main():
    # Force load_settings to return FakeSettings
    gc.load_settings = lambda: FakeSettings()
    # Prepare job context similar to controller
    job_id = str(uuid.uuid4())
    context = {
        "prompt": "BASE_PROMPT",
        "category": "环境",
        "negative_prompt": "",
        "count": 2,
        "service": "wan",
        "model": "wan2.6-t2i",
        "size": "1024*1024",
        "prompt_extend": True,
        "resolution": "1080p",
        "aspect_ratio": "16:9",
        "user_id": "-1",
        "session_id": str(uuid.uuid4()),
        "created_at": "2025123002",
        "base_prompt": "BASE_PROMPT",
        "category_prompt": "环境",
        "model_name": "wan2.6-t2i",
    }
    # Generate tasks from controller generator (will call refine once)
    tasks = gc._task_generator(context)
    # Stub process func to succeed
    def process_stub(params):
        return {"status": "success", "url": "http://localhost/image.png", "saved_path": os.path.join("outputs","环境","x.png"), "originalUrl": "http://localhost/image.png"}
    # Execute serial
    bts._execute_tasks_serial(job_id, tasks, process_stub, context, FakeSettings())
    print("refine_calls", CALLS["refine"])
    print("delta_calls", CALLS["delta"])
    print("delta_base", CALLS["bases"][0] if CALLS["bases"] else "")

if __name__ == "__main__":
    main()
