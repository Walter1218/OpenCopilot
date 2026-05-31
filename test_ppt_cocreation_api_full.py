#!/usr/bin/env python3
"""
PPT 共创 API 完整能力验收测试

测试所有 PPT 共创相关的 API 接口，包括：
1. /api/ppt/suggest - AI 主动建议
2. /api/ppt/analyze - 内容分析
3. /api/ppt/chat - 多轮对话
4. /api/ppt/check - 智能检查
5. /api/ppt/cocreation - PPT 共创（局部修改）

使用方式:
    1. 先启动 API 服务: python smart_copilot_api.py
    2. 运行测试: python test_ppt_cocreation_api_full.py
"""

import sys
import json
import httpx
import time
from typing import Dict, Any, List

BASE_URL = "http://localhost:8088"


def print_header(title: str):
    """打印测试标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_result(name: str, success: bool, detail: str = ""):
    """打印测试结果"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {name}")
    if detail:
        print(f"       {detail}")


def print_json(data: Dict[str, Any], prefix: str = "  "):
    """打印 JSON 数据"""
    print(f"{prefix}{json.dumps(data, ensure_ascii=False, indent=2)}")


def test_health() -> bool:
    """测试 API 服务健康状态"""
    print_header("API 服务健康检查")
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        data = r.json()
        success = r.status_code == 200 and data.get("status") == "healthy"
        print_result("健康检查", success, f"状态: {data.get('status')}, 运行时间: {data.get('uptime', 0):.1f}s")
        return success
    except Exception as e:
        print_result("健康检查", False, str(e))
        return False


def test_ppt_analyze() -> bool:
    """测试内容分析 API"""
    print_header("测试：内容分析 (/api/ppt/analyze)")
    
    test_cases = [
        {
            "name": "文本内容分析",
            "content": "这是一段关于人工智能的介绍，AI正在改变我们的生活和工作方式。",
            "expected_type": "text"
        },
        {
            "name": "数据对比内容分析",
            "content": "产品A销量100万，产品B销量200万，产品C销量150万，同比增长30%",
            "expected_type": "data_comparison"
        },
        {
            "name": "时间序列内容分析",
            "content": "2020年营收100万，2021年营收150万，2022年营收200万，2023年营收280万",
            "expected_type": "time_series"
        },
        {
            "name": "流程内容分析",
            "content": "第一步：需求分析，第二步：设计开发，第三步：测试验证，第四步：部署上线",
            "expected_type": "process"
        },
        {
            "name": "人物属性内容分析",
            "content": "姓名：张三，男，30岁，职位：高级工程师，擅长：Python和AI开发",
            "expected_type": "person_attributes"
        }
    ]
    
    results = []
    
    for case in test_cases:
        try:
            r = httpx.post(f"{BASE_URL}/api/ppt/analyze", json={
                "content": case["content"]
            }, timeout=30.0)
            
            data = r.json()
            success = r.status_code == 200
            content_type = data.get("content_type")
            confidence = data.get("confidence", 0)
            quality_score = data.get("quality_score", 0)
            
            # 检查返回的数据结构
            has_key_points = "key_points" in data
            has_entities = "entities" in data
            has_suggestions = "suggestions" in data
            has_recommended_visual = "recommended_visual" in data
            
            detail = (f"类型: {content_type} (期望: {case['expected_type']}), "
                     f"置信度: {confidence:.2f}, "
                     f"质量分: {quality_score:.2f}, "
                     f"关键点: {has_key_points}, 实体: {has_entities}, "
                     f"建议: {has_suggestions}, 推荐可视化: {has_recommended_visual}")
            
            # 检查内容类型是否符合预期
            type_match = content_type == case["expected_type"]
            
            print_result(case["name"], success and type_match, detail)
            results.append(success and type_match)
            
        except Exception as e:
            print_result(case["name"], False, str(e))
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n  内容分析测试: {passed}/{total} 通过")
    return passed == total


