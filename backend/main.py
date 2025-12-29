"""
/**
 * @file backend/main.py
 * @description FastAPI 应用入口（MVC：仅装配路由与中间件）。
 */
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import threading
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from backend.config import load_settings, reload_settings, CONFIG_PATH, CONFIG_LOCAL_PATH
from backend.services.background_task_service import start_job_dispatcher
from backend.services.record_service import RecordService
from backend.db.connection import init_db

from backend.controllers import generate_router, health_router, images_router, models_router, translate_router, tasks_router, download_router, db_router, ingest_router

app = FastAPI()
logging.basicConfig(level=logging.DEBUG)

class ConfigEventHandler(FileSystemEventHandler):
    """Handler for config file changes"""
    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Check if relevant files changed
        # Watchdog returns absolute paths usually
        if event.src_path == CONFIG_PATH or event.src_path == CONFIG_LOCAL_PATH:
            try:
                reload_settings()
            except Exception:
                pass

_observer = None

@app.on_event("startup")
async def startup_event():
    global _observer
    try:
        init_db()
    except Exception as e:
        print(f"Failed to init db: {e}")
    # Start job dispatcher in background
    start_job_dispatcher()
    # Start record service
    try:
        RecordService.instance().start()
    except Exception as e:
        print(f"Failed to start record service: {e}")
    # Start Watchdog Observer
    try:
        event_handler = ConfigEventHandler()
        _observer = Observer()
        config_dir = os.path.dirname(CONFIG_PATH)
        _observer.schedule(event_handler, config_dir, recursive=False)
        _observer.start()
        print(f"Config watcher started on {config_dir}")
    except Exception as e:
        print(f"Failed to start config watcher: {e}")
    # Initial load
    load_settings()
    

@app.on_event("shutdown")
async def shutdown_event():
    global _observer
    
    if _observer:
        _observer.stop()
        _observer.join()
    try:
        RecordService.instance().shutdown()
    except Exception as e:
        print(f"Failed to stop record service: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(models_router)
app.include_router(translate_router)
app.include_router(generate_router)
app.include_router(images_router)
app.include_router(tasks_router)
app.include_router(download_router)
app.include_router(db_router)
app.include_router(ingest_router)
from backend.controllers import categories_router, prompts_router, config_router
app.include_router(categories_router)
app.include_router(prompts_router)
app.include_router(config_router)
