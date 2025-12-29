from typing import Dict
from backend.db.connection import get_conn

def list_prompts() -> Dict[str, str]:
    with get_conn() as conn:
        cur = conn.execute("SELECT category, prompt FROM prompts ORDER BY category ASC")
        return {r[0]: r[1] for r in cur.fetchall()}

def upsert_prompt(category: str, prompt: str) -> None:
    with get_conn() as conn:
        conn.execute("INSERT INTO prompts(category, prompt) VALUES(?, ?) ON CONFLICT(category) DO UPDATE SET prompt=excluded.prompt", [category, prompt])

def delete_prompt(category: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM prompts WHERE category = ?", [category])

