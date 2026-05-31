# Coding Agent 设计方案

> **版本**: 1.0.0
> **日期**: 2026-05-31
> **定位**: Bug Fix + 能力补足
> **核心特性**: 动态 Prompt 生成

## 1. 定位与目标

### 1.1 核心定位

**不是**：全能的代码助手（与 IDE 竞争）

**而是**：
- **Bug Fix 专家**：快速定位和修复代码问题
- **能力补足器**：补足 API 调用时丢失的上下文

### 1.2 解决的核心问题

| 问题 | 当前状态 | Coding Agent 解决后 |
|------|----------|---------------------|
| **API 调用结果差异** | 通过 API 调用时丢失诊断、符号等上下文 | 自动获取并注入上下文 |
| **Bug 修复效率低** | 需要多轮对话才能定位问题 | 一次性获取所有信息，精准定位 |
| **Prompt 不够精准** | 静态 prompt，通用指导 | 动态生成针对性 prompt |

### 1.3 成功指标

- Bug 修复成功率 > 70%
- API 结果质量提升 > 30%（用户满意度）
- 平均修复时间 < 2 分钟

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Smart Copilot API                         │
├─────────────────────────────────────────────────────────────┤
│  /api/coding/fix-bug     Bug 修复接口                        │
│  /api/coding/enhance     API 结果增强接口                     │
│  /api/coding/analyze     代码分析接口                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Coding Agent Core                         │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Intent       │  │ Prompt       │  │ Tool         │      │
│  │ Detector     │  │ Generator    │  │ Executor     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│           │               │               │                 │
│           ▼               ▼               ▼                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Context Manager                         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    IDE Extension                             │
├─────────────────────────────────────────────────────────────┤
│  GET /diagnostics    诊断信息                                │
│  GET /symbol         符号信息                                │
│  GET /git-diff       Git diff                               │
│  POST /apply         应用修改                                │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

```python
# coding_agent/
# ├── __init__.py
# ├── core.py              # 核心 Agent 逻辑
# ├── intent_detector.py   # 意图识别
# ├── prompt_generator.py  # 动态 Prompt 生成
# ├── tool_executor.py     # 工具执行器
# ├── context_manager.py   # 上下文管理
# ├── tools/               # 工具实现
# │   ├── __init__.py
# │   ├── ide_tools.py     # IDE 工具
# │   └── analysis_tools.py # 分析工具
# └── prompts/             # Prompt 模板
#     ├── templates.py     # 模板库
#     └── strategies.py    # 策略库
```

---

## 3. 核心组件设计

### 3.1 意图识别器 (Intent Detector)

```python
# coding_agent/intent_detector.py

from enum import Enum
from typing import Optional

class CodingIntent(Enum):
    """编码意图枚举"""
    BUG_FIX = "bug_fix"           # Bug 修复
    CODE_REVIEW = "code_review"   # 代码审查
    EXPLAIN = "explain"           # 代码解释
    REFACTOR = "refactor"         # 代码重构
    ENHANCE_API = "enhance_api"   # API 结果增强
    GENERAL = "general"           # 通用

class IntentDetector:
    """意图识别器"""
    
    # 关键词映射
    KEYWORD_MAP = {
        CodingIntent.BUG_FIX: [
            "bug", "错误", "报错", "失败", "异常", "崩溃", "不工作",
            "fix", "修复", "解决", "error", "exception", "crash"
        ],
        CodingIntent.CODE_REVIEW: [
            "审查", "review", "检查", "看看", "质量", "规范",
            "check", "analyze", "quality"
        ],
        CodingIntent.EXPLAIN: [
            "解释", "explain", "什么意思", "怎么理解", "为什么",
            "what", "why", "how", "理解"
        ],
        CodingIntent.REFACTOR: [
            "重构", "refactor", "优化", "改进", "简化", "重写",
            "optimize", "improve", "simplify"
        ]
    }
    
    def detect(
        self,
        user_message: str,
        has_diagnostics: bool = False,
        has_error_message: bool = False
    ) -> CodingIntent:
        """
        检测用户意图
        
        Args:
            user_message: 用户消息
            has_diagnostics: 是否有诊断信息
            has_error_message: 是否有错误信息
        
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
        
        # 2. 关键词匹配
        for intent, keywords in self.KEYWORD_MAP.items():
            for keyword in keywords:
                if keyword in message_lower:
                    return intent
        
        # 3. 默认意图
        return CodingIntent.GENERAL
    
    def detect_from_context(self, context: dict) -> CodingIntent:
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
        
        return CodingIntent.GENERAL
```

