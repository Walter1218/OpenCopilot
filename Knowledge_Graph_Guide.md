# OpenCopilot 知识图谱使用指南

## 概述

OpenCopilot 知识图谱是从项目文档中自动提取核心知识，以结构化形式组织的知识库。它能够：

1. **自动提取**：从 89 个文档文件中自动识别实体和关系
2. **结构化存储**：以 JSON 格式存储实体、关系和属性
3. **智能查询**：支持多种查询方式，包括实体搜索、关系查询、路径查找等
4. **API 接口**：提供 RESTful API，支持远程查询

## 快速开始

### 1. 构建知识图谱

```python
from knowledge_graph import GraphManager

# 初始化图管理器
graph_manager = GraphManager("/path/to/OpenCopilot")

# 构建知识图谱（首次运行会自动提取）
knowledge_graph = graph_manager.build_graph()

# 获取统计信息
stats = graph_manager.get_statistics()
print(f"实体总数: {stats['total_entities']}")
print(f"关系总数: {stats['total_relations']}")
```

### 2. 查询知识图谱

```python
from knowledge_graph import QueryEngine

# 初始化查询引擎
query_engine = QueryEngine(knowledge_graph)

# 搜索实体
agents = graph_manager.search_entities("Agent", EntityType.COMPONENT)

# 获取实体上下文
context = query_engine.get_entity_context("entity_id")

# 查找相关实体
related = query_engine.find_related_entities("entity_id")
```

### 3. 启动 API 服务器

```bash
# 启动知识图谱 API 服务器
python start_knowledge_graph_api.py --port 8090

# 访问 API 文档
# http://localhost:8090/docs
```

## 知识图谱结构

### 实体类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `component` | 系统组件 | ASU Custom Agent、ASU Broker、IDE Extension |
| `api` | API 端点 | /v1/agent/chat、/api/v1/system/capabilities |
| `config` | 配置项 | 端口 18888、config.json |
| `feature` | 功能特性 | PPT 共创、Persona 系统、上下文管理 |
| `document` | 文档文件 | README.md、OpenCopilot_Custom_Agent_Guide.md |
| `test` | 测试相关 | Phase1 测试、单元测试 |
| `deployment` | 部署相关 | LaunchAgent、守护进程 |
| `persona` | 人设配置 | code.md、translate.md |
| `tool` | 工具 | evaluation_tools.py |
| `concept` | 架构概念 | 双引擎、双图层 |

### 关系类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `depends_on` | 依赖关系 | UI 依赖 Agent |
| `implements` | 实现关系 | 文档实现功能 |
| `configures` | 配置关系 | Persona 配置 Agent |
| `tests` | 测试关系 | 测试覆盖功能 |
| `documents` | 文档关系 | 文档描述组件 |
| `communicates_with` | 通信关系 | IDE 与 Agent 通信 |
| `contains` | 包含关系 | 目录包含文件 |
| `extends` | 扩展关系 | 组件扩展 |
| `uses` | 使用关系 | Agent 使用 Provider |
| `replaces` | 替代关系 | 新版替代旧版 |

## API 接口

### 基础接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | API 信息和能力列表 |
| `/health` | GET | 健康检查 |
| `/graph/statistics` | GET | 知识图谱统计信息 |

### 实体查询

| 端点 | 方法 | 描述 |
|------|------|------|
| `/entity/search` | GET | 搜索实体 |
| `/entity/{entity_id}` | GET | 获取实体详情 |
| `/entity/{entity_id}/related` | GET | 获取相关实体 |
| `/entity/{entity_id}/context` | GET | 获取实体上下文 |
| `/entity/{entity_id}/report` | GET | 获取实体报告 |
| `/entity/by-name/{name}` | GET | 根据名称获取实体 |
| `/entity/by-property` | GET | 根据属性获取实体 |

### 关系查询

| 端点 | 方法 | 描述 |
|------|------|------|
| `/relation/search` | GET | 搜索关系 |
| `/query/path` | GET | 查询实体路径 |

### 分类查询

| 端点 | 方法 | 描述 |
|------|------|------|
| `/query/components` | GET | 查询组件 |
| `/query/apis` | GET | 查询 API 端点 |
| `/query/features` | GET | 查询功能 |
| `/query/documents` | GET | 查询文档 |
| `/query/critical` | GET | 查询关键组件 |
| `/query/isolated` | GET | 查询孤立实体 |

### 实体管理

| 端点 | 方法 | 描述 |
|------|------|------|
| `/entity` | POST | 添加实体 |
| `/entity/{entity_id}` | PUT | 更新实体 |
| `/entity/{entity_id}` | DELETE | 删除实体 |
| `/relation` | POST | 添加关系 |

### 统计查询

| 端点 | 方法 | 描述 |
|------|------|------|
| `/graph/statistics` | GET | 获取统计信息 |
| `/graph/statistics-by-type` | GET | 按类型获取统计信息 |
| `/query/entities-by-document` | GET | 查询文档相关实体 |

### 导出功能

| 端点 | 方法 | 描述 |
|------|------|------|
| `/export/json` | GET | 导出为 JSON |
| `/export/csv` | GET | 导出为 CSV |
| `/export/report` | GET | 生成报告 |

## 使用示例

### 示例 1：查找 Agent 相关组件

```python
# 查找 Agent 相关组件
components = query_engine.find_components_by_feature("ASU Custom Agent")
for component in components:
    print(f"{component.name}: {component.description}")
```

