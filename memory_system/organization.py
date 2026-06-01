"""
记忆组织管理模块

提供记忆的自动分类、标签生成、重要性评分等功能。
"""

import re
import time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
from collections import Counter

from .storage import MemoryStorage


class AutoTagger:
    """自动标签生成器"""
    
    def __init__(self):
        """初始化标签生成器"""
        # 预定义标签规则
        self.tag_rules = {
            # 编程语言
            "python": ["python", "def ", "class ", "import ", "pip", "python3"],
            "javascript": ["javascript", "js", "function", "var ", "let ", "const ", "npm"],
            "typescript": ["typescript", "ts", "interface", "type ", "enum"],
            "java": ["java", "public class", "void ", "int ", "String"],
            "cpp": ["c++", "cpp", "#include", "iostream", "std::"],
            "go": ["golang", "go ", "func ", "package ", "import ("],
            "rust": ["rust", "fn ", "let mut", "impl ", "struct "],
            
            # 技术领域
            "web": ["html", "css", "javascript", "react", "vue", "angular", "node"],
            "data": ["data", "pandas", "numpy", "dataframe", "csv", "json"],
            "ai": ["machine learning", "ml", "ai", "neural", "model", "train"],
            "database": ["sql", "database", "table", "query", "select", "insert"],
            "api": ["api", "rest", "endpoint", "request", "response", "http"],
            "devops": ["docker", "kubernetes", "ci/cd", "deploy", "server"],
            
            # 内容类型
            "code": ["def ", "class ", "function", "import", "return", "if ", "for "],
            "documentation": ["readme", "docs", "documentation", "guide", "tutorial"],
            "error": ["error", "exception", "bug", "issue", "problem", "fix"],
            "question": ["?", "how to", "what is", "why", "can you", "help"],
            "instruction": ["please", "need to", "should", "must", "requirement"],
            
            # 情感/重要性
            "important": ["important", "critical", "urgent", "关键", "重要", "紧急"],
            "todo": ["todo", "fixme", "hack", "workaround", "待办", "需要"],
            "note": ["note", "remember", "注意", "记住", "备注"],
        }
        
        # 标签权重
        self.tag_weights = {
            "python": 1.0,
            "javascript": 1.0,
            "typescript": 1.0,
            "java": 1.0,
            "cpp": 1.0,
            "go": 1.0,
            "rust": 1.0,
            "web": 0.8,
            "data": 0.8,
            "ai": 0.9,
            "database": 0.8,
            "api": 0.8,
            "devops": 0.7,
            "code": 0.9,
            "documentation": 0.6,
            "error": 0.7,
            "question": 0.5,
            "instruction": 0.6,
            "important": 1.0,
            "todo": 0.8,
            "note": 0.6,
        }
    
    def generate_tags(self, content: str, max_tags: int = 5) -> List[str]:
        """
        生成标签
        
        Args:
            content: 文本内容
            max_tags: 最大标签数量
            
        Returns:
            标签列表
        """
        if not content:
            return []
        
        content_lower = content.lower()
        tag_scores: Dict[str, float] = {}
        
        # 应用规则匹配
        for tag, keywords in self.tag_rules.items():
            score = 0.0
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    score += 1.0
            
            if score > 0:
                # 应用标签权重
                weight = self.tag_weights.get(tag, 0.5)
                tag_scores[tag] = score * weight
        
        # 按分数排序
        sorted_tags = sorted(tag_scores.items(), key=lambda x: x[1], reverse=True)
        
        # 返回前max_tags个标签
        return [tag for tag, score in sorted_tags[:max_tags]]
    
    def extract_entities(self, content: str) -> Dict[str, List[str]]:
        """
        提取实体
        
        Args:
            content: 文本内容
            
        Returns:
            实体字典
        """
        entities = {
            "urls": [],
            "emails": [],
            "files": [],
            "functions": [],
            "classes": [],
            "variables": [],
        }
        
        # URL提取
        url_pattern = r'https?://[^\s]+'
        entities["urls"] = re.findall(url_pattern, content)
        
        # 邮箱提取
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities["emails"] = re.findall(email_pattern, content)
        
        # 文件路径提取
        file_pattern = r'[/\\][\w/\\.-]+\.\w+'
        entities["files"] = re.findall(file_pattern, content)
        
        # 函数定义提取
        func_patterns = [
            r'def\s+(\w+)\s*\(',  # Python
            r'function\s+(\w+)\s*\(',  # JavaScript
            r'(\w+)\s*=\s*function\s*\(',  # JavaScript
            r'(\w+)\s*=\s*\([^)]*\)\s*=>',  # JavaScript箭头函数
        ]
        for pattern in func_patterns:
            entities["functions"].extend(re.findall(pattern, content))
        
        # 类定义提取
        class_patterns = [
            r'class\s+(\w+)',  # Python/Java
            r'interface\s+(\w+)',  # TypeScript/Java
        ]
        for pattern in class_patterns:
            entities["classes"].extend(re.findall(pattern, content))
        
        # 变量提取（简单实现）
        var_patterns = [
            r'(\w+)\s*=\s*',  # 赋值语句
            r'let\s+(\w+)',  # JavaScript let
            r'const\s+(\w+)',  # JavaScript const
            r'var\s+(\w+)',  # JavaScript var
        ]
        for pattern in var_patterns:
            entities["variables"].extend(re.findall(pattern, content))
        
        # 去重
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities


