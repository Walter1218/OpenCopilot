#!/usr/bin/env python3
"""
上下文分析器单元测试
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppt_cocreation.context_analyzer import (
    ContextAnalyzer,
    ContentType,
    SuggestionType,
    analyze_content,
    check_style_consistency,
    analyze_structure
)


def test_analyze_content_text():
    """测试文本内容分析"""
    print("测试文本内容分析...")
    
    analyzer = ContextAnalyzer()
    
    # 测试普通文本
    content = "这是一段普通的文本内容，用于测试分析器的基本功能。"
    result = analyzer.analyze_content(content)
    
    assert result.content_type == ContentType.TEXT, f"期望 TEXT，实际 {result.content_type}"
    assert result.confidence > 0, "置信度应该大于 0"
    print("✅ 普通文本分析通过")


def test_analyze_content_data_comparison():
    """测试数据对比内容分析"""
    print("测试数据对比内容分析...")
    
    analyzer = ContextAnalyzer()
    
    # 测试数据对比
    content = "产品A销量100万，产品B销量200万，产品C销量150万"
    result = analyzer.analyze_content(content)
    
    assert result.content_type == ContentType.DATA_COMPARISON, f"期望 DATA_COMPARISON，实际 {result.content_type}"
    assert result.confidence > 0.5, "置信度应该大于 0.5"
    assert result.recommended_visual == ContentType.CHART, "应该推荐图表"
    print("✅ 数据对比分析通过")


def test_analyze_content_time_series():
    """测试时间序列内容分析"""
    print("测试时间序列内容分析...")
    
    analyzer = ContextAnalyzer()
    
    # 测试时间序列
    content = "Q1增长10%，Q2增长15%，Q3增长20%，Q4增长25%"
    result = analyzer.analyze_content(content)
    
    assert result.content_type == ContentType.TIME_SERIES, f"期望 TIME_SERIES，实际 {result.content_type}"
    assert result.recommended_visual == ContentType.CHART, "应该推荐图表"
    print("✅ 时间序列分析通过")


def test_analyze_content_process():
    """测试流程内容分析"""
    print("测试流程内容分析...")
    
    analyzer = ContextAnalyzer()
    
    # 测试流程
    content = "第一步：需求分析\n第二步：设计\n第三步：开发\n第四步：测试"
    result = analyzer.analyze_content(content)
    
    assert result.content_type == ContentType.PROCESS, f"期望 PROCESS，实际 {result.content_type}"
    assert result.recommended_visual == ContentType.FLOWCHART, "应该推荐流程图"
    print("✅ 流程分析通过")


def test_analyze_content_person_attributes():
    """测试人物属性内容分析"""
    print("测试人物属性内容分析...")
    
    analyzer = ContextAnalyzer()
    
    # 测试人物属性
    content = "张三今年25岁，在北京工作，月薪1.5万\n李四今年30岁，在上海工作，月薪2万"
    result = analyzer.analyze_content(content)
    
    assert result.content_type == ContentType.PERSON_ATTRIBUTES, f"期望 PERSON_ATTRIBUTES，实际 {result.content_type}"
    assert result.recommended_visual == ContentType.TABLE, "应该推荐表格"
    assert len(result.entities) > 0, "应该提取到实体"
    print("✅ 人物属性分析通过")


def test_analyze_content_list():
    """测试列表内容分析"""
    print("测试列表内容分析...")
    
    analyzer = ContextAnalyzer()
    
    # 测试列表
    content = "优点：\n- 便宜\n- 快速\n- 可靠\n- 易用"
    result = analyzer.analyze_content(content)
    
    assert result.content_type == ContentType.LIST, f"期望 LIST，实际 {result.content_type}"
    assert len(result.key_points) >= 3, "应该提取到至少3个关键点"
    print("✅ 列表分析通过")


def test_analyze_content_empty():
    """测试空内容分析"""
    print("测试空内容分析...")
    
    analyzer = ContextAnalyzer()
    
    # 测试空内容
    result = analyzer.analyze_content("")
    
    assert result.content_type == ContentType.TEXT, "空内容应该是 TEXT"
    assert result.confidence == 0.0, "空内容置信度应该是 0"
    print("✅ 空内容分析通过")


def test_check_style_consistency():
    """测试风格一致性检查"""
    print("测试风格一致性检查...")
    
    analyzer = ContextAnalyzer()
    
    # 测试一致的风格
    slides_consistent = [
        {"index": 0, "style": {"primary_color": "#4da6ff", "font": "微软雅黑"}},
        {"index": 1, "style": {"primary_color": "#4da6ff", "font": "微软雅黑"}},
        {"index": 2, "style": {"primary_color": "#4da6ff", "font": "微软雅黑"}},
    ]
    
    result = analyzer.check_style_consistency(slides_consistent)
    assert result.consistent == True, "一致的风格应该通过检查"
    assert result.consistency_score == 1.0, "一致性分数应该是 1.0"
    print("✅ 一致风格检查通过")
    
    # 测试不一致的风格
    slides_inconsistent = [
        {"index": 0, "style": {"primary_color": "#4da6ff", "font": "微软雅黑"}},
        {"index": 1, "style": {"primary_color": "#ff6b6b", "font": "宋体"}},
        {"index": 2, "style": {"primary_color": "#4da6ff", "font": "微软雅黑"}},
    ]
    
    result = analyzer.check_style_consistency(slides_inconsistent)
    assert result.consistent == False, "不一致的风格应该检测出来"
    assert len(result.issues) > 0, "应该发现问题"
    assert result.consistency_score < 1.0, "一致性分数应该小于 1.0"
    print("✅ 不一致风格检查通过")


def test_analyze_structure():
    """测试结构分析"""
    print("测试结构分析...")
    
    analyzer = ContextAnalyzer()
    
    # 测试完整结构
    slides_complete = [
        {"index": 0, "title": "封面", "content": "产品介绍"},
        {"index": 1, "title": "问题", "content": "用户痛点"},
        {"index": 2, "title": "解决方案", "content": "我们的方案"},
        {"index": 3, "title": "产品特点", "content": "核心功能"},
        {"index": 4, "title": "总结", "content": "感谢观看"},
    ]
    
    result = analyzer.analyze_structure(slides_complete)
    assert result.total_slides == 5, "应该有5页幻灯片"
    assert "cover" in result.slide_types, "应该包含封面"
    assert "summary" in result.slide_types, "应该包含总结"
    assert result.structure_score > 0.5, "结构分数应该大于 0.5"
    print("✅ 完整结构分析通过")
    
    # 测试不完整结构
    slides_incomplete = [
        {"index": 0, "title": "内容1", "content": "..."},
        {"index": 1, "title": "内容2", "content": "..."},
    ]
    
    result = analyzer.analyze_structure(slides_incomplete)
    assert len(result.missing_sections) > 0, "应该检测到缺失章节"
    print("✅ 不完整结构分析通过")


def test_convenience_functions():
    """测试便捷函数"""
    print("测试便捷函数...")
    
    # 测试 analyze_content
    content = "产品A销量100万，产品B销量200万"
    result = analyze_content(content)
    assert result.content_type == ContentType.DATA_COMPARISON
    print("✅ analyze_content 便捷函数通过")
    
    # 测试 check_style_consistency
    slides = [
        {"style": {"primary_color": "#4da6ff"}},
        {"style": {"primary_color": "#4da6ff"}},
    ]
    result = check_style_consistency(slides)
    assert result.consistent == True
    print("✅ check_style_consistency 便捷函数通过")
    
    # 测试 analyze_structure
    slides = [
        {"index": 0, "title": "封面", "content": "..."},
        {"index": 1, "title": "总结", "content": "..."},
    ]
    result = analyze_structure(slides)
    assert result.total_slides == 2
    print("✅ analyze_structure 便捷函数通过")


def test_quality_score():
    """测试质量分数计算"""
    print("测试质量分数计算...")
    
    analyzer = ContextAnalyzer()
    
    # 测试高质量内容
    high_quality = """
    核心优势：
    - 性能提升30%
    - 成本降低20%
    - 用户满意度95%
    - 支持1000+并发
    - 部署时间缩短50%
    """
    
    result = analyzer.analyze_content(high_quality)
    assert result.quality_score > 0.6, f"高质量内容分数应该大于 0.6，实际 {result.quality_score}"
    print("✅ 高质量内容分数通过")
    
    # 测试低质量内容
    low_quality = "内容"
    
    result = analyzer.analyze_content(low_quality)
    assert result.quality_score < 0.6, f"低质量内容分数应该小于 0.6，实际 {result.quality_score}"
    print("✅ 低质量内容分数通过")


def test_suggestions():
    """测试建议生成"""
    print("测试建议生成...")
    
    analyzer = ContextAnalyzer()
    
    # 测试数据对比建议
    content = "产品A销量100万，产品B销量200万"
    result = analyzer.analyze_content(content)
    
    assert len(result.suggestions) > 0, "应该生成建议"
    assert any(s["type"] == SuggestionType.VISUAL_ENHANCE for s in result.suggestions), "应该有视觉增强建议"
    print("✅ 数据对比建议通过")
    
    # 测试内容过多建议
    content_many_points = """
    优点：
    - 优点1
    - 优点2
    - 优点3
    - 优点4
    - 优点5
    - 优点6
    - 优点7
    - 优点8
    """
    
    result = analyzer.analyze_content(content_many_points)
    has_simplify = any(s["type"] == SuggestionType.STRUCTURE_IMPROVE for s in result.suggestions)
    assert has_simplify, "内容过多时应该有精简建议"
    print("✅ 内容过多建议通过")


def main():
    """主测试函数"""
    print("=" * 60)
    print("上下文分析器单元测试")
    print("=" * 60)
    
    tests = [
        test_analyze_content_text,
        test_analyze_content_data_comparison,
        test_analyze_content_time_series,
        test_analyze_content_process,
        test_analyze_content_person_attributes,
        test_analyze_content_list,
        test_analyze_content_empty,
        test_check_style_consistency,
        test_analyze_structure,
        test_convenience_functions,
        test_quality_score,
        test_suggestions,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_func.__name__} 失败: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} 错误: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print(f"{'='*60}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())