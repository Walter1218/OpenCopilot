"""
记忆压缩模块

提供记忆的压缩功能，减少存储空间，提高检索效率。
"""

import re
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
from collections import Counter

from .storage import MemoryStorage


class CompressionStrategy(Enum):
    """压缩策略枚举"""
    DEDUPLICATION = "deduplication"  # 去重
    SUMMARIZATION = "summarization"  # 摘要
    MERGING = "merging"              # 合并
    ARCHIVING = "archiving"          # 归档
    HYBRID = "hybrid"                # 混合策略


@dataclass
class CompressionConfig:
    """压缩配置"""
    strategy: CompressionStrategy = CompressionStrategy.HYBRID
    similarity_threshold: float = 0.8  # 相似度阈值
    min_content_length: int = 50       # 最小内容长度
    max_memories_per_group: int = 10   # 每组最大记忆数
    archive_after_days: int = 90       # 归档天数
    preserve_recent: bool = True       # 是否保留最近记忆
    preserve_important: bool = True    # 是否保留重要记忆


class MemoryCompression:
    """记忆压缩管理器"""
    
    def __init__(self, storage: MemoryStorage, config: CompressionConfig = None):
        """
        初始化记忆压缩管理器
        
        Args:
            storage: 存储引擎
            config: 压缩配置
        """
        self.storage = storage
        self.config = config or CompressionConfig()
    
    def compress_deduplication(self) -> Dict[str, Any]:
        """
        去重压缩
        
        Returns:
            压缩统计信息
        """
        # 获取所有记忆
        all_memories = self.storage.search({}, limit=10000)
        
        # 按内容哈希分组
        hash_groups: Dict[str, List[Dict[str, Any]]] = {}
        for memory in all_memories:
            content = memory.get("content", "")
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            if content_hash not in hash_groups:
                hash_groups[content_hash] = []
            hash_groups[content_hash].append(memory)
        
        # 找出重复的记忆
        duplicates = []
        for content_hash, memories in hash_groups.items():
            if len(memories) > 1:
                # 保留最新的一个，删除其他
                memories.sort(key=lambda x: x.get("created_at", 0), reverse=True)
                duplicates.extend(memories[1:])
        
        # 删除重复记忆
        deleted_count = 0
        for memory in duplicates:
            if self.storage.delete(memory["memory_id"]):
                deleted_count += 1
        
        return {
            "strategy": "deduplication",
            "total_memories": len(all_memories),
            "duplicate_groups": len([g for g in hash_groups.values() if len(g) > 1]),
            "deleted_count": deleted_count,
            "remaining_count": len(all_memories) - deleted_count,
        }
    
    def compress_summarization(self) -> Dict[str, Any]:
        """
        摘要压缩
        
        Returns:
            压缩统计信息
        """
        # 获取所有记忆
        all_memories = self.storage.search({}, limit=10000)
        
        # 按会话分组
        session_groups: Dict[str, List[Dict[str, Any]]] = {}
        for memory in all_memories:
            session_id = memory.get("session_id", "unknown")
            if session_id not in session_groups:
                session_groups[session_id] = []
            session_groups[session_id].append(memory)
        
        # 对每个会话进行摘要压缩
        compressed_count = 0
        for session_id, memories in session_groups.items():
            if len(memories) < 3:  # 记忆太少，不压缩
                continue
            
            # 按时间排序
            memories.sort(key=lambda x: x.get("created_at", 0))
            
            # 将连续的短记忆合并
            merged_memories = self._merge_consecutive_memories(memories)
            
            # 如果合并后数量减少，更新存储
            if len(merged_memories) < len(memories):
                # 删除原始记忆
                for memory in memories:
                    self.storage.delete(memory["memory_id"])
                
                # 存储合并后的记忆
                for memory in merged_memories:
                    self.storage.store(memory)
                
                compressed_count += len(memories) - len(merged_memories)
        
        return {
            "strategy": "summarization",
            "total_memories": len(all_memories),
            "compressed_count": compressed_count,
            "remaining_count": len(all_memories) - compressed_count,
        }
    
    def _merge_consecutive_memories(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并连续的记忆
        
        Args:
            memories: 记忆列表
            
        Returns:
            合并后的记忆列表
        """
        if not memories:
            return []
        
        merged = []
        current_group = [memories[0]]
        
        for i in range(1, len(memories)):
            current = memories[i]
            previous = memories[i - 1]
            
            # 检查是否应该合并
            if self._should_merge(previous, current):
                current_group.append(current)
            else:
                # 合并当前组
                if len(current_group) > 1:
                    merged_memory = self._merge_memory_group(current_group)
                    merged.append(merged_memory)
                else:
                    merged.append(current_group[0])
                
                current_group = [current]
        
        # 处理最后一组
        if len(current_group) > 1:
            merged_memory = self._merge_memory_group(current_group)
            merged.append(merged_memory)
        elif current_group:
            merged.append(current_group[0])
        
        return merged
    
    def _should_merge(self, memory1: Dict[str, Any], memory2: Dict[str, Any]) -> bool:
        """
        判断是否应该合并两个记忆
        
        Args:
            memory1: 记忆1
            memory2: 记忆2
            
        Returns:
            是否应该合并
        """
        # 检查时间间隔
        time1 = memory1.get("created_at", 0)
        time2 = memory2.get("created_at", 0)
        time_diff = abs(time2 - time1)
        
        # 如果时间间隔超过1小时，不合并
        if time_diff > 3600:
            return False
        
        # 检查内容相似度
        content1 = memory1.get("content", "")
        content2 = memory2.get("content", "")
        
        # 简单的相似度检查
        if len(content1) < 10 or len(content2) < 10:
            return False
        
        # 检查是否有重叠的关键词
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        
        return similarity > 0.3  # 30%相似度阈值
    
    def _merge_memory_group(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并一组记忆
        
        Args:
            memories: 记忆列表
            
        Returns:
            合并后的记忆
        """
        if not memories:
            return {}
        
        if len(memories) == 1:
            return memories[0]
        
        # 按时间排序
        memories.sort(key=lambda x: x.get("created_at", 0))
        
        # 合并内容
        contents = [m.get("content", "") for m in memories]
        merged_content = "\n---\n".join(contents)
        
        # 合并标签
        all_tags = set()
        for memory in memories:
            tags = memory.get("tags", [])
            all_tags.update(tags)
        
        # 合并元数据
        merged_metadata = {}
        for memory in memories:
            metadata = memory.get("metadata", {})
            merged_metadata.update(metadata)
        
        # 计算平均重要性
        importance_values = [m.get("importance", 0.5) for m in memories]
        avg_importance = sum(importance_values) / len(importance_values)
        
        # 计算总访问次数
        total_access = sum(m.get("access_count", 0) for m in memories)
        
        # 使用最新的时间戳
        latest_time = max(m.get("created_at", 0) for m in memories)
        
        # 创建合并后的记忆
        merged_memory = {
            "memory_id": memories[0]["memory_id"],  # 使用第一个记忆的ID
            "session_id": memories[0].get("session_id", ""),
            "content": merged_content,
            "memory_type": memories[0].get("memory_type", "short_term"),
            "importance": avg_importance,
            "access_count": total_access,
            "created_at": memories[0].get("created_at", time.time()),
            "updated_at": time.time(),
            "last_accessed": latest_time,
            "tags": list(all_tags),
            "metadata": {
                **merged_metadata,
                "merged_from": len(memories),
                "merged_at": time.time(),
            },
        }
        
        return merged_memory
    
    def compress_merging(self) -> Dict[str, Any]:
        """
        合并压缩
        
        Returns:
            压缩统计信息
        """
        # 获取所有记忆
        all_memories = self.storage.search({}, limit=10000)
        
        # 按标签分组
        tag_groups: Dict[str, List[Dict[str, Any]]] = {}
        for memory in all_memories:
            tags = memory.get("tags", [])
            for tag in tags:
                if tag not in tag_groups:
                    tag_groups[tag] = []
                tag_groups[tag].append(memory)
        
        # 对每个标签组进行合并
        merged_count = 0
        for tag, memories in tag_groups.items():
            if len(memories) < 2:
                continue
            
            # 按时间排序
            memories.sort(key=lambda x: x.get("created_at", 0))
            
            # 合并相似的记忆
            merged_memories = self._merge_similar_memories(memories)
            
            # 如果合并后数量减少，更新存储
            if len(merged_memories) < len(memories):
                # 删除原始记忆
                for memory in memories:
                    self.storage.delete(memory["memory_id"])
                
                # 存储合并后的记忆
                for memory in merged_memories:
                    self.storage.store(memory)
                
                merged_count += len(memories) - len(merged_memories)
        
        return {
            "strategy": "merging",
            "total_memories": len(all_memories),
            "merged_count": merged_count,
            "remaining_count": len(all_memories) - merged_count,
        }
    
    def _merge_similar_memories(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并相似的记忆
        
        Args:
            memories: 记忆列表
            
        Returns:
            合并后的记忆列表
        """
        if not memories:
            return []
        
        # 计算相似度矩阵
        n = len(memories)
        similarity_matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(i + 1, n):
                similarity = self._calculate_similarity(memories[i], memories[j])
                similarity_matrix[i][j] = similarity
                similarity_matrix[j][i] = similarity
        
        # 使用贪心算法合并相似记忆
        merged = [False] * n
        result = []
        
        for i in range(n):
            if merged[i]:
                continue
            
            # 找到与当前记忆相似的记忆
            similar_indices = [i]
            for j in range(i + 1, n):
                if not merged[j] and similarity_matrix[i][j] > self.config.similarity_threshold:
                    similar_indices.append(j)
                    merged[j] = True
            
            # 合并相似记忆
            if len(similar_indices) > 1:
                similar_memories = [memories[idx] for idx in similar_indices]
                merged_memory = self._merge_memory_group(similar_memories)
                result.append(merged_memory)
            else:
                result.append(memories[i])
        
        return result
    
    def _calculate_similarity(self, memory1: Dict[str, Any], memory2: Dict[str, Any]) -> float:
        """
        计算两个记忆的相似度
        
        Args:
            memory1: 记忆1
            memory2: 记忆2
            
        Returns:
            相似度 (0.0-1.0)
        """
        # 内容相似度
        content1 = memory1.get("content", "").lower()
        content2 = memory2.get("content", "").lower()
        
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        content_similarity = intersection / union if union > 0 else 0.0
        
        # 标签相似度
        tags1 = set(memory1.get("tags", []))
        tags2 = set(memory2.get("tags", []))
        
        if tags1 and tags2:
            tag_intersection = len(tags1.intersection(tags2))
            tag_union = len(tags1.union(tags2))
            tag_similarity = tag_intersection / tag_union if tag_union > 0 else 0.0
        else:
            tag_similarity = 0.0
        
        # 综合相似度
        return content_similarity * 0.7 + tag_similarity * 0.3
    
    def compress_archiving(self) -> Dict[str, Any]:
        """
        归档压缩
        
        Returns:
            压缩统计信息
        """
        # 获取所有记忆
        all_memories = self.storage.search({}, limit=10000)
        
        # 计算归档时间阈值
        archive_threshold = time.time() - (self.config.archive_after_days * 24 * 60 * 60)
        
        # 找出需要归档的记忆
        to_archive = []
        for memory in all_memories:
            # 检查时间
            last_accessed = memory.get("last_accessed", 0)
            if last_accessed < archive_threshold:
                # 如果配置了保留重要记忆，检查重要性
                if self.config.preserve_important:
                    if memory.get("importance", 0.5) >= 0.7:  # 重要性阈值
                        continue
                
                # 如果配置了保留最近记忆，检查创建时间
                if self.config.preserve_recent:
                    created_at = memory.get("created_at", 0)
                    if created_at > archive_threshold:
                        continue
                
                to_archive.append(memory)
        
        # 归档记忆（这里只是标记为归档，实际实现可以移动到归档表）
        archived_count = 0
        for memory in to_archive:
            # 更新记忆的元数据，标记为已归档
            metadata = memory.get("metadata", {})
            metadata["archived"] = True
            metadata["archived_at"] = time.time()
            
            self.storage.update(memory["memory_id"], {"metadata": metadata})
            archived_count += 1
        
        return {
            "strategy": "archiving",
            "total_memories": len(all_memories),
            "archived_count": archived_count,
            "remaining_count": len(all_memories) - archived_count,
            "archive_threshold_days": self.config.archive_after_days,
        }
    
    def compress_hybrid(self) -> Dict[str, Any]:
        """
        混合策略压缩
        
        Returns:
            压缩统计信息
        """
        # 执行多种压缩策略
        results = {}
        
        # 1. 去重
        dedup_result = self.compress_deduplication()
        results["deduplication"] = dedup_result
        
        # 2. 合并
        merge_result = self.compress_merging()
        results["merging"] = merge_result
        
        # 3. 归档
        archive_result = self.compress_archiving()
        results["archiving"] = archive_result
        
        # 计算总体统计
        total_deleted = dedup_result.get("deleted_count", 0)
        total_merged = merge_result.get("merged_count", 0)
        total_archived = archive_result.get("archived_count", 0)
        
        return {
            "strategy": "hybrid",
            "details": results,
            "total_compressed": total_deleted + total_merged + total_archived,
        }
    
    def compress(self, strategy: CompressionStrategy = None) -> Dict[str, Any]:
        """
        执行压缩
        
        Args:
            strategy: 压缩策略
            
        Returns:
            压缩统计信息
        """
        strategy = strategy or self.config.strategy
        
        if strategy == CompressionStrategy.DEDUPLICATION:
            return self.compress_deduplication()
        elif strategy == CompressionStrategy.SUMMARIZATION:
            return self.compress_summarization()
        elif strategy == CompressionStrategy.MERGING:
            return self.compress_merging()
        elif strategy == CompressionStrategy.ARCHIVING:
            return self.compress_archiving()
        elif strategy == CompressionStrategy.HYBRID:
            return self.compress_hybrid()
        else:
            raise ValueError(f"Unknown compression strategy: {strategy}")
    
    def get_compression_candidates(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取压缩候选记忆
        
        Args:
            limit: 返回数量限制
            
        Returns:
            压缩候选记忆列表
        """
        # 获取所有记忆
        all_memories = self.storage.search({}, limit=10000)
        
        # 计算压缩分数
        scored_memories = []
        for memory in all_memories:
            score = self._calculate_compression_score(memory)
            scored_memories.append((memory, score))
        
        # 按压缩分数排序（分数越高越适合压缩）
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前limit个候选
        candidates = []
        for memory, score in scored_memories[:limit]:
            memory["compression_score"] = score
            candidates.append(memory)
        
        return candidates
    
    def _calculate_compression_score(self, memory: Dict[str, Any]) -> float:
        """
        计算压缩分数
        
        Args:
            memory: 记忆数据
            
        Returns:
            压缩分数
        """
        # 内容长度因素（越长越适合压缩）
        content_length = len(memory.get("content", ""))
        length_score = min(content_length / 1000.0, 1.0)
        
        # 访问频率因素（访问越少越适合压缩）
        access_count = memory.get("access_count", 0)
        access_score = max(1.0 - (access_count / 10.0), 0.0)
        
        # 重要性因素（越不重要越适合压缩）
        importance = memory.get("importance", 0.5)
        importance_score = 1.0 - importance
        
        # 时间因素（越旧越适合压缩）
        created_at = memory.get("created_at", time.time())
        age_days = (time.time() - created_at) / (24 * 60 * 60)
        time_score = min(age_days / 30.0, 1.0)
        
        # 综合分数
        return (
            length_score * 0.3 +
            access_score * 0.3 +
            importance_score * 0.2 +
            time_score * 0.2
        )
