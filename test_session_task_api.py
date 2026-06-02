"""
测试会话管理和任务状态管理 API

运行方式：
    python test_session_task_api.py
"""

import os
import sys
import json
import asyncio
import requests
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# API 基础地址
BASE_URL = "http://localhost:8088"


def test_session_management():
    """测试会话管理接口"""
    print("\n" + "=" * 60)
    print("测试会话管理接口")
    print("=" * 60)
    
    # 1. 创建会话（通过聊天）
    print("\n1. 创建会话...")
    response = requests.post(f"{BASE_URL}/api/chat", json={
        "message": "你好",
        "session_id": "test_session_001"
    })
    
    if response.status_code == 200:
        data = response.json()
        session_id = data.get("session_id")
        print(f"   ✓ 会话创建成功: {session_id}")
    else:
        print(f"   ✗ 会话创建失败: {response.status_code}")
        return
    
    # 2. 获取会话列表
    print("\n2. 获取会话列表...")
    response = requests.get(f"{BASE_URL}/v1/agent/sessions")
    
    if response.status_code == 200:
        data = response.json()
        sessions = data.get("sessions", [])
        total = data.get("total", 0)
        print(f"   ✓ 获取成功，共 {total} 个会话")
        for session in sessions[:3]:  # 只显示前3个
            print(f"     - {session['session_id']}: {session['message_count']} 条消息")
    else:
        print(f"   ✗ 获取失败: {response.status_code}")
    
    # 3. 清空会话
    print("\n3. 清空会话...")
    response = requests.post(f"{BASE_URL}/v1/agent/session/clear", json={
        "session_id": "test_session_001"
    })
    
    if response.status_code == 200:
        print(f"   ✓ 会话清空成功")
    else:
        print(f"   ✗ 会话清空失败: {response.status_code}")


def test_persona_management():
    """测试 Persona 管理接口"""
    print("\n" + "=" * 60)
    print("测试 Persona 管理接口")
    print("=" * 60)
    
    # 1. 获取 Persona 列表
    print("\n1. 获取 Persona 列表...")
    response = requests.get(f"{BASE_URL}/v1/agent/personas")
    
    if response.status_code == 200:
        data = response.json()
        personas = data.get("personas", [])
        print(f"   ✓ 获取成功，共 {len(personas)} 个 Persona")
        for persona in personas[:5]:  # 只显示前5个
            print(f"     - {persona.get('name', 'unknown')}")
    else:
        print(f"   ✗ 获取失败: {response.status_code}")
    
    # 2. 热重载 Persona
    print("\n2. 热重载 Persona...")
    response = requests.post(f"{BASE_URL}/v1/agent/personas/reload")
    
    if response.status_code == 200:
        print(f"   ✓ Persona 重载成功")
    else:
        print(f"   ✗ Persona 重载失败: {response.status_code}")


