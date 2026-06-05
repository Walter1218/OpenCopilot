"""
PPT Skill

封装 PPT 共创模块为 Skill，支持 PPT 生成、建议、检查、分析等功能。
"""

import os
import json
from typing import Any, Dict, List, Optional
from .base import BaseSkill
from .models import SkillMetadata, SkillContext, SkillResult, SkillStatus


class PPTSkill(BaseSkill):
    """PPT Skill
    
    封装 PPT 共创模块，提供以下功能：
    - PPT 生成：从文本/大纲生成 PPT
    - PPT 建议：基于上下文生成优化建议
    - PPT 检查：检查 PPT 质量
    - PPT 分析：分析 PPT 结构和内容
    - 内容转换：文本转图表/表格
    - PPT 共创：AI 辅助编辑
    """
    
    @property
    def metadata(self) -> SkillMetadata:
        """获取 Skill 元数据"""
        return SkillMetadata(
            name="ppt_skill",
            version="1.0.0",
            description="PPT 共创技能，支持 PPT 生成、建议、检查、分析等功能",
            author="OpenCopilot",
            category="ppt",            tags=["ppt", "presentation", "generate", "suggest", "check", "analyze", "convert"],
            intents=[
                "ppt_generate",
                "ppt_suggest",
                "ppt_check",
                "ppt_analyze",
                "ppt_convert",
                "ppt_cocreate",
                "presentation",
                "slides"
            ],
            dependencies=[],
            config_schema={
                "output_dir": {
                    "type": "string",
                    "description": "PPT 输出目录",
                    "default": "./output"
                },
                "default_theme": {
                    "type": "string",
                    "description": "默认主题",
                    "enum": ["corporate", "modern", "creative", "minimal"],
                    "default": "corporate"
                },
                "max_slides": {
                    "type": "integer",
                    "description": "最大幻灯片数量",
                    "default": 20
                }
            },
            input_schema={
                "action": {
                    "type": "string",
                    "description": "操作类型",
                    "enum": ["generate", "suggest", "check", "analyze", "convert", "cocreate"],
                    "required": True
                },
                "content": {
                    "type": "string",
                    "description": "输入内容（文本或大纲）"
                },
                "slides": {
                    "type": "array",
                    "description": "幻灯片数据"
                },
                "context": {
                    "type": "object",
                    "description": "PPT 上下文"
                }
            },
            output_schema={
                "success": {
                    "type": "boolean",
                    "description": "是否成功"
                },
                "data": {
                    "type": "object",
                    "description": "结果数据"
                },
                "error": {
                    "type": "string",
                    "description": "错误信息"
                }
            }
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行 PPT Skill
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        try:
            action = context.input_data.get("action", "generate")
            
            if action == "generate":
                return await self._generate_ppt(context)
            elif action == "suggest":
                return await self._generate_suggestions(context)
            elif action == "check":
                return await self._check_ppt(context)
            elif action == "analyze":
                return await self._analyze_ppt(context)
            elif action == "convert":
                return await self._convert_content(context)
            elif action == "cocreate":
                return await self._cocreate_ppt(context)
            else:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"Unknown action: {action}",
                    status=SkillStatus.FAILED
                )
        
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=str(e),
                status=SkillStatus.FAILED
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
            if action in ["generate", "suggest", "check", "analyze", "convert", "cocreate"]:
                return 0.8
        
        # 检查内容类型
        content = context.input_data.get("content", "")
        if content and any(keyword in content.lower() for keyword in ["ppt", "幻灯片", "演示", "slides", "presentation"]):
            return 0.7
        
        return 0.0
    
    async def _generate_ppt(self, context: SkillContext) -> SkillResult:
        """生成 PPT
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        content = context.input_data.get("content", "")
        title = context.input_data.get("title", "演示文稿")
        output_dir = context.input_data.get("output_dir", self.config.get("output_dir", "./output"))
        
        if not content:
            return SkillResult(
                success=False,
                data={},
                error="Content is required for PPT generation",
                status=SkillStatus.FAILED
            )
        
        try:
            # 导入 PPT 生成器
            import sys
            from ppt_generator import generate_ppt_from_text
            
            # 生成 PPT
            output_path = os.path.join(output_dir, f"{title}.pptx")
            os.makedirs(output_dir, exist_ok=True)
            
            # generate_ppt_from_text 只接受 text 和 output_path 参数
            result_path = generate_ppt_from_text(
                text=content,
                output_path=output_path
            )
            
            return SkillResult(
                success=True,
                data={
                    "output_path": result_path,
                    "title": title,
                    "file_size": os.path.getsize(result_path) if os.path.exists(result_path) else 0
                },
                status=SkillStatus.COMPLETED
            )
        
        except ImportError as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to import PPT generator: {str(e)}",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to generate PPT: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _generate_suggestions(self, context: SkillContext) -> SkillResult:
        """生成优化建议
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        ppt_context = context.input_data.get("context", {})
        focus = context.input_data.get("focus")
        max_suggestions = context.input_data.get("max_suggestions", 5)
        
        if not ppt_context:
            return SkillResult(
                success=False,
                data={},
                error="PPT context is required for suggestions",
                status=SkillStatus.FAILED
            )
        
        try:
            # 导入（项目已安装为可编辑包，无需路径修正）
            from opencopilot.capabilities.ppt.suggestion_engine import SuggestionEngine
            
            # 创建建议引擎
            engine = SuggestionEngine()
            
            # 生成建议
            result = engine.generate_suggestions(
                context=ppt_context,
                focus=focus,
                max_suggestions=max_suggestions
            )
            
            return SkillResult(
                success=True,
                data={
                    "suggestions": result.to_dict(),
                    "count": len(result.suggestions)
                },
                status=SkillStatus.COMPLETED
            )
        
        except ImportError as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to import suggestion engine: {str(e)}",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to generate suggestions: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _check_ppt(self, context: SkillContext) -> SkillResult:
        """检查 PPT 质量
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        ppt_context = context.input_data.get("context", {})
        checks = context.input_data.get("checks", ["content_quality", "style_consistency", "logical_flow"])
        
        if not ppt_context:
            return SkillResult(
                success=False,
                data={},
                error="PPT context is required for checking",
                status=SkillStatus.FAILED
            )
        
        try:
            # 导入（项目已安装为可编辑包，无需路径修正）
            from opencopilot.capabilities.ppt.context_analyzer import ContextAnalyzer
            
            # 创建分析器
            analyzer = ContextAnalyzer()
            
            # 获取幻灯片列表
            slides = ppt_context.get("slides", [])
            
            # 分析 PPT 结构
            analysis = analyzer.analyze_structure(slides)
            
            # 执行检查
            results = {}
            for check_type in checks:
                if check_type == "content_quality":
                    results["content_quality"] = self._check_content_quality(ppt_context, analysis)
                elif check_type == "style_consistency":
                    results["style_consistency"] = self._check_style_consistency(ppt_context, analysis)
                elif check_type == "logical_flow":
                    results["logical_flow"] = self._check_logical_flow(ppt_context, analysis)
            
            # 计算总体分数
            total_score = sum(r.get("score", 0) for r in results.values()) / len(results) if results else 0
            
            # 转换分析结果为字典
            analysis_dict = {
                "total_slides": analysis.total_slides,
                "slide_types": analysis.slide_types,
                "logical_flow": analysis.logical_flow,
                "repeated_content": analysis.repeated_content,
                "missing_sections": analysis.missing_sections,
                "structure_score": analysis.structure_score
            }
            
            return SkillResult(
                success=True,
                data={
                    "results": results,
                    "total_score": round(total_score, 2),
                    "analysis": analysis_dict
                },
                status=SkillStatus.COMPLETED
            )
        
        except ImportError as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to import context analyzer: {str(e)}",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to check PPT: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _analyze_ppt(self, context: SkillContext) -> SkillResult:
        """分析 PPT 结构和内容
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        ppt_context = context.input_data.get("context", {})
        
        if not ppt_context:
            return SkillResult(
                success=False,
                data={},
                error="PPT context is required for analysis",
                status=SkillStatus.FAILED
            )
        
        try:
            # 导入（项目已安装为可编辑包，无需路径修正）
            from opencopilot.capabilities.ppt.context_analyzer import ContextAnalyzer
            
            # 创建分析器
            analyzer = ContextAnalyzer()
            
            # 获取幻灯片列表
            slides = ppt_context.get("slides", [])
            
            # 分析 PPT 结构
            structure_analysis = analyzer.analyze_structure(slides)
            
            # 分析每个幻灯片的内容
            content_analyses = []
            for slide in slides:
                content = slide.get("content", "")
                if content:
                    content_analysis = analyzer.analyze_content(content)
                    content_analyses.append({
                        "slide_index": slide.get("index", 0),
                        "content_type": content_analysis.content_type.value,
                        "confidence": content_analysis.confidence,
                        "key_points": content_analysis.key_points
                    })
            
            # 转换结构分析结果为字典
            structure_dict = {
                "total_slides": structure_analysis.total_slides,
                "slide_types": structure_analysis.slide_types,
                "logical_flow": structure_analysis.logical_flow,
                "repeated_content": structure_analysis.repeated_content,
                "missing_sections": structure_analysis.missing_sections,
                "structure_score": structure_analysis.structure_score
            }
            
            return SkillResult(
                success=True,
                data={
                    "structure": structure_dict,
                    "content_analyses": content_analyses,
                    "summary": {
                        "total_slides": len(slides),
                        "analyzed_slides": len(content_analyses),
                        "structure_score": structure_analysis.structure_score
                    }
                },
                status=SkillStatus.COMPLETED
            )
        
        except ImportError as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to import context analyzer: {str(e)}",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to analyze PPT: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _convert_content(self, context: SkillContext) -> SkillResult:
        """内容转换
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        content = context.input_data.get("content", "")
        target_type = context.input_data.get("target_type", "auto")
        title = context.input_data.get("title", "")
        
        if not content:
            return SkillResult(
                success=False,
                data={},
                error="Content is required for conversion",
                status=SkillStatus.FAILED
            )
        
        try:
            # 导入（项目已安装为可编辑包，无需路径修正）
            from opencopilot.capabilities.ppt.content_converter import TextAnalyzer
            
            # 分析文本
            analysis = TextAnalyzer.analyze(content)
            
            # 获取最佳匹配
            best_match = analysis.get("best_match")
            extracted_data = analysis.get("extracted_data")
            
            return SkillResult(
                success=True,
                data={
                    "analysis": analysis,
                    "best_match": best_match,
                    "extracted_data": extracted_data,
                    "recommendations": analysis.get("recommendations", [])
                },
                status=SkillStatus.COMPLETED
            )
        
        except ImportError as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to import content converter: {str(e)}",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to convert content: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    async def _cocreate_ppt(self, context: SkillContext) -> SkillResult:
        """PPT 共创
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        message = context.input_data.get("message", "")
        ppt_context = context.input_data.get("context", {})
        session_id = context.input_data.get("session_id", "default")
        
        if not message:
            return SkillResult(
                success=False,
                data={},
                error="Message is required for PPT co-creation",
                status=SkillStatus.FAILED
            )
        
        try:
            # 导入（项目已安装为可编辑包，无需路径修正）
            from opencopilot.capabilities.ppt.conversation_manager import ConversationManager
            
            # 创建对话管理器
            manager = ConversationManager()
            
            # 处理消息
            response = manager.process_message(
                session_id=session_id,
                message=message,
                context=ppt_context
            )
            
            # 转换响应为字典
            response_dict = response.to_dict()
            
            return SkillResult(
                success=True,
                data={
                    "response": response_dict.get("response", ""),
                    "session_id": response_dict.get("session_id", session_id),
                    "options": response_dict.get("options", []),
                    "context_update": response_dict.get("context_update"),
                    "requires_confirmation": response_dict.get("requires_confirmation", False)
                },
                status=SkillStatus.COMPLETED
            )
        
        except ImportError as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to import conversation manager: {str(e)}",
                status=SkillStatus.FAILED
            )
        except Exception as e:
            return SkillResult(
                success=False,
                data={},
                error=f"Failed to co-create PPT: {str(e)}",
                status=SkillStatus.FAILED
            )
    
    def _check_content_quality(self, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """检查内容质量"""
        slides = context.get("slides", [])
        issues = []
        score = 100
        
        for i, slide in enumerate(slides):
            title = slide.get("title", "")
            content = slide.get("content", "")
            
            # 检查标题
            if not title:
                issues.append({"slide": i, "type": "missing_title", "message": f"幻灯片 {i+1} 缺少标题"})
                score -= 5
            
            # 检查内容
            if not content:
                issues.append({"slide": i, "type": "empty_content", "message": f"幻灯片 {i+1} 内容为空"})
                score -= 10
            elif len(content) < 10:
                issues.append({"slide": i, "type": "short_content", "message": f"幻灯片 {i+1} 内容过短"})
                score -= 3
        
        return {
            "score": max(0, score),
            "issues": issues,
            "total_issues": len(issues)
        }
    
    def _check_style_consistency(self, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """检查样式一致性"""
        slides = context.get("slides", [])
        issues = []
        score = 100
        
        # 检查布局一致性
        layouts = [slide.get("layout", "default") for slide in slides]
        unique_layouts = set(layouts)
        
        if len(unique_layouts) > 3:
            issues.append({"type": "too_many_layouts", "message": "使用了过多不同的布局"})
            score -= 10
        
        # 检查标题格式一致性
        title_lengths = [len(slide.get("title", "")) for slide in slides if slide.get("title")]
        if title_lengths:
            avg_length = sum(title_lengths) / len(title_lengths)
            for i, slide in enumerate(slides):
                title = slide.get("title", "")
                if title and abs(len(title) - avg_length) > 20:
                    issues.append({"slide": i, "type": "inconsistent_title", "message": f"幻灯片 {i+1} 标题长度不一致"})
                    score -= 2
        
        return {
            "score": max(0, score),
            "issues": issues,
            "total_issues": len(issues)
        }
    
    def _check_logical_flow(self, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """检查逻辑流程"""
        slides = context.get("slides", [])
        issues = []
        score = 100
        
        # 检查是否有封面
        if slides and not any(keyword in slides[0].get("title", "").lower() for keyword in ["封面", "标题", "title", "cover"]):
            issues.append({"type": "missing_cover", "message": "缺少封面幻灯片"})
            score -= 15
        
        # 检查是否有总结
        if slides and not any(keyword in slides[-1].get("title", "").lower() for keyword in ["总结", "结论", "summary", "conclusion"]):
            issues.append({"type": "missing_summary", "message": "缺少总结幻灯片"})
            score -= 10
        
        # 检查幻灯片数量
        if len(slides) < 3:
            issues.append({"type": "too_few_slides", "message": "幻灯片数量过少"})
            score -= 20
        elif len(slides) > 20:
            issues.append({"type": "too_many_slides", "message": "幻灯片数量过多"})
            score -= 5
        
        return {
            "score": max(0, score),
            "issues": issues,
            "total_issues": len(issues)
        }
