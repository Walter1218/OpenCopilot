"""
文档知识提取器

从 OpenCopilot 项目文档中提取实体和关系。
"""

import re
import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

from .models import Entity, Relation, EntityType, RelationType, KnowledgeGraph

logger = logging.getLogger(__name__)


class DocumentExtractor:
    """文档知识提取器"""
    
    def __init__(self, project_root: str):
        """
        初始化提取器
        
        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root)
        self.knowledge_graph = KnowledgeGraph()
        
        # 实体缓存，避免重复创建
        self.entity_cache: Dict[str, Entity] = {}
        
        # 正则模式
        self.patterns = {
            # 组件模式
            'component': [
                r'(?:ASU\s+)?(?:Custom\s+)?Agent\s*\(([^)]+)\)',
                r'(?:Privileged\s+)?Broker\s*\(([^)]+)\)',
                r'IDE\s+Extension\s*\(([^)]+)\)',
                r'smart_copilot\.py',
                r'asu_custom_agent\.py',
                r'asu_broker/',
                r'asu-ide-extension/',
            ],
            # API端点模式
            'api_endpoint': [
                r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]+)',
                r'`(/[^\s]+)`',
                r'端口\s*(\d{4,5})',
            ],
            # 配置模式
            'config': [
                r'端口\s*(\d{4,5})',
                r'`([^`]+\.json)`',
                r'`([^`]+\.py)`',
                r'`([^`]+\.md)`',
            ],
            # 功能模式
            'feature': [
                r'PPT\s*共创',
                r'Persona\s*(?:系统|工坊|角色)',
                r'上下文(?:管理|窗口|感知)',
                r'双引擎',
                r'双图层',
                r'多模态',
                r'视觉感知',
            ],
        }
        
        # 组件端口映射
        self.component_ports = {
            '18888': 'ASU Custom Agent',
            '18889': 'ASU Broker',
            '8088': 'Smart Copilot API (旧版)',
            '8089': 'Smart Copilot Platform',
        }
        
        # 文档类型映射
        self.doc_type_mapping = {
            'README.md': '项目入口',
            'USER_GUIDE.md': '用户指南',
            'OpenCopilot_': '架构设计',
            'Smart_Copilot_': 'API文档',
            'PPT_CoCreation_': 'PPT共创',
            'Office_': '办公场景',
            'Phase': '测试文档',
            'Test_': '测试文档',
            'Quality_': '质量评估',
        }
    
    def extract_from_file(self, file_path: str) -> Tuple[List[Entity], List[Relation]]:
        """
        从单个文件提取实体和关系
        
        Args:
            file_path: 文件路径
            
        Returns:
            实体列表和关系列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 获取相对路径作为文档ID
            rel_path = os.path.relpath(file_path, self.project_root)
            
            # 提取文档实体
            doc_entity = self._extract_document_entity(rel_path, content)
            
            # 提取其他实体
            entities = [doc_entity]
            relations = []
            
            # 提取组件实体
            component_entities = self._extract_components(content, rel_path)
            entities.extend(component_entities)
            
            # 提取API端点
            api_entities = self._extract_api_endpoints(content, rel_path)
            entities.extend(api_entities)
            
            # 提取配置实体
            config_entities = self._extract_configs(content, rel_path)
            entities.extend(config_entities)
            
            # 提取功能实体
            feature_entities = self._extract_features(content, rel_path)
            entities.extend(feature_entities)
            
            # 创建关系
            for entity in entities[1:]:  # 跳过文档实体本身
                # 文档描述实体
                relation = Relation(
                    source_id=doc_entity.id,
                    target_id=entity.id,
                    relation_type=RelationType.DOCUMENTS,
                    description=f"文档 {rel_path} 描述了 {entity.name}",
                    source_documents=[rel_path]
                )
                relations.append(relation)
            
            return entities, relations
            
        except Exception as e:
            logger.error(f"提取文件 {file_path} 时出错: {e}")
            return [], []
    
    def _extract_document_entity(self, rel_path: str, content: str) -> Entity:
        """提取文档实体"""
        # 确定文档类型
        doc_type = "其他"
        for prefix, dtype in self.doc_type_mapping.items():
            if rel_path.startswith(prefix) or prefix in rel_path:
                doc_type = dtype
                break
        
        # 提取标题
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else Path(rel_path).stem
        
        # 提取版本信息
        version_match = re.search(r'[Vv]ersion[:\s]*(\d+\.\d+(?:\.\d+)?)', content)
        version = version_match.group(1) if version_match else ""
        
        # 提取状态信息
        status_match = re.search(r'状态[:\s]*([^\n]+)', content)
        status = status_match.group(1).strip() if status_match else ""
        
        entity = Entity(
            name=rel_path,
            entity_type=EntityType.DOCUMENT,
            description=f"{doc_type}文档: {title}",
            properties={
                "file_path": rel_path,
                "doc_type": doc_type,
                "title": title,
                "version": version,
                "status": status,
                "size_bytes": len(content.encode('utf-8')),
                "line_count": content.count('\n') + 1,
            },
            source_documents=[rel_path]
        )
        
        return entity
    
    def _extract_components(self, content: str, source_doc: str) -> List[Entity]:
        """提取组件实体"""
        entities = []
        
        # 组件模式匹配
        component_patterns = [
            (r'ASU\s+Custom\s+Agent\s*\(([^)]+)\)', 'ASU Custom Agent', '核心AI智能体'),
            (r'Privileged\s+Broker\s*\(([^)]+)\)', 'ASU Broker', '特权代理，系统级探针'),
            (r'IDE\s+Extension\s*\(([^)]+)\)', 'IDE Extension', 'IDE伴生插件'),
            (r'smart_copilot\.py', 'Smart Copilot UI', '主程序UI'),
            (r'asu_custom_agent\.py', 'ASU Custom Agent', '智能体核心代码'),
            (r'asu_broker/', 'ASU Broker', '特权代理模块'),
            (r'asu-ide-extension/', 'IDE Extension', 'IDE扩展模块'),
            (r'smart_copilot_platform\.py', 'Smart Copilot Platform', '能力平台API'),
            (r'smart_copilot_api\.py', 'Smart Copilot API', '旧版API'),
            (r'ppt_cocreation/', 'PPT CoCreation', 'PPT共创模块'),
            (r'personas/', 'Persona System', '角色人设系统'),
            (r'ContextWindowManager', 'Context Window Manager', '上下文窗口管理器'),
            (r'ContextEnvelope', 'Context Envelope', '统一上下文协议'),
        ]
        
        for pattern, name, description in component_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                # 检查缓存
                if name in self.entity_cache:
                    entity = self.entity_cache[name]
                    if source_doc not in entity.source_documents:
                        entity.source_documents.append(source_doc)
                    continue
                
                entity = Entity(
                    name=name,
                    entity_type=EntityType.COMPONENT,
                    description=description,
                    source_documents=[source_doc]
                )
                self.entity_cache[name] = entity
                entities.append(entity)
        
        return entities
    
    def _extract_api_endpoints(self, content: str, source_doc: str) -> List[Entity]:
        """提取API端点实体"""
        entities = []
        
        # API端点模式
        api_patterns = [
            (r'(?:GET|POST|PUT|DELETE|PATCH)\s+(/[^\s]+)', 'API Endpoint'),
            (r'`(/[^\s]+)`', 'API Endpoint'),
        ]
        
        for pattern, prefix in api_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                endpoint = match.group(1)
                
                # 清理端点
                endpoint = re.sub(r'[`\'""]', '', endpoint)
                if not endpoint.startswith('/'):
                    continue
                
                # 检查缓存
                if endpoint in self.entity_cache:
                    entity = self.entity_cache[endpoint]
                    if source_doc not in entity.source_documents:
                        entity.source_documents.append(source_doc)
                    continue
                
                # 确定API类型
                api_type = "REST API"
                if '/v1/agent/' in endpoint:
                    api_type = "Agent API"
                elif '/api/v1/system/' in endpoint:
                    api_type = "Broker API"
                elif '/api/ppt/' in endpoint:
                    api_type = "PPT API"
                elif '/api/context/' in endpoint:
                    api_type = "Context API"
                
                entity = Entity(
                    name=endpoint,
                    entity_type=EntityType.API,
                    description=f"{api_type}: {endpoint}",
                    properties={
                        "endpoint": endpoint,
                        "api_type": api_type,
                    },
                    source_documents=[source_doc]
                )
                self.entity_cache[endpoint] = entity
                entities.append(entity)
        
        return entities
    
    def _extract_configs(self, content: str, source_doc: str) -> List[Entity]:
        """提取配置实体"""
        entities = []
        
        # 端口配置
        port_pattern = r'端口\s*(\d{4,5})'
        port_matches = re.finditer(port_pattern, content)
        for match in port_matches:
            port = match.group(1)
            
            # 检查缓存
            if port in self.entity_cache:
                entity = self.entity_cache[port]
                if source_doc not in entity.source_documents:
                    entity.source_documents.append(source_doc)
                continue
            
            # 确定组件
            component = self.component_ports.get(port, "未知组件")
            
            entity = Entity(
                name=f"端口 {port}",
                entity_type=EntityType.CONFIG,
                description=f"{component} 使用的端口",
                properties={
                    "port": port,
                    "component": component,
                    "config_type": "port",
                },
                source_documents=[source_doc]
            )
            self.entity_cache[port] = entity
            entities.append(entity)
        
        # 配置文件
        config_patterns = [
            (r'`([^`]+\.json)`', 'JSON配置文件'),
            (r'`([^`]+\.py)`', 'Python配置文件'),
            (r'`([^`]+\.md)`', 'Markdown文档'),
        ]
        
        for pattern, config_type in config_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                filename = match.group(1)
                
                # 过滤掉明显不是配置的文件
                if any(skip in filename for skip in ['test_', '__pycache__', '.pyc']):
                    continue
                
                # 检查缓存
                if filename in self.entity_cache:
                    entity = self.entity_cache[filename]
                    if source_doc not in entity.source_documents:
                        entity.source_documents.append(source_doc)
                    continue
                
                entity = Entity(
                    name=filename,
                    entity_type=EntityType.CONFIG,
                    description=f"{config_type}: {filename}",
                    properties={
                        "filename": filename,
                        "config_type": config_type,
                    },
                    source_documents=[source_doc]
                )
                self.entity_cache[filename] = entity
                entities.append(entity)
        
        return entities
    
    def _extract_features(self, content: str, source_doc: str) -> List[Entity]:
        """提取功能实体"""
        entities = []
        
        # 功能模式
        feature_patterns = [
            (r'PPT\s*共创', 'PPT CoCreation', 'PPT共创模式'),
            (r'Persona\s*(?:系统|工坊|角色)', 'Persona System', '角色人设系统'),
            (r'上下文(?:管理|窗口|感知)', 'Context Management', '上下文管理'),
            (r'双引擎', 'Dual Engine', '双引擎架构'),
            (r'双图层', 'Dual Layer', '双图层架构'),
            (r'多模态', 'Multimodal', '多模态感知'),
            (r'视觉感知', 'Vision Perception', '视觉感知'),
            (r'会话持久化', 'Session Persistence', '会话持久化'),
            (r'LaunchAgent', 'LaunchAgent', 'macOS LaunchAgent部署'),
            (r'WebSocket', 'WebSocket', 'WebSocket通信'),
            (r'SSE', 'SSE', 'Server-Sent Events'),
        ]
        
        for pattern, name, description in feature_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                # 检查缓存
                if name in self.entity_cache:
                    entity = self.entity_cache[name]
                    if source_doc not in entity.source_documents:
                        entity.source_documents.append(source_doc)
                    continue
                
                entity = Entity(
                    name=name,
                    entity_type=EntityType.FEATURE,
                    description=description,
                    source_documents=[source_doc]
                )
                self.entity_cache[name] = entity
                entities.append(entity)
        
        return entities
    
    def extract_from_directory(self, directory: str = None) -> KnowledgeGraph:
        """
        从目录中提取所有文档的知识
        
        Args:
            directory: 目录路径，默认为项目根目录
            
        Returns:
            知识图谱
        """
        if directory is None:
            directory = self.project_root
        
        directory = Path(directory)
        
        # 收集所有Markdown文件
        md_files = list(directory.rglob('*.md'))
        
        logger.info(f"找到 {len(md_files)} 个Markdown文件")
        
        all_entities = []
        all_relations = []
        
        for md_file in md_files:
            # 跳过某些目录
            rel_path = md_file.relative_to(self.project_root)
            if any(skip in str(rel_path) for skip in ['node_modules', '.git', '__pycache__', '.codebuddy']):
                continue
            
            logger.info(f"处理文件: {rel_path}")
            entities, relations = self.extract_from_file(str(md_file))
            all_entities.extend(entities)
            all_relations.extend(relations)
        
        # 去重并添加到知识图谱
        unique_entities = {}
        for entity in all_entities:
            if entity.name not in unique_entities:
                unique_entities[entity.name] = entity
            else:
                # 合并来源文档
                existing = unique_entities[entity.name]
                for doc in entity.source_documents:
                    if doc not in existing.source_documents:
                        existing.source_documents.append(doc)
        
        # 添加实体到图谱
        for entity in unique_entities.values():
            self.knowledge_graph.add_entity(entity)
        
        # 添加关系到图谱
        for relation in all_relations:
            try:
                self.knowledge_graph.add_relation(relation)
            except ValueError as e:
                logger.warning(f"跳过关系: {e}")
        
        return self.knowledge_graph
    
    def extract_component_relationships(self):
        """提取组件间的关系"""
        # 组件依赖关系
        component_dependencies = [
            ('Smart Copilot UI', 'ASU Custom Agent', RelationType.DEPENDS_ON, 'UI依赖Agent'),
            ('Smart Copilot UI', 'ASU Broker', RelationType.DEPENDS_ON, 'UI依赖Broker'),
            ('ASU Custom Agent', 'MiniMax Provider', RelationType.USES, 'Agent使用MiniMax'),
            ('ASU Custom Agent', 'Ollama Provider', RelationType.USES, 'Agent使用Ollama'),
            ('ASU Broker', 'macOS TCC', RelationType.DEPENDS_ON, 'Broker依赖macOS权限'),
            ('IDE Extension', 'ASU Custom Agent', RelationType.COMMUNICATES_WITH, 'IDE与Agent通信'),
            ('PPT CoCreation', 'ASU Custom Agent', RelationType.DEPENDS_ON, 'PPT功能依赖Agent'),
            ('Persona System', 'ASU Custom Agent', RelationType.CONFIGURES, 'Persona配置Agent'),
        ]
        
        for source_name, target_name, rel_type, description in component_dependencies:
            source_entities = self.knowledge_graph.get_entity_by_name(source_name)
            target_entities = self.knowledge_graph.get_entity_by_name(target_name)
            
            if source_entities and target_entities:
                source = source_entities[0]
                target = target_entities[0]
                
                relation = Relation(
                    source_id=source.id,
                    target_id=target.id,
                    relation_type=rel_type,
                    description=description,
                    source_documents=['extracted_from_architecture']
                )
                
                try:
                    self.knowledge_graph.add_relation(relation)
                except ValueError as e:
                    logger.warning(f"跳过关系: {e}")