class ImportanceScorer:
    """重要性评分器"""
    
    def __init__(self):
        """初始化重要性评分器"""
        # 重要性关键词
        self.importance_keywords = {
            "high": [
                "important", "critical", "urgent", "关键", "重要", "紧急",
                "must", "required", "necessary", "必须", "需要", "必要",
                "error", "bug", "fix", "issue", "problem", "错误", "问题",
                "security", "vulnerability", "安全", "漏洞",
            ],
            "medium": [
                "should", "recommend", "建议", "应该",
                "improve", "optimize", "优化", "改进",
                "update", "change", "更新", "修改",
                "note", "remember", "注意", "记住",
            ],
            "low": [
                "example", "demo", "示例", "演示",
                "test", "experiment", "测试", "实验",
                "temporary", "temp", "临时", "暂时",
                "comment", "remark", "注释", "备注",
            ]
        }
        
        # 评分权重
        self.score_weights = {
            "high": 0.9,
            "medium": 0.6,
            "low": 0.3,
        }
    
    def calculate_importance(self, content: str, 
                           access_count: int = 0,
                           age_days: float = 0) -> float:
        """
        计算重要性评分
        
        Args:
            content: 文本内容
            access_count: 访问次数
            age_days: 年龄（天）
            
        Returns:
            重要性评分 (0.0-1.0)
        """
        if not content:
            return 0.0
        
        content_lower = content.lower()
        base_score = 0.5  # 基础分数
        
        # 关键词评分
        keyword_score = 0.0
        for level, keywords in self.importance_keywords.items():
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    keyword_score = max(keyword_score, self.score_weights[level])
                    break
        
        # 访问频率评分（访问越多越重要）
        access_score = min(access_count / 10.0, 1.0)  # 最大为1
        
        # 新鲜度评分（越新越重要）
        freshness_score = max(1.0 - (age_days / 30.0), 0.0)  # 30天内保持高分
        
        # 内容长度评分（较长的内容可能更重要）
        length_score = min(len(content) / 1000.0, 1.0)  # 最大为1
        
        # 加权综合评分
        final_score = (
            base_score * 0.2 +
            keyword_score * 0.4 +
            access_score * 0.2 +
            freshness_score * 0.1 +
            length_score * 0.1
        )
        
        return min(final_score, 1.0)
    
    def update_importance(self, memory_data: Dict[str, Any]) -> float:
        """
        更新重要性评分
        
        Args:
            memory_data: 记忆数据
            
        Returns:
            新的重要性评分
        """
        content = memory_data.get("content", "")
        access_count = memory_data.get("access_count", 0)
        created_at = memory_data.get("created_at", time.time())
        
        # 计算年龄（天）
        age_seconds = time.time() - created_at
        age_days = age_seconds / (24 * 60 * 60)
        
        return self.calculate_importance(content, access_count, age_days)


