from typing import List, Dict, Any, Optional
from backend.db.connection import get_conn

def list_models() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.execute("SELECT id, name, provider, model_name, description, enabled, max_limit FROM models ORDER BY name ASC")
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "name": r[1],
                "provider": r[2],
                "model_name": r[3],
                "description": r[4],
                "enabled": int(r[5]) if r[5] is not None else 1,
                "max_limit": int(r[6]) if len(r) > 6 and r[6] is not None else 0,
            }
            for r in rows
        ]

def create_model(m: Dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO models(id, name, provider, model_name, description, enabled, max_limit) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                m.get("id"),
                m.get("name"),
                m.get("provider"),
                m.get("model_name"),
                m.get("description"),
                1 if m.get("enabled", 1) else 0,
                int(m.get("max_limit", 0) or 0),
            ],
        )

def update_model(model_id: str, data: Dict[str, Any]) -> None:
    fields = []
    values = []
    for k in ["name", "provider", "model_name", "description", "enabled", "max_limit"]:
        if k in data:
            fields.append(f"{k} = ?")
            v = data[k]
            if k == "enabled":
                v = 1 if v else 0
            if k == "max_limit":
                try:
                    v = int(v)
                except Exception:
                    v = 0
            values.append(v)
    if not fields:
        return
    values.append(model_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE models SET {', '.join(fields)} WHERE id = ?", values)

def delete_model(model_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM models WHERE id = ?", [model_id])

def get_model_id_by_model_name(model_name: str) -> Optional[str]:
    with get_conn() as conn:
        cur = conn.execute("SELECT id FROM models WHERE model_name = ?", [model_name])
        row = cur.fetchone()
        return row[0] if row else None

def update_limit_by_model_name(model_name: str, limit: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE models SET max_limit = ? WHERE model_name = ?", [int(limit), model_name])
