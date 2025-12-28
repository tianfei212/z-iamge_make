"""
/**
 * @file backend/tests/test_settings_merge.py
 * @description 配置合并单元测试。
 */
"""

import json
import os
import tempfile
import unittest

from backend.config.settings import load_settings


class TestSettingsMerge(unittest.TestCase):
    def test_merge_base_and_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_path = os.path.join(tmp, "config.json")
            local_path = os.path.join(tmp, "config.local.json")
            example_path = os.path.join(tmp, "config.example.json")

            with open(base_path, "w") as f:
                json.dump({"api_keys": {"dashscope": "a"}, "models": {"qwen": "m1"}, "endpoints": {"qwen": "x"}}, f)
            with open(local_path, "w") as f:
                json.dump({"api_keys": {"dashscope": "b"}}, f)
            with open(example_path, "w") as f:
                json.dump({}, f)

            s = load_settings(base_path=base_path, local_path=local_path, example_path=example_path)
            self.assertEqual(s.api_keys.get("dashscope"), "b")
            self.assertEqual(s.models.get("qwen"), "m1")


if __name__ == "__main__":
    unittest.main()
