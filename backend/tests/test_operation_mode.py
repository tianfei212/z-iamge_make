import os
import json
import tempfile
import unittest
from unittest.mock import patch

from backend.db.connection import init_db, get_conn
from backend.config.settings import Settings, reload_settings
from backend.services.runtime_config_service import get_runtime_config

class TestOperationMode(unittest.TestCase):
    def setUp(self):
        init_db()
        with get_conn() as conn:
            conn.execute("DELETE FROM models")
            conn.execute("DELETE FROM categories")
            conn.execute("DELETE FROM prompts")
            conn.execute("DELETE FROM global_settings")

    def test_config_file_mode(self):
        raw = {
            "operation_mode": "config_file",
            "models_list": [
                {"id": "wan", "name": "Aliyun Wan 2.6", "provider": "aliyun", "model_name": "wan2.6-t2i", "description": "", "enabled": 1}
            ],
            "categories": ["人物"],
            "prompts_map": {"人物": "描述"},
            "global": {"common_subject": "A", "global_style": "B", "negative_prompt": "C"},
        }
        with patch("backend.config.settings.load_settings", return_value=Settings(raw=raw)):
            cfg = get_runtime_config()
            self.assertEqual(cfg.get("source"), "config_file")
            self.assertTrue(cfg.get("models"))
            self.assertTrue(cfg.get("categories"))
            self.assertTrue(cfg.get("prompts"))
            self.assertTrue(cfg.get("global"))

    def test_database_mode(self):
        with get_conn() as conn:
            conn.execute("INSERT INTO models(id,name,provider,model_name,description,enabled) VALUES('wan','Aliyun Wan 2.6','aliyun','wan2.6-t2i','',1)")
            conn.execute("INSERT INTO categories(name) VALUES('人物')")
            conn.execute("INSERT INTO prompts(category,prompt) VALUES('人物','描述')")
            conn.execute("INSERT INTO global_settings(id,common_subject,global_style,negative_prompt) VALUES(1,'A','B','C')")
        raw = {"operation_mode": "database"}
        with patch("backend.config.settings.load_settings", return_value=Settings(raw=raw)):
            cfg = get_runtime_config()
            self.assertEqual(cfg.get("source"), "database")
            self.assertTrue(cfg.get("models"))

    def test_invalid_mode_fallback(self):
        raw = {"operation_mode": "invalid"}
        with patch("backend.config.settings.load_settings", return_value=Settings(raw=raw)):
            cfg = get_runtime_config()
            self.assertEqual(cfg.get("source"), "config_file")

    def test_db_unavailable_fallback(self):
        raw = {"operation_mode": "database"}
        with patch("backend.config.settings.load_settings", return_value=Settings(raw=raw)):
            cfg = get_runtime_config()
            self.assertEqual(cfg.get("source"), "config_file")

    def test_config_corrupted(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        with open(path, "w") as f:
            f.write("{invalid json")
        s = reload_settings(base_path=path, local_path=path, example_path=path)
        self.assertIsInstance(s.raw, dict)
        os.remove(path)

if __name__ == "__main__":
    unittest.main()