### 3.2 动态 Prompt 生成器 (Prompt Generator)

```python
# coding_agent/prompt_generator.py

from typing import Dict, Any, Optional
from .intent_detector import CodingIntent

class PromptTemplate:
    """Prompt 模板"""
    
    def __init__(self, template: str, variables: list):
        self.template = template
        self.variables = variables
    
    def render(self, **kwargs) -> str:
        """渲染模板"""
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
        }
    }
    
    @classmethod
    def get_role(cls, intent: CodingIntent) -> str:
        """获取角色定义"""
        return cls.ROLES.get(intent, cls.ROLES[CodingIntent.BUG_FIX])
    
    @classmethod
    def get_bug_guide(cls, error_type: str) -> Optional[Dict]:
        """获取 Bug 类型指导"""
        return cls.BUG_TYPE_GUIDES.get(error_type)
    
    @classmethod
    def get_language_guide(cls, language: str) -> Optional[Dict]:
        """获取语言特定指导"""
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
        original_request: Dict[str, Any],
        api_result: str,
        enhanced_context: Dict[str, Any]
    ) -> str:
        """
        生成 API 结果增强 Prompt
        
        Args:
            original_request: 原始请求
            api_result: API 返回结果
            enhanced_context: 增强的上下文
        
        Returns:
            str: 生成的 Prompt
        """
        parts = []
        
        # 1. 角色定义
        parts.append(PromptLibrary.get_role(CodingIntent.ENHANCE_API))
        parts.append("")
        
        # 2. 原始请求分析
        parts.append("## 原始请求")
        parts.append(f"**意图**: {original_request.get('action', '未知')}")
        parts.append(f"**内容**: {original_request.get('text', '')[:500]}")
        parts.append("")
        
        # 3. 原始结果
        parts.append("## 原始 API 结果")
        parts.append(api_result[:1000])
        parts.append("")
        
        # 4. 补充的上下文
        parts.append("## 补充的上下文")
        
        if "diagnostics" in enhanced_context:
            diag = enhanced_context["diagnostics"]
            if diag.get("errors"):
                parts.append("**诊断信息**:")
                for error in diag["errors"][:3]:
                    parts.append(f"- 第{error.get('line', '?')}行: {error.get('message', '')}")
        
        if "symbol" in enhanced_context:
            symbol = enhanced_context["symbol"]
            if symbol.get("name"):
                parts.append(f"**当前符号**: {symbol['name']} ({symbol.get('kind', '')})")
        
        if "git_diff" in enhanced_context:
            diff = enhanced_context["git_diff"]
            if diff.get("diff"):
                parts.append("**最近变更**: 有未提交的修改")
        
        parts.append("")
        
        # 5. 任务
        parts.append("## 任务")
        parts.append("基于补充的上下文，重新分析并增强原始结果：")
        parts.append("1. 补充缺失的信息")
        parts.append("2. 修正可能的错误")
        parts.append("3. 提供更精准的建议")
        parts.append("")
        
        # 6. 输出格式
        parts.append("## 输出格式")
        parts.append("### 增强后的分析")
        parts.append("[基于补充上下文的增强分析]")
        parts.append("")
        parts.append("### 主要改进")
        parts.append("[说明相比原始结果的主要改进点]")
        
        return "\n".join(parts)
    
    def _identify_bug_type(self, error_message: str) -> Optional[Dict]:
        """识别 Bug 类型"""
        error_lower = error_message.lower()
        
        for error_type, guide in PromptLibrary.BUG_TYPE_GUIDES.items():
            if error_type.lower() in error_lower:
                return guide
        
        return None
```

