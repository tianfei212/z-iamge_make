import sys
import os
import time
import threading
import uuid
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.database import SQLiteConnectionPool, SessionRepository, DatabaseService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

DB_PATH = "sessions_test.db"

def test_crud():
    print("=== Testing CRUD ===")
    pool = SQLiteConnectionPool(DB_PATH, max_connections=2)
    repo = SessionRepository(pool)
    
    # 1. Create
    sid = str(uuid.uuid4())
    print(f"Creating session {sid}")
    repo.insert_session(sid, '{"prompt": "cat"}', "refined cat", '{"seed": 123}')
    
    # 2. Read
    sess = repo.get_session_by_id(sid)
    assert sess is not None
    assert sess["input_params"] == '{"prompt": "cat"}'
    print("Read success")
    
    # 3. Update
    repo.update_session_params(sid, '{"prompt": "dog"}')
    sess = repo.get_session_by_id(sid)
    assert sess["input_params"] == '{"prompt": "dog"}'
    assert sess["version"] == 1
    print("Update params success")
    
    repo.update_image_url(sid, "http://image.com/1.png")
    url = repo.get_image_url(sid)
    assert url == "http://image.com/1.png"
    print("Update URL success")
    
    # 4. Delete
    repo.delete_session(sid, soft=True)
    sess = repo.get_session_by_id(sid) # Should be None because is_deleted=0 filter
    assert sess is None
    print("Soft delete success")
    
    # Check if it's really there
    with pool.acquire() as conn:
        row = conn.execute("SELECT is_deleted FROM sessions WHERE session_id = ?", (sid,)).fetchone()
        assert row["is_deleted"] == 1
    
    pool.close_all()

def test_concurrency():
    print("\n=== Testing Concurrency ===")
    pool = SQLiteConnectionPool(DB_PATH, max_connections=4)
    repo = SessionRepository(pool)
    
    success_count = 0
    lock = threading.Lock()
    
    def worker(i):
        nonlocal success_count
        sid = f"concurrent_{i}"
        try:
            repo.insert_session(sid, "params", "prompt", "random")
            # Simulate some work
            time.sleep(0.01)
            repo.update_session_params(sid, "new_params")
            with lock:
                success_count += 1
        except Exception as e:
            print(f"Worker {i} failed: {e}")

    threads = []
    for i in range(20):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    print(f"Concurrency success: {success_count}/20")
    pool.close_all()

def test_service():
    print("\n=== Testing Service ===")
    pool = SQLiteConnectionPool(DB_PATH, max_connections=1)
    service = DatabaseService(DB_PATH, pool)
    
    stats = service.get_stats()
    print(f"Stats: {stats}")
    
    service.backup("backups_test")
    assert os.path.exists("backups_test")
    print("Backup success")
    
    service.vacuum()
    pool.close_all()

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    if os.path.exists("backups_test"):
        import shutil
        shutil.rmtree("backups_test")
        
    try:
        test_crud()
        test_concurrency()
        test_service()
        print("\nAll tests passed!")
    finally:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        if os.path.exists("backups_test"):
            import shutil
            shutil.rmtree("backups_test")
