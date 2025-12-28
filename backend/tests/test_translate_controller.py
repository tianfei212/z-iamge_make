import unittest
from unittest.mock import patch
from backend.controllers.translate_controller import translate
from backend.models.translate_request_model import TranslateRequest

class TestTranslateController(unittest.TestCase):
    @patch("backend.controllers.translate_controller.translate_zh_en")
    def test_translate_controller(self, mock_translate):
        mock_translate.return_value = {"status": "success", "output": "Hello"}
        req = TranslateRequest(text="你好", model="qwen-plus")
        
        resp = translate(req)
        
        self.assertEqual(resp, {"status": "success", "output": "Hello"})
        mock_translate.assert_called_with("你好", model="qwen-plus")

if __name__ == "__main__":
    unittest.main()