def test_task_management():
    """测试任务状态管理接口"""
    print("\n" + "=" * 60)
    print("测试任务状态管理接口")
    print("=" * 60)
    
    # 1. 创建任务
    print("\n1. 创建任务...")
    response = requests.post(f"{BASE_URL}/api/tasks/create", json={
        "task_type": "code_review",
        "description": "审查 main.py 代码质量",
        "session_id": "test_session_001"
    })
    
    if response.status_code == 200:
        data = response.json()
        task = data.get("task", {})
        task_id = task.get("task_id")
        print(f"   ✓ 任务创建成功: {task_id}")
    else:
        print(f"   ✗ 任务创建失败: {response.status_code}")
        return
    
    # 2. 获取任务详情
    print("\n2. 获取任务详情...")
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}")
    
    if response.status_code == 200:
        data = response.json()
        task = data.get("task", {})
        print(f"   ✓ 获取成功")
        print(f"     - 类型: {task.get('task_type')}")
        print(f"     - 状态: {task.get('status')}")
        print(f"     - 描述: {task.get('description')}")
    else:
        print(f"   ✗ 获取失败: {response.status_code}")
    
    # 3. 更新任务状态
    print("\n3. 更新任务状态...")
    response = requests.put(f"{BASE_URL}/api/tasks/{task_id}", json={
        "status": "in_progress",
        "progress": 0.5
    })
    
    if response.status_code == 200:
        data = response.json()
        task = data.get("task", {})
        print(f"   ✓ 更新成功")
        print(f"     - 状态: {task.get('status')}")
        print(f"     - 进度: {task.get('progress')}")
    else:
        print(f"   ✗ 更新失败: {response.status_code}")
    
    # 4. 添加任务上下文
    print("\n4. 添加任务上下文...")
    response = requests.post(f"{BASE_URL}/api/tasks/{task_id}/context", json={
        "context_type": "file",
        "content": "def main():\n    pass",
        "metadata": {"file_name": "main.py", "language": "python"}
    })
    
    if response.status_code == 200:
        print(f"   ✓ 上下文添加成功")
    else:
        print(f"   ✗ 上下文添加失败: {response.status_code}")
    
    # 5. 获取任务上下文
    print("\n5. 获取任务上下文...")
    response = requests.get(f"{BASE_URL}/api/tasks/{task_id}/context")
    
    if response.status_code == 200:
        data = response.json()
        context = data.get("context", [])
        print(f"   ✓ 获取成功，共 {len(context)} 个上下文")
    else:
        print(f"   ✗ 获取失败: {response.status_code}")
    
    # 6. 完成任务
    print("\n6. 完成任务...")
    response = requests.put(f"{BASE_URL}/api/tasks/{task_id}", json={
        "status": "completed",
        "progress": 1.0,
        "result": {"issues": ["缺少注释", "函数过长"]}
    })
    
    if response.status_code == 200:
        data = response.json()
        task = data.get("task", {})
        print(f"   ✓ 任务完成")
        print(f"     - 状态: {task.get('status')}")
        print(f"     - 结果: {task.get('result')}")
    else:
        print(f"   ✗ 任务完成失败: {response.status_code}")
    
    # 7. 获取任务列表
    print("\n7. 获取任务列表...")
    response = requests.get(f"{BASE_URL}/api/tasks")
    
    if response.status_code == 200:
        data = response.json()
        tasks = data.get("tasks", [])
        total = data.get("total", 0)
        print(f"   ✓ 获取成功，共 {total} 个任务")
    else:
        print(f"   ✗ 获取失败: {response.status_code}")


def test_task_templates():
    """测试任务模板接口"""
    print("\n" + "=" * 60)
    print("测试任务模板接口")
    print("=" * 60)
    
    # 1. 获取模板列表
    print("\n1. 获取模板列表...")
    response = requests.get(f"{BASE_URL}/api/tasks/templates")
    
    if response.status_code == 200:
        data = response.json()
        templates = data.get("templates", [])
        print(f"   ✓ 获取成功，共 {len(templates)} 个模板")
        for template in templates:
            print(f"     - {template.get('name')}: {template.get('task_type')}")
    else:
        print(f"   ✗ 获取失败: {response.status_code}")
    
    # 2. 从模板创建任务
    print("\n2. 从模板创建任务...")
    response = requests.post(f"{BASE_URL}/api/tasks/templates/code_review/create")
    
    if response.status_code == 200:
        data = response.json()
        task = data.get("task", {})
        print(f"   ✓ 任务创建成功: {task.get('task_id')}")
        print(f"     - 类型: {task.get('task_type')}")
        print(f"     - 元数据: {task.get('metadata')}")
    else:
        print(f"   ✗ 任务创建失败: {response.status_code}")


def main():
    """主测试函数"""
    print("=" * 60)
    print("OpenCopilot 会话管理与任务状态管理 API 测试")
    print("=" * 60)
    print(f"API 地址: {BASE_URL}")
    print(f"测试时间: {datetime.now().isoformat()}")
    
    # 检查 API 是否可用
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"\n❌ API 服务不可用 (状态码: {response.status_code})")
            print("请先启动 API 服务: python smart_copilot_api.py")
            return
    except requests.exceptions.ConnectionError:
        print(f"\n❌ 无法连接到 API 服务")
        print("请先启动 API 服务: python smart_copilot_api.py")
        return
    
    # 运行测试
    test_session_management()
    test_persona_management()
    test_task_management()
    test_task_templates()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
