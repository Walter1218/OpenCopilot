import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "provider_type": "minimax", # 'minimax' 或 'local'
        "local_api_base": "http://localhost:11434/v1",
        "local_model": "llama3"
    }

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

class BaseProvider:
    def stream_chat(self, prompt: str, system_prompt: str = ""):
        raise NotImplementedError
        
    def stream_chat_with_history(self, messages: list):
        raise NotImplementedError

class MiniMaxProvider(BaseProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY")
        if not self.api_key:
            print("警告: 未找到 MINIMAX_API_KEY 环境变量，请在 .env 文件中设置。")
            
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.minimax.chat/v1"
        )
        self.default_model = "MiniMax-M2.7"

    def chat(self, prompt: str, model: str = None, system_prompt: str = "") -> tuple[str, dict]:
        model = model or self.default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=model,
            messages=messages
        )
        
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        
        return response.choices[0].message.content, usage

    def stream_chat(self, prompt: str, model: str = None, system_prompt: str = ""):
        model = model or self.default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def stream_chat_with_history(self, messages: list):
        model = self.default_model

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class LocalProvider(BaseProvider):
    def __init__(self, api_base: str, model: str, api_key: str = "sk-local"):
        self.api_base = api_base
        self.model = model
        # 对于本地模型（如 Ollama, LMStudio, OpenClaw 等），需要正确配置 client
        import httpx
        self.client = OpenAI(
            api_key=api_key, # 默认为非空字符串，以防 OpenAI SDK 报错
            base_url=self.api_base,
            http_client=httpx.Client(verify=False) # 关闭 SSL 验证
        )

    def stream_chat(self, prompt: str, system_prompt: str = ""):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0.7 # 明确指定一些常见参数，防止本地大模型解析默认值时出错
            )
            
            for chunk in response:
                if chunk.choices and hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n[连接本地大模型失败]: {str(e)}\n请检查：\n1. API Base URL 是否正确 (如 http://localhost:11434/v1)\n2. 模型名称 ({self.model}) 是否已经在本地下载运行。"

    def stream_chat_with_history(self, messages: list):
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0.7
            )
            
            for chunk in response:
                if chunk.choices and hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n[连接本地大模型失败]: {str(e)}\n请检查第三方智能体配置或服务状态。"

class OpenClawGatewayProvider(BaseProvider):
    def __init__(self, api_base: str, api_key: str):
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key
        
    def stream_chat(self, prompt: str, system_prompt: str = ""):
        # Agent 不区分系统提示和普通提示，合并发送
        full_message = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        return self._send_to_gateway(full_message)
        
    def stream_chat_with_history(self, messages: list):
        # 提取历史记录中的最新一条或合并
        content = "\n".join([m.get("content", "") for m in messages])
        return self._send_to_gateway(content)
        
    def _send_to_gateway(self, content: str):
        import httpx
        url = f"{self.api_base}/api/v1/messages/send"
        
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
            
        payload = {
            "content": content,
            "agent": "main", # 默认使用主 Agent
            "channel": "feishu" # 兼容它的 channel 参数
        }
        
        try:
            with httpx.Client(timeout=60.0, verify=False) as client:
                # 修复：由于它是通过 query string 传递内容，改用 params 而不是 json
                response = client.post(url, params=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("result", "") or str(data)
                    # 简单切片模拟流式效果
                    for i in range(0, len(result), 5):
                        yield result[i:i+5]
                else:
                    yield f"\n[Agent网关请求失败]: HTTP {response.status_code}\n{response.text}"
        except Exception as e:
            yield f"\n[连接Agent网关失败]: {str(e)}\n请检查网关是否已启动并确认 API Key 是否正确。"

class ProviderFactory:
    @staticmethod
    def create_provider():
        config = load_config()
        provider_type = config.get("provider_type")
        
        if provider_type == "local":
            return LocalProvider(
                api_base=config.get("local_api_base", "http://localhost:11434/v1"),
                model=config.get("local_model", "llama3"),
                api_key=config.get("local_api_key", "sk-local")
            )
        elif provider_type == "openclaw":
            return OpenClawGatewayProvider(
                api_base=config.get("local_api_base", "http://127.0.0.1:18791"),
                api_key=config.get("local_api_key", "")
            )
        else:
            return MiniMaxProvider()