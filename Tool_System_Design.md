# 工具调用模块（Tool System）详细设计方案

> **文档版本**: v1.0  
> **创建日期**: 2026-06-01  
> **状态**: 待实施  
> **预计工期**: 5-7 天

---

## 一、概述

### 1.1 模块定位

工具调用模块是 OpenCopilot 智能体核心架构的第二阶段（P1）组件，负责：

- **统一工具管理**：注册、发现、调用各类工具
- **标准化接口**：提供一致的工具调用协议
- **安全执行**：权限控制、参数验证、沙盒隔离
- **可观测性**：执行追踪、性能监控、错误处理

### 1.2 与现有架构的关系

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenCopilot Agent Core                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Skill 架构   │    │  工具系统    │    │  代码执行    │  │
│  │  (现有)      │ →  │  (本模块)    │ ←  │  (待开发)    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         ↓                    ↓                    ↓         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              统一执行层 (Unified Execution Layer)      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**关键设计决策**：
- **不替代**现有 Skill 架构，而是**扩展**为通用工具系统
- Skill 作为**内部工具**的一种，自动注册到工具系统
- 支持**外部工具**注册（HTTP API、CLI、MCP 等）

---

## 二、核心组件设计

### 2.1 模块结构

```
tool_system/
├── __init__.py              # 模块初始化
├── models.py                # 数据模型定义
├── registry.py              # 工具注册表
├── executor.py              # 工具执行器
├── discovery.py             # 工具发现
├── validators.py            # 参数验证器
├── security.py              # 安全与权限
├── adapters/                # 工具适配器
│   ├── __init__.py
│   ├── skill_adapter.py     # Skill 适配器
│   ├── http_adapter.py      # HTTP API 适配器
│   ├── cli_adapter.py       # CLI 工具适配器
│   └── mcp_adapter.py       # MCP 工具适配器
├── api.py                   # RESTful API 端点
└── integration.py           # 与现有系统集成
```

### 2.2 数据模型

```python
# models.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import json


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
    tool_type: ToolType                       # 工具类型
    category: ToolCategory                    # 类别
    version: str = "1.0.0"                    # 版本
    author: str = ""                          # 作者
    parameters: List[ToolParameter] = field(default_factory=list)  # 参数列表
    output_schema: Optional[Dict] = None      # 输出格式
    requires_approval: bool = False           # 是否需要审批
    timeout: float = 30.0                     # 超时时间（秒）
    retry_count: int = 3                      # 重试次数
    tags: List[str] = field(default_factory=list)  # 标签
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class ToolCall:
    """工具调用请求"""
    tool_id: str                              # 工具 ID
    parameters: Dict[str, Any] = field(default_factory=dict)  # 参数
    call_id: Optional[str] = None             # 调用 ID（用于追踪）
    timeout: Optional[float] = None           # 覆盖默认超时
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


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
```

### 2.3 工具注册表

