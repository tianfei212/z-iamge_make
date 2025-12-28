import sys
import os
sys.path.append(os.getcwd())

from backend.config import load_settings
from backend.database import SQLiteConnectionPool, SessionRepository

def test_init():
    settings = load_settings()
    db_path = settings.database_path
    print(f"DB Path: {db_path}")
    
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        print(f"Creating dir: {db_dir}")
        os.makedirs(db_dir)
        
    pool = SQLiteConnectionPool(db_path)
    repo = SessionRepository(pool)
    print("DB initialized successfully")

if __name__ == "__main__":
    test_init()