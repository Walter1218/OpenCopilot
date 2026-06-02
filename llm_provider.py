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
        self.default_model = "MiniMax-M3"

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
                          context_meta: dict = None, context_envelope: dict = None,
                          image_base64: str = None):
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
        if image_base64:
            payload["image_base64"] = image_base64
        try:
            # timeout: connect=5s, read=120s（AI 思考可能较慢），write=10s, pool=5s
            timeout = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)
            with httpx.Client(verify=False, timeout=timeout) as client:
                with client.stream("POST", self.api_base, json=payload) as response:
                    if response.status_code != 200:
                        yield f"\n[Agent Server Error]: HTTP {response.status_code} - {response.text}"
                        return
                    for line in response.iter_lines():
                        if line == "data: [DONE]":
                            return  # 流结束，立即退出
                        if line.startswith("data: "):
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


class FailoverProvider(BaseProvider):
    """故障转移 Provider
    
    自动在多个 Provider 之间切换，保障服务可用性。
    当主 Provider 失败时，自动切换到备选 Provider。
    """
    
    def __init__(self, providers: list = None, health_check_interval: int = 60):
        """
        初始化故障转移 Provider
        
        Args:
            providers: Provider 列表，按优先级排序
            health_check_interval: 健康检查间隔（秒）
        """
        self.providers = providers or self._default_providers()
        self.current_index = 0
        self.health_check_interval = health_check_interval
        self.failure_counts = {i: 0 for i in range(len(self.providers))}
        self.max_failures = 3
        self._last_health_check = 0
        
        # 日志
        import logging
        self.logger = logging.getLogger(__name__)
    
    def _default_providers(self) -> list:
        """默认 Provider 列表"""
        config = load_config()
        providers = []
        
        # 优先使用云端 Provider
        if config.get("minimax_api_key") or os.environ.get("MINIMAX_API_KEY"):
            providers.append(("minimax", MiniMaxProvider()))
        
        # 备选本地 Provider
        local_api_base = config.get("local_api_base", "http://localhost:11434/v1")
        local_model = config.get("local_model", "llama3")
        providers.append(("local", LocalProvider(local_api_base, local_model)))
        
        # 最后备选：ASU Custom Agent
        providers.append(("agent", ASUCustomAgentClient()))
        
        return providers
    
    def _get_current_provider(self) -> BaseProvider:
        """获取当前可用的 Provider"""
        return self.providers[self.current_index][1]
    
    def _switch_to_next(self):
        """切换到下一个 Provider"""
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.providers)
        self.logger.warning(f"[Failover] 切换 Provider: {self.providers[old_index][0]} -> {self.providers[self.current_index][0]}")
    
    def _record_failure(self):
        """记录失败次数"""
        self.failure_counts[self.current_index] += 1
        
        # 如果失败次数超过阈值，切换 Provider
        if self.failure_counts[self.current_index] >= self.max_failures:
            self.logger.warning(f"[Failover] Provider {self.providers[self.current_index][0]} 失败次数过多，切换到下一个")
            self.failure_counts[self.current_index] = 0
            self._switch_to_next()
    
    def _record_success(self):
        """记录成功，重置失败计数"""
        self.failure_counts[self.current_index] = 0
    
    def stream_chat(self, prompt: str, system_prompt: str = ""):
        """流式聊天（带故障转移）"""
        max_retries = len(self.providers)
        
        for attempt in range(max_retries):
            try:
                provider = self._get_current_provider()
                self.logger.info(f"[Failover] 使用 Provider: {self.providers[self.current_index][0]}")
                
                # 尝试调用
                chunks = []
                for chunk in provider.stream_chat(prompt, system_prompt):
                    chunks.append(chunk)
                    yield chunk
                
                # 如果成功，记录成功
                self._record_success()
                return
                
            except Exception as e:
                self.logger.error(f"[Failover] Provider {self.providers[self.current_index][0]} 失败: {e}")
                self._record_failure()
                
                # 如果还有重试机会，切换到下一个
                if attempt < max_retries - 1:
                    self._switch_to_next()
                    yield f"\n[Failover] 切换到备选 Provider...\n"
                else:
                    yield f"\n[Failover] 所有 Provider 都失败，请检查服务状态。\n"
                    return
    
    def stream_chat_with_history(self, messages: list):
        """带历史的流式聊天（带故障转移）"""
        max_retries = len(self.providers)
        
        for attempt in range(max_retries):
            try:
                provider = self._get_current_provider()
                self.logger.info(f"[Failover] 使用 Provider: {self.providers[self.current_index][0]}")
                
                # 尝试调用
                chunks = []
                for chunk in provider.stream_chat_with_history(messages):
                    chunks.append(chunk)
                    yield chunk
                
                # 如果成功，记录成功
                self._record_success()
                return
                
            except Exception as e:
                self.logger.error(f"[Failover] Provider {self.providers[self.current_index][0]} 失败: {e}")
                self._record_failure()
                
                # 如果还有重试机会，切换到下一个
                if attempt < max_retries - 1:
                    self._switch_to_next()
                    yield f"\n[Failover] 切换到备选 Provider...\n"
                else:
                    yield f"\n[Failover] 所有 Provider 都失败，请检查服务状态。\n"
                    return
    
    def get_status(self) -> dict:
        """获取故障转移状态"""
        return {
            "current_provider": self.providers[self.current_index][0],
            "providers": [
                {
                    "name": name,
                    "failures": self.failure_counts[i],
                    "available": self.failure_counts[i] < self.max_failures
                }
                for i, (name, _) in enumerate(self.providers)
            ],
            "total_providers": len(self.providers)
        }


class ProviderFactoryWithFailover(ProviderFactory):
    """带故障转移的 Provider 工厂"""
    
    @staticmethod
    def create_provider(use_failover: bool = True) -> BaseProvider:
        """
        创建 Provider
        
        Args:
            use_failover: 是否使用故障转移
            
        Returns:
            Provider 实例
        """
        if use_failover:
            config = load_config()
            failover_enabled = config.get("failover", {}).get("enabled", True)
            
            if failover_enabled:
                return FailoverProvider()
        
        # 默认使用单个 Provider
        return ASUCustomAgentClient()