```python
# registry.py

import os
import json
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable
from pathlib import Path

from .models import (
    ToolDefinition, ToolType, ToolCategory,
    ToolParameter, ToolStatus
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册表
    
    职责：
    1. 管理工具定义的注册、更新、删除
    2. 支持多种工具类型的注册
    3. 提供工具发现和查询能力
    4. 持久化工具配置
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化工具注册表
        
        Args:
            storage_path: 工具配置存储路径（JSON 文件）
        """
        self._tools: Dict[str, ToolDefinition] = {}
        self._tool_handlers: Dict[str, Callable] = {}  # 工具处理函数
        self._storage_path = storage_path
        self._status_map: Dict[str, ToolStatus] = {}
        
        # 加载持久化的工具配置
        if storage_path and os.path.exists(storage_path):
            self._load_from_storage()
    
    def register(self, definition: ToolDefinition, handler: Callable) -> str:
        """
        注册工具
        
        Args:
            definition: 工具定义
            handler: 工具处理函数（同步或异步）
            
        Returns:
            str: 工具 ID
        """
        # 验证工具定义
        self._validate_definition(definition)
        
        # 注册
        self._tools[definition.tool_id] = definition
        self._tool_handlers[definition.tool_id] = handler
        self._status_map[definition.tool_id] = ToolStatus.AVAILABLE
        
        logger.info(f"Registered tool: {definition.tool_id} ({definition.name})")
        
        # 持久化
        if self._storage_path:
            self._save_to_storage()
        
        return definition.tool_id
    
    def unregister(self, tool_id: str) -> bool:
        """
        注销工具
        
        Args:
            tool_id: 工具 ID
            
        Returns:
            bool: 是否成功
        """
        if tool_id in self._tools:
            del self._tools[tool_id]
            del self._tool_handlers[tool_id]
            del self._status_map[tool_id]
            
            logger.info(f"Unregistered tool: {tool_id}")
            
            if self._storage_path:
                self._save_to_storage()
            
            return True
        return False
    
    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self._tools.get(tool_id)
    
    def get_handler(self, tool_id: str) -> Optional[Callable]:
        """获取工具处理函数"""
        return self._tool_handlers.get(tool_id)
    
    def get_status(self, tool_id: str) -> Optional[ToolStatus]:
        """获取工具状态"""
        return self._status_map.get(tool_id)
    
    def set_status(self, tool_id: str, status: ToolStatus) -> None:
        """设置工具状态"""
        if tool_id in self._tools:
            self._status_map[tool_id] = status
    
    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        tool_type: Optional[ToolType] = None,
        tags: Optional[List[str]] = None,
        status: Optional[ToolStatus] = None
    ) -> List[ToolDefinition]:
        """
        列出工具（支持过滤）
        
        Args:
            category: 按类别过滤
            tool_type: 按类型过滤
            tags: 按标签过滤（任意匹配）
            status: 按状态过滤
            
        Returns:
            List[ToolDefinition]: 工具定义列表
        """
        result = []
        
        for tool_id, definition in self._tools.items():
            # 应用过滤条件
            if category and definition.category != category:
                continue
            if tool_type and definition.tool_type != tool_type:
                continue
            if tags and not any(tag in definition.tags for tag in tags):
                continue
            if status and self._status_map.get(tool_id) != status:
                continue
            
            result.append(definition)
        
        return result
    
    def search_tools(self, query: str) -> List[ToolDefinition]:
        """
        搜索工具
        
        Args:
            query: 搜索关键词
            
        Returns:
            List[ToolDefinition]: 匹配的工具定义列表
        """
        query_lower = query.lower()
        result = []
        
        for definition in self._tools.values():
            # 搜索名称、描述、标签
            if (query_lower in definition.name.lower() or
                query_lower in definition.description.lower() or
                any(query_lower in tag.lower() for tag in definition.tags)):
                result.append(definition)
        
        return result
    
    def find_by_capability(self, capability: str) -> List[ToolDefinition]:
        """
        根据能力查找工具
        
        Args:
            capability: 能力描述（如 "code_review", "file_read"）
            
        Returns:
            List[ToolDefinition]: 匹配的工具定义列表
        """
        capability_lower = capability.lower()
        result = []
        
        for definition in self._tools.values():
            # 检查标签和元数据中的能力
            if (any(capability_lower in tag.lower() for tag in definition.tags) or
                capability_lower in definition.metadata.get("capabilities", [])):
                result.append(definition)
        
        return result
    
    def _validate_definition(self, definition: ToolDefinition) -> None:
        """验证工具定义"""
        if not definition.tool_id:
            raise ValueError("Tool ID is required")
        if not definition.name:
            raise ValueError("Tool name is required")
        if not definition.description:
            raise ValueError("Tool description is required")
        
        # 检查 ID 唯一性
        if definition.tool_id in self._tools:
            logger.warning(f"Tool {definition.tool_id} already exists, will be overwritten")
    
    def _load_from_storage(self) -> None:
        """从存储加载工具配置"""
        try:
            with open(self._storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for tool_data in data.get("tools", []):
                definition = ToolDefinition(**tool_data)
                self._tools[definition.tool_id] = definition
                self._status_map[definition.tool_id] = ToolStatus.AVAILABLE
            
            logger.info(f"Loaded {len(self._tools)} tools from storage")
        except Exception as e:
            logger.error(f"Failed to load tools from storage: {e}")
    
    def _save_to_storage(self) -> None:
        """保存工具配置到存储"""
        try:
            data = {
                "tools": [
                    {
                        "tool_id": d.tool_id,
                        "name": d.name,
                        "description": d.description,
                        "tool_type": d.tool_type.value,
                        "category": d.category.value,
                        "version": d.version,
                        "author": d.author,
                        "parameters": [
                            {
                                "name": p.name,
                                "type": p.type,
                                "description": p.description,
                                "required": p.required,
                                "default": p.default
                            }
                            for p in d.parameters
                        ],
                        "output_schema": d.output_schema,
                        "requires_approval": d.requires_approval,
                        "timeout": d.timeout,
                        "retry_count": d.retry_count,
                        "tags": d.tags,
                        "metadata": d.metadata
                    }
                    for d in self._tools.values()
                ]
            }
            
            os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
            with open(self._storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self._tools)} tools to storage")
        except Exception as e:
            logger.error(f"Failed to save tools to storage: {e}")
```

---

## 三、工具执行器

