#!/usr/bin/env python3
"""
智能体全面集成测试 - 带LLM模型的完整覆盖测试

测试所有核心模块的集成情况：
1. CodeExecutor (代码执行)
2. KnowledgeRetrieval (知识检索)
3. SearchCapability (搜索能力)
4. ContextManager (上下文管理)
5. StateManager (状态管理)
6. Planner (规划器)
7. SecurityModule (安全模块)
8. ObservabilityModule (可观测性)
9. ImmuneSystem (AGENTS.md免疫机制)
10. SkillArchitecture (Skill化架构)
"""

import os
import sys
import json
import time
import threading
import requests
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 测试配置
BASE_URL = "http://127.0.0.1:18888"
TEST_SESSION_ID = f"test-{int(time.time())}"

# 测试结果
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "errors": [],
    "details": []
}

def log_test(test_name, passed, details="", error=None):
    """记录测试结果"""
    test_results["total"] += 1
    if passed:
        test_results["passed"] += 1
        status = "✅ PASS"
    else:
        test_results["failed"] += 1
        status = "❌ FAIL"
        if error:
            test_results["errors"].append({"test": test_name, "error": str(error)})
    
    test_results["details"].append({
        "name": test_name,
        "status": status,
        "details": details,
        "error": str(error) if error else None
    })
    
    print(f"{status} | {test_name}")
    if details:
        print(f"      {details}")
    if error:
        print(f"      Error: {error}")

