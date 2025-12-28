"""
/**
 * @file backend/tests/test_bankmcp_wrappers.py
 * @description bankmcp 连接函数单元测试（使用 mock，避免真实网络请求）。
 */
"""

import unittest
from unittest.mock import Mock

from backend.bankmcp.connectors import connect_qwen, connect_wan, connect_z_image, translate_zh_en


class TestBankmcpWrappers(unittest.TestCase):
    def test_translate_empty(self):
        self.assertEqual(translate_zh_en(""), {"status": "success", "output": ""})

    def test_connect_qwen_uses_client(self):
        client = Mock()
        client.call_qwen.return_value = {"status": "success", "output": "ok"}
        out = connect_qwen("hi", model="qwen-max", client=client)
        client.call_qwen.assert_called_once_with("hi", model="qwen-max")
        self.assertEqual(out["status"], "success")

    def test_connect_wan_uses_client(self):
        client = Mock()
        client.call_wan.return_value = {"status": "success", "url": "u"}
        out = connect_wan("p", model="m", category="c", size="1*1", negative_prompt="n", client=client)
        client.call_wan.assert_called_once_with("p", model="m", category="c", size="1*1", negative_prompt="n")
        self.assertEqual(out["status"], "success")

    def test_connect_z_image_uses_client(self):
        client = Mock()
        client.call_z_image.return_value = {"status": "success", "url": "u"}
        out = connect_z_image("p", category="c", size="1*1", prompt_extend=True, client=client)
        client.call_z_image.assert_called_once_with("p", category="c", size="1*1", prompt_extend=True)
        self.assertEqual(out["status"], "success")


if __name__ == "__main__":
    unittest.main()

