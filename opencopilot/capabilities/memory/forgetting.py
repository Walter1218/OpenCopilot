"""
记忆遗忘机制模块

提供记忆的遗忘功能，基于时间、重要性、访问频率等因素自动遗忘不重要的记忆。
"""

import time
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

from .storage import MemoryStorage


class ForgettingStrategy(Enum):
    """遗忘策略枚举"""
    TIME_BASED = "time_based"           # 基于时间
    IMPORTANCE_BASED = "importance_based"  # 基于重要性
    ACCESS_BASED = "access_based"       # 基于访问频率
    HYBRID = "hybrid"                   # 混合策略
    EBBINGHAUS = "ebbinghaus"           # 艾宾浩斯遗忘曲线


@dataclass
class ForgettingConfig:
    """遗忘配置"""
    strategy: ForgettingStrategy = ForgettingStrategy.HYBRID
    time_threshold_days: int = 30       # 时间阈值（天）
    importance_threshold: float = 0.3   # 重要性阈值
    access_threshold: int = 2           # 访问次数阈值
    ebbinghaus_decay_rate: float = 0.5  # 艾宾浩斯衰减率
    max_memories: int = 10000           # 最大记忆数量
    preserve_important: bool = True     # 是否保留重要记忆


class MemoryForgetting:
    """记忆遗忘管理器"""
    
    def __init__(self, storage: MemoryStorage, config: ForgettingConfig = None):
        """
        初始化记忆遗忘管理器
        
        Args:
            storage: 存储引擎
            config: 遗忘配置
        """
        self.storage = storage
        self.config = config or ForgettingConfig()
    
    def forget_by_time(self, days_threshold: int = None) -> Dict[str, Any]:
        """
        基于时间遗忘
        
        Args:
            days_threshold: 天数阈值
            
        Returns:
            遗忘统计信息
        """
        threshold = days_threshold or self.config.time_threshold_days
        threshold_time = time.time() - (threshold * 24 * 60 * 60)
        
        # 获取所有记忆
        all_memories = self.storage.search({}, limit=10000)
        
        # 筛选需要遗忘的记忆
        to_forget = []
        for memory in all_memories:
            # 检查时间
            if memory.get("last_accessed", 0) < threshold_time:
                # 如果配置了保留重要记忆，检查重要性
                if self.config.preserve_important:
                    if memory.get("importance", 0.5) >= 0.7:  # 重要性阈值
                        continue
                to_forget.append(memory)
        
        # 执行遗忘
        forgotten_count = 0
        for memory in to_forget:
            if self.storage.delete(memory["memory_id"]):
                forgotten_count += 1
        
        return {
            "strategy": "time_based",
            "threshold_days": threshold,
            "total_memories": len(all_memories),
            "forgotten_count": forgotten_count,
            "remaining_count": len(all_memories) - forgotten_count,
        }
    
    def forget_by_importance(self, importance_threshold: float = None) -> Dict[str, Any]:
        """
        基于重要性遗忘
        
        Args:
            importance_threshold: 重要性阈值
            
        Returns:
            遗忘统计信息
        """
        threshold = importance_threshold or self.config.importance_threshold
        
        # 获取所有记忆
        all_memories = self.storage.search({}, limit=10000)
        
        # 筛选需要遗忘的记忆
        to_forget = []
        for memory in all_memories:
            if memory.get("importance", 0.5) < threshold:
                to_forget.append(memory)
        
        # 执行遗忘
        forgotten_count = 0
        for memory in to_forget:
            if self.storage.delete(memory["memory_id"]):
                forgotten_count += 1
        
        return {
            "strategy": "importance_based",
            "threshold": threshold,
            "total_memories": len(all_memories),
            "forgotten_count": forgotten_count,
            "remaining_count": len(all_memories) - forgotten_count,
        }
    
    def forget_by_access(self, access_threshold: int = None) -> Dict[str, Any]:
        """
        基于访问频率遗忘
        
        Args:
            access_threshold: 访问次数阈值
            
        Returns:
            遗忘统计信息
        """
        threshold = access_threshold or self.config.access_threshold
        
        # 获取所有记忆
        all_memories = self.storage.search({}, limit=10000)
        
        # 筛选需要遗忘的记忆
        to_forget = []
        for memory in all_memories:
            if memory.get("access_count", 0) < threshold:
                # 如果配置了保留重要记忆，检查重要性
                if self.config.preserve_important:
                    if memory.get("importance", 0.5) >= 0.7:  # 重要性阈值
                        continue
                to_forget.append(memory)
        
        # 执行遗忘
        forgotten_count = 0
        for memory in to_forget:
            if self.storage.delete(memory["memory_id"]):
                forgotten_count += 1
        
        return {
            "strategy": "access_based",
            "threshold": threshold,
            "total_memories": len(all_memories),
            "forgotten_count": forgotten_count,
            "remaining_count": len(all_memories) - forgotten_count,
        }
    
    def forget_hybrid(self) -> Dict[str, Any]:
        """
        混合策略遗忘
        
        Returns:
            遗忘统计信息
        """
        # 获取所有记忆
        all_memories = self.storage.search({}, limit=10000)
        
        # 计算每条记忆的遗忘分数
        scored_memories = []
        for memory in all_memories:
            score = self._calculate_forgetting_score(memory)
            scored_memories.append((memory, score))
        
        # 按遗忘分数排序（分数越高越容易被遗忘）
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        
        # 确定需要遗忘的记忆数量
        max_memories = self.config.max_memories
        if len(scored_memories) <= max_memories:
            return {
                "strategy": "hybrid",
                "total_memories": len(all_memories),
                "forgotten_count": 0,
                "remaining_count": len(all_memories),
                "reason": "记忆数量未超过上限",
            }
        
        # 遗忘多余的记忆
        to_forget = scored_memories[max_memories:]
        forgotten_count = 0
        
        for memory, score in to_forget:
            # 如果配置了保留重要记忆，检查重要性
            if self.config.preserve_important:
                if memory.get("importance", 0.5) >= 0.7:  # 重要性阈值
                    continue
            
            if self.storage.delete(memory["memory_id"]):
                forgotten_count += 1
        
        return {
            "strategy": "hybrid",
            "total_memories": len(all_memories),
            "forgotten_count": forgotten_count,
            "remaining_count": len(all_memories) - forgotten_count,
            "max_memories": max_memories,
        }
    
    def forget_ebbinghaus(self) -> Dict[str, Any]:
        """
        基于艾宾浩斯遗忘曲线遗忘
        
        Returns:
            遗忘统计信息
        """
        # 获取所有记忆
        all_memories = self.storage.search({}, limit=10000)
        
        # 计算每条记忆的保留概率
        to_forget = []
        for memory in all_memories:
            retention_probability = self._calculate_ebbinghaus_retention(memory)
            
            # 如果保留概率低于阈值，标记为遗忘
            if retention_probability < 0.3:  # 保留概率阈值
                # 如果配置了保留重要记忆，检查重要性
                if self.config.preserve_important:
                    if memory.get("importance", 0.5) >= 0.7:  # 重要性阈值
                        continue
                to_forget.append(memory)
        
        # 执行遗忘
        forgotten_count = 0
        for memory in to_forget:
            if self.storage.delete(memory["memory_id"]):
                forgotten_count += 1
        
        return {
            "strategy": "ebbinghaus",
            "total_memories": len(all_memories),
            "forgotten_count": forgotten_count,
            "remaining_count": len(all_memories) - forgotten_count,
            "decay_rate": self.config.ebbinghaus_decay_rate,
        }
    
    def _calculate_forgetting_score(self, memory: Dict[str, Any]) -> float:
        """
        计算遗忘分数（分数越高越容易被遗忘）
        
        Args:
            memory: 记忆数据
            
        Returns:
            遗忘分数
        """
        # 时间因素（越久越容易遗忘）
        created_at = memory.get("created_at", time.time())
        last_accessed = memory.get("last_accessed", time.time())
        
        age_days = (time.time() - created_at) / (24 * 60 * 60)
        days_since_access = (time.time() - last_accessed) / (24 * 60 * 60)
        
        time_score = min(age_days / 30.0, 1.0)  # 30天为满分
        access_time_score = min(days_since_access / 7.0, 1.0)  # 7天为满分
        
        # 重要性因素（越不重要越容易遗忘）
        importance = memory.get("importance", 0.5)
        importance_score = 1.0 - importance
        
        # 访问频率因素（访问越少越容易遗忘）
        access_count = memory.get("access_count", 0)
        access_score = max(1.0 - (access_count / 10.0), 0.0)  # 10次访问为0分
        
        # 内容长度因素（越短越容易遗忘）
        content_length = len(memory.get("content", ""))
        length_score = max(1.0 - (content_length / 1000.0), 0.0)  # 1000字符为0分
        
        # 加权综合评分
        final_score = (
            time_score * 0.3 +
            access_time_score * 0.3 +
            importance_score * 0.2 +
            access_score * 0.1 +
            length_score * 0.1
        )
        
        return final_score
    
    def _calculate_ebbinghaus_retention(self, memory: Dict[str, Any]) -> float:
        """
        计算艾宾浩斯保留概率
        
        Args:
            memory: 记忆数据
            
        Returns:
            保留概率 (0.0-1.0)
        """
        # R = e^(-t/S)
        # R: 保留概率
        # t: 时间（天）
        # S: 稳定性（与访问次数和重要性相关）
        
        created_at = memory.get("created_at", time.time())
        last_accessed = memory.get("last_accessed", time.time())
        
        # 计算时间（天）
        t = (time.time() - last_accessed) / (24 * 60 * 60)
        
        # 计算稳定性
        access_count = memory.get("access_count", 0)
        importance = memory.get("importance", 0.5)
        
        # 稳定性 = 基础稳定性 * 访问次数因子 * 重要性因子
        base_stability = 7.0  # 基础稳定性7天
        access_factor = 1.0 + (access_count * 0.1)  # 每次访问增加10%稳定性
        importance_factor = 0.5 + (importance * 0.5)  # 重要性0-1映射到0.5-1.0
        
        S = base_stability * access_factor * importance_factor
        
        # 计算保留概率
        decay_rate = self.config.ebbinghaus_decay_rate
        R = math.exp(-t / S * decay_rate)
        
        return R
    
    def forget(self, strategy: ForgettingStrategy = None) -> Dict[str, Any]:
        """
        执行遗忘
        
        Args:
            strategy: 遗忘策略
            
        Returns:
            遗忘统计信息
        """
        strategy = strategy or self.config.strategy
        
        if strategy == ForgettingStrategy.TIME_BASED:
            return self.forget_by_time()
        elif strategy == ForgettingStrategy.IMPORTANCE_BASED:
            return self.forget_by_importance()
        elif strategy == ForgettingStrategy.ACCESS_BASED:
            return self.forget_by_access()
        elif strategy == ForgettingStrategy.HYBRID:
            return self.forget_hybrid()
        elif strategy == ForgettingStrategy.EBBINGHAUS:
            return self.forget_ebbinghaus()
        else:
            raise ValueError(f"Unknown forgetting strategy: {strategy}")
    
    def get_forgetting_candidates(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取遗忘候选记忆
        
        Args:
            limit: 返回数量限制
            
        Returns:
            遗忘候选记忆列表
        """
        # 获取所有记忆
        all_memories = self.storage.search({}, limit=10000)
        
        # 计算遗忘分数
        scored_memories = []
        for memory in all_memories:
            score = self._calculate_forgetting_score(memory)
            scored_memories.append((memory, score))
        
        # 按遗忘分数排序（分数越高越容易被遗忘）
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前limit个候选
        candidates = []
        for memory, score in scored_memories[:limit]:
            memory["forgetting_score"] = score
            candidates.append(memory)
        
        return candidates
    
    def predict_forgetting_time(self, memory_id: str) -> Dict[str, Any]:
        """
        预测记忆遗忘时间
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            遗忘时间预测
        """
        memory_data = self.storage.retrieve(memory_id)
        if not memory_data:
            return {"error": "Memory not found"}
        
        # 计算当前保留概率
        current_retention = self._calculate_ebbinghaus_retention(memory_data)
        
        # 预测达到遗忘阈值的时间
        threshold = 0.3  # 遗忘阈值
        
        if current_retention <= threshold:
            return {
                "memory_id": memory_id,
                "current_retention": current_retention,
                "already_below_threshold": True,
                "recommendation": "建议立即遗忘",
            }
        
        # 计算需要多少天达到阈值
        # R = e^(-t/S) => t = -S * ln(R)
        access_count = memory_data.get("access_count", 0)
        importance = memory_data.get("importance", 0.5)
        
        base_stability = 7.0
        access_factor = 1.0 + (access_count * 0.1)
        importance_factor = 0.5 + (importance * 0.5)
        S = base_stability * access_factor * importance_factor
        
        # t = -S * ln(threshold)
        t = -S * math.log(threshold)
        
        return {
            "memory_id": memory_id,
            "current_retention": current_retention,
            "days_until_forgetting": t,
            "recommended_action": "保留" if t > 7 else "考虑遗忘",
        }
