"""
智能体生成质量评价工具

提供自动评分、质量分析和改进建议功能
"""

import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class QualityDimension(Enum):
    """质量维度枚举"""
    ACCURACY = "accuracy"          # 准确性
    COMPLETENESS = "completeness"  # 完整性
    RELEVANCE = "relevance"        # 相关性
    TIMELINESS = "timeliness"      # 时效性
    ORIGINALITY = "originality"    # 原创性
    FLUENCY = "fluency"            # 流畅性
    PROFESSIONALISM = "professionalism"  # 专业性
    GRAMMAR = "grammar"            # 语法正确性
    CONSISTENCY = "consistency"    # 风格一致性
    LOGICALITY = "logicality"      # 逻辑性
    FORMAT = "format"              # 格式规范
    READABILITY = "readability"    # 可读性
    TONE = "tone"                  # 语气恰当
    STYLE = "style"                # 风格匹配
    CULTURAL = "cultural"          # 文化适应


@dataclass
class EvaluationResult:
    """评价结果数据类"""
    dimension: QualityDimension
    score: float  # 1-5分
    weight: float  # 权重
    feedback: str  # 反馈信息
    suggestions: List[str]  # 改进建议


@dataclass
class QualityReport:
    """质量报告数据类"""
    content: str  # 被评价内容
    scene: str  # 场景类型
    results: List[EvaluationResult]  # 评价结果
    total_score: float  # 总分
    summary: str  # 总结
    improvement_plan: str  # 改进计划


