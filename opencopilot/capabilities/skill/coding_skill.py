"""
CodingSkill - 编码 Skill

将 Coding Agent 封装为 Skill，支持 Bug 修复、API 结果增强、代码分析等功能。
"""

import os
import logging
from typing import Dict, List, Any, Optional

from opencopilot.capabilities.skill.base import BaseSkill
from opencopilot.capabilities.skill.models import (
    SkillMetadata, SkillContext, SkillResult, SkillStatus
)

logger = logging.getLogger(__name__)


class CodingSkill(BaseSkill):
    """编码 Skill"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 CodingSkill
        
        Args:
            config: 配置字典，可包含：
                - ide_port: IDE 端口
                - project_root: 项目根目录
                - llm_provider: LLM 提供者
        """
        super().__init__(config)
        self._coding_agent = None
        self._initialized = False
    
    @property
    def metadata(self) -> SkillMetadata:
        """获取 Skill 元数据"""
        return SkillMetadata(
            name="coding",
            version="1.0.0",
            description="编码助手，支持 Bug 修复、API 结果增强、代码分析等",
            author="OpenCopilot",
            category="coding",            tags=["coding", "bug-fix", "code-review", "analysis", "refactor"],
            intents=[
                "bug_fix",
                "code_review",
                "explain",
                "refactor",
                "enhance_api",
                "analyze",
                "coding"
            ],
            dependencies=[],
            config_schema={
                "ide_port": {
                    "type": "integer",
                    "description": "IDE 端口",
                    "required": False
                },
                "project_root": {
                    "type": "string",
                    "description": "项目根目录",
                    "required": False
                },
                "llm_provider": {
                    "type": "object",
                    "description": "LLM 提供者",
                    "required": False
                }
            },
            input_schema={
                "file_path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "error_message": {
                    "type": "string",
                    "description": "错误信息"
                },
                "line_number": {
                    "type": "integer",
                    "description": "行号"
                },
                "code": {
                    "type": "string",
                    "description": "代码内容"
                },
                "language": {
                    "type": "string",
                    "description": "编程语言"
                },
                "user_message": {
                    "type": "string",
                    "description": "用户消息"
                },
                "analysis_type": {
                    "type": "string",
                    "description": "分析类型"
                },
                "original_request": {
                    "type": "object",
                    "description": "原始请求"
                },
                "api_result": {
                    "type": "string",
                    "description": "API 返回结果"
                }
            },
            output_schema={
                "analysis": {
                    "type": "string",
                    "description": "分析结果"
                },
                "fix_suggestion": {
                    "type": "string",
                    "description": "修复建议"
                },
                "explanation": {
                    "type": "string",
                    "description": "解释说明"
                },
                "refactored_code": {
                    "type": "string",
                    "description": "重构后的代码"
                },
                "enhanced_result": {
                    "type": "string",
                    "description": "增强后的结果"
                },
                "issues": {
                    "type": "array",
                    "description": "问题列表"
                },
                "suggestions": {
                    "type": "array",
                    "description": "建议列表"
                },
                "score": {
                    "type": "integer",
                    "description": "评分"
                },
                "confidence": {
                    "type": "number",
                    "description": "置信度"
                }
            }
        )
    
    async def initialize(self) -> bool:
        """
        初始化 Coding Agent
        
        Returns:
            bool: 是否成功
        """
        try:
            # 导入 Coding Agent 模块
            from coding_agent.core import CodingAgent
            
            # 获取配置
            ide_port = self._config.get("ide_port")
            project_root = self._config.get("project_root")
            llm_provider = self._config.get("llm_provider")
            
            # 创建 CodingAgent 实例
            self._coding_agent = CodingAgent(
                llm_provider=llm_provider,
                ide_port=ide_port,
                project_root=project_root
            )
            
            self._initialized = True
            logger.info("CodingSkill 初始化完成")
            
            return True
            
        except Exception as e:
            logger.error(f"CodingSkill 初始化失败: {e}")
            return False
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """
        执行 Skill
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        # 检查是否已初始化
        if not self._initialized:
            success = await self.initialize()
            if not success:
                return SkillResult(
                    success=False,
                    data={},
                    error="CodingSkill 初始化失败",
                    status=SkillStatus.FAILED
                )
        
        # 获取意图
        intent = context.intent
        
        # 根据意图执行相应的操作
        try:
            if intent == "bug_fix":
                return await self._handle_bug_fix(context)
            elif intent == "code_review":
                return await self._handle_code_review(context)
            elif intent == "explain":
                return await self._handle_explain(context)
            elif intent == "refactor":
                return await self._handle_refactor(context)
            elif intent == "enhance_api":
                return await self._handle_enhance_api(context)
            elif intent == "analyze":
                return await self._handle_analyze(context)
            elif intent == "coding":
                return await self._handle_general_coding(context)
            else:
                return SkillResult(
                    success=False,
                    data={},
                    error=f"不支持的意图: {intent}",
                    status=SkillStatus.FAILED
                )
        except Exception as e:
            logger.error(f"执行 CodingSkill 失败: {e}")
            return SkillResult(
                success=False,
                data={},
                error=str(e),
                status=SkillStatus.FAILED
            )
    
    async def can_handle(self, context: SkillContext) -> float:
        """
        判断是否能处理该上下文
        
        Args:
            context: 执行上下文
        
        Returns:
            float: 置信度 (0-1)
        """
        # 检查意图是否匹配
        if context.intent in self.metadata.intents:
            return 0.9
        
        # 检查输入数据中是否包含编码相关的关键词
        input_data = context.input_data
        if isinstance(input_data, dict):
            # 检查是否有文件路径
            if input_data.get("file_path"):
                return 0.7
            
            # 检查是否有错误信息
            if input_data.get("error_message"):
                return 0.8
            
            # 检查是否有代码内容
            if input_data.get("code"):
                return 0.7
            
            # 检查用户消息
            user_message = input_data.get("user_message", "")
            if isinstance(user_message, str):
                coding_keywords = ["bug", "错误", "修复", "代码", "分析", "重构", "解释", "review"]
                for keyword in coding_keywords:
                    if keyword in user_message.lower():
                        return 0.6
        
        return 0.0
    
    async def _handle_bug_fix(self, context: SkillContext) -> SkillResult:
        """
        处理 Bug 修复意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        
        # 调用 CodingAgent 的 fix_bug 方法
        result = await self._coding_agent.fix_bug(
            file_path=input_data.get("file_path"),
            error_message=input_data.get("error_message"),
            line_number=input_data.get("line_number"),
            user_message=input_data.get("user_message", ""),
            language=input_data.get("language")
        )
        
        return SkillResult(
            success=True,
            data=result,
            status=SkillStatus.COMPLETED
        )
    
    async def _handle_code_review(self, context: SkillContext) -> SkillResult:
        """
        处理代码审查意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        
        # 调用 CodingAgent 的 review_code 方法
        result = await self._coding_agent.review_code(
            file_path=input_data.get("file_path"),
            code=input_data.get("code"),
            language=input_data.get("language"),
            user_message=input_data.get("user_message", "")
        )
        
        return SkillResult(
            success=True,
            data=result,
            status=SkillStatus.COMPLETED
        )
    
    async def _handle_explain(self, context: SkillContext) -> SkillResult:
        """
        处理解释代码意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        
        # 调用 CodingAgent 的 explain_code 方法
        result = await self._coding_agent.explain_code(
            file_path=input_data.get("file_path"),
            code=input_data.get("code"),
            line_number=input_data.get("line_number"),
            language=input_data.get("language"),
            user_message=input_data.get("user_message", "")
        )
        
        return SkillResult(
            success=True,
            data=result,
            status=SkillStatus.COMPLETED
        )
    
    async def _handle_refactor(self, context: SkillContext) -> SkillResult:
        """
        处理代码重构意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        
        # 调用 CodingAgent 的 refactor_code 方法
        result = await self._coding_agent.refactor_code(
            file_path=input_data.get("file_path"),
            code=input_data.get("code"),
            language=input_data.get("language"),
            user_message=input_data.get("user_message", "")
        )
        
        return SkillResult(
            success=True,
            data=result,
            status=SkillStatus.COMPLETED
        )
    
    async def _handle_enhance_api(self, context: SkillContext) -> SkillResult:
        """
        处理 API 结果增强意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        
        # 调用 CodingAgent 的 enhance_api_result 方法
        result = await self._coding_agent.enhance_api_result(
            original_request=input_data.get("original_request", {}),
            api_result=input_data.get("api_result", ""),
            file_path=input_data.get("file_path")
        )
        
        return SkillResult(
            success=True,
            data=result,
            status=SkillStatus.COMPLETED
        )
    
    async def _handle_analyze(self, context: SkillContext) -> SkillResult:
        """
        处理代码分析意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        
        # 调用 CodingAgent 的 analyze_code 方法
        result = await self._coding_agent.analyze_code(
            file_path=input_data.get("file_path"),
            code=input_data.get("code"),
            language=input_data.get("language"),
            user_message=input_data.get("user_message", "")
        )
        
        return SkillResult(
            success=True,
            data=result,
            status=SkillStatus.COMPLETED
        )
    
    async def _handle_general_coding(self, context: SkillContext) -> SkillResult:
        """
        处理通用编码意图
        
        Args:
            context: 执行上下文
        
        Returns:
            SkillResult: 执行结果
        """
        input_data = context.input_data
        
        # 根据输入数据判断具体操作
        if input_data.get("error_message"):
            # 如果有错误信息，执行 Bug 修复
            return await self._handle_bug_fix(context)
        elif input_data.get("code"):
            # 如果有代码内容，执行代码分析
            return await self._handle_analyze(context)
        else:
            # 默认执行代码分析
            return await self._handle_analyze(context)
    
    async def cleanup(self) -> None:
        """清理资源"""
        self._coding_agent = None
        self._initialized = False
        logger.info("CodingSkill 已清理资源")