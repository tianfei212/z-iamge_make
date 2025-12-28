import unittest
from unittest.mock import MagicMock, patch
from backend.services.translation_service import translate_zh_en
from backend.services.dashscope_client_service import DashScopeClient

class TestTranslationService(unittest.TestCase):

    def test_translate_zh_en_calls_client(self):
        # Mock client
        mock_client = MagicMock(spec=DashScopeClient)
        mock_client.call_qwen.return_value = {"status": "success", "output": "Hello"}

        text = "你好"
        result = translate_zh_en(text, client=mock_client)

        self.assertEqual(result, {"status": "success", "output": "Hello"})
        
        # Verify call arguments
        mock_client.call_qwen.assert_called_once()
        args, kwargs = mock_client.call_qwen.call_args
        self.assertIn("Translate the following text", args[0])
        self.assertIn("你好", args[0])
    
    def test_translate_empty_text(self):
        result = translate_zh_en("")
        self.assertEqual(result, {"status": "success", "output": ""})

if __name__ == "__main__":
    unittest.main()