### 3.3 工具执行器 (Tool Executor)

```python
# coding_agent/tool_executor.py

import asyncio
from typing import Dict, Any, Optional, List
import aiohttp

class IDEToolExecutor:
    """IDE 工具执行器"""
    
    def __init__(self, ide_port: int = None):
        self.ide_port = ide_port
        self._port_cache = None
    
    async def _get_ide_port(self) -> int:
        """获取 IDE 端口"""
        if self.ide_port:
            return self.ide_port
        
        if self._port_cache:
            return self._port_cache
        
        # 从临时文件读取端口
        import os
        port_file = os.path.join(os.tmpdir(), 'asu_ide_port.txt')
        if os.path.exists(port_file):
            with open(port_file, 'r') as f:
                self._port_cache = int(f.read().strip())
                return self._port_cache
        
        raise RuntimeError("IDE Extension 未启动或端口文件不存在")
    
    async def get_diagnostics(self, file_path: str = None) -> Dict[str, Any]:
        """获取诊断信息"""
        try:
            port = await self._get_ide_port()
            url = f"http://localhost:{port}/diagnostics"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self._parse_diagnostics(data)
                    else:
                        return {"errors": [], "warnings": [], "raw": {}}
        except Exception as e:
            return {"errors": [], "warnings": [], "error": str(e)}
    
    async def get_symbol(self, file_path: str = None, line: int = None) -> Dict[str, Any]:
        """获取符号信息"""
        try:
            port = await self._get_ide_port()
            url = f"http://localhost:{port}/symbol"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_git_diff(self, file_path: str = None) -> Dict[str, Any]:
        """获取 Git diff"""
        try:
            port = await self._get_ide_port()
            url = f"http://localhost:{port}/git-diff"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {"diff": ""}
        except Exception as e:
            return {"diff": "", "error": str(e)}
    
    async def apply_change(
        self,
        content: str = None,
        replace: str = None,
        range_info: Dict = None,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """应用修改到 IDE"""
        if not confirm:
            return {
                "status": "pending",
                "message": "需要用户确认",
                "preview": (content or replace or "")[:500]
            }
        
        try:
            port = await self._get_ide_port()
            url = f"http://localhost:{port}/apply"
            
            payload = {}
            if content:
                payload["content"] = content
            if replace:
                payload["replace"] = replace
            if range_info:
                payload["range"] = range_info
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_diagnostics(self, raw_data: Dict) -> Dict[str, Any]:
        """解析诊断信息"""
        diagnostics = raw_data.get("diagnostics", [])
        
        errors = []
        warnings = []
        
        for diag in diagnostics:
            severity = diag.get("severity", 0)
            item = {
                "line": diag.get("line", 0),
                "character": diag.get("character", 0),
                "message": diag.get("message", ""),
                "code": diag.get("code", ""),
                "source": diag.get("source", "")
            }
            
            if severity == 0:  # Error
                errors.append(item)
            elif severity == 1:  # Warning
                warnings.append(item)
        
        return {
            "errors": errors,
            "warnings": warnings,
            "file": raw_data.get("fileName", ""),
            "raw": raw_data
        }

class ToolExecutor:
    """工具执行器（整合多个工具源）"""
    
    def __init__(self, ide_port: int = None):
        self.ide_executor = IDEToolExecutor(ide_port)
    
    async def gather_context(
        self,
        file_path: str = None,
        line_number: int = None,
        include_diagnostics: bool = True,
        include_symbol: bool = True,
        include_git_diff: bool = True
    ) -> Dict[str, Any]:
        """
        并行收集上下文信息
        
        Args:
            file_path: 文件路径
            line_number: 行号
            include_diagnostics: 是否包含诊断信息
            include_symbol: 是否包含符号信息
            include_git_diff: 是否包含 Git diff
        
        Returns:
            Dict: 收集到的上下文
        """
        tasks = {}
        
        if include_diagnostics:
            tasks["diagnostics"] = self.ide_executor.get_diagnostics(file_path)
        
        if include_symbol and line_number:
            tasks["symbol"] = self.ide_executor.get_symbol(file_path, line_number)
        
        if include_git_diff:
            tasks["git_diff"] = self.ide_executor.get_git_diff(file_path)
        
        # 并行执行
        results = {}
        if tasks:
            task_list = list(tasks.values())
            task_names = list(tasks.keys())
            
            completed = await asyncio.gather(*task_list, return_exceptions=True)
            
            for name, result in zip(task_names, completed):
                if isinstance(result, Exception):
                    results[name] = {"error": str(result)}
                else:
                    results[name] = result
        
        return results
```

