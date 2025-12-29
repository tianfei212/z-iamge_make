import unittest
from backend.controllers.config_controller import get_limits, update_all

class TestConfigEndpoints(unittest.TestCase):
    def test_get_limits(self):
        resp = get_limits()
        self.assertIn("model_limits", resp)
        ml = resp["model_limits"]
        self.assertIsInstance(ml, dict)
        # default keys should exist
        self.assertTrue(any(k for k in ml.keys()))
        for v in ml.values():
            self.assertIsInstance(v, int)
            self.assertGreaterEqual(v, 1)

    def test_update_all(self):
        payload = {
            "global": {
                "common_subject": "单元测试主体",
                "global_style": "写实",
                "negative_prompt": "水印",
            },
            "categories": ["单测分类A"],
            "prompts": {"单测分类A": "这是一个提示词"},
        }
        resp = update_all(payload)
        self.assertEqual(resp.get("status"), "ok")
        self.assertIn("global", resp)
        self.assertIn("categories", resp)
        self.assertIn("prompts", resp)
        self.assertIn("单测分类A", resp["categories"])
        self.assertEqual(resp["prompts"].get("单测分类A"), "这是一个提示词")

if __name__ == "__main__":
    unittest.main()

