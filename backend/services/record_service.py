from __future__ import annotations

import os
import json
import time
import gzip
import threading
import queue
import logging
import datetime
from typing import Dict, Any, List, Optional

from backend.models.record_models import RecordEntry, GeneratedItem
from backend.config import load_settings


logger = logging.getLogger("record_service")
perf_logger = logging.getLogger("record_perf")
arch_logger = logging.getLogger("record_archiver")


RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
ARCHIVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "archive")


def _utc_day_str(ts: Optional[float] = None) -> str:
    dt = datetime.datetime.utcfromtimestamp(ts or time.time())
    return dt.strftime("%Y-%m-%d")


def _ensure_dirs():
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)


class JSONFileStorageBackend:
    def __init__(self) -> None:
        _ensure_dirs()
        self._lock = threading.Lock()
        self._current_day = _utc_day_str()
        self._current_path = os.path.join(RAW_DIR, f"{self._current_day}.json")
        self._current_hash_path = self._current_path + ".sha256"
        # Ensure files exist
        open(self._current_path, "a").close()
        open(self._current_hash_path, "a").close()

    def _rotate_if_needed(self) -> None:
        day = _utc_day_str()
        if day != self._current_day:
            self._current_day = day
            self._current_path = os.path.join(RAW_DIR, f"{day}.json")
            self._current_hash_path = self._current_path + ".sha256"
            open(self._current_path, "a").close()
            open(self._current_hash_path, "a").close()
            logger.info(f"Rotated raw file to {self._current_path}")

    def append_line(self, line: str) -> None:
        import fcntl
        self._rotate_if_needed()
        with self._lock:
            with open(self._current_path, "a") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            # write sha256
            import hashlib
            digest = hashlib.sha256(line.encode("utf-8")).hexdigest()
            with open(self._current_hash_path, "a") as hf:
                hf.write(digest + "\n")

    def verify_day(self, day: str) -> Dict[str, Any]:
        path = os.path.join(RAW_DIR, f"{day}.json")
        hpath = path + ".sha256"
        if not os.path.exists(path) or not os.path.exists(hpath):
            return {"day": day, "exists": False}
        import hashlib
        ok = 0
        bad = 0
        with open(path, "r") as f, open(hpath, "r") as hf:
            for line, hd in zip(f, hf):
                digest = hashlib.sha256(line.encode("utf-8")).hexdigest()
                if digest.strip() == hd.strip():
                    ok += 1
                else:
                    bad += 1
        return {"day": day, "exists": True, "ok": ok, "bad": bad}


class RecordService:
    _instance = None
    _started = False

    def __init__(self) -> None:
        self._queue: "queue.Queue[str]" = queue.Queue(maxsize=10_000)
        self._backend = JSONFileStorageBackend()
        self._writer_thread: Optional[threading.Thread] = None
        self._archiver_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @classmethod
    def instance(cls) -> "RecordService":
        if cls._instance is None:
            cls._instance = RecordService()
        return cls._instance

    def start(self) -> None:
        if self._started:
            return
        self._stop_event.clear()
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self._archiver_thread = threading.Thread(target=self._archiver_loop, daemon=True)
        self._writer_thread.start()
        self._archiver_thread.start()
        self._started = True
        logger.info("RecordService started.")

    def shutdown(self) -> None:
        if not self._started:
            return
        logger.info("RecordService shutting down...")
        self._stop_event.set()
        if self._writer_thread:
            self._writer_thread.join(timeout=5)
        if self._archiver_thread:
            self._archiver_thread.join(timeout=5)
        self._started = False
        logger.info("RecordService stopped.")

    def add_record(self, job_meta: Dict[str, Any], items: List[Dict[str, Any]]) -> None:
        try:
            entry = RecordEntry(
                **{
                    "用户ID": job_meta.get("user_id"),
                    "SessionID": job_meta.get("session_id"),
                    "创建时间": job_meta.get("created_at"),
                    "通用基础提示词": job_meta.get("prompt"),
                    "分类描述提示词": job_meta.get("category"),
                    "优化后正向提示词": job_meta.get("refined_positive"),
                    "优化后反向提示词": job_meta.get("refined_negative", ""),
                    "比例": job_meta.get("aspect_ratio", "16:9"),
                    "画质": job_meta.get("resolution", "1K"),
                    "数量": job_meta.get("count", 1),
                    "模型名称": job_meta.get("model") or "",
                    "生成记录": [GeneratedItem(**{
                        "随机种子": str(it.get("seed")),
                        "热度值": float(it.get("temperature")),
                        "top值": float(it.get("top_p")),
                        "相对url路径": str(it.get("relative_url")),
                        "存储绝对路径": str(it.get("absolute_path")),
                    }).dict(by_alias=True) for it in items],
                }
            )
            line = json.dumps(entry.dict(by_alias=True), ensure_ascii=False) + "\n"
            self._queue.put(line, block=True, timeout=5)
        except Exception as e:
            logger.error(f"add_record failed: {e}")

    def _writer_loop(self) -> None:
        batch: List[str] = []
        last_flush = time.time()
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.2)
                batch.append(item)
            except queue.Empty:
                pass
            now = time.time()
            if batch and (len(batch) >= 100 or (now - last_flush) >= 0.5):
                start = time.time()
                try:
                    for line in batch:
                        self._backend.append_line(line)
                    perf_logger.info(f"flushed batch size={len(batch)} time_ms={int((time.time()-start)*1000)} qsize={self._queue.qsize()}")
                except Exception as e:
                    logger.error(f"writer flush failed: {e}")
                finally:
                    batch.clear()
                    last_flush = now
        # drain remaining
        if batch:
            for line in batch:
                try:
                    self._backend.append_line(line)
                except Exception as e:
                    logger.error(f"final flush failed: {e}")

    def _archiver_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                # 每小时检查一次；仅在 02:00 触发归档
                time.sleep(3600)
                utc_hour = datetime.datetime.utcnow().hour
                if utc_hour != 2:
                    continue
                self._archive_older_days()
            except Exception as e:
                arch_logger.error(f"archiver loop error: {e}")

    def _archive_older_days(self) -> None:
        try:
            files = [f for f in os.listdir(RAW_DIR) if f.endswith(".json")]
            today = _utc_day_str()
            for fname in files:
                day = fname.replace(".json", "")
                if day == today:
                    continue
                src = os.path.join(RAW_DIR, fname)
                sha_src = src + ".sha256"
                dst = os.path.join(ARCHIVE_DIR, fname + ".gz")
                if os.path.exists(dst):
                    continue
                with open(src, "rb") as fin, gzip.open(dst, "wb") as gout:
                    gout.write(fin.read())
                arch_logger.info(f"archived {src} -> {dst}")
                # 移动 sha256
                if os.path.exists(sha_src):
                    os.replace(sha_src, os.path.join(ARCHIVE_DIR, os.path.basename(sha_src)))
                # 移动原文件
                os.replace(src, os.path.join(ARCHIVE_DIR, fname))
        except Exception as e:
            arch_logger.error(f"archive failed: {e}")

    def verify(self, day: str) -> Dict[str, Any]:
        return self._backend.verify_day(day)