### 3.4 核心 Agent (Coding Agent)

```python
# coding_agent/core.py

from typing import Dict, Any, Optional
from .intent_detector import IntentDetector, CodingIntent
from .prompt_generator import PromptGenerator
from .tool_executor import ToolExecutor

class CodingAgent:
    """
    Coding Agent 核心
    
    定位：Bug Fix + 能力补足
    特性：动态 Prompt 生成
    """
    
    def __init__(self, llm_provider=None, ide_port: int = None):
        """
        初始化 Coding Agent
        
        Args:
            llm_provider: LLM 提供者
            ide_port: IDE Extension 端口
        """
        self.llm_provider = llm_provider
        self.intent_detector = IntentDetector()
        self.prompt_generator = PromptGenerator()
        self.tool_executor = ToolExecutor(ide_port)
    
    async def fix_bug(
        self,
        file_path: str = None,
        error_message: str = None,
        line_number: int = None,
        user_message: str = "",
        language: str = None
    ) -> Dict[str, Any]:
        """
        Bug 修复流程
        
        Args:
            file_path: 文件路径
            error_message: 错误信息
            line_number: 错误行号
            user_message: 用户描述
            language: 编程语言
        
        Returns:
            Dict: 修复结果
        """
        # 1. 收集上下文
        context = await self.tool_executor.gather_context(
            file_path=file_path,
            line_number=line_number,
            include_diagnostics=True,
            include_symbol=bool(line_number),
            include_git_diff=True
        )
        
        # 2. 动态生成 Prompt
        prompt = self.prompt_generator.generate_bug_fix_prompt(
            diagnostics=context.get("diagnostics", {}),
            symbol_info=context.get("symbol"),
            git_diff=context.get("git_diff"),
            language=language,
            user_message=user_message
        )
        
        # 3. 调用 LLM
        response = await self._call_llm(prompt, context)
        
        # 4. 解析响应
        parsed = self._parse_bug_fix_response(response)
        
        return {
            "analysis": parsed.get("analysis", ""),
            "fix_suggestion": parsed.get("fix_suggestion", ""),
            "explanation": parsed.get("explanation", ""),
            "context_used": context,
            "prompt_generated": prompt,
            "confidence": self._calculate_confidence(context)
        }
    
    async def enhance_api_result(
        self,
        original_request: Dict[str, Any],
        api_result: str,
        file_path: str = None
    ) -> Dict[str, Any]:
        """
        API 结果增强
        
        Args:
            original_request: 原始请求
            api_result: API 返回结果
            file_path: 文件路径（可选）
        
        Returns:
            Dict: 增强结果
        """
        # 1. 收集补充上下文
        enhanced_context = await self.tool_executor.gather_context(
            file_path=file_path,
            include_diagnostics=True,
            include_symbol=False,
            include_git_diff=True
        )
        
        # 2. 动态生成 Prompt
        prompt = self.prompt_generator.generate_enhance_prompt(
            original_request=original_request,
            api_result=api_result,
            enhanced_context=enhanced_context
        )
        
        # 3. 调用 LLM
        response = await self._call_llm(prompt, enhanced_context)
        
        return {
            "enhanced_result": response,
            "added_context": enhanced_context,
            "prompt_generated": prompt,
            "improvement_summary": self._extract_improvements(response)
        }
    
    async def analyze_code(
        self,
        file_path: str = None,
        line_number: int = None,
        analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """
        代码分析
        
        Args:
            file_path: 文件路径
            line_number: 行号
            analysis_type: 分析类型
        
        Returns:
            Dict: 分析结果
        """
        # 收集上下文
        context = await self.tool_executor.gather_context(
            file_path=file_path,
            line_number=line_number,
            include_diagnostics=True,
            include_symbol=bool(line_number),
            include_git_diff=True
        )
        
        # 生成分析 Prompt
        prompt = self._generate_analysis_prompt(context, analysis_type)
        
        # 调用 LLM
        response = await self._call_llm(prompt, context)
        
        return {
            "analysis": response,
            "context_used": context,
            "prompt_generated": prompt
        }
    
    async def _call_llm(self, prompt: str, context: Dict) -> str:
        """调用 LLM"""
        if not self.llm_provider:
            return "错误：LLM Provider 未初始化"
        
        try:
            # 构建消息
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": self._build_user_message(context)}
            ]
            
            # 调用 LLM
            response = ""
            for chunk in self.llm_provider.stream_chat_with_history(messages):
                response += chunk
            
            return response
        except Exception as e:
            return f"调用 LLM 失败: {str(e)}"
    
    def _build_user_message(self, context: Dict) -> str:
        """构建用户消息"""
        parts = ["请根据以上指导分析并解决问题。"]
        
        # 添加诊断信息摘要
        diagnostics = context.get("diagnostics", {})
        errors = diagnostics.get("errors", [])
        if errors:
            parts.append(f"\n当前有 {len(errors)} 个错误需要修复。")
        
        return "\n".join(parts)
    
    def _parse_bug_fix_response(self, response: str) -> Dict[str, str]:
        """解析 Bug 修复响应"""
        # 简单的解析逻辑，后续可以用更复杂的 NLP
        parts = {
            "analysis": "",
            "fix_suggestion": "",
            "explanation": ""
        }
        
        # 查找各个部分
        if "### 问题分析" in response:
            start = response.find("### 问题分析") + len("### 问题分析")
            end = response.find("###", start)
            if end == -1:
                end = len(response)
            parts["analysis"] = response[start:end].strip()
        
        if "### 修复方案" in response:
            start = response.find("### 修复方案") + len("### 修复方案")
            end = response.find("###", start)
            if end == -1:
                end = len(response)
            parts["fix_suggestion"] = response[start:end].strip()
        
        if "### 修复说明" in response:
            start = response.find("### 修复说明") + len("### 修复说明")
            parts["explanation"] = response[start:].strip()
        
        # 如果解析失败，使用整个响应
        if not any(parts.values()):
            parts["analysis"] = response
        
        return parts
    
    def _calculate_confidence(self, context: Dict) -> float:
        """计算置信度"""
        confidence = 0.5  # 基础置信度
        
        # 有诊断信息增加置信度
        diagnostics = context.get("diagnostics", {})
        if diagnostics.get("errors"):
            confidence += 0.2
        
        # 有符号信息增加置信度
        if context.get("symbol"):
            confidence += 0.1
        
        # 有 Git diff 增加置信度
        if context.get("git_diff", {}).get("diff"):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _extract_improvements(self, response: str) -> str:
        """提取改进摘要"""
        if "### 主要改进" in response:
            start = response.find("### 主要改进") + len("### 主要改进")
            return response[start:].strip()[:500]
        return "已基于补充上下文增强分析结果"
    
    def _generate_analysis_prompt(self, context: Dict, analysis_type: str) -> str:
        """生成分析 Prompt"""
        parts = ["你是一个代码分析专家。"]
        
        parts.append(f"\n## 分析类型: {analysis_type}")
        
        parts.append("\n## 代码上下文")
        
        # 添加诊断信息
        diagnostics = context.get("diagnostics", {})
        if diagnostics.get("errors"):
            parts.append("\n### 诊断信息")
            for error in diagnostics["errors"][:5]:
                parts.append(f"- 第{error.get('line', '?')}行: {error.get('message', '')}")
        
        # 添加符号信息
        symbol = context.get("symbol", {})
        if symbol.get("name"):
            parts.append(f"\n### 当前符号: {symbol['name']} ({symbol.get('kind', '')})")
        
        parts.append("\n## 任务")
        parts.append("请分析代码质量、潜在问题和改进建议。")
        
        return "\n".join(parts)
```

