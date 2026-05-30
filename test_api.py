"""
Smart Copilot API 测试脚本

测试所有 API 端点的功能。

使用方式:
    1. 先启动 API 服务: python smart_copilot_api.py
    2. 运行测试: python test_api.py
"""

import os
import sys
import json
import httpx
import asyncio
from datetime import datetime

BASE_URL = f"http://localhost:{os.environ.get('API_PORT', 8088)}"

def print_header(title):
    """打印测试标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_result(name, success, detail=""):
    """打印测试结果"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {name}")
    if detail:
        print(f"       {detail}")

def test_health_check():
    """测试健康检查"""
    print_header("健康检查")
    
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        data = response.json()
        
        success = response.status_code == 200 and data["status"] == "healthy"
        print_result("健康检查", success, f"状态: {data['status']}, 运行时间: {data['uptime']:.1f}秒")
        return success
    except Exception as e:
        print_result("健康检查", False, str(e))
        return False

def test_root():
    """测试根路径"""
    print_header("根路径")
    
    try:
        response = httpx.get(f"{BASE_URL}/", timeout=5.0)
        data = response.json()
        
        success = response.status_code == 200 and "message" in data
        print_result("根路径", success, f"消息: {data.get('message')}")
        return success
    except Exception as e:
        print_result("根路径", False, str(e))
        return False

def test_config():
    """测试配置接口"""
    print_header("配置管理")
    
    try:
        # 获取配置
        response = httpx.get(f"{BASE_URL}/api/config", timeout=5.0)
        data = response.json()
        
        success = response.status_code == 200
        print_result("获取配置", success, f"Provider 类型: {data.get('provider_type')}")
        
        # 扫描模型
        response = httpx.post(f"{BASE_URL}/api/config/scan-models", timeout=10.0)
        data = response.json()
        
        success = response.status_code == 200
        print_result("扫描模型", success, f"发现 {len(data.get('models', []))} 个模型")
        
        return True
    except Exception as e:
        print_result("配置接口", False, str(e))
        return False

def test_system_status():
    """测试系统状态"""
    print_header("系统状态")
    
    try:
        response = httpx.get(f"{BASE_URL}/api/system/status", timeout=5.0)
        data = response.json()
        
        success = response.status_code == 200
        print_result("系统状态", success, 
                     f"Broker: {'在线' if data.get('broker_online') else '离线'}, "
                     f"IDE: {'连接' if data.get('ide_connected') else '未连接'}")
        return success
    except Exception as e:
        print_result("系统状态", False, str(e))
        return False

