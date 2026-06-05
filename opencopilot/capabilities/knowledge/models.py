"""
知识图谱数据模型

定义实体、关系和知识图谱的数据结构。
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from datetime import datetime


class EntityType(str, Enum):
    """实体类型枚举"""
    COMPONENT = "component"          # 组件：Agent、Broker、IDE Extension等
    API = "api"                      # API端点
    CONFIG = "config"                # 配置：端口、配置文件、环境变量
    FEATURE = "feature"              # 功能：PPT共创、Persona系统等
    DOCUMENT = "document"            # 文档：.md文件
    TEST = "test"                    # 测试：测试阶段、测试用例
    DEPLOYMENT = "deployment"        # 部署：LaunchAgent、守护进程
    PERSONA = "persona"              # 人设：角色配置
    TOOL = "tool"                    # 工具：evaluation_tools.py等
    CONCEPT = "concept"              # 概念：架构概念、设计模式等


class RelationType(str, Enum):
    """关系类型枚举"""
    DEPENDS_ON = "depends_on"        # 依赖关系
    IMPLEMENTS = "implements"        # 实现关系
    CONFIGURES = "configures"        # 配置关系
    TESTS = "tests"                  # 测试关系
    DOCUMENTS = "documents"          # 文档关系
    COMMUNICATES_WITH = "communicates_with"  # 通信关系
    CONTAINS = "contains"            # 包含关系
    EXTENDS = "extends"              # 扩展关系
    USES = "uses"                    # 使用关系
    REPLACES = "replaces"            # 替代关系


@dataclass
class Entity:
    """实体类"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""                   # 实体名称
    entity_type: EntityType = EntityType.COMPONENT
    description: str = ""            # 描述
    properties: Dict[str, Any] = field(default_factory=dict)  # 属性
    source_documents: List[str] = field(default_factory=list)  # 来源文档
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "description": self.description,
            "properties": self.properties,
            "source_documents": self.source_documents,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        """从字典创建实体"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            entity_type=EntityType(data.get("entity_type", "component")),
            description=data.get("description", ""),
            properties=data.get("properties", {}),
            source_documents=data.get("source_documents", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )


@dataclass
class Relation:
    """关系类"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""              # 源实体ID
    target_id: str = ""              # 目标实体ID
    relation_type: RelationType = RelationType.DEPENDS_ON
    description: str = ""            # 关系描述
    properties: Dict[str, Any] = field(default_factory=dict)  # 关系属性
    weight: float = 1.0              # 关系权重
    source_documents: List[str] = field(default_factory=list)  # 来源文档
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "description": self.description,
            "properties": self.properties,
            "weight": self.weight,
            "source_documents": self.source_documents,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relation':
        """从字典创建关系"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            relation_type=RelationType(data.get("relation_type", "depends_on")),
            description=data.get("description", ""),
            properties=data.get("properties", {}),
            weight=data.get("weight", 1.0),
            source_documents=data.get("source_documents", []),
            created_at=data.get("created_at", datetime.now().isoformat())
        )


@dataclass
class KnowledgeGraph:
    """知识图谱类"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "OpenCopilot Knowledge Graph"
    description: str = "OpenCopilot 项目知识图谱"
    version: str = "1.0.0"
    entities: Dict[str, Entity] = field(default_factory=dict)  # id -> Entity
    relations: Dict[str, Relation] = field(default_factory=dict)  # id -> Relation
    entity_index: Dict[str, Set[str]] = field(default_factory=dict)  # name -> set of entity ids
    relation_index: Dict[str, Set[str]] = field(default_factory=dict)  # source_id -> set of relation ids
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_entity(self, entity: Entity) -> str:
        """添加实体"""
        self.entities[entity.id] = entity
        # 更新索引
        if entity.name not in self.entity_index:
            self.entity_index[entity.name] = set()
        self.entity_index[entity.name].add(entity.id)
        self.updated_at = datetime.now().isoformat()
        return entity.id
    
    def add_relation(self, relation: Relation) -> str:
        """添加关系"""
        # 验证源和目标实体存在
        if relation.source_id not in self.entities:
            raise ValueError(f"源实体 {relation.source_id} 不存在")
        if relation.target_id not in self.entities:
            raise ValueError(f"目标实体 {relation.target_id} 不存在")
        
        self.relations[relation.id] = relation
        # 更新索引
        if relation.source_id not in self.relation_index:
            self.relation_index[relation.source_id] = set()
        self.relation_index[relation.source_id].add(relation.id)
        self.updated_at = datetime.now().isoformat()
        return relation.id
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        return self.entities.get(entity_id)
    
    def get_entity_by_name(self, name: str) -> List[Entity]:
        """根据名称获取实体"""
        entity_ids = self.entity_index.get(name, set())
        return [self.entities[eid] for eid in entity_ids if eid in self.entities]
    
    def get_relations_for_entity(self, entity_id: str) -> List[Relation]:
        """获取实体的所有关系"""
        relation_ids = self.relation_index.get(entity_id, set())
        return [self.relations[rid] for rid in relation_ids if rid in self.relations]
    
    def get_related_entities(self, entity_id: str, relation_type: Optional[RelationType] = None) -> List[Entity]:
        """获取相关实体"""
        relations = self.get_relations_for_entity(entity_id)
        if relation_type:
            relations = [r for r in relations if r.relation_type == relation_type]
        
        related_entities = []
        for relation in relations:
            if relation.source_id == entity_id:
                related_entities.append(self.entities.get(relation.target_id))
            else:
                related_entities.append(self.entities.get(relation.source_id))
        
        return [e for e in related_entities if e is not None]
    
    def search_entities(self, query: str, entity_type: Optional[EntityType] = None) -> List[Entity]:
        """搜索实体"""
        results = []
        query_lower = query.lower()
        
        for entity in self.entities.values():
            # 按类型过滤
            if entity_type and entity.entity_type != entity_type:
                continue
            
            # 名称或描述匹配
            if (query_lower in entity.name.lower() or 
                query_lower in entity.description.lower()):
                results.append(entity)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        entity_types = {}
        for entity in self.entities.values():
            entity_type = entity.entity_type.value
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        relation_types = {}
        for relation in self.relations.values():
            relation_type = relation.relation_type.value
            relation_types[relation_type] = relation_types.get(relation_type, 0) + 1
        
        return {
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "entity_types": entity_types,
            "relation_types": relation_types,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "entities": {eid: entity.to_dict() for eid, entity in self.entities.items()},
            "relations": {rid: relation.to_dict() for rid, relation in self.relations.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeGraph':
        """从字典创建知识图谱"""
        graph = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "OpenCopilot Knowledge Graph"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )
        
        # 加载实体
        for eid, entity_data in data.get("entities", {}).items():
            entity = Entity.from_dict(entity_data)
            graph.entities[eid] = entity
            # 更新索引
            if entity.name not in graph.entity_index:
                graph.entity_index[entity.name] = set()
            graph.entity_index[entity.name].add(eid)
        
        # 加载关系
        for rid, relation_data in data.get("relations", {}).items():
            relation = Relation.from_dict(relation_data)
            graph.relations[rid] = relation
            # 更新索引
            if relation.source_id not in graph.relation_index:
                graph.relation_index[relation.source_id] = set()
            graph.relation_index[relation.source_id].add(rid)
        
        return graph
    
    def save_to_file(self, file_path: str):
        """保存到文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'KnowledgeGraph':
        """从文件加载"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)