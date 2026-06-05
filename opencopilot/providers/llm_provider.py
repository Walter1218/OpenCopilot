import os
import json
import httpx
from typing import AsyncGenerator
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

CONFIG_FILE = "config.json"

# 延迟导入避免循环依赖
def _get_config_manager():
    from config_manager import ConfigManager
    return ConfigManager.get_instance()

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "provider_type": "mimo",  # 'mimo', 'minimax' 或 'local'
        "mimo_model": "mimo-v2.5",
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
        # LLM 可配置参数（从 ConfigManager 读取）
        llm_cfg = _get_config_manager().get_llm()
        self._temperature = llm_cfg.get("temperature", 0.7)
        self._repetition_penalty = llm_cfg.get("repetition_penalty", 1.05)

    def _do_stream(self, messages: list):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.default_model,
            "messages": messages,
            "stream": True,
            "temperature": self._temperature,
            "repetition_penalty": self._repetition_penalty,
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

    # ---- Async methods ----

    async def _do_stream_async(self, messages: list) -> AsyncGenerator[str, None]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.default_model,
            "messages": messages,
            "stream": True,
            "temperature": self._temperature,
            "repetition_penalty": self._repetition_penalty,
        }
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", self.base_url, headers=headers, json=payload, timeout=30.0) as response:
                    async for line in response.aiter_lines():
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

    async def async_stream_chat(self, prompt: str, system_prompt: str = "") -> AsyncGenerator[str, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        async for chunk in self._do_stream_async(messages):
            yield chunk

    async def async_stream_chat_with_history(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        async for chunk in self._do_stream_async(messages):
            yield chunk


class MiMoProvider(BaseProvider):
    """小米 MiMo 模型 Provider

    支持 MiMo-V2.5 系列（mimo-v2.5, mimo-v2.5-pro, mimo-v2-flash）。
    API 兼容 OpenAI 格式，Base URL: https://api.xiaomimimo.com/v1
    支持按量计费（非 Token Plan），无需订阅即可使用。
    """

    # 按量计费单价（元/千 tokens），参考官方定价页
    PRICING = {
        "mimo-v2.5-pro":   {"input": 0.024, "output": 0.060},
        "mimo-v2.5":       {"input": 0.012, "output": 0.030},
        "mimo-v2-flash":   {"input": 0.002, "output": 0.006},
    }

    def __init__(self, api_key: str = None, model: str = None):
        config = load_config()
        self.api_key = api_key or config.get("mimo_api_key") or os.environ.get("XIAOMI_API_KEY") or os.environ.get("xiaomi_api_key") or os.environ.get("MIMO_API_KEY")
        if not self.api_key:
            print("警告: 未找到 XIAOMI_API_KEY / MIMO_API_KEY 环境变量或配置，请在 .env 文件中设置。")
        self.default_model = model or config.get("mimo_model", "mimo-v2.5")
        self.base_url = "https://api.xiaomimimo.com/v1/chat/completions"
        self._usage_stats = {"total_requests": 0, "total_input_tokens": 0, "total_output_tokens": 0, "total_cost_cny": 0.0}

        # LLM 可配置参数（从 ConfigManager 读取）
        llm_cfg = _get_config_manager().get_llm()
        self._temperature = llm_cfg.get("temperature", 0.7)
        self._max_completion_tokens = llm_cfg.get("max_completion_tokens", 4096)
        self._thinking = llm_cfg.get("thinking_enabled", False)
        self._repetition_penalty = llm_cfg.get("repetition_penalty", 1.05)

        # Web Search 配置
        ws_config = config.get("web_search", {})
        self.web_search_enabled = ws_config.get("enabled", False)
        self.web_search_force = ws_config.get("force_search", False)
        self.web_search_max_keyword = ws_config.get("max_keyword", 3)
        self.web_search_limit = ws_config.get("limit", 3)
        self.web_search_location = ws_config.get("user_location", None)

    def _build_payload(self, messages: list, tools: list = None, stream: bool = True) -> dict:
        """构建请求 payload（使用可配置参数）"""
        payload = {
            "model": self.default_model,
            "messages": messages,
            "stream": stream,
            "max_completion_tokens": self._max_completion_tokens,
            "temperature": self._temperature,
            "repetition_penalty": self._repetition_penalty,
            "thinking": {"type": "enabled"} if self._thinking else {"type": "disabled"},
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        return payload

    def _build_tools(self, enable_web_search: bool = None, force_search: bool = None,
                      max_keyword: int = None, limit: int = None,
                      user_location: dict = None) -> list:
        """构建 tools 参数（含 web_search）"""
        should_enable = enable_web_search if enable_web_search is not None else self.web_search_enabled
        if not should_enable:
            return []

        tool = {
            "type": "web_search",
            "max_keyword": max_keyword or self.web_search_max_keyword,
            "force_search": force_search if force_search is not None else self.web_search_force,
            "limit": limit or self.web_search_limit,
        }
        loc = user_location or self.web_search_location
        if loc:
            tool["user_location"] = loc
        return [tool]

    def _do_stream(self, messages: list, tools: list = None):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = self._build_payload(messages, tools=tools, stream=True)
        try:
            with httpx.Client() as client:
                with client.stream("POST", self.base_url, headers=headers, json=payload, timeout=300.0) as response:
                    if response.status_code != 200:
                        error_body = ""
                        for chunk in response.iter_text():
                            error_body += chunk
                        yield f"\n[MiMo API Error]: HTTP {response.status_code} - {error_body[:200]}"
                        return
                    for line in response.iter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                # 记录 usage（非流式最后一条或流式中的 usage）
                                if "usage" in data:
                                    self._update_usage(data["usage"])
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                                    # 流式模式下 annotations 在首包的 delta 中
                                    annotations = delta.get("annotations")
                                    if annotations:
                                        yield ("__annotations__", annotations)
                            except Exception:
                                pass
        except Exception as e:
            yield f"\n[MiMo 连接失败]: {str(e)}"

    def _do_non_stream(self, messages: list, tools: list = None) -> dict:
        """非流式调用，返回 {"content": str, "annotations": list}"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = self._build_payload(messages, tools=tools, stream=False)
        try:
            with httpx.Client() as client:
                resp = client.post(self.base_url, headers=headers, json=payload, timeout=300.0)
                if resp.status_code != 200:
                    return {"content": f"[MiMo API Error]: HTTP {resp.status_code} - {resp.text[:200]}", "annotations": []}
                data = resp.json()
                if "usage" in data:
                    self._update_usage(data["usage"])
                choices = data.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    return {
                        "content": msg.get("content", ""),
                        "annotations": msg.get("annotations", []),
                    }
                return {"content": "", "annotations": []}
        except Exception as e:
            return {"content": f"[MiMo 连接失败]: {str(e)}", "annotations": []}

    # Web Search 联网搜索计费（元/千次调用）
    WEB_SEARCH_PRICING = {
        "domestic": 0.016,   # ¥16 / 1000次
        "overseas": 0.035,   # ~$5 / 1000次
    }

    def _update_usage(self, usage: dict):
        """更新按量计费统计"""
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        self._usage_stats["total_requests"] += 1
        self._usage_stats["total_input_tokens"] += input_tokens
        self._usage_stats["total_output_tokens"] += output_tokens

        model_pricing = self.PRICING.get(self.default_model, self.PRICING["mimo-v2.5"])
        cost = (input_tokens / 1000 * model_pricing["input"]) + (output_tokens / 1000 * model_pricing["output"])
        self._usage_stats["total_cost_cny"] += cost

        # Web Search 计费
        ws_usage = usage.get("web_search_usage")
        if ws_usage:
            tool_usage = ws_usage.get("tool_usage", 0)
            self._usage_stats.setdefault("web_search_tool_usage", 0)
            self._usage_stats["web_search_tool_usage"] += tool_usage
            ws_cost = tool_usage / 1000 * self.WEB_SEARCH_PRICING["domestic"]
            self._usage_stats.setdefault("web_search_cost_cny", 0.0)
            self._usage_stats["web_search_cost_cny"] += ws_cost

    def get_usage_stats(self) -> dict:
        """获取按量计费统计"""
        return {
            "model": self.default_model,
            "billing_mode": "pay_as_you_go",
            **self._usage_stats,
        }

    def stream_chat(self, prompt: str, system_prompt: str = "", enable_web_search: bool = None):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        tools = self._build_tools(enable_web_search) if enable_web_search else None
        yield from self._do_stream(messages, tools=tools)

    def stream_chat_with_history(self, messages: list, enable_web_search: bool = None,
                                  force_search: bool = None, max_keyword: int = None,
                                  limit: int = None, user_location: dict = None):
        tools = self._build_tools(enable_web_search, force_search, max_keyword, limit, user_location) if (enable_web_search or self.web_search_enabled) else None
        yield from self._do_stream(messages, tools=tools)

    # ---- Async methods ----

    async def _do_stream_async(self, messages: list, tools: list = None) -> AsyncGenerator[str, None]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = self._build_payload(messages, tools=tools, stream=True)
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", self.base_url, headers=headers, json=payload, timeout=300.0) as response:
                    if response.status_code != 200:
                        error_body = ""
                        async for chunk in response.aiter_text():
                            error_body += chunk
                        yield f"\n[MiMo API Error]: HTTP {response.status_code} - {error_body[:200]}"
                        return
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                if "usage" in data:
                                    self._update_usage(data["usage"])
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                                    annotations = delta.get("annotations")
                                    if annotations:
                                        yield ("__annotations__", annotations)
                            except Exception:
                                pass
        except Exception as e:
            yield f"\n[MiMo 连接失败]: {str(e)}"

    async def _do_non_stream_async(self, messages: list, tools: list = None) -> dict:
        """异步非流式调用，返回 {"content": str, "annotations": list}"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = self._build_payload(messages, tools=tools, stream=False)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.base_url, headers=headers, json=payload, timeout=300.0)
                if resp.status_code != 200:
                    return {"content": f"[MiMo API Error]: HTTP {resp.status_code} - {resp.text[:200]}", "annotations": []}
                data = resp.json()
                if "usage" in data:
                    self._update_usage(data["usage"])
                choices = data.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    return {
                        "content": msg.get("content", ""),
                        "annotations": msg.get("annotations", []),
                    }
                return {"content": "", "annotations": []}
        except Exception as e:
            return {"content": f"[MiMo 连接失败]: {str(e)}", "annotations": []}

    async def async_stream_chat(self, prompt: str, system_prompt: str = "", enable_web_search: bool = None) -> AsyncGenerator[str, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        tools = self._build_tools(enable_web_search) if enable_web_search else None
        async for chunk in self._do_stream_async(messages, tools=tools):
            yield chunk

    async def async_stream_chat_with_history(self, messages: list, enable_web_search: bool = None,
                                              force_search: bool = None, max_keyword: int = None,
                                              limit: int = None, user_location: dict = None, **kwargs) -> AsyncGenerator[str, None]:
        tools = self._build_tools(enable_web_search, force_search, max_keyword, limit, user_location) if (enable_web_search or self.web_search_enabled) else None
        async for chunk in self._do_stream_async(messages, tools=tools):
            yield chunk


class LocalProvider(BaseProvider):
    def __init__(self, api_base: str, model: str, api_key: str = "sk-local"):
        self.api_base = api_base.rstrip("/") + "/chat/completions"
        self.model = model
        self.api_key = api_key
        # 从 ConfigManager 读取 LLM 参数
        llm_cfg = _get_config_manager().get_llm()
        self._temperature = llm_cfg.get("temperature", 0.7)
        self._repetition_penalty = llm_cfg.get("repetition_penalty", 1.05)

    def _do_stream(self, messages: list):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": self._temperature,
            "repetition_penalty": self._repetition_penalty,
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

    # ---- Async methods ----

    async def _do_stream_async(self, messages: list) -> AsyncGenerator[str, None]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": self._temperature,
            "repetition_penalty": self._repetition_penalty,
        }
        try:
            async with httpx.AsyncClient(verify=False) as client:
                async with client.stream("POST", self.api_base, headers=headers, json=payload, timeout=30.0) as response:
                    async for line in response.aiter_lines():
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

    async def async_stream_chat(self, prompt: str, system_prompt: str = "") -> AsyncGenerator[str, None]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        async for chunk in self._do_stream_async(messages):
            yield chunk

    async def async_stream_chat_with_history(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        async for chunk in self._do_stream_async(messages):
            yield chunk

class ProviderFactory:
    @staticmethod
    def create_provider():
        """创建默认 Provider（优先 MiMo）"""
        return MiMoProvider()


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
        # P2 参数：从 ConfigManager 读取故障转移失败阈值
        llm_cfg = _get_config_manager().get_llm()
        self.max_failures = llm_cfg.get("failover_max_failures", 3)
        self._last_health_check = 0
        
        # 日志
        import logging
        self.logger = logging.getLogger(__name__)
    
    def _default_providers(self) -> list:
        """默认 Provider 列表"""
        config = load_config()
        providers = []
        
        # 优先使用 MiMo（按量计费，性价比高）
        if config.get("mimo_api_key") or os.environ.get("XIAOMI_API_KEY") or os.environ.get("xiaomi_api_key") or os.environ.get("MIMO_API_KEY"):
            providers.append(("mimo", MiMoProvider()))
        
        # 备选 MiniMax
        if config.get("minimax_api_key") or os.environ.get("MINIMAX_API_KEY"):
            providers.append(("minimax", MiniMaxProvider()))
        
        # 备选本地 Provider
        local_api_base = config.get("local_api_base", "http://localhost:11434/v1")
        local_model = config.get("local_model", "llama3")
        providers.append(("local", LocalProvider(local_api_base, local_model)))
        
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

    # ---- Async methods ----

    async def async_stream_chat(self, prompt: str, system_prompt: str = "") -> AsyncGenerator[str, None]:
        """异步流式聊天（带故障转移）"""
        max_retries = len(self.providers)
        for attempt in range(max_retries):
            try:
                provider = self._get_current_provider()
                self.logger.info(f"[Failover] 使用 Provider: {self.providers[self.current_index][0]}")
                async for chunk in provider.async_stream_chat(prompt, system_prompt):
                    yield chunk
                self._record_success()
                return
            except Exception as e:
                self.logger.error(f"[Failover] Provider {self.providers[self.current_index][0]} 失败: {e}")
                self._record_failure()
                if attempt < max_retries - 1:
                    self._switch_to_next()
                    yield f"\n[Failover] 切换到备选 Provider...\n"
                else:
                    yield f"\n[Failover] 所有 Provider 都失败，请检查服务状态。\n"
                    return

    async def async_stream_chat_with_history(self, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        """异步带历史流式聊天（带故障转移）"""
        max_retries = len(self.providers)
        for attempt in range(max_retries):
            try:
                provider = self._get_current_provider()
                self.logger.info(f"[Failover] 使用 Provider: {self.providers[self.current_index][0]}")
                async for chunk in provider.async_stream_chat_with_history(messages, **kwargs):
                    yield chunk
                self._record_success()
                return
            except Exception as e:
                self.logger.error(f"[Failover] Provider {self.providers[self.current_index][0]} 失败: {e}")
                self._record_failure()
                if attempt < max_retries - 1:
                    self._switch_to_next()
                    yield f"\n[Failover] 切换到备选 Provider...\n"
                else:
                    yield f"\n[Failover] 所有 Provider 都失败，请检查服务状态。\n"
                    return


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
        
        # 默认使用 MiMo
        return MiMoProvider()