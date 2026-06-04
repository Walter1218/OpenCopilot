# skill_architecture/models.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class SkillStatus(Enum):
    """Skill 状态"""
    INITIALIZED = "initialized"      # 已初始化
    RUNNING = "running"              # 运行中
    COMPLETED = "completed"          # 已完成
    FAILED = "failed"                # 失败
    CANCELLED = "cancelled"          # 已取消


class ExecutionMode(Enum):
    """执行模式"""
    SINGLE = "single"                # 单 Skill 执行
    SEQUENTIAL = "sequential"        # 顺序执行多个 Skill
    PARALLEL = "parallel"            # 并行执行多个 Skill
    PIPELINE = "pipeline"            # 流水线执行


@dataclass
class SkillMetadata:
    """Skill 元数据"""
    name: str                        # Skill 名称
    version: str                     # 版本号
    description: str                 # 描述
    author: str = ""                 # 作者
    category: str = ""               # 类别 (coding/knowledge/ppt/evaluation/file/format/persona)
    tags: List[str] = field(default_factory=list)  # 标签
    intents: List[str] = field(default_factory=list)  # 支持的意图
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他 Skill
    config_schema: Dict[str, Any] = field(default_factory=dict)  # 配置模式
    input_schema: Dict[str, Any] = field(default_factory=dict)   # 输入模式
    output_schema: Dict[str, Any] = field(default_factory=dict)  # 输出模式


@dataclass
class SkillContext:
    """Skill 执行上下文"""
    intent: str                      # 用户意图
    input_data: Dict[str, Any]       # 输入数据
    config: Dict[str, Any] = field(default_factory=dict)  # 配置
    session_id: Optional[str] = None  # 会话 ID
    user_id: Optional[str] = None     # 用户 ID
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    chain_results: List[Dict[str, Any]] = field(default_factory=list)  # 链式执行结果


@dataclass
class SkillResult:
    """Skill 执行结果"""
    success: bool                    # 是否成功
    data: Dict[str, Any]             # 结果数据
    error: Optional[str] = None      # 错误信息
    status: SkillStatus = SkillStatus.COMPLETED  # 状态
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    next_skills: List[str] = field(default_factory=list)  # 建议的下一步 Skill


@dataclass
class ExecutionPlan:
    """执行计划"""
    mode: ExecutionMode              # 执行模式
    skills: List[str]                # 要执行的 Skill 列表
    dependencies: Dict[str, List[str]] = field(default_factory=dict)  # 依赖关系
    parallel_groups: List[List[str]] = field(default_factory=list)  # 并行组
    timeout: int = 30                # 超时时间（秒）
    retry_count: int = 3             # 重试次数