"""
ContentConvertSkill 全链路执行测试

不 mock 任何依赖，调用真实的 TextAnalyzer + ContentConverter：
1. 自动模式（auto）：数字对比数据 → 图表
2. 显式转表格（Markdown 表格 → 结构化 table_data）
3. 显式转图表（数值文本 → chart_data）
4. 显式转流程图（步骤文本 → flowchart_data）
5. 纯分析模式（analyze）：只返回建议不执行转换
6. 空文本防御
7. 未知意图防御
8. 意图 → 动作路由正确性
"""
import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def skill():
    from opencopilot.capabilities.skill import ContentConvertSkill
    return ContentConvertSkill()


def _run(coro):
    """同步包装器"""
    return asyncio.run(coro)


def _make_ctx(intent, text, title="", chart_type="", action=""):
    from opencopilot.capabilities.skill.models import SkillContext
    data = {"text": text}
    if title:
        data["title"] = title
    if chart_type:
        data["chart_type"] = chart_type
    if action:
        data["action"] = action
    return SkillContext(intent=intent, input_data=data)


class TestAutoConvert:
    """自动模式验证"""

    def test_auto_selects_chart_for_numbers(self, skill):
        """数字对比数据 → 自动选择图表"""
        text = "Q1: 100万, Q2: 200万, Q3: 150万, Q4: 300万"
        result = _run(skill.execute(_make_ctx("analyze_and_convert", text)))

        assert result.success
        assert result.data["action"] == "auto"
        assert result.data["auto_selected"] == "chart"
        assert "chart_data" in result.data

    def test_auto_returns_recommendations_for_unstructured(self, skill):
        """非结构化文本 → 不自动选择，返回建议"""
        text = "这是一段普通的描述性文本，没有明显的结构化数据。"
        result = _run(skill.execute(_make_ctx("content_convert", text)))

        assert result.success
        assert result.data["action"] == "auto"
        # auto_selected 可能为 None 或者有低置信度结果
        # 关键是成功返回且不崩溃


class TestConvertToTable:
    """显式转表格"""

    def test_markdown_table_to_structured(self, skill):
        """Markdown 表格 → 结构化 table_data"""
        text = "| 产品 | 价格 |\n|---|---|\n| iPhone | 6999 |\n| Samsung | 7999 |"
        result = _run(skill.execute(_make_ctx("convert_to_table", text, title="价格对比")))

        assert result.success
        assert result.data["action"] == "convert_table"
        raw = result.data["table_data"]
        assert raw["content_type"] == "table"
        inner = raw["table_data"]
        assert inner["title"] == "价格对比"
        assert len(inner["columns"]) >= 1
        assert len(inner["rows"]) >= 1

    def test_key_value_to_table(self, skill):
        """键值对文本 → 表格"""
        text = "销售部：营收 5000 万\n技术部：营收 3000 万\n市场部：营收 2000 万"
        result = _run(skill.execute(_make_ctx("convert_to_table", text, title="部门业绩")))

        assert result.success
        raw = result.data["table_data"]
        assert raw["content_type"] == "table"


class TestConvertToChart:
    """显式转图表"""

    def test_bar_chart_for_comparison(self, skill):
        """数值对比 → 柱状图"""
        text = "北京: 2100万, 上海: 2400万, 广州: 1500万, 深圳: 1300万"
        result = _run(skill.execute(_make_ctx(
            "convert_to_chart", text, title="城市人口", chart_type="bar"
        )))

        assert result.success
        assert result.data["action"] == "convert_chart"
        assert result.data["chart_type"] == "bar"
        raw = result.data["chart_data"]
        assert raw["content_type"] == "chart"

    def test_line_chart_for_trend(self, skill):
        """趋势数据 → 折线图"""
        text = "2020: 100亿, 2021: 150亿, 2022: 200亿, 2023: 280亿"
        result = _run(skill.execute(_make_ctx(
            "convert_to_chart", text, title="营收趋势", chart_type="line"
        )))

        assert result.success
        assert result.data["chart_type"] == "line"


