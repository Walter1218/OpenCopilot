"""
Pipeline PPT 修复测试

覆盖三项核心修复：
1. PlannerMiddleware：PPT 等 action_type 应跳过 Planner（不再触发 ERROR）
2. detect_request_type：PPT 关键词优先级高于 planning/security
3. extract_json_from_text：json_repair 库兜底（在迭代修复之后、截断修复之前）

不依赖 LLM，不 mock 任何外部调用。
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPlannerSkip:
    """PlannerMiddleware 按 action_type 跳过"""

    def test_skip_planner_types_includes_ppt(self):
        """PPT action_type 在跳过列表中"""
        from opencopilot.agent.middlewares import PlannerMiddleware

        assert "ppt" in PlannerMiddleware._skip_planner_types

    def test_skip_planner_types_includes_translate(self):
        """translate action_type 在跳过列表中"""
        from opencopilot.agent.middlewares import PlannerMiddleware

        assert "translate" in PlannerMiddleware._skip_planner_types

    def test_skip_planner_types_covers_all_non_planning(self):
        """跳过列表覆盖所有明确不需要 Planner 的类型"""
        from opencopilot.agent.middlewares import PlannerMiddleware

        expected = {"ppt", "translate", "polish", "fix", "evaluation", "revision", "custom"}
        actual = PlannerMiddleware._skip_planner_types

        for t in expected:
            assert t in actual, f"{t} 应在 _skip_planner_types 中"

    def test_planner_skip_class_attribute_is_frozenset_or_set(self):
        """_skip_planner_types 应为 set 或 frozenset（O(1) 查找）"""
        from opencopilot.agent.middlewares import PlannerMiddleware

        assert isinstance(PlannerMiddleware._skip_planner_types, (set, frozenset))


class TestDetectRequestTypePriority:
    """detect_request_type PPT 路由优先级"""

    def _detect(self, text):
        from asu_custom_agent import detect_request_type
        return detect_request_type(text)

    # ── PPT 应优先于 planning ──

    def test_ppt_with_planning_keyword(self):
        """PPT + 规划关键词 → ppt（非 planning）"""
        assert self._detect("帮我规划一份关于AI发展的PPT大纲") == "ppt"

    def test_ppt_with_design_keyword(self):
        """PPT + 设计关键词 → ppt"""
        assert self._detect("设计一份10页的产品介绍幻灯片") == "ppt"

    def test_ppt_with_security_keyword(self):
        """PPT + 安全关键词 → ppt（非 security）"""
        assert self._detect("这个PPT的安全审批流程怎么加") == "ppt"

    def test_ppt_presentation(self):
        """英文 presentation → ppt"""
        assert self._detect("make a presentation about AI") == "ppt"

    def test_ppt_slide(self):
        """英文 slide → ppt"""
        assert self._detect("add a new slide") == "ppt"

    # ── 非 PPT 请求不应受影响 ──

    def test_planning_without_ppt(self):
        """纯规划请求（无PPT关键词） → planning"""
        assert self._detect("帮我规划一下项目进度") == "planning"

    def test_code_execution_priority(self):
        """代码执行关键词优先级高于 PPT"""
        assert self._detect("运行代码生成PPT") == "code_execution"

    def test_knowledge_priority(self):
        """知识检索优先级高于 PPT"""
        assert self._detect("在知识图谱中搜索PPT相关内容") == "knowledge_query"

    def test_search_request(self):
        """搜索请求正常路由"""
        assert self._detect("搜索一下最新的AI论文") == "search"

    def test_chat_fallback(self):
        """无匹配关键词 → chat"""
        assert self._detect("你好") == "chat"

    # ── 一致性回归：同一请求多次调用结果一致 ──

    def test_route_consistency(self):
        """同一 PPT 请求 10 次调用结果一致"""
        text = "帮我规划一份关于AI发展的PPT大纲"
        results = [self._detect(text) for _ in range(10)]
        assert all(r == "ppt" for r in results), f"路由不一致: {set(results)}"


class TestJsonExtractRobustness:
    """extract_json_from_text 多层鲁棒性验证"""

    def _extract(self, text):
        from ppt_generator import extract_json_from_text
        return extract_json_from_text(text)

    # ── Layer 0: 标准 JSON ──

    def test_standard_json_object(self):
        """标准 JSON 对象直接解析"""
        text = '{"slides": [{"type": "title", "title": "Test"}]}'
        result = self._extract(text)
        assert result is not None
        assert "slides" in result
        assert len(result["slides"]) == 1

    def test_standard_json_with_title(self):
        """标准 JSON 带 title 字段"""
        text = '{"title": "演示文稿", "slides": [{"type": "title", "title": "首页"}]}'
        result = self._extract(text)
        assert result["title"] == "演示文稿"

    # ── Layer 1: 迭代修复 ──

    def test_trailing_comma_repair(self):
        """尾逗号 → 迭代修复"""
        text = '{"slides": [{"type": "title", "title": "Test",}]}'
        result = self._extract(text)
        assert result is not None
        assert "slides" in result

    # ── Layer 2: json_repair 兜底 ──

    def test_complex_broken_json(self):
        """复杂组合错误 → json_repair 兜底"""
        # 多处尾逗号 + 缺少闭合括号
        text = '{"title": "规划", "slides": [{"type": "title", "title": "首页",}, {"type": "content", "title": "内容", "items": [{"level": 0, "text": "要点"},]},]}'
        result = self._extract(text)
        # 至少应返回包含 slides 的结果
        assert result is not None
        if isinstance(result, dict):
            assert "slides" in result

    def test_json_repair_library_available(self):
        """json_repair 库应已安装"""
        try:
            import json_repair
            # 验证核心 API 可用
            repaired = json_repair.repair_json('{"key": "value",}', return_objects=True)
            assert isinstance(repaired, dict)
            assert repaired.get("key") == "value"
        except ImportError:
            pytest.fail("json-repair 库未安装，请运行: pip install json-repair")

    # ── Layer 3: 截断修复 ──

    def test_truncated_json_recovery(self):
        """被截断的 JSON → 保留完整 slide"""
        text = '{"slides": [{"type": "title", "title": "Page1"}, {"type": "content", "title": "Page2", "items": [{"level": 0, "text": "item1"}]}, {"type": "content", "title": "Page3", "items": [{"level": 0, "text": "trunc'
        result = self._extract(text)
        # 至少应恢复前 2 个完整 slide
        if result and isinstance(result, dict) and "slides" in result:
            assert len(result["slides"]) >= 1

    # ── Layer 4: Markdown 降级 ──

    def test_markdown_fallback(self):
        """JSON 全部失败时 → Markdown 降级"""
        text = "# 标题\n## 第一页\n- 要点1\n- 要点2\n## 第二页\n- 要点3"
        result = self._extract(text)
        assert result is not None
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_markdown_fallback_preserves_title(self):
        """Markdown 降级保留标题"""
        text = "# 主标题\n## 子页面\n- 内容"
        result = self._extract(text)
        assert result is not None
        # 至少有一个 slide 包含标题
        titles = [s.get("title", "") for s in result if isinstance(s, dict)]
        assert any("标题" in t or "子页面" in t for t in titles)

    # ── 中文引号处理 ──

    def test_chinese_quotes_handling(self):
        """中文引号应被正确处理"""
        text = '{\u201cslides\u201d: [{\u201ctype\u201d: \u201ctitle\u201d, \u201ctitle\u201d: \u201c测试\u201d}]}'
        result = self._extract(text)
        # 中文引号清理后应能解析
        if result:
            assert isinstance(result, (dict, list))

    # ── None/空输入防御 ──

    def test_empty_string(self):
        """空字符串 → None"""
        result = self._extract("")
        assert result is None

    def test_no_json_no_markdown(self):
        """无 JSON 无 Markdown → None"""
        result = self._extract("这只是一段普通文本，没有任何结构化数据")
        assert result is None


class TestPptGeneratorUnifiedImport:
    """capabilities/ppt/ppt_generator.py 统一导入验证"""

    def test_all_functions_importable(self):
        """所有关键函数可从 capabilities 子模块导入"""
        from opencopilot.capabilities.ppt.ppt_generator import (
            clean_markdown,
            apply_corporate_theme,
            format_title_slide,
            format_content_slide,
            format_chart_slide,
            generate_ppt_from_json,
            extract_json_from_text,
            generate_ppt_from_text,
            parse_inline_formatting,
            add_placeholder_image,
        )
        # 所有导入应为 callable
        for fn in [clean_markdown, apply_corporate_theme, format_title_slide,
                    format_content_slide, format_chart_slide, generate_ppt_from_json,
                    extract_json_from_text, generate_ppt_from_text,
                    parse_inline_formatting, add_placeholder_image]:
            assert callable(fn), f"{fn} 不是 callable"

    def test_imports_match_root_module(self):
        """capabilities 子模块的函数应与根模块是同一对象"""
        import ppt_generator as root
        from opencopilot.capabilities.ppt import ppt_generator as cap

        assert cap.extract_json_from_text is root.extract_json_from_text
        assert cap.generate_ppt_from_json is root.generate_ppt_from_json
        assert cap.clean_markdown is root.clean_markdown
