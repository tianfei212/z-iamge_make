from typing import Any, Dict, List, Optional
import logging
from backend.db.repositories import RecordsRepo, ItemsRepo
from backend.db.connection import init_db

logger = logging.getLogger("db_service")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setLevel(logging.DEBUG)
    _f = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
    _h.setFormatter(_f)
    logger.addHandler(_h)

init_db()


class DBService:
    def __init__(self) -> None:
        self.records = RecordsRepo()
        self.items = ItemsRepo()

    def create_record(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.debug("存储数据库的内容: %s", payload)
            rid = self.records.create_or_update(payload)
            rec = self.records.get(rid)
            logger.debug("写入成功: id=%s", rid)
            return rec or {}
        except Exception as e:
            logger.error("写入失败: %s", e)
            raise

    def update_record(self, record_id: int, patch: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.debug("存储数据库的内容: id=%s patch=%s", record_id, patch)
            self.records.update(record_id, patch)
            rec = self.records.get(record_id)
            logger.debug("写入成功: id=%s", record_id)
            return rec or {}
        except Exception as e:
            logger.error("写入失败: %s", e)
            raise

    def list_records(self, limit: int, offset: int, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.records.list(limit, offset, filters)

    def get_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        return self.records.get(record_id)

    def delete_record(self, record_id: int) -> None:
        try:
            logger.debug("存储数据库的内容: delete id=%s", record_id)
            self.records.delete(record_id)
            logger.debug("写入成功: delete id=%s", record_id)
        except Exception as e:
            logger.error("写入失败: %s", e)
            raise

    def add_item(self, record_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.debug("存储数据库的内容: record_id=%s item=%s", record_id, payload)
            iid, inserted = self.items.insert_unique(record_id, payload)
            if inserted:
                self.records.increment_item_count(record_id, 1)
            row = self.items.get(record_id, iid) or {}
            logger.debug("写入成功: item_id=%s inserted=%s", iid, inserted)
            return row
        except Exception as e:
            logger.error("写入失败: %s", e)
            raise

    def list_items(self, record_id: int, limit: int, offset: int) -> List[Dict[str, Any]]:
        return self.items.list(record_id, limit, offset)

    def get_item(self, record_id: int, item_id: int) -> Optional[Dict[str, Any]]:
        return self.items.get(record_id, item_id)

    def update_item(self, record_id: int, item_id: int, patch: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.debug("存储数据库的内容: record_id=%s item_id=%s patch=%s", record_id, item_id, patch)
            self.items.update(record_id, item_id, patch)
            row = self.items.get(record_id, item_id) or {}
            logger.debug("写入成功: item_id=%s", item_id)
            return row
        except Exception as e:
            logger.error("写入失败: %s", e)
            raise

    def delete_item(self, record_id: int, item_id: int) -> None:
        try:
            logger.debug("存储数据库的内容: delete record_id=%s item_id=%s", record_id, item_id)
            self.items.delete(record_id, item_id)
            logger.debug("写入成功: delete item_id=%s", item_id)
        except Exception as e:
            logger.error("写入失败: %s", e)
            raise

    def add_items(self, record_id: int, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            logger.debug("存储数据库的内容: record_id=%s items_count=%s", record_id, len(items))
            ids, inserted_count = self.items.insert_many(record_id, items)
            if inserted_count:
                self.records.increment_item_count(record_id, inserted_count)
            rows = [self.items.get(record_id, iid) or {} for iid in ids]
            logger.debug("写入成功: items_inserted=%s", inserted_count)
            return rows
        except Exception as e:
            logger.error("写入失败: %s", e)
            raise

    def update_record_by_job(self, job_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            logger.debug("存储数据库的内容: job_id=%s patch=%s", job_id, patch)
            rid = self.records.update_by_job(job_id, patch)
            if rid is None:
                return None
            rec = self.records.get(rid)
            logger.debug("写入成功: id=%s", rid)
            return rec or {}
        except Exception as e:
            logger.error("写入失败: %s", e)
            raise

    def get_items_count(self, record_id: int) -> int:
        return self.items.count_by_record(record_id)

    def validate_record_integrity(self, record_id: int) -> Dict[str, Any]:
        rec = self.records.get(record_id)
        if not rec:
            return {"record_exists": False}
        actual = self.items.count_by_record(record_id)
        expected = int(rec.get("item_count") or 0)
        ok = (actual == expected)
        return {
            "record_exists": True,
            "record_id": record_id,
            "expected_item_count": expected,
            "actual_item_count": actual,
            "valid": ok
        }
