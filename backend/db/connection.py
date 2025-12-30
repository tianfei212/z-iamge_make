import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "app.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.executescript(
            """
            DROP INDEX IF EXISTS uniq_items_rel_abs;
            CREATE UNIQUE INDEX IF NOT EXISTS uniq_records_hash ON records(content_hash);
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
            CREATE UNIQUE INDEX IF NOT EXISTS uniq_items_seed_rel_abs ON items(record_id, seed, relative_url, absolute_path);
            CREATE INDEX IF NOT EXISTS idx_items_abs ON items(absolute_path);
            CREATE INDEX IF NOT EXISTS idx_items_rel ON items(relative_url);

            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                provider TEXT NOT NULL,
                model_name TEXT NOT NULL,
                description TEXT,
                enabled INTEGER DEFAULT 1,
                max_limit INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_models_provider ON models(provider);
            CREATE INDEX IF NOT EXISTS idx_models_enabled ON models(enabled);

            CREATE TABLE IF NOT EXISTS categories (
                name TEXT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS prompts (
                category TEXT PRIMARY KEY REFERENCES categories(name) ON DELETE CASCADE,
                prompt TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS global_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                common_subject TEXT,
                global_style TEXT,
                negative_prompt TEXT
            );
            """
        )
    finally:
        conn.close()

    # Add missing columns for migrations
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("PRAGMA table_info(models)")
        cols = [r[1] for r in cur.fetchall()]
        if "max_limit" not in cols:
            conn.execute("ALTER TABLE models ADD COLUMN max_limit INTEGER DEFAULT 0")
            conn.commit()
        # migrate old 'limit' column if exists
        if "limit" in cols and "max_limit" in cols:
            try:
                conn.execute("UPDATE models SET max_limit = COALESCE(max_limit, limit)")
                conn.commit()
            except Exception:
                pass
        # ensure records has zh columns
        cur = conn.execute("PRAGMA table_info(records)")
        rcols = [r[1] for r in cur.fetchall()]
        if "positive_zh" not in rcols:
            conn.execute("ALTER TABLE records ADD COLUMN positive_zh TEXT")
            conn.commit()
        if "negative_zh" not in rcols:
            conn.execute("ALTER TABLE records ADD COLUMN negative_zh TEXT")
            conn.commit()
        # indexes for zh columns
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_pos_zh ON records(positive_zh)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_records_neg_zh ON records(negative_zh)")
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