def test_ppt_suggest() -> bool:
    """测试 AI 主动建议 API"""
    print_header("测试：AI 主动建议 (/api/ppt/suggest)")
    
    # 准备测试数据
    slides = [
        {
            "index": 0,
            "title": "公司介绍",
            "content": "我们是一家专注于人工智能技术的公司",
            "layout": "center",
            "items": []
        },
        {
            "index": 1,
            "title": "产品功能",
            "content": "产品A销量100万，产品B销量200万，产品C销量150万",
            "layout": "text_only",
            "items": [
                {"text": "功能1：智能对话", "level": 0},
                {"text": "功能2：文档处理", "level": 0}
            ]
        }
    ]
    
    test_cases = [
        {
            "name": "通用建议",
            "current_slide": 0,
            "focus": None,
            "max_suggestions": 3
        },
        {
            "name": "视觉增强建议",
            "current_slide": 1,
            "focus": "visual_enhance",
            "max_suggestions": 2
        },
        {
            "name": "内容优化建议",
            "current_slide": 0,
            "focus": "content_optimize",
            "max_suggestions": 1
        }
    ]
    
    results = []
    
    for case in test_cases:
        try:
            r = httpx.post(f"{BASE_URL}/api/ppt/suggest", json={
                "context": {
                    "title": "测试PPT",
                    "theme": "corporate",
                    "total_slides": len(slides),
                    "current_slide": case["current_slide"],
                    "slides": slides
                },
                "focus": case["focus"],
                "max_suggestions": case["max_suggestions"]
            }, timeout=30.0)
            
            data = r.json()
            success = r.status_code == 200
            
            suggestions = data.get("suggestions", [])
            analysis = data.get("analysis")
            
            has_suggestions = len(suggestions) > 0
            has_analysis = analysis is not None
            
            # 检查建议结构
            suggestion_valid = True
            if has_suggestions:
                for s in suggestions:
                    if not all(k in s for k in ["id", "type", "title", "description", "confidence"]):
                        suggestion_valid = False
                        break
            
            detail = (f"建议数: {len(suggestions)}, 有分析: {has_analysis}, "
                     f"建议结构有效: {suggestion_valid}")
            
            if has_suggestions:
                detail += f"\n       第一个建议: {suggestions[0].get('title', 'N/A')}"
            
            print_result(case["name"], success and has_suggestions and suggestion_valid, detail)
            results.append(success and has_suggestions and suggestion_valid)
            
        except Exception as e:
            print_result(case["name"], False, str(e))
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n  AI建议测试: {passed}/{total} 通过")
    return passed == total


