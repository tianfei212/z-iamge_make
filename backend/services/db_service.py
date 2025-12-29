from typing import Any, Dict, List, Optional
import logging
from backend.db.repositories import RecordsRepo, ItemsRepo
from backend.db.connection import init_db

logger = logging.getLogger("db_service")
logger.setLevel(logging.DEBUG)

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
            iid = self.items.insert_unique(record_id, payload)
            row = self.items.get(record_id, iid) or {}
            logger.debug("写入成功: item_id=%s", iid)
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
