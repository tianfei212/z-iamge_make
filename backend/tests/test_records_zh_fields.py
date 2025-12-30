import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services.db_service import DBService

def main():
    db = DBService()
    payload = {
        "job_id": "job_zh_test",
        "user_id": "-1",
        "session_id": "sess",
        "created_at": "2025123002",
        "base_prompt": "BP",
        "category_prompt": "环境",
        "refined_positive": "POS_EN",
        "refined_negative": "NEG_EN",
        "positive_zh": "正向中文",
        "negative_zh": "反向中文",
        "aspect_ratio": "16:9",
        "quality": "1080p",
        "count": 1,
        "model_name": "wan2.6-t2i",
        "status": "completed",
        "item_count": 0,
        "content_hash": "hash_zh_test",
    }
    rec = db.create_record(payload)
    rid = rec.get("id")
    rec2 = db.get_record(rid)
    assert rec2.get("positive_zh") == "正向中文"
    assert rec2.get("negative_zh") == "反向中文"
    print("ok", rid)

if __name__ == "__main__":
    main()
