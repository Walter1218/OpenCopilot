"""
检查点管理模块

提供检查点创建、恢复和管理功能。
支持自动检查点和手动检查点。
"""

import json
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
import threading


@dataclass
class Checkpoint:
    """检查点数据类"""
    checkpoint_id: str
    task_id: str
    session_id: str
    state_snapshot: Dict[str, Any]
    created_at: float = field(default_factory=time.time)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_auto: bool = False
    parent_checkpoint_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """从字典创建"""
        return cls(**data)


class CheckpointManager:
    """
    检查点管理器
    
    功能：
    1. 创建检查点（自动/手动）
    2. 恢复检查点
    3. 管理检查点历史
    4. 检查点清理
    """
    
    def __init__(self, db_path: str = "asu_agent.db", max_checkpoints_per_task: int = 10):
        """
        初始化检查点管理器
        
        Args:
            db_path: 数据库路径
            max_checkpoints_per_task: 每个任务最大检查点数量
        """
        self.db_path = db_path
        self.max_checkpoints_per_task = max_checkpoints_per_task
        self._lock = threading.Lock()
        self._cache: Dict[str, Checkpoint] = {}
        
        # 确保表存在
        self._init_db()
    
    def _get_conn(self):
        """获取数据库连接"""
        import sqlite3
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    state_snapshot TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    description TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    is_auto INTEGER DEFAULT 0,
                    parent_checkpoint_id TEXT,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id),
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_checkpoints_task ON checkpoints(task_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_checkpoints_session ON checkpoints(session_id)')
            conn.commit()
    
    def create_checkpoint(
        self,
        task_id: str,
        session_id: str,
        state_snapshot: Dict[str, Any],
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        is_auto: bool = False,
        parent_checkpoint_id: Optional[str] = None
    ) -> Checkpoint:
        """
        创建检查点
        
        Args:
            task_id: 任务ID
            session_id: 会话ID
            state_snapshot: 状态快照
            description: 检查点描述
            metadata: 额外元数据
            is_auto: 是否自动创建
            parent_checkpoint_id: 父检查点ID
            
        Returns:
            创建的检查点
        """
        checkpoint_id = str(uuid.uuid4())
        now = time.time()
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            session_id=session_id,
            state_snapshot=state_snapshot,
            created_at=now,
            description=description,
            metadata=metadata or {},
            is_auto=is_auto,
            parent_checkpoint_id=parent_checkpoint_id
        )
        
        with self._lock:
            # 持久化
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO checkpoints (
                        checkpoint_id, task_id, session_id, state_snapshot,
                        created_at, description, metadata, is_auto, parent_checkpoint_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    checkpoint_id,
                    task_id,
                    session_id,
                    json.dumps(state_snapshot, ensure_ascii=False),
                    now,
                    description,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    1 if is_auto else 0,
                    parent_checkpoint_id
                ))
                conn.commit()
            
            # 缓存
            self._cache[checkpoint_id] = checkpoint
            
            # 清理旧检查点
            self._cleanup_old_checkpoints(task_id)
        
        return checkpoint
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        获取检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            检查点对象，不存在返回 None
        """
        # 先查缓存
        if checkpoint_id in self._cache:
            return self._cache[checkpoint_id]
        
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT checkpoint_id, task_id, session_id, state_snapshot,
                       created_at, description, metadata, is_auto, parent_checkpoint_id
                FROM checkpoints WHERE checkpoint_id = ?
            ''', (checkpoint_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            checkpoint = Checkpoint(
                checkpoint_id=row[0],
                task_id=row[1],
                session_id=row[2],
                state_snapshot=json.loads(row[3]),
                created_at=row[4],
                description=row[5],
                metadata=json.loads(row[6]) if row[6] else {},
                is_auto=bool(row[7]),
                parent_checkpoint_id=row[8]
            )
            
            # 缓存
            self._cache[checkpoint_id] = checkpoint
            return checkpoint
    
    def get_task_checkpoints(
        self,
        task_id: str,
        limit: int = 100,
        include_auto: bool = True
    ) -> List[Checkpoint]:
        """
        获取任务的检查点列表
        
        Args:
            task_id: 任务ID
            limit: 返回数量限制
            include_auto: 是否包含自动检查点
            
        Returns:
            检查点列表
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            if include_auto:
                cursor.execute('''
                    SELECT checkpoint_id FROM checkpoints
                    WHERE task_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (task_id, limit))
            else:
                cursor.execute('''
                    SELECT checkpoint_id FROM checkpoints
                    WHERE task_id = ? AND is_auto = 0
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (task_id, limit))
            
            checkpoint_ids = [row[0] for row in cursor.fetchall()]
            return [self.get_checkpoint(cid) for cid in checkpoint_ids if self.get_checkpoint(cid)]
    
    def get_latest_checkpoint(self, task_id: str) -> Optional[Checkpoint]:
        """
        获取任务的最新检查点
        
        Args:
            task_id: 任务ID
            
        Returns:
            最新的检查点
        """
        checkpoints = self.get_task_checkpoints(task_id, limit=1)
        return checkpoints[0] if checkpoints else None
    
    def restore_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        恢复检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            恢复的状态快照
        """
        checkpoint = self.get_checkpoint(checkpoint_id)
        if checkpoint:
            return checkpoint.state_snapshot
        return None
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        删除检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            是否删除成功
        """
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM checkpoints WHERE checkpoint_id = ?", (checkpoint_id,))
                conn.commit()
            
            # 清除缓存
            if checkpoint_id in self._cache:
                del self._cache[checkpoint_id]
            
            return True
    
    def delete_task_checkpoints(self, task_id: str) -> int:
        """
        删除任务的所有检查点
        
        Args:
            task_id: 任务ID
            
        Returns:
            删除的检查点数量
        """
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM checkpoints WHERE task_id = ?", (task_id,))
                deleted_count = cursor.rowcount
                conn.commit()
            
            # 清除缓存
            to_remove = [cid for cid, cp in self._cache.items() if cp.task_id == task_id]
            for cid in to_remove:
                del self._cache[cid]
            
            return deleted_count
    
    def _cleanup_old_checkpoints(self, task_id: str):
        """清理旧检查点，保留最新的 N 个"""
        checkpoints = self.get_task_checkpoints(task_id, limit=1000)
        
        if len(checkpoints) > self.max_checkpoints_per_task:
            # 删除最旧的检查点
            to_delete = checkpoints[self.max_checkpoints_per_task:]
            for checkpoint in to_delete:
                self.delete_checkpoint(checkpoint.checkpoint_id)
    
    def get_checkpoint_chain(self, checkpoint_id: str) -> List[Checkpoint]:
        """
        获取检查点链（从当前到根）
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            检查点链
        """
        chain = []
        current_id = checkpoint_id
        
        while current_id:
            checkpoint = self.get_checkpoint(current_id)
            if not checkpoint:
                break
            
            chain.append(checkpoint)
            current_id = checkpoint.parent_checkpoint_id
        
        return chain
    
    def compare_checkpoints(
        self,
        checkpoint_id1: str,
        checkpoint_id2: str
    ) -> Dict[str, Any]:
        """
        比较两个检查点
        
        Args:
            checkpoint_id1: 检查点1 ID
            checkpoint_id2: 检查点2 ID
            
        Returns:
            比较结果
        """
        cp1 = self.get_checkpoint(checkpoint_id1)
        cp2 = self.get_checkpoint(checkpoint_id2)
        
        if not cp1 or not cp2:
            return {"error": "检查点不存在"}
        
        diff = {
            "checkpoint1": {
                "id": cp1.checkpoint_id,
                "created_at": cp1.created_at,
                "description": cp1.description
            },
            "checkpoint2": {
                "id": cp2.checkpoint_id,
                "created_at": cp2.created_at,
                "description": cp2.description
            },
            "differences": {}
        }
        
        # 比较状态快照
        state1 = cp1.state_snapshot
        state2 = cp2.state_snapshot
        
        all_keys = set(state1.keys()) | set(state2.keys())
        
        for key in all_keys:
            val1 = state1.get(key)
            val2 = state2.get(key)
            
            if val1 != val2:
                diff["differences"][key] = {
                    "checkpoint1": val1,
                    "checkpoint2": val2
                }
        
        return diff
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取检查点统计信息
        
        Returns:
            统计信息
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            stats = {
                "total_checkpoints": 0,
                "auto_checkpoints": 0,
                "manual_checkpoints": 0,
                "tasks_with_checkpoints": 0,
                "avg_checkpoints_per_task": 0
            }
            
            cursor.execute("SELECT COUNT(*) FROM checkpoints")
            stats["total_checkpoints"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM checkpoints WHERE is_auto = 1")
            stats["auto_checkpoints"] = cursor.fetchone()[0]
            
            stats["manual_checkpoints"] = stats["total_checkpoints"] - stats["auto_checkpoints"]
            
            cursor.execute("SELECT COUNT(DISTINCT task_id) FROM checkpoints")
            stats["tasks_with_checkpoints"] = cursor.fetchone()[0]
            
            if stats["tasks_with_checkpoints"] > 0:
                stats["avg_checkpoints_per_task"] = round(
                    stats["total_checkpoints"] / stats["tasks_with_checkpoints"], 2
                )
            
            return stats
    
    def cleanup(self, older_than_days: int = 30) -> int:
        """
        清理旧检查点
        
        Args:
            older_than_days: 保留最近多少天的数据
            
        Returns:
            清理的检查点数量
        """
        cutoff_time = time.time() - (older_than_days * 24 * 60 * 60)
        
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM checkpoints WHERE created_at < ?
                ''', (cutoff_time,))
                deleted_count = cursor.rowcount
                conn.commit()
            
            # 清除缓存
            to_remove = [cid for cid, cp in self._cache.items() if cp.created_at < cutoff_time]
            for cid in to_remove:
                del self._cache[cid]
            
            return deleted_count
