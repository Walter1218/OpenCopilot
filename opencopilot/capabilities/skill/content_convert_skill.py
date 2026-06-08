"""
Content Convert Skill

将选定文本智能转换为表格、图表、流程图等结构化可视化形式。
封装 TextAnalyzer + ContentConverter 能力，提供统一的 Skill 接口。
"""

import logging
from typing import Any, Dict
from .base import BaseSkill
from .models import SkillMetadata, SkillContext, SkillResult, SkillStatus

logger = logging.getLogger(__name__)


class ContentConvertSkill(BaseSkill):
    """内容转换 Skill
    
    支持以下转换动作：
    - analyze: 自动分析文本结构并推荐最佳转换方式
    - convert_table: 文本 → 结构化表格
    - convert_chart: 文本 → 图表（柱状图/折线图/饼图）
    - convert_flowchart: 文本 → 流程图
    - auto: 根据分析结果自动选择最佳转换
    """
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="content_convert",
            version="1.0.0",
            description="将文本智能转换为表格、图表、流程图等结构化可视化形式",
            author="OpenCopilot",
            category="visualization",
            tags=["convert", "table", "chart", "flowchart", "visualization", "structure"],
            intents=[
                "content_convert",
                "convert_to_table",
                "convert_to_chart",
                "convert_to_flowchart",
                "analyze_and_convert",
                "text_to_visual",
            ],
            dependencies=[],
        )
    
    async def can_handle(self, context: SkillContext) -> float:
        """判断是否能处理该请求"""
        # 精确意图匹配
        if context.intent in self.metadata.intents:
            return 0.95
        
        # 输入数据中包含转换相关关键词
        text = context.input_data.get("text", "")
        convert_keywords = ["转表格", "转图表", "流程图", "可视化", "转成表", "转为表", "画流程"]
        if any(kw in text for kw in convert_keywords):
            return 0.8
        
        return 0.0
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行内容转换"""
        action = self._resolve_action(context)
        text = context.input_data.get("text", "")
        title = context.input_data.get("title", "")
        
        if not text or not text.strip():
            return SkillResult(
                success=False,
                data={},
                error="未提供待转换的文本内容",
                status=SkillStatus.FAILED,
            )
        
        logger.info(f"[ContentConvertSkill] action={action}, text_len={len(text)}, title={title}")
        
        try:
            if action == "analyze":
                return self._do_analyze(text)
            elif action == "convert_table":
                return self._do_convert_table(text, title)
            elif action == "convert_chart":
                chart_type = context.input_data.get("chart_type", "bar")
                return self._do_convert_chart(text, chart_type, title)
            elif action == "convert_flowchart":
                return self._do_convert_flowchart(text, title)
            elif action == "auto":
                return self._do_auto_convert(text, title)
            else:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"未知的转换动作: {action}",
                    status=SkillStatus.FAILED,
                )
        except Exception as e:
            logger.error(f"[ContentConvertSkill] 转换失败: {e}", exc_info=True)
            return SkillResult(
                success=False,
                data={},
                error=f"转换失败: {str(e)}",
                status=SkillStatus.FAILED,
            )
    
    def _resolve_action(self, context: SkillContext) -> str:
        """从意图和输入数据中解析具体动作"""
        intent = context.intent
        action_map = {
            "convert_to_table": "convert_table",
            "convert_to_chart": "convert_chart",
            "convert_to_flowchart": "convert_flowchart",
            "analyze_and_convert": "auto",
            "content_convert": "auto",
            "text_to_visual": "auto",
        }
        if intent in action_map:
            return action_map[intent]
        
        # 从 input_data 中查找显式 action
        action = context.input_data.get("action", "")
        if action in ("analyze", "convert_table", "convert_chart", "convert_flowchart", "auto"):
            return action
        
        return "auto"
    
    def _do_analyze(self, text: str) -> SkillResult:
        """分析文本结构，返回转换建议"""
        from opencopilot.capabilities.ppt.content_converter import TextAnalyzer
        result = TextAnalyzer.analyze(text)
        return SkillResult(
            success=True,
            data={
                "action": "analyze",
                "recommendations": result.get("recommendations", []),
                "best_match": result.get("best_match"),
                "extracted_data": result.get("extracted_data"),
            },
        )
    
    def _do_convert_table(self, text: str, title: str) -> SkillResult:
        """文本 → 表格"""
        from opencopilot.capabilities.ppt.content_converter import ContentConverter
        result = ContentConverter.convert_to_table(text, title=title or "数据表格")
        return SkillResult(
            success=True,
            data={"action": "convert_table", "table_data": result},
        )
    
    def _do_convert_chart(self, text: str, chart_type: str, title: str) -> SkillResult:
        """文本 → 图表"""
        from opencopilot.capabilities.ppt.content_converter import ContentConverter
        result = ContentConverter.convert_to_chart(text, chart_type=chart_type, title=title or "数据图表")
        return SkillResult(
            success=True,
            data={"action": "convert_chart", "chart_type": chart_type, "chart_data": result},
        )
    
    def _do_convert_flowchart(self, text: str, title: str) -> SkillResult:
        """文本 → 流程图"""
        from opencopilot.capabilities.ppt.content_converter import ContentConverter
        result = ContentConverter.convert_to_flowchart(text, title=title or "流程图")
        return SkillResult(
            success=True,
            data={"action": "convert_flowchart", "flowchart_data": result},
        )
    
    def _do_auto_convert(self, text: str, title: str) -> SkillResult:
        """自动模式：分析后选择最佳转换"""
        from opencopilot.capabilities.ppt.content_converter import TextAnalyzer, ContentConverter
        
        analysis = TextAnalyzer.analyze(text)
        best_match = analysis.get("best_match")
        
        if not best_match:
            # 无法识别结构，返回分析结果让用户选择
            return SkillResult(
                success=True,
                data={
                    "action": "auto",
                    "auto_selected": None,
                    "recommendations": analysis.get("recommendations", []),
                    "message": "未识别到明确的结构化数据，请指定转换类型",
                },
            )
        
        match_type = best_match.get("type", "")
        confidence = best_match.get("confidence", 0)
        
        logger.info(f"[ContentConvertSkill] auto: best_match={match_type}, confidence={confidence}")
        
        if match_type == "table" and confidence >= 0.6:
            result = ContentConverter.convert_to_table(text, title=title or "数据表格")
            return SkillResult(
                success=True,
                data={"action": "auto", "auto_selected": "table", "table_data": result, "confidence": confidence},
            )
        elif match_type == "chart" and confidence >= 0.6:
            chart_sub = best_match.get("chart_type", "bar")
            result = ContentConverter.convert_to_chart(text, chart_type=chart_sub, title=title or "数据图表")
            return SkillResult(
                success=True,
                data={"action": "auto", "auto_selected": "chart", "chart_type": chart_sub, "chart_data": result, "confidence": confidence},
            )
        elif match_type == "flowchart" and confidence >= 0.6:
            result = ContentConverter.convert_to_flowchart(text, title=title or "流程图")
            return SkillResult(
                success=True,
                data={"action": "auto", "auto_selected": "flowchart", "flowchart_data": result, "confidence": confidence},
            )
        else:
            # 置信度不足，返回建议
            return SkillResult(
                success=True,
                data={
                    "action": "auto",
                    "auto_selected": None,
                    "best_match": best_match,
                    "recommendations": analysis.get("recommendations", []),
                    "message": f"识别到 {match_type} (置信度 {confidence:.1%})，低于阈值，请确认转换类型",
                },
            )
