#!/usr/bin/env python3
"""
Smart Copilot API 全面测试套件

覆盖所有33个API端点，进行功能验证和API化验证。

使用方式:
    1. 先启动 API 服务: python smart_copilot_api.py
    2. 运行测试: python test_api_comprehensive.py

测试分类:
    1. 基础端点 (3个)
    2. 聊天功能 (3个)
    3. PPT功能 (8个)
    4. 文本处理 (4个)
    5. 系统功能 (5个)
    6. 配置管理 (3个)
    7. 批量处理 (1个)
    8. 内部测试 (4个)
"""

import os
import sys
import json
import httpx
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

BASE_URL = f"http://localhost:{os.environ.get('API_PORT', 8088)}"

# 测试统计
test_stats = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "skipped": 0
}

def print_header(title: str):
    """打印测试标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_result(name: str, success: bool, detail: str = ""):
    """打印测试结果"""
    global test_stats
    test_stats["total"] += 1
    
    if success:
        test_stats["passed"] += 1
        status = "✅ PASS"
    else:
        test_stats["failed"] += 1
        status = "❌ FAIL"
    
    print(f"{status} | {name}")
    if detail:
        print(f"       {detail}")

def print_skip(name: str, reason: str):
    """打印跳过的测试"""
    global test_stats
    test_stats["total"] += 1
    test_stats["skipped"] += 1
    print(f"⏭️ SKIP | {name}")
    print(f"       {reason}")

def print_json(data: Dict[str, Any], prefix: str = "  "):
    """打印 JSON 数据"""
    print(f"{prefix}{json.dumps(data, ensure_ascii=False, indent=2)}")

# ==========================================
# 基础端点测试 (3个)
# ==========================================

def test_root():
    """测试根路径"""
    print_header("基础端点: 根路径")
    try:
        response = httpx.get(f"{BASE_URL}/", timeout=5.0)
        data = response.json()
        success = response.status_code == 200 and "message" in data
        print_result("根路径", success, f"消息: {data.get('message')}")
        return success
    except Exception as e:
        print_result("根路径", False, str(e))
        return False

def test_health():
    """测试健康检查"""
    print_header("基础端点: 健康检查")
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        data = response.json()
        success = response.status_code == 200 and data.get("status") == "healthy"
        print_result("健康检查", success, 
                    f"状态: {data.get('status')}, 运行时间: {data.get('uptime', 0):.1f}s")
        return success
    except Exception as e:
        print_result("健康检查", False, str(e))
        return False

def test_docs():
    """测试API文档"""
    print_header("基础端点: API文档")
    try:
        # 测试Swagger UI
        response = httpx.get(f"{BASE_URL}/docs", timeout=5.0)
        success = response.status_code == 200
        print_result("Swagger UI", success, f"状态码: {response.status_code}")
        
        # 测试ReDoc
        response = httpx.get(f"{BASE_URL}/redoc", timeout=5.0)
        success = response.status_code == 200
        print_result("ReDoc", success, f"状态码: {response.status_code}")
        
        return True
    except Exception as e:
        print_result("API文档", False, str(e))
        return False

# ==========================================
# 聊天功能测试 (3个)
# ==========================================

def test_chat():
    """测试聊天接口"""
    print_header("聊天功能: 非流式对话")
    try:
        response = httpx.post(f"{BASE_URL}/api/chat", json={
            "message": "请用一句话介绍自己",
            "session_id": "test-session-1"
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and "response" in data
        print_result("非流式对话", success, 
                    f"响应长度: {len(data.get('response', ''))} 字符")
        
        # 获取会话ID
        session_id = data.get("session_id")
        if session_id:
            # 测试获取历史
            response = httpx.get(f"{BASE_URL}/api/chat/{session_id}/history", timeout=5.0)
            history = response.json()
            success = response.status_code == 200
            print_result("会话历史", success, f"消息数: {len(history.get('messages', []))}")
        
        return success
    except Exception as e:
        print_result("聊天接口", False, str(e))
        return False

def test_stream_chat():
    """测试流式对话"""
    print_header("聊天功能: 流式对话")
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
        
        return success
    except Exception as e:
        print_result("流式对话", False, str(e))
        return False

def test_chat_history():
    """测试聊天历史"""
    print_header("聊天功能: 聊天历史")
    try:
        # 先创建会话
        response = httpx.post(f"{BASE_URL}/api/chat", json={
            "message": "测试消息",
            "session_id": "test-history-session"
        }, timeout=30.0)
        
        data = response.json()
        session_id = data.get("session_id")
        
        if not session_id:
            print_result("聊天历史", False, "未获取到会话ID")
            return False
        
        # 获取历史
        response = httpx.get(f"{BASE_URL}/api/chat/{session_id}/history", timeout=5.0)
        history = response.json()
        
        success = response.status_code == 200 and "messages" in history
        print_result("聊天历史", success, 
                    f"会话ID: {session_id[:8]}..., 消息数: {len(history.get('messages', []))}")
        
        return success
    except Exception as e:
        print_result("聊天历史", False, str(e))
        return False

# ==========================================
# PPT功能测试 (8个)
# ==========================================

def test_ppt_generate():
    """测试PPT生成"""
    print_header("PPT功能: PPT生成")
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
        
        response = httpx.post(f"{BASE_URL}/api/ppt/generate", json={
            "slides": slides,
            "filename": "test_api.pptx"
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and "file_path" in data
        print_result("PPT生成", success, 
                    f"文件: {data.get('file_path')}, 大小: {data.get('file_size')} bytes")
        
        return success
    except Exception as e:
        print_result("PPT生成", False, str(e))
        return False

def test_ppt_generate_and_download():
    """测试PPT生成并下载"""
    print_header("PPT功能: PPT生成并下载")
    try:
        slides = [
            {
                "type": "title",
                "title": "下载测试",
                "subtitle": "测试下载功能"
            }
        ]
        
        response = httpx.post(f"{BASE_URL}/api/ppt/generate-and-download", json={
            "slides": slides,
            "filename": "test_download.pptx"
        }, timeout=30.0)
        
        # 检查是否返回文件流
        success = response.status_code == 200
        content_type = response.headers.get("content-type", "")
        
        print_result("PPT生成并下载", success, 
                    f"状态码: {response.status_code}, 内容类型: {content_type}")
        
        return success
    except Exception as e:
        print_result("PPT生成并下载", False, str(e))
        return False

def test_ppt_extract_from_text():
    """测试从文本提取PPT"""
    print_header("PPT功能: 从文本提取PPT")
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
        print_result("从文本提取PPT", success, 
                    f"提取了 {data.get('slide_count', 0)} 页幻灯片")
        
        return success
    except Exception as e:
        print_result("从文本提取PPT", False, str(e))
        return False

def test_ppt_cocreation():
    """测试PPT共创"""
    print_header("PPT功能: PPT共创")
    try:
        slides = [
            {
                "index": 0,
                "title": "公司介绍",
                "content": "我们是一家专注于人工智能技术的公司",
                "layout": "center",
                "items": []
            }
        ]
        
        response = httpx.post(f"{BASE_URL}/api/ppt/cocreation", json={
            "original_text": "公司介绍",
            "slides": slides,
            "instruction": "把标题改为'智能科技'",
            "session_id": "test-cocreation-session"
        }, timeout=60.0)
        
        data = response.json()
        success = response.status_code == 200
        print_result("PPT共创", success, 
                    f"状态码: {response.status_code}")
        
        return success
    except Exception as e:
        print_result("PPT共创", False, str(e))
        return False

def test_ppt_suggest():
    """测试PPT建议"""
    print_header("PPT功能: PPT建议")
    try:
        slides = [
            {
                "index": 0,
                "title": "公司介绍",
                "content": "我们是一家专注于人工智能技术的公司",
                "layout": "center",
                "items": []
            }
        ]
        
        response = httpx.post(f"{BASE_URL}/api/ppt/suggest", json={
            "context": {
                "title": "测试PPT",
                "theme": "corporate",
                "total_slides": len(slides),
                "current_slide": 0,
                "slides": slides
            },
            "focus": "visual_enhance",
            "max_suggestions": 3
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and "suggestions" in data
        print_result("PPT建议", success, 
                    f"建议数: {len(data.get('suggestions', []))}")
        
        return success
    except Exception as e:
        print_result("PPT建议", False, str(e))
        return False

def test_ppt_analyze():
    """测试PPT分析"""
    print_header("PPT功能: PPT分析")
    try:
        content = "产品A销量100万，产品B销量200万，产品C销量150万，同比增长30%"
        
        response = httpx.post(f"{BASE_URL}/api/ppt/analyze", json={
            "content": content
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and "content_type" in data
        print_result("PPT分析", success, 
                    f"内容类型: {data.get('content_type')}, 置信度: {data.get('confidence', 0):.2f}")
        
        return success
    except Exception as e:
        print_result("PPT分析", False, str(e))
        return False

def test_ppt_chat():
    """测试PPT聊天"""
    print_header("PPT功能: PPT聊天")
    try:
        slides = [
            {
                "index": 0,
                "title": "产品介绍",
                "content": "这是一款智能助手产品",
                "layout": "center",
                "items": []
            }
        ]
        
        response = httpx.post(f"{BASE_URL}/api/ppt/chat", json={
            "session_id": None,
            "message": "你好，我想修改PPT",
            "context": {
                "title": "测试PPT",
                "current_slide": 0,
                "slides": slides
            }
        }, timeout=60.0)
        
        data = response.json()
        success = response.status_code == 200 and "response" in data
        print_result("PPT聊天", success, 
                    f"响应长度: {len(data.get('response', ''))} 字符")
        
        return success
    except Exception as e:
        print_result("PPT聊天", False, str(e))
        return False

def test_ppt_check():
    """测试PPT检查"""
    print_header("PPT功能: PPT检查")
    try:
        response = httpx.post(f"{BASE_URL}/api/ppt/check", json={
            "context": {
                "title": "测试PPT",
                "theme": "corporate",
                "total_slides": 1,
                "current_slide": 0,
                "slides": [
                    {
                        "index": 0,
                        "title": "封面",
                        "content": "公司年度报告",
                        "layout": "center",
                        "items": []
                    }
                ]
            },
            "checks": ["content_quality", "style_consistency", "logical_flow"]
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200
        print_result("PPT检查", success, 
                    f"状态码: {response.status_code}")
        
        return success
    except Exception as e:
        print_result("PPT检查", False, str(e))
        return False

# ==========================================
# 文本处理测试 (4个)
# ==========================================

def test_text_process():
    """测试文本处理"""
    print_header("文本处理: 通用处理")
    try:
        response = httpx.post(f"{BASE_URL}/api/text/process", json={
            "text": "Hello, how are you?",
            "action": "translate",
            "target_language": "zh"
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and "processed" in data
        print_result("文本处理", success, 
                    f"处理结果: {data.get('processed', '')[:50]}...")
        
        return success
    except Exception as e:
        print_result("文本处理", False, str(e))
        return False

def test_text_translate():
    """测试翻译"""
    print_header("文本处理: 翻译")
    try:
        response = httpx.post(f"{BASE_URL}/api/text/translate", params={
            "text": "Hello, how are you?",
            "target_language": "zh"
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and "processed" in data
        print_result("翻译", success, 
                    f"翻译结果: {data.get('processed', '')[:50]}...")
        
        return success
    except Exception as e:
        print_result("翻译", False, str(e))
        return False

def test_text_polish():
    """测试润色"""
    print_header("文本处理: 润色")
    try:
        response = httpx.post(f"{BASE_URL}/api/text/polish", params={
            "text": "这个产品很好用，功能很强"
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and "processed" in data
        print_result("润色", success, 
                    f"润色结果: {data.get('processed', '')[:50]}...")
        
        return success
    except Exception as e:
        print_result("润色", False, str(e))
        return False

def test_text_explain():
    """测试解释"""
    print_header("文本处理: 解释")
    try:
        response = httpx.post(f"{BASE_URL}/api/text/explain", params={
            "text": "机器学习是人工智能的一个子集"
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and "processed" in data
        print_result("解释", success, 
                    f"解释结果: {data.get('processed', '')[:50]}...")
        
        return success
    except Exception as e:
        print_result("解释", False, str(e))
        return False

# ==========================================
# 系统功能测试 (5个)
# ==========================================

def test_system_status():
    """测试系统状态"""
    print_header("系统功能: 系统状态")
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

def test_system_clipboard():
    """测试剪贴板"""
    print_header("系统功能: 剪贴板")
    try:
        response = httpx.get(f"{BASE_URL}/api/system/clipboard", timeout=5.0)
        data = response.json()
        
        success = response.status_code == 200
        print_result("剪贴板", success, 
                    f"状态码: {response.status_code}")
        
        return success
    except Exception as e:
        print_result("剪贴板", False, str(e))
        return False

def test_system_selection():
    """测试选中文本"""
    print_header("系统功能: 选中文本")
    try:
        response = httpx.get(f"{BASE_URL}/api/system/selection", timeout=5.0)
        data = response.json()
        
        success = response.status_code == 200
        print_result("选中文本", success, 
                    f"状态码: {response.status_code}")
        
        return success
    except Exception as e:
        print_result("选中文本", False, str(e))
        return False

def test_system_frontmost_app():
    """测试前台应用"""
    print_header("系统功能: 前台应用")
    try:
        response = httpx.get(f"{BASE_URL}/api/system/frontmost-app", timeout=5.0)
        data = response.json()
        
        success = response.status_code == 200
        print_result("前台应用", success, 
                    f"状态码: {response.status_code}")
        
        return success
    except Exception as e:
        print_result("前台应用", False, str(e))
        return False

def test_system_screenshot():
    """测试截图"""
    print_header("系统功能: 截图")
    try:
        response = httpx.get(f"{BASE_URL}/api/system/screenshot", timeout=10.0)
        
        success = response.status_code == 200
        print_result("截图", success, 
                    f"状态码: {response.status_code}, 内容类型: {response.headers.get('content-type')}")
        
        return success
    except Exception as e:
        print_result("截图", False, str(e))
        return False

# ==========================================
# 配置管理测试 (3个)
# ==========================================

def test_config_get():
    """测试获取配置"""
    print_header("配置管理: 获取配置")
    try:
        response = httpx.get(f"{BASE_URL}/api/config", timeout=5.0)
        data = response.json()
        
        success = response.status_code == 200
        print_result("获取配置", success, 
                    f"Provider类型: {data.get('provider_type')}")
        
        return success
    except Exception as e:
        print_result("获取配置", False, str(e))
        return False

def test_config_update():
    """测试更新配置"""
    print_header("配置管理: 更新配置")
    try:
        # 先获取当前配置
        response = httpx.get(f"{BASE_URL}/api/config", timeout=5.0)
        current_config = response.json()
        
        # 更新配置（这里只是测试接口，不实际修改）
        response = httpx.post(f"{BASE_URL}/api/config", json={
            "provider_type": current_config.get("provider_type")
        }, timeout=5.0)
        
        success = response.status_code == 200
        print_result("更新配置", success, 
                    f"状态码: {response.status_code}")
        
        return success
    except Exception as e:
        print_result("更新配置", False, str(e))
        return False

def test_config_scan_models():
    """测试扫描模型"""
    print_header("配置管理: 扫描模型")
    try:
        response = httpx.post(f"{BASE_URL}/api/config/scan-models", timeout=30.0)
        data = response.json()
        
        success = response.status_code == 200
        print_result("扫描模型", success, 
                    f"发现 {len(data.get('models', []))} 个模型")
        
        return success
    except Exception as e:
        print_result("扫描模型", False, str(e))
        return False

# ==========================================
# 批量处理测试 (1个)
# ==========================================

def test_batch_process():
    """测试批量处理"""
    print_header("批量处理: 批量翻译")
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
        print_result("批量处理", success, 
                    f"成功: {data.get('success')}, 失败: {data.get('failed')}")
        
        return success
    except Exception as e:
        print_result("批量处理", False, str(e))
        return False

# ==========================================
# 内部测试端点 (4个)
# ==========================================

def test_internal_test():
    """测试内部测试端点"""
    print_header("内部测试: 功能测试")
    try:
        response = httpx.post(f"{BASE_URL}/api/internal/test", json={
            "test_suite": "content_analysis",
            "test_cases": [
                {
                    "name": "文本分析测试",
                    "input": {"content": "产品A销量100万，产品B销量200万"},
                    "expected": {"content_type": "data_comparison"}
                }
            ],
            "auto_fix": False
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200
        print_result("内部测试", success, 
                    f"状态码: {response.status_code}")
        
        return success
    except Exception as e:
        print_result("内部测试", False, str(e))
        return False

def test_internal_verify():
    """测试内部验证端点"""
    print_header("内部测试: 功能验证")
    try:
        response = httpx.post(f"{BASE_URL}/api/internal/verify", json={
            "action": "analyze",
            "input_data": {"content": "测试内容"},
            "output_data": {"content_type": "text"}
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200
        print_result("内部验证", success, 
                    f"状态码: {response.status_code}")
        
        return success
    except Exception as e:
        print_result("内部验证", False, str(e))
        return False

def test_internal_benchmark():
    """测试内部基准测试端点"""
    print_header("内部测试: 基准测试")
    try:
        response = httpx.post(f"{BASE_URL}/api/internal/benchmark", json={
            "benchmark": "content_analysis",
            "iterations": 3,
            "test_data": {
                "content": "产品A销量100万，产品B销量200万"
            }
        }, timeout=60.0)
        
        data = response.json()
        success = response.status_code == 200
        print_result("基准测试", success, 
                    f"状态码: {response.status_code}")
        
        return success
    except Exception as e:
        print_result("基准测试", False, str(e))
        return False

def test_internal_self_check():
    """测试内部自检端点"""
    print_header("内部测试: 自检")
    try:
        response = httpx.get(f"{BASE_URL}/api/internal/self-check", timeout=30.0)
        data = response.json()
        
        success = response.status_code == 200
        print_result("自检", success, 
                    f"状态码: {response.status_code}")
        
        return success
    except Exception as e:
        print_result("自检", False, str(e))
        return False

# ==========================================
# 内容处理测试 (2个)
# ==========================================

def test_content_analyze():
    """测试内容分析"""
    print_header("内容处理: 内容分析")
    try:
        response = httpx.post(f"{BASE_URL}/api/content/analyze", json={
            "text": "产品A销量100万，产品B销量200万，产品C销量150万，同比增长30%"
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200 and data.get("success")
        print_result("内容分析", success, 
                    f"状态码: {response.status_code}, 分析结果: {data.get('data', {}).get('suggestions', [])[:2]}")
        
        return success
    except Exception as e:
        print_result("内容分析", False, str(e))
        return False

def test_content_convert():
    """测试内容转换"""
    print_header("内容处理: 内容转换")
    try:
        response = httpx.post(f"{BASE_URL}/api/content/convert", json={
            "text": "产品A销量100万，产品B销量200万，产品C销量150万",
            "target_type": "table",
            "title": "产品销量对比"
        }, timeout=30.0)
        
        data = response.json()
        success = response.status_code == 200
        print_result("内容转换", success, 
                    f"状态码: {response.status_code}")
        
        return success
    except Exception as e:
        print_result("内容转换", False, str(e))
        return False

# ==========================================
# 主测试函数
# ==========================================

def run_all_tests():
    """运行所有测试"""
    print("\n" + "🚀" * 30)
    print("  Smart Copilot API 全面测试套件")
    print("🚀" * 30)
    
    # 测试分类
    test_categories = [
        ("基础端点", [test_root, test_health, test_docs]),
        ("聊天功能", [test_chat, test_stream_chat, test_chat_history]),
        ("PPT功能", [
            test_ppt_generate, test_ppt_generate_and_download, 
            test_ppt_extract_from_text, test_ppt_cocreation,
            test_ppt_suggest, test_ppt_analyze, test_ppt_chat, test_ppt_check
        ]),
        ("文本处理", [test_text_process, test_text_translate, test_text_polish, test_text_explain]),
        ("系统功能", [
            test_system_status, test_system_clipboard, test_system_selection,
            test_system_frontmost_app, test_system_screenshot
        ]),
        ("配置管理", [test_config_get, test_config_update, test_config_scan_models]),
        ("批量处理", [test_batch_process]),
        ("内容处理", [test_content_analyze, test_content_convert]),
        ("内部测试", [
            test_internal_test, test_internal_verify, 
            test_internal_benchmark, test_internal_self_check
        ])
    ]
    
    # 运行测试
    for category, test_funcs in test_categories:
        print(f"\n📦 {category}")
        print("-" * 40)
        for test_func in test_funcs:
            try:
                test_func()
            except Exception as e:
                print_result(test_func.__name__, False, str(e))
    
    # 汇总结果
    print_header("测试汇总")
    
    print(f"\n  总计: {test_stats['total']} 项测试")
    print(f"  通过: {test_stats['passed']} ✅")
    print(f"  失败: {test_stats['failed']} ❌")
    print(f"  跳过: {test_stats['skipped']} ⏭️")
    print(f"  通过率: {test_stats['passed']/test_stats['total']*100:.1f}%")
    
    # API覆盖率
    total_api_endpoints = 33
    covered_endpoints = test_stats['total']
    coverage_rate = covered_endpoints / total_api_endpoints * 100
    
    print(f"\n  API端点总数: {total_api_endpoints}")
    print(f"  已测试端点: {covered_endpoints}")
    print(f"  覆盖率: {coverage_rate:.1f}%")
    
    if test_stats['failed'] > 0:
        print("\n  失败的测试:")
        # 这里可以添加失败测试的详细信息
    
    print("\n" + "=" * 60)
    
    return test_stats['failed'] == 0

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