def test_chat():
    """测试聊天接口"""
    print_header("AI 对话")
    
    try:
        # 非流式对话
        response = httpx.post(f"{BASE_URL}/api/chat", json={
            "message": "请用一句话介绍自己",
            "session_id": "test-session-1"
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and "response" in data
        print_result("非流式对话", success, 
                     f"响应长度: {len(data.get('response', ''))} 字符")
        
        # 获取历史
        session_id = data.get("session_id")
        response = httpx.get(f"{BASE_URL}/api/chat/{session_id}/history", timeout=5.0)
        history = response.json()
        
        success = response.status_code == 200
        print_result("会话历史", success, f"消息数: {len(history.get('messages', []))}")
        
        return True
    except Exception as e:
        print_result("聊天接口", False, str(e))
        return False

def test_text_process():
    """测试文本处理"""
    print_header("文本处理")
    
    try:
        # 翻译
        response = httpx.post(f"{BASE_URL}/api/text/translate", params={
            "text": "Hello, how are you?",
            "target_language": "zh"
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and "processed" in data
        print_result("翻译", success, f"结果: {data.get('processed', '')[:50]}...")
        
        # 润色
        response = httpx.post(f"{BASE_URL}/api/text/polish", params={
            "text": "这个产品很好用，功能很强"
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and "processed" in data
        print_result("润色", success, f"结果: {data.get('processed', '')[:50]}...")
        
        return True
    except Exception as e:
        print_result("文本处理", False, str(e))
        return False

def test_ppt_generate():
    """测试 PPT 生成"""
    print_header("PPT 生成")
    
    try:
        slides = [
            {
                "type": "title",
                "title": "测试演示文稿",
                "subtitle": "API 生成测试"
            },
            {
                "type": "content",
                "title": "功能列表",
                "layout": "text_only",
                "items": [
                    {"text": "AI 对话", "level": 0},
                    {"text": "PPT 生成", "level": 0},
                    {"text": "文本处理", "level": 1}
                ]
            }
        ]
        
        # 生成 PPT
        response = httpx.post(f"{BASE_URL}/api/ppt/generate", json={
            "slides": slides,
            "filename": "test_api.pptx"
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and "file_path" in data
        print_result("生成 PPT", success, 
                     f"文件: {data.get('file_path')}, 大小: {data.get('file_size')} bytes")
        
        return True
    except Exception as e:
        print_result("PPT 生成", False, str(e))
        return False

def test_ppt_extract():
    """测试从文本提取 PPT"""
    print_header("PPT 文本提取")
    
    try:
        text = """
        人工智能是计算机科学的一个分支，它企图了解智能的实质，
        并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
        
        机器学习是人工智能的一个子集，它使系统能够从数据中学习和改进。
        
        深度学习是机器学习的一个子集，它使用神经网络来模拟人脑的工作方式。
        """
        
        response = httpx.post(f"{BASE_URL}/api/ppt/extract-from-text", 
                            params={"text": text},
                            timeout=60.0)
        
        data = response.json()
        success = response.status_code == 200 and "extracted_slides" in data
        print_result("文本提取", success, 
                     f"提取了 {data.get('slide_count', 0)} 页幻灯片")
        
        return True
    except Exception as e:
        print_result("文本提取", False, str(e))
        return False

def test_batch_process():
    """测试批量处理"""
    print_header("批量处理")
    
    try:
        texts = [
            "Hello world",
            "Good morning",
            "Thank you"
        ]
        
        response = httpx.post(f"{BASE_URL}/api/batch/process", json={
            "texts": texts,
            "action": "translate",
            "target_language": "zh"
        }, timeout=60.0)
        
        data = response.json()
        success = response.status_code == 200 and "results" in data
        print_result("批量翻译", success, 
                     f"成功: {data.get('success')}, 失败: {data.get('failed')}")
        
        return True
    except Exception as e:
        print_result("批量处理", False, str(e))
        return False

def test_stream_chat():
    """测试流式对话"""
    print_header("流式对话")
    
    try:
        print("  测试流式响应...")
        full_response = ""
        
        with httpx.stream("POST", f"{BASE_URL}/api/chat/stream", json={
            "message": "请用3个词描述春天"
        }, timeout=30.0) as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "chunk" in data:
                        full_response += data["chunk"]
                        print(".", end="", flush=True)
                    elif data.get("done"):
                        print()
        
        success = len(full_response) > 0
        print_result("流式对话", success, f"响应长度: {len(full_response)} 字符")
        
        return True
    except Exception as e:
        print_result("流式对话", False, str(e))
        return False

def run_all_tests():
    """运行所有测试"""
    print("\n" + "🚀" * 30)
    print("  Smart Copilot API 测试")
    print("🚀" * 30)
    
    tests = [
        ("基础连接", [test_root, test_health_check]),
        ("配置管理", [test_config]),
        ("系统探测", [test_system_status]),
        ("AI 对话", [test_chat, test_stream_chat]),
        ("文本处理", [test_text_process]),
        ("PPT 功能", [test_ppt_generate, test_ppt_extract]),
        ("批量处理", [test_batch_process])
    ]
    
    results = []
    
    for category, test_funcs in tests:
        print(f"\n📦 {category}")
        print("-" * 40)
        for test_func in test_funcs:
            try:
                result = test_func()
                results.append((test_func.__name__, result))
            except Exception as e:
                print_result(test_func.__name__, False, str(e))
                results.append((test_func.__name__, False))
    
    # 汇总结果
    print_header("测试汇总")
    
    passed = sum(1 for _, r in results if r)
    failed = sum(1 for _, r in results if not r)
    total = len(results)
    
    print(f"\n  总计: {total} 项测试")
    print(f"  通过: {passed} ✅")
    print(f"  失败: {failed} ❌")
    print(f"  通过率: {passed/total*100:.1f}%")
    
    if failed > 0:
        print("\n  失败的测试:")
        for name, result in results:
            if not result:
                print(f"    - {name}")
    
    print("\n" + "=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    # 检查 API 是否运行
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=2.0)
        if response.status_code != 200:
            print("❌ API 服务未运行，请先启动: python smart_copilot_api.py")
            sys.exit(1)
    except:
        print("❌ 无法连接到 API 服务，请先启动: python smart_copilot_api.py")
        sys.exit(1)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)
