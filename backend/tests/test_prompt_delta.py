import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.controllers import generate_controller as gc
from backend.config.settings import Settings

class FakeSettings(Settings):
    def __init__(self):
        super().__init__(raw={
            "enable_prompt_update_request": True,
            "prompts": {
                "default_style": "photorealistic",
                "default_negative_prompt": "low quality"
            },
            "models": {"qwen": "qwen-max"}
        })

def main():
    gc.load_settings = lambda: FakeSettings()
    # Base refine returns POS1/NEG1; delta refine returns POS1_var/NEG1_var each time
    def fake_refine(prompt, category, default_style, default_negative_prompt, role):
        return {"positive_prompt": "POS1", "negative_prompt": "NEG1"}
    def fake_delta(base_positive, category, default_style, default_negative_prompt, role, change_ratio=0.1):
        return {"positive_prompt": f"{base_positive}_var", "negative_prompt": "NEG1_var"}
    gc.client.refine_prompt = fake_refine
    gc.client.refine_prompt_with_delta = fake_delta
    context = {
        "prompt": "BASE",
        "category": "cat",
        "negative_prompt": "",
        "count": 4,
        "service": "wan",
        "model": "wan2.6-t2i",
        "size": "1024*1024",
        "prompt_extend": True,
        "resolution": "1K",
        "aspect_ratio": "16:9",
    }
    tasks = gc._task_generator(context)
    assert len(tasks) == 4
    # 1st from base refine
    assert tasks[0]["prompt"] == "POS1"
    # 2nd-4th from delta each time based on previous
    assert tasks[1]["prompt"] == "POS1_var"
    assert tasks[1]["inherited_prompt"] is True and tasks[1]["delta_ratio"] == 0.1
    assert tasks[2]["prompt"] == "POS1_var_var"
    assert tasks[3]["prompt"] == "POS1_var_var_var"
    print("ok")

if __name__ == "__main__":
    main()
