"""
SQLite 管线日志存储 —— 大宽表设计，按 session_id 追踪全链路。

解决文本日志丢数据、难查询的问题：
- WAL 模式支持并发读写
- 线程安全（锁保护）
- 一行一个事件快照，字段齐全
- 按 session_id / app_run_id / event 快速检索

用法:
    from opencopilot.agent.log_store import LogStore

    store = LogStore.get_instance()
    store.insert(session_id="abc", event="START", source="Caller",
                 message="Agent pipeline started", caller_id=1)
"""

import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any


DB_DIR = str(Path(__file__).resolve().parent.parent)


class LogStore:
    """SQLite 管线日志单例"""

    _instance: Optional["LogStore"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._db_path = os.path.join(DB_DIR, "pipeline_logs.db")
        self._write_lock = threading.Lock()
        self._app_run_id = ""
        self._initialized = False
        self._init_db()

    @classmethod
    def get_instance(cls) -> "LogStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- 公共 API ----

    @property
    def app_run_id(self) -> str:
        return self._app_run_id

    def init_run(self, run_id: str = ""):
        """记录本次启动标识（main.py 启动时调用）"""
        self._app_run_id = run_id or str(uuid.uuid4())
        self.insert(
            session_id="",
            event="APP_START",
            source="MAIN",
            level="INFO",
            message=f"Application started | app_run_id={self._app_run_id}",
        )

    def insert(
        self,
        *,
        session_id: str = "",
        caller_id: Optional[int] = None,
        worker_id: Optional[int] = None,
        worker_type: str = "",
        event: str = "LOG",
        level: str = "INFO",
        source: str = "",
        thread_id: Optional[int] = None,
        message: str = "",
        chunk_count: Optional[int] = None,
        elapsed_ms: Optional[float] = None,
        data_json: str = "",
    ):
        """插入一条日志（线程安全）"""
        row = (
            time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(time.time() * 1000) % 1000:03d}",
            session_id,
            caller_id or 0,
            worker_id or 0,
            worker_type,
            event,
            level,
            source,
            thread_id or threading.current_thread().ident or 0,
            message,
            chunk_count or 0,
            elapsed_ms or 0.0,
            data_json,
            self._app_run_id,
        )
        try:
            with self._write_lock:
                self._conn.execute(
                    """INSERT INTO pipeline_logs
                       (timestamp, session_id, caller_id, worker_id, worker_type,
                        event, level, source, thread_id, message,
                        chunk_count, elapsed_ms, data_json, app_run_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    row,
                )
                self._conn.commit()
        except Exception:
            # 日志写入失败不应该影响主流程，fallback 到 stderr
            import sys
            import traceback
            print(f"[LogStore ERROR] message={message}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()

    def query(self, sql: str, params: tuple = ()) -> list:
        """执行查询并返回结果（调试用）"""
        try:
            cur = self._conn.execute(sql, params)
            return cur.fetchall()
        except Exception:
            return []

    # ---- 内部 ----

    def _init_db(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=-8000")  # 8MB cache
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_logs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp     TEXT NOT NULL,
                session_id    TEXT DEFAULT '',
                caller_id     INTEGER DEFAULT 0,
                worker_id     INTEGER DEFAULT 0,
                worker_type   TEXT DEFAULT '',
                event         TEXT NOT NULL,
                level         TEXT DEFAULT 'INFO',
                source        TEXT DEFAULT '',
                thread_id     INTEGER DEFAULT 0,
                message       TEXT DEFAULT '',
                chunk_count   INTEGER DEFAULT 0,
                elapsed_ms    REAL DEFAULT 0.0,
                data_json     TEXT DEFAULT '',
                app_run_id    TEXT DEFAULT '',
                created_at    TEXT DEFAULT (datetime('now'))
            )
        """)
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON pipeline_logs(session_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_event ON pipeline_logs(event)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_run ON pipeline_logs(app_run_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON pipeline_logs(source)")
        self._conn.commit()
        self._initialized = True
