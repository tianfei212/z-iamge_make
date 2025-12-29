from typing import List
from backend.db.connection import get_conn

def list_categories() -> List[str]:
    with get_conn() as conn:
        cur = conn.execute("SELECT name FROM categories ORDER BY name ASC")
        return [r[0] for r in cur.fetchall()]

def create_category(name: str) -> None:
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", [name])

def delete_category(name: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM categories WHERE name = ?", [name])

