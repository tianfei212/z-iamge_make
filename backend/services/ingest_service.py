import os
import json
import hashlib
from typing import Dict, Any, List
from backend.services.db_service import DBService


class IngestService:
    def __init__(self) -> None:
        self.svc = DBService()

    def _map_record(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        rec = {
            "job_id": None,
            "user_id": str(obj.get("用户ID", "-1")),
            "session_id": str(obj.get("SessionID", "-1")),
            "created_at": str(obj.get("创建时间", "")),
            "base_prompt": str(obj.get("通用基础提示词", "")),
            "category_prompt": str(obj.get("分类描述提示词", "")),
            "refined_positive": str(obj.get("优化后正向提示词", "")) or None,
            "refined_negative": str(obj.get("优化后反向提示词", "")) or None,
            "aspect_ratio": str(obj.get("比例", "")),
            "quality": str(obj.get("画质", "")),
            "count": int(obj.get("数量", 1)),
            "model_name": str(obj.get("模型名称", "")),
            "status": "completed",
            "item_count": 0,
        }
        return rec

    def _map_items(self, obj: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = []
        for it in obj.get("生成记录", []) or []:
            items.append(
                {
                    "seed": str(it.get("随机种子", "")),
                    "temperature": float(it.get("热度值", 0.0)),
                    "top_p": float(it.get("top值", 0.0)),
                    "relative_url": str(it.get("相对url路径", "")),
                    "absolute_path": str(it.get("存储绝对路径", "")),
                }
            )
        return items

    def ingest_file(self, file_path: str) -> Dict[str, Any]:
        total = 0
        inserted = 0
        items_inserted = 0
        if not os.path.isfile(file_path):
            return {"total": 0, "inserted": 0, "items_inserted": 0}
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                obj = json.loads(line)
                payload = self._map_record(obj)
                h = hashlib.sha256(line.encode("utf-8")).hexdigest()
                payload["content_hash"] = h
                existing = self.svc.records.by_job_id(payload.get("job_id")) if payload.get("job_id") else None
                rec = self.svc.create_record(payload)
                rid = rec.get("id")
                rows = self.svc.add_items(rid, self._map_items(obj))
                items_inserted += len(rows)
                self.svc.update_record(rid, {"item_count": len(rows), "status": "completed"})
                inserted += 1
        return {"total": total, "inserted": inserted, "items_inserted": items_inserted}

