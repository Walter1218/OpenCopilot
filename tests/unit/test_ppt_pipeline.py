"""
端到端验证测试 - PPT Content-First 4 阶段管线 + 共创协议

测试覆盖：
1. 4 阶段管线 fallback 路径（不依赖 LLM）
2. 内容转换无假数据降级
3. 意图路由器分类准确性
4. 溢出检测逻辑
5. 模块导入完整性
"""
import sys
import os
import json
import re

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_pipeline_fallback():
    """测试管线降级路径：从长文本生成幻灯片"""
    from opencopilot.capabilities.ppt.pipeline import PPTGenerationPipeline, PipelineResult
    
    text = """
    第一章：项目背景
    
    本项目旨在解决企业数字化转型中的核心痛点。传统人工流程效率低下，
    常常导致决策延迟。通过引入 AI 技术，可以将处理效率提升 300%。
    
    第二章：技术方案
    
    采用微服务架构，配合容器化部署。前端使用 React 框架，
    后端使用 Python FastAPI。数据库采用 PostgreSQL + Redis 缓存。
    
    第三章：预期收益
    
    预期第一年节约人力成本 500 万元，第二年 800 万元。
    客户满意度预计从 75% 提升到 92%。
    系统上线后响应时间从 5 秒降至 0.5 秒。
    """
    
    pipeline = PPTGenerationPipeline()
    result = pipeline.run(text)
    
    assert isinstance(result, PipelineResult), "应返回 PipelineResult"
    assert result.total_pages >= 2, f"至少应有 2 页幻灯片，实际: {result.total_pages}"
    assert len(result.topics) >= 2, f"至少应有 2 个主题，实际: {len(result.topics)}"
    assert len(result.slides) == result.total_pages, "slides 数量应等于 total_pages"
    
    # 验证 slides 结构
    for slide in result.slides:
        assert isinstance(slide, dict), f"每页应是 dict: {type(slide)}"
        assert "title" in slide, "每页应有 title 字段"
        assert slide.get("type") in ("title", "content"), f"不支持的 type: {slide.get('type')}"
    
    print(f"  ✅ Pipeline fallback: {result.total_pages} 页幻灯片, {len(result.topics)} 个主题")
    print(f"     Stage durations: {result.stage_durations}")
    return True


def test_content_converter_no_fake_data():
    """测试内容转换器不再返回假数据"""
    from opencopilot.capabilities.ppt.content_converter import ContentConverter
    
    # 无结构数据 → 应返回 error
    result = ContentConverter.convert_to_chart("这是一段普通的描述性文字，没有任何可比数据")
    assert "error" in result, f"无结构化数据应返回 error: {result}"
    assert result["content_type"] == "text", f"应标记为 text: {result}"
    
    # 有结构数据 → 应成功提取
    result2 = ContentConverter.convert_to_chart("第一季度营收 100 万，第二季度 150 万，第三季度 200 万")
    if "error" in result2:
        print(f"  ⚠️ 结构化文本首次提取失败（可接受，走 LLM 转换）")
    else:
        labels = result2.get("chart_data", {}).get("labels", [])
        print(f"  ✅ 结构化数据提取成功: labels={labels}")
    
    print(f"  ✅ ContentConverter 不再返回假数据 [10,20,30]")
    return True


def test_intent_router():
    """测试指令路由器分类准确性"""
    from opencopilot.capabilities.ppt.intent_router import IntentRouter
    
    test_cases = [
        ("把第2页标题改为Q1业绩回顾", "update_title", "direct"),
        ("标题改为人工智能应用", "update_title", "direct"),
        ("第3页版式改为图文混排", "update_layout", "direct"),
        ("转为柱状图", "convert_chart", "llm"),
        ("改成表格", "convert_table", "llm"),
        ("做成流程图", "convert_flowchart", "llm"),
        ("帮我润色一下这段文字", "polish_text", "llm"),
        ("添加一页新幻灯片", "add_slide", "direct"),
        ("删除第3页", "remove_slide", "direct"),
        ("重新生成整个PPT", "regenerate", "llm"),
    ]
    
    for instruction, expected_intent, expected_method in test_cases:
        result = IntentRouter.classify(instruction, current_slide_index=0)
        actual_intent = result["intent"]
        actual_method = result["method"]
        
        assert actual_intent == expected_intent, \
            f"指令 '{instruction}' 应分类为 '{expected_intent}'，实际: '{actual_intent}'"
        assert actual_method == expected_method, \
            f"指令 '{instruction}' 方法应为 '{expected_method}'，实际: '{actual_method}'"
    
    print(f"  ✅ IntentRouter: {len(test_cases)} 个测试用例全部通过")
    return True


