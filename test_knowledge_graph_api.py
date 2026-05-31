#!/usr/bin/env python3
"""
知识图谱 API 测试脚本

测试知识图谱 API 的各个端点。
"""

import requests
import json
import sys
import time
from pathlib import Path

# API 基础URL
BASE_URL = "http://localhost:8090"


def test_health():
    """测试健康检查"""
    print("1. 测试健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"   状态: {data['status']}")
            print(f"   实体数: {data['entities']}")
            print(f"   关系数: {data['relations']}")
            return True
        else:
            print(f"   失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   错误: {e}")
        return False


def test_statistics():
    """测试统计信息"""
    print("\n2. 测试统计信息...")
    try:
        response = requests.get(f"{BASE_URL}/graph/statistics")
        if response.status_code == 200:
            data = response.json()
            print(f"   实体总数: {data['total_entities']}")
            print(f"   关系总数: {data['total_relations']}")
            print(f"   实体类型: {len(data['entity_types'])}")
            print(f"   关系类型: {len(data['relation_types'])}")
            return True
        else:
            print(f"   失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   错误: {e}")
        return False


def test_entity_search():
    """测试实体搜索"""
    print("\n3. 测试实体搜索...")
    try:
        # 搜索Agent
        response = requests.get(f"{BASE_URL}/entity/search", params={"query": "Agent"})
        if response.status_code == 200:
            data = response.json()
            print(f"   搜索 'Agent' 找到 {data['count']} 个实体:")
            for entity in data['entities'][:3]:
                print(f"     - {entity['name']}: {entity['description']}")
            return True
        else:
            print(f"   失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   错误: {e}")
        return False


def test_entity_by_name():
    """测试根据名称获取实体"""
    print("\n4. 测试根据名称获取实体...")
    try:
        response = requests.get(f"{BASE_URL}/entity/by-name/ASU Custom Agent")
        if response.status_code == 200:
            data = response.json()
            print(f"   找到 {data['count']} 个 'ASU Custom Agent' 实体:")
            for entity in data['entities']:
                print(f"     - ID: {entity['id']}")
                print(f"       类型: {entity['entity_type']}")
                print(f"       描述: {entity['description']}")
            return True
        else:
            print(f"   失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   错误: {e}")
        return False


def test_entity_context():
    """测试获取实体上下文"""
    print("\n5. 测试获取实体上下文...")
    try:
        # 先获取一个实体ID
        response = requests.get(f"{BASE_URL}/entity/search", params={"query": "Agent"})
        if response.status_code != 200 or not response.json()['entities']:
            print("   无法获取实体ID")
            return False
        
        entity_id = response.json()['entities'][0]['id']
        response = requests.get(f"{BASE_URL}/entity/{entity_id}/context")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   实体: {data['entity']['name']}")
            print(f"   相关实体: {data['statistics']['related_count']}")
            print(f"   关系数: {data['statistics']['relation_count']}")
            print(f"   文档数: {data['statistics']['document_count']}")
            return True
        else:
            print(f"   失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   错误: {e}")
        return False


def test_query_components():
    """测试查询组件"""
    print("\n6. 测试查询组件...")
    try:
        response = requests.get(f"{BASE_URL}/query/components")
        if response.status_code == 200:
            data = response.json()
            print(f"   找到 {data['count']} 个组件:")
            for component in data['components'][:5]:
                print(f"     - {component['name']}: {component['description']}")
            return True
        else:
            print(f"   失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   错误: {e}")
        return False


def test_query_apis():
    """测试查询API"""
    print("\n7. 测试查询API...")
    try:
        response = requests.get(f"{BASE_URL}/query/apis")
        if response.status_code == 200:
            data = response.json()
            print(f"   找到 {data['count']} 个API端点:")
            for api in data['apis'][:5]:
                print(f"     - {api['name']}")
            return True
        else:
            print(f"   失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   错误: {e}")
        return False


def test_query_features():
    """测试查询功能"""
    print("\n8. 测试查询功能...")
    try:
        response = requests.get(f"{BASE_URL}/query/features")
        if response.status_code == 200:
            data = response.json()
            print(f"   找到 {data['count']} 个功能:")
            for feature in data['features'][:5]:
                print(f"     - {feature['name']}: {feature['description']}")
            return True
        else:
            print(f"   失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   错误: {e}")
        return False


def test_query_documents():
    """测试查询文档"""
    print("\n9. 测试查询文档...")
    try:
        response = requests.get(f"{BASE_URL}/query/documents")
        if response.status_code == 200:
            data = response.json()
            print(f"   找到 {data['count']} 个文档:")
            for doc in data['documents'][:5]:
                print(f"     - {doc['name']}: {doc['description']}")
            return True
        else:
            print(f"   失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   错误: {e}")
        return False


def test_export():
    """测试导出功能"""
    print("\n10. 测试导出功能...")
    try:
        response = requests.get(f"{BASE_URL}/export/report")
        if response.status_code == 200:
            data = response.json()
            print(f"   状态: {data['status']}")
            print(f"   报告长度: {len(data['report'])} 字符")
            return True
        else:
            print(f"   失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   错误: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("知识图谱 API 测试")
    print("=" * 60)
    
    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(2)
    
    tests = [
        test_health,
        test_statistics,
        test_entity_search,
        test_entity_by_name,
        test_entity_context,
        test_query_components,
        test_query_apis,
        test_query_features,
        test_query_documents,
        test_export
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"   测试异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")
    print("=" * 60)
    
    if passed == total:
        print("所有测试通过！")
        return 0
    else:
        print("部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())