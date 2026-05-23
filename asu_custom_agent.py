import os
import sys
import json
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from llm_provider import MiniMaxProvider, LocalProvider, load_config

# ==========================================
# 上下文感知的 System Prompt 构建
# ==========================================

# 格式: "source_type": "人类可读的描述模板"
CONTEXT_DESCRIPTIONS = {
    "ide": (
        "当前用户正在代码编辑器（IDE）中工作。用户提供的是代码文件内容。"
        "请以代码审查/架构分析的角度来理解和回应。"
    ),
    "browser": (
        "当前用户正在浏览器中浏览网页。用户提供的是网页文本内容。"
        "请以网页内容分析/信息提取的角度来理解和回应。"
    ),
    "drag": (
        "用户通过拖拽的方式提交了一段文本。该文本可能来自任意应用程序。"
    ),
    "chat": (
        "用户正在与ASU Copilot进行连续对话。请基于已有的对话历史进行连贯的追问回复。"
    ),
}


def build_context_prefix(context_source, context_meta):
    """根据上下文来源和元信息，生成注入到 system prompt 的前缀描述。"""
    base = CONTEXT_DESCRIPTIONS.get(context_source, "")
    parts = [base] if base else []

    if context_meta:
        file_name = context_meta.get("file_name", "")
        language = context_meta.get("language", "")
        app_name = context_meta.get("app_name", "")
        task = context_meta.get("task", "")

        if context_source == "ide" and file_name:
            detail = f"文件名：{file_name}"
            if language:
                detail += f"，编程语言：{language}"
            parts.append(detail)
        elif context_source == "browser" and app_name:
            parts.append(f"浏览器：{app_name}")

        # 任务上下文：工作台设定的任务注入到所有请求中
        if task:
            parts.append(f"用户当前任务：{task}。请围绕此任务目标进行回答，将分析结果与任务关联。")

    return "\n".join(parts)


class ASUAgentMemory:
    def __init__(self):
        self.sessions = {}

    def get_context(self, session_id):
        if session_id not in self.sessions:
            self.sessions[session_id] = {"messages": [], "persona": "default"}
        return self.sessions[session_id]

    def add_message(self, session_id, role, content):
        ctx = self.get_context(session_id)
        ctx["messages"].append({"role": role, "content": content})

    def set_persona(self, session_id, persona):
        ctx = self.get_context(session_id)
        ctx["persona"] = persona

    def clear(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id] = {"messages": [], "persona": "default"}

    def session_count(self):
        return len(self.sessions)


memory = ASUAgentMemory()

personas = {
    "translate": "你是一个金牌翻译官。请将用户提供的文本翻译为中文（如果是中文则翻译为英文）。要求信达雅，只输出翻译结果，不带任何解释和废话。",
    "code": "你是一个资深架构师。请对用户提供的代码进行深度解析：\n1. 总结核心功能。\n2. 指出潜在漏洞或优化空间。\n要求排版清晰，直接输出解析结果。",
    "polish": "你是一个资深编辑。请对用户提供的文本进行润色，修正语病，提升表达的专业度和流畅度，使其更具逻辑性。只输出润色后的结果，不解释。",
    "default": "你是一个强大的AI划词助手。请对用户提供的文本进行处理：如果是外语翻译为中文，如果是代码简要解释，普通文本进行总结或解释。排版清晰，直接输出结果，不说多余的客套话。"
}


def get_base_llm():
    config = load_config()
    provider_type = config.get("provider_type", "minimax")
    if provider_type == "local":
        return LocalProvider(
            api_base=config.get("local_api_base", "http://localhost:11434/v1"),
            model=config.get("local_model", "llama3"),
            api_key=config.get("local_api_key", "sk-local")
        )
    return MiniMaxProvider()


class AgentHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """健康检查端点。"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            resp = {
                "status": "ok",
                "active_sessions": memory.session_count()
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/v1/agent/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data.decode('utf-8'))

            action_type = req.get('action_type', 'default')
            text = req.get('text', '')
            session_id = req.get('session_id', str(uuid.uuid4()))
            is_new_task = req.get('is_new_task', False)

            # 新增：上下文感知参数
            context_source = req.get('context_source', 'drag')
            context_meta = req.get('context_meta', {})

            if is_new_task:
                memory.clear(session_id)
                memory.set_persona(session_id, action_type)

            ctx = memory.get_context(session_id)
            current_persona = ctx["persona"]
            persona_prompt = personas.get(current_persona, personas["default"])

            # 构建上下文前缀
            context_prefix = build_context_prefix(context_source, context_meta)

            # 将上下文前缀注入 system prompt
            if context_prefix:
                enriched_system = f"{context_prefix}\n\n{persona_prompt}"
            else:
                enriched_system = persona_prompt

            messages = [{"role": "system", "content": enriched_system}]
            messages.extend(ctx["messages"])
            messages.append({"role": "user", "content": text})

            memory.add_message(session_id, "user", text)

            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()

            try:
                llm = get_base_llm()
                full_reply = ""
                for chunk in llm.stream_chat_with_history(messages):
                    full_reply += chunk
                    resp = {"chunk": chunk}
                    self.wfile.write(f"data: {json.dumps(resp, ensure_ascii=False)}\n\n".encode('utf-8'))
                    self.wfile.flush()

                memory.add_message(session_id, "assistant", full_reply)
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except Exception as e:
                resp = {"chunk": f"\n[Agent Error]: {str(e)}"}
                self.wfile.write(f"data: {json.dumps(resp, ensure_ascii=False)}\n\n".encode('utf-8'))
                self.wfile.flush()
        else:
            self.send_response(404)
            self.end_headers()


def run_server(port=18888):
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, AgentHTTPRequestHandler)
    print(f"🚀 ASU 定制智能体已启动，监听在 http://127.0.0.1:{port}")
    httpd.serve_forever()


if __name__ == '__main__':
    run_server()
