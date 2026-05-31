# skill_architecture/__init__.py

from .models import (
    SkillStatus,
    ExecutionMode,
    SkillMetadata,
    SkillContext,
    SkillResult,
    ExecutionPlan
)
from .base import BaseSkill
from .registry import SkillRegistry
from .router import IntentRouter
from .executor import SkillExecutor
from .discovery import SkillDiscovery
from .knowledge_skill import KnowledgeSkill
from .coding_skill import CodingSkill
from .ppt_skill import PPTSkill

__all__ = [
    'SkillStatus',
    'ExecutionMode',
    'SkillMetadata',
    'SkillContext',
    'SkillResult',
    'ExecutionPlan',
    'BaseSkill',
    'SkillRegistry',
    'IntentRouter',
    'SkillExecutor',
    'SkillDiscovery',
    'KnowledgeSkill',
    'CodingSkill',
    'PPTSkill'
]