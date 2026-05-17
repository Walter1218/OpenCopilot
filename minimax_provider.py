import os
from openai import OpenAI

class MiniMaxProvider:
    """
    MiniMax LLM API Provider 模块
    使用 OpenAI 兼容接口，基于 MiniMax Token Plan 提供文本生成服务。
    """
    def __init__(self, api_key=None, base_url="https://api.minimax.chat/v1"):
        """
        初始化 MiniMax 客户端
        :param api_key: MiniMax API Key。如果不提供，则默认从环境变量 MINIMAX_API_KEY 中获取。
        :param base_url: OpenAI 兼容的 Base URL。
        """
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY")
        if not self.api_key:
            raise ValueError("请提供 api_key 或设置 MINIMAX_API_KEY 环境变量")
            
        self.base_url = base_url
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
    def chat(self, prompt, model="MiniMax-M2.7", system_prompt=None, temperature=0.7):
        """
        发送同步对话请求，并返回内容及 Token 消耗情况 (Token Plan 使用量)
        
        :param prompt: 用户的输入
        :param model: 模型名称，默认 "MiniMax-M2.7"
        :param system_prompt: 系统提示词
        :param temperature: 随机性
        :return: 包含响应文本和 Token usage 字典的元组
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            
            content = response.choices[0].message.content
            # 获取 Token Plan 消耗数据
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            }
            
            return content, usage
            
        except Exception as e:
            return f"MiniMax API 调用失败: {e}", None

    def stream_chat(self, prompt, model="MiniMax-M2.7", system_prompt=None, temperature=0.7):
        """
        发送流式对话请求 (Stream)
        
        :param prompt: 用户的输入
        :param model: 模型名称
        :param system_prompt: 系统提示词
        :param temperature: 随机性
        :yield: 逐步生成的文本片段
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\nMiniMax API 调用失败: {e}"

if __name__ == "__main__":
    # 简单的本地测试逻辑
    print("=== MiniMax LLM Provider 测试 ===")
    test_key = os.getenv("MINIMAX_API_KEY")
    if not test_key:
        print("提示：未检测到 MINIMAX_API_KEY 环境变量，测试将跳过。")
        print("如需测试，请运行: export MINIMAX_API_KEY='你的真实key'")
    else:
        provider = MiniMaxProvider()
        print("正在请求 MiniMax API...")
        content, usage = provider.chat("你好，请用一句话介绍你自己。")
        print(f"\n回答:\n{content}")
        print(f"\nToken 消耗 (Token Plan): {usage}")
