import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services.db_service import DBService
from backend.db.connection import DB_PATH, init_db


def main():
    # clean db
    try:
        os.remove(DB_PATH)
    except FileNotFoundError:
        pass
    init_db()
    svc = DBService()
    # create record
    rec = svc.create_record({
        "job_id": "job_test_1",
        "user_id": "u1",
        "session_id": "s1",
        "created_at": "2025122902",
        "base_prompt": "蓝鸟",
        "category_prompt": "nature",
        "aspect_ratio": "16:9",
        "quality": "1K",
        "count": 2,
        "model_name": "wan2.6-t2i",
        "status": "submitted",
    })
    rid = rec["id"]
    # update prompts
    svc.update_record(rid, {"refined_positive": "A blue bird", "status": "generating"})
    # add items
    svc.add_item(rid, {
        "seed": "a",
        "temperature": 0.8,
        "top_p": 0.6,
        "relative_url": "/api/images/bmF0/raw",
        "absolute_path": "/abs/path/a.png",
    })
    svc.add_item(rid, {
        "seed": "b",
        "temperature": 0.8,
        "top_p": 0.6,
        "relative_url": "/api/images/bmF1/raw",
        "absolute_path": "/abs/path/b.png",
    })
    items = svc.list_items(rid, 10, 0)
    print(json.dumps({"record_id": rid, "items_count": len(items)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
