#!/usr/bin/env python3
"""
知识图谱功能测试脚本

测试知识图谱的构建、查询和导出功能。
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from knowledge_graph import GraphManager, QueryEngine
from knowledge_graph.models import EntityType, RelationType


def test_basic_functionality():
    """测试基本功能"""
    print("=" * 60)
    print("测试知识图谱基本功能")
    print("=" * 60)
    
    # 初始化图管理器
    graph_manager = GraphManager(str(project_root))
    
    # 构建知识图谱
    print("1. 构建知识图谱...")
    knowledge_graph = graph_manager.build_graph(force_rebuild=True)
    
    # 获取统计信息
    stats = graph_manager.get_statistics()
    print(f"   实体总数: {stats['total_entities']}")
    print(f"   关系总数: {stats['total_relations']}")
    print(f"   实体类型分布:")
    for entity_type, count in stats['entity_types'].items():
        print(f"     - {entity_type}: {count}")
    
    return graph_manager


def test_entity_search(graph_manager):
    """测试实体搜索"""
    print("\n" + "=" * 60)
    print("测试实体搜索")
    print("=" * 60)
    
    # 搜索组件
    print("\n1. 搜索组件 'Agent':")
    agents = graph_manager.search_entities("Agent", EntityType.COMPONENT)
    for agent in agents:
        print(f"   - {agent.name}: {agent.description}")
    
    # 搜索API
    print("\n2. 搜索API端点 '/v1/agent/chat':")
    apis = graph_manager.search_entities("/v1/agent/chat", EntityType.API)
    for api in apis:
        print(f"   - {api.name}: {api.description}")
    
    # 搜索功能
    print("\n3. 搜索功能 'PPT':")
    features = graph_manager.search_entities("PPT", EntityType.FEATURE)
    for feature in features:
        print(f"   - {feature.name}: {feature.description}")
    
    # 搜索文档
    print("\n4. 搜索文档 'README':")
    docs = graph_manager.search_entities("README", EntityType.DOCUMENT)
    for doc in docs:
        print(f"   - {doc.name}: {doc.description}")


def test_relationships(graph_manager):
    """测试关系查询"""
    print("\n" + "=" * 60)
    print("测试关系查询")
    print("=" * 60)
    
    # 获取查询引擎
    query_engine = QueryEngine(graph_manager.knowledge_graph)
    
    # 查找Agent相关实体
    print("\n1. 查找 'ASU Custom Agent' 相关实体:")
    agent_entities = graph_manager.get_entity_by_name("ASU Custom Agent")
    if agent_entities:
        agent = agent_entities[0]
        related = query_engine.find_related_entities(agent.id)
        print(f"   找到 {related['count']} 个相关实体:")
        for entity in related['entities'][:5]:  # 只显示前5个
            print(f"     - {entity.name} ({entity.entity_type.value})")
    
    # 查找关键组件
    print("\n2. 查找关键组件（被依赖最多）:")
    critical = query_engine.find_critical_components()
    for component in critical[:5]:
        print(f"   - {component.name}: 被依赖 {component.properties.get('dependency_count', 0)} 次")


def test_export(graph_manager):
    """测试导出功能"""
    print("\n" + "=" * 60)
    print("测试导出功能")
    print("=" * 60)
    
    # 导出为JSON
    print("\n1. 导出为JSON文件:")
    json_file = graph_manager.export_to_json()
    print(f"   已导出到: {json_file}")
    
    # 生成报告
    print("\n2. 生成知识图谱报告:")
    report = graph_manager.generate_report()
    report_file = project_root / "knowledge_graph" / "export" / "knowledge_graph_report.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"   报告已保存到: {report_file}")
    
    # 显示报告摘要
    print("\n3. 报告摘要:")
    lines = report.split('\n')
    for line in lines[:20]:  # 只显示前20行
        print(f"   {line}")
    if len(lines) > 20:
        print(f"   ... 还有 {len(lines) - 20} 行")


def test_specific_queries(graph_manager):
    """测试特定查询"""
    print("\n" + "=" * 60)
    print("测试特定查询")
    print("=" * 60)
    
    query_engine = QueryEngine(graph_manager.knowledge_graph)
    
    # 查找端口配置
    print("\n1. 查找端口配置:")
    port_configs = graph_manager.search_entities("端口", EntityType.CONFIG)
    for config in port_configs[:5]:
        print(f"   - {config.name}: {config.description}")
    
    # 查找PPT相关组件
    print("\n2. 查找PPT相关组件:")
    ppt_components = query_engine.find_components_by_feature("PPT CoCreation")
    for component in ppt_components:
        print(f"   - {component.name}: {component.description}")
    
    # 查找Agent相关API
    print("\n3. 查找Agent相关API:")
    agent_apis = query_engine.find_apis_by_component("ASU Custom Agent")
    for api in agent_apis[:5]:
        print(f"   - {api.name}")
    
    # 查找孤立实体
    print("\n4. 查找孤立实体:")
    isolated = query_engine.find_isolated_entities()
    print(f"   找到 {len(isolated)} 个孤立实体")
    for entity in isolated[:5]:
        print(f"   - {entity.name} ({entity.entity_type.value})")


def main():
    """主函数"""
    print("OpenCopilot 知识图谱功能测试")
    print("=" * 60)
    
    try:
        # 基本功能测试
        graph_manager = test_basic_functionality()
        
        # 实体搜索测试
        test_entity_search(graph_manager)
        
        # 关系查询测试
        test_relationships(graph_manager)
        
        # 导出功能测试
        test_export(graph_manager)
        
        # 特定查询测试
        test_specific_queries(graph_manager)
        
        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        
        # 显示最终统计
        stats = graph_manager.get_statistics()
        print(f"\n最终统计:")
        print(f"  实体总数: {stats['total_entities']}")
        print(f"  关系总数: {stats['total_relations']}")
        print(f"  实体类型: {len(stats['entity_types'])}")
        print(f"  关系类型: {len(stats['relation_types'])}")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())