"""
知识图谱模块

从 OpenCopilot 项目文档中提取核心知识，构建知识图谱。
支持实体识别、关系抽取、知识存储和查询。
"""

from .models import Entity, Relation, KnowledgeGraph
from .extractor import DocumentExtractor
from .graph import GraphManager
from .query import QueryEngine
from .api import app, start_api_server

__version__ = "1.0.0"
__all__ = [
    "Entity", "Relation", "KnowledgeGraph", 
    "DocumentExtractor", "GraphManager", "QueryEngine",
    "app", "start_api_server"
]