---

## 4. API 设计

### 4.1 请求/响应模型

```python
# coding_agent/models.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum

class CodingIntentEnum(str, Enum):
    """编码意图枚举"""
    BUG_FIX = "bug_fix"
    CODE_REVIEW = "code_review"
    EXPLAIN = "explain"
    REFACTOR = "refactor"
    ENHANCE_API = "enhance_api"
    GENERAL = "general"

class BugFixRequest(BaseModel):
    """Bug 修复请求"""
    file_path: Optional[str] = Field(None, description="文件路径")
    error_message: Optional[str] = Field(None, description="错误信息")
    line_number: Optional[int] = Field(None, description="错误行号")
    description: Optional[str] = Field(None, description="问题描述")
    language: Optional[str] = Field(None, description="编程语言")
    return_prompt: bool = Field(False, description="是否返回生成的 prompt")

class BugFixResponse(BaseModel):
    """Bug 修复响应"""
    analysis: str = Field(..., description="问题分析")
    fix_suggestion: str = Field(..., description="修复建议")
    explanation: str = Field(..., description="修复说明")
    confidence: float = Field(..., description="置信度 (0-1)")
    prompt_used: Optional[str] = Field(None, description="使用的 prompt")

class EnhanceRequest(BaseModel):
    """API 结果增强请求"""
    original_request: Dict[str, Any] = Field(..., description="原始请求")
    api_result: str = Field(..., description="API 返回结果")
    file_path: Optional[str] = Field(None, description="文件路径")

class EnhanceResponse(BaseModel):
    """API 结果增强响应"""
    enhanced_result: str = Field(..., description="增强后的结果")
    added_context: Dict[str, Any] = Field(..., description="补充的上下文")
    improvement_summary: str = Field(..., description="改进摘要")
    prompt_used: Optional[str] = Field(None, description="使用的 prompt")

class AnalyzeRequest(BaseModel):
    """代码分析请求"""
    file_path: Optional[str] = Field(None, description="文件路径")
    line_number: Optional[int] = Field(None, description="行号")
    analysis_type: str = Field("general", description="分析类型")

class AnalyzeResponse(BaseModel):
    """代码分析响应"""
    analysis: str = Field(..., description="分析结果")
    prompt_used: Optional[str] = Field(None, description="使用的 prompt")
```

