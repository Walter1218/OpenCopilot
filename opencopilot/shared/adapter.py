"""
LLM 适配器

将现有的 LLM Provider 适配为 CodingAgent 需要的接口。
"""

import asyncio
from typing import Optional


class LLMAdapter:
    """
    LLM 适配器
    
    将流式 LLM Provider 适配为支持 generate 方法的接口。
    """
    
    def __init__(self, provider):
        """
        初始化适配器
        
        Args:
            provider: 原始 LLM Provider（需要有 stream_chat 方法）
        """
        self.provider = provider
    
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        生成响应（非流式）
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
        
        Returns:
            str: 完整的响应文本
        """
        # 收集所有流式响应
        response_chunks = []
        
        # 在线程池中运行同步的流式调用
        loop = asyncio.get_event_loop()
        
        def collect_stream():
            chunks = []
            for chunk in self.provider.stream_chat(prompt, system_prompt):
                chunks.append(chunk)
            return "".join(chunks)
        
        # 使用 run_in_executor 避免阻塞事件循环
        response = await loop.run_in_executor(None, collect_stream)
        
        return response
    
    async def generate_stream(self, prompt: str, system_prompt: str = ""):
        """
        生成响应（流式）
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
        
        Yields:
            str: 响应文本块
        """
        loop = asyncio.get_event_loop()
        
        def get_stream():
            return self.provider.stream_chat(prompt, system_prompt)
        
        stream = await loop.run_in_executor(None, get_stream)
        
        for chunk in stream:
            yield chunk


def create_llm_adapter(provider_type: str = "auto") -> Optional[LLMAdapter]:
    """
    创建 LLM 适配器
    
    Args:
        provider_type: 提供者类型 ("minimax", "local", "auto")
    
    Returns:
        Optional[LLMAdapter]: LLM 适配器实例
    """
    try:
        from llm_provider import ProviderFactory, load_config
        
        config = load_config()
        
        if provider_type == "auto":
            provider_type = config.get("provider_type", "minimax")
        
        if provider_type == "minimax":
            from llm_provider import MiniMaxProvider
            provider = MiniMaxProvider()
        elif provider_type == "local":
            from llm_provider import LocalProvider
            provider = LocalProvider(
                api_base=config.get("local_api_base", "http://localhost:11434/v1"),
                model=config.get("local_model", "llama3")
            )
        else:
            provider = ProviderFactory.create_provider()
        
        return LLMAdapter(provider)
    except Exception as e:
        print(f"创建 LLM 适配器失败: {e}")
        return None
