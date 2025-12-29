import time
import datetime
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.services.record_service import RecordService


def main():
    svc = RecordService.instance()
    svc.start()
    # simulate one job with two items
    job_meta = {
        "user_id": "u123",
        "session_id": "s456",
        "created_at": datetime.datetime.utcnow().strftime("%Y%m%d%H"),
        "prompt": "天空中飞翔的蓝色鸟",
        "category": "nature",
        "refined_positive": "A blue bird flying in the sky, high detail",
        "refined_negative": "",
        "aspect_ratio": "16:9",
        "resolution": "1K",
        "count": 2,
        "model": "wan2.6-t2i",
    }
    items = [
        {
            "seed": 123,
            "temperature": 1.0,
            "top_p": 0.8,
            "relative_url": "/api/images/abc/raw",
            "absolute_path": "/tmp/fake/path1.png",
        },
        {
            "seed": 456,
            "temperature": 1.0,
            "top_p": 0.8,
            "relative_url": "/api/images/def/raw",
            "absolute_path": "/tmp/fake/path2.png",
        },
    ]
    svc.add_record(job_meta, items)
    time.sleep(1.0)
    svc.shutdown()
    day = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    result = svc.verify(day)
    print(result)


if __name__ == "__main__":
    main()
