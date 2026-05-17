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

class MiniMaxProvider(BaseProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY")
        if not self.api_key:
            print("警告: 未找到 MINIMAX_API_KEY 环境变量，请在 .env 文件中设置。")
            
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.minimax.chat/v1"
        )
        self.default_model = "MiniMax-Text-01"

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


class LocalProvider(BaseProvider):
    def __init__(self, api_base: str, model: str):
        self.api_base = api_base
        self.model = model
        # 对于本地模型（如 Ollama, LMStudio），通常不需要真实的 API Key
        self.client = OpenAI(
            api_key="local-placeholder",
            base_url=self.api_base
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
                stream=True
            )
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n[连接本地大模型失败]: {str(e)}\n请检查配置的 API 地址是否正确，以及本地服务是否已启动。"

class ProviderFactory:
    @staticmethod
    def create_provider():
        config = load_config()
        if config.get("provider_type") == "local":
            return LocalProvider(
                api_base=config.get("local_api_base", "http://localhost:11434/v1"),
                model=config.get("local_model", "llama3")
            )
        else:
            return MiniMaxProvider()