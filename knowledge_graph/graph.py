"""
知识图谱管理器

负责知识图谱的存储、加载、更新和查询。
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from .models import Entity, Relation, EntityType, RelationType, KnowledgeGraph
from .extractor import DocumentExtractor

logger = logging.getLogger(__name__)


class GraphManager:
    """知识图谱管理器"""
    
    def __init__(self, project_root: str, graph_file: str = None):
        """
        初始化图管理器
        
        Args:
            project_root: 项目根目录
            graph_file: 知识图谱存储文件路径
        """
        self.project_root = Path(project_root)
        
        # 默认存储路径
        if graph_file is None:
            graph_file = self.project_root / "knowledge_graph" / "opencopilot_knowledge_graph.json"
        
        self.graph_file = Path(graph_file)
        self.knowledge_graph = KnowledgeGraph()
        self.extractor = DocumentExtractor(project_root)
        
        # 确保目录存在
        self.graph_file.parent.mkdir(parents=True, exist_ok=True)
    
    def build_graph(self, force_rebuild: bool = False) -> KnowledgeGraph:
        """
        构建知识图谱
        
        Args:
            force_rebuild: 是否强制重建
            
        Returns:
            知识图谱
        """
        # 如果图谱文件存在且不强制重建，直接加载
        if self.graph_file.exists() and not force_rebuild:
            logger.info(f"加载现有知识图谱: {self.graph_file}")
            self.knowledge_graph = KnowledgeGraph.load_from_file(str(self.graph_file))
            return self.knowledge_graph
        
        logger.info("构建新的知识图谱...")
        
        # 从文档中提取知识
        self.knowledge_graph = self.extractor.extract_from_directory()
        
        # 提取组件关系
        self.extractor.extract_component_relationships()
        
        # 保存图谱
        self.save_graph()
        
        logger.info(f"知识图谱构建完成: {self.knowledge_graph.get_statistics()}")
        return self.knowledge_graph
    
    def save_graph(self):
        """保存知识图谱到文件"""
        try:
            self.knowledge_graph.save_to_file(str(self.graph_file))
            logger.info(f"知识图谱已保存到: {self.graph_file}")
        except Exception as e:
            logger.error(f"保存知识图谱失败: {e}")
    
    def load_graph(self) -> KnowledgeGraph:
        """加载知识图谱"""
        if not self.graph_file.exists():
            logger.warning(f"知识图谱文件不存在: {self.graph_file}")
            return KnowledgeGraph()
        
        try:
            self.knowledge_graph = KnowledgeGraph.load_from_file(str(self.graph_file))
            logger.info(f"知识图谱已加载: {self.knowledge_graph.get_statistics()}")
            return self.knowledge_graph
        except Exception as e:
            logger.error(f"加载知识图谱失败: {e}")
            return KnowledgeGraph()
    
    def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新实体
        
        Args:
            entity_id: 实体ID
            updates: 更新内容
            
        Returns:
            是否更新成功
        """
        entity = self.knowledge_graph.get_entity(entity_id)
        if not entity:
            logger.warning(f"实体不存在: {entity_id}")
            return False
        
        # 更新属性
        for key, value in updates.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
            elif key in entity.properties:
                entity.properties[key] = value
        
        entity.updated_at = datetime.now().isoformat()
        self.save_graph()
        return True
    
    def add_entity(self, entity: Entity) -> str:
        """添加实体"""
        entity_id = self.knowledge_graph.add_entity(entity)
        self.save_graph()
        return entity_id
    
    def add_relation(self, relation: Relation) -> str:
        """添加关系"""
        relation_id = self.knowledge_graph.add_relation(relation)
        self.save_graph()
        return relation_id
    
    def remove_entity(self, entity_id: str) -> bool:
        """
        删除实体
        
        Args:
            entity_id: 实体ID
            
        Returns:
            是否删除成功
        """
        if entity_id not in self.knowledge_graph.entities:
            return False
        
        # 删除相关关系
        relations_to_remove = []
        for relation_id, relation in self.knowledge_graph.relations.items():
            if relation.source_id == entity_id or relation.target_id == entity_id:
                relations_to_remove.append(relation_id)
        
        for relation_id in relations_to_remove:
            del self.knowledge_graph.relations[relation_id]
        
        # 删除实体
        entity = self.knowledge_graph.entities.pop(entity_id)
        
        # 更新索引
        if entity.name in self.knowledge_graph.entity_index:
            self.knowledge_graph.entity_index[entity.name].discard(entity_id)
            if not self.knowledge_graph.entity_index[entity.name]:
                del self.knowledge_graph.entity_index[entity.name]
        
        if entity_id in self.knowledge_graph.relation_index:
            del self.knowledge_graph.relation_index[entity_id]
        
        self.save_graph()
        return True
    
    def get_entity_by_name(self, name: str) -> List[Entity]:
        """根据名称获取实体"""
        return self.knowledge_graph.get_entity_by_name(name)
    
    def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """根据ID获取实体"""
        return self.knowledge_graph.get_entity(entity_id)
    
    def search_entities(self, query: str, entity_type: Optional[EntityType] = None) -> List[Entity]:
        """搜索实体"""
        return self.knowledge_graph.search_entities(query, entity_type)
    
    def get_related_entities(self, entity_id: str, relation_type: Optional[RelationType] = None) -> List[Entity]:
        """获取相关实体"""
        return self.knowledge_graph.get_related_entities(entity_id, relation_type)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.knowledge_graph.get_statistics()
    
    def export_to_json(self, output_file: str = None) -> str:
        """
        导出为JSON文件
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            输出文件路径
        """
        if output_file is None:
            output_file = self.project_root / "knowledge_graph" / "export" / f"knowledge_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.knowledge_graph.save_to_file(str(output_file))
        logger.info(f"知识图谱已导出到: {output_file}")
        return str(output_file)
    
    def export_to_csv(self, output_dir: str = None):
        """
        导出为CSV文件
        
        Args:
            output_dir: 输出目录
        """
        if output_dir is None:
            output_dir = self.project_root / "knowledge_graph" / "export" / f"csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 导出实体
        entities_file = output_dir / "entities.csv"
        with open(entities_file, 'w', encoding='utf-8') as f:
            f.write("id,name,type,description,source_documents\n")
            for entity in self.knowledge_graph.entities.values():
                source_docs = "|".join(entity.source_documents)
                f.write(f'"{entity.id}","{entity.name}","{entity.entity_type.value}","{entity.description}","{source_docs}"\n')
        
        # 导出关系
        relations_file = output_dir / "relations.csv"
        with open(relations_file, 'w', encoding='utf-8') as f:
            f.write("id,source_id,target_id,type,description,weight\n")
            for relation in self.knowledge_graph.relations.values():
                f.write(f'"{relation.id}","{relation.source_id}","{relation.target_id}","{relation.relation_type.value}","{relation.description}",{relation.weight}\n')
        
        logger.info(f"知识图谱已导出到CSV: {output_dir}")
    
    def generate_report(self) -> str:
        """
        生成知识图谱报告
        
        Returns:
            报告内容
        """
        stats = self.get_statistics()
        
        report = f"""# OpenCopilot 知识图谱报告

## 概览

- **实体总数**: {stats['total_entities']}
- **关系总数**: {stats['total_relations']}
- **创建时间**: {stats['created_at']}
- **更新时间**: {stats['updated_at']}

## 实体类型分布

"""
        for entity_type, count in stats['entity_types'].items():
            report += f"- **{entity_type}**: {count}\n"
        
        report += "\n## 关系类型分布\n\n"
        for relation_type, count in stats['relation_types'].items():
            report += f"- **{relation_type}**: {count}\n"
        
        # 添加核心组件列表
        report += "\n## 核心组件\n\n"
        components = self.search_entities("", EntityType.COMPONENT)
        for component in components[:10]:  # 只显示前10个
            report += f"- **{component.name}**: {component.description}\n"
        
        # 添加API端点统计
        report += "\n## API端点\n\n"
        apis = self.search_entities("", EntityType.API)
        report += f"共找到 {len(apis)} 个API端点\n\n"
        
        # 按类型分组
        api_types = {}
        for api in apis:
            api_type = api.properties.get('api_type', '其他')
            if api_type not in api_types:
                api_types[api_type] = []
            api_types[api_type].append(api)
        
        for api_type, api_list in api_types.items():
            report += f"### {api_type}\n\n"
            for api in api_list[:5]:  # 每种类型最多显示5个
                report += f"- `{api.name}`\n"
            if len(api_list) > 5:
                report += f"- ... 还有 {len(api_list) - 5} 个\n"
            report += "\n"
        
        return report