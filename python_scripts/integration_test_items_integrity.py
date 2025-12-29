#!/usr/bin/env python3
import time
import json
import os
import sys
import requests

BASE = "http://localhost:8000"

def generate(count=2):
    payload = {
        "prompt": "批量生成测试",
        "category": "植物",
        "count": count,
        "service": "z_image",
        "size": "1024*1024",
        "prompt_extend": False,
        "resolution": "1080p",
        "aspect_ratio": "16:9",
        "model": ""
    }
    r = requests.post(f"{BASE}/api/generate", json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["job_id"]

def find_record(job_id, created_at_hour):
    r = requests.get(f"{BASE}/api/records", params={"created_at": created_at_hour}, timeout=30)
    r.raise_for_status()
    data = r.json()
    for rec in data.get("records", []):
        if rec.get("job_id") == job_id:
            return rec
    return None

def get_items(record_id):
    r = requests.get(f"{BASE}/api/records/{record_id}/items", timeout=30)
    r.raise_for_status()
    return r.json().get("items", [])

def validate_record(record_id):
    r = requests.get(f"{BASE}/api/records/{record_id}/validate", timeout=30)
    r.raise_for_status()
    return r.json()

def main():
    job_id = generate(count=2)
    created_at_hour = time.strftime("%Y%m%d%H", time.gmtime())
    for _ in range(24):
        time.sleep(5)
        rec = find_record(job_id, created_at_hour)
        if rec:
            record_id = rec["id"]
            items = get_items(record_id)
            report = validate_record(record_id)
            print(json.dumps({
                "job_id": job_id,
                "record_id": record_id,
                "item_count": rec.get("item_count"),
                "items_len": len(items),
                "validate": report
            }, ensure_ascii=False))
            if len(items) >= 2 and report.get("valid"):
                sys.exit(0)
    print("FAILED: integrity check", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
