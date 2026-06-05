"""
知识图谱 API 接口

提供 RESTful API 查询知识图谱。
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Any, Optional
import uvicorn
from pathlib import Path
import logging

from .graph import GraphManager
from .query import QueryEngine
from .models import EntityType, RelationType

logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="OpenCopilot 知识图谱 API",
    description="从 OpenCopilot 项目文档中提取的核心知识图谱查询接口",
    version="1.0.0"
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量
graph_manager: Optional[GraphManager] = None
query_engine: Optional[QueryEngine] = None


def initialize_graph(project_root: str = None):
    """初始化知识图谱"""
    global graph_manager, query_engine
    
    if project_root is None:
        project_root = str(Path(__file__).parent.parent)
    
    graph_manager = GraphManager(project_root)
    graph_manager.build_graph()
    query_engine = QueryEngine(graph_manager.knowledge_graph)
    
    logger.info("知识图谱 API 已初始化")


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    initialize_graph()


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "OpenCopilot 知识图谱 API",
        "version": "1.0.0",
        "description": "从项目文档中提取的核心知识图谱查询接口",
        "endpoints": {
            "/graph/statistics": "获取知识图谱统计信息",
            "/entity/search": "搜索实体",
            "/entity/{entity_id}": "获取实体详情",
            "/entity/{entity_id}/related": "获取相关实体",
            "/entity/{entity_id}/context": "获取实体上下文",
            "/relation/search": "搜索关系",
            "/query/path": "查询实体路径",
            "/query/components": "查询组件",
            "/query/apis": "查询API端点",
            "/query/features": "查询功能",
            "/query/documents": "查询文档",
            "/export/json": "导出为JSON",
            "/export/report": "生成报告"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    stats = graph_manager.get_statistics()
    return {
        "status": "healthy",
        "entities": stats["total_entities"],
        "relations": stats["total_relations"]
    }


@app.get("/graph/statistics")
async def get_statistics():
    """获取知识图谱统计信息"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    return graph_manager.get_statistics()


@app.get("/graph/statistics-by-type")
async def get_statistics_by_type():
    """按类型获取统计信息"""
    if query_engine is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    return query_engine.get_statistics_by_type()


@app.get("/entity/search")
async def search_entities(
    query: str = Query(..., description="搜索关键词"),
    entity_type: Optional[str] = Query(None, description="实体类型过滤")
):
    """搜索实体"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    # 转换实体类型
    etype = None
    if entity_type:
        try:
            etype = EntityType(entity_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的实体类型: {entity_type}")
    
    entities = graph_manager.search_entities(query, etype)
    return {
        "query": query,
        "entity_type": entity_type,
        "count": len(entities),
        "entities": [entity.to_dict() for entity in entities]
    }


# 注意：/entity/by-name/{name} 和 /entity/by-property 必须在 /entity/{entity_id} 之前定义
# 否则会被 /entity/{entity_id} 路由优先匹配
@app.get("/entity/by-name/{name}")
async def get_entity_by_name(name: str):
    """根据名称获取实体"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    entities = graph_manager.get_entity_by_name(name)
    if not entities:
        raise HTTPException(status_code=404, detail=f"实体不存在: {name}")
    
    return {
        "name": name,
        "count": len(entities),
        "entities": [entity.to_dict() for entity in entities]
    }


@app.get("/entity/by-property")
async def get_entity_by_property(
    property_name: str = Query(..., description="属性名"),
    property_value: str = Query(..., description="属性值")
):
    """根据属性获取实体"""
    if query_engine is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    entities = query_engine.search_by_property(property_name, property_value)
    return {
        "property_name": property_name,
        "property_value": property_value,
        "count": len(entities),
        "entities": [entity.to_dict() for entity in entities]
    }