### 4.2 API 端点

```python
# smart_copilot_api.py 新增

from coding_agent import CodingAgent
from coding_agent.models import (
    BugFixRequest, BugFixResponse,
    EnhanceRequest, EnhanceResponse,
    AnalyzeRequest, AnalyzeResponse
)

# 全局实例
coding_agent = None

@app.on_event("startup")
async def startup_coding_agent():
    """初始化 Coding Agent"""
    global coding_agent
    coding_agent = CodingAgent(
        llm_provider=provider,
        ide_port=None  # 自动检测
    )

@app.post("/api/coding/fix-bug", response_model=BugFixResponse)
async def fix_bug(request: BugFixRequest):
    """
    Bug 修复接口
    
    自动获取诊断信息、符号上下文，动态生成 Prompt，精准定位和修复 bug
    """
    if not coding_agent:
        raise HTTPException(status_code=500, detail="Coding Agent 未初始化")
    
    result = await coding_agent.fix_bug(
        file_path=request.file_path,
        error_message=request.error_message,
        line_number=request.line_number,
        user_message=request.description or "",
        language=request.language
    )
    
    return BugFixResponse(
        analysis=result["analysis"],
        fix_suggestion=result["fix_suggestion"],
        explanation=result["explanation"],
        confidence=result["confidence"],
        prompt_used=result.get("prompt_generated") if request.return_prompt else None
    )

@app.post("/api/coding/enhance", response_model=EnhanceResponse)
async def enhance_api_result(request: EnhanceRequest):
    """
    API 结果增强接口
    
    补充缺失的上下文，提升 API 调用结果的质量
    """
    if not coding_agent:
        raise HTTPException(status_code=500, detail="Coding Agent 未初始化")
    
    result = await coding_agent.enhance_api_result(
        original_request=request.original_request,
        api_result=request.api_result,
        file_path=request.file_path
    )
    
    return EnhanceResponse(
        enhanced_result=result["enhanced_result"],
        added_context=result["added_context"],
        improvement_summary=result["improvement_summary"],
        prompt_used=result.get("prompt_generated") if request.return_prompt else None
    )

@app.post("/api/coding/analyze", response_model=AnalyzeResponse)
async def analyze_code(request: AnalyzeRequest):
    """
    代码分析接口
    
    提供代码质量分析、问题检测等功能
    """
    if not coding_agent:
        raise HTTPException(status_code=500, detail="Coding Agent 未初始化")
    
    result = await coding_agent.analyze_code(
        file_path=request.file_path,
        line_number=request.line_number,
        analysis_type=request.analysis_type
    )
    
    return AnalyzeResponse(
        analysis=result["analysis"],
        prompt_used=result.get("prompt_generated") if request.return_prompt else None
    )
```

