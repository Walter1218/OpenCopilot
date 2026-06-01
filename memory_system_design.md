# 记忆系统模块设计

## 1. 设计目标

### 1.1 核心目标
1. **长期记忆**：跨会话保存重要信息
2. **智能检索**：基于语义相似度快速检索相关记忆
3. **自动组织**：自动分类和标签化记忆
4. **遗忘机制**：自动遗忘不重要的记忆，保持记忆库高效
5. **完全兼容**：与现有 ASUAgentMemory 100% 兼容

### 1.2 价值主张
1. **提升对话质量**：利用历史记忆提供更精准的回答
2. **减少重复计算**：缓存常见问题的答案
3. **个性化服务**：根据用户历史偏好定制回答
4. **知识积累**：随时间积累项目知识和用户偏好

## 2. 架构设计

### 2.1 核心组件

```
memory_system/
├── __init__.py          # 模块初始化
├── core.py              # MemoryManager 核心类
├── storage.py           # 记忆存储引擎
├── retrieval.py         # 记忆检索引擎
├── organization.py      # 记忆组织管理
├── forgetting.py        # 遗忘机制
├── compression.py       # 记忆压缩
├── api.py               # RESTful API
└── utils.py             # 工具函数
```

### 2.2 数据模型

#### 记忆条目（MemoryEntry）
```python
@dataclass
class MemoryEntry:
    memory_id: str              # 唯一标识
    session_id: str             # 所属会话
    content: str                # 记忆内容
    memory_type: MemoryType     # 记忆类型
    importance: float           # 重要性评分 (0.0-1.0)
    access_count: int           # 访问次数
    created_at: float           # 创建时间
    updated_at: float           # 更新时间
    last_accessed: float        # 最后访问时间
    tags: List[str]             # 标签列表
    metadata: Dict[str, Any]    # 元数据
    embedding: Optional[List[float]]  # 语义嵌入向量
```

#### 记忆类型（MemoryType）
```python
class MemoryType(Enum):
    SHORT_TERM = "short_term"   # 短期记忆（会话内）
    LONG_TERM = "long_term"     # 长期记忆（跨会话）
    WORKING = "working"         # 工作记忆（当前任务）
    EPISODIC = "episodic"       # 情景记忆（特定事件）
    SEMANTIC = "semantic"       # 语义记忆（知识事实）
    PROCEDURAL = "procedural"   # 程序记忆（操作步骤）
```

### 2.3 核心类设计

#### MemoryManager
```python
class MemoryManager:
    """记忆管理器 - 乐高积木模块"""
    
    def __init__(self, db_path: str = "memory.db", 
                 embedding_model: Optional[str] = None):
        # 初始化存储引擎
        self.storage = MemoryStorage(db_path)
        # 初始化检索引擎
        self.retrieval = MemoryRetrieval(self.storage, embedding_model)
        # 初始化组织管理
        self.organization = MemoryOrganization(self.storage)
        # 初始化遗忘机制
        self.forgetting = MemoryForgetting(self.storage)
        # 初始化压缩机制
        self.compression = MemoryCompression(self.storage)
    
    # 兼容 ASUAgentMemory 接口
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """获取会话上下文（兼容）"""
        pass
    
    def add_message(self, session_id: str, role: str, content: str):
        """添加消息（兼容）"""
        pass
    
    def set_persona(self, session_id: str, persona: str):
        """设置人设（兼容）"""
        pass
    
    def clear(self, session_id: str):
        """清空会话（兼容）"""
        pass
    
    def session_count(self) -> int:
        """获取会话数量（兼容）"""
        pass
    
    # 新增记忆功能
    def store_memory(self, content: str, memory_type: MemoryType,
                    session_id: str, importance: float = 0.5,
                    tags: List[str] = None) -> MemoryEntry:
        """存储记忆"""
        pass
    
    def retrieve_memories(self, query: str, limit: int = 10,
                         memory_types: List[MemoryType] = None,
                         min_importance: float = 0.0) -> List[MemoryEntry]:
        """检索相关记忆"""
        pass
    
    def search_by_tags(self, tags: List[str], limit: int = 10) -> List[MemoryEntry]:
        """按标签搜索记忆"""
        pass
    
    def update_memory(self, memory_id: str, content: str = None,
                     importance: float = None, tags: List[str] = None) -> MemoryEntry:
        """更新记忆"""
        pass
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        pass
    
    def get_important_memories(self, limit: int = 10) -> List[MemoryEntry]:
        """获取重要记忆"""
        pass
    
    def get_recent_memories(self, limit: int = 10) -> List[MemoryEntry]:
        """获取最近记忆"""
        pass
    
    def compress_memories(self, session_id: str = None) -> Dict[str, Any]:
        """压缩记忆"""
        pass
    
    def forget_old_memories(self, days_threshold: int = 30) -> Dict[str, Any]:
        """遗忘旧记忆"""
        pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        pass
```

## 3. 验证策略