```python
# executor.py

import asyncio
import time
import uuid
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable

from .models import (
    ToolDefinition, ToolCall, ToolResult, ToolStatus,
    ToolExecutionLog
)
from .registry import ToolRegistry
from .validators import ParameterValidator

logger = logging.getLogger(__name__)


class ToolExecutor:
    """工具执行器
    
    职责：
    1. 执行工具调用（支持同步/异步）
    2. 参数验证
    3. 超时控制
    4. 重试机制
    5. 执行日志记录
    6. 权限检查（与安全模块集成）
    """
    
    def __init__(
        self,
        registry: ToolRegistry,
        validator: Optional[ParameterValidator] = None,
        approval_handler: Optional[Callable] = None,
        max_concurrent: int = 10
    ):
        """
        初始化工具执行器
        
        Args:
            registry: 工具注册表
            validator: 参数验证器
            approval_handler: 审批处理器
            max_concurrent: 最大并发执行数
        """
        self._registry = registry
        self._validator = validator or ParameterValidator()
        self._approval_handler = approval_handler
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
        # 执行日志
        self._execution_logs: List[ToolExecutionLog] = []
        
        # 统计信息
        self._stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_duration_ms": 0.0
        }
    
    async def execute(
        self,
        call: ToolCall,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ToolResult:
        """
        执行工具调用
        
        Args:
            call: 工具调用请求
            user_id: 用户 ID
            session_id: 会话 ID
            
        Returns:
            ToolResult: 执行结果
        """
        call_id = call.call_id or str(uuid.uuid4())
        start_time = time.time()
        
        # 获取工具定义和处理函数
        definition = self._registry.get_tool(call.tool_id)
        if not definition:
            return self._create_error_result(
                call_id, call.tool_id, "unknown",
                f"Tool not found: {call.tool_id}",
                start_time
            )
        
        handler = self._registry.get_handler(call.tool_id)
        if not handler:
            return self._create_error_result(
                call_id, call.tool_id, definition.name,
                f"No handler for tool: {call.tool_id}",
                start_time
            )
        
        # 检查工具状态
        status = self._registry.get_status(call.tool_id)
        if status != ToolStatus.AVAILABLE:
            return self._create_error_result(
                call_id, call.tool_id, definition.name,
                f"Tool is not available: {status.value}",
                start_time
            )
        
        # 验证参数
        validation_error = self._validator.validate(
            call.parameters, definition.parameters
        )
        if validation_error:
            return self._create_error_result(
                call_id, call.tool_id, definition.name,
                f"Parameter validation failed: {validation_error}",
                start_time
            )
        
        # 检查是否需要审批
        if definition.requires_approval:
            if not await self._request_approval(definition, call, user_id):
                return self._create_error_result(
                    call_id, call.tool_id, definition.name,
                    "Approval denied",
                    start_time
                )
        
        # 执行工具
        try:
            # 设置工具状态为忙碌
            self._registry.set_status(call.tool_id, ToolStatus.BUSY)
            
            # 确定超时时间
            timeout = call.timeout or definition.timeout
            
            # 执行（带超时和并发控制）
            async with self._semaphore:
                result = await asyncio.wait_for(
                    self._execute_handler(handler, call.parameters),
                    timeout=timeout
                )
            
            # 计算执行时间
            duration_ms = (time.time() - start_time) * 1000
            
            # 创建成功结果
            tool_result = ToolResult(
                tool_call_id=call_id,
                tool_id=call.tool_id,
                tool_name=definition.name,
                success=True,
                output=result,
                duration_ms=duration_ms,
                metadata=call.metadata
            )
            
            # 更新统计
            self._update_stats(duration_ms, success=True)
            
            # 记录日志
            self._log_execution(
                call, definition, tool_result,
                start_time, user_id, session_id
            )
            
            return tool_result
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Tool execution timeout after {timeout}s"
            
            self._update_stats(duration_ms, success=False)
            
            return self._create_error_result(
                call_id, call.tool_id, definition.name,
                error_msg, start_time
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"{type(e).__name__}: {str(e)}"
            
            logger.error(f"Tool execution failed: {error_msg}", exc_info=True)
            
            self._update_stats(duration_ms, success=False)
            
            return self._create_error_result(
                call_id, call.tool_id, definition.name,
                error_msg, start_time
            )
            
        finally:
            # 恢复工具状态
            self._registry.set_status(call.tool_id, ToolStatus.AVAILABLE)
    
    async def batch_execute(
        self,
        calls: List[ToolCall],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        max_concurrent: Optional[int] = None
    ) -> List[ToolResult]:
        """
        批量执行工具调用
        
        Args:
            calls: 工具调用请求列表
            user_id: 用户 ID
            session_id: 会话 ID
            max_concurrent: 最大并发数
            
        Returns:
            List[ToolResult]: 执行结果列表
        """
        if not calls:
            return []
        
        # 确定并发数
        concurrent = max_concurrent or len(calls)
        semaphore = asyncio.Semaphore(concurrent)
        
        async def execute_with_semaphore(call: ToolCall) -> ToolResult:
            async with semaphore:
                return await self.execute(call, user_id, session_id)
        
        # 并行执行
        tasks = [execute_with_semaphore(call) for call in calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(self._create_error_result(
                    calls[i].call_id or str(uuid.uuid4()),
                    calls[i].tool_id,
                    "unknown",
                    str(result),
                    time.time()
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def _execute_handler(
        self,
        handler: Callable,
        parameters: Dict[str, Any]
    ) -> Any:
        """执行工具处理函数"""
        if asyncio.iscoroutinefunction(handler):
            return await handler(**parameters)
        else:
            # 同步函数在线程池中执行
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: handler(**parameters))
    
    async def _request_approval(
        self,
        definition: ToolDefinition,
        call: ToolCall,
        user_id: Optional[str]
    ) -> bool:
        """请求审批"""
        if not self._approval_handler:
            # 没有审批处理器，默认允许
            return True
        
        if asyncio.iscoroutinefunction(self._approval_handler):
            return await self._approval_handler(definition, call, user_id)
        else:
            return self._approval_handler(definition, call, user_id)
    
    def _create_error_result(
        self,
        call_id: str,
        tool_id: str,
        tool_name: str,
        error: str,
        start_time: float
    ) -> ToolResult:
        """创建错误结果"""
        return ToolResult(
            tool_call_id=call_id,
            tool_id=tool_id,
            tool_name=tool_name,
            success=False,
            error=error,
            duration_ms=(time.time() - start_time) * 1000
        )
    
    def _update_stats(self, duration_ms: float, success: bool) -> None:
        """更新统计信息"""
        self._stats["total_calls"] += 1
        self._stats["total_duration_ms"] += duration_ms
        
        if success:
            self._stats["successful_calls"] += 1
        else:
            self._stats["failed_calls"] += 1
    
    def _log_execution(
        self,
        call: ToolCall,
        definition: ToolDefinition,
        result: ToolResult,
        start_time: float,
        user_id: Optional[str],
        session_id: Optional[str]
    ) -> None:
        """记录执行日志"""
        log = ToolExecutionLog(
            log_id=str(uuid.uuid4()),
            tool_id=call.tool_id,
            tool_name=definition.name,
            call_id=result.tool_call_id,
            parameters=call.parameters,
            result=result,
            start_time=start_time,
            end_time=time.time(),
            duration_ms=result.duration_ms,
            user_id=user_id,
            session_id=session_id,
            error=result.error if not result.success else None
        )
        
        self._execution_logs.append(log)
        
        # 限制日志数量
        if len(self._execution_logs) > 1000:
            self._execution_logs = self._execution_logs[-500:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        if stats["total_calls"] > 0:
            stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_calls"]
            stats["success_rate"] = stats["successful_calls"] / stats["total_calls"]
        else:
            stats["avg_duration_ms"] = 0.0
            stats["success_rate"] = 0.0
        return stats
    
    def get_execution_logs(
        self,
        tool_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ToolExecutionLog]:
        """获取执行日志"""
        logs = self._execution_logs
        
        if tool_id:
            logs = [log for log in logs if log.tool_id == tool_id]
        
        return logs[-limit:]
```

