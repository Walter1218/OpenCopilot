# skill_architecture/router.py

from typing import Dict, List, Optional, Tuple
from .base import BaseSkill
from .registry import SkillRegistry
from .models import SkillContext


class IntentRouter:
    """意图路由器"""
    
    def __init__(self, registry: SkillRegistry):
        self._registry = registry
        self._intent_cache: Dict[str, List[str]] = {}
    
    async def route(self, context: SkillContext) -> Optional[str]:
        """
        路由到最合适的 Skill
        
        Args:
            context: 执行上下文
        
        Returns:
            str: Skill 名称，如果没有找到返回 None
        """
        # 1. 根据意图查找候选 Skill
        candidates = self._find_candidates(context)
        
        if not candidates:
            return None
        
        # 2. 计算每个候选 Skill 的置信度
        scored_candidates = await self._score_candidates(context, candidates)
        
        # 3. 选择置信度最高的 Skill
        if scored_candidates:
            best_skill, best_score = max(scored_candidates, key=lambda x: x[1])
            if best_score > 0.3:  # 最低置信度阈值
                return best_skill
        
        return None
    
    async def route_multiple(self, context: SkillContext, max_skills: int = 3) -> List[Tuple[str, float]]:
        """
        路由到多个 Skill（用于组合执行）
        
        Args:
            context: 执行上下文
            max_skills: 最大 Skill 数量
        
        Returns:
            List[Tuple[str, float]]: (Skill 名称, 置信度) 列表
        """
        # 1. 根据意图查找候选 Skill
        candidates = self._find_candidates(context)
        
        if not candidates:
            return []
        
        # 2. 计算每个候选 Skill 的置信度
        scored_candidates = await self._score_candidates(context, candidates)
        
        # 3. 按置信度排序，返回前 N 个
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        return scored_candidates[:max_skills]
    
    def _find_candidates(self, context: SkillContext) -> List[str]:
        """查找候选 Skill"""
        # 1. 精确意图匹配
        candidates = self._registry.find_by_intent(context.intent)
        
        if candidates:
            return candidates
        
        # 2. 模糊匹配（基于标签）
        # 提取意图中的关键词作为标签
        keywords = context.intent.split('_')
        for keyword in keywords:
            tag_matches = self._registry.find_by_tag(keyword)
            candidates.extend(tag_matches)
        
        return list(set(candidates))
    
    async def _score_candidates(
        self, 
        context: SkillContext, 
        candidates: List[str]
    ) -> List[Tuple[str, float]]:
        """计算候选 Skill 的置信度"""
        scored = []
        
        for skill_name in candidates:
            skill = self._registry.get_skill(skill_name)
            if skill:
                try:
                    score = await skill.can_handle(context)
                    scored.append((skill_name, score))
                except Exception:
                    # 如果 can_handle 抛出异常，给低分
                    scored.append((skill_name, 0.1))
        
        return scored
    
    def add_intent_mapping(self, intent: str, skills: List[str]) -> None:
        """
        添加意图映射
        
        Args:
            intent: 意图
            skills: Skill 名称列表
        """
        self._intent_cache[intent] = skills
    
    def get_intent_mapping(self, intent: str) -> List[str]:
        """获取意图映射"""
        return self._intent_cache.get(intent, [])