def test_ppt_chat() -> bool:
    """测试多轮对话 API"""
    print_header("测试：多轮对话 (/api/ppt/chat)")
    
    # 准备测试数据
    slides = [
        {
            "index": 0,
            "title": "产品介绍",
            "content": "这是一款智能助手产品",
            "layout": "center",
            "items": []
        }
    ]
    
    test_cases = [
        {
            "name": "创建会话",
            "session_id": None,
            "message": "你好，我想修改PPT",
            "context": {
                "title": "测试PPT",
                "current_slide": 0,
                "slides": slides
            }
        },
        {
            "name": "修改标题指令",
            "session_id": None,  # 将使用上一个测试的session_id
            "message": "把标题改为'智能助手'",
            "context": {
                "title": "测试PPT",
                "current_slide": 0,
                "slides": slides
            }
        }
    ]
    
    results = []
    session_id = None
    
    for case in test_cases:
        try:
            # 使用之前的session_id
            if case["session_id"] is None and session_id:
                case["session_id"] = session_id
            
            r = httpx.post(f"{BASE_URL}/api/ppt/chat", json={
                "session_id": case["session_id"],
                "message": case["message"],
                "context": case["context"]
            }, timeout=60.0)
            
            data = r.json()
            success = r.status_code == 200
            
            response = data.get("response") or ""
            new_session_id = data.get("session_id")
            options = data.get("options") or []
            requires_confirmation = data.get("requires_confirmation", False)
            context_update = data.get("context_update")
            
            # 保存session_id供后续测试使用
            if new_session_id:
                session_id = new_session_id
            
            has_response = len(response) > 0
            has_session = new_session_id is not None
            
            detail = (f"会话ID: {new_session_id[:8] if new_session_id else 'N/A'}..., "
                     f"响应长度: {len(response)}, 选项数: {len(options)}, "
                     f"需要确认: {requires_confirmation}")
            
            if has_response:
                detail += f"\n       响应预览: {response[:100]}..."
            
            print_result(case["name"], success and has_response and has_session, detail)
            results.append(success and has_response and has_session)
            
        except Exception as e:
            print_result(case["name"], False, str(e))
            results.append(False)
    
    # 测试获取会话历史
    if session_id:
        try:
            r = httpx.get(f"{BASE_URL}/api/ppt/chat/{session_id}/history", timeout=10.0)
            data = r.json()
            success = r.status_code == 200
            
            messages = data.get("messages") or []
            has_messages = len(messages) > 0
            
            print_result("获取会话历史", success and has_messages, 
                        f"消息数: {len(messages)}")
            results.append(success and has_messages)
            
        except Exception as e:
            print_result("获取会话历史", False, str(e))
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n  多轮对话测试: {passed}/{total} 通过")
    return passed == total


def test_ppt_check() -> bool:
    """测试智能检查 API"""
    print_header("测试：智能检查 (/api/ppt/check)")
    
    # 准备测试数据
    slides = [
        {
            "index": 0,
            "title": "封面",
            "content": "公司年度报告",
            "layout": "center",
            "items": [],
            "style": {"font_size": 24, "color": "#333333"}
        },
        {
            "index": 1,
            "title": "内容页",
            "content": "这是一段很长的内容" * 50,  # 故意创建超长内容
            "layout": "text_only",
            "items": [
                {"text": "要点1", "level": 0},
                {"text": "要点2", "level": 0}
            ],
            "style": {"font_size": 12, "color": "#666666"}
        },
        {
            "index": 2,
            "title": "数据页",
            "content": "销售额：100万，利润：20万，增长率：15%",
            "layout": "text_only",
            "items": [],
            "style": {"font_size": 14, "color": "#ff0000"}  # 不同的颜色风格
        }
    ]
    
    test_cases = [
        {
            "name": "内容质量检查",
            "checks": ["content_quality"],
            "expected_findings": True
        },
        {
            "name": "风格一致性检查",
            "checks": ["style_consistency"],
            "expected_findings": True
        },
        {
            "name": "逻辑流程检查",
            "checks": ["logical_flow"],
            "expected_findings": False  # 可能没有逻辑问题
        },
        {
            "name": "综合检查",
            "checks": ["content_quality", "style_consistency", "logical_flow"],
            "expected_findings": True
        }
    ]
    
    results = []
    
    for case in test_cases:
        try:
            r = httpx.post(f"{BASE_URL}/api/ppt/check", json={
                "context": {
                    "title": "测试PPT",
                    "theme": "corporate",
                    "total_slides": len(slides),
                    "current_slide": 0,
                    "slides": slides
                },
                "checks": case["checks"]
            }, timeout=30.0)
            
            data = r.json()
            success = r.status_code == 200
            
            check_results = data.get("results", [])
            has_findings = len(check_results) > 0
            
            # 检查结果结构
            results_valid = True
            if has_findings:
                for r in check_results:
                    if not all(k in r for k in ["id", "severity", "category", "message"]):
                        results_valid = False
                        break
            
            detail = (f"检查项: {case['checks']}, 发现问题: {len(check_results)}, "
                     f"结果有效: {results_valid}")
            
            if has_findings:
                detail += f"\n       第一个问题: {check_results[0].get('message', 'N/A')}"
            
            print_result(case["name"], success and results_valid, detail)
            results.append(success and results_valid)
            
        except Exception as e:
            print_result(case["name"], False, str(e))
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n  智能检查测试: {passed}/{total} 通过")
    return passed == total