def test_health_endpoint():
    """测试健康检查端点"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        passed = response.status_code == 200 and data.get("status") == "ok"
        log_test("健康检查端点", passed, f"Status: {data.get('status')}")
        return passed
    except Exception as e:
        log_test("健康检查端点", False, error=e)
        return False

def test_capabilities_endpoint():
    """测试能力查询端点"""
    try:
        response = requests.get(f"{BASE_URL}/capabilities", timeout=5)
        data = response.json()
        
        # 检查所有模块是否存在
        required_capabilities = [
            "code_execution", "knowledge_retrieval", "search",
            "context_management", "memory_system", "state_management",
            "planning", "security", "observability", "agents_md", "skill_architecture"
        ]
        
        capabilities = data.get("capabilities", {})
        missing = [cap for cap in required_capabilities if cap not in capabilities]
        
        passed = response.status_code == 200 and len(missing) == 0
        details = f"模块数: {len(capabilities)}, 缺失: {missing if missing else '无'}"
        log_test("能力查询端点", passed, details)
        return passed
    except Exception as e:
        log_test("能力查询端点", False, error=e)
        return False

def test_chat_endpoint(text, test_name, expected_keywords=None):
    """测试对话端点"""
    try:
        response = requests.post(
            f"{BASE_URL}/v1/agent/chat",
            json={
                "text": text,
                "session_id": TEST_SESSION_ID,
                "context_source": "chat"
            },
            timeout=120,
            stream=True
        )
        
        # 收集响应
        full_response = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: ") and line_str != "data: [DONE]":
                    try:
                        data = json.loads(line_str[6:])
                        full_response += data.get("chunk", "")
                    except:
                        pass
        
        # 检查是否包含预期关键词
        if expected_keywords:
            found_keywords = [kw for kw in expected_keywords if kw in full_response]
            passed = len(found_keywords) > 0
            details = f"响应长度: {len(full_response)}, 找到关键词: {found_keywords}"
        else:
            passed = len(full_response) > 0
            details = f"响应长度: {len(full_response)}"
        
        log_test(test_name, passed, details)
        return passed, full_response
    except Exception as e:
        log_test(test_name, False, error=e)
        return False, ""

def test_code_execution():
    """测试代码执行能力"""
    try:
        response = requests.post(
            f"{BASE_URL}/v1/agent/chat",
            json={
                "text": "执行代码: print(2 + 3)",
                "session_id": f"{TEST_SESSION_ID}-code",
                "context_source": "chat"
            },
            timeout=120,
            stream=True
        )
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: ") and line_str != "data: [DONE]":
                    try:
                        data = json.loads(line_str[6:])
                        full_response += data.get("chunk", "")
                    except:
                        pass
        
        passed = "5" in full_response and "代码执行成功" in full_response
        log_test("代码执行能力", passed, f"包含结果'5': {'5' in full_response}")
        return passed
    except Exception as e:
        log_test("代码执行能力", False, error=e)
        return False

def test_knowledge_retrieval():
    """测试知识检索能力"""
    try:
        response = requests.post(
            f"{BASE_URL}/v1/agent/chat",
            json={
                "text": "知识图谱中有哪些组件？",
                "session_id": f"{TEST_SESSION_ID}-knowledge",
                "context_source": "chat"
            },
            timeout=120,
            stream=True
        )
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: ") and line_str != "data: [DONE]":
                    try:
                        data = json.loads(line_str[6:])
                        full_response += data.get("chunk", "")
                    except:
                        pass
        
        passed = "知识检索" in full_response or "知识图谱" in full_response
        log_test("知识检索能力", passed, f"响应长度: {len(full_response)}")
        return passed
    except Exception as e:
        log_test("知识检索能力", False, error=e)
        return False

def test_search_capability():
    """测试搜索能力"""
    try:
        response = requests.post(
            f"{BASE_URL}/v1/agent/chat",
            json={
                "text": "搜索Python最佳实践",
                "session_id": f"{TEST_SESSION_ID}-search",
                "context_source": "chat"
            },
            timeout=120,
            stream=True
        )
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: ") and line_str != "data: [DONE]":
                    try:
                        data = json.loads(line_str[6:])
                        full_response += data.get("chunk", "")
                    except:
                        pass
        
        passed = "搜索" in full_response or "结果" in full_response
        log_test("搜索能力", passed, f"响应长度: {len(full_response)}")
        return passed
    except Exception as e:
        log_test("搜索能力", False, error=e)
        return False

def test_planning_capability():
    """测试任务规划能力"""
    try:
        response = requests.post(
            f"{BASE_URL}/v1/agent/chat",
            json={
                "text": "帮我规划一个Web应用开发任务",
                "session_id": f"{TEST_SESSION_ID}-planning",
                "context_source": "chat"
            },
            timeout=120,
            stream=True
        )
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: ") and line_str != "data: [DONE]":
                    try:
                        data = json.loads(line_str[6:])
                        full_response += data.get("chunk", "")
                    except:
                        pass
        
        passed = "规划" in full_response or "计划" in full_response or "步骤" in full_response
        log_test("任务规划能力", passed, f"响应长度: {len(full_response)}")
        return passed
    except Exception as e:
        log_test("任务规划能力", False, error=e)
        return False

def test_security_capability():
    """测试安全模块能力"""
    try:
        response = requests.post(
            f"{BASE_URL}/v1/agent/chat",
            json={
                "text": "查看安全模块状态",
                "session_id": f"{TEST_SESSION_ID}-security",
                "context_source": "chat"
            },
            timeout=120,
            stream=True
        )
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: ") and line_str != "data: [DONE]":
                    try:
                        data = json.loads(line_str[6:])
                        full_response += data.get("chunk", "")
                    except:
                        pass
        
        passed = "安全" in full_response or "权限" in full_response
        log_test("安全模块能力", passed, f"响应长度: {len(full_response)}")
        return passed
    except Exception as e:
        log_test("安全模块能力", False, error=e)
        return False

def test_llm_conversation():
    """测试LLM对话能力"""
    try:
        response = requests.post(
            f"{BASE_URL}/v1/agent/chat",
            json={
                "text": "你好，请介绍一下自己",
                "session_id": f"{TEST_SESSION_ID}-llm",
                "context_source": "chat"
            },
            timeout=120,
            stream=True
        )
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith("data: ") and line_str != "data: [DONE]":
                    try:
                        data = json.loads(line_str[6:])
                        full_response += data.get("chunk", "")
                    except:
                        pass
        
        passed = len(full_response) > 50  # 至少有50字符的响应
        log_test("LLM对话能力", passed, f"响应长度: {len(full_response)}")
        return passed
    except Exception as e:
        log_test("LLM对话能力", False, error=e)
        return False

def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("OpenCopilot 智能体全面集成测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试会话: {TEST_SESSION_ID}")
    print("="*60 + "\n")
    
    # 1. 基础端点测试
    print("\n【1. 基础端点测试】")
    test_health_endpoint()
    test_capabilities_endpoint()
    
    # 2. 核心能力测试
    print("\n【2. 核心能力测试】")
    test_code_execution()
    test_knowledge_retrieval()
    test_search_capability()
    
    # 3. 新集成模块测试
    print("\n【3. 新集成模块测试】")
    test_planning_capability()
    test_security_capability()
    
    # 4. LLM对话测试
    print("\n【4. LLM对话测试】")
    test_llm_conversation()
    
    # 5. 综合场景测试
    print("\n【5. 综合场景测试】")
    test_chat_endpoint(
        "帮我写一个Python函数计算斐波那契数列",
        "代码生成场景",
        expected_keywords=["def", "fibonacci"]
    )
    test_chat_endpoint(
        "解释一下什么是微服务架构",
        "知识问答场景",
        expected_keywords=["服务", "架构"]
    )
    
    # 输出测试结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    print(f"总测试数: {test_results['total']}")
    print(f"通过: {test_results['passed']} ✅")
    print(f"失败: {test_results['failed']} ❌")
    print(f"通过率: {test_results['passed']/test_results['total']*100:.1f}%")
    
    if test_results['errors']:
        print("\n失败详情:")
        for error in test_results['errors']:
            print(f"  - {error['test']}: {error['error']}")
    
    print("="*60)
    
    # 保存测试报告
    report = {
        "test_time": datetime.now().isoformat(),
        "session_id": TEST_SESSION_ID,
        "summary": {
            "total": test_results['total'],
            "passed": test_results['passed'],
            "failed": test_results['failed'],
            "pass_rate": f"{test_results['passed']/test_results['total']*100:.1f}%"
        },
        "details": test_results['details'],
        "errors": test_results['errors']
    }
    
    with open("agent_integration_test_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print("\n测试报告已保存: agent_integration_test_report.json")
    
    return test_results['failed'] == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
