import sqlite3
import queue
import threading
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger("database.pool")

class SQLiteConnectionPool:
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool = queue.Queue(maxsize=max_connections)
        self._created_connections = 0
        self._lock = threading.Lock()
        
    def _create_connection(self):
        """Create a new SQLite connection."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def get_connection(self, timeout: float = 5.0) -> sqlite3.Connection:
        """Get a connection from the pool."""
        try:
            return self._pool.get(block=False)
        except queue.Empty:
            with self._lock:
                if self._created_connections < self.max_connections:
                    self._created_connections += 1
                    try:
                        return self._create_connection()
                    except Exception as e:
                        self._created_connections -= 1
                        raise e
            
            # If we reached max connections, wait for one to be returned
            try:
                return self._pool.get(block=True, timeout=timeout)
            except queue.Empty:
                raise TimeoutError("Timeout waiting for database connection")

    def return_connection(self, conn: sqlite3.Connection):
        """Return a connection to the pool."""
        try:
            # Check if connection is alive? SQLite connections usually don't die unless closed.
            # We could do a quick check, but it might be overhead.
            self._pool.put(conn, block=False)
        except queue.Full:
            # Should not happen if logic is correct
            conn.close()
            with self._lock:
                self._created_connections -= 1
            logger.warning("Connection pool overflow, closed extra connection")

    def close_all(self):
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get(block=False)
                conn.close()
            except queue.Empty:
                break
        with self._lock:
            self._created_connections = 0

    @contextmanager
    def acquire(self):
        """Context manager for acquiring a connection."""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.return_connection(conn)
