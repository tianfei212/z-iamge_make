from backend.db.connection import get_conn

def main():
    with get_conn() as conn:
        rows = conn.execute('SELECT id,name,provider,model_name,enabled FROM models').fetchall()
        cats = conn.execute('SELECT name FROM categories').fetchall()
        prompts = conn.execute('SELECT category,prompt FROM prompts').fetchall()
        g = conn.execute('SELECT common_subject,global_style,negative_prompt FROM global_settings WHERE id=1').fetchone()
    print("models:", rows)
    print("categories:", cats)
    print("prompts count:", len(prompts))
    print("global:", g)

if __name__ == "__main__":
    main()
