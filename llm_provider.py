import os
import json
import httpx
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
        self.base_url = "https://api.minimax.chat/v1/text/chatcompletion_v2"
        self.default_model = "MiniMax-Text-01" # MiniMax新推荐模型

    def _do_stream(self, messages: list):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.default_model,
            "messages": messages,
            "stream": True
        }
        try:
            with httpx.Client() as client:
                with client.stream("POST", self.base_url, headers=headers, json=payload, timeout=30.0) as response:
                    for line in response.iter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                choices = data.get("choices", [])
                                if choices:
                                    content = choices[0].get("delta", {}).get("content", "")
                                    if content:
                                        yield content
                            except Exception:
                                pass
        except Exception as e:
            yield f"\n[MiniMax 连接失败]: {str(e)}"

    def stream_chat(self, prompt: str, model: str = None, system_prompt: str = ""):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        yield from self._do_stream(messages)

    def stream_chat_with_history(self, messages: list):
        yield from self._do_stream(messages)


class LocalProvider(BaseProvider):
    def __init__(self, api_base: str, model: str, api_key: str = "sk-local"):
        self.api_base = api_base.rstrip("/") + "/chat/completions"
        self.model = model
        self.api_key = api_key

    def _do_stream(self, messages: list):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": 0.7
        }
        try:
            with httpx.Client(verify=False) as client:
                with client.stream("POST", self.api_base, headers=headers, json=payload, timeout=30.0) as response:
                    for line in response.iter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                choices = data.get("choices", [])
                                if choices:
                                    content = choices[0].get("delta", {}).get("content", "")
                                    if content:
                                        yield content
                            except Exception:
                                pass
        except Exception as e:
            yield f"\n[连接本地大模型失败]: {str(e)}\n请检查：\n1. API Base URL 是否正确 (如 http://localhost:11434/v1)\n2. 服务是否运行中。"

    def stream_chat(self, prompt: str, system_prompt: str = ""):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        yield from self._do_stream(messages)

    def stream_chat_with_history(self, messages: list):
        yield from self._do_stream(messages)

class OpenClawServerProvider(BaseProvider):
    def __init__(self, agent_name: str = "main"):
        self.agent_name = agent_name or "main"
        self.api_base = "http://localhost:18791/v1/chat/completions"

    def _do_stream(self, messages: list):
        payload = {
            "model": self.agent_name,
            "messages": messages,
            "stream": True
        }
        try:
            with httpx.Client(verify=False) as client:
                with client.stream("POST", self.api_base, json=payload, timeout=30.0) as response:
                    if response.status_code != 200:
                        yield f"\n[OpenClaw Server Error]: HTTP {response.status_code} - {response.text}"
                        return
                    for line in response.iter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                choices = data.get("choices", [])
                                if choices:
                                    content = choices[0].get("delta", {}).get("content", "")
                                    if content:
                                        yield content
                            except Exception:
                                pass
        except Exception as e:
            yield f"\n[调用 OpenClaw Server 失败]: {str(e)}\n请检查后台服务是否启动在 18791 端口。"

    def stream_chat(self, prompt: str, system_prompt: str = ""):
        messages = []
        if system_prompt:
            # 针对 OpenClaw Agent 模式，采用更强指令格式避免被自带 Persona 覆盖
            messages.append({"role": "system", "content": f"请严格执行以下系统指令，忽略默认设定：\n{system_prompt}"})
        messages.append({"role": "user", "content": prompt})
        yield from self._do_stream(messages)

    def stream_chat_with_history(self, messages: list):
        # 如果存在系统指令，进行强覆盖处理
        for m in messages:
            if m.get("role") == "system":
                m["content"] = f"请严格执行以下系统指令，忽略默认设定：\n{m['content']}"
        yield from self._do_stream(messages)

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
            return OpenClawServerProvider(
                agent_name=config.get("agent_name", "main")
            )
        else:
            return MiniMaxProvider()