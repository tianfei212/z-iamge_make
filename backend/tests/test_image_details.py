import os
import sys
from fastapi.testclient import TestClient

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.main import app
from backend.db.connection import DB_PATH, init_db, get_conn
from backend.services.db_service import DBService

def setup_outputs(category: str, filename: str) -> str:
    base = os.path.abspath("outputs")
    path = os.path.join(base, category)
    os.makedirs(path, exist_ok=True)
    full = os.path.join(path, filename)
    with open(full, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")  # minimal header
    return full

def main():
    try:
        os.remove(DB_PATH)
    except FileNotFoundError:
        pass
    init_db()
    svc = DBService()
    category = "testcat"
    filename = "test.png"
    full_path = setup_outputs(category, filename)
    rec = svc.create_record({
        "job_id": "job_test_details",
        "user_id": "u1",
        "session_id": "s1",
        "created_at": "2025122902",
        "base_prompt": "base",
        "category_prompt": category,
        "refined_positive": "pos",
        "refined_negative": "neg",
        "aspect_ratio": "16:9",
        "quality": "1K",
        "count": 1,
        "model_name": "wan2.6-t2i",
        "status": "completed",
        "content_hash": "hash_x",
        "item_count": 1,
    })
    rid = rec["id"]
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO items(record_id,seed,temperature,top_p,relative_url,absolute_path) VALUES(?,?,?,?,?,?)",
            (rid, "seed", 0.7, 0.6, f"{category}/{filename}", full_path)
        )
    client = TestClient(app)
    r = client.get(f"/api/images/by-filename/{filename}/details", params={"category": category})
    print(r.status_code, r.json())

if __name__ == "__main__":
    main()
