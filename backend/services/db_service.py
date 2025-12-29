from typing import Any, Dict, List, Optional
import logging
from backend.db.repositories import RecordsRepo, ItemsRepo
from backend.db.connection import init_db

logger = logging.getLogger("db_service")

init_db()


class DBService:
    def __init__(self) -> None:
        self.records = RecordsRepo()
        self.items = ItemsRepo()

    def create_record(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        rid = self.records.create_or_update(payload)
        rec = self.records.get(rid)
        return rec or {}

    def update_record(self, record_id: int, patch: Dict[str, Any]) -> Dict[str, Any]:
        self.records.update(record_id, patch)
        rec = self.records.get(record_id)
        return rec or {}

    def list_records(self, limit: int, offset: int, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.records.list(limit, offset, filters)

    def get_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        return self.records.get(record_id)

    def delete_record(self, record_id: int) -> None:
        self.records.delete(record_id)

    def add_item(self, record_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        iid = self.items.insert_unique(record_id, payload)
        return self.items.get(record_id, iid) or {}

    def list_items(self, record_id: int, limit: int, offset: int) -> List[Dict[str, Any]]:
        return self.items.list(record_id, limit, offset)

    def get_item(self, record_id: int, item_id: int) -> Optional[Dict[str, Any]]:
        return self.items.get(record_id, item_id)

    def update_item(self, record_id: int, item_id: int, patch: Dict[str, Any]) -> Dict[str, Any]:
        self.items.update(record_id, item_id, patch)
        return self.items.get(record_id, item_id) or {}

    def delete_item(self, record_id: int, item_id: int) -> None:
        self.items.delete(record_id, item_id)

