# code_executor/models.py

"""
代码执行引擎数据模型定义
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import uuid


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"       # 等待执行
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"   # 完成
    FAILED = "failed"         # 失败
    TIMEOUT = "timeout"       # 超时
    CANCELLED = "cancelled"   # 取消


class LanguageType(Enum):
    """支持的编程语言类型"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    SHELL = "shell"
    BASH = "bash"
    POWERSHELL = "powershell"


@dataclass
class ExecutorConfig:
    """执行器配置"""
    # 默认超时时间（秒）
    default_timeout: float = 30.0
    # 最大超时时间（秒）
    max_timeout: float = 300.0
    # 最大内存限制（MB）
    max_memory_mb: int = 512
    # 最大输出大小（字节）
    max_output_size: int = 1024 * 1024  # 1MB
    # 是否启用沙盒
    enable_sandbox: bool = True
    # 允许的编程语言
    allowed_languages: List[str] = field(default_factory=lambda: [
        "python", "javascript", "typescript", "shell", "bash"
    ])
    # 工作目录
    working_directory: Optional[str] = None
    # 环境变量
    env_vars: Dict[str, str] = field(default_factory=dict)


@dataclass
class SandboxConfig:
    """沙盒配置"""
    # 资源限制
    max_memory_mb: int = 512
    max_cpu_percent: float = 100.0
    max_disk_mb: int = 1024
    timeout: float = 30.0
    
    # 网络限制
    allow_network: bool = False
    allowed_hosts: List[str] = field(default_factory=list)
    
    # 文件系统限制
    read_only_paths: List[str] = field(default_factory=lambda: ["/"])
    writable_paths: List[str] = field(default_factory=lambda: ["/tmp"])
    
    # 环境变量
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    # 是否隔离进程
    isolate_process: bool = True
    
    # 是否限制系统调用
    restrict_syscalls: bool = True


@dataclass
class CodeExecutionRequest:
    """代码执行请求"""
    code: str                                  # 要执行的代码
    language: str                              # 编程语言
    request_id: Optional[str] = None           # 请求 ID
    timeout: Optional[float] = None            # 超时时间
    sandbox_config: Optional[SandboxConfig] = None  # 沙盒配置
    working_directory: Optional[str] = None    # 工作目录
    env_vars: Optional[Dict[str, str]] = None  # 环境变量
    input_data: Optional[str] = None           # 标准输入数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化请求 ID"""
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())


@dataclass
class ExecutionResult:
    """执行结果"""
    execution_id: str                          # 执行 ID
    request_id: str                            # 请求 ID
    success: bool                              # 是否成功
    status: ExecutionStatus                    # 执行状态
    stdout: str = ""                           # 标准输出
    stderr: str = ""                           # 标准错误
    exit_code: int = 0                         # 退出码
    duration_ms: float = 0.0                   # 执行耗时（毫秒）
    memory_usage_mb: float = 0.0               # 内存使用（MB）
    artifacts: List[str] = field(default_factory=list)  # 生成的文件
    error: Optional[str] = None                # 错误信息
    language: str = ""                         # 编程语言
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化执行 ID"""
        if not self.execution_id:
            self.execution_id = str(uuid.uuid4())


@dataclass
class ValidationResult:
    """代码验证结果"""
    valid: bool                                # 是否有效
    language: str                              # 编程语言
    errors: List[str] = field(default_factory=list)      # 错误列表
    warnings: List[str] = field(default_factory=list)    # 警告列表
    suggestions: List[str] = field(default_factory=list) # 建议列表
    syntax_valid: bool = True                  # 语法是否有效
    security_issues: List[str] = field(default_factory=list)  # 安全问题


@dataclass
class LanguageInfo:
    """编程语言信息"""
    language: str                              # 语言名称
    version: str                               # 版本
    available: bool                            # 是否可用
    executable: str                            # 可执行文件路径
    file_extension: str                        # 文件扩展名
    syntax_check_cmd: Optional[str] = None     # 语法检查命令
    package_manager: Optional[str] = None      # 包管理器


@dataclass
class ExecutionLog:
    """执行日志"""
    log_id: str
    execution_id: str
    request_id: str
    language: str
    code_snippet: str                          # 代码片段（前 500 字符）
    start_time: float
    end_time: float
    duration_ms: float
    success: bool
    exit_code: int
    error: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


def generate_execution_id() -> str:
    """生成执行 ID"""
    return str(uuid.uuid4())


def generate_request_id() -> str:
    """生成请求 ID"""
    return str(uuid.uuid4())