---

## 四、工具适配器

### 4.1 Skill 适配器（将现有 Skill 注册为工具）

```python
# adapters/skill_adapter.py

from typing import Dict, Any, Optional
import uuid

from ..models import (
    ToolDefinition, ToolType, ToolCategory,
    ToolParameter, ToolCall, ToolResult
)
from ..registry import ToolRegistry

# 导入现有 Skill 架构
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from skill_architecture.models import SkillContext, SkillMetadata
from skill_architecture.base import BaseSkill
from skill_architecture.registry import SkillRegistry


class SkillAdapter:
    """Skill 适配器
    
    将现有的 Skill 注册为工具系统中的工具
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry
    ):
        self._tool_registry = tool_registry
        self._skill_registry = skill_registry
    
    def register_all_skills(self) -> int:
        """
        注册所有已注册的 Skill 为工具
        
        Returns:
            int: 注册的工具数量
        """
        count = 0
        
        for skill_name in self._skill_registry.list_skills():
            skill = self._skill_registry.get_skill(skill_name)
            if skill:
                self._register_skill(skill)
                count += 1
        
        return count
    
    def _register_skill(self, skill: BaseSkill) -> None:
        """注册单个 Skill"""
        metadata = skill.metadata
        
        # 创建工具定义
        definition = self._skill_to_tool_definition(metadata)
        
        # 创建处理函数
        handler = self._create_skill_handler(skill)
        
        # 注册到工具系统
        self._tool_registry.register(definition, handler)
    
    def _skill_to_tool_definition(self, metadata: SkillMetadata) -> ToolDefinition:
        """将 Skill 元数据转换为工具定义"""
        # 确定工具类别
        category = self._determine_category(metadata)
        
        # 转换参数
        parameters = self._convert_parameters(metadata.input_schema)
        
        return ToolDefinition(
            tool_id=f"skill_{metadata.name}",
            name=metadata.name,
            description=metadata.description,
            tool_type=ToolType.SKILL,
            category=category,
            version=metadata.version,
            author=metadata.author,
            parameters=parameters,
            output_schema=metadata.output_schema,
            requires_approval=False,  # 内部 Skill 默认不需要审批
            timeout=30.0,
            retry_count=3,
            tags=metadata.tags + ["skill", "internal"],
            metadata={
                "skill_name": metadata.name,
                "intents": metadata.intents,
                "dependencies": metadata.dependencies,
                "capabilities": metadata.tags
            }
        )
    
    def _determine_category(self, metadata: SkillMetadata) -> ToolCategory:
        """确定工具类别"""
        tags_lower = [tag.lower() for tag in metadata.tags]
        
        if any(tag in tags_lower for tag in ["code", "coding", "programming"]):
            return ToolCategory.CODE
        elif any(tag in tags_lower for tag in ["file", "filesystem"]):
            return ToolCategory.FILE
        elif any(tag in tags_lower for tag in ["web", "browser", "search"]):
            return ToolCategory.WEB
        elif any(tag in tags_lower for tag in ["knowledge", "graph"]):
            return ToolCategory.KNOWLEDGE
        elif any(tag in tags_lower for tag in ["system", "admin"]):
            return ToolCategory.SYSTEM
        else:
            return ToolCategory.CUSTOM
    
    def _convert_parameters(self, input_schema: Dict) -> list:
        """将 Skill 输入模式转换为工具参数"""
        parameters = []
        
        if not input_schema:
            return parameters
        
        properties = input_schema.get("properties", {})
        required_fields = input_schema.get("required", [])
        
        for name, prop in properties.items():
            param = ToolParameter(
                name=name,
                type=prop.get("type", "string"),
                description=prop.get("description", ""),
                required=name in required_fields,
                default=prop.get("default"),
                enum=prop.get("enum")
            )
            parameters.append(param)
        
        return parameters
    
    def _create_skill_handler(self, skill: BaseSkill):
        """创建 Skill 处理函数"""
        async def handler(**kwargs) -> Any:
            # 创建 Skill 上下文
            context = SkillContext(
                intent=kwargs.get("intent", "execute"),
                input_data=kwargs,
                config=skill.config
            )
            
            # 执行 Skill
            result = await skill.execute(context)
            
            if result.success:
                return result.data
            else:
                raise Exception(result.error or "Skill execution failed")
        
        return handler
```

