import os
import sys
import types

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

def test_inheritance():
    # Patch load_settings to return fake settings
    gc.load_settings = lambda: FakeSettings()
    # Patch client.refine_prompt to simulate behavior:
    # If input is 'BASE', return POS1/NEG1; if input is 'POS1', return POS2/NEG2
    def fake_refine(prompt, category, default_style, default_negative_prompt, role):
        if prompt == "BASE":
            return {"positive_prompt": "POS1", "negative_prompt": "NEG1"}
        if prompt == "POS1":
            return {"positive_prompt": "POS2", "negative_prompt": "NEG2"}
        return {"positive_prompt": prompt, "negative_prompt": default_negative_prompt}
    gc.client.refine_prompt = fake_refine
    context = {
        "prompt": "BASE",
        "category": "cat",
        "negative_prompt": "",
        "count": 2,
        "service": "wan",
        "model": "wan2.6-t2i",
        "size": "1024*1024",
        "prompt_extend": True,
        "resolution": "1K",
        "aspect_ratio": "16:9",
    }
    tasks = gc._task_generator(context)
    assert len(tasks) == 2
    assert tasks[0]["prompt"] == "POS1"
    assert tasks[0]["refined_positive"] == "POS1"
    assert tasks[0].get("inherited_prompt") is None
    assert tasks[1]["prompt"] == "POS2"
    assert tasks[1]["refined_positive"] == "POS2"
    assert tasks[1].get("inherited_prompt") is True

if __name__ == "__main__":
    test_inheritance()
    print("ok")
