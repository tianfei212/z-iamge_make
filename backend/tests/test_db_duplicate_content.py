import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services.db_service import DBService

def main():
    db = DBService()
    payload_common = {
        "user_id": "-1",
        "session_id": "sess",
        "created_at": "2025123002",
        "base_prompt": "BP",
        "category_prompt": "环境",
        "refined_positive": "POS",
        "refined_negative": "NEG",
        "aspect_ratio": "16:9",
        "quality": "1080p",
        "count": 1,
        "model_name": "wan2.6-t2i",
        "status": "completed",
        "item_count": 0,
        "content_hash": "fixed_hash_for_test",
    }
    p1 = {"job_id": "job1", **payload_common}
    p2 = {"job_id": "job2", **payload_common}
    r1 = db.create_record(p1)
    r2 = db.create_record(p2)
    print("ok", r1.get("id"), r2.get("id"))

if __name__ == "__main__":
    main()
