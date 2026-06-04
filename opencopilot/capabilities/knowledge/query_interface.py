"""
查询接口模块

提供高级查询接口和查询类型定义。
"""

from enum import Enum
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """查询类型枚举"""
    AUTO = "auto"              # 自动识别
    ENTITY = "entity"          # 实体查询
    RELATION = "relation"      # 关系查询
    PATH = "path"              # 路径查询
    COMPONENT = "component"    # 组件查询
    API = "api"                # API查询
    FEATURE = "feature"        # 功能查询
    DOCUMENT = "document"      # 文档查询
    CONTEXT = "context"        # 上下文查询
    STATISTICS = "statistics"  # 统计查询


class QueryInterface:
    """
    查询接口类
    
    提供高级查询接口，支持复杂的查询逻辑。
    """
    
    def __init__(self, knowledge_retrieval):
        """
        初始化查询接口
        
        Args:
            knowledge_retrieval: 知识检索实例
        """
        self.retrieval = knowledge_retrieval
    
    def search_by_keyword(self, keyword: str, search_type: str = "all") -> Dict[str, Any]:
        """
        关键词搜索
        
        Args:
            keyword: 搜索关键词
            search_type: 搜索类型 (all/entity/component/api/feature/document)
            
        Returns:
            搜索结果
        """
        results = {}
        
        if search_type == "all" or search_type == "entity":
            entity_result = self.retrieval.find_entity(keyword)
            if entity_result.success:
                results["entities"] = [e.to_dict() for e in entity_result.data]
        
        if search_type == "all" or search_type == "component":
            component_result = self.retrieval.query(keyword, "component")
            if component_result.success:
                results["components"] = [c.to_dict() for c in component_result.data]
        
        if search_type == "all" or search_type == "api":
            api_result = self.retrieval.query(keyword, "api")
            if api_result.success:
                results["apis"] = [a.to_dict() for a in api_result.data]
        
        if search_type == "all" or search_type == "feature":
            feature_result = self.retrieval.query(keyword, "feature")
            if feature_result.success:
                results["features"] = [f.to_dict() for f in feature_result.data]
        
        if search_type == "all" or search_type == "document":
            doc_result = self.retrieval.query(keyword, "document")
            if doc_result.success:
                results["documents"] = [d.to_dict() for d in doc_result.data]
        
        return {
            "keyword": keyword,
            "search_type": search_type,
            "results": results,
            "total_count": sum(len(v) for v in results.values())
        }
    
    def get_entity_full_info(self, entity_id: str) -> Dict[str, Any]:
        """
        获取实体完整信息
        
        Args:
            entity_id: 实体ID
            
        Returns:
            实体完整信息
        """
        # 获取实体详情
        entity_result = self.retrieval.query(f"id:{entity_id}", "entity")
        if not entity_result.success or not entity_result.data:
            return {"error": f"实体不存在: {entity_id}"}
        
        entity = entity_result.data[0]
        
        # 获取相关实体
        related_result = self.retrieval.find_related(entity_id, max_depth=1)
        related_entities = []
        related_relations = []
        
        if related_result.success:
            related_entities = [e.to_dict() for e in related_result.data.get("entities", []) if e.id != entity_id]
            related_relations = [r.to_dict() for r in related_result.data.get("relations", [])]
        
        # 获取上下文
        context_result = self.retrieval.get_entity_context(entity_id)
        context = context_result.data if context_result.success else {}
        
        return {
            "entity": entity.to_dict(),
            "related_entities": related_entities,
            "relations": related_relations,
            "context": context,
            "statistics": {
                "related_count": len(related_entities),
                "relation_count": len(related_relations)
            }
        }
    
    def find_dependency_chain(self, entity_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """
        查找依赖链
        
        Args:
            entity_id: 实体ID
            max_depth: 最大深度
            
        Returns:
            依赖链信息
        """
        # 查找依赖关系
        depends_result = self.retrieval.find_related(entity_id, "depends_on", max_depth)
        
        # 查找被依赖关系
        depended_by_result = self.retrieval.query(
            "", "relation",
            target_id=entity_id,
            relation_type="depends_on"
        )
        
        return {
            "entity_id": entity_id,
            "depends_on": depends_result.data if depends_result.success else [],
            "depended_by": depended_by_result.data if depended_by_result.success else [],
            "max_depth": max_depth
        }
    
    def find_implementation_chain(self, entity_id: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        查找实现链
        
        Args:
            entity_id: 实体ID
            max_depth: 最大深度
            
        Returns:
            实现链信息
        """
        # 查找实现关系
        implements_result = self.retrieval.find_related(entity_id, "implements", max_depth)
        
        # 查找被实现关系
        implemented_by_result = self.retrieval.query(
            "", "relation",
            target_id=entity_id,
            relation_type="implements"
        )
        
        return {
            "entity_id": entity_id,
            "implements": implements_result.data if implements_result.success else [],
            "implemented_by": implemented_by_result.data if implemented_by_result.success else [],
            "max_depth": max_depth
        }
    
    def find_documentation(self, entity_id: str) -> Dict[str, Any]:
        """
        查找相关文档
        
        Args:
            entity_id: 实体ID
            
        Returns:
            相关文档信息
        """
        # 获取实体相关文档
        doc_result = self.retrieval.query("", "document", entity_id=entity_id)
        
        # 获取文档关系
        relation_result = self.retrieval.query(
            "", "relation",
            source_id=entity_id,
            relation_type="documents"
        )
        
        return {
            "entity_id": entity_id,
            "documents": doc_result.data if doc_result.success else [],
            "document_relations": relation_result.data if relation_result.success else []
        }
    
    def find_tests(self, entity_id: str) -> Dict[str, Any]:
        """
        查找相关测试
        
        Args:
            entity_id: 实体ID
            
        Returns:
            相关测试信息
        """
        # 获取测试关系
        test_result = self.retrieval.query(
            "", "relation",
            target_id=entity_id,
            relation_type="tests"
        )
        
        # 获取测试实体
        test_entities = []
        if test_result.success:
            for relation in test_result.data:
                test_entity_result = self.retrieval.query(relation.source_id, "entity")
                if test_entity_result.success and test_entity_result.data:
                    test_entities.append(test_entity_result.data[0])
        
        return {
            "entity_id": entity_id,
            "test_relations": test_result.data if test_result.success else [],
            "test_entities": [t.to_dict() for t in test_entities]
        }
    
    def find_similar_entities(self, entity_id: str, similarity_threshold: float = 0.5) -> Dict[str, Any]:
        """
        查找相似实体
        
        Args:
            entity_id: 实体ID
            similarity_threshold: 相似度阈值
            
        Returns:
            相似实体信息
        """
        # 获取目标实体
        target_result = self.retrieval.query(entity_id, "entity")
        if not target_result.success or not target_result.data:
            return {"error": f"实体不存在: {entity_id}"}
        
        target_entity = target_result.data[0]
        
        # 获取所有同类型实体
        all_entities_result = self.retrieval.query("", target_entity.entity_type.value)
        if not all_entities_result.success:
            return {"error": "获取实体列表失败"}
        
        # 计算相似度
        similar_entities = []
        for entity in all_entities_result.data:
            if entity.id == entity_id:
                continue
            
            # 简单的相似度计算（基于名称和描述）
            similarity = self._calculate_similarity(target_entity, entity)
            if similarity >= similarity_threshold:
                similar_entities.append({
                    "entity": entity.to_dict(),
                    "similarity": similarity
                })
        
        # 按相似度排序
        similar_entities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return {
            "entity_id": entity_id,
            "entity_name": target_entity.name,
            "similar_entities": similar_entities[:10],  # 返回前10个
            "total_count": len(similar_entities)
        }
    
    def _calculate_similarity(self, entity1, entity2) -> float:
        """
        计算两个实体的相似度
        
        Args:
            entity1: 实体1
            entity2: 实体2
            
        Returns:
            相似度分数 (0-1)
        """
        # 名称相似度
        name_similarity = self._string_similarity(entity1.name, entity2.name)
        
        # 描述相似度
        desc_similarity = self._string_similarity(entity1.description, entity2.description)
        
        # 关键词重叠度
        keywords1 = set(entity1.name.lower().split() + entity1.description.lower().split())
        keywords2 = set(entity2.name.lower().split() + entity2.description.lower().split())
        
        if keywords1 and keywords2:
            keyword_overlap = len(keywords1.intersection(keywords2)) / len(keywords1.union(keywords2))
        else:
            keyword_overlap = 0
        
        # 加权平均
        return (name_similarity * 0.4 + desc_similarity * 0.3 + keyword_overlap * 0.3)
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """
        计算字符串相似度
        
        Args:
            str1: 字符串1
            str2: 字符串2
            
        Returns:
            相似度分数 (0-1)
        """
        if not str1 or not str2:
            return 0.0
        
        # 简单的包含关系检查
        str1_lower = str1.lower()
        str2_lower = str2.lower()
        
        if str1_lower in str2_lower or str2_lower in str1_lower:
            return 0.8
        
        # 计算公共子串比例
        common_chars = set(str1_lower) & set(str2_lower)
        total_chars = set(str1_lower) | set(str2_lower)
        
        if not total_chars:
            return 0.0
        
        return len(common_chars) / len(total_chars)
