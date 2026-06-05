---
name: knowledge_search
version: "1.0.0"
description: 查询项目知识图谱，支持实体搜索、关系查询、路径查找
eligibility:
  os: [darwin, linux, win32]
tools:
  - name: query_entity
    description: 搜索知识图谱中的实体
    parameters:
      keyword:
        type: string
        description: 搜索关键词
        required: true
      entity_type:
        type: string
        description: 实体类型 (component/api/config/feature/document)
        required: false
  - name: find_related
    description: 查找与指定实体相关的其他实体
    parameters:
      entity_name:
        type: string
        description: 实体名称
        required: true
      relation_type:
        type: string
        description: 关系类型 (depends_on/implements/configures/contains 等)
        required: false
  - name: find_path
    description: 查找两个实体之间的关联路径
    parameters:
      from_entity:
        type: string
        description: 起始实体
        required: true
      to_entity:
        type: string
        description: 目标实体
        required: true
---

# Knowledge Search Skill

## 使用方法
当用户需要查询项目结构、API 端点、配置信息、模块依赖时使用此 Skill。

## 触发条件
- 用户问"XX 模块在哪个文件"、"有哪些 API 端点"
- 用户问"XX 和 YY 的关系是什么"
- 用户要求查看项目架构、模块依赖
- 用户需要查找特定功能的相关文档

## 数据源
- 项目文档知识图谱 (knowledge_graph/)
- 提取的实体和关系数据
- 实体类型: component, api, config, feature, document
