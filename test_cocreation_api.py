#!/usr/bin/env python3
"""
PPT 共创 API 接口测试

测试局部修改功能是否正常工作。
需要先启动 API 服务：python smart_copilot_api.py
"""

import sys
import json
import httpx
import time

BASE_URL = "http://localhost:8088"


def print_header(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_result(name, success, detail=""):
    status = "PASS" if success else "FAIL"
    print(f"[{status}] {name}")
    if detail:
        print(f"       {detail}")


def test_health():
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


def test_cocreation_update_title():
    """测试：修改标题（局部更新）"""
    print_header("测试：修改标题")
    
    slides = [
        {
            "title": "AI 助手介绍",
            "subtitle": "智能办公",
            "type": "title",
            "layout": "center",
            "items": []
        },
        {
            "title": "核心功能",
            "subtitle": "",
            "type": "content",
            "layout": "text_only",
            "items": [
                {"text": "智能对话", "level": 0, "content_type": "text"},
                {"text": "文档处理", "level": 0, "content_type": "text"},
                {"text": "代码生成", "level": 0, "content_type": "text"}
            ]
        }
    ]
    
    try:
        r = httpx.post(f"{BASE_URL}/api/ppt/cocreation", json={
            "original_text": "",
            "slides": slides,
            "instruction": "把第2页的标题改为'产品亮点'"
        }, timeout=120.0)
        
        data = r.json()
        
        print(f"  HTTP状态码: {r.status_code}")
        print(f"  update_type: {data.get('update_type')}")
        print(f"  action: {data.get('action')}")
        print(f"  action_result: {json.dumps(data.get('action_result'), ensure_ascii=False)}")
        
        updated_slides = data.get("updated_slides", [])
        if updated_slides:
            new_title = updated_slides[1].get("title", "") if len(updated_slides) > 1 else ""
            print(f"  修改后第2页标题: '{new_title}'")
            
            # 验证是否为局部修改
            update_type = data.get("update_type")
            action = data.get("action")
            
            if update_type == "partial" and action == "update":
                print_result("局部修改标题", True, "AI 正确使用了局部修改模式")
                return True
            elif update_type == "full":
                print_result("局部修改标题", False, "AI 使用了全量替换模式（期望局部修改）")
                return False
            else:
                print_result("局部修改标题", False, f"未知 update_type: {update_type}")
                return False
        else:
            print_result("局部修改标题", False, f"返回数据为空: {data}")
            return False
    
    except Exception as e:
        print_result("局部修改标题", False, str(e))
        return False


def test_cocreation_add_item():
    """测试：添加要点"""
    print_header("测试：添加要点")
    
    slides = [
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
    ]
    
    try:
        r = httpx.post(f"{BASE_URL}/api/ppt/cocreation", json={
            "original_text": "",
            "slides": slides,
            "instruction": "在第1页添加一个新要点：功能C"
        }, timeout=120.0)
        
        data = r.json()
        
        print(f"  HTTP状态码: {r.status_code}")
        print(f"  update_type: {data.get('update_type')}")
        print(f"  action: {data.get('action')}")
        
        updated_slides = data.get("updated_slides", [])
        if updated_slides:
            items = updated_slides[0].get("items", [])
            print(f"  修改后要点数: {len(items)}")
            for i, item in enumerate(items):
                print(f"    [{i}] {item.get('text', '')}")
            
            update_type = data.get("update_type")
            action = data.get("action")
            
            if update_type == "partial" and action == "add_item":
                print_result("添加要点", True, "AI 正确使用了 add_item 模式")
                return True
            elif update_type == "full":
                print_result("添加要点", False, "AI 使用了全量替换模式（期望 add_item）")
                return False
            else:
                print_result("添加要点", False, f"action={action}, update_type={update_type}")
                return False
        else:
            print_result("添加要点", False, f"返回数据异常: {data}")
            return False
    
    except Exception as e:
        print_result("添加要点", False, str(e))
        return False


def test_cocreation_change_layout():
    """测试：修改版式"""
    print_header("测试：修改版式")
    
    slides = [
        {
            "title": "图文展示",
            "subtitle": "",
            "type": "content",
            "layout": "text_only",
            "items": [
                {"text": "展示内容", "level": 0, "content_type": "text"}
            ]
        }
    ]
    
    try:
        r = httpx.post(f"{BASE_URL}/api/ppt/cocreation", json={
            "original_text": "",
            "slides": slides,
            "instruction": "把第1页改为图文混排（图片在右边）"
        }, timeout=120.0)
        
        data = r.json()
        
        print(f"  HTTP状态码: {r.status_code}")
        print(f"  update_type: {data.get('update_type')}")
        print(f"  action: {data.get('action')}")
        
        updated_slides = data.get("updated_slides", [])
        if updated_slides:
            new_layout = updated_slides[0].get("layout", "")
            print(f"  修改后版式: {new_layout}")
            
            update_type = data.get("update_type")
            action = data.get("action")
            
            if update_type == "partial" and action == "update":
                print_result("修改版式", True, f"AI 正确使用了局部修改，layout={new_layout}")
                return True
            elif update_type == "full":
                print_result("修改版式", False, "AI 使用了全量替换模式（期望局部修改）")
                return False
            else:
                print_result("修改版式", False, f"action={action}, update_type={update_type}")
                return False
        else:
            print_result("修改版式", False, f"返回数据异常: {data}")
            return False
    
    except Exception as e:
        print_result("修改版式", False, str(e))
        return False


def test_cocreation_full_regen():
    """测试：全量重新生成（明确要求时）"""
    print_header("测试：全量重新生成")
    
    slides = [
        {
            "title": "旧标题",
            "subtitle": "旧副标题",
            "type": "title",
            "layout": "center",
            "items": []
        }
    ]
    
    try:
        r = httpx.post(f"{BASE_URL}/api/ppt/cocreation", json={
            "original_text": "",
            "slides": slides,
            "instruction": "请完全重新生成这个PPT，主题是人工智能发展史"
        }, timeout=120.0)
        
        data = r.json()
        
        print(f"  HTTP状态码: {r.status_code}")
        print(f"  update_type: {data.get('update_type')}")
        
        updated_slides = data.get("updated_slides", [])
        print(f"  返回幻灯片数: {len(updated_slides) if updated_slides else 0}")
        
        # 全量重新生成是可以接受的
        if updated_slides and len(updated_slides) > 0:
            print_result("全量重新生成", True, f"返回了 {len(updated_slides)} 页幻灯片")
            return True
        else:
            print_result("全量重新生成", False, "未返回有效幻灯片数据")
            return False
    
    except Exception as e:
        print_result("全量重新生成", False, str(e))
        return False


def test_parse_cocreation_response():
    """测试 _parse_cocreation_response 函数"""
    print_header("测试：响应解析函数")
    
    # 导入模块进行单元测试
    try:
        sys.path.insert(0, ".")
        from smart_copilot_api import _parse_cocreation_response
        
        tests_passed = 0
        tests_total = 0
        
        # 测试1: 局部更新 JSON
        tests_total += 1
        r1 = _parse_cocreation_response('```json\n{"action": "update", "slide_index": 0, "field": "title", "value": "新标题"}\n```')
        if r1.get("action") == "update" and r1.get("slide_index") == 0:
            print_result("解析局部更新 JSON", True)
            tests_passed += 1
        else:
            print_result("解析局部更新 JSON", False, f"结果: {r1}")
        
        # 测试2: 全量更新 JSON
        tests_total += 1
        r2 = _parse_cocreation_response('```json\n{"slides": [{"title": "新PPT"}]}\n```')
        if "slides" in r2 and len(r2["slides"]) == 1:
            print_result("解析全量更新 JSON", True)
            tests_passed += 1
        else:
            print_result("解析全量更新 JSON", False, f"结果: {r2}")
        
        # 测试3: 嵌套 JSON（add_item）
        tests_total += 1
        r3 = _parse_cocreation_response('{"action": "add_item", "slide_index": 0, "item": {"text": "新要点", "level": 0}}')
        if r3.get("action") == "add_item" and r3.get("item", {}).get("text") == "新要点":
            print_result("解析嵌套 JSON (add_item)", True)
            tests_passed += 1
        else:
            print_result("解析嵌套 JSON (add_item)", False, f"结果: {r3}")
        
        # 测试4: 数组格式
        tests_total += 1
        r4 = _parse_cocreation_response('[{"title": "幻灯片1"}]')
        if "slides" in r4 and len(r4["slides"]) == 1:
            print_result("解析数组格式", True)
            tests_passed += 1
        else:
            print_result("解析数组格式", False, f"结果: {r4}")
        
        # 测试5: 空响应
        tests_total += 1
        r5 = _parse_cocreation_response("抱歉，我无法理解你的指令")
        if r5 == {}:
            print_result("空响应处理", True)
            tests_passed += 1
        else:
            print_result("空响应处理", False, f"结果: {r5}")
        
        print(f"\n  解析函数测试: {tests_passed}/{tests_total} 通过")
        return tests_passed == tests_total
    
    except Exception as e:
        print_result("响应解析函数", False, str(e))
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("  PPT 共创 API 接口测试")
    print("  测试第一阶段改进：AI 局部修改功能")
    print("=" * 60)
    
    # 先测试解析函数（不需要 API 服务）
    parse_result = test_parse_cocreation_response()
    
    # 检查 API 服务
    if not test_health():
        print("\n API 服务未运行，跳过接口测试")
        print("  启动方式: python smart_copilot_api.py")
        return parse_result
    
    # 接口测试
    results = [
        ("响应解析函数", parse_result),
        ("修改标题（局部更新）", test_cocreation_update_title()),
        ("添加要点", test_cocreation_add_item()),
        ("修改版式", test_cocreation_change_layout()),
        ("全量重新生成", test_cocreation_full_regen()),
    ]
    
    # 汇总
    print_header("测试汇总")
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n  总计: {total} 项")
    print(f"  通过: {passed}")
    print(f"  失败: {total - passed}")
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"    [{status}] {name}")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
