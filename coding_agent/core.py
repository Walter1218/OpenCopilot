"""
Coding Agent 核心

实现 Coding Agent 的核心逻辑，包括 Bug 修复、API 结果增强、代码分析等功能。
"""

from typing import Dict, Any, Optional, List
from .intent_detector import IntentDetector, CodingIntent
from .prompt_generator import PromptGenerator
from .tool_executor import ToolExecutor


class CodingAgent:
    """
    Coding Agent 核心
    
    定位：Bug Fix + 能力补足
    特性：动态 Prompt 生成
    """
    
    def __init__(self, llm_provider=None, ide_port: Optional[int] = None, project_root: Optional[str] = None):
        """
        初始化 Coding Agent
        
        Args:
            llm_provider: LLM 提供者
            ide_port: IDE Extension 端口
            project_root: 项目根目录
        """
        self.llm_provider = llm_provider
        self.intent_detector = IntentDetector()
        self.prompt_generator = PromptGenerator()
        self.tool_executor = ToolExecutor(ide_port, project_root)
    
    async def fix_bug(
        self,
        file_path: Optional[str] = None,
        error_message: Optional[str] = None,
        line_number: Optional[int] = None,
        user_message: str = "",
        language: Optional[str] = None
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
            Dict[str, Any]: 修复结果
        """
        # 1. 收集上下文
        context = await self.tool_executor.get_full_context(file_path, line_number)
        
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
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        API 结果增强
        
        Args:
            original_request: 原始请求
            api_result: API 返回结果
            file_path: 文件路径（可选）
        
        Returns:
            Dict[str, Any]: 增强结果
        """
        # 1. 收集补充上下文
        context = await self.tool_executor.get_full_context(file_path)
        
        # 2. 动态生成 Prompt
        prompt = self.prompt_generator.generate_enhance_prompt(
            api_result={"content": api_result},
            context=context,
            user_message=original_request.get("text", "")
        )
        
        # 3. 调用 LLM
        response = await self._call_llm(prompt, context)
        
        # 4. 解析响应
        parsed = self._parse_enhance_response(response)
        
        return {
            "enhanced_result": parsed.get("enhanced_result", ""),
            "improvements": parsed.get("improvements", ""),
            "context_used": context,
            "prompt_generated": prompt
        }
    
    async def analyze_code(
        self,
        file_path: Optional[str] = None,
        code: Optional[str] = None,
        language: Optional[str] = None,
        user_message: str = ""
    ) -> Dict[str, Any]:
        """
        代码分析
        
        Args:
            file_path: 文件路径
            code: 代码内容
            language: 编程语言
            user_message: 用户消息
        
        Returns:
            Dict[str, Any]: 分析结果
        """
        # 1. 获取代码内容
        if code is None and file_path:
            file_content = await self.tool_executor.analysis_executor.read_file(file_path)
            code = file_content.get("content", "")
        
        # 2. 动态生成 Prompt
        prompt = self.prompt_generator.generate_analyze_prompt(
            code=code or "",
            language=language,
            user_message=user_message
        )
        
        # 3. 调用 LLM
        response = await self._call_llm(prompt, {})
        
        # 4. 解析响应
        parsed = self._parse_analyze_response(response)
        
        return {
            "analysis": parsed.get("analysis", ""),
            "issues": parsed.get("issues", []),
            "suggestions": parsed.get("suggestions", []),
            "prompt_generated": prompt
        }
    
    async def review_code(
        self,
        file_path: Optional[str] = None,
        code: Optional[str] = None,
        language: Optional[str] = None,
        user_message: str = ""
    ) -> Dict[str, Any]:
        """
        代码审查
        
        Args:
            file_path: 文件路径
            code: 代码内容
            language: 编程语言
            user_message: 用户消息
        
        Returns:
            Dict[str, Any]: 审查结果
        """
        # 1. 获取代码内容
        if code is None and file_path:
            file_content = await self.tool_executor.analysis_executor.read_file(file_path)
            code = file_content.get("content", "")
        
        # 2. 获取上下文
        context = await self.tool_executor.get_full_context(file_path)
        
        # 3. 动态生成 Prompt
        prompt = self.prompt_generator.generate_code_review_prompt(
            code=code or "",
            git_diff=context.get("git_diff"),
            language=language,
            user_message=user_message
        )
        
        # 4. 调用 LLM
        response = await self._call_llm(prompt, context)
        
        # 5. 解析响应
        parsed = self._parse_review_response(response)
        
        return {
            "review": parsed.get("review", ""),
            "issues": parsed.get("issues", []),
            "suggestions": parsed.get("suggestions", []),
            "score": parsed.get("score", 0),
            "context_used": context,
            "prompt_generated": prompt
        }
    
    async def explain_code(
        self,
        file_path: Optional[str] = None,
        code: Optional[str] = None,
        line_number: Optional[int] = None,
        language: Optional[str] = None,
        user_message: str = ""
    ) -> Dict[str, Any]:
        """
        代码解释
        
        Args:
            file_path: 文件路径
            code: 代码内容
            line_number: 行号
            language: 编程语言
            user_message: 用户消息
        
        Returns:
            Dict[str, Any]: 解释结果
        """
        # 1. 获取代码内容
        if code is None and file_path:
            file_content = await self.tool_executor.analysis_executor.read_file(file_path)
            code = file_content.get("content", "")
        
        # 2. 获取符号信息
        symbol_info = None
        if file_path and line_number:
            symbol_info = await self.tool_executor.ide_executor.get_symbol(file_path, line_number)
        
        # 3. 动态生成 Prompt
        prompt = self.prompt_generator.generate_explain_prompt(
            code=code or "",
            symbol_info=symbol_info,
            language=language,
            user_message=user_message
        )
        
        # 4. 调用 LLM
        response = await self._call_llm(prompt, {})
        
        # 5. 解析响应
        parsed = self._parse_explain_response(response)
        
        return {
            "explanation": parsed.get("explanation", ""),
            "key_points": parsed.get("key_points", []),
            "prompt_generated": prompt
        }
    
    async def refactor_code(
        self,
        file_path: Optional[str] = None,
        code: Optional[str] = None,
        language: Optional[str] = None,
        user_message: str = ""
    ) -> Dict[str, Any]:
        """
        代码重构
        
        Args:
            file_path: 文件路径
            code: 代码内容
            language: 编程语言
            user_message: 用户消息
        
        Returns:
            Dict[str, Any]: 重构结果
        """
        # 1. 获取代码内容
        if code is None and file_path:
            file_content = await self.tool_executor.analysis_executor.read_file(file_path)
            code = file_content.get("content", "")
        
        # 2. 获取上下文
        context = await self.tool_executor.get_full_context(file_path)
        
        # 3. 动态生成 Prompt
        prompt = self.prompt_generator.generate_refactor_prompt(
            code=code or "",
            diagnostics=context.get("diagnostics"),
            language=language,
            user_message=user_message
        )
        
        # 4. 调用 LLM
        response = await self._call_llm(prompt, context)
        
        # 5. 解析响应
        parsed = self._parse_refactor_response(response)
        
        return {
            "refactored_code": parsed.get("refactored_code", ""),
            "changes": parsed.get("changes", []),
            "explanation": parsed.get("explanation", ""),
            "context_used": context,
            "prompt_generated": prompt
        }
    
    async def _call_llm(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        调用 LLM
        
        Args:
            prompt: Prompt
            context: 上下文
        
        Returns:
            str: LLM 响应
        """
        if self.llm_provider is None:
            # 如果没有 LLM 提供者，返回模拟响应
            return self._generate_mock_response(prompt, context)
        
        try:
            # 调用 LLM
            response = await self.llm_provider.generate(prompt)
            return response
        except Exception as e:
            # 如果调用失败，返回错误信息
            return f"调用 LLM 失败: {str(e)}"
    
    def _generate_mock_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """
        生成模拟响应（用于测试）
        
        Args:
            prompt: Prompt
            context: 上下文
        
        Returns:
            str: 模拟响应
        """
        # 根据 prompt 内容生成模拟响应
        if "Bug 类型分析" in prompt:
            return """### 问题分析
根据诊断信息，代码中存在一个错误。

### 修复方案
```python
# 修复后的代码
def example_function():
    return True
```

### 修复说明
修复了代码中的错误。"""
        
        elif "API 结果分析" in prompt:
            return """### 增强后的分析
基于补充的上下文信息，对原始分析结果进行了增强。

### 主要改进
1. 补充了诊断信息
2. 添加了符号信息
3. 整合了 Git diff"""
        
        elif "待审查代码" in prompt:
            return """### 问题列表
1. 代码风格问题
2. 潜在的性能问题

### 改进建议
1. 添加类型注解
2. 优化循环结构

### 代码质量评分
7/10"""
        
        elif "待解释代码" in prompt:
            return """### 功能说明
这段代码实现了一个功能。

### 工作原理
通过特定的算法实现。

### 关键点
1. 使用了特定的数据结构
2. 采用了优化的算法"""
        
        elif "待重构代码" in prompt:
            return """### 问题分析
代码存在一些可以改进的地方。

### 重构方案
```python
# 重构后的代码
def improved_function():
    return True
```

### 重构说明
重构提高了代码的可读性和性能。"""
        
        elif "待分析代码" in prompt:
            return """### 代码结构分析
代码结构清晰，遵循了良好的编程实践。

### 潜在问题
1. 缺少错误处理
2. 缺少类型注解

### 优化建议
1. 添加异常处理
2. 添加类型注解
3. 优化性能"""
        
        else:
            return "这是一个模拟响应。"
    
    def _parse_bug_fix_response(self, response: str) -> Dict[str, str]:
        """
        解析 Bug 修复响应
        
        Args:
            response: LLM 响应
        
        Returns:
            Dict[str, str]: 解析结果
        """
        result = {
            "analysis": "",
            "fix_suggestion": "",
            "explanation": ""
        }
        
        # 简单的解析逻辑
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            if "### 问题分析" in line:
                current_section = "analysis"
            elif "### 修复方案" in line:
                current_section = "fix_suggestion"
            elif "### 修复说明" in line:
                current_section = "explanation"
            elif current_section and line.strip():
                result[current_section] += line + "\n"
        
        return result
    
    def _parse_enhance_response(self, response: str) -> Dict[str, str]:
        """
        解析增强响应
        
        Args:
            response: LLM 响应
        
        Returns:
            Dict[str, str]: 解析结果
        """
        result = {
            "enhanced_result": "",
            "improvements": ""
        }
        
        # 简单的解析逻辑
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            if "### 增强后的分析" in line:
                current_section = "enhanced_result"
            elif "### 主要改进" in line:
                current_section = "improvements"
            elif current_section and line.strip():
                result[current_section] += line + "\n"
        
        return result
    
    def _parse_analyze_response(self, response: str) -> Dict[str, Any]:
        """
        解析分析响应
        
        Args:
            response: LLM 响应
        
        Returns:
            Dict[str, Any]: 解析结果
        """
        result = {
            "analysis": "",
            "issues": [],
            "suggestions": []
        }
        
        # 简单的解析逻辑
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            if "### 代码结构分析" in line:
                current_section = "analysis"
            elif "### 潜在问题" in line:
                current_section = "issues"
            elif "### 优化建议" in line:
                current_section = "suggestions"
            elif current_section and line.strip():
                if current_section == "analysis":
                    result[current_section] += line + "\n"
                else:
                    # 提取列表项
                    if line.startswith("- ") or line.startswith("* "):
                        result[current_section].append(line[2:])
        
        return result
    
    def _parse_review_response(self, response: str) -> Dict[str, Any]:
        """
        解析审查响应
        
        Args:
            response: LLM 响应
        
        Returns:
            Dict[str, Any]: 解析结果
        """
        result = {
            "review": "",
            "issues": [],
            "suggestions": [],
            "score": 0
        }
        
        # 简单的解析逻辑
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            if "### 问题列表" in line:
                current_section = "issues"
            elif "### 改进建议" in line:
                current_section = "suggestions"
            elif "### 代码质量评分" in line:
                current_section = "score"
            elif current_section and line.strip():
                if current_section == "score":
                    # 提取评分
                    try:
                        score_str = line.split("/")[0].strip()
                        result["score"] = int(score_str)
                    except:
                        pass
                elif current_section in ["issues", "suggestions"]:
                    # 提取列表项
                    if line.startswith("- ") or line.startswith("* "):
                        result[current_section].append(line[2:])
                    elif line[0].isdigit() and ". " in line:
                        result[current_section].append(line.split(". ", 1)[1])
        
        return result
    
    def _parse_explain_response(self, response: str) -> Dict[str, Any]:
        """
        解析解释响应
        
        Args:
            response: LLM 响应
        
        Returns:
            Dict[str, Any]: 解析结果
        """
        result = {
            "explanation": "",
            "key_points": []
        }
        
        # 简单的解析逻辑
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            if "### 功能说明" in line:
                current_section = "explanation"
            elif "### 关键点" in line:
                current_section = "key_points"
            elif current_section and line.strip():
                if current_section == "explanation":
                    result[current_section] += line + "\n"
                else:
                    # 提取列表项
                    if line.startswith("- ") or line.startswith("* "):
                        result[current_section].append(line[2:])
        
        return result
    
    def _parse_refactor_response(self, response: str) -> Dict[str, Any]:
        """
        解析重构响应
        
        Args:
            response: LLM 响应
        
        Returns:
            Dict[str, Any]: 解析结果
        """
        result = {
            "refactored_code": "",
            "changes": [],
            "explanation": ""
        }
        
        # 简单的解析逻辑
        lines = response.split('\n')
        current_section = None
        in_code_block = False
        code_lines = []
        
        for line in lines:
            if "### 重构方案" in line:
                current_section = "refactored_code"
            elif "### 重构说明" in line:
                current_section = "explanation"
            elif current_section and line.strip():
                if current_section == "refactored_code":
                    if line.startswith("```"):
                        in_code_block = not in_code_block
                    elif in_code_block:
                        code_lines.append(line)
                elif current_section == "explanation":
                    result[current_section] += line + "\n"
        
        result["refactored_code"] = "\n".join(code_lines)
        
        return result
    
    def _calculate_confidence(self, context: Dict[str, Any]) -> float:
        """
        计算置信度
        
        Args:
            context: 上下文
        
        Returns:
            float: 置信度 (0-1)
        """
        confidence = 0.5  # 基础置信度
        
        # 诊断信息
        diagnostics = context.get("diagnostics", {})
        errors = diagnostics.get("errors", [])
        if errors:
            confidence += 0.2
        
        # 符号信息
        symbol = context.get("symbol", {})
        if symbol and not symbol.get("error"):
            confidence += 0.1
        
        # Git diff
        git_diff = context.get("git_diff", {})
        if git_diff and git_diff.get("diff"):
            confidence += 0.1
        
        # 文件内容
        file_content = context.get("file_content", {})
        if file_content and file_content.get("content"):
            confidence += 0.1
        
        return min(1.0, confidence)