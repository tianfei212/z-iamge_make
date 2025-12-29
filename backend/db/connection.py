import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY,
                job_id TEXT UNIQUE,
                user_id TEXT,
                session_id TEXT,
                created_at TEXT,
                base_prompt TEXT,
                category_prompt TEXT,
                refined_positive TEXT,
                refined_negative TEXT,
                aspect_ratio TEXT,
                quality TEXT,
                count INTEGER,
                model_name TEXT,
                status TEXT,
                item_count INTEGER DEFAULT 0,
                content_hash TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_records_created ON records(created_at);
            CREATE INDEX IF NOT EXISTS idx_records_cat_model ON records(category_prompt, model_name);
            
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                record_id INTEGER REFERENCES records(id) ON DELETE CASCADE,
                seed TEXT,
                temperature REAL,
                top_p REAL,
                relative_url TEXT,
                absolute_path TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS uniq_items_rel_abs ON items(record_id, relative_url, absolute_path);
            CREATE INDEX IF NOT EXISTS idx_items_abs ON items(absolute_path);
            CREATE INDEX IF NOT EXISTS idx_items_rel ON items(relative_url);
            """
        )
    finally:
        conn.close()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

