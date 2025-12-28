"""
/**
 * @file backend/tests/test_models_crud.py
 * @description 模型 CRUD 单元测试（内存实现）。
 */
"""

import unittest

from backend.models.generate_request_model import GenerateRequest
from backend.models.translate_request_model import TranslateRequest


class TestModelsCRUD(unittest.TestCase):
    def test_generate_request_crud(self):
        key = "k1"
        GenerateRequest.create(key, {"a": 1})
        self.assertEqual(GenerateRequest.read(key), {"a": 1})
        GenerateRequest.update(key, {"b": 2})
        self.assertEqual(GenerateRequest.read(key), {"a": 1, "b": 2})
        GenerateRequest.delete(key)
        self.assertIsNone(GenerateRequest.read(key))


if __name__ == "__main__":
    unittest.main()

