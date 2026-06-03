"""
状态管理核心模块

提供 StateManager 类，管理智能体的任务状态和会话状态。
完全兼容现有 ASUAgentMemory 接口，并扩展更多功能。
"""

import time
import uuid
import sqlite3
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import threading
from datetime import datetime


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"           # 等待执行
    IN_PROGRESS = "in_progress"   # 执行中
    PAUSED = "paused"             # 已暂停
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 已取消


@dataclass
class TaskState:
    """任务状态数据类"""
    task_id: str
    session_id: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    task_type: str = "default"
    description: str = ""
    progress: float = 0.0  # 0.0 - 1.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    checkpoint_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["status"] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskState":
        """从字典创建"""
        data = data.copy()
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TaskStatus(data["status"])
        return cls(**data)


@dataclass
class SessionState:
    """会话状态数据类"""
    session_id: str
    persona: str = "default"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    is_active: bool = True
    task_count: int = 0
    completed_task_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """从字典创建"""
        return cls(**data)


class StateManager:
    """
    状态管理器 - 乐高积木模块
    
    功能：
    1. 管理会话状态（兼容 ASUAgentMemory）
    2. 管理任务状态（新增）
    3. 提供检查点机制（新增）
    4. 支持状态持久化（增强）
    5. 支持状态查询和统计（新增）
    
    完全兼容现有 ASUAgentMemory 接口：
    - get_context(session_id)
    - add_message(session_id, role, content)
    - set_persona(session_id, persona)
    - clear(session_id)
    - session_count()
    """
    
    def __init__(self, db_path: str = "asu_agent.db", auto_checkpoint: bool = True):
        """
        初始化状态管理器
        
        Args:
            db_path: 数据库路径
            auto_checkpoint: 是否自动创建检查点
        """
        self.db_path = db_path
        self.auto_checkpoint = auto_checkpoint
        self._lock = threading.Lock()
        
        # 初始化数据库
        self._init_db()
        
        # 缓存（线程安全）
        self._session_cache: Dict[str, SessionState] = {}
        self._task_cache: Dict[str, TaskState] = {}
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    @staticmethod
    def _migrate_sessions_table(cursor):
        """迁移 sessions 表，添加新列"""
        cols = {"created_at": "REAL", "is_active": "INTEGER DEFAULT 1", "metadata": "TEXT DEFAULT '{}'"}
        existing = {row[1] for row in cursor.execute("PRAGMA table_info(sessions)").fetchall()}
        for col_name, col_type in cols.items():
            if col_name not in existing:
                try:
                    cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 会话表（兼容现有）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    persona TEXT DEFAULT 'default',
                    updated_at REAL
                )
            ''')
            
            # 迁移: 添加旧表缺少的列
            self._migrate_sessions_table(cursor)
            
            # 消息表（兼容现有）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            ''')
            
            # 任务表（新增）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    status TEXT DEFAULT 'pending',
                    task_type TEXT DEFAULT 'default',
                    description TEXT DEFAULT '',
                    progress REAL DEFAULT 0.0,
                    result TEXT,
                    error TEXT,
                    metadata TEXT DEFAULT '{}',
                    checkpoint_id TEXT,
                    created_at REAL,
                    updated_at REAL,
                    completed_at REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            ''')
            
            # 检查点表（新增）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    task_id TEXT,
                    session_id TEXT,
                    state_snapshot TEXT,
                    created_at REAL,
                    description TEXT DEFAULT '',
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id),
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            ''')
            
            # 索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_session ON tasks(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_checkpoints_task ON checkpoints(task_id)')
            
            conn.commit()
    
    # ==========================================
    # 兼容 ASUAgentMemory 接口
    # ==========================================
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话上下文（兼容 ASUAgentMemory）
        
        Args:
            session_id: 会话ID
            
        Returns:
            包含 messages 和 persona 的字典
        """
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # 获取或创建会话
                cursor.execute("SELECT persona FROM sessions WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                
                if row:
                    persona = row[0]
                else:
                    persona = "default"
                    cursor.execute(
                        "INSERT INTO sessions (session_id, persona, updated_at, created_at) VALUES (?, ?, ?, ?)",
                        (session_id, persona, time.time(), time.time())
                    )
                    conn.commit()
                
                # 获取消息历史
                cursor.execute(
                    "SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
                    (session_id,)
                )
                messages = [{"role": r[0], "content": r[1]} for r in cursor.fetchall()]
                
                return {"messages": messages, "persona": persona}
    
    def add_message(self, session_id: str, role: str, content: str):
        """
        添加消息（兼容 ASUAgentMemory）
        
        Args:
            session_id: 会话ID
            role: 角色（user/assistant/system）
            content: 消息内容
        """
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # 确保会话存在
                cursor.execute(
                    "INSERT OR IGNORE INTO sessions (session_id, persona, updated_at, created_at) VALUES (?, 'default', ?, ?)",
                    (session_id, time.time(), time.time())
                )
                
                # 添加消息
                cursor.execute(
                    "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    (session_id, role, content, time.time())
                )
                
                # 更新会话时间
                cursor.execute(
                    "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                    (time.time(), session_id)
                )
                
                conn.commit()
    
    def set_persona(self, session_id: str, persona: str):
        """
        设置人设（兼容 ASUAgentMemory）
        
        Args:
            session_id: 会话ID
            persona: 人设类型
        """
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # 检查会话是否存在
                cursor.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
                if cursor.fetchone():
                    cursor.execute(
                        "UPDATE sessions SET persona = ?, updated_at = ? WHERE session_id = ?",
                        (persona, time.time(), session_id)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO sessions (session_id, persona, updated_at, created_at) VALUES (?, ?, ?, ?)",
                        (session_id, persona, time.time(), time.time())
                    )
                
                conn.commit()
                
                # 更新缓存
                if session_id in self._session_cache:
                    self._session_cache[session_id].persona = persona
                    self._session_cache[session_id].updated_at = time.time()
    
    def clear(self, session_id: str):
        """
        清空会话（兼容 ASUAgentMemory）
        
        Args:
            session_id: 会话ID
        """
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # 删除消息
                cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
                
                # 重置会话
                cursor.execute(
                    "UPDATE sessions SET persona = 'default', updated_at = ? WHERE session_id = ?",
                    (time.time(), session_id)
                )
                
                conn.commit()
                
                # 清除缓存
                if session_id in self._session_cache:
                    del self._session_cache[session_id]
    
    def session_count(self) -> int:
        """
        获取会话数量（兼容 ASUAgentMemory）
        
        Returns:
            会话数量
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sessions")
            row = cursor.fetchone()
            return row[0] if row else 0
    
    # ==========================================
    # 新增：任务状态管理
    # ==========================================
    
    def create_task(
        self,
        session_id: str,
        task_type: str = "default",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> TaskState:
        """
        创建新任务
        
        Args:
            session_id: 会话ID
            task_type: 任务类型
            description: 任务描述
            metadata: 额外元数据
            
        Returns:
            创建的任务状态
        """
        task_id = str(uuid.uuid4())
        now = time.time()
        
        task = TaskState(
            task_id=task_id,
            session_id=session_id,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            task_type=task_type,
            description=description,
            metadata=metadata or {}
        )
        
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tasks (
                        task_id, session_id, status, task_type, description,
                        progress, metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_id, session_id, task.status.value, task_type, description,
                    0.0, json.dumps(metadata or {}), now, now
                ))
                
                # 更新会话任务计数
                cursor.execute(
                    "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                    (now, session_id)
                )
                
                conn.commit()
            
            # 缓存任务
            self._task_cache[task_id] = task
        
        return task
    
    def get_task(self, task_id: str) -> Optional[TaskState]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态，不存在返回 None
        """
        # 先查缓存
        if task_id in self._task_cache:
            return self._task_cache[task_id]
        
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_id, session_id, status, task_type, description,
                       progress, result, error, metadata, checkpoint_id,
                       created_at, updated_at, completed_at
                FROM tasks WHERE task_id = ?
            ''', (task_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            task = TaskState(
                task_id=row[0],
                session_id=row[1],
                status=TaskStatus(row[2]),
                task_type=row[3],
                description=row[4],
                progress=row[5],
                result=json.loads(row[6]) if row[6] else None,
                error=row[7],
                metadata=json.loads(row[8]) if row[8] else {},
                checkpoint_id=row[9],
                created_at=row[10],
                updated_at=row[11],
                completed_at=row[12]
            )
            
            # 缓存
            self._task_cache[task_id] = task
            return task
    
    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[float] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[TaskState]:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            progress: 新进度
            result: 任务结果
            error: 错误信息
            metadata: 额外元数据
            
        Returns:
            更新后的任务状态
        """
        with self._lock:
            task = self.get_task(task_id)
            if not task:
                return None
            
            # 更新字段
            if status is not None:
                task.status = status
                if status == TaskStatus.COMPLETED:
                    task.completed_at = time.time()
                    task.progress = 1.0
            
            if progress is not None:
                task.progress = max(0.0, min(1.0, progress))
            
            if result is not None:
                task.result = result
            
            if error is not None:
                task.error = error
                if error:
                    task.status = TaskStatus.FAILED
            
            if metadata is not None:
                task.metadata.update(metadata)
            
            task.updated_at = time.time()
            
            # 持久化
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE tasks SET
                        status = ?, progress = ?, result = ?, error = ?,
                        metadata = ?, updated_at = ?, completed_at = ?,
                        checkpoint_id = ?
                    WHERE task_id = ?
                ''', (
                    task.status.value,
                    task.progress,
                    json.dumps(task.result) if task.result else None,
                    task.error,
                    json.dumps(task.metadata),
                    task.updated_at,
                    task.completed_at,
                    task.checkpoint_id,
                    task_id
                ))
                conn.commit()
            
            # 更新缓存
            self._task_cache[task_id] = task
            
            # 自动创建检查点
            if self.auto_checkpoint and status in [TaskStatus.IN_PROGRESS, TaskStatus.PAUSED]:
                self._auto_checkpoint(task)
            
            return task
    
    def get_session_tasks(
        self,
        session_id: str,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[TaskState]:
        """
        获取会话的任务列表
        
        Args:
            session_id: 会话ID
            status: 过滤状态
            limit: 返回数量限制
            
        Returns:
            任务列表
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            if status:
                cursor.execute('''
                    SELECT task_id FROM tasks
                    WHERE session_id = ? AND status = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                ''', (session_id, status.value, limit))
            else:
                cursor.execute('''
                    SELECT task_id FROM tasks
                    WHERE session_id = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                ''', (session_id, limit))
            
            task_ids = [row[0] for row in cursor.fetchall()]
            return [self.get_task(tid) for tid in task_ids if self.get_task(tid)]
    
    def get_active_tasks(self, session_id: str) -> List[TaskState]:
        """
        获取会话的活跃任务（进行中或暂停）
        
        Args:
            session_id: 会话ID
            
        Returns:
            活跃任务列表
        """
        active_statuses = [TaskStatus.IN_PROGRESS, TaskStatus.PAUSED]
        all_tasks = self.get_session_tasks(session_id)
        return [t for t in all_tasks if t.status in active_statuses]
    
    # ==========================================
    # 新增：会话状态管理
    # ==========================================
    
    def get_session_state(self, session_id: str) -> SessionState:
        """
        获取会话状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话状态
        """
        # 先查缓存
        if session_id in self._session_cache:
            return self._session_cache[session_id]
        
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_id, persona, created_at, updated_at, is_active, metadata
                FROM sessions WHERE session_id = ?
            ''', (session_id,))
            
            row = cursor.fetchone()
            if not row:
                # 创建新会话
                now = time.time()
                state = SessionState(
                    session_id=session_id,
                    persona="default",
                    created_at=now,
                    updated_at=now,
                    is_active=True,
                    metadata={}
                )
                
                cursor.execute('''
                    INSERT INTO sessions (session_id, persona, created_at, updated_at, is_active, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (session_id, "default", now, now, 1, "{}"))
                conn.commit()
            else:
                state = SessionState(
                    session_id=row[0],
                    persona=row[1],
                    created_at=row[2],
                    updated_at=row[3],
                    is_active=bool(row[4]),
                    metadata=json.loads(row[5]) if row[5] else {}
                )
                
                # 计算任务统计
                cursor.execute('''
                    SELECT COUNT(*) FROM tasks WHERE session_id = ?
                ''', (session_id,))
                state.task_count = cursor.fetchone()[0]
                
                cursor.execute('''
                    SELECT COUNT(*) FROM tasks WHERE session_id = ? AND status = 'completed'
                ''', (session_id,))
                state.completed_task_count = cursor.fetchone()[0]
            
            # 缓存
            self._session_cache[session_id] = state
            return state
    
    def update_session_state(
        self,
        session_id: str,
        persona: Optional[str] = None,
        is_active: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionState:
        """
        更新会话状态
        
        Args:
            session_id: 会话ID
            persona: 人设
            is_active: 是否活跃
            metadata: 额外元数据
            
        Returns:
            更新后的会话状态
        """
        state = self.get_session_state(session_id)
        
        if persona is not None:
            state.persona = persona
        
        if is_active is not None:
            state.is_active = is_active
        
        if metadata is not None:
            state.metadata.update(metadata)
        
        state.updated_at = time.time()
        
        # 持久化
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sessions SET
                        persona = ?, updated_at = ?, is_active = ?, metadata = ?
                    WHERE session_id = ?
                ''', (
                    state.persona,
                    state.updated_at,
                    1 if state.is_active else 0,
                    json.dumps(state.metadata),
                    session_id
                ))
                conn.commit()
        
        # 更新缓存
        self._session_cache[session_id] = state
        return state
    
    # ==========================================
    # 内部方法
    # ==========================================
    
    def _auto_checkpoint(self, task: TaskState):
        """自动创建检查点"""
        # 这里只是占位，实际实现在 checkpoint.py
        pass
    
    # ==========================================
    # 统计和查询
    # ==========================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取状态管理统计信息
        
        Returns:
            统计信息字典
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            stats = {
                "total_sessions": 0,
                "active_sessions": 0,
                "total_tasks": 0,
                "tasks_by_status": {},
                "total_messages": 0,
            }
            
            # 会话统计
            cursor.execute("SELECT COUNT(*) FROM sessions")
            stats["total_sessions"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE is_active = 1")
            stats["active_sessions"] = cursor.fetchone()[0]
            
            # 任务统计
            cursor.execute("SELECT COUNT(*) FROM tasks")
            stats["total_tasks"] = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT status, COUNT(*) FROM tasks GROUP BY status
            ''')
            for row in cursor.fetchall():
                stats["tasks_by_status"][row[0]] = row[1]
            
            # 消息统计
            cursor.execute("SELECT COUNT(*) FROM messages")
            stats["total_messages"] = cursor.fetchone()[0]
            
            return stats
    
    def clear_all(self):
        """清空所有数据（危险操作）"""
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM messages")
                cursor.execute("DELETE FROM checkpoints")
                cursor.execute("DELETE FROM tasks")
                cursor.execute("DELETE FROM sessions")
                conn.commit()
            
            # 清空缓存
            self._session_cache.clear()
            self._task_cache.clear()


# 兼容性别名
ASUAgentMemory = StateManager
