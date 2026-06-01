"""
状态持久化模块

提供多种持久化策略：
- SQLiteStateStorage: SQLite 存储（默认）
- FileStateStorage: 文件系统存储
- StatePersistence: 统一持久化接口
"""

import json
import os
import time
import sqlite3
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pathlib import Path
import threading


class StateStorage(ABC):
    """状态存储抽象基类"""
    
    @abstractmethod
    def save_state(self, key: str, state: Dict[str, Any]) -> bool:
        """保存状态"""
        pass
    
    @abstractmethod
    def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        """加载状态"""
        pass
    
    @abstractmethod
    def delete_state(self, key: str) -> bool:
        """删除状态"""
        pass
    
    @abstractmethod
    def list_states(self, prefix: str = "") -> List[str]:
        """列出所有状态键"""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查状态是否存在"""
        pass


class SQLiteStateStorage(StateStorage):
    """
    SQLite 状态存储
    
    优点：
    - 支持并发访问
    - 事务支持
    - 查询能力强
    
    缺点：
    - 需要数据库文件
    """
    
    def __init__(self, db_path: str = "state_storage.db"):
        """
        初始化 SQLite 存储
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS states (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_states_key ON states(key)')
            conn.commit()
    
    def save_state(self, key: str, state: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """保存状态"""
        try:
            now = time.time()
            value_json = json.dumps(state, ensure_ascii=False)
            meta_json = json.dumps(metadata or {}, ensure_ascii=False)
            
            with self._lock:
                with self._get_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO states (key, value, created_at, updated_at, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (key, value_json, now, now, meta_json))
                    conn.commit()
            
            return True
        except Exception as e:
            print(f"保存状态失败: {e}")
            return False
    
    def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        """加载状态"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM states WHERE key = ?", (key,))
                row = cursor.fetchone()
                
                if row:
                    return json.loads(row[0])
                return None
        except Exception as e:
            print(f"加载状态失败: {e}")
            return None
    
    def delete_state(self, key: str) -> bool:
        """删除状态"""
        try:
            with self._lock:
                with self._get_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM states WHERE key = ?", (key,))
                    conn.commit()
            return True
        except Exception as e:
            print(f"删除状态失败: {e}")
            return False
    
    def list_states(self, prefix: str = "") -> List[str]:
        """列出所有状态键"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                if prefix:
                    cursor.execute("SELECT key FROM states WHERE key LIKE ?", (f"{prefix}%",))
                else:
                    cursor.execute("SELECT key FROM states")
                
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"列出状态失败: {e}")
            return []
    
    def exists(self, key: str) -> bool:
        """检查状态是否存在"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM states WHERE key = ?", (key,))
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"检查状态失败: {e}")
            return False
    
    def save_with_ttl(self, key: str, state: Dict[str, Any], ttl_seconds: int) -> bool:
        """保存带过期时间的状态"""
        metadata = {"ttl": ttl_seconds, "expires_at": time.time() + ttl_seconds}
        return self.save_state(key, state, metadata)
    
    def cleanup_expired(self) -> int:
        """清理过期状态"""
        try:
            now = time.time()
            count = 0
            
            with self._lock:
                with self._get_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT key, metadata FROM states
                        WHERE metadata LIKE '%expires_at%'
                    ''')
                    
                    expired_keys = []
                    for row in cursor.fetchall():
                        try:
                            meta = json.loads(row[1])
                            if meta.get("expires_at", float("inf")) < now:
                                expired_keys.append(row[0])
                        except:
                            pass
                    
                    for key in expired_keys:
                        cursor.execute("DELETE FROM states WHERE key = ?", (key,))
                        count += 1
                    
                    conn.commit()
            
            return count
        except Exception as e:
            print(f"清理过期状态失败: {e}")
            return 0


class FileStateStorage(StateStorage):
    """
    文件系统状态存储
    
    优点：
    - 简单直观
    - 易于调试
    - 可直接查看文件
    
    缺点：
    - 并发支持差
    - 性能较低
    """
    
    def __init__(self, base_dir: str = "state_storage"):
        """
        初始化文件存储
        
        Args:
            base_dir: 存储目录
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
    
    def _get_file_path(self, key: str) -> Path:
        """获取状态文件路径"""
        # 将 key 转换为安全的文件名
        safe_key = key.replace("/", "_").replace("\\", "_").replace(":", "_")
        return self.base_dir / f"{safe_key}.json"
    
    def save_state(self, key: str, state: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> bool:
        """保存状态"""
        try:
            file_path = self._get_file_path(key)
            
            data = {
                "key": key,
                "value": state,
                "metadata": metadata or {},
                "created_at": time.time(),
                "updated_at": time.time()
            }
            
            # 如果文件已存在，保留创建时间
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        old_data = json.load(f)
                        data["created_at"] = old_data.get("created_at", time.time())
                except:
                    pass
            
            with self._lock:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存状态失败: {e}")
            return False
    
    def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        """加载状态"""
        try:
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                return None
            
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("value")
        except Exception as e:
            print(f"加载状态失败: {e}")
            return None
    
    def delete_state(self, key: str) -> bool:
        """删除状态"""
        try:
            file_path = self._get_file_path(key)
            
            if file_path.exists():
                with self._lock:
                    file_path.unlink()
            
            return True
        except Exception as e:
            print(f"删除状态失败: {e}")
            return False
    
    def list_states(self, prefix: str = "") -> List[str]:
        """列出所有状态键"""
        try:
            keys = []
            
            for file_path in self.base_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        key = data.get("key", "")
                        if key and (not prefix or key.startswith(prefix)):
                            keys.append(key)
                except:
                    continue
            
            return keys
        except Exception as e:
            print(f"列出状态失败: {e}")
            return []
    
    def exists(self, key: str) -> bool:
        """检查状态是否存在"""
        file_path = self._get_file_path(key)
        return file_path.exists()


class StatePersistence:
    """
    状态持久化管理器
    
    提供统一的持久化接口，支持多种存储后端
    """
    
    def __init__(self, storage: Optional[StateStorage] = None):
        """
        初始化持久化管理器
        
        Args:
            storage: 存储后端，默认使用 SQLite
        """
        self.storage = storage or SQLiteStateStorage()
    
    def save_session_state(self, session_id: str, state: Dict[str, Any]) -> bool:
        """保存会话状态"""
        key = f"session:{session_id}"
        return self.storage.save_state(key, state)
    
    def load_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """加载会话状态"""
        key = f"session:{session_id}"
        return self.storage.load_state(key)
    
    def save_task_state(self, task_id: str, state: Dict[str, Any]) -> bool:
        """保存任务状态"""
        key = f"task:{task_id}"
        return self.storage.save_state(key, state)
    
    def load_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """加载任务状态"""
        key = f"task:{task_id}"
        return self.storage.load_state(key)
    
    def save_checkpoint(self, checkpoint_id: str, checkpoint_data: Dict[str, Any]) -> bool:
        """保存检查点"""
        key = f"checkpoint:{checkpoint_id}"
        return self.storage.save_state(key, checkpoint_data)
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """加载检查点"""
        key = f"checkpoint:{checkpoint_id}"
        return self.storage.load_state(key)
    
    def list_sessions(self) -> List[str]:
        """列出所有会话"""
        keys = self.storage.list_states("session:")
        return [k.replace("session:", "") for k in keys]
    
    def list_tasks(self, session_id: Optional[str] = None) -> List[str]:
        """列出所有任务"""
        keys = self.storage.list_states("task:")
        task_ids = [k.replace("task:", "") for k in keys]
        
        if session_id:
            # 过滤特定会话的任务
            filtered = []
            for task_id in task_ids:
                state = self.load_task_state(task_id)
                if state and state.get("session_id") == session_id:
                    filtered.append(task_id)
            return filtered
        
        return task_ids
    
    def list_checkpoints(self, task_id: Optional[str] = None) -> List[str]:
        """列出所有检查点"""
        keys = self.storage.list_states("checkpoint:")
        checkpoint_ids = [k.replace("checkpoint:", "") for k in keys]
        
        if task_id:
            # 过滤特定任务的检查点
            filtered = []
            for checkpoint_id in checkpoint_ids:
                state = self.load_checkpoint(checkpoint_id)
                if state and state.get("task_id") == task_id:
                    filtered.append(checkpoint_id)
            return filtered
        
        return checkpoint_ids
    
    def cleanup(self, older_than_days: int = 30) -> Dict[str, int]:
        """清理旧数据"""
        cutoff_time = time.time() - (older_than_days * 24 * 60 * 60)
        
        stats = {
            "sessions_deleted": 0,
            "tasks_deleted": 0,
            "checkpoints_deleted": 0
        }
        
        # 清理会话
        for session_id in self.list_sessions():
            state = self.load_session_state(session_id)
            if state and state.get("updated_at", 0) < cutoff_time:
                if self.storage.delete_state(f"session:{session_id}"):
                    stats["sessions_deleted"] += 1
        
        # 清理任务
        for task_id in self.list_tasks():
            state = self.load_task_state(task_id)
            if state and state.get("updated_at", 0) < cutoff_time:
                if self.storage.delete_state(f"task:{task_id}"):
                    stats["tasks_deleted"] += 1
        
        # 清理检查点
        for checkpoint_id in self.list_checkpoints():
            state = self.load_checkpoint(checkpoint_id)
            if state and state.get("created_at", 0) < cutoff_time:
                if self.storage.delete_state(f"checkpoint:{checkpoint_id}"):
                    stats["checkpoints_deleted"] += 1
        
        return stats