---

## 5. 文件结构

```
OpenCopilot/
├── coding_agent/
│   ├── __init__.py
│   ├── core.py                 # 核心 Agent
│   ├── intent_detector.py      # 意图识别
│   ├── prompt_generator.py     # Prompt 生成
│   ├── tool_executor.py        # 工具执行
│   └── models.py               # 数据模型
├── smart_copilot_api.py        # API 端点（新增 coding 相关）
└── test_coding_agent.py        # 测试文件
```

---

## 6. 实现计划

### 阶段 1：核心框架（3-5 天）

**目标**：实现基本的 Bug Fix 流程

1. **Day 1-2**: 实现核心组件
   - `intent_detector.py` - 意图识别
   - `prompt_generator.py` - Prompt 生成
   - `tool_executor.py` - 工具执行

2. **Day 3-4**: 实现 Agent 核心
   - `core.py` - Bug Fix 流程
   - 集成 LLM Provider

3. **Day 5**: API 集成
   - 添加 `/api/coding/fix-bug` 端点
   - 基本测试

**交付物**：
- 可工作的 Bug Fix API
- 基本的动态 Prompt 生成

### 阶段 2：能力补足（3-5 天）

**目标**：实现 API 结果增强

1. **Day 1-2**: 增强 Prompt 生成
   - 支持更多 Bug 类型
   - 支持语言特定指导

2. **Day 3-4**: 实现增强流程
   - `enhance_api_result` 方法
   - 上下文补充逻辑

3. **Day 5**: API 集成
   - 添加 `/api/coding/enhance` 端点
   - 测试验证

**交付物**：
- API 结果增强功能
- 完整的 Prompt 模板库

### 阶段 3：优化完善（3-5 天）

**目标**：优化用户体验和准确性

1. **Day 1-2**: 准确性优化
   - 改进意图识别
   - 改进 Prompt 质量

2. **Day 3-4**: 用户体验
   - 添加置信度
   - 改进错误处理

3. **Day 5**: 文档和测试
   - 编写使用文档
   - 完善测试用例

**交付物**：
- 优化后的 Coding Agent
- 完整的文档和测试

---

## 7. 测试验证

### 7.1 测试用例设计

