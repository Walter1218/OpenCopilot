#!/usr/bin/env python3
"""
第二阶段功能测试：文本智能识别、图表/表格渲染、内容转换API

测试内容：
1. 文本分析器（TextAnalyzer）
2. 内容转换器（ContentConverter）
3. 数据结构定义
4. 预览面板渲染（通过API测试）
5. 内容转换API
"""

import os
import sys
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_text_analyzer():
    """测试文本分析器"""
    print("\n=== 测试文本分析器 ===")
    
    from ppt_cocreation.content_converter import TextAnalyzer
    
    # 测试1: 数字对比检测
    print("测试1: 数字对比检测")
    text1 = "产品A：Q1 100万，Q2 120万，Q3 150万，Q4 180万"
    result1 = TextAnalyzer.analyze(text1)
    assert result1["best_match"] is not None, "应检测到数字对比"
    assert result1["best_match"]["type"] == "chart", f"应检测为图表，实际: {result1['best_match']['type']}"
    print(f"  ✓ 检测结果: {result1['best_match']['type']}/{result1['best_match'].get('subtype', 'N/A')}")
    
    # 测试2: Markdown表格检测
    print("测试2: Markdown表格检测")
    text2 = """| 项目 | Q1 | Q2 | Q3 |
|------|----|----|----|
| 产品A | 100 | 120 | 150 |
| 产品B | 80 | 90 | 110 |"""
    result2 = TextAnalyzer.analyze(text2)
    assert result2["best_match"] is not None, "应检测到表格"
    assert result2["best_match"]["type"] == "table", f"应检测为表格，实际: {result2['best_match']['type']}"
    print(f"  ✓ 检测结果: {result2['best_match']['type']}/{result2['best_match'].get('subtype', 'N/A')}")
    
    # 测试3: 流程步骤检测
    print("测试3: 流程步骤检测")
    text3 = """首先，收集用户需求
然后，进行需求分析
接着，设计方案
最后，交付验收"""
    result3 = TextAnalyzer.analyze(text3)
    assert result3["best_match"] is not None, "应检测到流程步骤"
    assert result3["best_match"]["type"] == "flowchart", f"应检测为流程图，实际: {result3['best_match']['type']}"
    print(f"  ✓ 检测结果: {result3['best_match']['type']}/{result3['best_match'].get('subtype', 'N/A')}")
    
    # 测试4: 百分比分布检测
    print("测试4: 百分比分布检测")
    text4 = "市场份额：产品A 35%，产品B 25%，产品C 20%，其他 20%"
    result4 = TextAnalyzer.analyze(text4)
    assert result4["best_match"] is not None, "应检测到百分比分布"
    print(f"  ✓ 检测结果: {result4['best_match']['type']}/{result4['best_match'].get('subtype', 'N/A')}")
    
    # 测试5: 空文本处理
    print("测试5: 空文本处理")
    result5 = TextAnalyzer.analyze("")
    assert result5["best_match"] is None, "空文本应返回 None"
    print("  ✓ 空文本处理正确")
    
    print("✓ 文本分析器测试通过！\n")


def test_table_extraction():
    """测试表格数据提取"""
    print("=== 测试表格数据提取 ===")
    
    from ppt_cocreation.content_converter import TextAnalyzer
    
    # 测试 Markdown 表格提取
    print("测试: Markdown表格数据提取")
    text = """| 产品 | Q1 | Q2 | Q3 | Q4 |
|------|----|----|----|----|
| 产品A | 100 | 120 | 150 | 180 |
| 产品B | 80 | 90 | 110 | 130 |"""
    
    analysis = TextAnalyzer.analyze(text)
    extracted = analysis.get("extracted_data")
    
    assert extracted is not None, "应提取到数据"
    assert "columns" in extracted, "应包含列名"
    assert "rows" in extracted, "应包含行数据"
    assert len(extracted["columns"]) == 5, f"应有5列，实际: {len(extracted['columns'])}"
    assert len(extracted["rows"]) == 2, f"应有2行数据，实际: {len(extracted['rows'])}"
    print(f"  ✓ 提取到 {len(extracted['columns'])} 列, {len(extracted['rows'])} 行")
    print(f"    列名: {extracted['columns']}")
    print(f"    数据: {extracted['rows']}")
    
    print("✓ 表格数据提取测试通过！\n")


def test_chart_extraction():
    """测试图表数据提取"""
    print("=== 测试图表数据提取 ===")
    
    from ppt_cocreation.content_converter import TextAnalyzer
    
    # 测试数字对比提取
    print("测试: 数字对比数据提取")
    text = "销售额：一月 100万，二月 120万，三月 150万，四月 180万"
    
    analysis = TextAnalyzer.analyze(text)
    extracted = analysis.get("extracted_data")
    
    assert extracted is not None, "应提取到数据"
    assert "labels" in extracted, "应包含标签"
    assert "datasets" in extracted, "应包含数据集"
    assert len(extracted["labels"]) >= 3, f"应有至少3个标签，实际: {len(extracted['labels'])}"
    print(f"  ✓ 提取到 {len(extracted['labels'])} 个数据点")
    print(f"    标签: {extracted['labels']}")
    print(f"    数据: {extracted['datasets'][0]['data']}")
    
    print("✓ 图表数据提取测试通过！\n")


