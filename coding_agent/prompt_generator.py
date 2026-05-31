"""
动态 Prompt 生成器

根据上下文和意图生成针对性的 Prompt。
"""

from typing import Dict, Any, Optional, List
from .intent_detector import CodingIntent


class PromptTemplate:
    """Prompt 模板"""
    
    def __init__(self, template: str, variables: List[str]):
        """
        初始化 Prompt 模板
        
        Args:
            template: 模板字符串
            variables: 变量列表
        """
        self.template = template
        self.variables = variables
    
    def render(self, **kwargs) -> str:
        """
        渲染模板
        
        Args:
            **kwargs: 变量值
        
        Returns:
            str: 渲染后的字符串
        """
        result = self.template
        for var in self.variables:
            if var in kwargs:
                result = result.replace(f"{{{var}}}", str(kwargs[var]))
        return result


class PromptLibrary:
    """Prompt 模板库"""
    
    # 角色定义
    ROLES = {
        CodingIntent.BUG_FIX: "你是一个专业的 Bug 修复专家，擅长快速定位和修复代码问题。",
        CodingIntent.CODE_REVIEW: "你是一个资深的代码审查专家，擅长发现代码中的问题和改进点。",
        CodingIntent.EXPLAIN: "你是一个代码解释专家，擅长用简洁清晰的语言解释复杂代码。",
        CodingIntent.REFACTOR: "你是一个代码重构专家，擅长在不改变行为的前提下改进代码结构。",
        CodingIntent.ENHANCE_API: "你是一个代码分析专家，擅长补充分析上下文，提供更精准的分析结果。",
        CodingIntent.ANALYZE: "你是一个代码分析专家，擅长静态分析和代码质量评估。",
        CodingIntent.GENERAL: "你是一个专业的编程助手，擅长解决各种编程问题。"
    }
    
    # Bug 类型特定指导
    BUG_TYPE_GUIDES = {
        "NameError": {
            "description": "变量未定义错误",
            "causes": [
                "变量名拼写错误",
                "变量未在当前作用域定义",
                "忘记导入模块",
                "变量定义顺序错误"
            ],
            "strategy": "检查变量名、作用域、导入语句"
        },
        "TypeError": {
            "description": "类型不匹配错误",
            "causes": [
                "函数参数类型错误",
                "操作符用于不兼容的类型",
                "方法调用对象类型错误",
                "None 值参与运算"
            ],
            "strategy": "检查类型、添加类型检查、使用 isinstance()"
        },
        "SyntaxError": {
            "description": "语法错误",
            "causes": [
                "缺少括号、引号",
                "缩进错误",
                "关键字拼写错误",
                "非法字符"
            ],
            "strategy": "检查括号匹配、缩进、关键字拼写"
        },
        "AttributeError": {
            "description": "属性不存在错误",
            "causes": [
                "对象没有该属性",
                "对象类型错误",
                "属性名拼写错误",
                "对象为 None"
            ],
            "strategy": "检查对象类型、属性名、是否为 None"
        },
        "IndexError": {
            "description": "索引越界错误",
            "causes": [
                "列表索引超出范围",
                "空列表访问",
                "索引计算错误",
                "负数索引使用不当"
            ],
            "strategy": "检查列表长度、索引值、空值检查"
        },
        "KeyError": {
            "description": "键不存在错误",
            "causes": [
                "字典键名错误",
                "键不存在",
                "大小写不匹配",
                "嵌套键路径错误"
            ],
            "strategy": "检查键名、使用 get() 方法、添加键存在检查"
        },
        "RecursionError": {
            "description": "无限递归错误",
            "causes": [
                "递归终止条件缺失",
                "递归条件永远为真",
                "基本情况处理错误",
                "递归深度过大"
            ],
            "strategy": "检查递归终止条件、添加深度限制、改用迭代"
        },
        "ImportError": {
            "description": "导入错误",
            "causes": [
                "模块不存在",
                "模块名拼写错误",
                "循环导入",
                "路径问题"
            ],
            "strategy": "检查模块名、安装依赖、检查路径"
        },
        "FileNotFoundError": {
            "description": "文件未找到错误",
            "causes": [
                "文件路径错误",
                "文件不存在",
                "权限问题",
                "相对路径问题"
            ],
            "strategy": "检查文件路径、使用绝对路径、检查权限"
        },
        "PermissionError": {
            "description": "权限错误",
            "causes": [
                "文件权限不足",
                "目录权限不足",
                "用户权限不足"
            ],
            "strategy": "检查权限、使用 sudo、修改权限"
        },
        "ZeroDivisionError": {
            "description": "除零错误",
            "causes": [
                "分母为零",
                "除法运算错误",
                "未检查除数"
            ],
            "strategy": "检查除数、添加零值检查"
        },
        "RuntimeError": {
            "description": "运行时错误",
            "causes": [
                "逻辑错误",
                "资源不足",
                "状态异常"
            ],
            "strategy": "检查逻辑、资源、状态"
        }
    }
    
    # 语言特定指导
    LANGUAGE_GUIDES = {
        "python": {
            "name": "Python",
            "tips": [
                "检查缩进（Python 对缩进敏感）",
                "检查 self 参数（类方法）",
                "检查导入语句",
                "检查列表推导式语法"
            ]
        },
        "javascript": {
            "name": "JavaScript",
            "tips": [
                "检查分号",
                "检查 this 绑定",
                "检查异步/等待",
                "检查 undefined 和 null"
            ]
        },
        "typescript": {
            "name": "TypeScript",
            "tips": [
                "检查类型注解",
                "检查接口定义",
                "检查泛型使用",
                "检查空值处理"
            ]
        },
        "java": {
            "name": "Java",
            "tips": [
                "检查类和方法签名",
                "检查异常处理",
                "检查泛型类型",
                "检查访问修饰符"
            ]
        },
        "c++": {
            "name": "C++",
            "tips": [
                "检查指针和引用",
                "检查内存管理",
                "检查模板使用",
                "检查头文件包含"
            ]
        }
    }
    
    @classmethod
    def get_role(cls, intent: CodingIntent) -> str:
        """
        获取角色定义
        
        Args:
            intent: 编码意图
        
        Returns:
            str: 角色定义
        """
        return cls.ROLES.get(intent, cls.ROLES[CodingIntent.GENERAL])
    
    @classmethod
    def get_bug_guide(cls, error_type: str) -> Optional[Dict[str, Any]]:
        """
        获取 Bug 类型指导
        
        Args:
            error_type: 错误类型
        
        Returns:
            Optional[Dict[str, Any]]: Bug 类型指导
        """
        return cls.BUG_TYPE_GUIDES.get(error_type)
    
    @classmethod
    def get_language_guide(cls, language: str) -> Optional[Dict[str, Any]]:
        """
        获取语言特定指导
        
        Args:
            language: 编程语言
        
        Returns:
            Optional[Dict[str, Any]]: 语言特定指导
        """
        return cls.LANGUAGE_GUIDES.get(language.lower())


