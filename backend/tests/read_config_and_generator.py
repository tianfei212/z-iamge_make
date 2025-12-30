import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.config.settings import load_settings
from backend.controllers import generate_controller as gc

def main():
    s = load_settings()
    print("enable_prompt_update_request(parameters)=", s.enable_prompt_update_request)
    print("prompt_delta_ratio(parameters)=", s.prompt_delta_ratio)
    calls = {"refine": 0, "delta": 0}
    def fake_refine(prompt, category, default_style, default_negative_prompt, role):
        calls["refine"] += 1
        return {"positive_prompt": "POS1", "negative_prompt": "NEG1"}
    def fake_delta(base_positive, category, default_style, default_negative_prompt, role, change_ratio=0.1):
        calls["delta"] += 1
        return {"positive_prompt": base_positive + "_VAR", "negative_prompt": "NEG_VAR"}
    gc.client.refine_prompt = fake_refine
    gc.client.refine_prompt_with_delta = fake_delta
    ctx = {
        "prompt": "BASE",
        "category": "环境",
        "negative_prompt": "",
        "count": 2,
        "service": "wan",
        "model": "wan2.6-t2i",
        "size": "1024*1024",
        "prompt_extend": True,
        "resolution": "1080p",
        "aspect_ratio": "16:9",
    }
    tasks = gc._task_generator(ctx)
    print("refine_calls=", calls["refine"], "delta_calls=", calls["delta"], "tasks_count=", len(tasks))
    print("t1=", tasks[0]["prompt"])
    print("t2=", tasks[1]["prompt"])

if __name__ == "__main__":
    main()