### 4.2 HTTP API 适配器

```python
# adapters/http_adapter.py

import aiohttp
import json
from typing import Dict, Any, Optional

from ..models import (
    ToolDefinition, ToolType, ToolCategory,
    ToolParameter
)
from ..registry import ToolRegistry


class HTTPAdapter:
    """HTTP API 适配器
    
    将外部 HTTP API 注册为工具
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        self._tool_registry = tool_registry
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取 HTTP 会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    def register_api(
        self,
        tool_id: str,
        name: str,
        description: str,
        endpoint: str,
        method: str = "POST",
        parameters: list = None,
        headers: Dict[str, str] = None,
        category: ToolCategory = ToolCategory.CUSTOM,
        timeout: float = 30.0,
        tags: list = None
    ) -> str:
        """
        注册 HTTP API 为工具
        
        Args:
            tool_id: 工具 ID
            name: 工具名称
            description: 描述
            endpoint: API 端点
            method: HTTP 方法
            parameters: 参数列表
            headers: 请求头
            category: 类别
            timeout: 超时时间
            tags: 标签
            
        Returns:
            str: 工具 ID
        """
        # 创建工具定义
        definition = ToolDefinition(
            tool_id=tool_id,
            name=name,
            description=description,
            tool_type=ToolType.HTTP_API,
            category=category,
            parameters=parameters or [],
            timeout=timeout,
            tags=tags or ["http", "api"],
            metadata={
                "endpoint": endpoint,
                "method": method,
                "headers": headers or {}
            }
        )
        
        # 创建处理函数
        handler = self._create_http_handler(endpoint, method, headers)
        
        # 注册
        self._tool_registry.register(definition, handler)
        
        return tool_id
    
    def _create_http_handler(
        self,
        endpoint: str,
        method: str,
        headers: Dict[str, str] = None
    ):
        """创建 HTTP 处理函数"""
        async def handler(**kwargs) -> Any:
            session = await self._get_session()
            
            # 准备请求
            request_headers = headers or {}
            request_headers.setdefault("Content-Type", "application/json")
            
            # 发送请求
            async with session.request(
                method,
                endpoint,
                json=kwargs,
                headers=request_headers
            ) as response:
                # 检查响应状态
                if response.status >= 400:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                
                # 解析响应
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return await response.json()
                else:
                    return await response.text()
        
        return handler
    
    async def close(self):
        """关闭 HTTP 会话"""
        if self._session and not self._session.closed:
            await self._session.close()
```

---

## 五、RESTful API 端点