class MemoryOrganization:
    """记忆组织管理器"""
    
    def __init__(self, storage: MemoryStorage):
        """
        初始化记忆组织管理器
        
        Args:
            storage: 存储引擎
        """
        self.storage = storage
        self.tagger = AutoTagger()
        self.scorer = ImportanceScorer()
    
    def auto_tag_memory(self, memory_id: str) -> List[str]:
        """
        自动为记忆生成标签
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            生成的标签列表
        """
        memory_data = self.storage.retrieve(memory_id)
        if not memory_data:
            return []
        
        content = memory_data.get("content", "")
        existing_tags = memory_data.get("tags", [])
        
        # 生成新标签
        new_tags = self.tagger.generate_tags(content)
        
        # 合并标签（去重）
        all_tags = list(set(existing_tags + new_tags))
        
        # 更新记忆
        self.storage.update(memory_id, {"tags": all_tags})
        
        return all_tags
    
    def auto_score_importance(self, memory_id: str) -> float:
        """
        自动计算重要性评分
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            重要性评分
        """
        memory_data = self.storage.retrieve(memory_id)
        if not memory_data:
            return 0.0
        
        # 计算新重要性
        new_importance = self.scorer.update_importance(memory_data)
        
        # 更新记忆
        self.storage.update(memory_id, {"importance": new_importance})
        
        return new_importance
    
    def categorize_memory(self, memory_id: str) -> str:
        """
        对记忆进行分类
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            分类结果
        """
        memory_data = self.storage.retrieve(memory_id)
        if not memory_data:
            return "unknown"
        
        content = memory_data.get("content", "").lower()
        tags = memory_data.get("tags", [])
        
        # 基于内容和标签的分类规则
        if any(tag in tags for tag in ["code", "python", "javascript", "java", "cpp", "go", "rust"]):
            return "code"
        elif any(tag in tags for tag in ["documentation", "readme", "guide"]):
            return "documentation"
        elif any(tag in tags for tag in ["error", "bug", "issue"]):
            return "error"
        elif any(tag in tags for tag in ["question", "help"]):
            return "question"
        elif any(tag in tags for tag in ["todo", "task"]):
            return "task"
        elif any(tag in tags for tag in ["note", "remember"]):
            return "note"
        else:
            # 基于内容的简单分类
            if "def " in content or "class " in content or "function" in content:
                return "code"
            elif "?" in content or "how to" in content or "what is" in content:
                return "question"
            elif "todo" in content or "fixme" in content:
                return "task"
            else:
                return "general"
    
    def organize_memories(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        组织记忆（批量处理）
        
        Args:
            session_id: 会话ID（可选）
            
        Returns:
            组织统计信息
        """
        # 获取所有记忆
        if session_id:
            query = {"session_id": session_id}
        else:
            query = {}
        
        memories = self.storage.search(query, limit=1000)
        
        stats = {
            "total_memories": len(memories),
            "tagged_memories": 0,
            "scored_memories": 0,
            "categorized_memories": 0,
            "categories": Counter(),
            "tags": Counter(),
        }
        
        for memory in memories:
            memory_id = memory["memory_id"]
            
            # 自动标签
            tags = self.auto_tag_memory(memory_id)
            if tags:
                stats["tagged_memories"] += 1
                stats["tags"].update(tags)
            
            # 自动评分
            importance = self.auto_score_importance(memory_id)
            if importance > 0:
                stats["scored_memories"] += 1
            
            # 自动分类
            category = self.categorize_memory(memory_id)
            stats["categorized_memories"] += 1
            stats["categories"][category] += 1
        
        return stats
    
    def get_memory_clusters(self, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取记忆聚类
        
        Args:
            limit: 每个聚类的最大记忆数
            
        Returns:
            按类别分组的记忆
        """
        memories = self.storage.search({}, limit=1000)
        
        clusters: Dict[str, List[Dict[str, Any]]] = {}
        
        for memory in memories:
            # 获取或计算类别
            memory_id = memory["memory_id"]
            category = self.categorize_memory(memory_id)
            
            if category not in clusters:
                clusters[category] = []
            
            if len(clusters[category]) < limit:
                clusters[category].append(memory)
        
        return clusters
    
    def get_related_memories(self, memory_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        获取相关记忆
        
        Args:
            memory_id: 记忆ID
            limit: 返回数量限制
            
        Returns:
            相关记忆列表
        """
        memory_data = self.storage.retrieve(memory_id)
        if not memory_data:
            return []
        
        # 获取相同标签的记忆
        tags = memory_data.get("tags", [])
        if not tags:
            return []
        
        related_memories = []
        for tag in tags:
            query = {"tags": [tag]}
            memories = self.storage.search(query, limit=limit * 2)
            
            for memory in memories:
                if memory["memory_id"] != memory_id:
                    related_memories.append(memory)
        
        # 去重
        seen_ids = set()
        unique_memories = []
        for memory in related_memories:
            if memory["memory_id"] not in seen_ids:
                seen_ids.add(memory["memory_id"])
                unique_memories.append(memory)
        
        return unique_memories[:limit]
    
    def get_memory_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取记忆摘要
        
        Args:
            session_id: 会话ID（可选）
            
        Returns:
            记忆摘要
        """
        if session_id:
            query = {"session_id": session_id}
        else:
            query = {}
        
        memories = self.storage.search(query, limit=1000)
        
        if not memories:
            return {
                "total_memories": 0,
                "categories": {},
                "top_tags": [],
                "avg_importance": 0.0,
                "most_accessed": None,
            }
        
        # 统计信息
        categories = Counter()
        tags = Counter()
        importance_sum = 0.0
        most_accessed = None
        max_access = 0
        
        for memory in memories:
            # 类别统计
            category = self.categorize_memory(memory["memory_id"])
            categories[category] += 1
            
            # 标签统计
            for tag in memory.get("tags", []):
                tags[tag] += 1
            
            # 重要性统计
            importance_sum += memory.get("importance", 0.0)
            
            # 访问次数统计
            access_count = memory.get("access_count", 0)
            if access_count > max_access:
                max_access = access_count
                most_accessed = memory
        
        return {
            "total_memories": len(memories),
            "categories": dict(categories),
            "top_tags": tags.most_common(10),
            "avg_importance": importance_sum / len(memories),
            "most_accessed": most_accessed,
        }