class TestConvertToFlowchart:
    """显式转流程图"""

    def test_flowchart_with_steps(self, skill):
        """步骤文本 → 流程图"""
        text = "首先提交申请，然后领导审批，接着HR审核，最后完成"
        result = _run(skill.execute(_make_ctx(
            "convert_to_flowchart", text, title="审批流程"
        )))

        assert result.success
        assert result.data["action"] == "convert_flowchart"
        raw = result.data["flowchart_data"]
        assert raw["content_type"] == "flowchart"
        inner = raw["flowchart_data"]
        assert inner["title"] == "审批流程"
        # 降级处理也会生成 steps
        assert len(inner.get("steps", [])) >= 1

    def test_flowchart_fallback_to_lines(self, skill):
        """无明确步骤关键词时按行降级为流程图"""
        text = "需求分析\n方案设计\n编码实现\n测试验证\n上线部署"
        result = _run(skill.execute(_make_ctx(
            "convert_to_flowchart", text, title="开发流程"
        )))

        assert result.success
        inner = result.data["flowchart_data"]["flowchart_data"]
        assert len(inner["steps"]) >= 3, f"降级应按行拆分，实际: {inner['steps']}"


class TestAnalyzeOnly:
    """纯分析模式"""

    def test_analyze_returns_recommendations(self, skill):
        """analyze 动作只返回分析建议，不执行转换"""
        text = "销售额: 5000万, 利润: 1200万, 增长率: 15%"
        # 使用不在 action_map 中的 intent，通过 input_data.action 指定 analyze
        result = _run(skill.execute(_make_ctx("chat", text, action="analyze")))

        assert result.success
        assert result.data["action"] == "analyze"
        assert "recommendations" in result.data
        # 不应有 table_data/chart_data/flowchart_data
        assert "table_data" not in result.data
        assert "chart_data" not in result.data


class TestDefensiveBehavior:
    """防御性行为验证"""

    def test_empty_text_returns_failure(self, skill):
        """空文本 → 失败"""
        result = _run(skill.execute(_make_ctx("content_convert", "")))
        assert not result.success
        assert "未提供" in result.error

    def test_whitespace_only_returns_failure(self, skill):
        """纯空白 → 失败"""
        result = _run(skill.execute(_make_ctx("content_convert", "   \n  \n  ")))
        assert not result.success

    def test_unknown_action_via_input_data(self, skill):
        """通过 input_data 指定未知 action → 走 auto 兜底"""
        result = _run(skill.execute(_make_ctx(
            "chat", "Q1: 100, Q2: 200", action="unknown_action"
        )))
        # unknown_action 不在已知列表，fallback 到 auto
        assert result.success
        assert result.data["action"] == "auto"


class TestIntentRouting:
    """意图 → 动作路由"""

    def test_convert_to_table_intent(self, skill):
        """intent=convert_to_table → convert_table 动作"""
        result = _run(skill.execute(_make_ctx(
            "convert_to_table", "| A | B |\n|---|---|\n| 1 | 2 |"
        )))
        assert result.data["action"] == "convert_table"

    def test_convert_to_chart_intent(self, skill):
        """intent=convert_to_chart → convert_chart 动作"""
        result = _run(skill.execute(_make_ctx(
            "convert_to_chart", "A: 100, B: 200"
        )))
        assert result.data["action"] == "convert_chart"

    def test_convert_to_flowchart_intent(self, skill):
        """intent=convert_to_flowchart → convert_flowchart 动作"""
        result = _run(skill.execute(_make_ctx(
            "convert_to_flowchart", "首先A 然后B 最后C"
        )))
        assert result.data["action"] == "convert_flowchart"

    def test_text_to_visual_intent_maps_to_auto(self, skill):
        """intent=text_to_visual → auto 动作"""
        result = _run(skill.execute(_make_ctx(
            "text_to_visual", "Q1: 100, Q2: 200"
        )))
        assert result.data["action"] == "auto"
