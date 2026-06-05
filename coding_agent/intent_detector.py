"""
意图识别器

识别用户的编码意图，支持多种意图类型。
"""

from enum import Enum
from typing import Optional, Dict, Any


class CodingIntent(Enum):
    """编码意图枚举"""
    BUG_FIX = "bug_fix"           # Bug 修复
    CODE_REVIEW = "code_review"   # 代码审查
    EXPLAIN = "explain"           # 代码解释
    REFACTOR = "refactor"         # 代码重构
    ENHANCE_API = "enhance_api"   # API 结果增强
    ANALYZE = "analyze"           # 代码分析
    GENERAL = "general"           # 通用


class IntentDetector:
    """意图识别器"""
    
    # 关键词映射
    KEYWORD_MAP = {
        CodingIntent.BUG_FIX: [
            "bug", "错误", "报错", "失败", "异常", "崩溃", "不工作",
            "fix", "修复", "解决", "error", "exception", "crash",
            "问题", "issue", "problem", "trouble"
        ],
        CodingIntent.CODE_REVIEW: [
            "审查", "review", "检查", "看看", "质量", "规范",
            "check", "analyze", "quality", "audit", "inspect"
        ],
        CodingIntent.EXPLAIN: [
            "解释", "explain", "什么意思", "怎么理解", "为什么",
            "what", "why", "how", "理解", "understand", "mean"
        ],
        CodingIntent.REFACTOR: [
            "重构", "refactor", "优化", "改进", "简化", "重写",
            "optimize", "improve", "simplify", "rewrite", "clean"
        ],
        CodingIntent.ENHANCE_API: [
            "增强", "enhance", "补足", "补充", "完善",
            "augment", "enrich", "supplement", "context"
        ],
        CodingIntent.ANALYZE: [
            "分析", "analyze", "分析代码", "代码分析",
            "code analysis", "static analysis", "lint"
        ]
    }
    
    # 错误类型模式
    ERROR_PATTERNS = {
        "NameError": ["NameError", "未定义", "not defined"],
        "TypeError": ["TypeError", "类型错误", "type error"],
        "ValueError": ["ValueError", "值错误", "value error"],
        "AttributeError": ["AttributeError", "属性错误", "attribute error"],
        "ImportError": ["ImportError", "导入错误", "import error"],
        "SyntaxError": ["SyntaxError", "语法错误", "syntax error"],
        "IndexError": ["IndexError", "索引错误", "index error"],
        "KeyError": ["KeyError", "键错误", "key error"],
        "FileNotFoundError": ["FileNotFoundError", "文件未找到", "file not found"],
        "PermissionError": ["PermissionError", "权限错误", "permission error"],
        "ZeroDivisionError": ["ZeroDivisionError", "除零错误", "division by zero"],
        "RuntimeError": ["RuntimeError", "运行时错误", "runtime error"],
        "Exception": ["Exception", "异常", "exception"]
    }
    
    def detect(
        self,
        user_message: str,
        has_diagnostics: bool = False,
        has_error_message: bool = False,
        error_type: Optional[str] = None
    ) -> CodingIntent:
        """
        检测用户意图
        
        Args:
            user_message: 用户消息
            has_diagnostics: 是否有诊断信息
            has_error_message: 是否有错误信息
            error_type: 错误类型
        
        Returns:
            CodingIntent: 检测到的意图
        """
        message_lower = user_message.lower()
        
        # 1. 检查是否有诊断信息或错误消息（优先级最高）
        if has_diagnostics or has_error_message:
            # 如果有明确的错误信息，优先认为是 bug fix
            for keyword in self.KEYWORD_MAP[CodingIntent.BUG_FIX]:
                if keyword in message_lower:
                    return CodingIntent.BUG_FIX
        
        # 2. 检查错误类型
        if error_type:
            for intent_type, patterns in self.ERROR_PATTERNS.items():
                for pattern in patterns:
                    if pattern.lower() in error_type.lower():
                        return CodingIntent.BUG_FIX
        
        # 3. 关键词匹配
        for intent, keywords in self.KEYWORD_MAP.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return intent
        
        # 4. 默认意图
        return CodingIntent.GENERAL
    
    def detect_from_context(self, context: Dict[str, Any]) -> CodingIntent:
        """
        从上下文推断意图
        
        Args:
            context: 上下文信息
        
        Returns:
            CodingIntent: 推断的意图
        """
        diagnostics = context.get("diagnostics", {})
        errors = diagnostics.get("errors", [])
        
        # 如果有错误诊断，认为是 bug fix
        if errors:
            return CodingIntent.BUG_FIX
        
        # 如果有 git diff，可能是 code review
        git_diff = context.get("git_diff", {})
        if git_diff.get("diff"):
            return CodingIntent.CODE_REVIEW
        
        # 如果有符号信息，可能是 explain
        symbols = context.get("symbols", {})
        if symbols:
            return CodingIntent.EXPLAIN
        
        return CodingIntent.GENERAL
    
    def detect_error_type(self, error_message: str) -> Optional[str]:
        """
        检测错误类型
        
        Args:
            error_message: 错误消息
        
        Returns:
            Optional[str]: 错误类型，如果未检测到则返回 None
        """
        error_message_lower = error_message.lower()
        
        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in error_message_lower:
                    return error_type
        
        return None
    
    def get_confidence(self, intent: CodingIntent, user_message: str, context: Dict[str, Any] = None) -> float:
        """
        获取意图识别的置信度
        
        Args:
            intent: 检测到的意图
            user_message: 用户消息
            context: 上下文信息
        
        Returns:
            float: 置信度 (0-1)
        """
        if context is None:
            context = {}
        
        confidence = 0.5  # 基础置信度
        
        # 关键词匹配数量
        message_lower = user_message.lower()
        keywords = self.KEYWORD_MAP.get(intent, [])
        matched_keywords = sum(1 for keyword in keywords if keyword in message_lower)
        
        # 关键词匹配越多，置信度越高
        if matched_keywords > 0:
            confidence += min(0.3, matched_keywords * 0.1)
        
        # 上下文信息
        diagnostics = context.get("diagnostics", {})
        errors = diagnostics.get("errors", [])
        
        # 如果有错误信息且意图是 bug fix，增加置信度
        if errors and intent == CodingIntent.BUG_FIX:
            confidence += 0.2
        
        # 如果有 git diff 且意图是 code review，增加置信度
        git_diff = context.get("git_diff", {})
        if git_diff.get("diff") and intent == CodingIntent.CODE_REVIEW:
            confidence += 0.2
        
        # 限制置信度范围
        return min(1.0, max(0.0, confidence))