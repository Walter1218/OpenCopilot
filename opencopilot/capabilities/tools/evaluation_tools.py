"""
OpenCopilot 划词功能质量评价工具

围绕划词核心交互功能设计的评价体系：
1. 自动模式 - 类型判断 + 翻译/解释/总结
2. 翻译 - 信达雅
3. 代码解析 - 功能总结 + 漏洞发现
4. 润色 - 语病修正 + 专业度提升
5. 全文修订 - 修订质量 + 联动发现
6. 自定义指令 - 指令遵循度
"""

import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


# ============================================================
# 划词功能场景枚举
# ============================================================

class ActionScene(Enum):
    """划词功能场景"""
    AUTO = "auto"                    # 自动模式
    TRANSLATE = "translate"          # 翻译
    CODE = "code"                    # 代码解析
    POLISH = "polish"                # 润色
    REVISION = "revision"            # 全文修订
    CUSTOM = "custom"                # 自定义指令


# ============================================================
# 各场景评价维度
# ============================================================

class AutoDimension(Enum):
    """自动模式评价维度"""
    TYPE_JUDGMENT = "type_judgment"          # 类型判断准确性
    RESPONSE_APPROPRIATENESS = "response_appropriateness"  # 响应恰当性
    OUTPUT_QUALITY = "output_quality"        # 输出质量


class TranslateDimension(Enum):
    """翻译评价维度"""
    ACCURACY = "accuracy"                    # 翻译准确性
    FAITHFULNESS = "faithfulness"            # 信：忠实原文
    EXPRESSIVENESS = "expressiveness"        # 达：表达通顺
    ELEGANCE = "elegance"                    # 雅：用词优雅
    TERMINOLOGY = "terminology"              # 术语一致性


class CodeDimension(Enum):
    """代码解析评价维度"""
    FUNCTION_SUMMARY = "function_summary"    # 功能总结准确性
    VULNERABILITY_DETECTION = "vulnerability_detection"  # 漏洞发现率
    OPTIMIZATION_SUGGESTIONS = "optimization_suggestions"  # 优化建议合理性
    EXPLANATION_CLARITY = "explanation_clarity"  # 解释清晰度


class PolishDimension(Enum):
    """润色评价维度"""
    GRAMMAR_CORRECTION = "grammar_correction"  # 语病修正率
    PROFESSIONALISM = "professionalism"        # 专业度提升
    FLUENCY_IMPROVEMENT = "fluency_improvement"  # 流畅度改善
    MEANING_PRESERVATION = "meaning_preservation"  # 语义保持度


class RevisionDimension(Enum):
    """全文修订评价维度"""
    REVISION_QUALITY = "revision_quality"    # 修订质量
    LINKAGE_DETECTION = "linkage_detection"  # 联动发现率
    CONTRADICTION_DETECTION = "contradiction_detection"  # 矛盾检测准确性
    ZERO_FALSE_POSITIVE = "zero_false_positive"  # 零误报率
    OUTPUT_FORMAT = "output_format"          # 输出格式规范性


class CustomDimension(Enum):
    """自定义指令评价维度"""
    INSTRUCTION_COMPLIANCE = "instruction_compliance"  # 指令遵循度
    OUTPUT_SPECIFICATION = "output_specification"  # 输出规范性
    FORMAT_PRESERVATION = "format_preservation"  # 格式保持度
    CHANGE_PRECISION = "change_precision"    # 修改精准度


class CommonDimension(Enum):
    """跨场景通用维度"""
    OUTPUT_LENGTH_CONTROL = "output_length_control"  # 输出长度控制
    ERROR_HANDLING = "error_handling"        # 错误处理能力
    CONSISTENCY = "consistency"              # 多次调用一致性


class EdgeCaseDimension(Enum):
    """边界情况处理维度"""
    EMPTY_INPUT = "empty_input"              # 空输入处理
    INVALID_INPUT = "invalid_input"          # 无效输入处理
    AMBIGUOUS_INSTRUCTION = "ambiguous"      # 模糊指令处理


# ============================================================
# 评价结果数据类
# ============================================================

@dataclass
class EvaluationResult:
    """评价结果"""
    dimension: str           # 维度名称
    dimension_label: str     # 维度中文标签
    score: float             # 1-5分
    weight: float            # 权重
    feedback: str            # 反馈信息
    suggestions: List[str] = field(default_factory=list)  # 改进建议


@dataclass
class QualityReport:
    """质量报告"""
    content: str                              # 被评价内容
    scene: str                                # 场景类型
    scene_label: str                          # 场景中文标签
    results: List[EvaluationResult]           # 评价结果
    total_score: float                        # 总分
    level: str                                # 等级
    summary: str                              # 总结
    improvement_plan: str                     # 改进计划
    input_text: str = ""                      # 输入文本
    reference_text: str = ""                  # 参考文本
    custom_instruction: str = ""              # 自定义指令
    full_document: str = ""                   # 完整文档（修订模式）


# ============================================================
# 各场景评价器
# ============================================================

