#!/usr/bin/env python3
"""
知识图谱API覆盖率分析脚本

分析当前API端点与后端功能的覆盖情况。
"""

import re
import ast
from pathlib import Path


def analyze_api_coverage():
    """分析API覆盖率"""
    
    # 读取api.py文件
    api_file = Path("/Users/onetwo/Documents/trae_projects/OpenCopilot/knowledge_graph/api.py")
    with open(api_file, 'r', encoding='utf-8') as f:
        api_content = f.read()
    
    # 提取所有API端点
    api_pattern = r'@app\.(get|post|put|delete)\("([^"]+)"\)'
    api_endpoints = re.findall(api_pattern, api_content)
    
    print("=" * 80)
    print("知识图谱API覆盖率分析")
    print("=" * 80)
    
    print("\n1. 当前已实现的API端点：")
    print("-" * 40)
    for i, (method, path) in enumerate(api_endpoints, 1):
        print(f"  {i:2d}. [{method.upper()}] {path}")
    
    print(f"\n  总计：{len(api_endpoints)} 个API端点")
    
    # 读取query.py文件
    query_file = Path("/Users/onetwo/Documents/trae_projects/OpenCopilot/knowledge_graph/query.py")
    with open(query_file, 'r', encoding='utf-8') as f:
        query_content = f.read()
    
    # 提取QueryEngine类的所有方法
    query_methods = re.findall(r'def (\w+)\(self', query_content)
    
    print("\n2. QueryEngine类的方法：")
    print("-" * 40)
    for i, method in enumerate(query_methods, 1):
        print(f"  {i:2d}. {method}()")
    
    print(f"\n  总计：{len(query_methods)} 个方法")
    
    # 读取graph.py文件
    graph_file = Path("/Users/onetwo/Documents/trae_projects/OpenCopilot/knowledge_graph/graph.py")
    with open(graph_file, 'r', encoding='utf-8') as f:
        graph_content = f.read()
    
    # 提取GraphManager类的所有方法
    graph_methods = re.findall(r'def (\w+)\(self', graph_content)
    
    print("\n3. GraphManager类的方法：")
    print("-" * 40)
    for i, method in enumerate(graph_methods, 1):
        print(f"  {i:2d}. {method}()")
    
    print(f"\n  总计：{len(graph_methods)} 个方法")
    
    # 分析覆盖情况
    print("\n4. API覆盖分析：")
    print("-" * 40)
    
    # 已覆盖的方法（从API端点推断）
    covered_methods = {
        "search_entities": "/entity/search",
        "get_entity_by_id": "/entity/{entity_id}",
        "get_entity_context": "/entity/{entity_id}/context",
        "generate_entity_report": "/entity/{entity_id}/report",
        "find_related_entities": "/entity/{entity_id}/related",
        "get_entity_by_name": "/entity/by-name/{name}",
        "search_by_property": "/entity/by-property",
        "find_path": "/query/path",
        "find_components_by_feature": "/query/components",
        "find_apis_by_component": "/query/apis",
        "find_documents_by_entity": "/query/documents",
        "find_entities_by_document": "/query/entities-by-document",
        "find_critical_components": "/query/critical",
        "find_isolated_entities": "/query/isolated",
        "get_statistics": "/graph/statistics",
        "get_statistics_by_type": "/graph/statistics-by-type",
        "update_entity": "/entity/{entity_id}",
        "add_entity": "/entity",
        "add_relation": "/relation",
        "remove_entity": "/entity/{entity_id}",
        "export_to_json": "/export/json",
        "export_to_csv": "/export/csv",
        "generate_report": "/export/report"
    }
    
    # 内部方法（不需要API暴露）
    internal_methods = {
        "__init__", "build_graph", "save_graph", "load_graph", "find_entity", "get_related_entities"
    }
    
    # 未覆盖的方法
    uncovered_query = []
    for method in query_methods:
        if method not in covered_methods and method not in internal_methods:
            uncovered_query.append(method)
    
    uncovered_graph = []
    for method in graph_methods:
        if method not in covered_methods and method not in internal_methods:
            uncovered_graph.append(method)
    
    print("\n  已覆盖的方法：")
    for method, endpoint in covered_methods.items():
        print(f"    ✓ {method} -> {endpoint}")
    
    print(f"\n  未覆盖的方法（QueryEngine）：")
    for method in uncovered_query:
        if method != "__init__":
            print(f"    ✗ {method}()")
    
    print(f"\n  未覆盖的方法（GraphManager）：")
    for method in uncovered_graph:
        if method != "__init__":
            print(f"    ✗ {method}()")
    
    # 计算覆盖率
    total_methods = len(query_methods) + len(graph_methods) - 2  # 减去__init__
    covered_count = len(covered_methods)
    coverage = (covered_count / total_methods) * 100 if total_methods > 0 else 0
    
    print(f"\n5. 覆盖率统计：")
    print("-" * 40)
    print(f"  总方法数：{total_methods}")
    print(f"  已覆盖数：{covered_count}")
    print(f"  未覆盖数：{total_methods - covered_count}")
    print(f"  覆盖率：{coverage:.1f}%")
    
    # 建议添加的API
    print("\n6. 建议添加的API端点：")
    print("-" * 40)
    
    suggestions = []
    
    if "find_entities_by_document" not in covered_methods:
        suggestions.append(("find_entities_by_document", "/query/entities-by-document", "GET"))
    
    if "get_statistics_by_type" not in covered_methods:
        suggestions.append(("get_statistics_by_type", "/graph/statistics-by-type", "GET"))
    
    if "update_entity" not in covered_methods:
        suggestions.append(("update_entity", "/entity/{entity_id}", "PUT"))
    
    if "add_entity" not in covered_methods:
        suggestions.append(("add_entity", "/entity", "POST"))
    
    if "add_relation" not in covered_methods:
        suggestions.append(("add_relation", "/relation", "POST"))
    
    if "remove_entity" not in covered_methods:
        suggestions.append(("remove_entity", "/entity/{entity_id}", "DELETE"))
    
    if "export_to_csv" not in covered_methods:
        suggestions.append(("export_to_csv", "/export/csv", "GET"))
    
    for i, (method, endpoint, http_method) in enumerate(suggestions, 1):
        print(f"  {i}. [{http_method}] {endpoint} -> {method}()")
    
    if not suggestions:
        print("  无建议添加的API端点")
    
    print("\n" + "=" * 80)
    
    return {
        "total_endpoints": len(api_endpoints),
        "total_methods": total_methods,
        "covered_count": covered_count,
        "coverage": coverage,
        "uncovered_query": uncovered_query,
        "uncovered_graph": uncovered_graph,
        "suggestions": suggestions
    }


if __name__ == "__main__":
    result = analyze_api_coverage()