"""Prompt 构建 - 兼容入口 → opencopilot.shared.prompt"""
from opencopilot.shared.prompt import (
    CONTEXT_DESCRIPTIONS, CONTEXT_SOURCE_PRIORITY,
    PERSONA_CONFLICT_PATTERNS, build_context_prefix,
    sanitize_persona_for_context, load_persona,
)
