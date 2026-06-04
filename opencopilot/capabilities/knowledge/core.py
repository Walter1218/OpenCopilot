"""
知识检索核心模块

提供统一的知识检索接口，封装底层知识图谱功能。
"""

import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path

# 添加项目根目录到路径

from knowledge_graph.graph import GraphManager
from knowledge_graph.query import QueryEngine
from knowledge_graph.models import Entity, Relation, EntityType, RelationType

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """检索结果"""
    success: bool = True
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "success": self.success,
            "metadata": self.metadata
        }
        
        if self.success:
            if isinstance(self.data, list):
                result["data"] = [item.to_dict() if hasattr(item, 'to_dict') else item for item in self.data]
            elif hasattr(self.data, 'to_dict'):
                result["data"] = self.data.to_dict()
            else:
                result["data"] = self.data
        else:
            result["error"] = self.error
        
        return result


class KnowledgeRetrieval:
    """
    知识检索类
    
    提供统一的知识检索接口，封装底层知识图谱功能。
    """
    
    def __init__(self, project_root: str = None, graph_file: str = None):
        """
        初始化知识检索
        
        Args:
            project_root: 项目根目录，默认为当前文件的父目录
            graph_file: 知识图谱存储文件路径
        """
        if project_root is None:
            project_root = str(Path(__file__).parent.parent)
        
        self.project_root = Path(project_root)
        self.graph_manager = GraphManager(project_root, graph_file)
        self.query_engine = None
        self._initialized = False
        
        logger.info(f"知识检索初始化: {project_root}")
    
    def initialize(self, force_rebuild: bool = False) -> RetrievalResult:
        """
        初始化知识图谱
        
        Args:
            force_rebuild: 是否强制重建图谱
            
        Returns:
            初始化结果
        """
        try:
            # 构建图谱
            knowledge_graph = self.graph_manager.build_graph(force_rebuild)
            
            # 创建查询引擎
            self.query_engine = QueryEngine(knowledge_graph)
            self._initialized = True
            
            stats = knowledge_graph.get_statistics()
            logger.info(f"知识图谱初始化完成: {stats}")
            
            return RetrievalResult(
                success=True,
                data=stats,
                metadata={"action": "initialize"}
            )
        except Exception as e:
            logger.error(f"知识图谱初始化失败: {e}")
            return RetrievalResult(
                success=False,
                error=str(e),
                metadata={"action": "initialize"}
            )
    
    def _ensure_initialized(self) -> bool:
        """确保已初始化"""
        if not self._initialized:
            result = self.initialize()
            return result.success
        return True
    
    def query(self, query_text: str, query_type: str = "auto", **kwargs) -> RetrievalResult:
        """
        统一查询接口
        
        Args:
            query_text: 查询文本
            query_type: 查询类型 (auto/entity/relation/path/component/api/feature/document)
            **kwargs: 其他查询参数
            
        Returns:
            查询结果
        """
        if not self._ensure_initialized():
            return RetrievalResult(success=False, error="知识图谱未初始化")
        
        try:
            # 自动识别查询类型
            if query_type == "auto":
                query_type = self._detect_query_type(query_text)
            
            # 根据类型执行查询
            if query_type == "entity":
                return self._query_entity(query_text, **kwargs)
            elif query_type == "relation":
                return self._query_relation(**kwargs)
            elif query_type == "path":
                return self._query_path(**kwargs)
            elif query_type == "component":
                return self._query_component(query_text, **kwargs)
            elif query_type == "api":
                return self._query_api(query_text, **kwargs)
            elif query_type == "feature":
                return self._query_feature(query_text, **kwargs)
            elif query_type == "document":
                return self._query_document(query_text, **kwargs)
            else:
                # 默认执行实体搜索
                return self._query_entity(query_text, **kwargs)
        
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return RetrievalResult(success=False, error=str(e))
    
    def _detect_query_type(self, query_text: str) -> str:
        """自动检测查询类型"""
        query_lower = query_text.lower()
        
        # 关键词映射
        keywords = {
            "component": ["组件", "模块", "component", "module"],
            "api": ["api", "接口", "端点", "endpoint"],
            "feature": ["功能", "特性", "feature", "能力"],
            "document": ["文档", "document", "doc", "指南"],
            "path": ["路径", "path", "关系链"],
            "relation": ["关系", "relation", "依赖", "连接"]
        }
        
        for qtype, kws in keywords.items():
            for kw in kws:
                if kw in query_lower:
                    return qtype
        
        return "entity"
    
    def _query_entity(self, query_text: str, entity_type: str = None, **kwargs) -> RetrievalResult:
        """查询实体"""
        # 转换实体类型
        etype = None
        if entity_type:
            try:
                etype = EntityType(entity_type)
            except ValueError:
                pass
        
        entities = self.graph_manager.search_entities(query_text, etype)
        
        return RetrievalResult(
            success=True,
            data=entities,
            metadata={
                "query_type": "entity",
                "query": query_text,
                "entity_type": entity_type,
                "count": len(entities)
            }
        )
    
    def _query_relation(self, source_id: str = None, target_id: str = None, 
                       relation_type: str = None, **kwargs) -> RetrievalResult:
        """查询关系"""
        results = []
        
        for relation in self.graph_manager.knowledge_graph.relations.values():
            # 过滤条件
            if source_id and relation.source_id != source_id:
                continue
            if target_id and relation.target_id != target_id:
                continue
            if relation_type and relation.relation_type.value != relation_type:
                continue
            
            results.append(relation)
        
        return RetrievalResult(
            success=True,
            data=results,
            metadata={
                "query_type": "relation",
                "source_id": source_id,
                "target_id": target_id,
                "relation_type": relation_type,
                "count": len(results)
            }
        )
    
    def _query_path(self, source_id: str = None, target_id: str = None, 
                   max_depth: int = 3, **kwargs) -> RetrievalResult:
        """查询路径"""
        if not source_id or not target_id:
            return RetrievalResult(
                success=False,
                error="路径查询需要 source_id 和 target_id"
            )
        
        paths = self.query_engine.find_path(source_id, target_id, max_depth)
        
        return RetrievalResult(
            success=True,
            data=paths,
            metadata={
                "query_type": "path",
                "source_id": source_id,
                "target_id": target_id,
                "max_depth": max_depth,
                "count": len(paths)
            }
        )
    
    def _query_component(self, feature: str = None, component_type: str = None, **kwargs) -> RetrievalResult:
        """查询组件"""
        if feature:
            components = self.query_engine.find_components_by_feature(feature)
        else:
            components = self.graph_manager.search_entities("", EntityType.COMPONENT)
        
        # 按类型过滤
        if component_type:
            components = [c for c in components if component_type.lower() in c.name.lower()]
        
        return RetrievalResult(
            success=True,
            data=components,
            metadata={
                "query_type": "component",
                "feature": feature,
                "component_type": component_type,
                "count": len(components)
            }
        )
    
    def _query_api(self, component: str = None, api_type: str = None, **kwargs) -> RetrievalResult:
        """查询API"""
        if component:
            apis = self.query_engine.find_apis_by_component(component)
        else:
            apis = self.graph_manager.search_entities("", EntityType.API)
        
        # 按类型过滤
        if api_type:
            apis = [a for a in apis if api_type.lower() in a.properties.get('api_type', '').lower()]
        
        return RetrievalResult(
            success=True,
            data=apis,
            metadata={
                "query_type": "api",
                "component": component,
                "api_type": api_type,
                "count": len(apis)
            }
        )
    
    def _query_feature(self, category: str = None, **kwargs) -> RetrievalResult:
        """查询功能"""
        features = self.graph_manager.search_entities("", EntityType.FEATURE)
        
        # 按类别过滤
        if category:
            features = [f for f in features if category.lower() in f.description.lower()]
        
        return RetrievalResult(
            success=True,
            data=features,
            metadata={
                "query_type": "feature",
                "category": category,
                "count": len(features)
            }
        )
    
    def _query_document(self, doc_type: str = None, entity_id: str = None, **kwargs) -> RetrievalResult:
        """查询文档"""
        if entity_id:
            documents = self.query_engine.find_documents_by_entity(entity_id)
            docs = []
            for doc_path in documents:
                doc_entities = self.graph_manager.get_entity_by_name(doc_path)
                if doc_entities:
                    docs.append(doc_entities[0])
        else:
            docs = self.graph_manager.search_entities("", EntityType.DOCUMENT)
        
        # 按类型过滤
        if doc_type:
            docs = [d for d in docs if doc_type.lower() in d.properties.get('doc_type', '').lower()]
        
        return RetrievalResult(
            success=True,
            data=docs,
            metadata={
                "query_type": "document",
                "doc_type": doc_type,
                "entity_id": entity_id,
                "count": len(docs)
            }
        )
    
    def find_entity(self, name: str, entity_type: str = None) -> RetrievalResult:
        """
        查找实体
        
        Args:
            name: 实体名称
            entity_type: 实体类型
            
        Returns:
            查找结果
        """
        if not self._ensure_initialized():
            return RetrievalResult(success=False, error="知识图谱未初始化")
        
        try:
            etype = None
            if entity_type:
                try:
                    etype = EntityType(entity_type)
                except ValueError:
                    pass
            
            entities = self.query_engine.find_entity(name, etype)
            
            return RetrievalResult(
                success=True,
                data=entities,
                metadata={
                    "action": "find_entity",
                    "name": name,
                    "entity_type": entity_type,
                    "count": len(entities)
                }
            )
        except Exception as e:
            logger.error(f"查找实体失败: {e}")
            return RetrievalResult(success=False, error=str(e))
    
    def find_related(self, entity_id: str, relation_type: str = None, 
                    max_depth: int = 1) -> RetrievalResult:
        """
        查找相关实体
        
        Args:
            entity_id: 实体ID
            relation_type: 关系类型
            max_depth: 最大深度
            
        Returns:
            相关实体结果
        """
        if not self._ensure_initialized():
            return RetrievalResult(success=False, error="知识图谱未初始化")
        
        try:
            rtype = None
            if relation_type:
                try:
                    rtype = RelationType(relation_type)
                except ValueError:
                    pass
            
            result = self.query_engine.find_related_entities(entity_id, rtype, max_depth)
            
            return RetrievalResult(
                success=True,
                data=result,
                metadata={
                    "action": "find_related",
                    "entity_id": entity_id,
                    "relation_type": relation_type,
                    "max_depth": max_depth,
                    "count": result["count"]
                }
            )
        except Exception as e:
            logger.error(f"查找相关实体失败: {e}")
            return RetrievalResult(success=False, error=str(e))
    
    def find_path(self, source_id: str, target_id: str, 
                 max_depth: int = 3) -> RetrievalResult:
        """
        查找路径
        
        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            max_depth: 最大深度
            
        Returns:
            路径结果
        """
        if not self._ensure_initialized():
            return RetrievalResult(success=False, error="知识图谱未初始化")
        
        try:
            paths = self.query_engine.find_path(source_id, target_id, max_depth)
            
            return RetrievalResult(
                success=True,
                data=paths,
                metadata={
                    "action": "find_path",
                    "source_id": source_id,
                    "target_id": target_id,
                    "max_depth": max_depth,
                    "count": len(paths)
                }
            )
        except Exception as e:
            logger.error(f"查找路径失败: {e}")
            return RetrievalResult(success=False, error=str(e))
    
    def build(self, force_rebuild: bool = False) -> RetrievalResult:
        """
        构建/重建知识图谱
        
        Args:
            force_rebuild: 是否强制重建
            
        Returns:
            构建结果
        """
        return self.initialize(force_rebuild)
    
    def get_statistics(self) -> RetrievalResult:
        """
        获取统计信息
        
        Returns:
            统计信息结果
        """
        if not self._ensure_initialized():
            return RetrievalResult(success=False, error="知识图谱未初始化")
        
        try:
            stats = self.graph_manager.get_statistics()
            stats_by_type = self.query_engine.get_statistics_by_type()
            
            return RetrievalResult(
                success=True,
                data={
                    "total": stats,
                    "by_type": stats_by_type
                },
                metadata={"action": "get_statistics"}
            )
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return RetrievalResult(success=False, error=str(e))
    
    def get_entity_context(self, entity_id: str) -> RetrievalResult:
        """
        获取实体上下文
        
        Args:
            entity_id: 实体ID
            
        Returns:
            实体上下文结果
        """
        if not self._ensure_initialized():
            return RetrievalResult(success=False, error="知识图谱未初始化")
        
        try:
            context = self.query_engine.get_entity_context(entity_id)
            
            if not context:
                return RetrievalResult(
                    success=False,
                    error=f"实体不存在: {entity_id}"
                )
            
            return RetrievalResult(
                success=True,
                data=context,
                metadata={"action": "get_entity_context", "entity_id": entity_id}
            )
        except Exception as e:
            logger.error(f"获取实体上下文失败: {e}")
            return RetrievalResult(success=False, error=str(e))
    
    def export_json(self, output_file: str = None) -> RetrievalResult:
        """
        导出为JSON
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            导出结果
        """
        if not self._ensure_initialized():
            return RetrievalResult(success=False, error="知识图谱未初始化")
        
        try:
            file_path = self.graph_manager.export_to_json(output_file)
            
            return RetrievalResult(
                success=True,
                data={"file_path": file_path},
                metadata={"action": "export_json"}
            )
        except Exception as e:
            logger.error(f"导出JSON失败: {e}")
            return RetrievalResult(success=False, error=str(e))
    
    def generate_report(self) -> RetrievalResult:
        """
        生成报告
        
        Returns:
            报告结果
        """
        if not self._ensure_initialized():
            return RetrievalResult(success=False, error="知识图谱未初始化")
        
        try:
            report = self.graph_manager.generate_report()
            
            return RetrievalResult(
                success=True,
                data=report,
                metadata={"action": "generate_report"}
            )
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            return RetrievalResult(success=False, error=str(e))
