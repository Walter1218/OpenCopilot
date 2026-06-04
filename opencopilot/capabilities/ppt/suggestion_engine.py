"""
AI 主动建议引擎

基于上下文分析，主动为用户提供优化建议。
"""

import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from .context_analyzer import (
    ContextAnalyzer,
    ContentType,
    SuggestionType,
    ContentAnalysis,
    StyleCheckResult,
    PPTStructureAnalysis
)


@dataclass
class Suggestion:
    """建议"""
    id: str
    type: SuggestionType
    title: str
    description: str
    confidence: float
    action: Dict[str, Any]
    preview: Optional[Dict[str, Any]] = None
    priority: int = 0  # 优先级，数字越小优先级越高
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "action": self.action,
            "preview": self.preview,
            "priority": self.priority
        }


@dataclass
class SuggestionResult:
    """建议结果"""
    suggestions: List[Suggestion]
    analysis: Dict[str, Any]
    context_summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "suggestions": [s.to_dict() for s in self.suggestions],
            "analysis": self.analysis,
            "context_summary": self.context_summary
        }


class SuggestionEngine:
    """建议引擎
    
    基于上下文分析，主动为用户提供优化建议。
    """
    
    def __init__(self):
        """初始化建议引擎"""
        self.context_analyzer = ContextAnalyzer()
        
        # 建议优先级配置
        self.priority_config = {
            SuggestionType.VISUAL_ENHANCE: 1,  # 视觉增强优先级最高
            SuggestionType.CONTENT_OPTIMIZE: 2,
            SuggestionType.STRUCTURE_IMPROVE: 3,
            SuggestionType.STYLE_CONSISTENT: 4,
        }
    
    def generate_suggestions(
        self,
        context: Dict[str, Any],
        focus: Optional[str] = None,
        max_suggestions: int = 5
    ) -> SuggestionResult:
        """生成建议
        
        Args:
            context: PPT 上下文
            focus: 关注点（可选）
            max_suggestions: 最大建议数
            
        Returns:
            SuggestionResult: 建议结果
        """
        slides = context.get("slides", [])
        current_slide_data = context.get("current_slide", 0)
        
        # 分析当前幻灯片（支持字典或整数索引）
        current_slide = None
        if isinstance(current_slide_data, dict):
            # 直接传入了幻灯片数据
            current_slide = current_slide_data
        elif isinstance(current_slide_data, int):
            # 传入的是索引
            if 0 <= current_slide_data < len(slides):
                current_slide = slides[current_slide_data]
        
        # 生成建议
        all_suggestions = []
        
        # 1. 基于当前内容的建议
        if current_slide:
            content = current_slide.get("content", "")
            if content:
                content_suggestions = self._generate_content_suggestions(content)
                all_suggestions.extend(content_suggestions)
        
        # 2. 基于整体结构的建议
        structure_suggestions = self._generate_structure_suggestions(slides)
        all_suggestions.extend(structure_suggestions)
        
        # 3. 基于风格一致性的建议
        style_suggestions = self._generate_style_suggestions(slides)
        all_suggestions.extend(style_suggestions)
        
        # 4. 基于关注点的建议
        if focus:
            focus_suggestions = self._generate_focus_suggestions(
                current_slide, focus
            )
            all_suggestions.extend(focus_suggestions)
        
        # 去重和排序
        unique_suggestions = self._deduplicate_suggestions(all_suggestions)
        sorted_suggestions = self._sort_suggestions(unique_suggestions)
        
        # 限制数量
        limited_suggestions = sorted_suggestions[:max_suggestions]
        
        # 生成分析结果
        analysis = self._generate_analysis(current_slide, slides)
        
        # 获取当前幻灯片索引
        current_slide_index = 0
        if isinstance(current_slide_data, int):
            current_slide_index = current_slide_data
        elif isinstance(current_slide_data, dict) and slides:
            # 尝试从slides中找到当前幻灯片的索引
            for i, slide in enumerate(slides):
                if slide == current_slide_data:
                    current_slide_index = i
                    break
        
        # 生成上下文摘要
        context_summary = self._generate_context_summary(slides, current_slide_index)
        
        return SuggestionResult(
            suggestions=limited_suggestions,
            analysis=analysis,
            context_summary=context_summary
        )
    
    def _generate_content_suggestions(self, content: str) -> List[Suggestion]:
        """基于内容生成建议
        
        Args:
            content: 内容文本
            
        Returns:
            List[Suggestion]: 建议列表
        """
        suggestions = []
        
        # 分析内容
        analysis = self.context_analyzer.analyze_content(content)
        
        # 基于内容类型生成建议
        if analysis.content_type == ContentType.DATA_COMPARISON:
            suggestions.append(Suggestion(
                id=str(uuid.uuid4()),
                type=SuggestionType.VISUAL_ENHANCE,
                title="数据可视化建议",
                description="检测到数据对比内容，建议使用柱状图展示",
                confidence=0.9,
                action={
                    "type": "convert_to_chart",
                    "params": {
                        "chart_type": "bar",
                        "data": analysis.entities
                    }
                },
                preview={
                    "chart_type": "bar",
                    "labels": [e.get("name", "") for e in analysis.entities],
                    "data": [e.get("value", 0) for e in analysis.entities]
                },
                priority=self.priority_config[SuggestionType.VISUAL_ENHANCE]
            ))
        
        elif analysis.content_type == ContentType.PERSON_ATTRIBUTES:
            suggestions.append(Suggestion(
                id=str(uuid.uuid4()),
                type=SuggestionType.VISUAL_ENHANCE,
                title="表格展示建议",
                description="检测到人物属性数据，建议转换为表格",
                confidence=0.95,
                action={
                    "type": "convert_to_table",
                    "params": {
                        "columns": ["姓名", "年龄", "城市", "月薪"],
                        "data": analysis.entities
                    }
                },
                preview={
                    "columns": ["姓名", "年龄", "城市", "月薪"],
                    "rows": [list(e.values()) for e in analysis.entities]
                },
                priority=self.priority_config[SuggestionType.VISUAL_ENHANCE]
            ))
        
        elif analysis.content_type == ContentType.PROCESS:
            suggestions.append(Suggestion(
                id=str(uuid.uuid4()),
                type=SuggestionType.VISUAL_ENHANCE,
                title="流程图建议",
                description="检测到流程步骤，建议使用流程图展示",
                confidence=0.85,
                action={
                    "type": "convert_to_flowchart",
                    "params": {
                        "steps": analysis.key_points
                    }
                },
                preview={
                    "type": "flowchart",
                    "steps": analysis.key_points
                },
                priority=self.priority_config[SuggestionType.VISUAL_ENHANCE]
            ))
        
        elif analysis.content_type == ContentType.TIME_SERIES:
            suggestions.append(Suggestion(
                id=str(uuid.uuid4()),
                type=SuggestionType.VISUAL_ENHANCE,
                title="趋势图建议",
                description="检测到时间序列数据，建议使用折线图展示趋势",
                confidence=0.9,
                action={
                    "type": "convert_to_chart",
                    "params": {
                        "chart_type": "line",
                        "data": analysis.entities
                    }
                },
                preview={
                    "chart_type": "line",
                    "labels": [e.get("period", "") for e in analysis.entities],
                    "data": [e.get("value", 0) for e in analysis.entities]
                },
                priority=self.priority_config[SuggestionType.VISUAL_ENHANCE]
            ))
        
        # 基于质量分数的建议
        if analysis.quality_score < 0.6:
            suggestions.append(Suggestion(
                id=str(uuid.uuid4()),
                type=SuggestionType.CONTENT_OPTIMIZE,
                title="内容优化建议",
                description="内容结构可以优化，建议添加更多关键点和数据支撑",
                confidence=0.7,
                action={
                    "type": "optimize_content",
                    "params": {
                        "suggestions": [
                            "添加数据支撑",
                            "优化语言表达",
                            "增加关键点"
                        ]
                    }
                },
                priority=self.priority_config[SuggestionType.CONTENT_OPTIMIZE]
            ))
        
        # 基于关键点数量的建议
        if len(analysis.key_points) > 7:
            suggestions.append(Suggestion(
                id=str(uuid.uuid4()),
                type=SuggestionType.STRUCTURE_IMPROVE,
                title="内容精简建议",
                description=f"当前有{len(analysis.key_points)}个要点，建议精简到5个以内",
                confidence=0.8,
                action={
                    "type": "simplify_content",
                    "params": {
                        "current_points": len(analysis.key_points),
                        "recommended_points": 5
                    }
                },
                priority=self.priority_config[SuggestionType.STRUCTURE_IMPROVE]
            ))
        
        return suggestions
    
    def _generate_structure_suggestions(self, slides: List[Dict[str, Any]]) -> List[Suggestion]:
        """基于结构生成建议
        
        Args:
            slides: 幻灯片列表
            
        Returns:
            List[Suggestion]: 建议列表
        """
        suggestions = []
        
        if not slides:
            return suggestions
        
        # 分析结构
        analysis = self.context_analyzer.analyze_structure(slides)
        
        # 基于缺失章节的建议
        if analysis.missing_sections:
            section_names = {
                "cover": "封面",
                "problem": "问题",
                "solution": "解决方案",
                "summary": "总结"
            }
            
            missing_names = [
                section_names.get(s, s) for s in analysis.missing_sections
            ]
            
            suggestions.append(Suggestion(
                id=str(uuid.uuid4()),
                type=SuggestionType.STRUCTURE_IMPROVE,
                title="结构完整性建议",
                description=f"建议添加以下章节：{', '.join(missing_names)}",
                confidence=0.85,
                action={
                    "type": "add_sections",
                    "params": {
                        "sections": analysis.missing_sections
                    }
                },
                priority=self.priority_config[SuggestionType.STRUCTURE_IMPROVE]
            ))
        
        # 基于重复内容的建议
        if analysis.repeated_content:
            for repeated in analysis.repeated_content:
                suggestions.append(Suggestion(
                    id=str(uuid.uuid4()),
                    type=SuggestionType.STRUCTURE_IMPROVE,
                    title="重复内容检测",
                    description=f"检测到重复内容：{repeated['title']}",
                    confidence=0.9,
                    action={
                        "type": "merge_duplicates",
                        "params": {
                            "title": repeated["title"],
                            "indices": repeated["indices"]
                        }
                    },
                    priority=self.priority_config[SuggestionType.STRUCTURE_IMPROVE]
                ))
        
        # 基于逻辑流程的建议
        if analysis.logical_flow:
            for suggestion_text in analysis.logical_flow:
                suggestions.append(Suggestion(
                    id=str(uuid.uuid4()),
                    type=SuggestionType.STRUCTURE_IMPROVE,
                    title="逻辑流程建议",
                    description=suggestion_text,
                    confidence=0.75,
                    action={
                        "type": "improve_flow",
                        "params": {
                            "suggestion": suggestion_text
                        }
                    },
                    priority=self.priority_config[SuggestionType.STRUCTURE_IMPROVE]
                ))
        
        return suggestions
    
    def _generate_style_suggestions(self, slides: List[Dict[str, Any]]) -> List[Suggestion]:
        """基于风格生成建议
        
        Args:
            slides: 幻灯片列表
            
        Returns:
            List[Suggestion]: 建议列表
        """
        suggestions = []
        
        if not slides:
            return suggestions
        
        # 检查风格一致性
        result = self.context_analyzer.check_style_consistency(slides)
        
        if not result.consistent:
            for issue in result.issues:
                suggestions.append(Suggestion(
                    id=str(uuid.uuid4()),
                    type=SuggestionType.STYLE_CONSISTENT,
                    title=f"风格一致性：{issue['issue']}",
                    description=f"第{issue['slide_index'] + 1}页{issue['issue']}",
                    confidence=0.9,
                    action={
                        "type": "fix_style",
                        "params": {
                            "slide_index": issue["slide_index"],
                            **issue["suggestion"]["params"]
                        }
                    },
                    priority=self.priority_config[SuggestionType.STYLE_CONSISTENT]
                ))
        
        return suggestions
    
    def _generate_focus_suggestions(
        self,
        slide: Optional[Dict[str, Any]],
        focus: str
    ) -> List[Suggestion]:
        """基于关注点生成建议
        
        Args:
            slide: 当前幻灯片
            focus: 关注点
            
        Returns:
            List[Suggestion]: 建议列表
        """
        suggestions = []
        
        if not slide:
            return suggestions
        
        content = slide.get("content", "")
        
        if focus == "visual_enhance":
            # 关注视觉增强
            analysis = self.context_analyzer.analyze_content(content)
            
            if analysis.recommended_visual:
                visual_names = {
                    ContentType.CHART: "图表",
                    ContentType.TABLE: "表格",
                    ContentType.FLOWCHART: "流程图",
                    ContentType.LIST: "列表"
                }
                
                visual_name = visual_names.get(analysis.recommended_visual, "可视化")
                
                suggestions.append(Suggestion(
                    id=str(uuid.uuid4()),
                    type=SuggestionType.VISUAL_ENHANCE,
                    title=f"{visual_name}展示建议",
                    description=f"建议将当前内容转换为{visual_name}展示",
                    confidence=analysis.confidence,
                    action={
                        "type": f"convert_to_{analysis.recommended_visual.value}",
                        "params": {}
                    },
                    priority=self.priority_config[SuggestionType.VISUAL_ENHANCE]
                ))
        
        elif focus == "content_optimize":
            # 关注内容优化
            analysis = self.context_analyzer.analyze_content(content)
            
            if analysis.quality_score < 0.7:
                suggestions.append(Suggestion(
                    id=str(uuid.uuid4()),
                    type=SuggestionType.CONTENT_OPTIMIZE,
                    title="内容质量提升",
                    description="当前内容质量可以进一步提升",
                    confidence=0.8,
                    action={
                        "type": "enhance_content",
                        "params": {
                            "current_score": analysis.quality_score,
                            "target_score": 0.8
                        }
                    },
                    priority=self.priority_config[SuggestionType.CONTENT_OPTIMIZE]
                ))
        
        return suggestions
    
    def _deduplicate_suggestions(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """去重建议
        
        Args:
            suggestions: 建议列表
            
        Returns:
            List[Suggestion]: 去重后的建议列表
        """
        seen = set()
        unique = []
        
        for suggestion in suggestions:
            # 使用类型和标题作为去重键
            key = (suggestion.type, suggestion.title)
            
            if key not in seen:
                seen.add(key)
                unique.append(suggestion)
        
        return unique
    
    def _sort_suggestions(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """排序建议
        
        Args:
            suggestions: 建议列表
            
        Returns:
            List[Suggestion]: 排序后的建议列表
        """
        # 按优先级和置信度排序
        return sorted(
            suggestions,
            key=lambda s: (s.priority, -s.confidence)
        )
    
    def _generate_analysis(
        self,
        current_slide: Optional[Dict[str, Any]],
        slides: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成分析结果
        
        Args:
            current_slide: 当前幻灯片
            slides: 所有幻灯片
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        analysis = {
            "total_slides": len(slides),
            "current_slide_analyzed": current_slide is not None
        }
        
        if current_slide:
            content = current_slide.get("content", "")
            if content:
                content_analysis = self.context_analyzer.analyze_content(content)
                analysis["content_type"] = content_analysis.content_type.value
                analysis["quality_score"] = content_analysis.quality_score
                analysis["key_points_count"] = len(content_analysis.key_points)
        
        if slides:
            structure_analysis = self.context_analyzer.analyze_structure(slides)
            analysis["structure_score"] = structure_analysis.structure_score
            analysis["missing_sections"] = structure_analysis.missing_sections
        
        return analysis
    
    def _generate_context_summary(
        self,
        slides: List[Dict[str, Any]],
        current_slide_index: int
    ) -> Dict[str, Any]:
        """生成上下文摘要
        
        Args:
            slides: 幻灯片列表
            current_slide_index: 当前幻灯片索引
            
        Returns:
            Dict[str, Any]: 上下文摘要
        """
        return {
            "total_slides": len(slides),
            "current_slide": current_slide_index,
            "has_title": any(s.get("title") for s in slides),
            "has_content": any(s.get("content") for s in slides),
            "slide_types": [
                self.context_analyzer._detect_slide_type(
                    s.get("title", ""),
                    s.get("content", "")
                )
                for s in slides
            ]
        }


# 便捷函数
def generate_suggestions(
    context: Dict[str, Any],
    focus: Optional[str] = None,
    max_suggestions: int = 5
) -> SuggestionResult:
    """生成建议（便捷函数）"""
    engine = SuggestionEngine()
    return engine.generate_suggestions(context, focus, max_suggestions)