def test_ppt_cocreation() -> bool:
    """测试 PPT 共创 API（局部修改）"""
    print_header("测试：PPT 共创 (/api/ppt/cocreation)")
    
    test_cases = [
        {
            "name": "修改标题",
            "slides": [
                {
                    "title": "AI 助手介绍",
                    "subtitle": "智能办公",
                    "type": "title",
                    "layout": "center",
                    "items": []
                }
            ],
            "instruction": "把标题改为'智能助手'",
            "expected_action": "update"
        },
        {
            "name": "添加要点",
            "slides": [
                {
                    "title": "产品功能",
                    "subtitle": "",
                    "type": "content",
                    "layout": "text_only",
                    "items": [
                        {"text": "功能A", "level": 0, "content_type": "text"},
                        {"text": "功能B", "level": 0, "content_type": "text"}
                    ]
                }
            ],
            "instruction": "添加一个新要点：功能C",
            "expected_action": "add_item"
        }
    ]
    
    results = []
    
    for case in test_cases:
        try:
            r = httpx.post(f"{BASE_URL}/api/ppt/cocreation", json={
                "original_text": "",
                "slides": case["slides"],
                "instruction": case["instruction"]
            }, timeout=120.0)
            
            data = r.json()
            success = r.status_code == 200
            
            update_type = data.get("update_type")
            action = data.get("action")
            updated_slides = data.get("updated_slides", [])
            
            has_updated_slides = len(updated_slides) > 0
            action_match = action == case["expected_action"] or update_type == "partial"
            
            detail = (f"更新类型: {update_type}, 动作: {action}, "
                     f"幻灯片数: {len(updated_slides)}")
            
            print_result(case["name"], success and has_updated_slides and action_match, detail)
            results.append(success and has_updated_slides and action_match)
            
        except Exception as e:
            print_result(case["name"], False, str(e))
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n  PPT共创测试: {passed}/{total} 通过")
    return passed == total


def test_internal_apis() -> bool:
    """测试内部 API（测试、验证、基准测试、自检）"""
    print_header("测试：内部 API")
    
    results = []
    
    # 测试内部测试 API
    try:
        r = httpx.post(f"{BASE_URL}/api/internal/test", json={
            "test_suite": "ppt_cocreation",
            "test_cases": [
                {
                    "name": "内容分析",
                    "input": {"content": "测试内容"},
                    "expected": {"content_type": "text"}
                }
            ],
            "auto_fix": False
        }, timeout=30.0)
        
        data = r.json()
        success = r.status_code == 200
        
        test_results = data.get("results", [])
        has_results = len(test_results) > 0
        
        print_result("内部测试 API", success and has_results, 
                    f"测试结果数: {len(test_results)}")
        results.append(success and has_results)
        
    except Exception as e:
        print_result("内部测试 API", False, str(e))
        results.append(False)
    
    # 测试内部验证 API
    try:
        r = httpx.post(f"{BASE_URL}/api/internal/verify", json={
            "action": "validate_table",
            "input_data": {"content": "测试数据"},
            "output_data": {
                "title": "测试表格",
                "rows": [["A", 100], ["B", 200]],
                "columns": ["名称", "数值"]
            },
            "validation_rules": [
                {"rule": "has_title", "expected": True},
                {"rule": "row_count", "expected": 2}
            ]
        }, timeout=30.0)
        
        data = r.json()
        success = r.status_code == 200
        
        all_passed = data.get("all_passed", False)
        checks = data.get("checks", [])
        
        print_result("内部验证 API", success, 
                    f"全部通过: {all_passed}, 检查项: {len(checks)}")
        results.append(success)
        
    except Exception as e:
        print_result("内部验证 API", False, str(e))
        results.append(False)
    
    # 测试基准测试 API
    try:
        r = httpx.post(f"{BASE_URL}/api/internal/benchmark", json={
            "benchmark": "content_analysis",
            "iterations": 5,
            "test_data": {"content": "测试内容"}
        }, timeout=30.0)
        
        data = r.json()
        success = r.status_code == 200
        
        avg_time = data.get("avg_time", 0)
        
        print_result("基准测试 API", success, 
                    f"平均耗时: {avg_time:.3f}s")
        results.append(success)
        
    except Exception as e:
        print_result("基准测试 API", False, str(e))
        results.append(False)
    
    # 测试自检 API
    try:
        r = httpx.get(f"{BASE_URL}/api/internal/self-check", timeout=30.0)
        
        data = r.json()
        success = r.status_code == 200
        
        status = data.get("status", "unknown")
        
        print_result("自检 API", success, 
                    f"状态: {status}")
        results.append(success)
        
    except Exception as e:
        print_result("自检 API", False, str(e))
        results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n  内部API测试: {passed}/{total} 通过")
    return passed == total