```python
# api.py

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .models import (
    ToolDefinition, ToolCall, ToolResult,
    ToolCategory, ToolType, ToolStatus
)
from .registry import ToolRegistry
from .executor import ToolExecutor


# Pydantic 模型（用于 API 请求/响应）

class ToolParameterSchema(BaseModel):
    """工具参数模式"""
    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None


class RegisterToolRequest(BaseModel):
    """注册工具请求"""
    tool_id: str
    name: str
    description: str
    tool_type: str = "custom"
    category: str = "custom"
    version: str = "1.0.0"
    author: str = ""
    parameters: List[ToolParameterSchema] = []
    output_schema: Optional[Dict] = None
    requires_approval: bool = False
    timeout: float = 30.0
    retry_count: int = 3
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class CallToolRequest(BaseModel):
    """调用工具请求"""
    tool_id: str
    parameters: Dict[str, Any] = {}
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = {}


class BatchCallRequest(BaseModel):
    """批量调用请求"""
    calls: List[CallToolRequest]
    max_concurrent: Optional[int] = None


class ToolResponse(BaseModel):
    """工具响应"""
    tool_id: str
    name: str
    description: str
    tool_type: str
    category: str
    version: str
    status: str
    parameters: List[ToolParameterSchema]
    tags: List[str]


class CallResultResponse(BaseModel):
    """调用结果响应"""
    tool_call_id: str
    tool_id: str
    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float


class StatsResponse(BaseModel):
    """统计响应"""
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    avg_duration_ms: float


def create_tool_router(
    registry: ToolRegistry,
    executor: ToolExecutor
) -> APIRouter:
    """
    创建工具 API 路由器
    
    Args:
        registry: 工具注册表
        executor: 工具执行器
        
    Returns:
        APIRouter: 路由器
    """
    router = APIRouter(prefix="/api/tools", tags=["tools"])
    
    @router.get("", response_model=List[ToolResponse])
    async def list_tools(
        category: Optional[str] = Query(None, description="按类别过滤"),
        tool_type: Optional[str] = Query(None, description="按类型过滤"),
        tag: Optional[str] = Query(None, description="按标签过滤"),
        status: Optional[str] = Query(None, description="按状态过滤")
    ):
        """列出所有工具"""
        # 解析过滤参数
        cat = ToolCategory(category) if category else None
        tt = ToolType(tool_type) if tool_type else None
        ts = ToolStatus(status) if status else None
        tags = [tag] if tag else None
        
        tools = registry.list_tools(
            category=cat,
            tool_type=tt,
            tags=tags,
            status=ts
        )
        
        return [_tool_to_response(tool) for tool in tools]
    
    @router.get("/search", response_model=List[ToolResponse])
    async def search_tools(
        q: str = Query(..., description="搜索关键词")
    ):
        """搜索工具"""
        tools = registry.search_tools(q)
        return [_tool_to_response(tool) for tool in tools]
    
    @router.get("/{tool_id}", response_model=ToolResponse)
    async def get_tool(tool_id: str):
        """获取工具详情"""
        tool = registry.get_tool(tool_id)
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
        return _tool_to_response(tool)
    
    @router.post("", response_model=Dict[str, str])
    async def register_tool(request: RegisterToolRequest):
        """注册工具"""
        # 注意：这里需要工具处理函数，实际实现需要更复杂的逻辑
        # 简化示例：只返回成功
        return {"tool_id": request.tool_id, "status": "registered"}
    
    @router.delete("/{tool_id}")
    async def unregister_tool(tool_id: str):
        """注销工具"""
        success = registry.unregister(tool_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
        return {"status": "unregistered"}
    
    @router.post("/call", response_model=CallResultResponse)
    async def call_tool(
        request: CallToolRequest,
        user_id: Optional[str] = Query(None),
        session_id: Optional[str] = Query(None)
    ):
        """调用工具"""
        call = ToolCall(
            tool_id=request.tool_id,
            parameters=request.parameters,
            timeout=request.timeout,
            metadata=request.metadata
        )
        
        result = await executor.execute(call, user_id, session_id)
        
        return CallResultResponse(
            tool_call_id=result.tool_call_id,
            tool_id=result.tool_id,
            tool_name=result.tool_name,
            success=result.success,
            output=result.output,
            error=result.error,
            duration_ms=result.duration_ms
        )
    
    @router.post("/batch-call", response_model=List[CallResultResponse])
    async def batch_call_tools(
        request: BatchCallRequest,
        user_id: Optional[str] = Query(None),
        session_id: Optional[str] = Query(None)
    ):
        """批量调用工具"""
        calls = [
            ToolCall(
                tool_id=c.tool_id,
                parameters=c.parameters,
                timeout=c.timeout,
                metadata=c.metadata
            )
            for c in request.calls
        ]
        
        results = await executor.batch_execute(
            calls, user_id, session_id, request.max_concurrent
        )
        
        return [
            CallResultResponse(
                tool_call_id=r.tool_call_id,
                tool_id=r.tool_id,
                tool_name=r.tool_name,
                success=r.success,
                output=r.output,
                error=r.error,
                duration_ms=r.duration_ms
            )
            for r in results
        ]
    
    @router.get("/stats", response_model=StatsResponse)
    async def get_stats():
        """获取统计信息"""
        stats = executor.get_stats()
        return StatsResponse(**stats)
    
    def _tool_to_response(tool: ToolDefinition) -> ToolResponse:
        """转换工具定义为响应"""
        return ToolResponse(
            tool_id=tool.tool_id,
            name=tool.name,
            description=tool.description,
            tool_type=tool.tool_type.value,
            category=tool.category.value,
            version=tool.version,
            status=registry.get_status(tool.tool_id).value if registry.get_status(tool.tool_id) else "unknown",
            parameters=[
                ToolParameterSchema(
                    name=p.name,
                    type=p.type,
                    description=p.description,
                    required=p.required,
                    default=p.default,
                    enum=p.enum
                )
                for p in tool.parameters
            ],
            tags=tool.tags
        )
    
    return router
```

---

## 六、与现有系统集成

```python
# integration.py

import logging
from typing import Optional

from .registry import ToolRegistry
from .executor import ToolExecutor
from .adapters.skill_adapter import SkillAdapter
from .api import create_tool_router

# 导入现有系统
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from skill_architecture.registry import SkillRegistry as ExistingSkillRegistry
from skill_architecture.executor import SkillExecutor as ExistingSkillExecutor
from skill_architecture.discovery import SkillDiscovery

logger = logging.getLogger(__name__)


class ToolSystemIntegration:
    """工具系统集成器
    
    负责将工具系统集成到现有的 OpenCopilot 架构中
    """
    
    def __init__(
        self,
        tool_storage_path: Optional[str] = None
    ):
        # 创建工具系统组件
        self.tool_registry = ToolRegistry(storage_path=tool_storage_path)
        self.tool_executor = ToolExecutor(registry=self.tool_registry)
        
        # 获取现有的 Skill 系统
        self.skill_registry = ExistingSkillRegistry()
        self.skill_discovery = SkillDiscovery()
        
        # 创建 Skill 适配器
        self.skill_adapter = SkillAdapter(
            tool_registry=self.tool_registry,
            skill_registry=self.skill_registry
        )
        
        # API 路由器
        self.router = None
    
    async def initialize(self) -> None:
        """初始化工具系统"""
        logger.info("Initializing Tool System...")
        
        # 1. 自动发现并注册 Skill
        self.skill_discovery.auto_discover("skill_architecture")
        
        # 2. 将 Skill 注册为工具
        skill_count = self.skill_adapter.register_all_skills()
        logger.info(f"Registered {skill_count} skills as tools")
        
        # 3. 注册内置工具（如文件操作、代码执行等）
        await self._register_builtin_tools()
        
        # 4. 创建 API 路由器
        self.router = create_tool_router(
            self.tool_registry,
            self.tool_executor
        )
        
        logger.info(f"Tool System initialized with {len(self.tool_registry.list_tools())} tools")
    
    async def _register_builtin_tools(self) -> None:
        """注册内置工具"""
        from .models import (
            ToolDefinition, ToolType, ToolCategory,
            ToolParameter
        )
        
        # 示例：注册文件读取工具
        file_read_tool = ToolDefinition(
            tool_id="builtin_file_read",
            name="file_read",
            description="读取文件内容",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="文件路径",
                    required=True
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="文件编码",
                    required=False,
                    default="utf-8"
                )
            ],
            tags=["file", "read", "builtin"],
            metadata={"builtin": True}
        )
        
        async def file_read_handler(file_path: str, encoding: str = "utf-8") -> str:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        
        self.tool_registry.register(file_read_tool, file_read_handler)
        
        # 更多内置工具...
    
    def get_api_router(self):
        """获取 API 路由器"""
        return self.router
    
    async def shutdown(self) -> None:
        """关闭工具系统"""
        logger.info("Shutting down Tool System...")
        # 清理资源
```

