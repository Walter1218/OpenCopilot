import os
import sys
import json
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from llm_provider import MiniMaxProvider, LocalProvider, load_config

class ASUAgentMemory:
    def __init__(self):
        self.sessions = {} # session_id -> { "messages": [], "persona": "" }

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
    def do_POST(self):
        if self.path == '/v1/agent/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            req = json.loads(post_data.decode('utf-8'))
            
            action_type = req.get('action_type', 'default')
            text = req.get('text', '')
            session_id = req.get('session_id', str(uuid.uuid4()))
            is_new_task = req.get('is_new_task', False)
            
            if is_new_task:
                memory.clear(session_id)
                memory.set_persona(session_id, action_type)
            
            ctx = memory.get_context(session_id)
            # 保持之前的 persona 设定，除非是全新的任务
            current_persona = ctx["persona"]
            persona_prompt = personas.get(current_persona, personas["default"])
            
            messages = [{"role": "system", "content": persona_prompt}]
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
