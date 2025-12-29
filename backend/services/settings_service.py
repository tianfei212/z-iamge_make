from typing import Dict, Any
from backend.db.connection import get_conn

def get_global_settings() -> Dict[str, Any]:
    with get_conn() as conn:
        cur = conn.execute("SELECT common_subject, global_style, negative_prompt FROM global_settings WHERE id = 1")
        row = cur.fetchone()
        if not row:
            return {"common_subject": "", "global_style": "", "negative_prompt": ""}
        return {"common_subject": row[0] or "", "global_style": row[1] or "", "negative_prompt": row[2] or ""}

def update_global_settings(data: Dict[str, Any]) -> None:
    with get_conn() as conn:
        cur = conn.execute("SELECT 1 FROM global_settings WHERE id = 1")
        exists = cur.fetchone() is not None
        if not exists:
            conn.execute(
                "INSERT INTO global_settings(id, common_subject, global_style, negative_prompt) VALUES(1, ?, ?, ?)",
                [data.get("common_subject", ""), data.get("global_style", ""), data.get("negative_prompt", "")],
            )
        else:
            conn.execute(
                "UPDATE global_settings SET common_subject = ?, global_style = ?, negative_prompt = ? WHERE id = 1",
                [data.get("common_subject", ""), data.get("global_style", ""), data.get("negative_prompt", "")],
            )