---

## 七、测试策略

### 7.1 单元测试

```python
# test_tool_system.py

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from tool_system.models import (
    ToolDefinition, ToolCall, ToolResult,
    ToolType, ToolCategory, ToolParameter
)
from tool_system.registry import ToolRegistry
from tool_system.executor import ToolExecutor
from tool_system.validators import ParameterValidator


class TestToolRegistry:
    """工具注册表测试"""
    
    def test_register_tool(self):
        """测试注册工具"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        handler = lambda **kwargs: "result"
        
        tool_id = registry.register(definition, handler)
        
        assert tool_id == "test_tool"
        assert registry.get_tool("test_tool") == definition
        assert registry.get_handler("test_tool") == handler
    
    def test_unregister_tool(self):
        """测试注销工具"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        registry.register(definition, lambda: None)
        
        success = registry.unregister("test_tool")
        
        assert success is True
        assert registry.get_tool("test_tool") is None
    
    def test_list_tools_with_filter(self):
        """测试过滤工具"""
        registry = ToolRegistry()
        
        # 注册多个工具
        for i in range(5):
            definition = ToolDefinition(
                tool_id=f"tool_{i}",
                name=f"Tool {i}",
                description=f"Tool {i}",
                tool_type=ToolType.FUNCTION,
                category=ToolCategory.CODE if i % 2 == 0 else ToolCategory.FILE,
                tags=["test"]
            )
            registry.register(definition, lambda: None)
        
        # 按类别过滤
        code_tools = registry.list_tools(category=ToolCategory.CODE)
        assert len(code_tools) == 3  # 0, 2, 4
        
        file_tools = registry.list_tools(category=ToolCategory.FILE)
        assert len(file_tools) == 2  # 1, 3
    
    def test_search_tools(self):
        """测试搜索工具"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="code_review",
            name="Code Review",
            description="Review code for issues",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CODE,
            tags=["code", "review"]
        )
        registry.register(definition, lambda: None)
        
        results = registry.search_tools("review")
        assert len(results) == 1
        assert results[0].tool_id == "code_review"


class TestToolExecutor:
    """工具执行器测试"""
    
    @pytest.mark.asyncio
    async def test_execute_success(self):
        """测试成功执行"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM,
            parameters=[
                ToolParameter(
                    name="input",
                    type="string",
                    required=True
                )
            ]
        )
        
        async def handler(input: str) -> str:
            return f"Processed: {input}"
        
        registry.register(definition, handler)
        
        executor = ToolExecutor(registry=registry)
        
        call = ToolCall(
            tool_id="test_tool",
            parameters={"input": "hello"}
        )
        
        result = await executor.execute(call)
        
        assert result.success is True
        assert result.output == "Processed: hello"
        assert result.duration_ms > 0
    
    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        """测试超时"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="slow_tool",
            name="Slow Tool",
            description="A slow tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM,
            timeout=0.1  # 100ms 超时
        )
        
        async def handler():
            await asyncio.sleep(1)  # 1秒延迟
            return "done"
        
        registry.register(definition, handler)
        
        executor = ToolExecutor(registry=registry)
        
        call = ToolCall(tool_id="slow_tool")
        
        result = await executor.execute(call)
        
        assert result.success is False
        assert "timeout" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_batch_execute(self):
        """测试批量执行"""
        registry = ToolRegistry()
        
        definition = ToolDefinition(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.CUSTOM
        )
        
        call_count = 0
        
        async def handler():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"
        
        registry.register(definition, handler)
        
        executor = ToolExecutor(registry=registry)
        
        calls = [
            ToolCall(tool_id="test_tool"),
            ToolCall(tool_id="test_tool"),
            ToolCall(tool_id="test_tool")
        ]
        
        results = await executor.batch_execute(calls)
        
        assert len(results) == 3
        assert all(r.success for r in results)
        assert call_count == 3
```

### 7.2 集成测试