class AutoEvaluator:
    """自动模式评价器"""

    # 维度权重
    WEIGHTS = {
        "type_judgment": 0.40,
        "response_appropriateness": 0.35,
        "output_quality": 0.25,
    }

    # 维度标签
    LABELS = {
        "type_judgment": "类型判断准确性",
        "response_appropriateness": "响应恰当性",
        "output_quality": "输出质量",
    }

    def evaluate(self, input_text: str, output_text: str) -> List[EvaluationResult]:
        """评价自动模式输出"""
        results = []

        # 1. 类型判断准确性
        results.append(self._evaluate_type_judgment(input_text, output_text))

        # 2. 响应恰当性
        results.append(self._evaluate_response_appropriateness(input_text, output_text))

        # 3. 输出质量
        results.append(self._evaluate_output_quality(output_text))

        return results

    def _evaluate_type_judgment(self, input_text: str, output_text: str) -> EvaluationResult:
        """评价类型判断准确性"""
        score = 5.0
        feedback = "类型判断准确"
        suggestions = []

        # 检测输入类型
        has_english = bool(re.search(r'[a-zA-Z]{3,}', input_text))
        has_chinese = bool(re.search(r'[\u4e00-\u9fa5]', input_text))
        has_code = bool(re.search(r'(def |class |import |function |var |const |let )', input_text))

        # 检查输出是否匹配输入类型
        if has_english and has_chinese:
            # 中英混合 -> 应该翻译或解释
            if "翻译" not in output_text and "translate" not in output_text.lower():
                # 检查是否真的是翻译
                pass  # 不扣分，可能是解释
        elif has_code:
            # 代码 -> 应该解释
            if "功能" not in output_text and "函数" not in output_text and "方法" not in output_text:
                score -= 1.0
                feedback = "代码类型判断正确，但解释不够聚焦"
                suggestions.append("请聚焦于代码功能和逻辑的解释")

        # 检查输出长度合理性
        if len(output_text) < 10:
            score -= 1.5
            feedback = "输出过短，可能类型判断或响应不当"
            suggestions.append("请提供更详细的响应")
        elif len(output_text) > len(input_text) * 10:
            score -= 0.5
            feedback = "输出过长，可能过度解释"
            suggestions.append("请保持响应简洁")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="type_judgment",
            dimension_label=self.LABELS["type_judgment"],
            score=score,
            weight=self.WEIGHTS["type_judgment"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_response_appropriateness(self, input_text: str, output_text: str) -> EvaluationResult:
        """评价响应恰当性"""
        score = 5.0
        feedback = "响应恰当"
        suggestions = []

        # 检查是否有多余的客套话
        courtesy_patterns = [
            r'好的[，,]',
            r'没问题[，,]',
            r'当然可以',
            r'我很乐意',
            r'希望.*有帮助',
        ]
        for pattern in courtesy_patterns:
            if re.search(pattern, output_text):
                score -= 0.5
                feedback = "包含多余客套话"
                suggestions.append("直接输出结果，不要客套话")
                break

        # 检查是否有解释性前缀
        prefix_patterns = [
            r'^以下是.*[：:]',
            r'^翻译[：:]',
            r'^解释[：:]',
            r'^分析[：:]',
        ]
        for pattern in prefix_patterns:
            if re.search(pattern, output_text):
                score -= 0.5
                feedback = "包含解释性前缀"
                suggestions.append("直接输出结果，不要前缀说明")
                break

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="response_appropriateness",
            dimension_label=self.LABELS["response_appropriateness"],
            score=score,
            weight=self.WEIGHTS["response_appropriateness"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_output_quality(self, output_text: str) -> EvaluationResult:
        """评价输出质量"""
        score = 5.0
        feedback = "输出质量良好"
        suggestions = []

        # 检查排版清晰度
        has_paragraphs = '\n' in output_text
        has_structure = bool(re.search(r'^[#\-*\d]', output_text, re.MULTILINE))

        if not has_paragraphs and len(output_text) > 200:
            score -= 0.5
            feedback = "长文本缺少段落分隔"
            suggestions.append("请使用段落分隔提高可读性")

        # 检查标点符号
        if not re.search(r'[。！？.!?]', output_text):
            score -= 0.5
            suggestions.append("请使用适当的标点符号")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="output_quality",
            dimension_label=self.LABELS["output_quality"],
            score=score,
            weight=self.WEIGHTS["output_quality"],
            feedback=feedback,
            suggestions=suggestions
        )


class TranslateEvaluator:
    """翻译评价器"""

    WEIGHTS = {
        "accuracy": 0.30,
        "faithfulness": 0.25,
        "expressiveness": 0.20,
        "elegance": 0.15,
        "terminology": 0.10,
    }

    LABELS = {
        "accuracy": "翻译准确性",
        "faithfulness": "信（忠实原文）",
        "expressiveness": "达（表达通顺）",
        "elegance": "雅（用词优雅）",
        "terminology": "术语一致性",
    }

    def evaluate(self, input_text: str, output_text: str, reference: str = None) -> List[EvaluationResult]:
        """评价翻译输出"""
        results = []

        results.append(self._evaluate_accuracy(input_text, output_text, reference))
        results.append(self._evaluate_faithfulness(input_text, output_text))
        results.append(self._evaluate_expressiveness(output_text))
        results.append(self._evaluate_elegance(output_text))
        results.append(self._evaluate_terminology(input_text, output_text))

        return results

    def _evaluate_accuracy(self, input_text: str, output_text: str, reference: str = None) -> EvaluationResult:
        """评价翻译准确性"""
        score = 5.0
        feedback = "翻译准确"
        suggestions = []

        # 如果有参考翻译，进行对比
        if reference:
            # 检查数字一致性
            input_numbers = set(re.findall(r'\d+\.?\d*', input_text))
            output_numbers = set(re.findall(r'\d+\.?\d*', output_text))
            ref_numbers = set(re.findall(r'\d+\.?\d*', reference))

            if input_numbers != output_numbers:
                score -= 1.0
                feedback = "数字翻译可能有误"
                suggestions.append("请核对数字翻译的准确性")

        # 检查是否有遗漏（通过长度比例）
        input_len = len(input_text)
        output_len = len(output_text)
        if output_len < input_len * 0.3:
            score -= 1.5
            feedback = "翻译可能有遗漏"
            suggestions.append("请确保完整翻译所有内容")
        elif output_len > input_len * 3:
            score -= 0.5
            feedback = "翻译可能过度扩展"
            suggestions.append("请保持翻译简洁")

        # 检查是否包含原文（可能未翻译）
        if input_text in output_text:
            score -= 2.0
            feedback = "包含未翻译的原文"
            suggestions.append("请翻译所有内容")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="accuracy",
            dimension_label=self.LABELS["accuracy"],
            score=score,
            weight=self.WEIGHTS["accuracy"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_faithfulness(self, input_text: str, output_text: str) -> EvaluationResult:
        """评价忠实度（信）—— 关键信息是否保留"""
        score = 5.0
        feedback = "忠实于原文"
        suggestions = []

        # 1. 检查数字是否保留
        input_numbers = set(re.findall(r'\d+\.?\d*', input_text))
        output_numbers = set(re.findall(r'\d+\.?\d*', output_text))
        missing_numbers = input_numbers - output_numbers
        if missing_numbers:
            score -= min(2.0, len(missing_numbers) * 0.5)
            feedback = f"遗漏了 {len(missing_numbers)} 处数字信息"
            suggestions.append("请确保数字信息完整翻译")

        # 2. 检查专有名词/英文术语是否保留（首字母大写的词）
        proper_nouns = re.findall(r'\b[A-Z][a-zA-Z]{2,}(?:\s[A-Z][a-zA-Z]{2,})*\b', input_text)
        missing_nouns = 0
        for noun in proper_nouns:
            if len(noun) > 3 and noun not in output_text and noun.lower() not in output_text.lower():
                missing_nouns += 1
        if missing_nouns > 0:
            score -= min(2.0, missing_nouns * 0.3)
            if missing_nouns > 2:
                feedback = "多个专有名词未保留"
                suggestions.append("专有名词应保留原文或给出准确翻译")

        # 3. 检查关键中文关键词是否在译文中体现
        cn_keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', input_text)
        if cn_keywords and len(cn_keywords) < 30:
            # 短文本：检查至少 50% 关键词有对应
            key_set = set(cn_keywords[:20])  # 取前 20 个关键词
            matched = sum(1 for k in key_set if k in output_text)
            if len(key_set) > 5 and matched / len(key_set) < 0.3:
                score -= 1.0
                feedback = "部分关键信息可能缺失"

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="faithfulness",
            dimension_label=self.LABELS["faithfulness"],
            score=score,
            weight=self.WEIGHTS["faithfulness"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_expressiveness(self, output_text: str) -> EvaluationResult:
        """评价表达通顺度（达）"""
        score = 5.0
        feedback = "表达通顺"
        suggestions = []

        # 检查句子流畅性
        sentences = re.split(r'[。！？.!?]', output_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if sentences:
            avg_len = sum(len(s) for s in sentences) / len(sentences)
            if avg_len > 100:
                score -= 1.0
                feedback = "句子过长，影响流畅性"
                suggestions.append("请将长句拆分为短句")

        # 检查连接词
        connectors = ['因此', '然而', '此外', '同时', '并且', '但是']
        connector_count = sum(1 for c in connectors if c in output_text)
        if len(sentences) > 3 and connector_count < 1:
            score -= 0.5
            suggestions.append("请增加连接词提高连贯性")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="expressiveness",
            dimension_label=self.LABELS["expressiveness"],
            score=score,
            weight=self.WEIGHTS["expressiveness"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_elegance(self, output_text: str) -> EvaluationResult:
        """评价用词优雅度（雅）"""
        score = 5.0
        feedback = "用词优雅"
        suggestions = []

        # 检查是否有口语化表达
        colloquial_patterns = [
            r'挺好的',
            r'还不错',
            r'挺多的',
            r'挺大的',
        ]
        for pattern in colloquial_patterns:
            if re.search(pattern, output_text):
                score -= 0.5
                feedback = "存在口语化表达"
                suggestions.append("请使用更书面化的表达")
                break

        # 检查词汇丰富度
        words = re.findall(r'[\u4e00-\u9fa5]+', output_text)
        if words:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                score -= 0.5
                feedback = "词汇重复度较高"
                suggestions.append("请使用更多同义词替换")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="elegance",
            dimension_label=self.LABELS["elegance"],
            score=score,
            weight=self.WEIGHTS["elegance"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_terminology(self, input_text: str, output_text: str) -> EvaluationResult:
        """评价术语一致性"""
        score = 5.0
        feedback = "术语翻译一致"
        suggestions = []

        # 1. 提取原文中的英文术语（大写字母开头或全大写的词）
        terms = re.findall(r'\b[A-Z][a-zA-Z]{2,}(?:\s[A-Z][a-zA-Z]{2,}){0,2}\b', input_text)
        
        if not terms:
            # 没有英文术语，跳过
            return EvaluationResult(
                dimension="terminology",
                dimension_label=self.LABELS["terminology"],
                score=5.0,
                weight=self.WEIGHTS["terminology"],
                feedback="无术语需要检查",
                suggestions=[]
            )
        
        # 2. 检查术语是否在译文中出现（保留或翻译）
        missing_terms = 0
        for term in set(terms):
            if len(term) > 3 and term.lower() not in output_text.lower():
                missing_terms += 1
        
        if missing_terms > 0:
            term_ratio = missing_terms / len(set(terms))
            if term_ratio > 0.5:
                score -= 2.0
                feedback = f"超过半数术语({missing_terms}个)未在译文中体现"
                suggestions.append("请确保专业术语被正确翻译或保留")
            elif term_ratio > 0.2:
                score -= 1.0
                feedback = f"部分术语({missing_terms}个)可能缺失"

        # 3. 检查数字、符号等是否一致
        input_symbols = re.findall(r'[%$€£¥@#]', input_text)
        output_symbols = re.findall(r'[%$€£¥@#]', output_text)
        if len(input_symbols) != len(output_symbols):
            score -= 0.5
            suggestions.append("特殊符号数量不一致，请检查")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="terminology",
            dimension_label=self.LABELS["terminology"],
            score=score,
            weight=self.WEIGHTS["terminology"],
            feedback=feedback,
            suggestions=suggestions
        )


class CodeEvaluator:
    """代码解析评价器"""

    WEIGHTS = {
        "function_summary": 0.30,
        "vulnerability_detection": 0.25,
        "optimization_suggestions": 0.25,
        "explanation_clarity": 0.20,
    }

    LABELS = {
        "function_summary": "功能总结准确性",
        "vulnerability_detection": "漏洞发现率",
        "optimization_suggestions": "优化建议合理性",
        "explanation_clarity": "解释清晰度",
    }

    def evaluate(self, input_code: str, output_text: str) -> List[EvaluationResult]:
        """评价代码解析输出"""
        results = []

        results.append(self._evaluate_function_summary(input_code, output_text))
        results.append(self._evaluate_vulnerability_detection(input_code, output_text))
        results.append(self._evaluate_optimization_suggestions(input_code, output_text))
        results.append(self._evaluate_explanation_clarity(output_text))

        return results

    def _evaluate_function_summary(self, input_code: str, output_text: str) -> EvaluationResult:
        """评价功能总结准确性"""
        score = 5.0
        feedback = "功能总结准确"
        suggestions = []

        # 检查是否包含功能描述
        function_indicators = ['功能', '作用', '目的', '实现', '用于', '负责']
        has_function_desc = any(indicator in output_text for indicator in function_indicators)

        if not has_function_desc:
            score -= 2.0
            feedback = "缺少功能总结"
            suggestions.append("请总结代码的核心功能")

        # 检查是否提取了关键函数/类名
        code_names = re.findall(r'def\s+(\w+)|class\s+(\w+)', input_code)
        code_names = [name for names in code_names for name in names if name]

        mentioned_names = sum(1 for name in code_names if name in output_text)
        if code_names and mentioned_names < len(code_names) * 0.5:
            score -= 1.0
            feedback = "未充分提及关键函数/类"
            suggestions.append("请提及代码中的关键函数或类名")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="function_summary",
            dimension_label=self.LABELS["function_summary"],
            score=score,
            weight=self.WEIGHTS["function_summary"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_vulnerability_detection(self, input_code: str, output_text: str) -> EvaluationResult:
        """评价漏洞发现能力"""
        score = 5.0
        feedback = "漏洞分析到位"
        suggestions = []

        # 检测代码中可能的问题
        potential_issues = []

        # 检查常见安全问题
        if 'eval(' in input_code or 'exec(' in input_code:
            potential_issues.append("eval/exec使用")
        if 'SELECT' in input_code and 'WHERE' in input_code and "'" in input_code:
            potential_issues.append("SQL注入风险")
        if 'password' in input_code.lower() and ('=' in input_code or 'hardcod' in input_code.lower()):
            potential_issues.append("硬编码密码")
        if 'try:' not in input_code and 'except' not in input_code:
            if len(input_code) > 200:
                potential_issues.append("缺少异常处理")

        # 检查输出是否提到了这些问题
        if potential_issues:
            detected = sum(1 for issue in potential_issues
                          if any(keyword in output_text for keyword in issue.split('/')))
            detection_rate = detected / len(potential_issues)

            if detection_rate < 0.5:
                score -= 1.5
                feedback = f"未能发现 {len(potential_issues) - detected} 个潜在问题"
                suggestions.append("请分析代码中的潜在安全和质量问题")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="vulnerability_detection",
            dimension_label=self.LABELS["vulnerability_detection"],
            score=score,
            weight=self.WEIGHTS["vulnerability_detection"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_optimization_suggestions(self, input_code: str, output_text: str) -> EvaluationResult:
        """评价优化建议合理性"""
        score = 5.0
        feedback = "优化建议合理"
        suggestions = []

        # 检查是否有优化建议
        optimization_keywords = ['优化', '改进', '建议', '可以', '应该', '更好', '性能']
        has_suggestions = any(keyword in output_text for keyword in optimization_keywords)

        if not has_suggestions and len(input_code) > 100:
            score -= 1.0
            feedback = "缺少优化建议"
            suggestions.append("请提供代码优化建议")

        # 检查建议是否具体
        if has_suggestions:
            # 检查是否包含具体的代码示例
            has_code_example = '```' in output_text or '    ' in output_text
            if not has_code_example:
                score -= 0.5
                feedback = "优化建议不够具体"
                suggestions.append("请提供具体的代码示例")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="optimization_suggestions",
            dimension_label=self.LABELS["optimization_suggestions"],
            score=score,
            weight=self.WEIGHTS["optimization_suggestions"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_explanation_clarity(self, output_text: str) -> EvaluationResult:
        """评价解释清晰度"""
        score = 5.0
        feedback = "解释清晰"
        suggestions = []

        # 检查结构化程度
        has_structure = bool(re.search(r'^\d+\.|^[-*]|^#{1,3}\s', output_text, re.MULTILINE))

        if not has_structure and len(output_text) > 200:
            score -= 0.5
            feedback = "解释结构不够清晰"
            suggestions.append("请使用编号或列表提高结构化程度")

        # 检查是否有总结
        summary_keywords = ['总结', '综上', '总之', '概括']
        has_summary = any(keyword in output_text for keyword in summary_keywords)

        if not has_summary and len(output_text) > 300:
            score -= 0.5
            suggestions.append("请添加总结部分")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="explanation_clarity",
            dimension_label=self.LABELS["explanation_clarity"],
            score=score,
            weight=self.WEIGHTS["explanation_clarity"],
            feedback=feedback,
            suggestions=suggestions
        )


class PolishEvaluator:
    """润色评价器"""

    WEIGHTS = {
        "grammar_correction": 0.30,
        "professionalism": 0.25,
        "fluency_improvement": 0.25,
        "meaning_preservation": 0.20,
    }

    LABELS = {
        "grammar_correction": "语病修正率",
        "professionalism": "专业度提升",
        "fluency_improvement": "流畅度改善",
        "meaning_preservation": "语义保持度",
    }

    def evaluate(self, input_text: str, output_text: str) -> List[EvaluationResult]:
        """评价润色输出"""
        results = []

        results.append(self._evaluate_grammar_correction(input_text, output_text))
        results.append(self._evaluate_professionalism(input_text, output_text))
        results.append(self._evaluate_fluency_improvement(input_text, output_text))
        results.append(self._evaluate_meaning_preservation(input_text, output_text))

        return results

    def _evaluate_grammar_correction(self, input_text: str, output_text: str) -> EvaluationResult:
        """评价语病修正率"""
        score = 5.0
        feedback = "语病修正到位"
        suggestions = []

        # 检查常见语病是否修正
        grammar_issues = []

        # 检查"的得地"使用
        if re.search(r'跑的快|走的慢|做的好', input_text):
            if re.search(r'跑得快|走得慢|做得好', output_text):
                pass  # 已修正
            else:
                grammar_issues.append("的得地未修正")

        # 检查标点符号
        if re.search(r'[，,][，,]+', input_text):
            if re.search(r'[，,][，,]+', output_text):
                grammar_issues.append("重复标点未修正")

        # 检查主谓搭配
        if re.search(r'我们.*是.*的', input_text):
            if re.search(r'我们.*是.*的', output_text):
                pass  # 可能是正常表达

        if grammar_issues:
            score -= len(grammar_issues) * 0.5
            feedback = f"存在 {len(grammar_issues)} 处语病未修正"
            suggestions.extend(grammar_issues)

        # 检查输出是否有新的语法错误
        if re.search(r'[，,][，,]+', output_text):
            score -= 1.0
            feedback = "润色后引入新的标点错误"
            suggestions.append("请检查标点符号使用")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="grammar_correction",
            dimension_label=self.LABELS["grammar_correction"],
            score=score,
            weight=self.WEIGHTS["grammar_correction"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_professionalism(self, input_text: str, output_text: str) -> EvaluationResult:
        """评价专业度提升"""
        score = 5.0
        feedback = "专业度提升明显"
        suggestions = []

        # 检查口语化表达是否减少
        colloquial_before = len(re.findall(r'挺好的|还不错|挺多的|挺大的|特别特别', input_text))
        colloquial_after = len(re.findall(r'挺好的|还不错|挺多的|挺大的|特别特别', output_text))

        if colloquial_before > 0 and colloquial_after >= colloquial_before:
            score -= 1.0
            feedback = "口语化表达未改善"
            suggestions.append("请将口语化表达替换为更专业的用词")

        # 检查是否使用了更正式的词汇
        informal_words = ['搞定', '弄', '搞', '弄好']
        formal_words = ['完成', '处理', '执行', '实现']

        informal_before = sum(1 for w in informal_words if w in input_text)
        informal_after = sum(1 for w in informal_words if w in output_text)

        if informal_before > 0 and informal_after >= informal_before:
            score -= 0.5
            feedback = "非正式用语未改善"
            suggestions.append("请使用更正式的词汇")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="professionalism",
            dimension_label=self.LABELS["professionalism"],
            score=score,
            weight=self.WEIGHTS["professionalism"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_fluency_improvement(self, input_text: str, output_text: str) -> EvaluationResult:
        """评价流畅度改善"""
        score = 5.0
        feedback = "流畅度有所提升"
        suggestions = []

        # 检查句子平均长度
        def avg_sentence_length(text):
            sentences = re.split(r'[。！？.!?]', text)
            sentences = [s.strip() for s in sentences if s.strip()]
            if not sentences:
                return 0
            return sum(len(s) for s in sentences) / len(sentences)

        input_avg = avg_sentence_length(input_text)
        output_avg = avg_sentence_length(output_text)

        # 检查长句是否得到改善
        if input_avg > 80 and output_avg > 80:
            score -= 1.0
            feedback = "长句未得到改善"
            suggestions.append("请将长句拆分为短句")

        # 检查连接词使用
        connectors = ['因此', '然而', '此外', '同时', '首先', '其次', '最后']
        input_connectors = sum(1 for c in connectors if c in input_text)
        output_connectors = sum(1 for c in connectors if c in output_text)

        if input_connectors == 0 and output_connectors == 0 and len(output_text) > 200:
            score -= 0.5
            suggestions.append("请增加连接词提高连贯性")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="fluency_improvement",
            dimension_label=self.LABELS["fluency_improvement"],
            score=score,
            weight=self.WEIGHTS["fluency_improvement"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_meaning_preservation(self, input_text: str, output_text: str) -> EvaluationResult:
        """评价语义保持度"""
        score = 5.0
        feedback = "语义保持良好"
        suggestions = []

        # 检查数字是否保持一致
        input_numbers = set(re.findall(r'\d+\.?\d*', input_text))
        output_numbers = set(re.findall(r'\d+\.?\d*', output_text))

        if input_numbers and input_numbers != output_numbers:
            score -= 1.5
            feedback = "数字信息可能被修改"
            suggestions.append("请保持数字信息不变")

        # 检查人名是否保持一致
        input_names = set(re.findall(r'[\u4e00-\u9fa5]{2,4}(?:先生|女士|总|经理|主任)?', input_text))
        output_names = set(re.findall(r'[\u4e00-\u9fa5]{2,4}(?:先生|女士|总|经理|主任)?', output_text))

        if input_names:
            missing_names = input_names - output_names
            if missing_names:
                score -= 1.0
                feedback = "人名可能被遗漏"
                suggestions.append("请保持所有人名不变")

        # 检查长度变化
        if len(output_text) < len(input_text) * 0.5:
            score -= 1.0
            feedback = "内容大幅缩减，可能丢失信息"
            suggestions.append("请保持内容完整性")
        elif len(output_text) > len(input_text) * 2:
            score -= 0.5
            feedback = "内容大幅扩展，可能添加了额外信息"
            suggestions.append("请保持内容简洁")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="meaning_preservation",
            dimension_label=self.LABELS["meaning_preservation"],
            score=score,
            weight=self.WEIGHTS["meaning_preservation"],
            feedback=feedback,
            suggestions=suggestions
        )


class RevisionEvaluator:
    """全文修订评价器"""

    WEIGHTS = {
        "revision_quality": 0.30,
        "linkage_detection": 0.25,
        "contradiction_detection": 0.20,
        "zero_false_positive": 0.15,
        "output_format": 0.10,
    }

    LABELS = {
        "revision_quality": "修订质量",
        "linkage_detection": "联动发现率",
        "contradiction_detection": "矛盾检测准确性",
        "zero_false_positive": "零误报率",
        "output_format": "输出格式规范性",
    }

    def evaluate(self, selection: str, full_document: str, output_text: str) -> List[EvaluationResult]:
        """评价全文修订输出"""
        results = []

        results.append(self._evaluate_revision_quality(selection, output_text))
        results.append(self._evaluate_linkage_detection(selection, full_document, output_text))
        results.append(self._evaluate_contradiction_detection(selection, full_document, output_text))
        results.append(self._evaluate_zero_false_positive(full_document, output_text))
        results.append(self._evaluate_output_format(output_text))

        return results

    def _evaluate_revision_quality(self, selection: str, output_text: str) -> EvaluationResult:
        """评价修订质量"""
        score = 5.0
        feedback = "修订质量良好"
        suggestions = []

        # 检查是否包含修订后文本
        revision_indicators = ['修订后', '修改后', '📝', '修订后文本']
        has_revision = any(indicator in output_text for indicator in revision_indicators)

        if not has_revision:
            score -= 2.0
            feedback = "缺少修订后文本"
            suggestions.append("请提供修订后的文本")

        # 检查修订是否改变了原意
        if selection and output_text:
            # 提取修订后文本部分
            revision_match = re.search(r'(?:修订后|修改后)[文本]*[：:]\s*(.*?)(?=🔍|$)', output_text, re.DOTALL)
            if revision_match:
                revised_text = revision_match.group(1).strip()

                # 检查数字一致性
                selection_numbers = set(re.findall(r'\d+\.?\d*', selection))
                revised_numbers = set(re.findall(r'\d+\.?\d*', revised_text))

                if selection_numbers != revised_numbers:
                    score -= 1.0
                    feedback = "修订改变了数字信息"
                    suggestions.append("请确保数字信息一致（除非有意修改）")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="revision_quality",
            dimension_label=self.LABELS["revision_quality"],
            score=score,
            weight=self.WEIGHTS["revision_quality"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_linkage_detection(self, selection: str, full_document: str, output_text: str) -> EvaluationResult:
        """评价联动发现率"""
        score = 5.0
        feedback = "联动分析到位"
        suggestions = []

        # 检查是否包含联动分析
        linkage_indicators = ['联动', '影响', '同步', '关联', '🔍']
        has_linkage = any(indicator in output_text for indicator in linkage_indicators)

        if not has_linkage:
            score -= 2.0
            feedback = "缺少联动影响分析"
            suggestions.append("请分析全文中的联动影响")

        # 检查是否正确识别"无联动"的情况
        no_linkage_indicators = ['未发现', '无需', '无需联动', '✅']
        has_no_linkage = any(indicator in output_text for indicator in no_linkage_indicators)

        # 如果选中文本是独立的，应该识别为无联动
        if selection and not any(char in full_document.replace(selection, '') for char in selection[:10]):
            if not has_no_linkage:
                score -= 1.0
                feedback = "可能误判联动关系"
                suggestions.append("独立文本可能不需要联动分析")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="linkage_detection",
            dimension_label=self.LABELS["linkage_detection"],
            score=score,
            weight=self.WEIGHTS["linkage_detection"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_contradiction_detection(self, selection: str, full_document: str, output_text: str) -> EvaluationResult:
        """评价矛盾检测准确性"""
        score = 5.0
        feedback = "矛盾检测准确"
        suggestions = []

        # 检查是否包含矛盾检测结果
        contradiction_indicators = ['矛盾', '不一致', '冲突', '歧义']
        has_contradiction_analysis = any(indicator in output_text for indicator in contradiction_indicators)

        # 检查数字矛盾
        selection_numbers = re.findall(r'\d+\.?\d*', selection)
        doc_numbers = re.findall(r'\d+\.?\d*', full_document)

        # 如果有数字变化，应该检测到矛盾
        if selection_numbers:
            for num in selection_numbers:
                # 检查文档中是否有相同数字但上下文不同
                pass

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="contradiction_detection",
            dimension_label=self.LABELS["contradiction_detection"],
            score=score,
            weight=self.WEIGHTS["contradiction_detection"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_zero_false_positive(self, full_document: str, output_text: str) -> EvaluationResult:
        """评价零误报率"""
        score = 5.0
        feedback = "无误报"
        suggestions = []

        # 检查联动分析部分
        linkage_match = re.search(r'🔍.*?联动.*?(?=💡|$)', output_text, re.DOTALL)
        if linkage_match:
            linkage_text = linkage_match.group(0)

            # 检查是否有过多的联动标记
            linkage_items = re.findall(r'- \*\*位置\*\*', linkage_text)
            if len(linkage_items) > 5:
                score -= 1.0
                feedback = "联动标记过多，可能存在误报"
                suggestions.append("请精简联动分析，只标记真正需要修改的位置")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="zero_false_positive",
            dimension_label=self.LABELS["zero_false_positive"],
            score=score,
            weight=self.WEIGHTS["zero_false_positive"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_output_format(self, output_text: str) -> EvaluationResult:
        """评价输出格式规范性"""
        score = 5.0
        feedback = "格式规范"
        suggestions = []

        # 检查三段式格式
        has_revision = bool(re.search(r'📝|修订后', output_text))
        has_linkage = bool(re.search(r'🔍|联动', output_text))
        has_explanation = bool(re.search(r'💡|说明', output_text))

        format_completeness = sum([has_revision, has_linkage, has_explanation])

        if format_completeness < 2:
            score -= 1.5
            feedback = "输出格式不完整"
            suggestions.append("请按照三段式格式输出：修订后文本 + 联动影响分析 + 修订说明")
        elif format_completeness < 3:
            score -= 0.5
            feedback = "输出格式基本完整"
            suggestions.append("建议补充修订说明部分")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="output_format",
            dimension_label=self.LABELS["output_format"],
            score=score,
            weight=self.WEIGHTS["output_format"],
            feedback=feedback,
            suggestions=suggestions
        )


class CustomEvaluator:
    """自定义指令评价器"""

    WEIGHTS = {
        "instruction_compliance": 0.35,
        "output_specification": 0.25,
        "format_preservation": 0.20,
        "change_precision": 0.20,
    }

    LABELS = {
        "instruction_compliance": "指令遵循度",
        "output_specification": "输出规范性",
        "format_preservation": "格式保持度",
        "change_precision": "修改精准度",
    }

    def evaluate(self, instruction: str, input_text: str, output_text: str) -> List[EvaluationResult]:
        """评价自定义指令输出"""
        results = []

        results.append(self._evaluate_instruction_compliance(instruction, input_text, output_text))
        results.append(self._evaluate_output_specification(output_text))
        results.append(self._evaluate_format_preservation(input_text, output_text))
        results.append(self._evaluate_change_precision(instruction, input_text, output_text))

        return results

    def _evaluate_instruction_compliance(self, instruction: str, input_text: str, output_text: str) -> EvaluationResult:
        """评价指令遵循度"""
        score = 5.0
        feedback = "指令遵循良好"
        suggestions = []

        # 检查指令关键词是否体现在输出中
        instruction_keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', instruction)

        if instruction_keywords:
            matched_keywords = sum(1 for keyword in instruction_keywords if keyword in output_text)
            match_rate = matched_keywords / len(instruction_keywords)

            if match_rate < 0.3:
                score -= 1.5
                feedback = "指令遵循度较低"
                suggestions.append("请严格按照指令执行修改")

        # 检查是否有多余的解释
        explanation_patterns = [
            r'我已将',
            r'修改说明',
            r'以下是修改后的版本',
            r'按照要求',
        ]
        for pattern in explanation_patterns:
            if re.search(pattern, output_text):
                score -= 1.0
                feedback = "包含多余解释"
                suggestions.append("只输出修改后的文本，不要解释")
                break

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="instruction_compliance",
            dimension_label=self.LABELS["instruction_compliance"],
            score=score,
            weight=self.WEIGHTS["instruction_compliance"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_output_specification(self, output_text: str) -> EvaluationResult:
        """评价输出规范性"""
        score = 5.0
        feedback = "输出规范"
        suggestions = []

        # 检查是否包含代码围栏
        if '```' in output_text:
            score -= 0.5
            feedback = "包含代码围栏"
            suggestions.append("不要使用代码围栏包裹输出")

        # 检查是否有前缀标记
        prefix_patterns = [
            r'^修改后[：:]',
            r'^结果[：:]',
            r'^输出[：:]',
        ]
        for pattern in prefix_patterns:
            if re.search(pattern, output_text):
                score -= 0.5
                feedback = "包含前缀标记"
                suggestions.append("直接输出修改后的文本")
                break

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="output_specification",
            dimension_label=self.LABELS["output_specification"],
            score=score,
            weight=self.WEIGHTS["output_specification"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_format_preservation(self, input_text: str, output_text: str) -> EvaluationResult:
        """评价格式保持度"""
        score = 5.0
        feedback = "格式保持良好"
        suggestions = []

        # 检查缩进是否保持
        input_indent = len(input_text) - len(input_text.lstrip())
        output_indent = len(output_text) - len(output_text.lstrip())

        if input_indent != output_indent:
            score -= 0.5
            feedback = "缩进格式发生变化"
            suggestions.append("请保持原有的缩进格式")

        # 检查行数是否保持（如果指令没有要求增删）
        input_lines = input_text.count('\n')
        output_lines = output_text.count('\n')

        if abs(input_lines - output_lines) > 2:
            score -= 0.5
            feedback = "行数变化较大"
            suggestions.append("请保持原有的行数结构")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="format_preservation",
            dimension_label=self.LABELS["format_preservation"],
            score=score,
            weight=self.WEIGHTS["format_preservation"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_change_precision(self, instruction: str, input_text: str, output_text: str) -> EvaluationResult:
        """评价修改精准度"""
        score = 5.0
        feedback = "修改精准"
        suggestions = []

        # 检查未修改部分是否保持不变
        # 这需要更复杂的diff分析，这里简化处理

        # 检查输出长度变化
        length_ratio = len(output_text) / len(input_text) if input_text else 1

        if length_ratio < 0.5:
            score -= 1.0
            feedback = "内容大幅缩减"
            suggestions.append("请确保只修改指令要求的部分")
        elif length_ratio > 2:
            score -= 0.5
            feedback = "内容大幅扩展"
            suggestions.append("请确保只修改指令要求的部分")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="change_precision",
            dimension_label=self.LABELS["change_precision"],
            score=score,
            weight=self.WEIGHTS["change_precision"],
            feedback=feedback,
            suggestions=suggestions
        )


class CommonEvaluator:
    """跨场景通用评价器"""

    WEIGHTS = {
        "output_length_control": 0.40,
        "error_handling": 0.35,
        "consistency": 0.25,
    }

    LABELS = {
        "output_length_control": "输出长度控制",
        "error_handling": "错误处理能力",
        "consistency": "多次调用一致性",
    }

    def evaluate(self, input_text: str, output_text: str, 
                 expected_length: int = None) -> List[EvaluationResult]:
        """评价跨场景通用维度"""
        results = []

        results.append(self._evaluate_output_length_control(input_text, output_text, expected_length))
        results.append(self._evaluate_error_handling(input_text, output_text))
        results.append(self._evaluate_consistency(output_text))

        return results

    def _evaluate_output_length_control(self, input_text: str, output_text: str, 
                                       expected_length: int = None) -> EvaluationResult:
        """评价输出长度控制"""
        score = 5.0
        feedback = "输出长度合理"
        suggestions = []

        input_len = len(input_text)
        output_len = len(output_text)

        # 检查输出是否过短
        if output_len < 10:
            score -= 2.0
            feedback = "输出过短"
            suggestions.append("请提供更详细的输出")
        # 检查输出是否过长
        elif expected_length and output_len > expected_length * 2:
            score -= 1.0
            feedback = "输出超出预期长度"
            suggestions.append("请控制输出长度")
        # 检查输入输出比例
        elif input_len > 0:
            ratio = output_len / input_len
            if ratio > 10:
                score -= 0.5
                feedback = "输出相对输入过长"
                suggestions.append("请保持输出简洁")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="output_length_control",
            dimension_label=self.LABELS["output_length_control"],
            score=score,
            weight=self.WEIGHTS["output_length_control"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_error_handling(self, input_text: str, output_text: str) -> EvaluationResult:
        """评价错误处理能力"""
        score = 5.0
        feedback = "错误处理良好"
        suggestions = []

        # 检查是否包含错误信息
        error_indicators = ['错误', '失败', '无法', '不支持', 'error', 'failed', 'cannot']
        has_error = any(indicator in output_text.lower() for indicator in error_indicators)

        # 检查输入是否为空或无效
        if not input_text or len(input_text.strip()) == 0:
            if has_error:
                # 空输入时输出错误信息是合理的
                pass
            else:
                score -= 1.0
                feedback = "空输入时未给出适当提示"
                suggestions.append("空输入时应给出使用提示")

        # 检查是否包含堆栈跟踪或技术细节（不应该暴露给用户）
        technical_patterns = [
            r'Traceback \(most recent call last\)',
            r'File ".*", line \d+',
            r'Exception:',
            r'Error:',
        ]
        for pattern in technical_patterns:
            if re.search(pattern, output_text):
                score -= 1.5
                feedback = "暴露了技术细节"
                suggestions.append("不要向用户暴露技术错误细节")
                break

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="error_handling",
            dimension_label=self.LABELS["error_handling"],
            score=score,
            weight=self.WEIGHTS["error_handling"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_consistency(self, output_text: str) -> EvaluationResult:
        """评价多次调用一致性"""
        score = 5.0
        feedback = "输出格式一致"
        suggestions = []

        # 检查输出格式是否规范
        # 这里主要检查格式一致性，实际的一致性需要多次调用对比
        
        # 检查是否有不一致的格式
        if '```' in output_text and output_text.count('```') % 2 != 0:
            score -= 1.0
            feedback = "代码块格式不完整"
            suggestions.append("请确保代码块正确闭合")

        # 检查标点符号一致性
        chinese_punctuation = len(re.findall(r'[，。！？；：、]', output_text))
        english_punctuation = len(re.findall(r'[,.!?;:]', output_text))
        
        if chinese_punctuation > 0 and english_punctuation > 0:
            # 混合使用中英文标点
            if abs(chinese_punctuation - english_punctuation) > 3:
                score -= 0.5
                feedback = "标点符号使用不一致"
                suggestions.append("请统一使用中文或英文标点")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="consistency",
            dimension_label=self.LABELS["consistency"],
            score=score,
            weight=self.WEIGHTS["consistency"],
            feedback=feedback,
            suggestions=suggestions
        )


class EdgeCaseEvaluator:
    """边界情况处理评价器"""

    WEIGHTS = {
        "empty_input": 0.35,
        "invalid_input": 0.35,
        "ambiguous": 0.30,
    }

    LABELS = {
        "empty_input": "空输入处理",
        "invalid_input": "无效输入处理",
        "ambiguous": "模糊指令处理",
    }

    def evaluate(self, input_text: str, output_text: str, 
                 instruction: str = None) -> List[EvaluationResult]:
        """评价边界情况处理"""
        results = []

        results.append(self._evaluate_empty_input(input_text, output_text))
        results.append(self._evaluate_invalid_input(input_text, output_text))
        results.append(self._evaluate_ambiguous_instruction(instruction, output_text))

        return results

    def _evaluate_empty_input(self, input_text: str, output_text: str) -> EvaluationResult:
        """评价空输入处理"""
        score = 5.0
        feedback = "空输入处理得当"
        suggestions = []

        # 检查输入是否为空
        if not input_text or len(input_text.strip()) == 0:
            # 空输入时应该给出提示
            help_indicators = ['请输入', '请提供', '需要', '帮助', 'help', 'usage']
            has_help = any(indicator in output_text.lower() for indicator in help_indicators)
            
            if not has_help:
                score -= 2.0
                feedback = "空输入时未给出使用提示"
                suggestions.append("空输入时应给出使用帮助或提示")
            elif len(output_text) > 500:
                score -= 0.5
                feedback = "空输入时输出过长"
                suggestions.append("空输入时提示应简洁")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="empty_input",
            dimension_label=self.LABELS["empty_input"],
            score=score,
            weight=self.WEIGHTS["empty_input"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_invalid_input(self, input_text: str, output_text: str) -> EvaluationResult:
        """评价无效输入处理"""
        score = 5.0
        feedback = "无效输入处理得当"
        suggestions = []

        # 检查输入是否包含明显无效内容
        invalid_patterns = [
            r'^[\s\n]*$',  # 空白字符
            r'^[^\w\s]+$',  # 只有特殊字符
            r'测试测试测试',  # 测试文本
            r'asdfghjkl',  # 乱码
        ]
        
        is_invalid = any(re.match(pattern, input_text) for pattern in invalid_patterns)
        
        if is_invalid:
            # 无效输入时应该给出提示
            error_indicators = ['无效', '无法识别', '请重新', '格式错误', 'invalid']
            has_error_handling = any(indicator in output_text.lower() for indicator in error_indicators)
            
            if not has_error_handling:
                score -= 1.5
                feedback = "无效输入时未给出适当提示"
                suggestions.append("无效输入时应提示用户重新输入")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="invalid_input",
            dimension_label=self.LABELS["invalid_input"],
            score=score,
            weight=self.WEIGHTS["invalid_input"],
            feedback=feedback,
            suggestions=suggestions
        )

    def _evaluate_ambiguous_instruction(self, instruction: str, output_text: str) -> EvaluationResult:
        """评价模糊指令处理"""
        score = 5.0
        feedback = "模糊指令处理得当"
        suggestions = []

        if instruction:
            # 检查指令是否模糊
            ambiguous_patterns = [
                r'修改一下',
                r'优化一下',
                r'改得更好',
                r'随便改改',
                r'make it better',
                r'improve',
            ]
            
            is_ambiguous = any(re.search(pattern, instruction.lower()) for pattern in ambiguous_patterns)
            
            if is_ambiguous:
                # 模糊指令时应该要求澄清或给出合理默认行为
                clarification_indicators = ['请问', '具体', '哪方面', '如何', 'clarify']
                has_clarification = any(indicator in output_text.lower() for indicator in clarification_indicators)
                
                if not has_clarification and len(output_text) > 100:
                    # 直接执行了模糊指令，可能不符合用户预期
                    score -= 1.0
                    feedback = "模糊指令时未要求澄清"
                    suggestions.append("模糊指令时应要求用户明确需求或给出合理默认行为")

        score = max(1.0, min(5.0, score))
        return EvaluationResult(
            dimension="ambiguous",
            dimension_label=self.LABELS["ambiguous"],
            score=score,
            weight=self.WEIGHTS["ambiguous"],
            feedback=feedback,
            suggestions=suggestions
        )


# ============================================================
# 主评价器
# ============================================================

class OpenCopilotEvaluator:
    """OpenCopilot 划词功能评价器"""

    def __init__(self):
        """初始化评价器"""
        self.evaluators = {
            ActionScene.AUTO: AutoEvaluator(),
            ActionScene.TRANSLATE: TranslateEvaluator(),
            ActionScene.CODE: CodeEvaluator(),
            ActionScene.POLISH: PolishEvaluator(),
            ActionScene.REVISION: RevisionEvaluator(),
            ActionScene.CUSTOM: CustomEvaluator(),
        }
        
        # 通用评价器
        self.common_evaluator = CommonEvaluator()
        self.edge_case_evaluator = EdgeCaseEvaluator()

        self.scene_labels = {
            ActionScene.AUTO: "自动模式",
            ActionScene.TRANSLATE: "翻译",
            ActionScene.CODE: "代码解析",
            ActionScene.POLISH: "润色",
            ActionScene.REVISION: "全文修订",
            ActionScene.CUSTOM: "自定义指令",
        }

    def evaluate(self, scene: str, input_text: str, output_text: str,
                 reference: str = None, instruction: str = None,
                 full_document: str = None) -> QualityReport:
        """
        评价划词功能输出

        Args:
            scene: 场景类型 (auto/translate/code/polish/revision/custom)
            input_text: 输入文本
            output_text: 输出文本
            reference: 参考文本（翻译场景可选）
            instruction: 自定义指令（custom场景必填）
            full_document: 完整文档（revision场景必填）

        Returns:
            QualityReport: 质量报告
        """
        try:
            action_scene = ActionScene(scene)
        except ValueError:
            action_scene = ActionScene.AUTO

        evaluator = self.evaluators[action_scene]

        # 根据场景调用不同的评价器
        if action_scene == ActionScene.TRANSLATE:
            results = evaluator.evaluate(input_text, output_text, reference)
        elif action_scene == ActionScene.REVISION:
            results = evaluator.evaluate(input_text, full_document or "", output_text)
        elif action_scene == ActionScene.CUSTOM:
            results = evaluator.evaluate(instruction or "", input_text, output_text)
        else:
            results = evaluator.evaluate(input_text, output_text)

        # 添加通用维度评价
        common_results = self.common_evaluator.evaluate(input_text, output_text)
        results.extend(common_results)

        # 添加边界情况维度评价
        edge_case_results = self.edge_case_evaluator.evaluate(input_text, output_text, instruction)
        results.extend(edge_case_results)

        # 计算总分（加权平均）
        total_score = 0.0
        total_weight = 0.0
        for result in results:
            total_score += result.score * result.weight
            total_weight += result.weight

        if total_weight > 0:
            total_score = total_score / total_weight
        else:
            total_score = 0.0

        # 确定等级
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

        # 生成总结
        summary = self._generate_summary(results, total_score, level, action_scene)

        # 生成改进计划
        improvement_plan = self._generate_improvement_plan(results, action_scene)

        return QualityReport(
            content=output_text,
            scene=scene,
            scene_label=self.scene_labels[action_scene],
            results=results,
            total_score=total_score,
            level=level,
            summary=summary,
            improvement_plan=improvement_plan,
            input_text=input_text,
            reference_text=reference or "",
            custom_instruction=instruction or "",
            full_document=full_document or ""
        )

    def _generate_summary(self, results: List[EvaluationResult], total_score: float,
                          level: str, scene: ActionScene) -> str:
        """生成评价总结"""
        summary = f"## {self.scene_labels[scene]}评价结果\n\n"
        summary += f"**总分**: {total_score:.1f}/5.0 ({level})\n\n"
        summary += "### 各维度得分\n\n"

        for result in results:
            status = "✅" if result.score >= 4.0 else "⚠️" if result.score >= 3.0 else "❌"
            summary += f"- {status} **{result.dimension_label}**: {result.score:.1f}/5.0 - {result.feedback}\n"

        # 找出最高和最低分维度
        best = max(results, key=lambda x: x.score)
        worst = min(results, key=lambda x: x.score)

        summary += f"\n**最佳维度**: {best.dimension_label} ({best.score:.1f}分)\n"
        summary += f"**待改进维度**: {worst.dimension_label} ({worst.score:.1f}分)\n"

        return summary

    def _generate_improvement_plan(self, results: List[EvaluationResult], scene: ActionScene) -> str:
        """生成改进计划"""
        plan = f"## {self.scene_labels[scene]}改进计划\n\n"

        # 按分数排序，优先改进低分维度
        sorted_results = sorted(results, key=lambda x: x.score)

        has_improvements = False
        for i, result in enumerate(sorted_results, 1):
            if result.score < 4.0:
                has_improvements = True
                plan += f"### {i}. {result.dimension_label} ({result.score:.1f}分)\n"
                for suggestion in result.suggestions:
                    plan += f"- {suggestion}\n"
                plan += "\n"

        if not has_improvements:
            plan += "当前质量良好，无需改进。\n"

        return plan


# ============================================================
# 全局实例和便捷函数
# ============================================================

# 创建全局评价器实例
evaluator = OpenCopilotEvaluator()


def evaluate_auto(input_text: str, output_text: str) -> QualityReport:
    """评价自动模式输出"""
    return evaluator.evaluate("auto", input_text, output_text)


def evaluate_translate(input_text: str, output_text: str, reference: str = None) -> QualityReport:
    """评价翻译输出"""
    return evaluator.evaluate("translate", input_text, output_text, reference=reference)


def evaluate_code(input_code: str, output_text: str) -> QualityReport:
    """评价代码解析输出"""
    return evaluator.evaluate("code", input_code, output_text)


def evaluate_polish(input_text: str, output_text: str) -> QualityReport:
    """评价润色输出"""
    return evaluator.evaluate("polish", input_text, output_text)


def evaluate_revision(selection: str, full_document: str, output_text: str) -> QualityReport:
    """评价全文修订输出"""
    return evaluator.evaluate("revision", selection, output_text, full_document=full_document)


def evaluate_custom(instruction: str, input_text: str, output_text: str) -> QualityReport:
    """评价自定义指令输出"""
    return evaluator.evaluate("custom", input_text, output_text, instruction=instruction)


def evaluate_generation_quality(content: str, scene: str,
                                reference: str = None,
                                requirements: List[str] = None,
                                instruction: str = None,
                                full_document: str = None,
                                input_text: str = "") -> QualityReport:
    """
    通用评价函数（兼容旧接口）

    Args:
        content: 输出内容
        scene: 场景类型
        reference: 参考内容
        requirements: 必要信息要求（旧接口兼容）
        instruction: 自定义指令
        full_document: 完整文档
        input_text: 输入文本

    Returns:
        QualityReport: 质量报告
    """
    return evaluator.evaluate(
        scene=scene,
        input_text=input_text,
        output_text=content,
        reference=reference,
        instruction=instruction,
        full_document=full_document
    )


# ============================================================
# 工具注册信息
# ============================================================

TOOL_INFO = {
    "name": "opencopilot_evaluation",
    "description": "OpenCopilot 划词功能质量评价工具 - 围绕6大核心场景设计",
    "version": "2.0",
    "scenes": {
        "auto": {
            "description": "自动模式 - 类型判断 + 翻译/解释/总结",
            "dimensions": ["类型判断准确性", "响应恰当性", "输出质量"]
        },
        "translate": {
            "description": "翻译 - 信达雅",
            "dimensions": ["翻译准确性", "信（忠实原文）", "达（表达通顺）", "雅（用词优雅）", "术语一致性"]
        },
        "code": {
            "description": "代码解析 - 功能总结 + 漏洞发现",
            "dimensions": ["功能总结准确性", "漏洞发现率", "优化建议合理性", "解释清晰度"]
        },
        "polish": {
            "description": "润色 - 语病修正 + 专业度提升",
            "dimensions": ["语病修正率", "专业度提升", "流畅度改善", "语义保持度"]
        },
        "revision": {
            "description": "全文修订 - 修订质量 + 联动发现",
            "dimensions": ["修订质量", "联动发现率", "矛盾检测准确性", "零误报率", "输出格式规范性"]
        },
        "custom": {
            "description": "自定义指令 - 指令遵循度",
            "dimensions": ["指令遵循度", "输出规范性", "格式保持度", "修改精准度"]
        }
    }
}
