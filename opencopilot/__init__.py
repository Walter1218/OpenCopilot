"""
OpenCopilot v4.0 - macOS 系统级 AI 操作员
分层架构：表示层 → 应用层 → 领域层 → 安全层 → 基础设施
"""
__version__ = "4.0.0"

from opencopilot.providers.llm_provider import (
    BaseProvider, MiniMaxProvider, MiMoProvider,
    LocalProvider, ProviderFactory, load_config, save_config,
)
from opencopilot.shared.adapter import LLMAdapter, create_llm_adapter
from opencopilot.shared.prompt import (
    CONTEXT_DESCRIPTIONS, build_context_prefix,
    sanitize_persona_for_context, load_persona,
)
from opencopilot.shared.cursor import Ripple, CursorOverlay
from opencopilot.agent.caller import call_agent_pipeline_sync
from opencopilot.agent.pipeline import PipelineContext
from opencopilot.agent.core import ContextWindowManager
from opencopilot.capabilities.coding.core import CodeExecutor
from opencopilot.capabilities.coding.models import ExecutorConfig
from opencopilot.capabilities.memory.core import MemoryManager, MemoryEntry, MemoryType
from opencopilot.capabilities.memory import ASUAgentMemory
from opencopilot.capabilities.skill import SkillRegistry
from opencopilot.safety.security.core import SecurityModule
from opencopilot.safety.security.models import SecurityConfig
from opencopilot.safety.immune.immune_system import ImmuneSystem
from opencopilot.safety.planner.core import Planner
from opencopilot.observability.core import ObservabilityModule
from opencopilot.config.manager import ConfigManager
