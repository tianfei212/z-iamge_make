import sys
import os
import threading
import time
sys.path.append(os.getcwd())

print("Step 1: Importing modules...")
from backend.config import load_settings
from backend.database import SQLiteConnectionPool, SessionRepository, DatabaseService
from backend.services.background_task_service import start_job_dispatcher, set_db_repo
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

print("Step 2: Loading settings...")
settings = load_settings()
print(f"Settings loaded. DB Path: {settings.database_path}")

print("Step 3: Initializing Database...")
try:
    db_path = settings.database_path
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    db_pool = SQLiteConnectionPool(db_path)
    db_repo = SessionRepository(db_pool)
    db_service = DatabaseService(db_path, db_pool)
    db_service.start_monitoring()
    set_db_repo(db_repo)
    print("Database initialized.")
except Exception as e:
    print(f"Database init failed: {e}")

print("Step 4: Starting Job Dispatcher...")
start_job_dispatcher()
print("Job Dispatcher started.")

print("Step 5: Starting Watchdog...")
class ConfigEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        print(f"File modified: {event.src_path}")

try:
    event_handler = ConfigEventHandler()
    observer = Observer()
    config_dir = os.path.dirname(os.path.abspath("backend/config.json"))
    observer.schedule(event_handler, config_dir, recursive=False)
    observer.start()
    print("Watchdog started.")
except Exception as e:
    print(f"Watchdog failed: {e}")

print("Startup simulation complete.")
observer.stop()
observer.join()
