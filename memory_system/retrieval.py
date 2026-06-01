"""
记忆检索引擎模块

提供记忆的检索功能，支持语义检索、时间检索、标签检索等。
"""

import time
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
import json

from .storage import MemoryStorage


class MemoryRetrieval(ABC):
    """记忆检索抽象基类"""
    
    @abstractmethod
    def retrieve(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """检索相关记忆"""
        pass
    
    @abstractmethod
    def retrieve_by_time(self, start_time: float, end_time: float, 
                        limit: int = 10) -> List[Dict[str, Any]]:
        """按时间检索记忆"""
        pass
    
    @abstractmethod
    def retrieve_by_tags(self, tags: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """按标签检索记忆"""
        pass
    
    @abstractmethod
    def retrieve_by_importance(self, min_importance: float, 
                              limit: int = 10) -> List[Dict[str, Any]]:
        """按重要性检索记忆"""
        pass


class SemanticRetrieval(MemoryRetrieval):
    """语义检索实现"""
    
    def __init__(self, storage: MemoryStorage, embedding_model: Optional[str] = None):
        """
        初始化语义检索
        
        Args:
            storage: 存储引擎
            embedding_model: 嵌入模型名称（可选）
        """
        self.storage = storage
        self.embedding_model = embedding_model
        self._embedding_cache: Dict[str, List[float]] = {}
    
    def _get_embedding(self, text: str) -> List[float]:
        """
        获取文本的嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        # 简单实现：使用TF-IDF或词袋模型
        # 实际实现应该使用预训练的嵌入模型
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        
        # 简单的词袋模型
        words = text.lower().split()
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 创建固定维度的向量（这里使用100维）
        embedding = [0.0] * 100
        for word, freq in word_freq.items():
            # 简单的哈希函数将单词映射到向量维度
            hash_val = hash(word) % 100
            embedding[hash_val] += freq
        
        # 归一化
        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        self._embedding_cache[text] = embedding
        return embedding
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            余弦相似度
        """
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def retrieve(self, query: str, limit: int = 10, 
                memory_types: List[str] = None,
                min_importance: float = 0.0,
                session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        语义检索相关记忆
        
        Args:
            query: 查询文本
            limit: 返回数量限制
            memory_types: 记忆类型过滤
            min_importance: 最小重要性
            session_id: 会话ID过滤
            
        Returns:
            相关记忆列表
        """
        # 获取查询的嵌入向量
        query_embedding = self._get_embedding(query)
        
        # 构建搜索条件
        search_query = {}
        if memory_types:
            search_query["memory_type"] = memory_types
        if min_importance > 0:
            search_query["min_importance"] = min_importance
        if session_id:
            search_query["session_id"] = session_id
        
        # 获取所有匹配的记忆
        all_memories = self.storage.search(search_query, limit=1000)  # 获取更多结果用于排序
        
        # 计算相似度并排序
        scored_memories = []
        for memory in all_memories:
            # 获取记忆的嵌入向量
            memory_embedding = memory.get("embedding")
            if not memory_embedding:
                # 如果没有预计算的嵌入，从内容计算
                memory_embedding = self._get_embedding(memory["content"])
            
            # 计算相似度
            similarity = self._cosine_similarity(query_embedding, memory_embedding)
            
            # 综合评分：相似度 + 重要性 + 访问频率
            importance_score = memory.get("importance", 0.5)
            access_score = min(memory.get("access_count", 0) / 10.0, 1.0)  # 最大为1
            
            # 加权综合评分
            final_score = (
                similarity * 0.6 +  # 相似度权重60%
                importance_score * 0.3 +  # 重要性权重30%
                access_score * 0.1  # 访问频率权重10%
            )
            
            scored_memories.append((memory, final_score))
        
        # 按评分排序
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前limit个结果
        results = []
        for memory, score in scored_memories[:limit]:
            memory["relevance_score"] = score
            results.append(memory)
        
        return results
    
    def retrieve_by_time(self, start_time: float, end_time: float,
                        limit: int = 10) -> List[Dict[str, Any]]:
        """
        按时间检索记忆
        
        Args:
            start_time: 开始时间戳
            end_time: 结束时间戳
            limit: 返回数量限制
            
        Returns:
            时间范围内的记忆列表
        """
        query = {
            "created_after": start_time,
            "created_before": end_time,
            "order_by": "created_at DESC"
        }
        
        return self.storage.search(query, limit)
    
    def retrieve_by_tags(self, tags: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        按标签检索记忆
        
        Args:
            tags: 标签列表
            limit: 返回数量限制
            
        Returns:
            匹配的记忆列表
        """
        query = {"tags": tags}
        return self.storage.search(query, limit)
    
    def retrieve_by_importance(self, min_importance: float,
                              limit: int = 10) -> List[Dict[str, Any]]:
        """
        按重要性检索记忆
        
        Args:
            min_importance: 最小重要性评分
            limit: 返回数量限制
            
        Returns:
            重要记忆列表
        """
        query = {
            "min_importance": min_importance,
            "order_by": "importance DESC, access_count DESC"
        }
        
        return self.storage.search(query, limit)
    
    def retrieve_similar_to_memory(self, memory_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        检索与指定记忆相似的其他记忆
        
        Args:
            memory_id: 记忆ID
            limit: 返回数量限制
            
        Returns:
            相似记忆列表
        """
        # 获取目标记忆
        target_memory = self.storage.retrieve(memory_id)
        if not target_memory:
            return []
        
        # 使用目标记忆的内容作为查询
        query = target_memory["content"]
        
        # 获取所有记忆
        all_memories = self.storage.search({}, limit=1000)
        
        # 计算相似度
        target_embedding = target_memory.get("embedding")
        if not target_embedding:
            target_embedding = self._get_embedding(query)
        
        scored_memories = []
        for memory in all_memories:
            if memory["memory_id"] == memory_id:
                continue  # 跳过自身
            
            memory_embedding = memory.get("embedding")
            if not memory_embedding:
                memory_embedding = self._get_embedding(memory["content"])
            
            similarity = self._cosine_similarity(target_embedding, memory_embedding)
            scored_memories.append((memory, similarity))
        
        # 按相似度排序
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前limit个结果
        results = []
        for memory, score in scored_memories[:limit]:
            memory["similarity_score"] = score
            results.append(memory)
        
        return results
    
    def retrieve_recent(self, hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        """
        检索最近的记忆
        
        Args:
            hours: 小时数
            limit: 返回数量限制
            
        Returns:
            最近记忆列表
        """
        end_time = time.time()
        start_time = end_time - (hours * 60 * 60)
        
        return self.retrieve_by_time(start_time, end_time, limit)
    
    def retrieve_frequently_accessed(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        检索频繁访问的记忆
        
        Args:
            limit: 返回数量限制
            
        Returns:
            频繁访问的记忆列表
        """
        query = {"order_by": "access_count DESC"}
        return self.storage.search(query, limit)
    
    def retrieve_by_content_type(self, content_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        按内容类型检索记忆
        
        Args:
            content_type: 内容类型（如 "code", "text", "data"）
            limit: 返回数量限制
            
        Returns:
            匹配的记忆列表
        """
        # 简单实现：基于关键词匹配
        # 实际实现应该使用更复杂的内容类型检测
        type_keywords = {
            "code": ["def ", "class ", "import ", "function", "var ", "let ", "const "],
            "data": ["json", "csv", "data", "table", "array", "list"],
            "text": ["。", "，", "！", "？", "the", "is", "are"],
        }
        
        keywords = type_keywords.get(content_type, [])
        if not keywords:
            return []
        
        # 构建查询
        query = {"content_like": keywords[0]}  # 简单使用第一个关键词
        
        results = self.storage.search(query, limit)
        
        # 过滤包含其他关键词的结果
        filtered_results = []
        for memory in results:
            content = memory["content"].lower()
            if any(keyword.lower() in content for keyword in keywords):
                filtered_results.append(memory)
        
        return filtered_results


class HybridRetrieval(MemoryRetrieval):
    """混合检索实现（结合语义和关键词）"""
    
    def __init__(self, storage: MemoryStorage, embedding_model: Optional[str] = None):
        """
        初始化混合检索
        
        Args:
            storage: 存储引擎
            embedding_model: 嵌入模型名称
        """
        self.storage = storage
        self.semantic_retrieval = SemanticRetrieval(storage, embedding_model)
    
    def retrieve(self, query: str, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """
        混合检索相关记忆
        
        Args:
            query: 查询文本
            limit: 返回数量限制
            **kwargs: 其他参数
            
        Returns:
            相关记忆列表
        """
        # 语义检索
        semantic_results = self.semantic_retrieval.retrieve(query, limit * 2, **kwargs)
        
        # 关键词检索
        keyword_query = {"content_like": query}
        keyword_results = self.storage.search(keyword_query, limit * 2)
        
        # 合并结果并去重
        seen_ids = set()
        merged_results = []
        
        # 优先语义检索结果
        for memory in semantic_results:
            memory_id = memory["memory_id"]
            if memory_id not in seen_ids:
                seen_ids.add(memory_id)
                merged_results.append(memory)
        
        # 添加关键词检索结果
        for memory in keyword_results:
            memory_id = memory["memory_id"]
            if memory_id not in seen_ids:
                seen_ids.add(memory_id)
                # 为关键词检索结果添加相关性评分
                memory["relevance_score"] = 0.5  # 中等相关性
                merged_results.append(memory)
        
        # 按相关性排序
        merged_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return merged_results[:limit]
    
    def retrieve_by_time(self, start_time: float, end_time: float,
                        limit: int = 10) -> List[Dict[str, Any]]:
        """按时间检索"""
        return self.semantic_retrieval.retrieve_by_time(start_time, end_time, limit)
    
    def retrieve_by_tags(self, tags: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """按标签检索"""
        return self.semantic_retrieval.retrieve_by_tags(tags, limit)
    
    def retrieve_by_importance(self, min_importance: float,
                              limit: int = 10) -> List[Dict[str, Any]]:
        """按重要性检索"""
        return self.semantic_retrieval.retrieve_by_importance(min_importance, limit)
