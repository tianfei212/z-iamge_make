import os
import sys
import sqlite3
from backend.db.connection import DB_PATH

def main():
    conn = sqlite3.connect(DB_PATH)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(records)").fetchall()]
    print("records columns:", cols)
    conn.close()

if __name__ == "__main__":
    main()