@app.get("/entity/{entity_id}")
async def get_entity(entity_id: str):
    """获取实体详情"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    entity = graph_manager.get_entity_by_id(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail=f"实体不存在: {entity_id}")
    
    return entity.to_dict()


@app.get("/entity/{entity_id}/related")
async def get_related_entities(
    entity_id: str,
    relation_type: Optional[str] = Query(None, description="关系类型过滤"),
    max_depth: int = Query(1, description="最大深度")
):
    """获取相关实体"""
    if query_engine is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    # 转换关系类型
    rtype = None
    if relation_type:
        try:
            rtype = RelationType(relation_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的关系类型: {relation_type}")
    
    result = query_engine.find_related_entities(entity_id, rtype, max_depth)
    return {
        "entity_id": entity_id,
        "relation_type": relation_type,
        "max_depth": max_depth,
        "count": result["count"],
        "entities": [entity.to_dict() for entity in result["entities"]],
        "relations": [relation.to_dict() for relation in result["relations"]]
    }


@app.get("/entity/{entity_id}/context")
async def get_entity_context(entity_id: str):
    """获取实体上下文"""
    if query_engine is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    context = query_engine.get_entity_context(entity_id)
    if not context:
        raise HTTPException(status_code=404, detail=f"实体不存在: {entity_id}")
    
    return context


@app.get("/entity/{entity_id}/report")
async def get_entity_report(entity_id: str):
    """获取实体报告"""
    if query_engine is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    report = query_engine.generate_entity_report(entity_id)
    if "不存在" in report:
        raise HTTPException(status_code=404, detail=f"实体不存在: {entity_id}")
    
    return {"entity_id": entity_id, "report": report}


@app.get("/relation/search")
async def search_relations(
    source_id: Optional[str] = Query(None, description="源实体ID"),
    target_id: Optional[str] = Query(None, description="目标实体ID"),
    relation_type: Optional[str] = Query(None, description="关系类型")
):
    """搜索关系"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    results = []
    for relation in graph_manager.knowledge_graph.relations.values():
        # 过滤条件
        if source_id and relation.source_id != source_id:
            continue
        if target_id and relation.target_id != target_id:
            continue
        if relation_type and relation.relation_type.value != relation_type:
            continue
        
        results.append(relation.to_dict())
    
    return {
        "filters": {
            "source_id": source_id,
            "target_id": target_id,
            "relation_type": relation_type
        },
        "count": len(results),
        "relations": results
    }


@app.get("/query/path")
async def query_path(
    source_id: str = Query(..., description="源实体ID"),
    target_id: str = Query(..., description="目标实体ID"),
    max_depth: int = Query(3, description="最大深度")
):
    """查询实体路径"""
    if query_engine is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    paths = query_engine.find_path(source_id, target_id, max_depth)
    return {
        "source_id": source_id,
        "target_id": target_id,
        "max_depth": max_depth,
        "paths": paths,
        "count": len(paths)
    }


@app.get("/query/components")
async def query_components(
    feature: Optional[str] = Query(None, description="功能名称"),
    component_type: Optional[str] = Query(None, description="组件类型")
):
    """查询组件"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    if feature:
        # 根据功能查找组件
        components = query_engine.find_components_by_feature(feature)
    else:
        # 查找所有组件
        components = graph_manager.search_entities("", EntityType.COMPONENT)
    
    # 按类型过滤
    if component_type:
        components = [c for c in components if component_type.lower() in c.name.lower()]
    
    return {
        "feature": feature,
        "component_type": component_type,
        "count": len(components),
        "components": [component.to_dict() for component in components]
    }


@app.get("/query/apis")
async def query_apis(
    component: Optional[str] = Query(None, description="组件名称"),
    api_type: Optional[str] = Query(None, description="API类型")
):
    """查询API端点"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    if component:
        # 根据组件查找API
        apis = query_engine.find_apis_by_component(component)
    else:
        # 查找所有API
        apis = graph_manager.search_entities("", EntityType.API)
    
    # 按类型过滤
    if api_type:
        apis = [a for a in apis if api_type.lower() in a.properties.get('api_type', '').lower()]
    
    return {
        "component": component,
        "api_type": api_type,
        "count": len(apis),
        "apis": [api.to_dict() for api in apis]
    }


@app.get("/query/features")
async def query_features(
    category: Optional[str] = Query(None, description="功能类别")
):
    """查询功能"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    features = graph_manager.search_entities("", EntityType.FEATURE)
    
    # 按类别过滤
    if category:
        features = [f for f in features if category.lower() in f.description.lower()]
    
    return {
        "category": category,
        "count": len(features),
        "features": [feature.to_dict() for feature in features]
    }


@app.get("/query/documents")
async def query_documents(
    doc_type: Optional[str] = Query(None, description="文档类型"),
    entity_id: Optional[str] = Query(None, description="关联实体ID")
):
    """查询文档"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    if entity_id:
        # 根据实体查找文档
        documents = query_engine.find_documents_by_entity(entity_id)
        docs = []
        for doc_path in documents:
            doc_entities = graph_manager.get_entity_by_name(doc_path)
            if doc_entities:
                docs.append(doc_entities[0])
    else:
        # 查找所有文档
        docs = graph_manager.search_entities("", EntityType.DOCUMENT)
    
    # 按类型过滤
    if doc_type:
        docs = [d for d in docs if doc_type.lower() in d.properties.get('doc_type', '').lower()]
    
    return {
        "doc_type": doc_type,
        "entity_id": entity_id,
        "count": len(docs),
        "documents": [doc.to_dict() for doc in docs]
    }


