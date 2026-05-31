#!/usr/bin/env python3
"""
建议引擎单元测试
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppt_cocreation.suggestion_engine import (
    SuggestionEngine,
    Suggestion,
    SuggestionResult,
    generate_suggestions
)
from ppt_cocreation.context_analyzer import SuggestionType


def test_generate_content_suggestions():
    """测试内容建议生成"""
    print("测试内容建议生成...")
    
    engine = SuggestionEngine()
    
    # 测试数据对比内容
    context = {
        "slides": [
            {
                "index": 0,
                "title": "产品销量",
                "content": "产品A销量100万，产品B销量200万，产品C销量150万"
            }
        ],
        "current_slide": 0
    }
    
    result = engine.generate_suggestions(context)
    
    assert len(result.suggestions) > 0, "应该生成建议"
    assert any(
        s.type == SuggestionType.VISUAL_ENHANCE 
        for s in result.suggestions
    ), "应该有视觉增强建议"
    
    print("✅ 数据对比建议通过")
    
    # 测试人物属性内容
    context = {
        "slides": [
            {
                "index": 0,
                "title": "员工信息",
                "content": "张三今年25岁，在北京工作，月薪1.5万\n李四今年30岁，在上海工作，月薪2万"
            }
        ],
        "current_slide": 0
    }
    
    result = engine.generate_suggestions(context)
    
    assert len(result.suggestions) > 0, "应该生成建议"
    
    print("✅ 人物属性建议通过")


def test_generate_structure_suggestions():
    """测试结构建议生成"""
    print("测试结构建议生成...")
    
    engine = SuggestionEngine()
    
    # 测试不完整结构
    context = {
        "slides": [
            {"index": 0, "title": "内容1", "content": "..."},
            {"index": 1, "title": "内容2", "content": "..."}
        ],
        "current_slide": 0
    }
    
    result = engine.generate_suggestions(context)
    
    # 应该有结构完整性建议
    structure_suggestions = [
        s for s in result.suggestions 
        if s.type == SuggestionType.STRUCTURE_IMPROVE
    ]
    
    assert len(structure_suggestions) > 0, "应该有结构改进建议"
    
    print("✅ 结构建议通过")


def test_generate_style_suggestions():
    """测试风格建议生成"""
    print("测试风格建议生成...")
    
    engine = SuggestionEngine()
    
    # 测试不一致风格
    context = {
        "slides": [
            {"index": 0, "style": {"primary_color": "#4da6ff", "font": "微软雅黑"}},
            {"index": 1, "style": {"primary_color": "#ff6b6b", "font": "宋体"}},
            {"index": 2, "style": {"primary_color": "#4da6ff", "font": "微软雅黑"}}
        ],
        "current_slide": 0
    }
    
    result = engine.generate_suggestions(context)
    
    # 应该有风格一致性建议
    style_suggestions = [
        s for s in result.suggestions 
        if s.type == SuggestionType.STYLE_CONSISTENT
    ]
    
    assert len(style_suggestions) > 0, "应该有风格一致性建议"
    
    print("✅ 风格建议通过")


def test_generate_focus_suggestions():
    """测试关注点建议生成"""
    print("测试关注点建议生成...")
    
    engine = SuggestionEngine()
    
    # 测试视觉增强关注点
    context = {
        "slides": [
            {
                "index": 0,
                "title": "数据",
                "content": "产品A销量100万，产品B销量200万"
            }
        ],
        "current_slide": 0
    }
    
    result = engine.generate_suggestions(context, focus="visual_enhance")
    
    assert len(result.suggestions) > 0, "应该生成建议"
    
    print("✅ 关注点建议通过")


def test_suggestion_result_structure():
    """测试建议结果结构"""
    print("测试建议结果结构...")
    
    engine = SuggestionEngine()
    
    context = {
        "slides": [
            {
                "index": 0,
                "title": "测试",
                "content": "测试内容"
            }
        ],
        "current_slide": 0
    }
    
    result = engine.generate_suggestions(context)
    
    # 检查结果结构
    assert isinstance(result, SuggestionResult), "结果应该是 SuggestionResult 类型"
    assert isinstance(result.suggestions, list), "建议应该是列表"
    assert isinstance(result.analysis, dict), "分析应该是字典"
    assert isinstance(result.context_summary, dict), "上下文摘要应该是字典"
    
    # 检查分析内容
    assert "total_slides" in result.analysis, "分析应该包含 total_slides"
    assert "current_slide_analyzed" in result.analysis, "分析应该包含 current_slide_analyzed"
    
    # 检查上下文摘要
    assert "total_slides" in result.context_summary, "上下文摘要应该包含 total_slides"
    assert "current_slide" in result.context_summary, "上下文摘要应该包含 current_slide"
    
    print("✅ 结果结构通过")


def test_suggestion_to_dict():
    """测试建议转字典"""
    print("测试建议转字典...")
    
    suggestion = Suggestion(
        id="test_id",
        type=SuggestionType.VISUAL_ENHANCE,
        title="测试建议",
        description="测试描述",
        confidence=0.9,
        action={"type": "test"},
        preview={"test": True},
        priority=1
    )
    
    result = suggestion.to_dict()
    
    assert result["id"] == "test_id", "ID 应该正确"
    assert result["type"] == "visual_enhance", "类型应该正确"
    assert result["title"] == "测试建议", "标题应该正确"
    assert result["description"] == "测试描述", "描述应该正确"
    assert result["confidence"] == 0.9, "置信度应该正确"
    assert result["action"] == {"type": "test"}, "动作应该正确"
    assert result["preview"] == {"test": True}, "预览应该正确"
    assert result["priority"] == 1, "优先级应该正确"
    
    print("✅ 建议转字典通过")


def test_suggestion_result_to_dict():
    """测试建议结果转字典"""
    print("测试建议结果转字典...")
    
    engine = SuggestionEngine()
    
    context = {
        "slides": [
            {
                "index": 0,
                "title": "测试",
                "content": "测试内容"
            }
        ],
        "current_slide": 0
    }
    
    result = engine.generate_suggestions(context)
    result_dict = result.to_dict()
    
    assert isinstance(result_dict, dict), "结果应该是字典"
    assert "suggestions" in result_dict, "应该包含 suggestions"
    assert "analysis" in result_dict, "应该包含 analysis"
    assert "context_summary" in result_dict, "应该包含 context_summary"
    
    print("✅ 结果转字典通过")


def test_max_suggestions():
    """测试最大建议数限制"""
    print("测试最大建议数限制...")
    
    engine = SuggestionEngine()
    
    # 创建一个会生成很多建议的上下文
    context = {
        "slides": [
            {
                "index": 0,
                "title": "封面",
                "content": "产品介绍"
            },
            {
                "index": 1,
                "title": "问题",
                "content": "用户痛点"
            },
            {
                "index": 2,
                "title": "解决方案",
                "content": "我们的方案"
            },
            {
                "index": 3,
                "title": "产品特点",
                "content": "核心功能"
            },
            {
                "index": 4,
                "title": "总结",
                "content": "感谢观看"
            }
        ],
        "current_slide": 0
    }
    
    # 测试限制为 3 个建议
    result = engine.generate_suggestions(context, max_suggestions=3)
    
    assert len(result.suggestions) <= 3, f"建议数应该不超过 3，实际 {len(result.suggestions)}"
    
    print("✅ 最大建议数限制通过")


def test_convenience_function():
    """测试便捷函数"""
    print("测试便捷函数...")
    
    context = {
        "slides": [
            {
                "index": 0,
                "title": "测试",
                "content": "产品A销量100万，产品B销量200万"
            }
        ],
        "current_slide": 0
    }
    
    result = generate_suggestions(context)
    
    assert isinstance(result, SuggestionResult), "结果应该是 SuggestionResult 类型"
    assert len(result.suggestions) > 0, "应该生成建议"
    
    print("✅ 便捷函数通过")


def test_empty_slides():
    """测试空幻灯片"""
    print("测试空幻灯片...")
    
    engine = SuggestionEngine()
    
    context = {
        "slides": [],
        "current_slide": 0
    }
    
    result = engine.generate_suggestions(context)
    
    assert isinstance(result, SuggestionResult), "结果应该是 SuggestionResult 类型"
    assert result.context_summary["total_slides"] == 0, "总幻灯片数应该是 0"
    
    print("✅ 空幻灯片通过")


def main():
    """主测试函数"""
    print("=" * 60)
    print("建议引擎单元测试")
    print("=" * 60)
    
    tests = [
        test_generate_content_suggestions,
        test_generate_structure_suggestions,
        test_generate_style_suggestions,
        test_generate_focus_suggestions,
        test_suggestion_result_structure,
        test_suggestion_to_dict,
        test_suggestion_result_to_dict,
        test_max_suggestions,
        test_convenience_function,
        test_empty_slides,
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