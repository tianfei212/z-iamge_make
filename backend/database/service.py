import os
import shutil
import logging
import sqlite3
import threading
import time
from typing import Optional

logger = logging.getLogger("database.service")

class DatabaseService:
    def __init__(self, db_path: str, pool):
        self.db_path = db_path
        self.pool = pool
        self._monitor_thread = None
        self._stop_event = threading.Event()

    def start_monitoring(self):
        """Start the background monitoring thread."""
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Database monitoring started")

    def stop_monitoring(self):
        """Stop the background monitoring thread."""
        if self._monitor_thread:
            self._stop_event.set()
            self._monitor_thread.join()
            logger.info("Database monitoring stopped")

    def _monitor_loop(self):
        """Background loop for monitoring DB size and maintenance."""
        while not self._stop_event.is_set():
            try:
                self._check_db_size()
                # Run vacuum every 24 hours (simplified logic here, check timestamp in real app)
                # Here we just sleep for 1 hour interval checks
                time.sleep(3600) 
            except Exception as e:
                logger.error(f"Error in database monitor: {e}")

    def _check_db_size(self):
        try:
            size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
            if size_mb > 2000:
                logger.warning(f"Database file size is large: {size_mb:.2f} MB")
            
            # If size is huge, maybe trigger vacuum?
            # For now just log.
        except OSError:
            pass

    def vacuum(self):
        """Run VACUUM command to optimize database."""
        try:
            logger.info("Starting VACUUM...")
            with self.pool.acquire() as conn:
                conn.execute("VACUUM;")
            logger.info("VACUUM completed")
        except Exception as e:
            logger.error(f"VACUUM failed: {e}")

    def backup(self, backup_dir: str):
        """Create a backup of the database."""
        try:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"sessions_{timestamp}.db")
            
            # Using SQLite backup API is better than file copy while DB is open
            with self.pool.acquire() as conn:
                dest_conn = sqlite3.connect(backup_path)
                conn.backup(dest_conn)
                dest_conn.close()
            
            logger.info(f"Database backup created at {backup_path}")
        except Exception as e:
            logger.error(f"Backup failed: {e}")

    def get_stats(self):
        """Get database statistics (Prometheus format style dict)."""
        stats = {
            "db_size_bytes": 0,
            "connection_pool_size": self.pool._pool.qsize(),
            "created_connections": self.pool._created_connections
        }
        try:
            stats["db_size_bytes"] = os.path.getsize(self.db_path)
        except OSError:
            pass
        return stats
