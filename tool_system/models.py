# tool_system/models.py

"""
工具系统数据模型定义
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import json
import uuid


class ToolType(Enum):
    """工具类型"""
    SKILL = "skill"           # 内部 Skill
    HTTP_API = "http_api"     # HTTP API
    CLI = "cli"               # CLI 工具
    MCP = "mcp"               # MCP 工具
    FUNCTION = "function"     # Python 函数


class ToolCategory(Enum):
    """工具类别"""
    CODE = "code"             # 代码相关
    FILE = "file"             # 文件操作
    WEB = "web"               # 网络相关
    KNOWLEDGE = "knowledge"   # 知识检索
    SYSTEM = "system"         # 系统工具
    AI = "ai"                 # AI/LLM 相关
    CUSTOM = "custom"         # 自定义工具


class ToolStatus(Enum):
    """工具状态"""
    AVAILABLE = "available"   # 可用
    BUSY = "busy"             # 忙碌
    DISABLED = "disabled"     # 禁用
    ERROR = "error"           # 错误


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str                          # 参数名
    type: str                          # 类型：string, number, boolean, object, array
    description: str = ""              # 描述
    required: bool = False             # 是否必需
    default: Any = None                # 默认值
    enum: Optional[List[Any]] = None   # 枚举值
    schema: Optional[Dict] = None      # JSON Schema（复杂类型）


@dataclass
class ToolDefinition:
    """工具定义"""
    tool_id: str                              # 工具唯一 ID
    name: str                                 # 工具名称
    description: str                          # 描述
    tool_type: ToolType = ToolType.FUNCTION   # 工具类型
    category: ToolCategory = ToolCategory.CUSTOM  # 类别
    version: str = "1.0.0"                    # 版本
    author: str = ""                          # 作者
    parameters: List[ToolParameter] = field(default_factory=list)  # 参数列表
    output_schema: Optional[Dict] = None      # 输出格式
    requires_approval: bool = False           # 是否需要审批
    timeout: float = 30.0                     # 超时时间（秒）
    retry_count: int = 3                      # 重试次数
    tags: List[str] = field(default_factory=list)  # 标签
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

    def __post_init__(self):
        """验证工具定义"""
        if not self.tool_id:
            raise ValueError("Tool ID is required")
        if not self.name:
            raise ValueError("Tool name is required")
        if not self.description:
            raise ValueError("Tool description is required")


@dataclass
class ToolCall:
    """工具调用请求"""
    tool_id: str                              # 工具 ID
    parameters: Dict[str, Any] = field(default_factory=dict)  # 参数
    call_id: Optional[str] = None             # 调用 ID（用于追踪）
    timeout: Optional[float] = None           # 覆盖默认超时
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

    def __post_init__(self):
        """初始化调用 ID"""
        if self.call_id is None:
            self.call_id = str(uuid.uuid4())


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_call_id: str                         # 调用 ID
    tool_id: str                              # 工具 ID
    tool_name: str                            # 工具名称
    success: bool                             # 是否成功
    output: Any = None                        # 输出数据
    error: Optional[str] = None               # 错误信息
    duration_ms: float = 0.0                  # 执行耗时（毫秒）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    artifacts: List[str] = field(default_factory=list)  # 生成的文件/资源


@dataclass
class ToolExecutionLog:
    """工具执行日志"""
    log_id: str
    tool_id: str
    tool_name: str
    call_id: str
    parameters: Dict[str, Any]
    result: Optional[ToolResult]
    start_time: float
    end_time: float
    duration_ms: float
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    error: Optional[str] = None
