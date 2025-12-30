import os
import sys
import sqlite3
import shutil
from typing import List, Dict, Any

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.db.connection import DB_PATH

NEW_DB = os.path.join(os.path.dirname(DB_PATH), "app_new.db")
BACKUP_DB = os.path.join(os.path.dirname(DB_PATH), "app.bak")

def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;
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
            positive_zh TEXT,
            negative_zh TEXT,
            aspect_ratio TEXT,
            quality TEXT,
            count INTEGER,
            model_name TEXT,
            status TEXT,
            item_count INTEGER DEFAULT 0,
            content_hash TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uniq_records_hash ON records(content_hash);
        CREATE INDEX IF NOT EXISTS idx_records_created ON records(created_at);
        CREATE INDEX IF NOT EXISTS idx_records_cat_model ON records(category_prompt, model_name);
        CREATE INDEX IF NOT EXISTS idx_records_pos_zh ON records(positive_zh);
        CREATE INDEX IF NOT EXISTS idx_records_neg_zh ON records(negative_zh);
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            record_id INTEGER REFERENCES records(id) ON DELETE CASCADE,
            seed TEXT,
            temperature REAL,
            top_p REAL,
            relative_url TEXT,
            absolute_path TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uniq_items_seed_rel_abs ON items(record_id, seed, relative_url, absolute_path);
        CREATE INDEX IF NOT EXISTS idx_items_abs ON items(absolute_path);
        CREATE INDEX IF NOT EXISTS idx_items_rel ON items(relative_url);
        """
    )

def fetch_all(conn: sqlite3.Connection, sql: str) -> List[Dict[str, Any]]:
    cur = conn.execute(sql)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

def copy_data(old: sqlite3.Connection, new: sqlite3.Connection) -> None:
    old_records = fetch_all(old, "SELECT * FROM records ORDER BY id")
    for r in old_records:
        new.execute(
            """
            INSERT INTO records(id,job_id,user_id,session_id,created_at,base_prompt,category_prompt,refined_positive,refined_negative,positive_zh,negative_zh,aspect_ratio,quality,count,model_name,status,item_count,content_hash)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                r.get("id"),
                r.get("job_id"),
                r.get("user_id"),
                r.get("session_id"),
                r.get("created_at"),
                r.get("base_prompt"),
                r.get("category_prompt"),
                r.get("refined_positive"),
                r.get("refined_negative"),
                r.get("positive_zh"),
                r.get("negative_zh"),
                r.get("aspect_ratio"),
                r.get("quality"),
                r.get("count"),
                r.get("model_name"),
                r.get("status"),
                r.get("item_count"),
                r.get("content_hash"),
            ),
        )
    old_items = fetch_all(old, "SELECT * FROM items ORDER BY id")
    for it in old_items:
        new.execute(
            """
            INSERT INTO items(id,record_id,seed,temperature,top_p,relative_url,absolute_path)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                it.get("id"),
                it.get("record_id"),
                it.get("seed"),
                it.get("temperature"),
                it.get("top_p"),
                it.get("relative_url"),
                it.get("absolute_path"),
            ),
        )

def main():
    if os.path.exists(NEW_DB):
        os.remove(NEW_DB)
    old = sqlite3.connect(DB_PATH)
    new = sqlite3.connect(NEW_DB)
    try:
        create_schema(new)
        copy_data(old, new)
        new.commit()
        print("NEW_DB_READY", NEW_DB)
    finally:
        old.close()
        new.close()
    # do not swap automatically to avoid interfering with running services
    print("BACKUP_HINT", BACKUP_DB)

if __name__ == "__main__":
    main()