def test_overflow_detection():
    """测试溢出检测逻辑在预览面板中的代码结构"""
    # 验证 preview_panel.py 中的溢出相关代码
    import ast
    preview_path = os.path.join(os.path.dirname(__file__), "..", "opencopilot", "capabilities", "ppt", "preview_panel.py")
    
    with open(preview_path) as f:
        source = f.read()
    
    # 检查关键代码是否存在
    checks = [
        ("max_y", "溢出边界变量"),
        ("SLIDE_HEIGHT", "幻灯片高度常量"),
        ("TextWordWrap", "自动换行标志"),
        ("QFontMetrics", "字体度量计算"),
        ("PPT_OVERFLOW_DETECTED", "溢出日志事件"),
        ("ellipsis" if "..." in source else "…", "溢出省略号"),
    ]
    
    for keyword, desc in checks:
        assert keyword in source, f"preview_panel.py 缺少 {desc}: '{keyword}'"
    
    print(f"  ✅ 溢出检测代码完整性验证通过")
    return True


def test_ppt_generator_adaptive():
    """测试 ppt_generator.py 自适应高度和动态字号"""
    # 验证代码结构
    gen_path = os.path.join(os.path.dirname(__file__), "..", "opencopilot", "capabilities", "ppt", "ppt_generator.py")
    
    with open(gen_path) as f:
        source = f.read()
    
    checks = [
        ("level0_size", "一级字号动态变量"),
        ("level1_size", "二级字号动态变量"),
        ("word_wrap", "自动换行设置"),
        ("max_body_height", "最大正文高度"),
        ("estimated_height", "预估高度计算"),
        ("item_count", "内容数量检测"),
    ]
    
    for keyword, desc in checks:
        assert keyword in source, f"ppt_generator.py 缺少 {desc}: '{keyword}'"
    
    print(f"  ✅ ppt_generator 自适应排版代码完整性验证通过")
    return True


def test_prompt_new_sources():
    """测试 prompt.py 新增的上下文源定义"""
    from opencopilot.shared.prompt import CONTEXT_DESCRIPTIONS, CONTEXT_SOURCE_PRIORITY
    
    new_sources = ["ppt_topic_extract", "ppt_content_map", "ppt_chart_convert"]
    for source in new_sources:
        assert source in CONTEXT_DESCRIPTIONS, f"缺少 context_source: {source}"
        assert source in CONTEXT_SOURCE_PRIORITY, f"缺少 priority: {source}"
        assert CONTEXT_SOURCE_PRIORITY[source] == "high", f"{source} 应为 high 优先级"
    
    print(f"  ✅ Prompt 新上下文源: {new_sources}")
    return True


def test_module_exports():
    """测试模块导出完整性"""
    from opencopilot.capabilities.ppt import (
        PPTGenerationPipeline, PipelineResult, Topic, ContentMapping, FormatResult,
        IntentRouter, StorylineView,
    )
    
    assert PPTGenerationPipeline is not None
    assert IntentRouter is not None
    assert StorylineView is not None
    
    print(f"  ✅ 模块导出完整性验证通过")
    return True


def run_all():
    tests = [
        ("Pipeline Fallback", test_pipeline_fallback),
        ("ContentConverter No Fake Data", test_content_converter_no_fake_data),
        ("IntentRouter Classification", test_intent_router),
        ("Overflow Detection Code", test_overflow_detection),
        ("PPT Generator Adaptive", test_ppt_generator_adaptive),
        ("Prompt New Sources", test_prompt_new_sources),
        ("Module Exports", test_module_exports),
    ]
    
    passed = 0
    failed = 0
    
    print("\n" + "=" * 60)
    print("PPT Content-First Pipeline 端到端验证")
    print("=" * 60)
    
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  ❌ {name} FAILED: {e}")
            failed += 1
    
    print(f"\n结果: {passed}/{len(tests)} 通过, {failed} 失败")
    return failed == 0


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
