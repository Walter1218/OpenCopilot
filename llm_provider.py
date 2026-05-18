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

class OpenClawCLIProvider(BaseProvider):
    def __init__(self, agent_name: str = "main"):
        self.agent_name = agent_name or "main"
        
    def stream_chat(self, prompt: str, system_prompt: str = ""):
        if system_prompt:
            # 针对 OpenClaw Agent 模式，采用更强指令格式避免被自带 Persona 覆盖
            full_message = f"请严格执行以下【系统指令】，忽略其他不相关的默认设定：\n\n【系统指令】\n{system_prompt}\n\n【待处理的用户输入】\n{prompt}"
        else:
            full_message = prompt
        return self._run_cli(full_message)
        
    def stream_chat_with_history(self, messages: list):
        # 格式化多轮对话历史，带上角色前缀，帮助 Agent 理解上下文
        formatted_messages = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                formatted_messages.append(f"【系统指令】\n{content}")
            elif role == "assistant":
                formatted_messages.append(f"【AI回复】\n{content}")
            else:
                formatted_messages.append(f"【用户输入】\n{content}")
                
        final_content = "\n\n".join(formatted_messages)
        return self._run_cli(final_content)
        
    def _run_cli(self, content: str):
        import subprocess
        import json
        
        try:
            yield "[OpenClaw 智能体正在思考并执行任务，请稍候...]\n\n"
            
            cmd = ["openclaw", "agent", "--agent", self.agent_name, "-m", content, "--json"]
            
            # 使用 os.environ 传递当前环境变量，确保权限和路径一致
            env = os.environ.copy()
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            output = result.stdout
            
            # 记录详细日志以供排查
            if result.returncode != 0:
                print(f"[OpenClaw Error] Return Code: {result.returncode}")
                print(f"[OpenClaw Error] STDERR: {result.stderr}")
                print(f"[OpenClaw Error] STDOUT: {output}")
            
            # 使用正则精准提取返回的 JSON 对象，避免被日志干扰
            import re
            match = re.search(r"\{\s*\"runId\".*?\}\s*\}$", output, re.DOTALL)
            if not match:
                # 尝试更通用的 JSON 对象匹配
                match = re.search(r"\{.*?\}", output, re.DOTALL)
                
            if match:
                try:
                    data = json.loads(match.group(0))
                    payloads = data.get("result", {}).get("payloads", [])
                    if payloads:
                        final_text = payloads[0].get("text", "")
                        # 简单切片模拟流式打字效果
                        for i in range(0, len(final_text), 3):
                            yield final_text[i:i+3]
                    else:
                        yield "Agent 执行完毕，但没有返回文本。"
                except json.JSONDecodeError:
                    yield f"\n[解析 OpenClaw 返回数据失败]: \n{output}"
            else:
                yield f"\n[Agent 执行失败，可能发生了内部错误]:\n{result.stderr or output}"
                
        except FileNotFoundError:
            yield "\n[未找到 openclaw 命令]: 请确保 OpenClaw 已安装并在系统的 PATH 环境变量中。"
        except Exception as e:
            yield f"\n[调用 OpenClaw 失败]: {str(e)}"

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
            return OpenClawCLIProvider(
                agent_name=config.get("agent_name", "main")
            )
        else:
            return MiniMaxProvider()