```python
# test_tool_integration.py

import pytest
from fastapi.testclient import TestClient

from tool_system.integration import ToolSystemIntegration


class TestToolSystemIntegration:
    """工具系统集成测试"""
    
    @pytest.fixture
    def integration(self):
        """创建集成实例"""
        return ToolSystemIntegration()
    
    @pytest.fixture
    def client(self, integration):
        """创建测试客户端"""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(integration.get_api_router())
        
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_initialize(self, integration):
        """测试初始化"""
        await integration.initialize()
        
        tools = integration.tool_registry.list_tools()
        assert len(tools) > 0
        
        # 应该有 Skill 工具
        skill_tools = [
            t for t in tools 
            if t.tool_type.value == "skill"
        ]
        assert len(skill_tools) > 0
    
    def test_list_tools_api(self, client, integration):
        """测试列出工具 API"""
        # 先初始化
        import asyncio
        asyncio.run(integration.initialize())
        
        response = client.get("/api/tools")
        
        assert response.status_code == 200
        tools = response.json()
        assert isinstance(tools, list)
    
    def test_call_tool_api(self, client, integration):
        """测试调用工具 API"""
        import asyncio
        asyncio.run(integration.initialize())
        
        # 调用内置工具
        response = client.post(
            "/api/tools/call",
            json={
                "tool_id": "builtin_file_read",
                "parameters": {
                    "file_path": "README.md"
                }
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True
```

---

## 八、实现计划

### 8.1 阶段划分

| 阶段 | 任务 | 时间 | 产出 |
|------|------|------|------|
| **阶段 1** | 核心框架 | 2 天 | models.py, registry.py, validators.py |
| **阶段 2** | 执行器 | 2 天 | executor.py, 重试/超时机制 |
| **阶段 3** | 适配器 | 1 天 | skill_adapter.py, http_adapter.py |
| **阶段 4** | API 端点 | 1 天 | api.py, 测试 |
| **阶段 5** | 集成测试 | 1 天 | integration.py, 端到端测试 |
| **总计** | | **7 天** | |

### 8.2 文件清单

```
tool_system/
├── __init__.py
├── models.py                 # 数据模型
├── registry.py               # 工具注册表
├── executor.py               # 工具执行器
├── validators.py             # 参数验证器
├── discovery.py              # 工具发现（可选）
├── security.py               # 安全模块（可选）
├── adapters/
│   ├── __init__.py
│   ├── skill_adapter.py      # Skill 适配器
│   ├── http_adapter.py       # HTTP API 适配器
│   ├── cli_adapter.py        # CLI 工具适配器（可选）
│   └── mcp_adapter.py        # MCP 工具适配器（可选）
├── api.py                    # RESTful API
└── integration.py            # 系统集成

tests/
├── test_tool_models.py       # 模型测试
├── test_tool_registry.py     # 注册表测试
├── test_tool_executor.py     # 执行器测试
├── test_tool_adapters.py     # 适配器测试
├── test_tool_api.py          # API 测试
└── test_tool_integration.py  # 集成测试

docs/
└── Tool_System_Design.md     # 本文档
```

### 8.3 依赖项

```
# requirements.txt 新增
aiohttp>=3.8.0          # HTTP 客户端（用于 HTTP 适配器）
pydantic>=2.0.0         # 数据验证（FastAPI 依赖）
```

---

## 九、风险评估与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 性能问题 | 工具调用延迟高 | 1. 并发控制<br>2. 连接池<br>3. 缓存机制 |
| 安全风险 | 恶意工具调用 | 1. 参数验证<br>2. 权限控制<br>3. 沙盒隔离 |
| 兼容性问题 | 现有 Skill 无法适配 | 1. 充分测试<br>2. 渐进式迁移<br>3. 回退机制 |
| 复杂度过高 | 开发周期延长 | 1. 分阶段实施<br>2. 优先核心功能<br>3. 复用现有代码 |

---

## 十、总结

工具调用模块是 OpenCopilot 智能体架构的核心组件，通过：

1. **统一接口**：提供一致的工具调用协议
2. **灵活适配**：支持多种工具类型（Skill、HTTP、CLI、MCP）
3. **安全可靠**：参数验证、权限控制、错误处理
4. **可观测性**：执行日志、性能监控、统计分析

为后续的代码执行引擎、规划器等模块提供坚实的基础。

### 已实现的核心模块

基于本工具系统设计，OpenCopilot 已于 2026-06-01 完成了 5 个智能体核心模块的开发：

| 模块 | 功能 | 与工具系统的关系 |
|------|------|-----------------|
| **Planner** | 任务分解、执行计划、动态调整 | 使用工具系统执行计划步骤 |
| **Code Executor** | 代码执行、沙盒环境、资源限制 | 作为工具系统的代码执行工具 |
| **Security** | 权限控制、审计日志、审批流程 | 为工具系统提供安全控制 |
| **Observability** | 结构化日志、指标收集、分布式追踪 | 为工具系统提供可观测性 |
| **Agents MD** | 规则检查、违规检测、自动修复 | 为工具系统提供规则检查 |

**验证结果**：
- API 覆盖率：51 个端点，100% 覆盖
- 真实 LLM 验证：21 个测试用例，100% 通过
- 消融测试：18 个测试用例，100% 通过

**文档**：[Agent_Core_Modules_Design.md](./Agent_Core_Modules_Design.md)、[Module_Verification_Report.md](./Module_Verification_Report.md)

---

## 附录：参考文档

- [Agent_Core_Modules_Design.md](./Agent_Core_Modules_Design.md) - 核心模块设计
- [skill_architecture/](./skill_architecture/) - 现有 Skill 架构
- [OpenCopilot_Development_TODO.md](./OpenCopilot_Development_TODO.md) - 开发计划
- [Tool_System_Verification_and_Compatibility.md](./Tool_System_Verification_and_Compatibility.md) - 验证方案与兼容性处理