def test_error_handling() -> bool:
    """测试错误处理"""
    print_header("测试：错误处理")
    
    results = []
    
    # 测试无效请求
    test_cases = [
        {
            "name": "空内容分析",
            "url": "/api/ppt/analyze",
            "data": {"content": "   "},
            "expected_status": 422  # 验证错误
        },
        {
            "name": "无效JSON",
            "url": "/api/ppt/analyze",
            "data": "invalid json",
            "expected_status": 422
        },
        {
            "name": "缺少必填字段",
            "url": "/api/ppt/suggest",
            "data": {},
            "expected_status": 422
        }
    ]
    
    for case in test_cases:
        try:
            if isinstance(case["data"], str):
                # 发送无效JSON
                r = httpx.post(f"{BASE_URL}{case['url']}", 
                              content=case["data"],
                              headers={"Content-Type": "application/json"},
                              timeout=10.0)
            else:
                r = httpx.post(f"{BASE_URL}{case['url']}", 
                              json=case["data"],
                              timeout=10.0)
            
            success = r.status_code == case["expected_status"]
            print_result(case["name"], success, 
                        f"状态码: {r.status_code} (期望: {case['expected_status']})")
            results.append(success)
            
        except Exception as e:
            print_result(case["name"], False, str(e))
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    print(f"\n  错误处理测试: {passed}/{total} 通过")
    return passed == total


def run_all_tests() -> bool:
    """运行所有测试"""
    print_header("PPT 共创 API 完整能力验收测试")
    print("测试所有 PPT 共创相关的 API 接口")
    print("=" * 60)
    
    # 先检查 API 服务
    if not test_health():
        print("\n❌ API 服务未运行，请先启动: python smart_copilot_api.py")
        return False
    
    # 运行所有测试
    test_results = []
    
    tests = [
        ("内容分析", test_ppt_analyze),
        ("AI主动建议", test_ppt_suggest),
        ("多轮对话", test_ppt_chat),
        ("智能检查", test_ppt_check),
        ("PPT共创", test_ppt_cocreation),
        ("内部API", test_internal_apis),
        ("错误处理", test_error_handling)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print_result(test_name, False, f"测试异常: {str(e)}")
            test_results.append((test_name, False))
    
    # 汇总结果
    print_header("测试汇总")
    
    passed = sum(1 for _, r in test_results if r)
    failed = sum(1 for _, r in test_results if not r)
    total = len(test_results)
    
    print(f"\n  总计: {total} 个测试模块")
    print(f"  通过: {passed} ✅")
    print(f"  失败: {failed} ❌")
    print(f"  通过率: {passed/total*100:.1f}%")
    
    print("\n  详细结果:")
    for name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"    {status} | {name}")
    
    if failed > 0:
        print("\n  失败的测试模块:")
        for name, result in test_results:
            if not result:
                print(f"    - {name}")
    
    print("\n" + "=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)