class PromptGenerator:
    """动态 Prompt 生成器"""
    
    def generate_bug_fix_prompt(
        self,
        diagnostics: Dict[str, Any],
        symbol_info: Optional[Dict[str, Any]] = None,
        git_diff: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
        user_message: str = ""
    ) -> str:
        """
        生成 Bug 修复 Prompt
        
        Args:
            diagnostics: 诊断信息
            symbol_info: 符号信息
            git_diff: Git diff
            language: 编程语言
            user_message: 用户消息
        
        Returns:
            str: 生成的 Prompt
        """
        parts = []
        
        # 1. 角色定义
        parts.append(PromptLibrary.get_role(CodingIntent.BUG_FIX))
        parts.append("")
        
        # 2. Bug 类型分析
        errors = diagnostics.get("errors", [])
        if errors:
            error_msg = errors[0].get("message", "")
            bug_guide = self._identify_bug_type(error_msg)
            
            if bug_guide:
                parts.append("## Bug 类型分析")
                parts.append(f"**类型**: {bug_guide['description']}")
                parts.append("")
                parts.append("**常见原因**:")
                for cause in bug_guide['causes']:
                    parts.append(f"- {cause}")
                parts.append("")
                parts.append(f"**修复策略**: {bug_guide['strategy']}")
                parts.append("")
        
        # 3. 诊断信息
        parts.append("## 当前诊断信息")
        if errors:
            for error in errors[:5]:  # 最多显示5个
                line = error.get('line', '?')
                message = error.get('message', '未知错误')
                parts.append(f"- 第{line}行 [错误] {message}")
        else:
            parts.append("- 无诊断信息")
        parts.append("")
        
        # 4. 语言特定指导
        if language:
            lang_guide = PromptLibrary.get_language_guide(language)
            if lang_guide:
                parts.append(f"## {lang_guide['name']} 特定提示")
                for tip in lang_guide['tips']:
                    parts.append(f"- {tip}")
                parts.append("")
        
        # 5. 代码上下文
        if symbol_info:
            parts.append("## 代码上下文")
            symbol_name = symbol_info.get('name', '未知')
            symbol_kind = symbol_info.get('kind', '未知')
            parts.append(f"- 当前符号: {symbol_name} ({symbol_kind})")
            parts.append("")
        
        # 6. Git diff（如果有）
        if git_diff and git_diff.get('diff'):
            parts.append("## 最近变更")
            parts.append("```diff")
            parts.append(git_diff['diff'][:1000])  # 限制长度
            parts.append("```")
            parts.append("")
        
        # 7. 输出格式
        parts.append("## 输出格式")
        parts.append("### 问题分析")
        parts.append("[详细分析问题的根本原因]")
        parts.append("")
        parts.append("### 修复方案")
        parts.append("```python")
        parts.append("[修复后的代码]")
        parts.append("```")
        parts.append("")
        parts.append("### 修复说明")
        parts.append("[解释为什么这样修复]")
        
        return "\n".join(parts)
    
    def generate_enhance_prompt(
        self,
        api_result: Dict[str, Any],
        context: Dict[str, Any],
        user_message: str = ""
    ) -> str:
        """
        生成 API 结果增强 Prompt
        
        Args:
            api_result: API 返回结果
            context: 上下文信息
            user_message: 用户消息
        
        Returns:
            str: 生成的 Prompt
        """
        parts = []
        
        # 1. 角色定义
        parts.append(PromptLibrary.get_role(CodingIntent.ENHANCE_API))
        parts.append("")
        
        # 2. API 结果分析
        parts.append("## API 结果分析")
        parts.append(f"**原始结果**: {api_result.get('content', '')[:500]}")
        parts.append("")
        
        # 3. 上下文信息
        parts.append("## 补充上下文")
        
        # 诊断信息
        diagnostics = context.get("diagnostics", {})
        errors = diagnostics.get("errors", [])
        if errors:
            parts.append("### 诊断信息")
            for error in errors[:3]:
                line = error.get('line', '?')
                message = error.get('message', '未知错误')
                parts.append(f"- 第{line}行: {message}")
            parts.append("")
        
        # 符号信息
        symbols = context.get("symbols", {})
        if symbols:
            parts.append("### 符号信息")
            parts.append(f"- 名称: {symbols.get('name', '未知')}")
            parts.append(f"- 类型: {symbols.get('kind', '未知')}")
            parts.append("")
        
        # Git diff
        git_diff = context.get("git_diff", {})
        if git_diff.get('diff'):
            parts.append("### 最近变更")
            parts.append("```diff")
            parts.append(git_diff['diff'][:500])
            parts.append("```")
            parts.append("")
        
        # 4. 输出格式
        parts.append("## 输出格式")
        parts.append("### 增强后的分析")
        parts.append("[基于上下文信息，提供更精准的分析结果]")
        parts.append("")
        parts.append("### 建议")
        parts.append("[根据上下文提供具体的建议]")
        
        return "\n".join(parts)
    
    def generate_code_review_prompt(
        self,
        code: str,
        git_diff: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
        user_message: str = ""
    ) -> str:
        """
        生成代码审查 Prompt
        
        Args:
            code: 代码内容
            git_diff: Git diff
            language: 编程语言
            user_message: 用户消息
        
        Returns:
            str: 生成的 Prompt
        """
        parts = []
        
        # 1. 角色定义
        parts.append(PromptLibrary.get_role(CodingIntent.CODE_REVIEW))
        parts.append("")
        
        # 2. 代码内容
        parts.append("## 待审查代码")
        parts.append("```" + (language or ""))
        parts.append(code[:2000])  # 限制长度
        parts.append("```")
        parts.append("")
        
        # 3. Git diff（如果有）
        if git_diff and git_diff.get('diff'):
            parts.append("## 最近变更")
            parts.append("```diff")
            parts.append(git_diff['diff'][:1000])
            parts.append("```")
            parts.append("")
        
        # 4. 语言特定指导
        if language:
            lang_guide = PromptLibrary.get_language_guide(language)
            if lang_guide:
                parts.append(f"## {lang_guide['name']} 审查要点")
                for tip in lang_guide['tips']:
                    parts.append(f"- {tip}")
                parts.append("")
        
        # 5. 输出格式
        parts.append("## 输出格式")
        parts.append("### 问题列表")
        parts.append("[列出发现的问题]")
        parts.append("")
        parts.append("### 改进建议")
        parts.append("[提供具体的改进建议]")
        parts.append("")
        parts.append("### 代码质量评分")
        parts.append("[1-10分的评分]")
        
        return "\n".join(parts)
    
    def generate_explain_prompt(
        self,
        code: str,
        symbol_info: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
        user_message: str = ""
    ) -> str:
        """
        生成代码解释 Prompt
        
        Args:
            code: 代码内容
            symbol_info: 符号信息
            language: 编程语言
            user_message: 用户消息
        
        Returns:
            str: 生成的 Prompt
        """
        parts = []
        
        # 1. 角色定义
        parts.append(PromptLibrary.get_role(CodingIntent.EXPLAIN))
        parts.append("")
        
        # 2. 代码内容
        parts.append("## 待解释代码")
        parts.append("```" + (language or ""))
        parts.append(code[:2000])  # 限制长度
        parts.append("```")
        parts.append("")
        
        # 3. 符号信息
        if symbol_info:
            parts.append("## 符号信息")
            parts.append(f"- 名称: {symbol_info.get('name', '未知')}")
            parts.append(f"- 类型: {symbol_info.get('kind', '未知')}")
            parts.append("")
        
        # 4. 输出格式
        parts.append("## 输出格式")
        parts.append("### 功能说明")
        parts.append("[解释代码的功能]")
        parts.append("")
        parts.append("### 工作原理")
        parts.append("[解释代码的工作原理]")
        parts.append("")
        parts.append("### 关键点")
        parts.append("[列出代码的关键点]")
        
        return "\n".join(parts)
    
    def generate_refactor_prompt(
        self,
        code: str,
        diagnostics: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
        user_message: str = ""
    ) -> str:
        """
        生成代码重构 Prompt
        
        Args:
            code: 代码内容
            diagnostics: 诊断信息
            language: 编程语言
            user_message: 用户消息
        
        Returns:
            str: 生成的 Prompt
        """
        parts = []
        
        # 1. 角色定义
        parts.append(PromptLibrary.get_role(CodingIntent.REFACTOR))
        parts.append("")
        
        # 2. 代码内容
        parts.append("## 待重构代码")
        parts.append("```" + (language or ""))
        parts.append(code[:2000])  # 限制长度
        parts.append("```")
        parts.append("")
        
        # 3. 诊断信息
        if diagnostics:
            errors = diagnostics.get("errors", [])
            warnings = diagnostics.get("warnings", [])
            
            if errors or warnings:
                parts.append("## 诊断信息")
                for error in errors[:3]:
                    line = error.get('line', '?')
                    message = error.get('message', '未知错误')
                    parts.append(f"- 第{line}行 [错误] {message}")
                for warning in warnings[:3]:
                    line = warning.get('line', '?')
                    message = warning.get('message', '未知警告')
                    parts.append(f"- 第{line}行 [警告] {message}")
                parts.append("")
        
        # 4. 语言特定指导
        if language:
            lang_guide = PromptLibrary.get_language_guide(language)
            if lang_guide:
                parts.append(f"## {lang_guide['name']} 重构要点")
                for tip in lang_guide['tips']:
                    parts.append(f"- {tip}")
                parts.append("")
        
        # 5. 输出格式
        parts.append("## 输出格式")
        parts.append("### 问题分析")
        parts.append("[分析代码中存在的问题]")
        parts.append("")
        parts.append("### 重构方案")
        parts.append("```python")
        parts.append("[重构后的代码]")
        parts.append("```")
        parts.append("")
        parts.append("### 重构说明")
        parts.append("[解释为什么这样重构]")
        
        return "\n".join(parts)
    
    def generate_analyze_prompt(
        self,
        code: str,
        language: Optional[str] = None,
        user_message: str = ""
    ) -> str:
        """
        生成代码分析 Prompt
        
        Args:
            code: 代码内容
            language: 编程语言
            user_message: 用户消息
        
        Returns:
            str: 生成的 Prompt
        """
        parts = []
        
        # 1. 角色定义
        parts.append(PromptLibrary.get_role(CodingIntent.ANALYZE))
        parts.append("")
        
        # 2. 代码内容
        parts.append("## 待分析代码")
        parts.append("```" + (language or ""))
        parts.append(code[:2000])  # 限制长度
        parts.append("```")
        parts.append("")
        
        # 3. 语言特定指导
        if language:
            lang_guide = PromptLibrary.get_language_guide(language)
            if lang_guide:
                parts.append(f"## {lang_guide['name']} 分析要点")
                for tip in lang_guide['tips']:
                    parts.append(f"- {tip}")
                parts.append("")
        
        # 4. 输出格式
        parts.append("## 输出格式")
        parts.append("### 代码结构分析")
        parts.append("[分析代码的结构]")
        parts.append("")
        parts.append("### 潜在问题")
        parts.append("[列出潜在的问题]")
        parts.append("")
        parts.append("### 优化建议")
        parts.append("[提供优化建议]")
        
        return "\n".join(parts)
    
    def _identify_bug_type(self, error_message: str) -> Optional[Dict[str, Any]]:
        """
        识别 Bug 类型
        
        Args:
            error_message: 错误消息
        
        Returns:
            Optional[Dict[str, Any]]: Bug 类型指导
        """
        error_message_lower = error_message.lower()
        
        for error_type, guide in PromptLibrary.BUG_TYPE_GUIDES.items():
            if error_type.lower() in error_message_lower:
                return guide
        
        return None