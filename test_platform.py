#!/usr/bin/env python3
"""
Smart Copilot 能力平台测试脚本
"""

import httpx
import json
import time

BASE_URL = 'http://localhost:8089'

def test_health():
    """测试健康检查"""
    print("🔍 测试健康检查...")
    resp = httpx.get(f'{BASE_URL}/health')
    data = resp.json()
    print(f"   状态: {data['status']}, 版本: {data['version']}")
    return data['status'] == 'healthy'

def test_root():
    """测试根路径"""
    print("🔍 测试根路径...")
    resp = httpx.get(f'{BASE_URL}/')
    data = resp.json()
    print(f"   名称: {data['name']}")
    print(f"   能力: {data['capabilities']}")
    return 'capabilities' in data

def test_context_inject():
    """测试上下文注入"""
    print("🔍 测试上下文注入...")
    resp = httpx.post(
        f'{BASE_URL}/api/context/inject',
        params={'content': '这是一个测试文本，用于验证上下文注入功能。'}
    )
    data = resp.json()
    print(f"   上下文ID: {data.get('context_id', 'N/A')}")
    print(f"   来源: {data.get('source', 'N/A')}")
    return 'context_id' in data

def test_context_current():
    """测试获取当前上下文"""
    print("🔍 测试获取当前上下文...")
    resp = httpx.get(f'{BASE_URL}/api/context/current')
    data = resp.json()
    print(f"   内容: {data.get('content', 'N/A')[:50]}...")
    return 'content' in data

def test_probe_status():
    """测试系统探测状态"""
    print("🔍 测试系统探测状态...")
    resp = httpx.get(f'{BASE_URL}/api/probe/status')
    data = resp.json()
    print(f"   Broker 在线: {data.get('broker_online', False)}")
    print(f"   IDE 连接: {data.get('ide_connected', False)}")
    print(f"   浏览器连接: {data.get('browser_connected', False)}")
    return 'broker_online' in data

def test_execute_translate():
    """测试翻译动作"""
    print("🔍 测试翻译动作...")
    resp = httpx.post(
        f'{BASE_URL}/api/execute',
        json={
            'action': 'translate',
            'context_source': 'custom',
            'context_content': 'Hello World, this is a test.',
            'parameters': {'target_language': 'zh'}
        },
        timeout=30.0
    )
    data = resp.json()
    print(f"   动作: {data.get('action', 'N/A')}")
    print(f"   结果: {data.get('result', 'N/A')[:50]}...")
    return 'result' in data

def test_execute_polish():
    """测试润色动作"""
    print("🔍 测试润色动作...")
    resp = httpx.post(
        f'{BASE_URL}/api/execute',
        json={
            'action': 'polish',
            'context_source': 'custom',
            'context_content': '这个产品很好，功能强大。',
            'parameters': {}
        },
        timeout=30.0
    )
    data = resp.json()
    print(f"   动作: {data.get('action', 'N/A')}")
    print(f"   结果: {data.get('result', 'N/A')[:50]}...")
    return 'result' in data

def test_execute_code():
    """测试代码解析动作"""
    print("🔍 测试代码解析动作...")
    resp = httpx.post(
        f'{BASE_URL}/api/execute',
        json={
            'action': 'code',
            'context_source': 'custom',
            'context_content': 'def hello():\n    print("Hello, World!")',
            'parameters': {}
        },
        timeout=30.0
    )
    data = resp.json()
    print(f"   动作: {data.get('action', 'N/A')}")
    print(f"   结果: {data.get('result', 'N/A')[:50]}...")
    return 'result' in data

def test_execute_auto():
    """测试自动动作"""
    print("🔍 测试自动动作...")
    resp = httpx.post(
        f'{BASE_URL}/api/execute',
        json={
            'action': 'auto',
            'context_source': 'custom',
            'context_content': '人工智能是计算机科学的一个分支，它企图了解智能的实质。',
            'parameters': {}
        },
        timeout=30.0
    )
    data = resp.json()
    print(f"   动作: {data.get('action', 'N/A')}")
    print(f"   结果: {data.get('result', 'N/A')[:50]}...")
    return 'result' in data

def main():
    """主测试函数"""
    print("=" * 60)
    print("  Smart Copilot 能力平台测试")
    print("=" * 60)
    
    results = []
    
    # 基础测试
    print("\n📦 基础接口测试")
    print("-" * 40)
    results.append(("健康检查", test_health()))
    results.append(("根路径", test_root()))
    
    # 上下文测试
    print("\n📦 上下文管理测试")
    print("-" * 40)
    results.append(("上下文注入", test_context_inject()))
    results.append(("当前上下文", test_context_current()))
    
    # 系统探测测试
    print("\n📦 系统探测测试")
    print("-" * 40)
    results.append(("探测状态", test_probe_status()))
    
    # 动作执行测试
    print("\n📦 动作执行测试")
    print("-" * 40)
    results.append(("翻译动作", test_execute_translate()))
    results.append(("润色动作", test_execute_polish()))
    results.append(("代码解析", test_execute_code()))
    results.append(("自动动作", test_execute_auto()))
    
    # 汇总
    print("\n" + "=" * 60)
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    print(f"总计: {len(results)} 项 | 通过: {passed} ✅ | 失败: {failed} ❌")
    print(f"通过率: {passed/len(results)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 所有测试通过！Smart Copilot 能力平台可正常使用。")
    else:
        print("\n⚠️ 部分测试失败，请检查服务状态。")
    
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
