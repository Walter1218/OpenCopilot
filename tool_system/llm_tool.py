# tool_system/llm_tool.py

"""
LLM 工具

将 LLM 能力封装为工具系统可调用的工具。
"""

import asyncio
from typing import Dict, Any, Optional
from .models import ToolDefinition, ToolType, ToolCategory, ToolParameter


class LLMTool:
    """LLM 工具 - 将 LLM 能力封装为工具"""
    
    def __init__(self, llm_adapter=None):
        """
        初始化 LLM 工具
        
        Args:
            llm_adapter: LLM 适配器实例
        """
        self._llm_adapter = llm_adapter
        self._definition = self._create_definition()
    
    def _create_definition(self) -> ToolDefinition:
        """创建工具定义"""
        return ToolDefinition(
            tool_id="llm_chat",
            name="LLM Chat",
            description="使用大语言模型进行对话和文本生成",
            tool_type=ToolType.FUNCTION,
            category=ToolCategory.AI,
            parameters=[
                ToolParameter(
                    name="prompt",
                    type="string",
                    description="用户提示",
                    required=True
                ),
                ToolParameter(
                    name="system_prompt",
                    type="string",
                    description="系统提示（可选）",
                    required=False,
                    default=""
                ),
                ToolParameter(
                    name="max_tokens",
                    type="integer",
                    description="最大生成 token 数",
                    required=False,
                    default=2000
                ),
                ToolParameter(
                    name="temperature",
                    type="number",
                    description="生成温度（0-1）",
                    required=False,
                    default=0.7
                )
            ],
            timeout=60.0  # LLM 调用可能需要较长时间
        )
    
    @property
    def definition(self) -> ToolDefinition:
        """获取工具定义"""
        return self._definition
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行 LLM 调用
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大 token 数
            temperature: 温度
        
        Returns:
            Dict: 包含响应的结果
        """
        prompt = kwargs.get("prompt", "")
        system_prompt = kwargs.get("system_prompt", "")
        
        if not prompt:
            return {
                "success": False,
                "error": "Prompt is required",
                "response": ""
            }
        
        try:
            # 使用 LLM 适配器生成响应
            if self._llm_adapter:
                response = await self._llm_adapter.generate(prompt, system_prompt)
                return {
                    "success": True,
                    "response": response,
                    "prompt": prompt,
                    "system_prompt": system_prompt
                }
            else:
                # 如果没有 LLM 适配器，返回模拟响应
                return {
                    "success": True,
                    "response": f"[模拟 LLM 响应] 收到提示: {prompt[:50]}...",
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "simulated": True
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": ""
            }


class LLMToolWithProvider(LLMTool):
    """带 Provider 的 LLM 工具"""
    
    def __init__(self, provider_type: str = "auto"):
        """
        初始化带 Provider 的 LLM 工具
        
        Args:
            provider_type: Provider 类型 ("minimax", "local", "auto")
        """
        from llm_adapter import create_llm_adapter
        
        llm_adapter = create_llm_adapter(provider_type)
        super().__init__(llm_adapter)
        self._provider_type = provider_type
    
    @property
    def provider_type(self) -> str:
        """获取 Provider 类型"""
        return self._provider_type


# 工具工厂函数
def create_llm_tool(
    provider_type: str = "auto",
    use_real_llm: bool = True
) -> LLMTool:
    """
    创建 LLM 工具
    
    Args:
        provider_type: Provider 类型
        use_real_llm: 是否使用真实的 LLM
    
    Returns:
        LLMTool: LLM 工具实例
    """
    if use_real_llm:
        try:
            return LLMToolWithProvider(provider_type)
        except Exception as e:
            print(f"创建真实 LLM 工具失败，使用模拟工具: {e}")
            return LLMTool()
    else:
        return LLMTool()