def test_content_converter():
    """测试内容转换器"""
    print("=== 测试内容转换器 ===")
    
    from ppt_cocreation.content_converter import ContentConverter
    
    # 测试1: 转换为表格
    print("测试1: 转换为表格")
    text1 = "| 姓名 | 年龄 | 城市 |\n|------|------|------|\n| 张三 | 25 | 北京 |\n| 李四 | 30 | 上海 |"
    table = ContentConverter.convert_to_table(text1, "员工信息")
    assert table["content_type"] == "table", "类型应为 table"
    assert "table_data" in table, "应包含 table_data"
    assert table["table_data"]["title"] == "员工信息", "标题应为 '员工信息'"
    print(f"  ✓ 转换成功: {table['table_data']['title']}, {len(table['table_data']['columns'])} 列")
    
    # 测试2: 转换为柱状图
    print("测试2: 转换为柱状图")
    text2 = "产品A：100，产品B：200，产品C：150"
    chart = ContentConverter.convert_to_chart(text2, "bar", "产品对比")
    assert chart["content_type"] == "chart", "类型应为 chart"
    assert chart["chart_type"] == "bar", "图表类型应为 bar"
    assert "chart_data" in chart, "应包含 chart_data"
    print(f"  ✓ 转换成功: {chart['chart_data']['title']}, {len(chart['chart_data']['labels'])} 个数据点")
    
    # 测试3: 转换为流程图
    print("测试3: 转换为流程图")
    text3 = "1. 需求分析\n2. 方案设计\n3. 开发实现\n4. 测试验收"
    flow = ContentConverter.convert_to_flowchart(text3, "开发流程")
    assert flow["content_type"] == "flowchart", "类型应为 flowchart"
    assert "flowchart_data" in flow, "应包含 flowchart_data"
    print(f"  ✓ 转换成功: {flow['flowchart_data']['title']}, {len(flow['flowchart_data']['steps'])} 个步骤")
    
    print("✓ 内容转换器测试通过！\n")


def test_data_structures():
    """测试数据结构定义"""
    print("=== 测试数据结构定义 ===")
    
    from ppt_cocreation.content_converter import (
        create_table_data, create_chart_data, create_flowchart_data
    )
    
    # 测试表格数据结构
    print("测试1: 表格数据结构")
    table = create_table_data("测试表格", ["列1", "列2"], [["a", "b"]])
    assert table["content_type"] == "table"
    assert table["table_data"]["columns"] == ["列1", "列2"]
    print("  ✓ 表格结构正确")
    
    # 测试图表数据结构
    print("测试2: 图表数据结构")
    chart = create_chart_data("测试图表", "bar", ["A", "B"], [{"label": "系列1", "data": [1, 2]}])
    assert chart["content_type"] == "chart"
    assert chart["chart_type"] == "bar"
    print("  ✓ 图表结构正确")
    
    # 测试流程图数据结构
    print("测试3: 流程图数据结构")
    flow = create_flowchart_data("测试流程", ["步骤1", "步骤2"])
    assert flow["content_type"] == "flowchart"
    assert len(flow["flowchart_data"]["steps"]) == 2
    print("  ✓ 流程图结构正确")
    
    print("✓ 数据结构定义测试通过！\n")


def test_conversion_suggestions():
    """测试转换建议"""
    print("=== 测试转换建议 ===")
    
    from ppt_cocreation.content_converter import get_conversion_suggestions
    
    text = "销售额：Q1 100万，Q2 120万，Q3 150万"
    result = get_conversion_suggestions(text)
    
    assert "suggestions" in result, "应包含 suggestions"
    assert len(result["suggestions"]) > 0, "应有转换建议"
    
    # 检查是否有推荐的转换方式
    recommended = [s for s in result["suggestions"] if s.get("recommended")]
    assert len(recommended) > 0, "应有推荐的转换方式"
    
    print(f"  ✓ 获取到 {len(result['suggestions'])} 个转换建议")
    print(f"    推荐: {recommended[0]['label']}")
    
    print("✓ 转换建议测试通过！\n")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("第二阶段功能测试：文本智能识别、图表/表格、内容转换")
    print("=" * 60)
    
    try:
        test_text_analyzer()
        test_table_extraction()
        test_chart_extraction()
        test_content_converter()
        test_data_structures()
        test_conversion_suggestions()
        
        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n✗ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