### 示例 2：查找关键组件

```python
# 查找被依赖最多的组件
critical = query_engine.find_critical_components()
for component in critical:
    print(f"{component.name}: 被依赖 {component.properties.get('dependency_count', 0)} 次")
```

### 示例 3：生成实体报告

```python
# 生成实体报告
report = query_engine.generate_entity_report("entity_id")
print(report)
```

### 示例 4：通过 API 查询

```bash
# 搜索 Agent 相关实体
curl "http://localhost:8090/entity/search?query=Agent"

# 获取组件列表
curl "http://localhost:8090/query/components"

# 获取 API 端点
curl "http://localhost:8090/query/apis"

# 生成报告
curl "http://localhost:8090/export/report"
```

## 知识图谱统计

当前知识图谱包含：

- **实体总数**：264 个
- **关系总数**：166 个
- **实体类型**：5 种
- **关系类型**：4 种

### 实体分布

| 类型 | 数量 | 说明 |
|------|------|------|
| document | 52 | 文档文件 |
| config | 103 | 配置项 |
| api | 90 | API 端点 |
| feature | 10 | 功能特性 |
| component | 9 | 系统组件 |

### 关系分布

| 类型 | 数量 | 说明 |
|------|------|------|
| documents | 161 | 文档描述关系 |
| depends_on | 2 | 依赖关系 |
| uses | 2 | 使用关系 |
| communicates_with | 1 | 通信关系 |

## 扩展知识图谱

### 添加新实体

```python
from knowledge_graph.models import Entity, EntityType

entity = Entity(
    name="NewComponent",
    entity_type=EntityType.COMPONENT,
    description="新组件",
    properties={"version": "1.0"},
    source_documents=["new_doc.md"]
)

graph_manager.add_entity(entity)
```

### 添加新关系

```python
from knowledge_graph.models import Relation, RelationType

relation = Relation(
    source_id="entity_id_1",
    target_id="entity_id_2",
    relation_type=RelationType.DEPENDS_ON,
    description="依赖关系"
)

graph_manager.add_relation(relation)
```

### 重新构建知识图谱

```python
# 强制重新构建
knowledge_graph = graph_manager.build_graph(force_rebuild=True)
```

## 文件结构

```
knowledge_graph/
├── __init__.py          # 模块初始化
├── models.py            # 数据模型定义
├── extractor.py         # 文档知识提取器
├── graph.py             # 知识图谱管理器
├── query.py             # 查询引擎
├── api.py               # RESTful API 接口
└── export/              # 导出文件目录
    ├── knowledge_graph_*.json
    └── knowledge_graph_report.md
```

## 常见问题

### Q: 如何更新知识图谱？

A: 调用 `graph_manager.build_graph(force_rebuild=True)` 会重新从文档中提取知识。

### Q: 如何添加新的文档类型？

A: 在 `extractor.py` 中的 `doc_type_mapping` 字典中添加新的映射。

### Q: 如何自定义实体提取规则？

A: 在 `extractor.py` 中修改相应的正则表达式模式。

### Q: API 服务器如何生产部署？

A: 使用 uvicorn 或 gunicorn 部署：
```bash
uvicorn knowledge_graph.api:app --host 0.0.0.0 --port 8090 --workers 4
```

## 相关文档

- `Knowledge_Graph_Guide.md` - 本使用指南
- `Project_Documentation_Overview.md` - 项目文档全景分析
- `Smart_Copilot_API_Guide.md` - API 使用指南

## 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-05-31 | v1.0 | 初始版本，实现知识图谱构建和查询功能 |
| 2026-05-31 | v1.1 | 补充缺失API端点，实现100%功能覆盖 |

## API 覆盖率测试

### 测试结果

- **总测试数**：37
- **成功测试**：37
- **失败测试**：0
- **成功率**：100.0%

### 覆盖的功能

| 功能模块 | API 端点 | 测试状态 |
|----------|----------|----------|
| 健康检查 | `/health`, `/` | ✓ 通过 |
| 统计信息 | `/graph/statistics`, `/graph/statistics-by-type` | ✓ 通过 |
| 实体操作 | `/entity/search`, `/entity/{entity_id}`, `/entity/by-name/{name}`, `/entity/by-property` | ✓ 通过 |
| 实体管理 | `/entity` (POST), `/entity/{entity_id}` (PUT/DELETE) | ✓ 通过 |
| 关系操作 | `/relation/search`, `/relation` (POST) | ✓ 通过 |
| 查询功能 | `/query/path`, `/query/components`, `/query/apis`, `/query/features`, `/query/documents`, `/query/entities-by-document`, `/query/critical`, `/query/isolated` | ✓ 通过 |
| 导出功能 | `/export/json`, `/export/csv`, `/export/report` | ✓ 通过 |
| 错误处理 | 无效参数、不存在实体、缺少必填字段 | ✓ 通过 |

### 运行测试

```bash
# 启动 API 服务器
python start_knowledge_graph_api.py --port 8090

# 运行覆盖率测试
python test_api_coverage.py

# 运行覆盖率分析
python analyze_api_coverage.py
```

### 测试文件

| 文件 | 说明 |
|------|------|
| `test_api_coverage.py` | API 覆盖率测试脚本 |
| `analyze_api_coverage.py` | API 覆盖率分析脚本 |
| `knowledge_graph/test_results.json` | 测试结果数据 |