### 3.1 功能验证

#### 3.1.1 记忆存储验证
- **测试用例**：
  1. 存储单条记忆
  2. 批量存储记忆
  3. 存储不同类型记忆
  4. 存储带标签的记忆
  5. 存储带元数据的记忆

- **验证指标**：
  - 存储成功率：100%
  - 数据完整性：100%
  - 存储性能：<100ms/条

#### 3.1.2 记忆检索验证
- **测试用例**：
  1. 语义相似度检索
  2. 时间范围检索
  3. 标签组合检索
  4. 重要性筛选检索
  5. 混合条件检索

- **验证指标**：
  - 检索准确率：>80%
  - 检索召回率：>70%
  - 检索性能：<50ms/次

#### 3.1.3 记忆组织验证
- **测试用例**：
  1. 自动标签生成
  2. 重要性自动评分
  3. 记忆分类
  4. 关联关系建立

- **验证指标**：
  - 标签准确率：>70%
  - 重要性评分合理性：人工评估
  - 分类准确率：>75%

#### 3.1.4 遗忘机制验证
- **测试用例**：
  1. 基于时间的遗忘
  2. 基于重要性的遗忘
  3. 基于访问频率的遗忘
  4. 遗忘后检索不受影响

- **验证指标**：
  - 遗忘合理性：人工评估
  - 存储空间减少：>30%
  - 检索质量不下降：<5%

### 3.2 兼容性验证

#### 3.2.1 接口兼容性
- **测试用例**：
  1. get_context 接口
  2. add_message 接口
  3. set_persona 接口
  4. clear 接口
  5. session_count 接口

- **验证指标**：
  - 接口签名一致：100%
  - 返回格式一致：100%
  - 行为一致：100%

#### 3.2.2 数据格式兼容性
- **测试用例**：
  1. 消息格式
  2. 会话格式
  3. 人设格式

- **验证指标**：
  - 数据格式一致：100%
  - 数据迁移无损：100%

#### 3.2.3 性能兼容性
- **测试用例**：
  1. 响应时间对比
  2. 内存使用对比
  3. 并发性能对比

- **验证指标**：
  - 响应时间差异：<20%
  - 内存使用差异：<30%
  - 并发性能差异：<20%

### 3.3 消融实验

#### 3.3.1 实验设计
**基线**：无记忆系统
- 每次对话从头开始
- 不利用历史信息
- 简单的会话管理

**增强**：有记忆系统
- 利用历史记忆
- 智能检索相关记忆
- 自动组织和遗忘

#### 3.3.2 测试场景
1. **连续对话场景**
   - 基线：每次对话独立
   - 增强：利用对话历史

2. **知识问答场景**
   - 基线：每次问答独立
   - 增强：利用历史问答

3. **任务执行场景**
   - 基线：每次任务独立
   - 增强：利用历史任务经验

#### 3.3.3 测量指标
1. **对话质量**
   - 回答准确率
   - 回答相关性
   - 用户满意度

2. **响应时间**
   - 首次响应时间
   - 平均响应时间

3. **资源消耗**
   - 存储空间
   - 计算资源

### 3.4 价值验证

#### 3.4.1 开发效率提升
- **测量指标**：
  - 代码行数减少
  - 开发时间减少
  - 维护成本降低

#### 3.4.2 运行时效率提升
- **测量指标**：
  - 响应时间减少
  - 缓存命中率
  - 资源利用率

#### 3.4.3 功能完整性提升
- **测量指标**：
  - 新增功能数量
  - 功能覆盖度
  - 用户满意度

#### 3.4.4 用户体验提升
- **测量指标**：
  - 对话连贯性
  - 个性化程度
  - 知识积累效果

## 4. 实现路线图

### 4.1 阶段1：核心框架（2-3天）
1. 创建模块目录结构
2. 实现数据模型
3. 实现存储引擎
4. 实现基本CRUD操作

### 4.2 阶段2：检索引擎（2-3天）
1. 实现语义检索
2. 实现时间检索
3. 实现标签检索
4. 实现混合检索

### 4.3 阶段3：组织管理（1-2天）
1. 实现自动标签
2. 实现重要性评分
3. 实现记忆分类

### 4.4 阶段4：高级功能（2-3天）
1. 实现遗忘机制
2. 实现压缩机制
3. 实现记忆总结

### 4.5 阶段5：验证测试（2-3天）
1. 实现功能验证
2. 实现兼容性验证
3. 实现消融实验
4. 实现价值验证

## 5. 预期成果

### 5.1 技术成果
1. 完整的记忆系统模块
2. 100% API 覆盖
3. 100% 兼容性
4. 完整的验证框架

### 5.2 业务价值
1. 对话质量提升：>20%
2. 响应时间减少：>30%
3. 用户满意度提升：>25%
4. 知识积累效果：可量化

### 5.3 验证报告
1. 功能验证报告
2. 兼容性验证报告
3. 消融实验报告
4. 价值验证报告
