"""
记忆系统核心模块

提供 MemoryManager 类，管理智能体的记忆系统。
完全兼容现有 ASUAgentMemory 接口，并扩展高级记忆功能。
"""

import time
import uuid
import json
import sqlite3
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading


class MemoryType(Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"   # 短期记忆（会话内）
    LONG_TERM = "long_term"     # 长期记忆（跨会话）
    WORKING = "working"         # 工作记忆（当前任务）
    EPISODIC = "episodic"       # 情景记忆（特定事件）
    SEMANTIC = "semantic"       # 语义记忆（知识事实）
    PROCEDURAL = "procedural"   # 程序记忆（操作步骤）


@dataclass
class MemoryEntry:
    """记忆条目数据类"""
    memory_id: str
    session_id: str
    content: str
    memory_type: MemoryType = MemoryType.SHORT_TERM
    importance: float = 0.5  # 0.0-1.0
    access_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["memory_type"] = self.memory_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """从字典创建"""
        data = data.copy()
        if "memory_type" in data and isinstance(data["memory_type"], str):
            data["memory_type"] = MemoryType(data["memory_type"])
        return cls(**data)


class MemoryManager:
    """
    记忆管理器 - 乐高积木模块
    
    功能：
    1. 管理会话记忆（兼容 ASUAgentMemory）
    2. 管理长期记忆（新增）
    3. 提供语义检索（新增）
    4. 支持记忆组织（新增）
    5. 支持遗忘机制（新增）
    
    完全兼容现有 ASUAgentMemory 接口：
    - get_context(session_id)
    - add_message(session_id, role, content)
    - set_persona(session_id, persona)
    - clear(session_id)
    - session_count()
    """
    
    def __init__(self, db_path: str = "memory.db", 
                 embedding_model: Optional[str] = None,
                 auto_compress: bool = True):
        """
        初始化记忆管理器
        
        Args:
            db_path: 数据库路径
            embedding_model: 嵌入模型名称（可选）
            auto_compress: 是否自动压缩
        """
        self.db_path = db_path
        self.embedding_model = embedding_model
        self.auto_compress = auto_compress
        self._lock = threading.RLock()  # RLock 防止 add_message → store_memory 同一线程重入死锁
        
        # 初始化数据库
        self._init_db()
        
        # 缓存（线程安全）
        self._memory_cache: Dict[str, MemoryEntry] = {}
        self._session_cache: Dict[str, Dict[str, Any]] = {}
        
        # 初始化子模块（延迟加载）
        self._storage = None
        self._retrieval = None
        self._organization = None
        self._forgetting = None
        self._compression = None
    
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
            
            # 记忆表（新增）
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
                    embedding TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            ''')
            
            # 记忆标签表（新增）
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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memories_last_accessed ON memories(last_accessed)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_tags_memory ON memory_tags(memory_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_memory_tags_tag ON memory_tags(tag)')
            
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
                
                # 自动存储重要消息到记忆
                if self._is_important_message(content):
                    self.store_memory(
                        content=content,
                        memory_type=MemoryType.EPISODIC,
                        session_id=session_id,
                        importance=0.6,
                        tags=[role, "message"]
                    )
    
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
                    self._session_cache[session_id]["persona"] = persona
                    self._session_cache[session_id]["updated_at"] = time.time()
    
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
    # 新增：记忆管理功能
    # ==========================================
    
    def store_memory(self, content: str, memory_type: MemoryType,
                    session_id: str, importance: float = 0.5,
                    tags: List[str] = None, metadata: Dict[str, Any] = None) -> MemoryEntry:
        """
        存储记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型
            session_id: 会话ID
            importance: 重要性评分 (0.0-1.0)
            tags: 标签列表
            metadata: 额外元数据
            
        Returns:
            存储的记忆条目
        """
        memory_id = str(uuid.uuid4())
        now = time.time()
        
        # 确保会话存在
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO sessions (session_id, persona, updated_at, created_at) VALUES (?, 'default', ?, ?)",
                (session_id, now, now)
            )
            conn.commit()
        
        memory = MemoryEntry(
            memory_id=memory_id,
            session_id=session_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            access_count=0,
            created_at=now,
            updated_at=now,
            last_accessed=now,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO memories (
                        memory_id, session_id, content, memory_type, importance,
                        access_count, created_at, updated_at, last_accessed,
                        tags, metadata, embedding
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    memory_id, session_id, content, memory_type.value, importance,
                    0, now, now, now,
                    json.dumps(tags or []), json.dumps(metadata or {}),
                    json.dumps(memory.embedding) if memory.embedding else None
                ))
                
                # 添加标签
                if tags:
                    for tag in tags:
                        cursor.execute(
                            "INSERT INTO memory_tags (memory_id, tag, created_at) VALUES (?, ?, ?)",
                            (memory_id, tag, now)
                        )
                
                conn.commit()
            
            # 缓存记忆
            self._memory_cache[memory_id] = memory
        
        return memory
    
    def retrieve_memories(self, query: str, limit: int = 10,
                         memory_types: List[MemoryType] = None,
                         min_importance: float = 0.0,
                         session_id: Optional[str] = None) -> List[MemoryEntry]:
        """
        检索相关记忆
        
        Args:
            query: 查询文本
            limit: 返回数量限制
            memory_types: 记忆类型过滤
            min_importance: 最小重要性
            session_id: 会话ID过滤（可选）
            
        Returns:
            相关记忆列表
        """
        # 简单实现：基于关键词匹配
        # 实际实现应该使用语义嵌入和向量相似度
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if memory_types:
                type_placeholders = ','.join(['?' for _ in memory_types])
                conditions.append(f"memory_type IN ({type_placeholders})")
                params.extend([t.value for t in memory_types])
            
            if min_importance > 0:
                conditions.append("importance >= ?")
                params.append(min_importance)
            
            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)
            
            # 简单的关键词匹配
            if query:
                conditions.append("content LIKE ?")
                params.append(f"%{query}%")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cursor.execute(f'''
                SELECT memory_id, session_id, content, memory_type, importance,
                       access_count, created_at, updated_at, last_accessed,
                       tags, metadata, embedding
                FROM memories
                WHERE {where_clause}
                ORDER BY importance DESC, last_accessed DESC
                LIMIT ?
            ''', params + [limit])
            
            memories = []
            for row in cursor.fetchall():
                memory = MemoryEntry(
                    memory_id=row[0],
                    session_id=row[1],
                    content=row[2],
                    memory_type=MemoryType(row[3]),
                    importance=row[4],
                    access_count=row[5],
                    created_at=row[6],
                    updated_at=row[7],
                    last_accessed=row[8],
                    tags=json.loads(row[9]) if row[9] else [],
                    metadata=json.loads(row[10]) if row[10] else {},
                    embedding=json.loads(row[11]) if row[11] else None
                )
                memories.append(memory)
                
                # 更新访问计数
                cursor.execute(
                    "UPDATE memories SET access_count = access_count + 1, last_accessed = ? WHERE memory_id = ?",
                    (time.time(), memory.memory_id)
                )
            
            conn.commit()
            
            return memories
    
    def search_by_tags(self, tags: List[str], limit: int = 10) -> List[MemoryEntry]:
        """
        按标签搜索记忆
        
        Args:
            tags: 标签列表
            limit: 返回数量限制
            
        Returns:
            匹配的记忆列表
        """
        if not tags:
            return []
        
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 使用标签表进行搜索
            placeholders = ','.join(['?' for _ in tags])
            cursor.execute(f'''
                SELECT DISTINCT m.memory_id, m.session_id, m.content, m.memory_type, m.importance,
                       m.access_count, m.created_at, m.updated_at, m.last_accessed,
                       m.tags, m.metadata, m.embedding
                FROM memories m
                JOIN memory_tags mt ON m.memory_id = mt.memory_id
                WHERE mt.tag IN ({placeholders})
                ORDER BY m.importance DESC, m.last_accessed DESC
                LIMIT ?
            ''', tags + [limit])
            
            memories = []
            for row in cursor.fetchall():
                memory = MemoryEntry(
                    memory_id=row[0],
                    session_id=row[1],
                    content=row[2],
                    memory_type=MemoryType(row[3]),
                    importance=row[4],
                    access_count=row[5],
                    created_at=row[6],
                    updated_at=row[7],
                    last_accessed=row[8],
                    tags=json.loads(row[9]) if row[9] else [],
                    metadata=json.loads(row[10]) if row[10] else {},
                    embedding=json.loads(row[11]) if row[11] else None
                )
                memories.append(memory)
            
            return memories
    
    def update_memory(self, memory_id: str, content: str = None,
                     importance: float = None, tags: List[str] = None,
                     metadata: Dict[str, Any] = None) -> Optional[MemoryEntry]:
        """
        更新记忆
        
        Args:
            memory_id: 记忆ID
            content: 新内容
            importance: 新重要性
            tags: 新标签
            metadata: 新元数据
            
        Returns:
            更新后的记忆条目
        """
        with self._lock:
            # 从缓存或数据库获取记忆
            memory = self._memory_cache.get(memory_id)
            if not memory:
                with self._get_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT * FROM memories WHERE memory_id = ?",
                        (memory_id,)
                    )
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    memory = MemoryEntry(
                        memory_id=row[0],
                        session_id=row[1],
                        content=row[2],
                        memory_type=MemoryType(row[3]),
                        importance=row[4],
                        access_count=row[5],
                        created_at=row[6],
                        updated_at=row[7],
                        last_accessed=row[8],
                        tags=json.loads(row[9]) if row[9] else [],
                        metadata=json.loads(row[10]) if row[10] else {},
                        embedding=json.loads(row[11]) if row[11] else None
                    )
            
            # 更新字段
            if content is not None:
                memory.content = content
            if importance is not None:
                memory.importance = importance
            if tags is not None:
                memory.tags = tags
            if metadata is not None:
                memory.metadata.update(metadata)
            
            memory.updated_at = time.time()
            
            # 持久化
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE memories SET
                        content = ?, importance = ?, tags = ?, metadata = ?,
                        updated_at = ?, embedding = ?
                    WHERE memory_id = ?
                ''', (
                    memory.content, memory.importance,
                    json.dumps(memory.tags), json.dumps(memory.metadata),
                    memory.updated_at,
                    json.dumps(memory.embedding) if memory.embedding else None,
                    memory_id
                ))
                
                # 更新标签表
                if tags is not None:
                    cursor.execute("DELETE FROM memory_tags WHERE memory_id = ?", (memory_id,))
                    for tag in tags:
                        cursor.execute(
                            "INSERT INTO memory_tags (memory_id, tag, created_at) VALUES (?, ?, ?)",
                            (memory_id, tag, time.time())
                        )
                
                conn.commit()
            
            # 更新缓存
            self._memory_cache[memory_id] = memory
            
            return memory
    
    def delete_memory(self, memory_id: str) -> bool:
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
            
            # 从缓存删除
            if memory_id in self._memory_cache:
                del self._memory_cache[memory_id]
            
            return deleted
    
    def get_important_memories(self, limit: int = 10) -> List[MemoryEntry]:
        """
        获取重要记忆
        
        Args:
            limit: 返回数量限制
            
        Returns:
            重要记忆列表
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT memory_id, session_id, content, memory_type, importance,
                       access_count, created_at, updated_at, last_accessed,
                       tags, metadata, embedding
                FROM memories
                ORDER BY importance DESC, access_count DESC
                LIMIT ?
            ''', (limit,))
            
            memories = []
            for row in cursor.fetchall():
                memory = MemoryEntry(
                    memory_id=row[0],
                    session_id=row[1],
                    content=row[2],
                    memory_type=MemoryType(row[3]),
                    importance=row[4],
                    access_count=row[5],
                    created_at=row[6],
                    updated_at=row[7],
                    last_accessed=row[8],
                    tags=json.loads(row[9]) if row[9] else [],
                    metadata=json.loads(row[10]) if row[10] else {},
                    embedding=json.loads(row[11]) if row[11] else None
                )
                memories.append(memory)
            
            return memories
    
    def get_recent_memories(self, limit: int = 10) -> List[MemoryEntry]:
        """
        获取最近记忆
        
        Args:
            limit: 返回数量限制
            
        Returns:
            最近记忆列表
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT memory_id, session_id, content, memory_type, importance,
                       access_count, created_at, updated_at, last_accessed,
                       tags, metadata, embedding
                FROM memories
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            memories = []
            for row in cursor.fetchall():
                memory = MemoryEntry(
                    memory_id=row[0],
                    session_id=row[1],
                    content=row[2],
                    memory_type=MemoryType(row[3]),
                    importance=row[4],
                    access_count=row[5],
                    created_at=row[6],
                    updated_at=row[7],
                    last_accessed=row[8],
                    tags=json.loads(row[9]) if row[9] else [],
                    metadata=json.loads(row[10]) if row[10] else {},
                    embedding=json.loads(row[11]) if row[11] else None
                )
                memories.append(memory)
            
            return memories
    
    def compress_memories(self, session_id: str = None) -> Dict[str, Any]:
        """
        压缩记忆
        
        Args:
            session_id: 会话ID（可选）
            
        Returns:
            压缩统计信息
        """
        # 简单实现：删除低重要性、低访问次数的记忆
        # 实际实现应该使用更复杂的压缩算法
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # 统计压缩前的记忆数量
                if session_id:
                    cursor.execute("SELECT COUNT(*) FROM memories WHERE session_id = ?", (session_id,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM memories")
                before_count = cursor.fetchone()[0]
                
                # 删除低重要性、低访问次数的记忆
                if session_id:
                    cursor.execute('''
                        DELETE FROM memories 
                        WHERE session_id = ? AND importance < 0.3 AND access_count < 2
                    ''', (session_id,))
                else:
                    cursor.execute('''
                        DELETE FROM memories 
                        WHERE importance < 0.3 AND access_count < 2
                    ''')
                
                deleted_count = cursor.rowcount
                
                # 统计压缩后的记忆数量
                if session_id:
                    cursor.execute("SELECT COUNT(*) FROM memories WHERE session_id = ?", (session_id,))
                else:
                    cursor.execute("SELECT COUNT(*) FROM memories")
                after_count = cursor.fetchone()[0]
                
                conn.commit()
            
            # 清除缓存中已删除的记忆
            self._memory_cache.clear()
            
            return {
                "before_count": before_count,
                "after_count": after_count,
                "deleted_count": deleted_count,
                "compression_ratio": deleted_count / before_count if before_count > 0 else 0
            }
    
    def forget_old_memories(self, days_threshold: int = 30) -> Dict[str, Any]:
        """
        遗忘旧记忆
        
        Args:
            days_threshold: 天数阈值
            
        Returns:
            遗忘统计信息
        """
        threshold_time = time.time() - (days_threshold * 24 * 60 * 60)
        
        with self._lock:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # 统计遗忘前的记忆数量
                cursor.execute("SELECT COUNT(*) FROM memories")
                before_count = cursor.fetchone()[0]
                
                # 删除旧的、低重要性的记忆
                cursor.execute('''
                    DELETE FROM memories 
                    WHERE last_accessed < ? AND importance < 0.5
                ''', (threshold_time,))
                
                deleted_count = cursor.rowcount
                
                # 统计遗忘后的记忆数量
                cursor.execute("SELECT COUNT(*) FROM memories")
                after_count = cursor.fetchone()[0]
                
                conn.commit()
            
            # 清除缓存中已删除的记忆
            self._memory_cache.clear()
            
            return {
                "before_count": before_count,
                "after_count": after_count,
                "deleted_count": deleted_count,
                "forget_ratio": deleted_count / before_count if before_count > 0 else 0,
                "days_threshold": days_threshold
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取记忆统计信息
        
        Returns:
            统计信息字典
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            stats = {
                "total_sessions": 0,
                "total_messages": 0,
                "total_memories": 0,
                "memories_by_type": {},
                "memories_by_importance": {},
                "avg_importance": 0.0,
                "avg_access_count": 0.0,
            }
            
            # 会话统计
            cursor.execute("SELECT COUNT(*) FROM sessions")
            stats["total_sessions"] = cursor.fetchone()[0]
            
            # 消息统计
            cursor.execute("SELECT COUNT(*) FROM messages")
            stats["total_messages"] = cursor.fetchone()[0]
            
            # 记忆统计
            cursor.execute("SELECT COUNT(*) FROM memories")
            stats["total_memories"] = cursor.fetchone()[0]
            
            # 按类型统计
            cursor.execute('''
                SELECT memory_type, COUNT(*) FROM memories GROUP BY memory_type
            ''')
            for row in cursor.fetchall():
                stats["memories_by_type"][row[0]] = row[1]
            
            # 按重要性统计
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN importance >= 0.8 THEN 'high'
                        WHEN importance >= 0.5 THEN 'medium'
                        ELSE 'low'
                    END as importance_level,
                    COUNT(*) 
                FROM memories 
                GROUP BY importance_level
            ''')
            for row in cursor.fetchall():
                stats["memories_by_importance"][row[0]] = row[1]
            
            # 平均重要性
            cursor.execute("SELECT AVG(importance) FROM memories")
            avg_importance = cursor.fetchone()[0]
            stats["avg_importance"] = avg_importance if avg_importance else 0.0
            
            # 平均访问次数
            cursor.execute("SELECT AVG(access_count) FROM memories")
            avg_access = cursor.fetchone()[0]
            stats["avg_access_count"] = avg_access if avg_access else 0.0
            
            return stats
    
    def _is_important_message(self, content: str) -> bool:
        """
        判断消息是否重要（避免每条 AI 回复都触发同步 SQLite 存储）

        Args:
            content: 消息内容

        Returns:
            是否重要
        """
        # 太短的消息不存储（过滤"你好"、"谢谢"等简单问候）
        if len(content) < 30:
            return False
        # 只有明确意图的消息才存储为记忆
        important_keywords = [
            "记住这个", "保存下来", "别忘了", "记住",
            "bug", "error", "fix", "issue", "problem", "solution",
        ]

        content_lower = content.lower()
        return any(keyword in content_lower for keyword in important_keywords)


# 兼容性别名
ASUAgentMemory = MemoryManager
