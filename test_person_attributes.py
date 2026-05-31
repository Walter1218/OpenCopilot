#!/usr/bin/env python3
"""
人物属性内容检测测试脚本

测试更多真实场景下的人物属性识别能力。
"""

import sys
import os
import json
import requests

sys.path.insert(0, os.path.dirname(__file__))

API_BASE = "http://127.0.0.1:8088"

def test_person_detection(content, expected_type="person_attributes"):
    """测试内容类型检测"""
    try:
        resp = requests.post(
            f"{API_BASE}/api/ppt/analyze",
            json={"content": content},
            timeout=5
        )
        if resp.status_code == 200:
            result = resp.json()
            detected_type = result.get("content_type", "unknown")
            status = "✅" if detected_type == expected_type else "❌"
            return {
                "status": status,
                "detected": detected_type,
                "expected": expected_type,
                "content": content[:50] + "..." if len(content) > 50 else content
            }
        else:
            return {"status": "❌", "error": f"HTTP {resp.status_code}", "content": content[:50]}
    except Exception as e:
        return {"status": "❌", "error": str(e), "content": content[:50]}


def main():
    """运行测试"""
    print("=" * 60)
    print("人物属性内容检测测试")
    print("=" * 60)
    
    # 测试用例：应该被识别为 person_attributes 的内容
    person_cases = [
        # 标准格式
        "姓名：张三，年龄：30岁，职位：工程师",
        "姓名：李四\n年龄：25\n职位：产品经理",
        
        # 自然语言格式
        "张三，男，30岁，工程师",
        "李女士，45岁，企业家",
        "王经理，35岁，销售总监",
        
        # 描述性格式
        "我们的团队leader是张三，他今年30岁",
        "客户王女士今年45岁，是一位企业家",
        "项目经理李四今年35岁，擅长Python开发",
        
        # 多人格式
        "团队成员：张三（工程师，30岁）、李四（设计师，28岁）",
        "候选人：王五，男，28岁，5年经验；赵六，女，25岁，3年经验",
        
        # 简化格式
        "张三 30岁 工程师",
        "李四，产品经理，28岁",
    ]
    
    # 测试用例：不应该被识别为 person_attributes 的内容
    non_person_cases = [
        "2024年Q1销售额100万，Q2销售额120万",
        "第一步：需求分析\n第二步：设计\n第三步：开发",
        "人工智能（AI）是计算机科学的一个分支",
        "10年工作经验，精通Python、Java、Go",
        "公司成立于2020年，员工500人",
    ]
    
    print("\n【正向测试】应该识别为 person_attributes")
    print("-" * 60)
    
    pass_count = 0
    fail_count = 0
    
    for i, content in enumerate(person_cases, 1):
        result = test_person_detection(content, "person_attributes")
        print(f"{result['status']} {i:2d}. {result['content']}")
        if result['status'] == "✅":
            pass_count += 1
        else:
            fail_count += 1
            print(f"     期望: person_attributes, 实际: {result.get('detected', result.get('error', 'N/A'))}")
    
    print(f"\n【反向测试】不应该识别为 person_attributes")
    print("-" * 60)
    
    for i, content in enumerate(non_person_cases, 1):
        result = test_person_detection(content, "text")  # 期望是 text 或其他类型
        # 只要不是 person_attributes 就算通过
        is_pass = result.get('detected') != 'person_attributes'
        status = "✅" if is_pass else "❌"
        print(f"{status} {i:2d}. {result['content']}")
        if is_pass:
            pass_count += 1
        else:
            fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"测试汇总: {pass_count}/{pass_count + fail_count} 通过, {fail_count} 失败")
    print(f"通过率: {pass_count/(pass_count + fail_count)*100:.1f}%")
    print("=" * 60)
    
    return fail_count == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
