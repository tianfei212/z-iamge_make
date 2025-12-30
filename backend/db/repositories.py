from typing import Any, Dict, List, Optional, Tuple
from .connection import get_conn


class RecordsRepo:
    def create_or_update(self, data: Dict[str, Any]) -> int:
        with get_conn() as conn:
            cur = conn.cursor()
            # First try to update existing record by job_id (without touching content_hash to avoid unique conflict)
            cur.execute("SELECT id FROM records WHERE job_id=?", (data.get("job_id"),))
            row = cur.fetchone()
            if row:
                rid = int(row[0])
                cur.execute(
                    """
                    UPDATE records SET
                        user_id=?,
                        session_id=?,
                        created_at=?,
                        base_prompt=?,
                        category_prompt=?,
                        refined_positive=?,
                        refined_negative=?,
                        aspect_ratio=?,
                        quality=?,
                        count=?,
                        model_name=?,
                        status=?,
                        item_count=?
                    WHERE id=?
                    """,
                    (
                        data.get("user_id"),
                        data.get("session_id"),
                        data.get("created_at"),
                        data.get("base_prompt"),
                        data.get("category_prompt"),
                        data.get("refined_positive"),
                        data.get("refined_negative"),
                        data.get("aspect_ratio"),
                        data.get("quality"),
                        data.get("count"),
                        data.get("model_name"),
                        data.get("status"),
                        int(data.get("item_count") or 0),
                        rid,
                    ),
                )
                return rid
            # Otherwise insert, but ignore if content_hash already exists to avoid UNIQUE violation
            cur.execute(
                """
                INSERT OR IGNORE INTO records(job_id,user_id,session_id,created_at,base_prompt,category_prompt,refined_positive,refined_negative,aspect_ratio,quality,count,model_name,status,content_hash,item_count)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    data.get("job_id"),
                    data.get("user_id"),
                    data.get("session_id"),
                    data.get("created_at"),
                    data.get("base_prompt"),
                    data.get("category_prompt"),
                    data.get("refined_positive"),
                    data.get("refined_negative"),
                    data.get("aspect_ratio"),
                    data.get("quality"),
                    data.get("count"),
                    data.get("model_name"),
                    data.get("status"),
                    data.get("content_hash"),
                    int(data.get("item_count") or 0),
                ),
            )
            # Resolve id either by job_id or content_hash
            cur.execute("SELECT id FROM records WHERE job_id=?", (data.get("job_id"),))
            row = cur.fetchone()
            if row:
                return int(row[0])
            cur.execute("SELECT id FROM records WHERE content_hash=?", (data.get("content_hash"),))
            row = cur.fetchone()
            if row:
                return int(row[0])
            # As a fallback, insert without content_hash if still not present
            cur.execute(
                """
                INSERT INTO records(job_id,user_id,session_id,created_at,base_prompt,category_prompt,refined_positive,refined_negative,aspect_ratio,quality,count,model_name,status,item_count)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    data.get("job_id"),
                    data.get("user_id"),
                    data.get("session_id"),
                    data.get("created_at"),
                    data.get("base_prompt"),
                    data.get("category_prompt"),
                    data.get("refined_positive"),
                    data.get("refined_negative"),
                    data.get("aspect_ratio"),
                    data.get("quality"),
                    data.get("count"),
                    data.get("model_name"),
                    data.get("status"),
                    int(data.get("item_count") or 0),
                ),
            )
            cur.execute("SELECT id FROM records WHERE job_id=?", (data.get("job_id"),))
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def update(self, record_id: int, patch: Dict[str, Any]) -> None:
        if not patch:
            return
        keys = []
        vals: List[Any] = []
        for k, v in patch.items():
            keys.append(f"{k}=?")
            vals.append(v)
        sql = f"UPDATE records SET {', '.join(keys)} WHERE id=?"
        vals.append(record_id)
        with get_conn() as conn:
            conn.execute(sql, tuple(vals))

    def get(self, record_id: int) -> Optional[Dict[str, Any]]:
        with get_conn() as conn:
            cur = conn.execute("SELECT * FROM records WHERE id=?", (record_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            return dict(zip(cols, row))

    def list(self, limit: int, offset: int, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        where = []
        vals: List[Any] = []
        if filters.get("created_at"):
            where.append("created_at=?")
            vals.append(filters["created_at"])
        if filters.get("category_prompt"):
            where.append("category_prompt=?")
            vals.append(filters["category_prompt"])
        if filters.get("model_name"):
            where.append("model_name=?")
            vals.append(filters["model_name"])
        if filters.get("status"):
            where.append("status=?")
            vals.append(filters["status"])
        sql = "SELECT * FROM records"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        vals.extend([limit, offset])
        with get_conn() as conn:
            cur = conn.execute(sql, tuple(vals))
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def delete(self, record_id: int) -> None:
        with get_conn() as conn:
            conn.execute("DELETE FROM records WHERE id=?", (record_id,))

    def by_job_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        with get_conn() as conn:
            cur = conn.execute("SELECT * FROM records WHERE job_id=?", (job_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            return dict(zip(cols, row))

    def increment_item_count(self, record_id: int, n: int) -> None:
        with get_conn() as conn:
            conn.execute("UPDATE records SET item_count=item_count+? WHERE id=?", (n, record_id))

    def update_by_job(self, job_id: str, patch: Dict[str, Any]) -> Optional[int]:
        if not patch:
            return None
        keys = []
        vals: List[Any] = []
        for k, v in patch.items():
            keys.append(f"{k}=?")
            vals.append(v)
        sql = f"UPDATE records SET {', '.join(keys)} WHERE job_id=?"
        vals.append(job_id)
        with get_conn() as conn:
            conn.execute(sql, tuple(vals))
            cur = conn.execute("SELECT id FROM records WHERE job_id=?", (job_id,))
            row = cur.fetchone()
            return int(row[0]) if row else None

class ItemsRepo:
    def count_by_record(self, record_id: int) -> int:
        with get_conn() as conn:
            cur = conn.execute("SELECT COUNT(1) FROM items WHERE record_id=?", (record_id,))
            row = cur.fetchone()
            return int(row[0] or 0)
    def insert_unique(self, record_id: int, data: Dict[str, Any]) -> Tuple[int, bool]:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO items(record_id,seed,temperature,top_p,relative_url,absolute_path)
                VALUES(?,?,?,?,?,?)
                """,
                (
                    record_id,
                    data.get("seed"),
                    data.get("temperature"),
                    data.get("top_p"),
                    data.get("relative_url"),
                    data.get("absolute_path"),
                ),
            )
            inserted = cur.rowcount == 1
            cur.execute(
                "SELECT id FROM items WHERE record_id=? AND seed=? AND relative_url=? AND absolute_path=?",
                (record_id, data.get("seed"), data.get("relative_url"), data.get("absolute_path")),
            )
            row = cur.fetchone()
            return int(row[0]), inserted

    def insert_many(self, record_id: int, items: List[Dict[str, Any]]) -> Tuple[List[int], int]:
        ids: List[int] = []
        inserted_count = 0
        with get_conn() as conn:
            cur = conn.cursor()
            for data in items:
                cur.execute(
                    """
                    INSERT OR IGNORE INTO items(record_id,seed,temperature,top_p,relative_url,absolute_path)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (
                        record_id,
                        data.get("seed"),
                        data.get("temperature"),
                        data.get("top_p"),
                        data.get("relative_url"),
                        data.get("absolute_path"),
                    ),
                )
                if cur.rowcount == 1:
                    inserted_count += 1
                cur.execute(
                    "SELECT id FROM items WHERE record_id=? AND seed=? AND relative_url=? AND absolute_path=?",
                    (record_id, data.get("seed"), data.get("relative_url"), data.get("absolute_path")),
                )
                row = cur.fetchone()
                ids.append(int(row[0]))
        return ids, inserted_count

    def get(self, record_id: int, item_id: int) -> Optional[Dict[str, Any]]:
        with get_conn() as conn:
            cur = conn.execute("SELECT * FROM items WHERE id=? AND record_id=?", (item_id, record_id))
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            return dict(zip(cols, row))

    def list(self, record_id: int, limit: int, offset: int) -> List[Dict[str, Any]]:
        with get_conn() as conn:
            cur = conn.execute(
                "SELECT * FROM items WHERE record_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (record_id, limit, offset),
            )
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def update(self, record_id: int, item_id: int, patch: Dict[str, Any]) -> None:
        if not patch:
            return
        keys = []
        vals: List[Any] = []
        for k, v in patch.items():
            keys.append(f"{k}=?")
            vals.append(v)
        sql = f"UPDATE items SET {', '.join(keys)} WHERE id=? AND record_id=?"
        vals.extend([item_id, record_id])
        with get_conn() as conn:
            conn.execute(sql, tuple(vals))

    def delete(self, record_id: int, item_id: int) -> None:
        with get_conn() as conn:
            conn.execute("DELETE FROM items WHERE id=? AND record_id=?", (item_id, record_id))