@app.get("/query/entities-by-document")
async def query_entities_by_document(
    doc_path: str = Query(..., description="文档路径")
):
    """查询文档相关的实体"""
    if query_engine is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    entities = query_engine.find_entities_by_document(doc_path)
    return {
        "doc_path": doc_path,
        "count": len(entities),
        "entities": [entity.to_dict() for entity in entities]
    }


@app.get("/query/critical")
async def query_critical_components():
    """查询关键组件"""
    if query_engine is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    critical = query_engine.find_critical_components()
    return {
        "count": len(critical),
        "components": [component.to_dict() for component in critical]
    }


@app.get("/query/isolated")
async def query_isolated_entities():
    """查询孤立实体"""
    if query_engine is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    isolated = query_engine.find_isolated_entities()
    return {
        "count": len(isolated),
        "entities": [entity.to_dict() for entity in isolated]
    }


@app.post("/entity")
async def add_entity(entity_data: Dict[str, Any]):
    """添加实体"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    try:
        from .models import Entity, EntityType
        
        # 验证必填字段
        required_fields = ["name", "entity_type", "description"]
        for field in required_fields:
            if field not in entity_data:
                raise HTTPException(status_code=400, detail=f"缺少必填字段: {field}")
        
        # 创建实体对象
        entity = Entity(
            name=entity_data["name"],
            entity_type=EntityType(entity_data["entity_type"]),
            description=entity_data["description"],
            properties=entity_data.get("properties", {}),
            source_documents=entity_data.get("source_documents", [])
        )
        
        entity_id = graph_manager.add_entity(entity)
        return {
            "status": "success",
            "entity_id": entity_id,
            "message": "实体添加成功"
        }
    except HTTPException:
        # 重新抛出HTTPException
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的实体类型: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加实体失败: {str(e)}")


@app.put("/entity/{entity_id}")
async def update_entity(entity_id: str, updates: Dict[str, Any]):
    """更新实体"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    success = graph_manager.update_entity(entity_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail=f"实体不存在: {entity_id}")
    
    return {
        "status": "success",
        "entity_id": entity_id,
        "message": "实体更新成功"
    }


@app.delete("/entity/{entity_id}")
async def delete_entity(entity_id: str):
    """删除实体"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    success = graph_manager.remove_entity(entity_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"实体不存在: {entity_id}")
    
    return {
        "status": "success",
        "entity_id": entity_id,
        "message": "实体删除成功"
    }


@app.post("/relation")
async def add_relation(relation_data: Dict[str, Any]):
    """添加关系"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    try:
        from .models import Relation, RelationType
        
        # 验证必填字段
        required_fields = ["source_id", "target_id", "relation_type", "description"]
        for field in required_fields:
            if field not in relation_data:
                raise HTTPException(status_code=400, detail=f"缺少必填字段: {field}")
        
        # 验证实体是否存在
        source_entity = graph_manager.get_entity_by_id(relation_data["source_id"])
        target_entity = graph_manager.get_entity_by_id(relation_data["target_id"])
        
        if not source_entity:
            raise HTTPException(status_code=404, detail=f"源实体不存在: {relation_data['source_id']}")
        if not target_entity:
            raise HTTPException(status_code=404, detail=f"目标实体不存在: {relation_data['target_id']}")
        
        # 创建关系对象
        relation = Relation(
            source_id=relation_data["source_id"],
            target_id=relation_data["target_id"],
            relation_type=RelationType(relation_data["relation_type"]),
            description=relation_data["description"],
            properties=relation_data.get("properties", {}),
            weight=relation_data.get("weight", 1.0)
        )
        
        relation_id = graph_manager.add_relation(relation)
        return {
            "status": "success",
            "relation_id": relation_id,
            "message": "关系添加成功"
        }
    except HTTPException:
        # 重新抛出HTTPException
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的关系类型: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加关系失败: {str(e)}")


@app.get("/export/json")
async def export_json():
    """导出为JSON"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    try:
        file_path = graph_manager.export_to_json()
        return {
            "status": "success",
            "file_path": file_path,
            "message": "知识图谱已导出为JSON文件"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@app.get("/export/report")
async def export_report():
    """生成报告"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    try:
        report = graph_manager.generate_report()
        return {
            "status": "success",
            "report": report,
            "message": "知识图谱报告已生成"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成报告失败: {str(e)}")


@app.get("/export/csv")
async def export_csv():
    """导出为CSV"""
    if graph_manager is None:
        raise HTTPException(status_code=503, detail="知识图谱未初始化")
    
    try:
        graph_manager.export_to_csv()
        return {
            "status": "success",
            "message": "知识图谱已导出为CSV文件"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


def start_api_server(host: str = "0.0.0.0", port: int = 8090, project_root: str = None):
    """启动API服务器"""
    initialize_graph(project_root)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_api_server()