"""
知识图谱查询引擎

提供多种查询方式：实体查询、关系查询、路径查询等。
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import logging

from .models import Entity, Relation, EntityType, RelationType, KnowledgeGraph

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """查询结果"""
    entities: List[Entity]
    relations: List[Relation]
    paths: List[List[str]]  # 实体ID路径
    metadata: Dict[str, Any]


class QueryEngine:
    """查询引擎"""
    
    def __init__(self, knowledge_graph: KnowledgeGraph):
        """
        初始化查询引擎
        
        Args:
            knowledge_graph: 知识图谱
        """
        self.graph = knowledge_graph
    
    def find_entity(self, name: str, entity_type: Optional[EntityType] = None) -> List[Entity]:
        """
        查找实体
        
        Args:
            name: 实体名称
            entity_type: 实体类型过滤
            
        Returns:
            匹配的实体列表
        """
        results = []
        
        # 精确匹配
        exact_matches = self.graph.get_entity_by_name(name)
        for entity in exact_matches:
            if entity_type is None or entity.entity_type == entity_type:
                results.append(entity)
        
        # 模糊匹配
        if not results:
            for entity in self.graph.entities.values():
                if entity_type and entity.entity_type != entity_type:
                    continue
                
                if (name.lower() in entity.name.lower() or 
                    name.lower() in entity.description.lower()):
                    results.append(entity)
        
        return results
    
    def find_related_entities(self, entity_id: str, 
                            relation_type: Optional[RelationType] = None,
                            max_depth: int = 1) -> Dict[str, Any]:
        """
        查找相关实体
        
        Args:
            entity_id: 实体ID
            relation_type: 关系类型过滤
            max_depth: 最大深度
            
        Returns:
            相关实体和关系
        """
        visited = set()
        result_entities = []
        result_relations = []
        
        def dfs(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            entity = self.graph.get_entity(current_id)
            if entity:
                result_entities.append(entity)
            
            # 获取关系
            relations = self.graph.get_relations_for_entity(current_id)
            if relation_type:
                relations = [r for r in relations if r.relation_type == relation_type]
            
            for relation in relations:
                result_relations.append(relation)
                next_id = relation.target_id if relation.source_id == current_id else relation.source_id
                dfs(next_id, depth + 1)
        
        dfs(entity_id, 0)
        
        return {
            "entities": result_entities,
            "relations": result_relations,
            "count": len(result_entities)
        }
    
    def find_path(self, source_id: str, target_id: str, max_depth: int = 3) -> List[List[str]]:
        """
        查找两个实体之间的路径
        
        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            max_depth: 最大深度
            
        Returns:
            路径列表
        """
        paths = []
        
        def dfs(current_id: str, path: List[str], visited: Set[str]):
            if len(path) > max_depth + 1:
                return
            
            if current_id == target_id:
                paths.append(path.copy())
                return
            
            if current_id in visited:
                return
            
            visited.add(current_id)
            
            # 获取关系
            relations = self.graph.get_relations_for_entity(current_id)
            for relation in relations:
                next_id = relation.target_id if relation.source_id == current_id else relation.source_id
                path.append(next_id)
                dfs(next_id, path, visited)
                path.pop()
            
            visited.remove(current_id)
        
        dfs(source_id, [source_id], set())
        return paths
    
    def find_components_by_feature(self, feature_name: str) -> List[Entity]:
        """
        根据功能查找相关组件
        
        Args:
            feature_name: 功能名称
            
        Returns:
            相关组件列表
        """
        # 先查找功能实体
        feature_entities = self.find_entity(feature_name, EntityType.FEATURE)
        if not feature_entities:
            return []
        
        # 查找相关组件
        components = []
        for feature in feature_entities:
            related = self.find_related_entities(feature.id, RelationType.DEPENDS_ON)
            for entity in related['entities']:
                if entity.entity_type == EntityType.COMPONENT:
                    components.append(entity)
        
        return components
    
    def find_apis_by_component(self, component_name: str) -> List[Entity]:
        """
        根据组件查找相关API
        
        Args:
            component_name: 组件名称
            
        Returns:
            相关API列表
        """
        # 先查找组件实体
        component_entities = self.find_entity(component_name, EntityType.COMPONENT)
        if not component_entities:
            return []
        
        # 查找相关API
        apis = []
        for component in component_entities:
            related = self.find_related_entities(component.id, RelationType.USES)
            for entity in related['entities']:
                if entity.entity_type == EntityType.API:
                    apis.append(entity)
        
        return apis
    
    def find_documents_by_entity(self, entity_id: str) -> List[str]:
        """
        查找实体相关的文档
        
        Args:
            entity_id: 实体ID
            
        Returns:
            文档路径列表
        """
        entity = self.graph.get_entity(entity_id)
        if not entity:
            return []
        
        return entity.source_documents
    
    def find_entities_by_document(self, doc_path: str) -> List[Entity]:
        """
        查找文档相关的实体
        
        Args:
            doc_path: 文档路径
            
        Returns:
            实体列表
        """
        entities = []
        for entity in self.graph.entities.values():
            if doc_path in entity.source_documents:
                entities.append(entity)
        
        return entities
    
    def get_entity_context(self, entity_id: str) -> Dict[str, Any]:
        """
        获取实体上下文信息
        
        Args:
            entity_id: 实体ID
            
        Returns:
            实体上下文
        """
        entity = self.graph.get_entity(entity_id)
        if not entity:
            return {}
        
        # 获取相关实体
        related = self.find_related_entities(entity_id, max_depth=1)
        
        # 获取文档
        documents = self.find_documents_by_entity(entity_id)
        
        return {
            "entity": entity.to_dict(),
            "related_entities": [e.to_dict() for e in related['entities'] if e.id != entity_id],
            "relations": [r.to_dict() for r in related['relations']],
            "documents": documents,
            "statistics": {
                "related_count": len(related['entities']) - 1,
                "relation_count": len(related['relations']),
                "document_count": len(documents)
            }
        }
    
    def search_by_property(self, property_name: str, property_value: Any) -> List[Entity]:
        """
        根据属性搜索实体
        
        Args:
            property_name: 属性名
            property_value: 属性值
            
        Returns:
            匹配的实体列表
        """
        results = []
        
        for entity in self.graph.entities.values():
            # 检查实体属性
            if hasattr(entity, property_name):
                if getattr(entity, property_name) == property_value:
                    results.append(entity)
                    continue
            
            # 检查properties字典
            if property_name in entity.properties:
                if entity.properties[property_name] == property_value:
                    results.append(entity)
        
        return results
    
    def get_statistics_by_type(self) -> Dict[str, Dict[str, int]]:
        """
        按类型获取统计信息
        
        Returns:
            统计信息
        """
        stats = {}
        
        for entity in self.graph.entities.values():
            entity_type = entity.entity_type.value
            if entity_type not in stats:
                stats[entity_type] = {"count": 0, "documents": set()}
            
            stats[entity_type]["count"] += 1
            stats[entity_type]["documents"].update(entity.source_documents)
        
        # 转换set为list
        for entity_type in stats:
            stats[entity_type]["documents"] = list(stats[entity_type]["documents"])
            stats[entity_type]["document_count"] = len(stats[entity_type]["documents"])
        
        return stats
    
    def find_critical_components(self) -> List[Entity]:
        """
        查找关键组件（被依赖最多的组件）
        
        Returns:
            关键组件列表
        """
        # 统计每个实体被依赖的次数
        dependency_count = {}
        
        for relation in self.graph.relations.values():
            if relation.relation_type in [RelationType.DEPENDS_ON, RelationType.USES]:
                target_id = relation.target_id
                dependency_count[target_id] = dependency_count.get(target_id, 0) + 1
        
        # 按依赖次数排序
        sorted_entities = sorted(dependency_count.items(), key=lambda x: x[1], reverse=True)
        
        # 返回前10个关键组件
        critical_components = []
        for entity_id, count in sorted_entities[:10]:
            entity = self.graph.get_entity(entity_id)
            if entity:
                entity.properties['dependency_count'] = count
                critical_components.append(entity)
        
        return critical_components
    
    def find_isolated_entities(self) -> List[Entity]:
        """
        查找孤立实体（没有关系的实体）
        
        Returns:
            孤立实体列表
        """
        connected_entities = set()
        
        for relation in self.graph.relations.values():
            connected_entities.add(relation.source_id)
            connected_entities.add(relation.target_id)
        
        isolated = []
        for entity_id, entity in self.graph.entities.items():
            if entity_id not in connected_entities:
                isolated.append(entity)
        
        return isolated
    
    def generate_entity_report(self, entity_id: str) -> str:
        """
        生成实体报告
        
        Args:
            entity_id: 实体ID
            
        Returns:
            报告内容
        """
        context = self.get_entity_context(entity_id)
        if not context:
            return f"实体 {entity_id} 不存在"
        
        entity = context['entity']
        related = context['related_entities']
        relations = context['relations']
        documents = context['documents']
        
        report = f"""# 实体报告: {entity['name']}

## 基本信息

- **ID**: {entity['id']}
- **类型**: {entity['entity_type']}
- **描述**: {entity['description']}
- **创建时间**: {entity['created_at']}
- **更新时间**: {entity['updated_at']}

## 属性

"""
        for key, value in entity['properties'].items():
            report += f"- **{key}**: {value}\n"
        
        report += f"\n## 相关实体 ({len(related)})\n\n"
        for rel_entity in related[:10]:  # 只显示前10个
            report += f"- **{rel_entity['name']}** ({rel_entity['entity_type']}): {rel_entity['description']}\n"
        
        if len(related) > 10:
            report += f"- ... 还有 {len(related) - 10} 个\n"
        
        report += f"\n## 关系 ({len(relations)})\n\n"
        for relation in relations[:10]:  # 只显示前10个
            source = self.graph.get_entity(relation['source_id'])
            target = self.graph.get_entity(relation['target_id'])
            source_name = source.name if source else relation['source_id']
            target_name = target.name if target else relation['target_id']
            report += f"- **{source_name}** --[{relation['relation_type']}]--> **{target_name}**: {relation['description']}\n"
        
        report += f"\n## 来源文档 ({len(documents)})\n\n"
        for doc in documents:
            report += f"- {doc}\n"
        
        return report