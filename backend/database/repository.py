import sqlite3
import logging
import time
import threading
from typing import Optional, List, Dict, Any
from collections import OrderedDict
from datetime import datetime

logger = logging.getLogger("database.repository")

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key not in self.cache:
                return None
            self.cache.move_to_end(key)
            return self.cache[key]

    def put(self, key: str, value: Any):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

    def invalidate(self, key: str):
        with self.lock:
            if key in self.cache:
                del self.cache[key]

class SessionRepository:
    def __init__(self, pool):
        self.pool = pool
        self._cache = LRUCache(capacity=100)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        schema = """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            input_params TEXT NOT NULL,
            qwen_prompt TEXT NOT NULL,
            random_params TEXT NOT NULL,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            version INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_created_at ON sessions(created_at);
        """
        with self.pool.acquire() as conn:
            conn.executescript(schema)
            conn.commit()

    def _execute_with_retry(self, func, *args, max_retries=3, **kwargs):
        """Execute a function with retry logic for database locks."""
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000
                if duration > 30:
                    logger.warning(f"Slow query detected: {duration:.2f}ms")
                return result
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Database locked, retrying... ({attempt + 1}/{max_retries})")
                    time.sleep(0.1 * (attempt + 1))
                    continue
                logger.error(f"Database error: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

    def insert_session(self, session_id: str, input_params: str, qwen_prompt: str, random_params: str, image_url: str = None):
        if not all([session_id, input_params, qwen_prompt, random_params]):
            raise ValueError("Missing required fields")

        def _do_insert():
            with self.pool.acquire() as conn:
                conn.execute(
                    """
                    INSERT INTO sessions (session_id, input_params, qwen_prompt, random_params, image_url)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (session_id, input_params, qwen_prompt, random_params, image_url)
                )
                conn.commit()
                logger.info(f"Created session {session_id}")

        self._execute_with_retry(_do_insert)

    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        # Check cache
        cached = self._cache.get(session_id)
        if cached:
            return cached

        def _do_get():
            with self.pool.acquire() as conn:
                cursor = conn.execute(
                    "SELECT * FROM sessions WHERE session_id = ? AND is_deleted = 0",
                    (session_id,)
                )
                row = cursor.fetchone()
                if row:
                    data = dict(row)
                    self._cache.put(session_id, data)
                    return data
                return None

        return self._execute_with_retry(_do_get)

    def get_image_url(self, session_id: str) -> Optional[str]:
        session = self.get_session_by_id(session_id)
        return session["image_url"] if session else None

    def get_all_sessions(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        def _do_get_all():
            with self.pool.acquire() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM sessions 
                    WHERE is_deleted = 0 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                )
                return [dict(row) for row in cursor.fetchall()]

        return self._execute_with_retry(_do_get_all)

    def update_session_params(self, session_id: str, new_params: str):
        def _do_update():
            with self.pool.acquire() as conn:
                # Optimistic locking using version
                cursor = conn.execute(
                    """
                    UPDATE sessions 
                    SET input_params = ?, updated_at = CURRENT_TIMESTAMP, version = version + 1
                    WHERE session_id = ? AND is_deleted = 0
                    """,
                    (new_params, session_id)
                )
                if cursor.rowcount == 0:
                    # Check if it exists but is deleted or just doesn't exist
                    raise ValueError(f"Session {session_id} not found or update conflict")
                conn.commit()
                self._cache.invalidate(session_id)
                logger.info(f"Updated params for session {session_id}")

        self._execute_with_retry(_do_update)

    def update_image_url(self, session_id: str, new_url: str):
        def _do_update():
            with self.pool.acquire() as conn:
                cursor = conn.execute(
                    """
                    UPDATE sessions 
                    SET image_url = ?, updated_at = CURRENT_TIMESTAMP, version = version + 1
                    WHERE session_id = ? AND is_deleted = 0
                    """,
                    (new_url, session_id)
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Session {session_id} not found or update conflict")
                conn.commit()
                self._cache.invalidate(session_id)
                logger.info(f"Updated image_url for session {session_id}")

        self._execute_with_retry(_do_update)

    def delete_session(self, session_id: str, soft: bool = True):
        def _do_delete():
            with self.pool.acquire() as conn:
                if soft:
                    cursor = conn.execute(
                        "UPDATE sessions SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
                        (session_id,)
                    )
                else:
                    cursor = conn.execute(
                        "DELETE FROM sessions WHERE session_id = ?",
                        (session_id,)
                    )
                
                if cursor.rowcount > 0:
                    conn.commit()
                    self._cache.invalidate(session_id)
                    logger.info(f"Deleted session {session_id} (soft={soft})")
                else:
                    logger.warning(f"Session {session_id} not found for deletion")

        self._execute_with_retry(_do_delete)

    def clean_expired_sessions(self, expiry_days: int = 30):
        def _do_clean():
            with self.pool.acquire() as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM sessions 
                    WHERE created_at < datetime('now', ?) 
                    """,
                    (f'-{expiry_days} days',)
                )
                conn.commit()
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    logger.info(f"Cleaned {deleted_count} expired sessions")
                    # Clear entire cache to be safe or rely on individual access? 
                    # Cache stores by ID, so it's fine. If we query a deleted ID, cache miss -> DB miss -> None.

        self._execute_with_retry(_do_clean)
