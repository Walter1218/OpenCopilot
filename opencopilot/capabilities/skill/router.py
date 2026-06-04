# skill_architecture/router.py

import logging
from typing import Dict, List, Optional, Tuple, Any
from collections import OrderedDict
from datetime import datetime, timedelta
from .base import BaseSkill
from .registry import SkillRegistry
from .models import SkillContext

logger = logging.getLogger(__name__)


class IntentRouter:
    """意图路由器 - 增强版
    
    新增功能：
    1. 模糊匹配增强：支持编辑距离、同义词、语义相似度
    2. 置信度排序优化：多维度置信度计算
    3. 意图缓存增强：LRU缓存、过期机制、命中率统计
    """
    
    def __init__(self, registry: SkillRegistry, cache_size: int = 100, cache_ttl: int = 300):
        self._registry = registry
        self._intent_cache: Dict[str, List[str]] = {}
        
        # LRU缓存配置
        self._cache_size = cache_size
        self._cache_ttl = timedelta(seconds=cache_ttl)
        self._cache: OrderedDict[str, Tuple[List[Tuple[str, float]], datetime]] = OrderedDict()
        
        # 统计信息
        self._stats = {
            "total_routes": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "fuzzy_matches": 0,
            "exact_matches": 0
        }
        
        # 同义词映射
        self._synonyms: Dict[str, List[str]] = {
            "fix": ["repair", "debug", "troubleshoot", "resolve"],
            "create": ["generate", "make", "build", "produce"],
            "analyze": ["examine", "inspect", "review", "evaluate"],
            "convert": ["transform", "change", "translate", "modify"],
            "optimize": ["improve", "enhance", "refine", "upgrade"],
            "search": ["find", "lookup", "query", "retrieve"],
            "delete": ["remove", "erase", "clear", "drop"],
            "update": ["modify", "change", "edit", "revise"],
        }
        
        # 反向同义词映射
        self._reverse_synonyms: Dict[str, str] = {}
        for key, synonyms in self._synonyms.items():
            for synonym in synonyms:
                self._reverse_synonyms[synonym] = key
    
    async def route(self, context: SkillContext) -> Optional[str]:
        """
        路由到最合适的 Skill
        
        Args:
            context: 执行上下文
        
        Returns:
            str: Skill 名称，如果没有找到返回 None
        """
        self._stats["total_routes"] += 1
        
        # 1. 检查缓存
        cache_key = self._get_cache_key(context)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            self._stats["cache_hits"] += 1
            if cached_result:
                return cached_result[0][0]  # 返回置信度最高的
            return None
        
        self._stats["cache_misses"] += 1
        
        # 2. 根据意图查找候选 Skill
        candidates = self._find_candidates(context)
        
        if not candidates:
            self._add_to_cache(cache_key, [])
            return None
        
        # 3. 计算每个候选 Skill 的置信度
        scored_candidates = await self._score_candidates(context, candidates)
        
        # 4. 按置信度排序
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 5. 缓存结果
        self._add_to_cache(cache_key, scored_candidates)
        
        # 6. 选择置信度最高的 Skill
        if scored_candidates:
            best_skill, best_score = scored_candidates[0]
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
        self._stats["total_routes"] += 1
        
        # 1. 检查缓存
        cache_key = self._get_cache_key(context)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            self._stats["cache_hits"] += 1
            return cached_result[:max_skills]
        
        self._stats["cache_misses"] += 1
        
        # 2. 根据意图查找候选 Skill
        candidates = self._find_candidates(context)
        
        if not candidates:
            self._add_to_cache(cache_key, [])
            return []
        
        # 3. 计算每个候选 Skill 的置信度
        scored_candidates = await self._score_candidates(context, candidates)
        
        # 4. 按置信度排序，返回前 N 个
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 5. 缓存结果
        self._add_to_cache(cache_key, scored_candidates)
        
        return scored_candidates[:max_skills]
    
    def _find_candidates(self, context: SkillContext) -> List[str]:
        """查找候选 Skill - 增强版"""
        candidates = []
        
        # 1. 精确意图匹配
        exact_matches = self._registry.find_by_intent(context.intent)
        if exact_matches:
            candidates.extend(exact_matches)
            self._stats["exact_matches"] += 1
        
        # 2. 模糊匹配（基于标签）
        keywords = context.intent.split('_')
        for keyword in keywords:
            # 直接标签匹配
            tag_matches = self._registry.find_by_tag(keyword)
            candidates.extend(tag_matches)
            
            # 同义词匹配
            synonym_matches = self._find_by_synonym(keyword)
            candidates.extend(synonym_matches)
            
            # 编辑距离匹配
            fuzzy_matches = self._find_by_edit_distance(keyword)
            candidates.extend(fuzzy_matches)
        
        # 3. 语义相似度匹配（基于标签组合）
        semantic_matches = self._find_by_semantic_similarity(context)
        candidates.extend(semantic_matches)
        
        # 去重并返回
        unique_candidates = list(set(candidates))
        if len(unique_candidates) > len(exact_matches or []):
            self._stats["fuzzy_matches"] += 1
        
        return unique_candidates
    
    def _find_by_synonym(self, keyword: str) -> List[str]:
        """通过同义词查找"""
        matches = []
        
        # 检查是否是同义词
        if keyword in self._reverse_synonyms:
            main_word = self._reverse_synonyms[keyword]
            matches.extend(self._registry.find_by_tag(main_word))
        
        # 检查是否有同义词
        if keyword in self._synonyms:
            for synonym in self._synonyms[keyword]:
                matches.extend(self._registry.find_by_tag(synonym))
        
        return matches
    
    def _find_by_edit_distance(self, keyword: str, max_distance: int = 2) -> List[str]:
        """通过编辑距离查找"""
        matches = []
        
        # 获取所有标签
        all_tags = set()
        for skill_name in self._registry.list_skills():
            skill = self._registry.get_skill(skill_name)
            if skill:
                all_tags.update(skill.metadata.tags)
        
        # 计算编辑距离
        for tag in all_tags:
            distance = self._levenshtein_distance(keyword, tag)
            if distance <= max_distance:
                matches.extend(self._registry.find_by_tag(tag))
        
        return matches
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算两个字符串的编辑距离"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _find_by_semantic_similarity(self, context: SkillContext) -> List[str]:
        """通过语义相似度查找"""
        matches = []
        
        # 提取上下文中的关键词
        input_text = str(context.input_data)
        keywords = set(context.intent.split('_'))
        
        # 从输入数据中提取关键词
        import re
        words = re.findall(r'\w+', input_text.lower())
        keywords.update(words[:10])  # 只取前10个词
        
        # 计算每个Skill的语义相似度
        for skill_name in self._registry.list_skills():
            skill = self._registry.get_skill(skill_name)
            if skill:
                # 计算标签匹配度
                skill_tags = set(skill.metadata.tags)
                skill_intents = set(skill.metadata.intents)
                
                # 计算交集比例
                tag_intersection = keywords.intersection(skill_tags)
                intent_intersection = keywords.intersection(skill_intents)
                
                if tag_intersection or intent_intersection:
                    matches.append(skill_name)
        
        return matches
    
    async def _score_candidates(
        self, 
        context: SkillContext, 
        candidates: List[str]
    ) -> List[Tuple[str, float]]:
        """计算候选 Skill 的置信度 - 增强版"""
        scored = []
        
        for skill_name in candidates:
            skill = self._registry.get_skill(skill_name)
            if skill:
                try:
                    # 1. 基础置信度（来自 can_handle）
                    base_score = await skill.can_handle(context)
                    
                    # 2. 意图匹配度
                    intent_score = self._calculate_intent_score(context, skill)
                    
                    # 3. 标签匹配度
                    tag_score = self._calculate_tag_score(context, skill)
                    
                    # 4. 历史成功率（如果有缓存）
                    history_score = self._get_history_score(skill_name)
                    
                    # 5. 综合置信度（加权平均）
                    final_score = (
                        base_score * 0.4 +
                        intent_score * 0.3 +
                        tag_score * 0.2 +
                        history_score * 0.1
                    )
                    
                    scored.append((skill_name, min(1.0, final_score)))
                    
                except Exception as e:
                    logger.warning(f"Skill {skill_name} can_handle failed: {e}")
                    # 如果 can_handle 抛出异常，给低分
                    scored.append((skill_name, 0.1))
        
        return scored
    
    def _calculate_intent_score(self, context: SkillContext, skill: BaseSkill) -> float:
        """计算意图匹配度"""
        if context.intent in skill.metadata.intents:
            return 1.0
        
        # 检查同义词
        for intent in skill.metadata.intents:
            if self._is_synonym(context.intent, intent):
                return 0.8
        
        return 0.0
    
    def _calculate_tag_score(self, context: SkillContext, skill: BaseSkill) -> float:
        """计算标签匹配度"""
        keywords = set(context.intent.split('_'))
        skill_tags = set(skill.metadata.tags)
        
        if not skill_tags:
            return 0.0
        
        intersection = keywords.intersection(skill_tags)
        return len(intersection) / len(keywords) if keywords else 0.0
    
    def _get_history_score(self, skill_name: str) -> float:
        """获取历史成功率"""
        # 从缓存中获取历史数据
        if skill_name in self._intent_cache:
            return 0.7  # 默认历史成功率
        return 0.5  # 无历史数据
    
    def _is_synonym(self, word1: str, word2: str) -> bool:
        """检查两个词是否是同义词"""
        # 检查直接同义词
        if word1 in self._synonyms and word2 in self._synonyms[word1]:
            return True
        if word2 in self._synonyms and word1 in self._synonyms[word2]:
            return True
        
        # 检查反向同义词
        if word1 in self._reverse_synonyms and self._reverse_synonyms[word1] == word2:
            return True
        if word2 in self._reverse_synonyms and self._reverse_synonyms[word2] == word1:
            return True
        
        return False
    
    def _get_cache_key(self, context: SkillContext) -> str:
        """生成缓存键"""
        # 使用意图和输入数据的关键部分作为缓存键
        key_parts = [
            context.intent,
            str(sorted(context.input_data.keys())),
        ]
        return "|".join(key_parts)
    
    def _get_from_cache(self, key: str) -> Optional[List[Tuple[str, float]]]:
        """从缓存获取"""
        if key in self._cache:
            result, timestamp = self._cache[key]
            # 检查是否过期
            if datetime.now() - timestamp < self._cache_ttl:
                # 移到最新位置（LRU）
                self._cache.move_to_end(key)
                return result
            else:
                # 过期，删除
                del self._cache[key]
        return None
    
    def _add_to_cache(self, key: str, result: List[Tuple[str, float]]) -> None:
        """添加到缓存"""
        # 如果缓存已满，删除最旧的
        if len(self._cache) >= self._cache_size:
            self._cache.popitem(last=False)
        
        self._cache[key] = (result, datetime.now())
    
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
    
    def add_synonyms(self, main_word: str, synonyms: List[str]) -> None:
        """
        添加同义词映射
        
        Args:
            main_word: 主词
            synonyms: 同义词列表
        """
        if main_word not in self._synonyms:
            self._synonyms[main_word] = []
        self._synonyms[main_word].extend(synonyms)
        
        # 更新反向映射
        for synonym in synonyms:
            self._reverse_synonyms[synonym] = main_word
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        stats["cache_size"] = len(self._cache)
        stats["cache_hit_rate"] = (
            stats["cache_hits"] / stats["total_routes"] 
            if stats["total_routes"] > 0 else 0.0
        )
        stats["synonyms_count"] = len(self._synonyms)
        return stats
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
        logger.info("IntentRouter cache cleared")
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "total_routes": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "fuzzy_matches": 0,
            "exact_matches": 0
        }