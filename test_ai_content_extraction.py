#!/usr/bin/env python3
"""
AI内容提取测试：验证从非结构化文本中提取表格/图表数据的能力

测试场景：
1. 人物属性提取 → 表格
2. 产品对比提取 → 柱状图
3. 时间序列提取 → 折线图
4. 百分比分布提取 → 饼图
5. 流程步骤提取 → 流程图
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_extract_person_attributes():
    """测试1：从人物描述中提取表格数据"""
    print("\n=== 测试1：人物属性提取 ===")
    
    # 输入：非结构化文本
    input_text = """
    张三今年25岁，在北京工作，月薪1.5万
    李四今年30岁，在上海工作，月薪2万
    王五今年28岁，在深圳工作，月薪1.8万
    """
    
    # 期望输出：表格JSON
    expected_result = {
        "action": "add_item",
        "slide_index": 0,
        "item": {
            "content_type": "table",
            "table_data": {
                "title": "员工信息",
                "columns": ["姓名", "年龄", "城市", "月薪"],
                "rows": [
                    ["张三", "25", "北京", "1.5万"],
                    ["李四", "30", "上海", "2万"],
                    ["王五", "28", "深圳", "1.8万"]
                ]
            }
        }
    }
    
    print(f"输入文本：{input_text.strip()}")
    print(f"期望输出：{json.dumps(expected_result, ensure_ascii=False, indent=2)}")
    print("✓ 测试用例定义完成")
    return expected_result


def test_extract_product_comparison():
    """测试2：从产品对比中提取柱状图数据"""
    print("\n=== 测试2：产品对比提取 ===")
    
    # 输入：非结构化文本
    input_text = """
    产品A销量100万，产品B销量200万，产品C销量150万，产品D销量180万
    """
    
    # 期望输出：柱状图JSON
    expected_result = {
        "action": "add_item",
        "slide_index": 0,
        "item": {
            "content_type": "chart",
            "chart_type": "bar",
            "chart_data": {
                "title": "产品销量对比",
                "labels": ["产品A", "产品B", "产品C", "产品D"],
                "datasets": [
                    {
                        "label": "销量(万)",
                        "data": [100, 200, 150, 180],
                        "color": "#007bff"
                    }
                ]
            }
        }
    }
    
    print(f"输入文本：{input_text.strip()}")
    print(f"期望输出：{json.dumps(expected_result, ensure_ascii=False, indent=2)}")
    print("✓ 测试用例定义完成")
    return expected_result


def test_extract_time_series():
    """测试3：从时间序列中提取折线图数据"""
    print("\n=== 测试3：时间序列提取 ===")
    
    # 输入：非结构化文本
    input_text = """
    Q1增长10%，Q2增长15%，Q3增长12%，Q4增长18%
    """
    
    # 期望输出：折线图JSON
    expected_result = {
        "action": "add_item",
        "slide_index": 0,
        "item": {
            "content_type": "chart",
            "chart_type": "line",
            "chart_data": {
                "title": "季度增长趋势",
                "labels": ["Q1", "Q2", "Q3", "Q4"],
                "datasets": [
                    {
                        "label": "增长率",
                        "data": [10, 15, 12, 18],
                        "color": "#28a745"
                    }
                ]
            }
        }
    }
    
    print(f"输入文本：{input_text.strip()}")
    print(f"期望输出：{json.dumps(expected_result, ensure_ascii=False, indent=2)}")
    print("✓ 测试用例定义完成")
    return expected_result


def test_extract_percentage_distribution():
    """测试4：从百分比分布中提取饼图数据"""
    print("\n=== 测试4：百分比分布提取 ===")
    
    # 输入：非结构化文本
    input_text = """
    市场份额：产品A占35%，产品B占25%，产品C占20%，其他占20%
    """
    
    # 期望输出：饼图JSON
    expected_result = {
        "action": "add_item",
        "slide_index": 0,
        "item": {
            "content_type": "chart",
            "chart_type": "pie",
            "chart_data": {
                "title": "市场份额分布",
                "labels": ["产品A", "产品B", "产品C", "其他"],
                "datasets": [
                    {
                        "label": "份额",
                        "data": [35, 25, 20, 20],
                        "color": "#007bff"
                    }
                ]
            }
        }
    }
    
    print(f"输入文本：{input_text.strip()}")
    print(f"期望输出：{json.dumps(expected_result, ensure_ascii=False, indent=2)}")
    print("✓ 测试用例定义完成")
    return expected_result


def test_extract_process_steps():
    """测试5：从流程描述中提取流程图数据"""
    print("\n=== 测试5：流程步骤提取 ===")
    
    # 输入：非结构化文本
    input_text = """
    首先需要收集用户需求，然后进行需求分析，接着设计技术方案，
    最后开发实现并测试验收
    """
    
    # 期望输出：流程图JSON
    expected_result = {
        "action": "add_item",
        "slide_index": 0,
        "item": {
            "content_type": "flowchart",
            "flowchart_data": {
                "title": "项目流程",
                "steps": [
                    "收集用户需求",
                    "进行需求分析",
                    "设计技术方案",
                    "开发实现",
                    "测试验收"
                ]
            }
        }
    }
    
    print(f"输入文本：{input_text.strip()}")
    print(f"期望输出：{json.dumps(expected_result, ensure_ascii=False, indent=2)}")
    print("✓ 测试用例定义完成")
    return expected_result


def simulate_ai_extraction(input_text: str, target_type: str) -> dict:
    """
    模拟AI提取过程（实际由LLM完成）
    
    Args:
        input_text: 非结构化文本
        target_type: 目标类型 (table/chart/flowchart)
    
    Returns:
        转换指令JSON
    """
    # 这里模拟AI的提取逻辑
    # 实际实现中，这部分由LLM根据系统提示完成
    
    if target_type == "table":
        # 模拟提取人物属性
        if "张三" in input_text and "李四" in input_text:
            return {
                "action": "add_item",
                "slide_index": 0,
                "item": {
                    "content_type": "table",
                    "table_data": {
                        "title": "员工信息",
                        "columns": ["姓名", "年龄", "城市", "月薪"],
                        "rows": [
                            ["张三", "25", "北京", "1.5万"],
                            ["李四", "30", "上海", "2万"],
                            ["王五", "28", "深圳", "1.8万"]
                        ]
                    }
                }
            }
    
    elif target_type == "chart":
        # 模拟提取产品对比
        if "产品A" in input_text and "产品B" in input_text:
            return {
                "action": "add_item",
                "slide_index": 0,
                "item": {
                    "content_type": "chart",
                    "chart_type": "bar",
                    "chart_data": {
                        "title": "产品销量对比",
                        "labels": ["产品A", "产品B", "产品C", "产品D"],
                        "datasets": [
                            {
                                "label": "销量(万)",
                                "data": [100, 200, 150, 180],
                                "color": "#007bff"
                            }
                        ]
                    }
                }
            }
    
    elif target_type == "flowchart":
        # 模拟提取流程步骤
        if "首先" in input_text and "然后" in input_text:
            return {
                "action": "add_item",
                "slide_index": 0,
                "item": {
                    "content_type": "flowchart",
                    "flowchart_data": {
                        "title": "项目流程",
                        "steps": [
                            "收集用户需求",
                            "进行需求分析",
                            "设计技术方案",
                            "开发实现",
                            "测试验收"
                        ]
                    }
                }
            }
    
    return None


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("AI内容提取测试：非结构化文本 → 表格/图表/流程图")
    print("=" * 60)
    
    # 定义测试用例
    test_cases = [
        {
            "name": "人物属性 → 表格",
            "input": "张三今年25岁，在北京工作，月薪1.5万\n李四今年30岁，在上海工作，月薪2万\n王五今年28岁，在深圳工作，月薪1.8万",
            "target": "table",
            "expected_title": "员工信息"
        },
        {
            "name": "产品对比 → 柱状图",
            "input": "产品A销量100万，产品B销量200万，产品C销量150万，产品D销量180万",
            "target": "chart",
            "expected_title": "产品销量对比"
        },
        {
            "name": "时间序列 → 折线图",
            "input": "Q1增长10%，Q2增长15%，Q3增长12%，Q4增长18%",
            "target": "chart",
            "expected_title": "季度增长趋势"
        },
        {
            "name": "百分比分布 → 饼图",
            "input": "市场份额：产品A占35%，产品B占25%，产品C占20%，其他占20%",
            "target": "chart",
            "expected_title": "市场份额分布"
        },
        {
            "name": "流程描述 → 流程图",
            "input": "首先需要收集用户需求，然后进行需求分析，接着设计技术方案，最后开发实现并测试验收",
            "target": "flowchart",
            "expected_title": "项目流程"
        }
    ]
    
    # 运行测试
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 测试 {i}: {test_case['name']} ---")
        print(f"输入：{test_case['input'][:50]}...")
        
        # 模拟AI提取
        result = simulate_ai_extraction(test_case['input'], test_case['target'])
        
        if result:
            # 验证结果
            actual_type = result['item']['content_type']
            if actual_type == 'table':
                actual_title = result['item']['table_data']['title']
            elif actual_type == 'chart':
                actual_title = result['item']['chart_data']['title']
            elif actual_type == 'flowchart':
                actual_title = result['item']['flowchart_data']['title']
            else:
                actual_title = "未知"
            
            if actual_title == test_case['expected_title']:
                print(f"✓ 测试通过：{actual_type} - {actual_title}")
                passed += 1
            else:
                print(f"✗ 测试失败：期望 '{test_case['expected_title']}', 实际 '{actual_title}'")
                failed += 1
        else:
            print(f"✗ 测试失败：未能提取数据")
            failed += 1
    
    # 总结
    print("\n" + "=" * 60)
    print(f"测试结果：{passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    
    # 打印示例提示词
    print("\n" + "=" * 60)
    print("示例：用户对AI说的话")
    print("=" * 60)
    print("""
用户：把这页PPT的内容做成表格
AI（应该这样响应）：
```json
{"action": "add_item", "slide_index": 0, "item": {"content_type": "table", "table_data": {"title": "员工信息", "columns": ["姓名", "年龄", "城市", "月薪"], "rows": [["张三", "25", "北京", "1.5万"], ["李四", "30", "上海", "2万"], ["王五", "28", "深圳", "1.8万"]]}}}
```

用户：用柱状图展示这些数据
AI（应该这样响应）：
```json
{"action": "add_item", "slide_index": 0, "item": {"content_type": "chart", "chart_type": "bar", "chart_data": {"title": "产品销量对比", "labels": ["产品A", "产品B", "产品C", "产品D"], "datasets": [{"label": "销量(万)", "data": [100, 200, 150, 180], "color": "#007bff"}]}}}
```
""")
    
    sys.exit(0 if success else 1)