class QualityEvaluator:
    """质量评价器"""
    
    def __init__(self):
        """初始化评价器"""
        self.dimension_weights = {
            QualityDimension.ACCURACY: 0.30,
            QualityDimension.COMPLETENESS: 0.25,
            QualityDimension.RELEVANCE: 0.20,
            QualityDimension.TIMELINESS: 0.15,
            QualityDimension.ORIGINALITY: 0.10,
            QualityDimension.FLUENCY: 0.35,
            QualityDimension.PROFESSIONALISM: 0.30,
            QualityDimension.GRAMMAR: 0.25,
            QualityDimension.CONSISTENCY: 0.10,
            QualityDimension.LOGICALITY: 0.40,
            QualityDimension.FORMAT: 0.30,
            QualityDimension.READABILITY: 0.20,
            QualityDimension.TONE: 0.40,
            QualityDimension.STYLE: 0.30,
            QualityDimension.CULTURAL: 0.20,
        }
        
        # 场景特定权重调整
        self.scene_weights = {
            "business_email": {
                QualityDimension.TONE: 0.50,
                QualityDimension.PROFESSIONALISM: 0.40,
            },
            "academic_paper": {
                QualityDimension.ACCURACY: 0.40,
                QualityDimension.PROFESSIONALISM: 0.35,
            },
            "technical_doc": {
                QualityDimension.ACCURACY: 0.35,
                QualityDimension.READABILITY: 0.30,
            },
            "translation": {
                QualityDimension.ACCURACY: 0.45,
                QualityDimension.FLUENCY: 0.40,
            },
        }
    
    def evaluate_accuracy(self, content: str, reference: str = None) -> EvaluationResult:
        """
        评估准确性
        
        Args:
            content: 被评价内容
            reference: 参考内容（可选）
            
        Returns:
            EvaluationResult: 评价结果
        """
        score = 5.0
        feedback = "内容准确性良好"
        suggestions = []
        
        # 检查数字准确性
        numbers_in_content = re.findall(r'\d+', content)
        if reference:
            numbers_in_ref = re.findall(r'\d+', reference)
            # 比较数字是否一致
            if set(numbers_in_content) != set(numbers_in_ref):
                score -= 1.0
                feedback = "数字信息与参考内容不一致"
                suggestions.append("请核对数字信息的准确性")
        
        # 检查常见错误模式
        error_patterns = [
            (r'(?i)error|错误|失败', "包含负面词汇，可能影响准确性"),
            (r'(?i)maybe|perhaps|可能|也许', "包含不确定词汇，降低准确性"),
            (r'(?i)approximately|大约|左右', "包含模糊词汇，影响准确性"),
        ]
        
        for pattern, desc in error_patterns:
            if re.search(pattern, content):
                score -= 0.5
                suggestions.append(desc)
        
        # 确保分数在1-5范围内
        score = max(1.0, min(5.0, score))
        
        return EvaluationResult(
            dimension=QualityDimension.ACCURACY,
            score=score,
            weight=self.dimension_weights[QualityDimension.ACCURACY],
            feedback=feedback,
            suggestions=suggestions
        )
    
    def evaluate_completeness(self, content: str, requirements: List[str] = None) -> EvaluationResult:
        """
        评估完整性
        
        Args:
            content: 被评价内容
            requirements: 必要信息要求列表
            
        Returns:
            EvaluationResult: 评价结果
        """
        score = 5.0
        feedback = "内容完整性良好"
        suggestions = []
        
        # 检查内容长度
        if len(content) < 50:
            score -= 1.0
            feedback = "内容过短，可能不完整"
            suggestions.append("请增加更多详细信息")
        
        # 检查必要信息
        if requirements:
            missing_requirements = []
            for req in requirements:
                if req.lower() not in content.lower():
                    missing_requirements.append(req)
            
            if missing_requirements:
                score -= len(missing_requirements) * 0.5
                feedback = f"缺少必要信息：{', '.join(missing_requirements)}"
                suggestions.append(f"请补充以下信息：{', '.join(missing_requirements)}")
        
        # 检查结构完整性
        if not re.search(r'[。！？.!?]', content):
            score -= 0.5
            suggestions.append("请添加适当的标点符号")
        
        # 确保分数在1-5范围内
        score = max(1.0, min(5.0, score))
        
        return EvaluationResult(
            dimension=QualityDimension.COMPLETENESS,
            score=score,
            weight=self.dimension_weights[QualityDimension.COMPLETENESS],
            feedback=feedback,
            suggestions=suggestions
        )
    
    def evaluate_fluency(self, content: str) -> EvaluationResult:
        """
        评估流畅性
        
        Args:
            content: 被评价内容
            
        Returns:
            EvaluationResult: 评价结果
        """
        score = 5.0
        feedback = "语言流畅性良好"
        suggestions = []
        
        # 检查句子长度
        sentences = re.split(r'[。！？.!?]', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences:
            avg_length = sum(len(s) for s in sentences) / len(sentences)
            if avg_length > 100:
                score -= 1.0
                feedback = "句子过长，影响流畅性"
                suggestions.append("请将长句拆分为短句")
            elif avg_length < 10:
                score -= 0.5
                feedback = "句子过短，可能不流畅"
                suggestions.append("请适当合并短句")
        
        # 检查重复表达
        words = re.findall(r'[\u4e00-\u9fa5]+', content)
        if words:
            word_count = {}
            for word in words:
                if len(word) > 1:  # 忽略单字词
                    word_count[word] = word_count.get(word, 0) + 1
            
            repeated_words = [word for word, count in word_count.items() if count > 3]
            if repeated_words:
                score -= 0.5
                feedback = f"存在重复表达：{', '.join(repeated_words[:3])}"
                suggestions.append("请使用同义词替换重复表达")
        
        # 检查连接词使用
        connectors = ['因此', '然而', '此外', '另外', '同时', '首先', '其次', '最后']
        connector_count = sum(1 for conn in connectors if conn in content)
        if connector_count < 2:
            score -= 0.5
            suggestions.append("请增加连接词使用，提高逻辑连贯性")
        
        # 确保分数在1-5范围内
        score = max(1.0, min(5.0, score))
        
        return EvaluationResult(
            dimension=QualityDimension.FLUENCY,
            score=score,
            weight=self.dimension_weights[QualityDimension.FLUENCY],
            feedback=feedback,
            suggestions=suggestions
        )
    
    def evaluate_grammar(self, content: str) -> EvaluationResult:
        """
        评估语法正确性
        
        Args:
            content: 被评价内容
            
        Returns:
            EvaluationResult: 评价结果
        """
        score = 5.0
        feedback = "语法正确性良好"
        suggestions = []
        
        # 检查标点符号使用
        punctuation_errors = [
            (r'[，,][，,]+', "逗号重复"),
            (r'[。.][。.]+', "句号重复"),
            (r'[！!][！!]+', "感叹号重复"),
            (r'[？?][？?]+', "问号重复"),
        ]
        
        for pattern, desc in punctuation_errors:
            if re.search(pattern, content):
                score -= 0.5
                suggestions.append(f"请修复{desc}问题")
        
        # 检查空格使用
        if re.search(r'[\u4e00-\u9fa5]\s+[\u4e00-\u9fa5]', content):
            score -= 0.5
            suggestions.append("中文之间不应有空格")
        
        # 检查引号配对
        quotes = ['"', '"', "'", "'", '「', '」', '『', '』']
        for i in range(0, len(quotes), 2):
            open_quote = quotes[i]
            close_quote = quotes[i+1]
            open_count = content.count(open_quote)
            close_count = content.count(close_quote)
            if open_count != close_count:
                score -= 0.5
                suggestions.append(f"引号 {open_quote}{close_quote} 不配对")
        
        # 确保分数在1-5范围内
        score = max(1.0, min(5.0, score))
        
        return EvaluationResult(
            dimension=QualityDimension.GRAMMAR,
            score=score,
            weight=self.dimension_weights[QualityDimension.GRAMMAR],
            feedback=feedback,
            suggestions=suggestions
        )
    
    def evaluate_tone(self, content: str, scene: str) -> EvaluationResult:
        """
        评估语气恰当性
        
        Args:
            content: 被评价内容
            scene: 场景类型
            
        Returns:
            EvaluationResult: 评价结果
        """
        score = 5.0
        feedback = "语气恰当性良好"
        suggestions = []
        
        # 场景特定语气检查
        if scene == "business_email":
            # 商务邮件应正式
            informal_patterns = [
                (r'(?i)hi|hello|hey', "使用非正式称呼"),
                (r'(?i)thanks|thx', "使用非正式感谢"),
                (r'(?i)ok|okay', "使用非正式确认"),
            ]
            
            for pattern, desc in informal_patterns:
                if re.search(pattern, content):
                    score -= 1.0
                    suggestions.append(f"商务邮件中应避免{desc}")
        
        elif scene == "academic_paper":
            # 学术论文应客观
            subjective_patterns = [
                (r'(?i)i think|我认为|我觉得', "使用主观表达"),
                (r'(?i)maybe|perhaps|可能', "使用不确定表达"),
                (r'(?i)very|extremely|非常', "使用过度修饰"),
            ]
            
            for pattern, desc in subjective_patterns:
                if re.search(pattern, content):
                    score -= 1.0
                    suggestions.append(f"学术论文中应避免{desc}")
        
        # 检查礼貌用语
        polite_words = ['请', '您', '谢谢', '感谢', '此致', '敬礼']
        polite_count = sum(1 for word in polite_words if word in content)
        if polite_count < 2:
            score -= 0.5
            suggestions.append("请增加礼貌用语")
        
        # 确保分数在1-5范围内
        score = max(1.0, min(5.0, score))
        
        return EvaluationResult(
            dimension=QualityDimension.TONE,
            score=score,
            weight=self.dimension_weights[QualityDimension.TONE],
            feedback=feedback,
            suggestions=suggestions
        )
    
    def evaluate_content(self, content: str, scene: str, 
                        reference: str = None, 
                        requirements: List[str] = None) -> QualityReport:
        """
        综合评价内容质量
        
        Args:
            content: 被评价内容
            scene: 场景类型
            reference: 参考内容（可选）
            requirements: 必要信息要求列表（可选）
            
        Returns:
            QualityReport: 质量报告
        """
        results = []
        
        # 评估各个维度
        results.append(self.evaluate_accuracy(content, reference))
        results.append(self.evaluate_completeness(content, requirements))
        results.append(self.evaluate_fluency(content))
        results.append(self.evaluate_grammar(content))
        results.append(self.evaluate_tone(content, scene))
        
        # 计算总分
        total_score = 0.0
        for result in results:
            # 根据场景调整权重
            weight = result.weight
            if scene in self.scene_weights:
                if result.dimension in self.scene_weights[scene]:
                    weight = self.scene_weights[scene][result.dimension]
            
            total_score += result.score * weight
        
        # 生成总结
        summary = self._generate_summary(results, total_score)
        
        # 生成改进计划
        improvement_plan = self._generate_improvement_plan(results)
        
        return QualityReport(
            content=content,
            scene=scene,
            results=results,
            total_score=total_score,
            summary=summary,
            improvement_plan=improvement_plan
        )
    
    def _generate_summary(self, results: List[EvaluationResult], total_score: float) -> str:
        """
        生成评价总结
        
        Args:
            results: 评价结果列表
            total_score: 总分
            
        Returns:
            str: 总结文本
        """
        if total_score >= 4.5:
            level = "优秀"
        elif total_score >= 3.5:
            level = "良好"
        elif total_score >= 2.5:
            level = "合格"
        elif total_score >= 1.5:
            level = "需改进"
        else:
            level = "不合格"
        
        # 找出最高和最低分维度
        best_result = max(results, key=lambda x: x.score)
        worst_result = min(results, key=lambda x: x.score)
        
        summary = f"综合评价：{level}（{total_score:.1f}/5.0）\n"
        summary += f"最佳维度：{best_result.dimension.value}（{best_result.score:.1f}分）\n"
        summary += f"待改进维度：{worst_result.dimension.value}（{worst_result.score:.1f}分）"
        
        return summary
    
    def _generate_improvement_plan(self, results: List[EvaluationResult]) -> str:
        """
        生成改进计划
        
        Args:
            results: 评价结果列表
            
        Returns:
            str: 改进计划文本
        """
        plan = "改进计划：\n"
        
        # 按分数排序，优先改进低分维度
        sorted_results = sorted(results, key=lambda x: x.score)
        
        for i, result in enumerate(sorted_results, 1):
            if result.score < 4.0:  # 只改进低于4分的维度
                plan += f"{i}. {result.dimension.value}（{result.score:.1f}分）：\n"
                for suggestion in result.suggestions:
                    plan += f"   - {suggestion}\n"
        
        return plan


class PromptOptimizer:
    """Prompt优化器"""
    
    def __init__(self):
        """初始化优化器"""
        self.optimization_history = []
    
    def analyze_evaluation(self, report: QualityReport) -> Dict[str, Any]:
        """
        分析评价结果，生成优化建议
        
        Args:
            report: 质量报告
            
        Returns:
            Dict: 优化建议
        """
        suggestions = {}
        
        for result in report.results:
            if result.score < 4.0:
                suggestions[result.dimension.value] = {
                    "current_score": result.score,
                    "target_score": 4.5,
                    "suggestions": result.suggestions,
                    "priority": "high" if result.score < 3.0 else "medium"
                }
        
        return suggestions
    
    def generate_prompt_improvements(self, current_prompt: str, 
                                   suggestions: Dict[str, Any]) -> str:
        """
        生成改进后的prompt
        
        Args:
            current_prompt: 当前prompt
            suggestions: 优化建议
            
        Returns:
            str: 改进后的prompt
        """
        improved_prompt = current_prompt
        
        # 根据建议添加指导
        if "fluency" in suggestions:
            improved_prompt += "\n\n## 语言要求\n- 使用简洁明了的语言\n- 避免冗长复杂的句子\n- 使用连接词增强连贯性"
        
        if "tone" in suggestions:
            improved_prompt += "\n\n## 语气要求\n- 保持专业正式的语气\n- 使用礼貌用语\n- 避免过于随意的表达"
        
        if "accuracy" in suggestions:
            improved_prompt += "\n\n## 准确性要求\n- 确保所有信息准确无误\n- 核对数字和数据\n- 避免模糊不确定的表达"
        
        if "completeness" in suggestions:
            improved_prompt += "\n\n## 完整性要求\n- 包含所有必要信息\n- 确保内容完整无遗漏\n- 提供充分的细节"
        
        return improved_prompt
    
    def optimize_prompt(self, current_prompt: str, 
                       evaluation_report: QualityReport) -> str:
        """
        优化prompt
        
        Args:
            current_prompt: 当前prompt
            evaluation_report: 评价报告
            
        Returns:
            str: 优化后的prompt
        """
        # 分析评价结果
        suggestions = self.analyze_evaluation(evaluation_report)
        
        # 生成改进后的prompt
        improved_prompt = self.generate_prompt_improvements(current_prompt, suggestions)
        
        # 记录优化历史
        self.optimization_history.append({
            "original_prompt": current_prompt,
            "improved_prompt": improved_prompt,
            "suggestions": suggestions,
            "evaluation_score": evaluation_report.total_score
        })
        
        return improved_prompt


# 创建全局评价器实例
quality_evaluator = QualityEvaluator()
prompt_optimizer = PromptOptimizer()


def evaluate_generation_quality(content: str, scene: str, 
                               reference: str = None, 
                               requirements: List[str] = None) -> QualityReport:
    """
    评估生成内容质量
    
    Args:
        content: 生成的内容
        scene: 场景类型
        reference: 参考内容（可选）
        requirements: 必要信息要求列表（可选）
        
    Returns:
        QualityReport: 质量报告
    """
    return quality_evaluator.evaluate_content(content, scene, reference, requirements)


def optimize_prompt_template(current_prompt: str, 
                            evaluation_report: QualityReport) -> str:
    """
    优化prompt模板
    
    Args:
        current_prompt: 当前prompt模板
        evaluation_report: 评价报告
        
    Returns:
        str: 优化后的prompt模板
    """
    return prompt_optimizer.optimize_prompt(current_prompt, evaluation_report)


# 工具注册信息
TOOL_INFO = {
    "name": "quality_evaluation",
    "description": "智能体生成质量评价工具",
    "parameters": {
        "content": {
            "type": "string",
            "description": "被评价的内容",
            "required": True
        },
        "scene": {
            "type": "string",
            "description": "场景类型（business_email, academic_paper, technical_doc, translation）",
            "required": True
        },
        "reference": {
            "type": "string",
            "description": "参考内容（可选）",
            "required": False
        },
        "requirements": {
            "type": "array",
            "description": "必要信息要求列表（可选）",
            "required": False
        }
    }
}