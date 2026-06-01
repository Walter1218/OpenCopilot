"""
KnowledgeSkill - 知识图谱 Skill

将知识图谱系统封装为 Skill，支持知识查询、构建和导出。
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from skill_architecture.base import BaseSkill
from skill_architecture.models import (
    SkillMetadata, SkillContext, SkillResult, SkillStatus
)

logger = logging.getLogger(__name__)


class KnowledgeSkill(BaseSkill):
    """知识图谱 Skill"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 KnowledgeSkill
        
        Args:
            config: 配置字典，可包含：
                - project_root: 项目根目录
                - graph_file: 知识图谱存储文件路径
        """
        super().__init__(config)
        self._graph_manager = None
        self._query_engine = None
        self._initialized = False
    
    @property
    def metadata(self) -> SkillMetadata:
        """获取 Skill 元数据"""
        return SkillMetadata(
            name="knowledge",
            version="1.0.0",
            description="知识图谱查询、构建和导出",
            author="OpenCopilot",
            tags=["knowledge", "graph", "query", "search"],
            intents=[
                "knowledge_query",
                "knowledge_build", 
                "knowledge_export",
                "search_entity",
                "find_related",
                "find_path",
                "get_statistics"
            ],
            dependencies=[],
            config_schema={
                "project_root": {
                    "type": "string",
                    "description": "项目根目录",
                    "required": False
                },
                "graph_file": {
                    "type": "string",
                    "description": "知识图谱存储文件路径",
                    "required": False
                }
            },
            input_schema={
                "query": {
                    "type": "string",
                    "description": "查询关键词"
                },
                "entity_type": {
                    "type": "string",
                    "description": "实体类型过滤"
                },
                "entity_id": {
                    "type": "string",
                    "description": "实体ID"
                },
                "relation_type": {
                    "type": "string",
                    "description": "关系类型过滤"
                },
                "max_depth": {
                    "type": "integer",
                    "description": "最大深度"
                },
                "force_rebuild": {
                    "type": "boolean",
                    "description": "是否强制重建"
                },
                "format": {
                    "type": "string",
                    "description": "导出格式"
                }
            },
            output_schema={
                "entities": {
                    "type": "array",
                    "description": "实体列表"
                },
                "relations": {
                    "type": "array",
                    "description": "关系列表"
                },
                "statistics": {
                    "type": "object",
                    "description": "统计信息"
                },
                "paths": {
                    "type": "array",
                    "description": "路径列表"
                }
            }
        )
    
    async def initialize(self) -> bool:
        """
        初始化知识图谱系统
        
        Returns:
            bool: 是否成功
        """
        try:
            # 导入知识图谱模块
            from knowledge_graph.graph import GraphManager
            from knowledge_graph.query import QueryEngine
            
            # 获取项目根目录
            project_root = self._config.get("project_root")
            if project_root is None:
                project_root = str(Path(__file__).parent)
            
            # 获取图谱文件路径
            graph_file = self._config.get("graph_file")
            
            # 创建 GraphManager
            self._graph_manager = GraphManager(project_root, graph_file)
            
            # 构建或加载知识图谱
            knowledge_graph = self._graph_manager.build_graph()
            
            # 创建 QueryEngine
            self._query_engine = QueryEngine(knowledge_graph)
            
            self._initialized = True
            logger.info(f"KnowledgeSkill 初始化完成: {knowledge_graph.get_statistics()}")
            
            return True
            
        except Exception as e:
            logger.error(f"KnowledgeSkill 初始化失败: {e}")
            return False
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """
        执行 Skill
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        # 检查是否已初始化
        if not self._initialized:
            success = await self.initialize()
            if not success:
                return SkillResult(
                    success=False,
                    data={},
                    error="KnowledgeSkill 初始化失败",
                    status=SkillStatus.FAILED
                )
        
        # 获取意图
        intent = context.intent
        
        # 根据意图执行相应的操作
        try:
            if intent == "knowledge_query":
                return await self._handle_query(context)
            elif intent == "knowledge_build":
                return await self._handle_build(context)
            elif intent == "knowledge_export":
                return await self._handle_export(context)
            elif intent == "search_entity":
                return await self._handle_search_entity(context)
            elif intent == "find_related":
                return await self._handle_find_related(context)
            elif intent == "find_path":
                return await self._handle_find_path(context)
            elif intent == "get_statistics":
                return await self._handle_get_statistics(context)
            else:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"不支持的意图: {intent}",
                    status=SkillStatus.FAILED
                )
        except Exception as e:
            logger.error(f"执行 KnowledgeSkill 失败: {e}")
            return SkillResult(
                success=False,
                data={},
                error=str(e),
                status=SkillStatus.FAILED
            )
    
    async def can_handle(self, context: SkillContext) -> float:
        """
        判断是否能处理该上下文
        
        Args:
            context: 执行上下文
        
        Returns:
            float: 置信度 (0-1)
        """
        # 检查意图是否匹配
        if context.intent in self.metadata.intents:
            return 0.9
        
        # 检查输入数据中是否包含知识图谱相关的关键词
        input_data = context.input_data
        if isinstance(input_data, dict):
            query = input_data.get("query", "")
            if isinstance(query, str):
                query_lower = query.lower()
                knowledge_keywords = ["知识", "图谱", "实体", "关系", "查询", "搜索", "路径"]
                for keyword in knowledge_keywords:
                    if keyword in query_lower:
                        return 0.7
        
        return 0.0
    
    async def _handle_query(self, context: SkillContext) -> SkillResult:
        """
        处理知识查询意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        query = input_data.get("query", "")
        entity_type = input_data.get("entity_type")
        
        if not query:
            return SkillResult(
                success=False,
                data={},
                error="查询关键词不能为空",
                status=SkillStatus.FAILED
            )
        
        # 搜索实体
        entities = self._query_engine.find_entity(query, entity_type)
        
        # 转换为字典列表
        entity_dicts = [entity.to_dict() for entity in entities]
        
        return SkillResult(
            success=True,
            data={
                "query": query,
                "entity_type": entity_type,
                "count": len(entity_dicts),
                "entities": entity_dicts
            },
            status=SkillStatus.COMPLETED
        )
    
    async def _handle_build(self, context: SkillContext) -> SkillResult:
        """
        处理知识构建意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        content = input_data.get("content", "")
        source = input_data.get("source", "unknown")
        force_rebuild = input_data.get("force_rebuild", False)
        
        try:
            # 导入 QueryEngine
            from knowledge_graph.query import QueryEngine
            from knowledge_graph.models import Entity, Relation
            
            # 如果有内容，从内容中提取实体和关系
            if content and content.strip():
                # 导入EntityType和RelationType
                from knowledge_graph.models import EntityType, RelationType
                
                # 简单的实体提取（基于关键词）
                entities_extracted = []
                relations_extracted = []
                
                # 提取概念实体
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 提取标题作为实体
                    if line.startswith('#'):
                        entity_name = line.lstrip('#').strip()
                        if entity_name:
                            entity = Entity(
                                id=f"entity_{len(entities_extracted)}",
                                name=entity_name,
                                entity_type=EntityType.CONCEPT,
                                properties={"source": source, "line": i},
                                description=f"从{source}提取的概念"
                            )
                            entities_extracted.append(entity)
                    
                    # 提取列表项作为实体
                    elif line.startswith('-') or line.startswith('*'):
                        item_name = line.lstrip('-* ').strip()
                        if item_name and len(item_name) > 2:
                            entity = Entity(
                                id=f"entity_{len(entities_extracted)}",
                                name=item_name[:50],  # 限制长度
                                entity_type=EntityType.FEATURE,
                                properties={"source": source, "line": i},
                                description=f"从{source}提取的条目"
                            )
                            entities_extracted.append(entity)
                
                # 提取关键概念（简单关键词提取）
                keywords = ["Python", "编程", "语言", "特点", "功能", "API", "系统", "架构"]
                for keyword in keywords:
                    if keyword.lower() in content.lower():
                        # 检查是否已存在
                        exists = any(e.name.lower() == keyword.lower() for e in entities_extracted)
                        if not exists:
                            entity = Entity(
                                id=f"entity_{len(entities_extracted)}",
                                name=keyword,
                                entity_type=EntityType.CONCEPT,
                                properties={"source": source},
                                description=f"关键词: {keyword}"
                            )
                            entities_extracted.append(entity)
                
                # 创建实体间的关系
                for i in range(len(entities_extracted) - 1):
                    relation = Relation(
                        id=f"relation_{len(relations_extracted)}",
                        source_id=entities_extracted[i].id,
                        target_id=entities_extracted[i+1].id,
                        relation_type=RelationType.USES,
                        properties={"source": source}
                    )
                    relations_extracted.append(relation)
                
                # 添加到知识图谱
                for entity in entities_extracted:
                    self._graph_manager.knowledge_graph.add_entity(entity)
                
                for relation in relations_extracted:
                    self._graph_manager.knowledge_graph.add_relation(relation)
                
                # 保存图谱
                self._graph_manager.save_graph()
            
            # 如果强制重建或没有内容，执行完整构建
            if force_rebuild or not content:
                knowledge_graph = self._graph_manager.build_graph(force_rebuild=force_rebuild)
            else:
                knowledge_graph = self._graph_manager.knowledge_graph
            
            # 更新查询引擎
            self._query_engine = QueryEngine(knowledge_graph)
            
            return SkillResult(
                success=True,
                data={
                    "statistics": knowledge_graph.get_statistics(),
                    "entities_extracted": len(entities_extracted) if content else 0,
                    "relations_extracted": len(relations_extracted) if content else 0,
                    "force_rebuild": force_rebuild
                },
                status=SkillStatus.COMPLETED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"构建知识图谱失败: {e}",
                status=SkillStatus.FAILED
            )
    
    async def _handle_export(self, context: SkillContext) -> SkillResult:
        """
        处理知识导出意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        export_format = input_data.get("format", "json")
        
        try:
            # 获取知识图谱统计信息
            statistics = self._graph_manager.knowledge_graph.get_statistics()
            
            # 获取所有实体和关系
            entities = [entity.to_dict() for entity in self._graph_manager.knowledge_graph.entities.values()]
            relations = [relation.to_dict() for relation in self._graph_manager.knowledge_graph.relations.values()]
            
            # 根据格式导出
            if export_format == "json":
                export_data = {
                    "statistics": statistics,
                    "entities": entities,
                    "relations": relations
                }
            elif export_format == "csv":
                # 简化的 CSV 导出
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # 写入实体
                writer.writerow(["Entity ID", "Name", "Type", "Description"])
                for entity in entities:
                    writer.writerow([
                        entity["id"],
                        entity["name"],
                        entity["entity_type"],
                        entity["description"]
                    ])
                
                # 写入关系
                writer.writerow([])
                writer.writerow(["Relation ID", "Source", "Target", "Type", "Description"])
                for relation in relations:
                    writer.writerow([
                        relation["id"],
                        relation["source_id"],
                        relation["target_id"],
                        relation["relation_type"],
                        relation["description"]
                    ])
                
                export_data = {
                    "format": "csv",
                    "content": output.getvalue()
                }
            else:
                export_data = {
                    "statistics": statistics,
                    "entities": entities,
                    "relations": relations
                }
            
            return SkillResult(
                success=True,
                data=export_data,
                status=SkillStatus.COMPLETED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"导出知识图谱失败: {e}",
                status=SkillStatus.FAILED
            )
    
    async def _handle_search_entity(self, context: SkillContext) -> SkillResult:
        """
        处理搜索实体意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        query = input_data.get("query", "")
        entity_type = input_data.get("entity_type")
        
        if not query:
            return SkillResult(
                success=False,
                data={},
                error="搜索关键词不能为空",
                status=SkillStatus.FAILED
            )
        
        # 搜索实体
        entities = self._query_engine.find_entity(query, entity_type)
        
        # 转换为字典列表
        entity_dicts = [entity.to_dict() for entity in entities]
        
        return SkillResult(
            success=True,
            data={
                "query": query,
                "entity_type": entity_type,
                "count": len(entity_dicts),
                "entities": entity_dicts
            },
            status=SkillStatus.COMPLETED
        )
    
    async def _handle_find_related(self, context: SkillContext) -> SkillResult:
        """
        处理查找相关实体意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        entity_id = input_data.get("entity_id")
        relation_type = input_data.get("relation_type")
        max_depth = input_data.get("max_depth", 1)
        
        if not entity_id:
            return SkillResult(
                success=False,
                data={},
                error="实体ID不能为空",
                status=SkillStatus.FAILED
            )
        
        # 查找相关实体
        result = self._query_engine.find_related_entities(entity_id, relation_type, max_depth)
        
        # 转换为字典
        entity_dicts = [entity.to_dict() for entity in result["entities"]]
        relation_dicts = [relation.to_dict() for relation in result["relations"]]
        
        return SkillResult(
            success=True,
            data={
                "entity_id": entity_id,
                "relation_type": relation_type,
                "max_depth": max_depth,
                "count": result["count"],
                "entities": entity_dicts,
                "relations": relation_dicts
            },
            status=SkillStatus.COMPLETED
        )
    
    async def _handle_find_path(self, context: SkillContext) -> SkillResult:
        """
        处理查找路径意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        source_id = input_data.get("source_id")
        target_id = input_data.get("target_id")
        max_depth = input_data.get("max_depth", 3)
        
        if not source_id or not target_id:
            return SkillResult(
                success=False,
                data={},
                error="源实体ID和目标实体ID不能为空",
                status=SkillStatus.FAILED
            )
        
        # 查找路径
        paths = self._query_engine.find_path(source_id, target_id, max_depth)
        
        return SkillResult(
            success=True,
            data={
                "source_id": source_id,
                "target_id": target_id,
                "max_depth": max_depth,
                "paths": paths,
                "count": len(paths)
            },
            status=SkillStatus.COMPLETED
        )
    
    async def _handle_get_statistics(self, context: SkillContext) -> SkillResult:
        """
        处理获取统计信息意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        try:
            # 获取统计信息
            statistics = self._graph_manager.knowledge_graph.get_statistics()
            
            return SkillResult(
                success=True,
                data=statistics,
                status=SkillStatus.COMPLETED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"获取统计信息失败: {e}",
                status=SkillStatus.FAILED
            )
    
    async def cleanup(self) -> None:
        """清理资源"""
        self._graph_manager = None
        self._query_engine = None
        self._initialized = False
        logger.info("KnowledgeSkill 已清理资源")