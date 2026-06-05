"""
记忆配额管理器模块

提供记忆类型配额管理、配额检查、配额强制执行等功能。
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .config import MemoryType, MemoryTypeQuota, ConfigManager, get_config


@dataclass
class MemoryStats:
    """记忆统计信息"""
    memory_type: MemoryType
    count: int
    total_chars: int
    avg_importance: float
    avg_access_count: float
    oldest_memory_age_days: float
    newest_memory_age_days: float


class QuotaManager:
    """记忆配额管理器"""
    
    def __init__(self, config_manager: ConfigManager = None):
        """
        初始化配额管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or get_config()
    
    def check_quota(self, memory_type: MemoryType, 
                   current_stats: MemoryStats) -> Tuple[bool, str]:
        """
        检查是否超出配额
        
        Args:
            memory_type: 记忆类型
            current_stats: 当前统计信息
            
        Returns:
            (是否超出配额, 原因说明)
        """
        quota = self.config_manager.get_memory_type_quota(memory_type)
        
        # 检查数量限制
        if current_stats.count >= quota.max_count:
            return False, f"超出数量限制：{current_stats.count}/{quota.max_count}"
        
        # 检查字符数限制
        if current_stats.total_chars >= quota.max_chars:
            return False, f"超出字符数限制：{current_stats.total_chars}/{quota.max_chars}"
        
        # 检查年龄限制
        if current_stats.oldest_memory_age_days > quota.max_age_days:
            return False, f"存在过期记忆：{current_stats.oldest_memory_age_days:.1f}天/{quota.max_age_days}天"
        
        return True, "配额充足"
    
    def enforce_quota(self, memory_type: MemoryType, 
                     memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        强制执行配额，返回需要删除的记忆列表
        
        Args:
            memory_type: 记忆类型
            memories: 该类型的所有记忆列表
            
        Returns:
            需要删除的记忆列表
        """
        quota = self.config_manager.get_memory_type_quota(memory_type)
        memories_to_delete = []
        
        # 按重要性和访问次数排序，优先保留重要的记忆
        sorted_memories = sorted(
            memories,
            key=lambda m: (m.get("importance", 0), m.get("access_count", 0)),
            reverse=True
        )
        
        # 检查数量限制
        if len(sorted_memories) > quota.max_count:
            # 删除超出部分（从最不重要的开始）
            memories_to_delete.extend(sorted_memories[quota.max_count:])
            sorted_memories = sorted_memories[:quota.max_count]
        
        # 检查字符数限制
        total_chars = sum(len(m.get("content", "")) for m in sorted_memories)
        if total_chars > quota.max_chars:
            # 逐个删除最不重要的记忆，直到满足字符数限制
            chars_to_remove = total_chars - quota.max_chars
            removed_chars = 0
            
            for memory in reversed(sorted_memories):
                if removed_chars >= chars_to_remove:
                    break
                
                memory_chars = len(memory.get("content", ""))
                memories_to_delete.append(memory)
                removed_chars += memory_chars
        
        # 检查年龄限制
        current_time = time.time()
        for memory in sorted_memories:
            created_at = memory.get("created_at", current_time)
            age_days = (current_time - created_at) / (24 * 60 * 60)
            
            if age_days > quota.max_age_days:
                # 检查重要性阈值
                importance = memory.get("importance", 0)
                if importance < quota.importance_threshold:
                    memories_to_delete.append(memory)
        
        # 去重
        unique_memories_to_delete = []
        seen_ids = set()
        for memory in memories_to_delete:
            memory_id = memory.get("memory_id")
            if memory_id not in seen_ids:
                seen_ids.add(memory_id)
                unique_memories_to_delete.append(memory)
        
        return unique_memories_to_delete
    
    def get_memory_stats(self, memories: List[Dict[str, Any]], 
                        memory_type: MemoryType) -> MemoryStats:
        """
        获取记忆统计信息
        
        Args:
            memories: 记忆列表
            memory_type: 记忆类型
            
        Returns:
            统计信息
        """
        if not memories:
            return MemoryStats(
                memory_type=memory_type,
                count=0,
                total_chars=0,
                avg_importance=0.0,
                avg_access_count=0.0,
                oldest_memory_age_days=0.0,
                newest_memory_age_days=0.0
            )
        
        current_time = time.time()
        total_chars = sum(len(m.get("content", "")) for m in memories)
        total_importance = sum(m.get("importance", 0) for m in memories)
        total_access_count = sum(m.get("access_count", 0) for m in memories)
        
        ages = []
        for memory in memories:
            created_at = memory.get("created_at", current_time)
            age_days = (current_time - created_at) / (24 * 60 * 60)
            ages.append(age_days)
        
        return MemoryStats(
            memory_type=memory_type,
            count=len(memories),
            total_chars=total_chars,
            avg_importance=total_importance / len(memories),
            avg_access_count=total_access_count / len(memories),
            oldest_memory_age_days=max(ages) if ages else 0.0,
            newest_memory_age_days=min(ages) if ages else 0.0
        )
    
    def get_quota_usage(self, memory_type: MemoryType, 
                       current_stats: MemoryStats) -> Dict[str, Any]:
        """
        获取配额使用情况
        
        Args:
            memory_type: 记忆类型
            current_stats: 当前统计信息
            
        Returns:
            配额使用情况字典
        """
        quota = self.config_manager.get_memory_type_quota(memory_type)
        
        return {
            "memory_type": memory_type.value,
            "quota": {
                "max_count": quota.max_count,
                "max_chars": quota.max_chars,
                "max_age_days": quota.max_age_days,
                "importance_threshold": quota.importance_threshold,
                "access_count_threshold": quota.access_count_threshold,
            },
            "current": {
                "count": current_stats.count,
                "total_chars": current_stats.total_chars,
                "avg_importance": current_stats.avg_importance,
                "avg_access_count": current_stats.avg_access_count,
                "oldest_memory_age_days": current_stats.oldest_memory_age_days,
            },
            "usage": {
                "count_usage": current_stats.count / quota.max_count if quota.max_count > 0 else 0,
                "chars_usage": current_stats.total_chars / quota.max_chars if quota.max_chars > 0 else 0,
                "age_usage": current_stats.oldest_memory_age_days / quota.max_age_days if quota.max_age_days > 0 else 0,
            },
            "status": {
                "count_ok": current_stats.count < quota.max_count,
                "chars_ok": current_stats.total_chars < quota.max_chars,
                "age_ok": current_stats.oldest_memory_age_days < quota.max_age_days,
            }
        }
    
    def get_all_quota_usage(self, memories_by_type: Dict[MemoryType, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        获取所有记忆类型的配额使用情况
        
        Args:
            memories_by_type: 按类型分组的记忆字典
            
        Returns:
            所有类型的配额使用情况
        """
        result = {}
        
        for memory_type in MemoryType:
            memories = memories_by_type.get(memory_type, [])
            stats = self.get_memory_stats(memories, memory_type)
            usage = self.get_quota_usage(memory_type, stats)
            result[memory_type.value] = usage
        
        return result
    
    def suggest_cleanup(self, memories_by_type: Dict[MemoryType, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        建议清理策略
        
        Args:
            memories_by_type: 按类型分组的记忆字典
            
        Returns:
            清理建议
        """
        suggestions = {}
        
        for memory_type in MemoryType:
            memories = memories_by_type.get(memory_type, [])
            if not memories:
                continue
            
            stats = self.get_memory_stats(memories, memory_type)
            usage = self.get_quota_usage(memory_type, stats)
            
            # 检查是否需要清理
            needs_cleanup = False
            reasons = []
            
            if not usage["status"]["count_ok"]:
                needs_cleanup = True
                reasons.append(f"数量超出：{stats.count}/{usage['quota']['max_count']}")
            
            if not usage["status"]["chars_ok"]:
                needs_cleanup = True
                reasons.append(f"字符数超出：{stats.total_chars}/{usage['quota']['max_chars']}")
            
            if not usage["status"]["age_ok"]:
                needs_cleanup = True
                reasons.append(f"存在过期记忆：{stats.oldest_memory_age_days:.1f}天/{usage['quota']['max_age_days']}天")
            
            if needs_cleanup:
                # 获取需要删除的记忆
                memories_to_delete = self.enforce_quota(memory_type, memories)
                
                suggestions[memory_type.value] = {
                    "needs_cleanup": True,
                    "reasons": reasons,
                    "memories_to_delete_count": len(memories_to_delete),
                    "memories_to_delete_ids": [m.get("memory_id") for m in memories_to_delete],
                    "estimated_chars_freed": sum(len(m.get("content", "")) for m in memories_to_delete),
                }
            else:
                suggestions[memory_type.value] = {
                    "needs_cleanup": False,
                    "reasons": ["配额充足"],
                    "memories_to_delete_count": 0,
                    "memories_to_delete_ids": [],
                    "estimated_chars_freed": 0,
                }
        
        return suggestions


# 默认配额管理器实例
default_quota_manager = QuotaManager()


def get_quota_manager() -> QuotaManager:
    """获取默认配额管理器"""
    return default_quota_manager


def create_quota_manager(config_manager: ConfigManager = None) -> QuotaManager:
    """创建配额管理器"""
    return QuotaManager(config_manager)