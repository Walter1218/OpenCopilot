"""
Evaluation Skill

封装 OpenCopilotEvaluator 为 Skill，支持内容质量评价、评分、等级判定等功能。
"""

import os
import sys
from typing import Any, Dict, List, Optional
from .base import BaseSkill
from .models import SkillMetadata, SkillContext, SkillResult, SkillStatus


class EvaluationSkill(BaseSkill):
    """Evaluation Skill
    
    封装 OpenCopilotEvaluator，提供以下功能：
    - 内容质量评价：对文本、代码、翻译等内容进行质量评价
    - 评分：返回 1-5 分的评分
    - 等级判定：优秀、良好、合格、需改进、不合格
    - 详细报告：各维度评分、反馈、改进建议
    """
    
    @property
    def metadata(self) -> SkillMetadata:
        """获取 Skill 元数据"""
        return SkillMetadata(
            name="evaluation_skill",
            version="1.0.0",
            description="内容质量评价技能，支持多场景质量评估",
            author="OpenCopilot",
            tags=["evaluation", "quality", "score", "review"],
            intents=[
                "evaluate",
                "quality_check",
                "score",
                "review",
                "assess"
            ],
            dependencies=[],
            config_schema={},
            input_schema={
                "content": {
                    "type": "string",
                    "description": "要评价的内容",
                    "required": True
                },
                "scene": {
                    "type": "string",
                    "description": "场景类型",
                    "enum": ["auto", "translate", "code", "polish", "revision", "custom"],
                    "required": True
                },
                "input_text": {
                    "type": "string",
                    "description": "输入文本（原文）",
                    "required": False
                },
                "reference": {
                    "type": "string",
                    "description": "参考文本（翻译场景可选）",
                    "required": False
                },
                "instruction": {
                    "type": "string",
                    "description": "自定义指令（custom场景必填）",
                    "required": False
                },
                "full_document": {
                    "type": "string",
                    "description": "完整文档（revision场景必填）",
                    "required": False
                }
            },
            output_schema={
                "score": {
                    "type": "number",
                    "description": "评分（1-5）"
                },
                "level": {
                    "type": "string",
                    "description": "等级（优秀、良好、合格、需改进、不合格）"
                },
                "summary": {
                    "type": "string",
                    "description": "评价总结"
                },
                "improvement_plan": {
                    "type": "string",
                    "description": "改进计划"
                },
                "report": {
                    "type": "object",
                    "description": "详细报告"
                }
            }
        )
    
    async def can_handle(self, context: SkillContext) -> float:
        """判断是否能处理该上下文
        
        Args:
            context: 执行上下文
        
        Returns:
            float: 置信度 (0-1)
        """
        # 检查意图
        if context.intent in self.metadata.intents:
            return 0.9
        
        # 检查输入数据
        if "action" in context.input_data:
            action = context.input_data["action"]
            if action in ["evaluate", "quality_check", "score", "review", "assess"]:
                return 0.8
        
        # 检查内容类型
        content = context.input_data.get("content", "")
        if isinstance(content, str):
            content_lower = content.lower()
            evaluation_keywords = ["评估", "评价", "质量", "评分", "等级", "evaluate", "quality", "score"]
            if any(keyword in content_lower for keyword in evaluation_keywords):
                return 0.7
        
        return 0.0
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行评价
        
        Args:
            context: 执行上下文
            
        Returns:
            SkillResult: 执行结果
        """
        # 获取参数
        content = context.input_data.get("content")
        scene = context.input_data.get("scene", "auto")
        input_text = context.input_data.get("input_text", "")
        reference = context.input_data.get("reference")
        instruction = context.input_data.get("instruction")
        full_document = context.input_data.get("full_document")
        
        # 验证必填参数
        if not content:
            return SkillResult(
                success=False,
                data={},
                error="content is required",
                status=SkillStatus.FAILED
            )
        
        # 验证场景类型
        valid_scenes = ["auto", "translate", "code", "polish", "revision", "custom"]
        if scene not in valid_scenes:
            return SkillResult(
                success=False,
                data={},
                error=f"Invalid scene: {scene}. Valid scenes: {', '.join(valid_scenes)}",
                status=SkillStatus.FAILED
            )
        
        # 验证 custom 场景必须有 instruction
        if scene == "custom" and not instruction:
            return SkillResult(
                success=False,
                data={},
                error="instruction is required for custom scene",
                status=SkillStatus.FAILED
            )
        
        # 验证 revision 场景必须有 full_document
        if scene == "revision" and not full_document:
            return SkillResult(
                success=False,
                data={},
                error="full_document is required for revision scene",
                status=SkillStatus.FAILED
            )
        
        try:
            # 导入评价工具
            import sys
            # 添加项目根目录到路径
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            
            from tools.evaluation_tools import OpenCopilotEvaluator
            
            # 创建评价器
            evaluator = OpenCopilotEvaluator()
            
            # 执行评价
            report = evaluator.evaluate(
                scene=scene,
                input_text=input_text,
                output_text=content,
                reference=reference,
                instruction=instruction,
                full_document=full_document
            )
            
            # 转换报告为字典
            report_dict = self._convert_report_to_dict(report)
            
            return SkillResult(
                success=True,
                data={
                    "score": report.total_score,
                    "level": report.level,
                    "summary": report.summary,
                    "improvement_plan": report.improvement_plan,
                    "report": report_dict
                },
                status=SkillStatus.COMPLETED
            )
        
        except ImportError as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to import evaluation tools: {str(e)}",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to evaluate content: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    def _convert_report_to_dict(self, report) -> Dict[str, Any]:
        """将 QualityReport 转换为字典
        
        Args:
            report: QualityReport 对象
            
        Returns:
            Dict[str, Any]: 字典格式的报告
        """
        report_dict = {
            "content": report.content,
            "scene": report.scene,
            "scene_label": report.scene_label,
            "total_score": report.total_score,
            "level": report.level,
            "summary": report.summary,
            "improvement_plan": report.improvement_plan,
            "input_text": report.input_text,
            "reference_text": report.reference_text,
            "custom_instruction": report.custom_instruction,
            "full_document": report.full_document,
            "results": []
        }
        
        # 转换评价结果
        for result in report.results:
            result_dict = {
                "dimension": result.dimension,
                "dimension_label": result.dimension_label,
                "score": result.score,
                "weight": result.weight,
                "feedback": result.feedback,
                "suggestions": result.suggestions
            }
            report_dict["results"].append(result_dict)
        
        return report_dict
    
    async def _evaluate_content(self, context: SkillContext) -> SkillResult:
        """评价内容（内部方法）
        
        Args:
            context: 执行上下文
            
        Returns:
            SkillResult: 执行结果
        """
        return await self.execute(context)
    
    async def _get_score(self, context: SkillContext) -> SkillResult:
        """获取评分（内部方法）
        
        Args:
            context: 执行上下文
            
        Returns:
            SkillResult: 执行结果
        """
        result = await self.execute(context)
        if result.success:
            # 只返回评分信息
            return SkillResult(
                success=True,
                data={
                    "score": result.data.get("score"),
                    "level": result.data.get("level")
                },
                status=SkillStatus.COMPLETED
            )
        return result
    
    async def _get_report(self, context: SkillContext) -> SkillResult:
        """获取详细报告（内部方法）
        
        Args:
            context: 执行上下文
            
        Returns:
            SkillResult: 执行结果
        """
        result = await self.execute(context)
        if result.success:
            # 只返回报告信息
            return SkillResult(
                success=True,
                data={
                    "report": result.data.get("report"),
                    "summary": result.data.get("summary"),
                    "improvement_plan": result.data.get("improvement_plan")
                },
                status=SkillStatus.COMPLETED
            )
        return result