"""
记忆存储引擎模块

提供记忆的持久化存储功能，支持 SQLite 和文件系统两种存储后端。
"""

import time
import json
import sqlite3
from typing import Dict, List, Optional, Any, Protocol
from abc import ABC, abstractmethod
from dataclasses import dataclass
import threading


class MemoryStorage(ABC):
    """记忆存储抽象基类"""
    
    @abstractmethod
    def store(self, memory_data: Dict[str, Any]) -> bool:
        """存储记忆"""
        pass
    
    @abstractmethod
    def retrieve(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """检索记忆"""
        pass
    
    @abstractmethod
    def update(self, memory_id: str, memory_data: Dict[str, Any]) -> bool:
        """更新记忆"""
        pass
    
    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    def search(self, query: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """搜索记忆"""
        pass
    
    @abstractmethod
    def count(self, query: Dict[str, Any] = None) -> int:
        """统计记忆数量"""
        pass


class SQLiteMemoryStorage(MemoryStorage):
    """SQLite 记忆存储实现"""
    
    def __init__(self, db_path: str = "memory.db"):
        """
        初始化 SQLite 存储
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 记忆表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    content TEXT,
                    memory_type TEXT DEFAULT 'short_term',
                    importance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    created_at REAL,
                    updated_at REAL,
                    last_accessed REAL,
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    embedding TEXT
                )
            ''')
            
            # 标签表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT,
                    tag TEXT,
                    created_at REAL,
                    FOREIGN KEY(memory_id) REFERENCES memories(memory_id)
                )
            ''')
            
            # 索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_last_accessed ON memories(last_accessed)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_tags_memory ON memory_tags(memory_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_tags_tag ON memory_tags(tag)')
            
            conn.commit()
    
    def store(self, memory_data: Dict[str, Any]) -> bool:
        """
        存储记忆
        
        Args:
            memory_data: 记忆数据字典
            
        Returns:
            是否存储成功
        """
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # 准备数据
                memory_id = memory_data.get("memory_id")
                session_id = memory_data.get("session_id")
                content = memory_data.get("content")
                memory_type = memory_data.get("memory_type", "short_term")
                importance = memory_data.get("importance", 0.5)
                access_count = memory_data.get("access_count", 0)
                created_at = memory_data.get("created_at", time.time())
                updated_at = memory_data.get("updated_at", time.time())
                last_accessed = memory_data.get("last_accessed", time.time())
                tags = memory_data.get("tags", [])
                metadata = memory_data.get("metadata", {})
                embedding = memory_data.get("embedding")
                
                # 插入记忆
                cursor.execute('''
                    INSERT INTO memories (
                        memory_id, session_id, content, memory_type, importance,
                        access_count, created_at, updated_at, last_accessed,
                        tags, metadata, embedding
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    memory_id, session_id, content, memory_type, importance,
                    access_count, created_at, updated_at, last_accessed,
                    json.dumps(tags), json.dumps(metadata),
                    json.dumps(embedding) if embedding else None
                ))
                
                # 插入标签
                for tag in tags:
                    cursor.execute(
                        "INSERT INTO memory_tags (memory_id, tag, created_at) VALUES (?, ?, ?)",
                        (memory_id, tag, created_at)
                    )
                
                conn.commit()
                return True
    
    def retrieve(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        检索记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            记忆数据字典
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM memories WHERE memory_id = ?",
                (memory_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # 转换为字典
            columns = [description[0] for description in cursor.description]
            memory_data = dict(zip(columns, row))
            
            # 解析JSON字段
            memory_data["tags"] = json.loads(memory_data["tags"]) if memory_data["tags"] else []
            memory_data["metadata"] = json.loads(memory_data["metadata"]) if memory_data["metadata"] else {}
            memory_data["embedding"] = json.loads(memory_data["embedding"]) if memory_data["embedding"] else None
            
            # 更新访问计数
            cursor.execute(
                "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE memory_id = ?",
                (time.time(), memory_id)
            )
            conn.commit()
            
            return memory_data
    
    def update(self, memory_id: str, memory_data: Dict[str, Any]) -> bool:
        """
        更新记忆
        
        Args:
            memory_id: 记忆ID
            memory_data: 更新的数据
            
        Returns:
            是否更新成功
        """
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # 检查记忆是否存在
                cursor.execute("SELECT 1 FROM memories WHERE memory_id = ?", (memory_id,))
                if not cursor.fetchone():
                    return False
                
                # 构建更新语句
                update_fields = []
                params = []
                
                for field in ["content", "memory_type", "importance", "access_count",
                             "created_at", "updated_at", "last_accessed", "embedding"]:
                    if field in memory_data:
                        update_fields.append(f"{field} = ?")
                        if field == "embedding" and memory_data[field] is not None:
                            params.append(json.dumps(memory_data[field]))
                        else:
                            params.append(memory_data[field])
                
                # 处理JSON字段
                if "tags" in memory_data:
                    update_fields.append("tags = ?")
                    params.append(json.dumps(memory_data["tags"]))
                    
                    # 更新标签表
                    cursor.execute("DELETE FROM memory_tags WHERE memory_id = ?", (memory_id,))
                    for tag in memory_data["tags"]:
                        cursor.execute(
                            "INSERT INTO memory_tags (memory_id, tag, created_at) VALUES (?, ?, ?)",
                            (memory_id, tag, time.time())
                        )
                
                if "metadata" in memory_data:
                    update_fields.append("metadata = ?")
                    params.append(json.dumps(memory_data["metadata"]))
                
                if not update_fields:
                    return True
                
                # 执行更新
                update_fields.append("updated_at = ?")
                params.append(time.time())
                params.append(memory_id)
                
                cursor.execute(f'''
                    UPDATE memories SET {', '.join(update_fields)}
                    WHERE memory_id = ?
                ''', params)
                
                conn.commit()
                return True
    
    def delete(self, memory_id: str) -> bool:
        """
        删除记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            是否删除成功
        """
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # 删除标签
                cursor.execute("DELETE FROM memory_tags WHERE memory_id = ?", (memory_id,))
                
                # 删除记忆
                cursor.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))
                
                deleted = cursor.rowcount > 0
                conn.commit()
                
                return deleted
    
    def search(self, query: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索记忆
        
        Args:
            query: 查询条件
            limit: 返回数量限制
            
        Returns:
            匹配的记忆列表
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if "session_id" in query:
                conditions.append("session_id = ?")
                params.append(query["session_id"])
            
            if "memory_type" in query:
                if isinstance(query["memory_type"], list):
                    placeholders = ','.join(['?' for _ in query["memory_type"]])
                    conditions.append(f"memory_type IN ({placeholders})")
                    params.extend(query["memory_type"])
                else:
                    conditions.append("memory_type = ?")
                    params.append(query["memory_type"])
            
            if "min_importance" in query:
                conditions.append("importance >= ?")
                params.append(query["min_importance"])
            
            if "max_importance" in query:
                conditions.append("importance <= ?")
                params.append(query["max_importance"])
            
            if "tags" in query:
                # 使用标签表进行搜索
                tag_conditions = []
                for tag in query["tags"]:
                    tag_conditions.append("? IN (SELECT tag FROM memory_tags WHERE memory_id = memories.memory_id)")
                    params.append(tag)
                if tag_conditions:
                    conditions.append(f"({' AND '.join(tag_conditions)})")
            
            if "content_like" in query:
                conditions.append("content LIKE ?")
                params.append(f"%{query['content_like']}%")
            
            if "created_after" in query:
                conditions.append("created_at >= ?")
                params.append(query["created_after"])
            
            if "created_before" in query:
                conditions.append("created_at <= ?")
                params.append(query["created_before"])
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 排序
            order_by = "importance DESC, last_accessed DESC"
            if "order_by" in query:
                order_by = query["order_by"]
            
            cursor.execute(f'''
                SELECT * FROM memories
                WHERE {where_clause}
                ORDER BY {order_by}
                LIMIT ?
            ''', params + [limit])
            
            results = []
            columns = [description[0] for description in cursor.description]
            
            for row in cursor.fetchall():
                memory_data = dict(zip(columns, row))
                memory_data["tags"] = json.loads(memory_data["tags"]) if memory_data["tags"] else []
                memory_data["metadata"] = json.loads(memory_data["metadata"]) if memory_data["metadata"] else {}
                memory_data["embedding"] = json.loads(memory_data["embedding"]) if memory_data["embedding"] else None
                results.append(memory_data)
            
            return results
    
    def count(self, query: Dict[str, Any] = None) -> int:
        """
        统计记忆数量
        
        Args:
            query: 查询条件（可选）
            
        Returns:
            记忆数量
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            if query:
                # 构建查询条件
                conditions = []
                params = []
                
                if "session_id" in query:
                    conditions.append("session_id = ?")
                    params.append(query["session_id"])
                
                if "memory_type" in query:
                    conditions.append("memory_type = ?")
                    params.append(query["memory_type"])
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                cursor.execute(f"SELECT COUNT(*) FROM memories WHERE {where_clause}", params)
            else:
                cursor.execute("SELECT COUNT(*) FROM memories")
            
            return cursor.fetchone()[0]
    
    def get_all_memories(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取所有记忆（分页）
        
        Args:
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            记忆列表
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM memories
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            results = []
            columns = [description[0] for description in cursor.description]
            
            for row in cursor.fetchall():
                memory_data = dict(zip(columns, row))
                memory_data["tags"] = json.loads(memory_data["tags"]) if memory_data["tags"] else []
                memory_data["metadata"] = json.loads(memory_data["metadata"]) if memory_data["metadata"] else {}
                memory_data["embedding"] = json.loads(memory_data["embedding"]) if memory_data["embedding"] else None
                results.append(memory_data)
            
            return results
    
    def clear_session(self, session_id: str) -> int:
        """
        清空会话的所有记忆
        
        Args:
            session_id: 会话ID
            
        Returns:
            删除的记忆数量
        """
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # 获取会话的所有记忆ID
                cursor.execute("SELECT memory_id FROM memories WHERE session_id = ?", (session_id,))
                memory_ids = [row[0] for row in cursor.fetchall()]
                
                # 删除标签
                for memory_id in memory_ids:
                    cursor.execute("DELETE FROM memory_tags WHERE memory_id = ?", (memory_id,))
                
                # 删除记忆
                cursor.execute("DELETE FROM memories WHERE session_id = ?", (session_id,))
                deleted_count = cursor.rowcount
                
                conn.commit()
                
                return deleted_count
    
    def clear_all(self) -> int:
        """
        清空所有记忆
        
        Returns:
            删除的记忆数量
        """
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # 删除所有标签
                cursor.execute("DELETE FROM memory_tags")
                
                # 删除所有记忆
                cursor.execute("DELETE FROM memories")
                deleted_count = cursor.rowcount
                
                conn.commit()
                
                return deleted_count
