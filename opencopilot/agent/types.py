"""
Agent Pipeline 核心类型定义

集中管理所有 Agent 管线相关的类型，避免循环导入和分散定义。
模块间交互使用这些类型作为契约，保障接口清晰和可扩展性。

按职责分为以下分组：
- PipelineContext 扩展字段定义
- Agent 范式与复杂度判定
- 计划与执行步骤
- Skill 声明与工具描述
- LLM Provider 抽象接口
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Callable


# ============================================================
# Agent 范式
# ============================================================

class AgentParadigm(Enum):
    """Agent 推理范式"""
    ONE_SHOT = "one_shot"         # 直接 LLM 回答，无工具调用
    PLAN_SOLVE = "plan_solve"     # 先生成计划，再逐步执行
    REACT = "react"               # Think→Act→Observe 循环


class TaskComplexity(Enum):
    """任务复杂度等级"""
    SIMPLE = "simple"             # One-Shot：简单对话/翻译
    MEDIUM = "medium"             # Plan-and-Solve：多步任务
    COMPLEX = "complex"           # Plan → ReAct fallback：未知探索


# ============================================================
# 计划与执行
# ============================================================

@dataclass
class PlanStep:
    """计划步骤"""
    step_id: int
    description: str
    tool_name: Optional[str] = None         # 需要的工具名称
    tool_args: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"                  # pending | running | done | failed
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ExecutionPlan:
    """执行计划"""
    paradigm: AgentParadigm = AgentParadigm.ONE_SHOT
    steps: List[PlanStep] = field(default_factory=list)
    reasoning: str = ""                      # LLM 的规划推理过程
    total_turns: int = 0                     # 已执行的 turn 数


@dataclass
class AgentTurn:
    """Agent Loop 中的单次 Turn"""
    turn_number: int
    paradigm: AgentParadigm
    thought: str = ""                        # Think 阶段输出
    action: Optional[str] = None             # 调用的工具名称
    action_args: Dict[str, Any] = field(default_factory=dict)
    observation: Optional[str] = None        # 工具返回结果
    is_final: bool = False                   # 是否为最终回答


# ============================================================
# Skill 与工具声明
# ============================================================

@dataclass
class ToolSpec:
    """单个工具的描述（用于注入 System Prompt）"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None       # 工具调用处理函数


@dataclass
class SkillSpec:
    """Skill 声明规格（从 SKILL.md 解析）"""
    name: str
    description: str
    version: str = "1.0.0"
    eligibility: Dict[str, Any] = field(default_factory=dict)  # OS / env / config 条件
    tools: List[ToolSpec] = field(default_factory=list)
    markdown_body: str = ""                  # SKILL.md 正文（用法说明）
    source_file: str = ""                    # SKILL.md 文件路径

    def is_eligible(self) -> bool:
        """检查当前环境是否满足 Eligibility 条件"""
        import os as _os
        import sys as _sys
        import platform as _platform

        # OS 检查
        os_condition = self.eligibility.get("os")
        if os_condition:
            current_os = _sys.platform
            if isinstance(os_condition, list):
                if current_os not in os_condition:
                    return False
            elif current_os != os_condition:
                return False

        # 环境变量检查
        env_condition = self.eligibility.get("env", {})
        for env_key, env_val in env_condition.items():
            actual_value = _os.environ.get(env_key)
            if env_val == "*":
                # "*" 表示存在且非空
                if not actual_value:
                    return False
            elif actual_value != env_val:
                return False

        # Python 版本检查
        py_version = self.eligibility.get("python_version")
        if py_version:
            if _sys.version_info < tuple(map(int, py_version.split("."))):
                return False

        return True


# ============================================================
# LLM Provider 异步抽象接口
# ============================================================

from abc import ABC, abstractmethod
from typing import AsyncGenerator


class AsyncBaseProvider(ABC):
    """异步 LLM Provider 抽象基类

    所有 LLM Provider 应实现此接口以支持原生异步调用。
    旧同步方法保留为兼容层（标记 deprecated），新代码优先使用 async 方法。

    使用方式:
        provider = MiMoProvider(api_key="...")
        async for chunk in provider.async_stream_chat(prompt, system_prompt):
            await ctx.awrite_sse(chunk)
    """

    @abstractmethod
    async def async_stream_chat(
        self, prompt: str, system_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        """异步流式对话（单轮，无历史）"""
        yield ""  # pragma: no cover

    @abstractmethod
    async def async_stream_chat_with_history(
        self, messages: list, **kwargs
    ) -> AsyncGenerator[str, None]:
        """异步流式对话（多轮，带历史）"""
        yield ""  # pragma: no cover

    def stream_chat(self, prompt: str, system_prompt: str = ""):
        """[DEPRECATED] 同步流式对话，仅保留兼容。
        新代码请使用 async_stream_chat()。
        """
        raise NotImplementedError("Use async_stream_chat() instead")

    def stream_chat_with_history(self, messages: list):
        """[DEPRECATED] 同步流式对话（带历史），仅保留兼容。
        新代码请使用 async_stream_chat_with_history()。
        """
        raise NotImplementedError("Use async_stream_chat_with_history() instead")


# ============================================================
# PipelineContext 扩展：Agent Loop 相关元数据
# ============================================================

@dataclass
class AgentContextMeta:
    """Agent Loop 执行上下文元数据

    挂载到 PipelineContext.metadata 中，由 LLMAgentMiddleware 维护。
    """
    paradigm: AgentParadigm = AgentParadigm.ONE_SHOT
    complexity: TaskComplexity = TaskComplexity.SIMPLE
    plan: Optional[ExecutionPlan] = None
    turns: List[AgentTurn] = field(default_factory=list)
    current_turn: int = 0
    max_turns: int = 10
    # 工具调用追踪
    tool_calls_count: int = 0
    tool_calls_failed: int = 0


# ============================================================
# 兼容性导入
# ============================================================

# 重新导出 PipelineContext 方便使用
# (在 pipeline.py 已定义，此处仅标记引用位置)