```python
# test_coding_agent.py

import pytest
from coding_agent import CodingAgent
from coding_agent.intent_detector import IntentDetector, CodingIntent

class TestIntentDetector:
    """意图识别测试"""
    
    def test_bug_fix_intent(self):
        """测试 Bug Fix 意图识别"""
        detector = IntentDetector()
        
        # 明确的 bug fix 关键词
        assert detector.detect("这个函数报错了") == CodingIntent.BUG_FIX
        assert detector.detect("帮我修复这个 bug") == CodingIntent.BUG_FIX
        assert detector.detect("error occurred") == CodingIntent.BUG_FIX
        
        # 有诊断信息时
        assert detector.detect(
            "帮我看看",
            has_diagnostics=True
        ) == CodingIntent.BUG_FIX
    
    def test_code_review_intent(self):
        """测试代码审查意图"""
        detector = IntentDetector()
        
        assert detector.detect("帮我审查这个代码") == CodingIntent.CODE_REVIEW
        assert detector.detect("code review") == CodingIntent.CODE_REVIEW
    
    def test_explain_intent(self):
        """测试解释意图"""
        detector = IntentDetector()
        
        assert detector.detect("这段代码什么意思") == CodingIntent.EXPLAIN
        assert detector.detect("explain this") == CodingIntent.EXPLAIN
    
    def test_general_intent(self):
        """测试通用意图"""
        detector = IntentDetector()
        
        assert detector.detect("你好") == CodingIntent.GENERAL
        assert detector.detect("今天天气怎么样") == CodingIntent.GENERAL

class TestPromptGenerator:
    """Prompt 生成测试"""
    
    def test_bug_fix_prompt_with_diagnostics(self):
        """测试有诊断信息的 Bug Fix Prompt"""
        generator = PromptGenerator()
        
        diagnostics = {
            "errors": [
                {"line": 15, "message": "NameError: name 'x' is not defined"}
            ]
        }
        
        prompt = generator.generate_bug_fix_prompt(
            diagnostics=diagnostics,
            language="python"
        )
        
        assert "NameError" in prompt
        assert "变量未定义错误" in prompt
        assert "Python 特定提示" in prompt
    
    def test_bug_fix_prompt_without_diagnostics(self):
        """测试无诊断信息的 Bug Fix Prompt"""
        generator = PromptGenerator()
        
        prompt = generator.generate_bug_fix_prompt(
            diagnostics={},
            user_message="这个函数有问题"
        )
        
        assert "Bug 修复专家" in prompt
        assert "输出格式" in prompt

class TestCodingAgent:
    """Coding Agent 测试"""
    
    @pytest.mark.asyncio
    async def test_fix_bug_flow(self):
        """测试 Bug Fix 流程"""
        # Mock LLM Provider
        class MockLLMProvider:
            def stream_chat_with_history(self, messages):
                yield "### 问题分析\n测试分析"
                yield "\n\n### 修复方案\n```python\n# 修复\n```"
                yield "\n\n### 修复说明\n测试说明"
        
        agent = CodingAgent(llm_provider=MockLLMProvider())
        
        result = await agent.fix_bug(
            error_message="NameError: name 'x' is not defined",
            user_message="这个函数报错了"
        )
        
        assert "analysis" in result
        assert "fix_suggestion" in result
        assert "confidence" in result
```

### 7.2 验收标准

| 功能 | 验收标准 | 测试方法 |
|------|----------|----------|
| **意图识别** | 准确率 > 90% | 单元测试 |
| **Prompt 生成** | 包含必要的上下文 | 人工审查 |
| **Bug Fix** | 成功率 > 70% | 真实案例测试 |
| **API 增强** | 结果质量提升 > 30% | A/B 测试 |

---

## 8. 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| **IDE Extension 未启动** | 工具调用失败 | 降级为纯文本分析 |
| **LLM 理解错误** | 修复建议不准确 | 添加置信度，用户确认 |
| **诊断信息不准确** | 误判问题 | 结合多种信息源 |
| **性能问题** | 响应慢 | 异步并行，缓存 |

---

## 9. 总结

### 核心价值

1. **聚焦**：只做 Bug Fix 和能力补足，不做全能助手
2. **智能**：动态生成针对性 Prompt，提升准确性
3. **补足**：解决 API 调用时的上下文丢失问题
4. **可行**：复用现有架构，实现复杂度可控

### 差异化优势

- **vs IDE 插件**：不竞争，而是补足 API 调用的差异
- **vs 通用 Agent**：聚焦代码场景，更专业
- **vs 静态 Prompt**：动态生成，更精准

### 预期效果

- Bug 修复效率提升 50%+
- API 结果质量提升 30%+
- 用户满意度显著提升
