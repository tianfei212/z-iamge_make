from backend.db.connection import init_db, get_conn
from backend.config.settings import load_settings
from backend.services.model_registry_service import list_available_models

def main():
    init_db()
    s = load_settings()
    raw = s.raw
    models_list = raw.get("models_list")
    if not isinstance(models_list, list) or not models_list:
        models_list = []
        for m in list_available_models(s).get("models", []):
            models_list.append({
                "id": m.get("id"),
                "name": m.get("name"),
                "provider": m.get("provider"),
                "model_name": m.get("modelName"),
                "description": m.get("description"),
                "enabled": 1,
            })
    categories = raw.get("categories")
    if not isinstance(categories, list) or not categories:
        categories = ["人物","动物","机械","植物","火焰","建筑","环境"]
    prompts_map = raw.get("prompts_map")
    if not isinstance(prompts_map, dict) or not prompts_map:
        prompts_map = {
            "人物": "特写肖像，动态姿势，服饰质感极其写实",
            "动物": "自然栖息地中的生物，极具张力的动作瞬间",
            "机械": "复杂的内部结构外露，蓝图感与实物结合",
            "植物": "带有魔幻感的植物形态，微观纹理与生物发光",
            "火焰": "不同色温混合的火焰，粒子飞溅与烟雾效果",
            "建筑": "未来主义建筑，几何空间，冷淡材质",
            "环境": "宏大的地貌景观，史诗感的大气效果"
        }
    g = raw.get("global") if isinstance(raw.get("global"), dict) else {}
    common_subject = g.get("common_subject", "")
    global_style = g.get("global_style", "")
    negative_prompt = g.get("negative_prompt", "")
    with get_conn() as conn:
        for m in models_list:
            conn.execute(
                "INSERT OR IGNORE INTO models(id,name,provider,model_name,description,enabled) VALUES(?,?,?,?,?,?)",
                [m.get("id"), m.get("name"), m.get("provider"), m.get("model_name"), m.get("description"), 1 if m.get("enabled", 1) else 0],
            )
        for c in categories:
            conn.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", [c])
        for k, v in prompts_map.items():
            conn.execute("INSERT OR REPLACE INTO prompts(category,prompt) VALUES(?,?)", [k, v])
        cur = conn.execute("SELECT 1 FROM global_settings WHERE id = 1")
        if cur.fetchone() is None:
            conn.execute(
                "INSERT INTO global_settings(id,common_subject,global_style,negative_prompt) VALUES(1,?,?,?)",
                [common_subject, global_style, negative_prompt],
            )
        else:
            conn.execute(
                "UPDATE global_settings SET common_subject = ?, global_style = ?, negative_prompt = ? WHERE id = 1",
                [common_subject, global_style, negative_prompt],
            )
    print("Seed completed.")

if __name__ == "__main__":
    main()
