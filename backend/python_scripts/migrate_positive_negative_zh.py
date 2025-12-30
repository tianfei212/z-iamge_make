import os
import sys
import logging
from typing import Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.db.connection import get_conn, DB_PATH
from backend.services.dashscope_client_service import DashScopeClient

log_path = os.path.join(os.path.dirname(DB_PATH), "migration.log")
logging.basicConfig(filename=log_path, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("migration")

def translate_pair(client: DashScopeClient, pos: str, neg: str) -> Tuple[str, str]:
    try:
        pos_zh = client._translate(pos or "") if pos else None
    except Exception as e:
        logger.error(f"translate pos failed: {e}")
        pos_zh = None
    try:
        neg_zh = client._translate(neg or "") if neg else None
    except Exception as e:
        logger.error(f"translate neg failed: {e}")
        neg_zh = None
    return pos_zh, neg_zh

def main():
    client = DashScopeClient()
    with get_conn() as conn:
        conn.execute("BEGIN")
        try:
            # Ensure columns exist
            cur = conn.execute("PRAGMA table_info(records)")
            cols = [r[1] for r in cur.fetchall()]
            if "positive_zh" not in cols:
                conn.execute("ALTER TABLE records ADD COLUMN positive_zh TEXT")
            if "negative_zh" not in cols:
                conn.execute("ALTER TABLE records ADD COLUMN negative_zh TEXT")
            # Backfill where missing and refined_* available
            cur = conn.execute("""
                SELECT id, refined_positive, refined_negative
                FROM records
                WHERE (positive_zh IS NULL OR positive_zh = '')
                   OR (negative_zh IS NULL OR negative_zh = '')
            """)
            rows = cur.fetchall()
            updated = 0
            for rid, pos, neg in rows:
                pos_zh, neg_zh = translate_pair(client, pos, neg)
                conn.execute(
                    "UPDATE records SET positive_zh = COALESCE(?, positive_zh), negative_zh = COALESCE(?, negative_zh) WHERE id=?",
                    (pos_zh, neg_zh, rid)
                )
                updated += 1
            # Create indexes if not exist
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_pos_zh ON records(positive_zh)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_records_neg_zh ON records(negative_zh)")
            logger.info(f"migration completed: updated_rows={updated}")
        except Exception as e:
            logger.error(f"migration failed: {e}")
            raise

if __name__ == "__main__":
    try:
        main()
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
