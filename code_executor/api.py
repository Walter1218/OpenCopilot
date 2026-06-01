# code_executor/api.py

"""
代码执行引擎 RESTful API 端点
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .models import (
    ExecutorConfig, SandboxConfig, ExecutionResult,
    ValidationResult, LanguageInfo, ExecutionStatus
)
from .core import CodeExecutor


# Pydantic 模型（用于 API 请求/响应）

class ExecuteCodeRequest(BaseModel):
    """执行代码请求"""
    code: str = Field(..., description="要执行的代码")
    language: str = Field(..., description="编程语言")
    timeout: Optional[float] = Field(None, description="超时时间（秒）")
    working_directory: Optional[str] = Field(None, description="工作目录")
    env_vars: Optional[Dict[str, str]] = Field(None, description="环境变量")
    input_data: Optional[str] = Field(None, description="标准输入数据")
    use_sandbox: bool = Field(True, description="是否使用沙盒")


class SandboxExecuteRequest(BaseModel):
    """沙盒执行请求"""
    code: str = Field(..., description="要执行的代码")
    language: str = Field(..., description="编程语言")
    sandbox_config: Optional[SandboxConfig] = Field(None, description="沙盒配置")
    timeout: Optional[float] = Field(None, description="超时时间（秒）")


class ValidateCodeRequest(BaseModel):
    """验证代码请求"""
    code: str = Field(..., description="要验证的代码")
    language: str = Field(..., description="编程语言")


class InstallPackageRequest(BaseModel):
    """安装包请求"""
    package: str = Field(..., description="包名")
    language: str = Field(..., description="编程语言")


class ExecutionResultResponse(BaseModel):
    """执行结果响应"""
    execution_id: str
    request_id: str
    success: bool
    status: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0
    memory_usage_mb: float = 0.0
    artifacts: List[str] = []
    error: Optional[str] = None
    language: str = ""


class ValidationResultResponse(BaseModel):
    """验证结果响应"""
    valid: bool
    language: str
    errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []
    syntax_valid: bool = True
    security_issues: List[str] = []


class LanguageInfoResponse(BaseModel):
    """语言信息响应"""
    language: str
    version: str
    available: bool
    executable: str
    file_extension: str
    syntax_check_cmd: Optional[str] = None
    package_manager: Optional[str] = None


class StatsResponse(BaseModel):
    """统计响应"""
    total_executions: int
    successful_executions: int
    failed_executions: int
    timeout_executions: int
    total_duration_ms: float
    avg_duration_ms: float
    success_rate: float


class StatusResponse(BaseModel):
    """状态响应"""
    status: str
    config: Dict[str, Any]
    supported_languages: List[Dict[str, Any]]
    active_sandboxes: int
    stats: Dict[str, Any]


def create_executor_router(executor: CodeExecutor) -> APIRouter:
    """
    创建代码执行引擎 API 路由器
    
    Args:
        executor: 代码执行引擎实例
        
    Returns:
        APIRouter: 路由器
    """
    router = APIRouter(prefix="/api/executor", tags=["executor"])
    
    @router.post("/execute", response_model=ExecutionResultResponse)
    async def execute_code(request: ExecuteCodeRequest):
        """执行代码"""
        result = await executor.execute_code(
            code=request.code,
            language=request.language,
            timeout=request.timeout,
            working_directory=request.working_directory,
            env_vars=request.env_vars,
            input_data=request.input_data,
            use_sandbox=request.use_sandbox
        )
        
        return ExecutionResultResponse(
            execution_id=result.execution_id,
            request_id=result.request_id,
            success=result.success,
            status=result.status.value,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            memory_usage_mb=result.memory_usage_mb,
            artifacts=result.artifacts,
            error=result.error,
            language=result.language
        )
    
    @router.post("/sandbox", response_model=ExecutionResultResponse)
    async def execute_in_sandbox(request: SandboxExecuteRequest):
        """在沙盒中执行代码"""
        result = await executor.execute_in_sandbox(
            code=request.code,
            language=request.language,
            sandbox_config=request.sandbox_config,
            timeout=request.timeout
        )
        
        return ExecutionResultResponse(
            execution_id=result.execution_id,
            request_id=result.request_id,
            success=result.success,
            status=result.status.value,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            memory_usage_mb=result.memory_usage_mb,
            artifacts=result.artifacts,
            error=result.error,
            language=result.language
        )
    
    @router.post("/validate", response_model=ValidationResultResponse)
    async def validate_code(request: ValidateCodeRequest):
        """验证代码"""
        result = await executor.validate_code(
            code=request.code,
            language=request.language
        )
        
        return ValidationResultResponse(
            valid=result.valid,
            language=result.language,
            errors=result.errors,
            warnings=result.warnings,
            suggestions=result.suggestions,
            syntax_valid=result.syntax_valid,
            security_issues=result.security_issues
        )
    
    @router.get("/languages", response_model=List[LanguageInfoResponse])
    async def get_supported_languages():
        """获取支持的语言"""
        languages = await executor.get_supported_languages()
        
        return [
            LanguageInfoResponse(
                language=lang.language,
                version=lang.version,
                available=lang.available,
                executable=lang.executable,
                file_extension=lang.file_extension,
                syntax_check_cmd=lang.syntax_check_cmd,
                package_manager=lang.package_manager
            )
            for lang in languages
        ]
    
    @router.post("/install")
    async def install_package(request: InstallPackageRequest):
        """安装包"""
        success = await executor.install_package(
            package=request.package,
            language=request.language
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to install package: {request.package}"
            )
        
        return {"status": "success", "message": f"Package {request.package} installed"}
    
    @router.get("/status", response_model=StatusResponse)
    async def get_status():
        """获取执行器状态"""
        status = await executor.get_status()
        return StatusResponse(**status)
    
    @router.get("/stats", response_model=StatsResponse)
    async def get_stats():
        """获取统计信息"""
        stats = executor.get_stats()
        return StatsResponse(**stats)
    
    @router.get("/logs")
    async def get_execution_logs(
        language: Optional[str] = Query(None, description="按语言过滤"),
        limit: int = Query(100, description="返回数量限制")
    ):
        """获取执行日志"""
        logs = executor.get_execution_logs(
            language=language,
            limit=limit
        )
        
        return [
            {
                "log_id": log.log_id,
                "execution_id": log.execution_id,
                "request_id": log.request_id,
                "language": log.language,
                "code_snippet": log.code_snippet,
                "start_time": log.start_time,
                "end_time": log.end_time,
                "duration_ms": log.duration_ms,
                "success": log.success,
                "exit_code": log.exit_code,
                "error": log.error,
                "user_id": log.user_id,
                "session_id": log.session_id
            }
            for log in logs
        ]
    
    return router
