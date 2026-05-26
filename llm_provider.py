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
        # 优先使用传入的 api_key，其次使用 config 中的，最后回退到环境变量
        config = load_config()
        self.api_key = api_key or config.get("minimax_api_key") or os.environ.get("MINIMAX_API_KEY")
        if not self.api_key:
            print("警告: 未找到 MINIMAX_API_KEY 环境变量或配置，请在 .env 文件中或设置面板中设置。")
        self.base_url = "https://api.minimax.chat/v1/chat/completions"
        self.default_model = "MiniMax-M2.7"

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

    def stream_chat(self, prompt: str, system_prompt: str = ""):
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

class ASUCustomAgentClient(BaseProvider):
    def __init__(self, port=18888):
        self.api_base = f"http://127.0.0.1:{port}/v1/agent/chat"

    def stream_agent_task(self, text: str, action_type: str = "default", session_id: str = "default",
                          is_new_task: bool = False, context_source: str = "drag",
                          context_meta: dict = None, context_envelope: dict = None):
        payload = {
            "text": text,
            "action_type": action_type,
            "session_id": session_id,
            "is_new_task": is_new_task,
            "context_source": context_source,
            "context_meta": context_meta or {},
        }
        if context_envelope:
            payload["context_envelope"] = context_envelope
        try:
            with httpx.Client(verify=False) as client:
                with client.stream("POST", self.api_base, json=payload, timeout=30.0) as response:
                    if response.status_code != 200:
                        yield f"\n[Agent Server Error]: HTTP {response.status_code} - {response.text}"
                        return
                    for line in response.iter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                chunk = data.get("chunk", "")
                                if chunk:
                                    yield chunk
                            except Exception:
                                pass
        except Exception as e:
            yield f"\n[连接后台智能体失败]: {str(e)}\n请检查服务是否正常启动。"

    def stream_chat(self, prompt: str, system_prompt: str = ""):
        # 为了兼容旧接口，直接转发为 default 任务
        yield from self.stream_agent_task(text=prompt, action_type="default", session_id="default", is_new_task=True)

    def stream_chat_with_history(self, messages: list):
        # 为了兼容旧接口，取最后一条消息即可（历史在 agent 端维护）
        last_msg = messages[-1]["content"] if messages else ""
        yield from self.stream_agent_task(text=last_msg, action_type="chat", session_id="default", is_new_task=False)

class ProviderFactory:
    @staticmethod
    def create_provider():
        # 现在所有请求都经过定制的 Agent Server 统一处理
        return ASUCustomAgentClient()