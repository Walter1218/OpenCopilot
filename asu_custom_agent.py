import os
import sys
import json
import uuid
import sqlite3
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from llm_provider import MiniMaxProvider, LocalProvider, load_config


# ==========================================
# Context Window 管理（P0）
# ==========================================

class ContextWindowManager:
    """基于预算的上下文窗口管理器（字符预算近似 token 预算）。"""

    def __init__(self, max_input_chars=24000, reserve_output_chars=6000,
                 recent_turns=6, max_history_msg_chars=2200):
        self.max_input_chars = max_input_chars
        self.reserve_output_chars = reserve_output_chars
        self.recent_turns = recent_turns
        self.max_history_msg_chars = max_history_msg_chars

    def _truncate_text(self, text, limit):
        if not text or limit <= 0:
            return ""
        if len(text) <= limit:
            return text
        marker = "\n\n...[已截断]...\n\n"
        marker_len = len(marker)
        if limit <= marker_len + 20:
            return text[:limit]
        head = int((limit - marker_len) * 0.7)
        tail = limit - marker_len - head
        return text[:head] + marker + text[-tail:]

    def _clip_by_source(self, source, text, limit):
        """按来源做裁剪策略：IDE 保留头尾，Browser 偏头部，其他常规截断。"""
        if not text or limit <= 0:
            return ""
        if len(text) <= limit:
            return text

        if source == "ide":
            marker = "\n\n...[IDE内容已裁剪，保留头尾关键片段]...\n\n"
            marker_len = len(marker)
            if limit <= marker_len + 20:
                return text[:limit]
            head = int((limit - marker_len) * 0.55)
            tail = limit - marker_len - head
            return text[:head] + marker + text[-tail:]

        if source == "browser":
            marker = "\n\n...[网页正文已裁剪]...\n\n"
            marker_len = len(marker)
            if limit <= marker_len + 20:
                return text[:limit]
            head = limit - marker_len
            return text[:head] + marker

        return self._truncate_text(text, limit)

    def _build_user_payload(self, envelope, budget):
        source = envelope.get("source", "drag")
        content = envelope.get("content", "")
        selection = envelope.get("selection", "")
        task = envelope.get("task", "")
        custom_instruction = envelope.get("custom_instruction", "")
        meta = envelope.get("meta", {}) or {}

        # 元信息摘要
        meta_parts = []
        for k in ("file_name", "language", "app_name", "title", "url"):
            v = meta.get(k)
            if v:
                meta_parts.append(f"{k}={v}")
        # custom_instruction 优先从 envelope 顶层取，其次从 meta 取
        if not custom_instruction:
            custom_instruction = meta.get("custom_instruction", "")
        meta_text = "；".join(meta_parts)

        # 先构建骨架，再把正文按剩余预算裁剪
        payload_parts = [f"[context_source] {source}"]
        if task:
            payload_parts.append(f"[task] {task}")
        if meta_text:
            payload_parts.append(f"[meta] {meta_text}")
            
        # 注入高级 IDE 上下文
        diagnostics = meta.get("diagnostics")
        if diagnostics and isinstance(diagnostics, list):
            diag_lines = []
            for d in diagnostics:
                sev_idx = d.get("severity", 0)
                severity = ["Error", "Warning", "Information", "Hint"][sev_idx] if isinstance(sev_idx, int) and 0 <= sev_idx <= 3 else "Error"
                diag_lines.append(f"- Line {d.get('line')}: [{severity}] {d.get('message')}")
            if diag_lines:
                payload_parts.append("[diagnostics] (当前文件存在的诊断报错)\n" + "\n".join(diag_lines))
        
        git_diff = meta.get("git_diff")
        if git_diff and isinstance(git_diff, str) and git_diff.strip():
            payload_parts.append(f"[git_diff] (当前文件的未提交变更)\n{git_diff[:2000]}") # 限制长度防止超限

        if custom_instruction:
            payload_parts.append(
                f"[custom_instruction]\n{custom_instruction}\n\n"
                f"请严格按照上述指令对 [selection] 或当前代码块中的文本进行修改，只输出修改后的文本，不要输出任何解释或说明。"
            )
        if selection:
            payload_parts.append(f"[selection]\n{selection}")

        skeleton = "\n\n".join(payload_parts)
        remaining = max(0, budget - len(skeleton) - 20)
        clipped_content = self._clip_by_source(source, content, remaining)
        payload_parts.append(f"[content]\n{clipped_content}")

        return "\n\n".join(payload_parts)

    def _pick_recent_history(self, history_messages, budget):
        """保留最近若干轮历史，并对单条消息做上限截断。"""
        if budget <= 0:
            return []

        selected = []
        recent_msgs = history_messages[-(self.recent_turns * 2):] if self.recent_turns > 0 else history_messages

        # 从最近往前装，保证时序时再翻转
        for msg in reversed(recent_msgs):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            clipped = self._truncate_text(content, self.max_history_msg_chars)
            unit = len(role) + len(clipped) + 16
            if unit > budget:
                break
            selected.append({"role": role, "content": clipped})
            budget -= unit

        selected.reverse()
        return selected

    def build_messages(self, system_prompt, envelope, history_messages):
        """生成最终发给模型的消息列表。"""
        sys_unit = len(system_prompt)
        total_budget = max(1500, self.max_input_chars - self.reserve_output_chars)
        remaining = max(0, total_budget - sys_unit)

        # 历史与当前输入按 45/55 分配预算
        history_budget = int(remaining * 0.45)
        user_budget = max(500, remaining - history_budget)

        history_msgs = self._pick_recent_history(history_messages, history_budget)
        user_payload = self._build_user_payload(envelope, user_budget)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history_msgs)
        messages.append({"role": "user", "content": user_payload})
        return messages


def normalize_context_envelope(req, fallback_text, fallback_source, fallback_meta):
    """兼容新旧协议：优先 context_envelope，其次旧字段。同时确保 custom_instruction 不丢失。"""
    env = req.get("context_envelope")
    safe_fallback_meta = fallback_meta if isinstance(fallback_meta, dict) else {}

    if isinstance(env, dict):
        raw_meta = env.get("meta", safe_fallback_meta)
        safe_meta = raw_meta if isinstance(raw_meta, dict) else {}
        envelope = {
            "source": env.get("source", fallback_source),
            "content": env.get("content", fallback_text),
            "selection": env.get("selection", ""),
            "task": env.get("task", safe_meta.get("task", "")),
            "meta": safe_meta,
            "timestamp": env.get("timestamp", time.time()),
        }
        # 确保 custom_instruction 从 context_meta 合并进 envelope（envelope meta 可能缺少）
        ci = safe_fallback_meta.get("custom_instruction", "")
        if ci and "custom_instruction" not in safe_meta:
            envelope["custom_instruction"] = ci
        elif ci and safe_meta.get("custom_instruction"):
            envelope["custom_instruction"] = safe_meta["custom_instruction"]
    else:
        envelope = {
            "source": fallback_source,
            "content": fallback_text,
            "selection": "",
            "task": safe_fallback_meta.get("task", ""),
            "meta": safe_fallback_meta,
            "timestamp": time.time(),
        }
        ci = safe_fallback_meta.get("custom_instruction", "")
        if ci:
            envelope["custom_instruction"] = ci

    # 兜底：弱类型输入统一转字符串，避免拼装阶段异常
    envelope["source"] = str(envelope.get("source", fallback_source) or fallback_source)
    envelope["content"] = str(envelope.get("content", "") or "")
    envelope["selection"] = str(envelope.get("selection", "") or "")
    envelope["task"] = str(envelope.get("task", "") or "")
    return envelope

# ==========================================
# 上下文感知的 System Prompt 构建
# ==========================================

# 格式: "source_type": "人类可读的描述模板"
CONTEXT_DESCRIPTIONS = {
    "ide": (
        "当前用户正在代码编辑器（IDE）中工作。"
        "如果请求中包含 [diagnostics]（诊断报错）或 [git_diff]（版本变更），请重点结合这些信息来分析代码问题或代码变动。"
        "如果请求中包含 [selection]（用户选中的文本片段）或 [content] 只是一个局部代码块，"
        "说明用户只想修改当前聚焦的代码。此时：只输出修改后的代码片段，不要输出全文，不要输出解释。"
        "如果没有选区，则以代码审查/架构分析的角度来理解和回应。"
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
    "revision": (
        "用户正在对文档进行修订。你收到两部分：[selection] 是用户选中的待修改文本，"
        "[content] 是完整文档。请先按选中文本的要求进行修改，再扫描全文找出由于此修改而产生矛盾"
        "或也应同步调整的位置，标记给用户。"
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
        revision_target = context_meta.get("revision_target", "")
        custom_instruction = context_meta.get("custom_instruction", "")
        source_text = context_meta.get("source_text", "")

        if context_source in ("ide", "revision") and file_name:
            detail = f"文件名：{file_name}"
            if language:
                detail += f"，编程语言：{language}"
            parts.append(detail)
        elif context_source == "browser" and app_name:
            parts.append(f"浏览器：{app_name}")

        # 任务上下文：工作台设定的任务注入到所有请求中
        if task:
            parts.append(f"用户当前任务：{task}。请围绕此任务目标进行回答，将分析结果与任务关联。")

        # 修订模式降级：无全文时告知 Agent 仅做局部修订
        if revision_target and context_source == "revision":
            parts.append(f"[选择文本]（待修订内容）:\n{revision_target}")

        # 自定义指令：明确告诉 Agent 用户的修改要求
        if custom_instruction:
            parts.append(f"[用户修改指令] {custom_instruction}\n请严格按此指令对提供的文本进行修改，只输出修改后的结果，不要输出任何解释。")

        # 聊天模式中附带的源文本上下文
        if source_text and context_source == "chat":
            preview = source_text[:2000] + ("…" if len(source_text) > 2000 else "")
            parts.append(f"[用户当前关注的源文本]:\n{preview}")

    return "\n".join(parts)


def load_persona(action_type):
    """动态加载 Persona 文件，支持热更新"""
    filepath = os.path.join(os.path.dirname(__file__), "personas", f"{action_type}.md")
    if not os.path.exists(filepath):
        filepath = os.path.join(os.path.dirname(__file__), "personas", "default.md")
        if not os.path.exists(filepath):
            return "你是一个强大的AI助手，请直接回答用户的问题。"
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read().strip()


class ASUAgentMemory:
    def __init__(self, db_path="asu_agent.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    persona TEXT DEFAULT 'default',
                    updated_at REAL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            ''')
            conn.commit()

    def get_context(self, session_id):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT persona FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                persona = row[0]
            else:
                persona = "default"
                cursor.execute("INSERT INTO sessions (session_id, persona, updated_at) VALUES (?, ?, ?)", 
                               (session_id, persona, time.time()))
                conn.commit()

            cursor.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
            messages = [{"role": r[0], "content": r[1]} for r in cursor.fetchall()]
            
            return {"messages": messages, "persona": persona}

    def add_message(self, session_id, role, content):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO sessions (session_id, persona, updated_at) VALUES (?, 'default', ?)", 
                           (session_id, time.time()))
            cursor.execute("INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                           (session_id, role, content, time.time()))
            cursor.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (time.time(), session_id))
            conn.commit()

    def set_persona(self, session_id, persona):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # SQLite upsert equivalent
            cursor.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
            if cursor.fetchone():
                cursor.execute("UPDATE sessions SET persona = ?, updated_at = ? WHERE session_id = ?", 
                               (persona, time.time(), session_id))
            else:
                cursor.execute("INSERT INTO sessions (session_id, persona, updated_at) VALUES (?, ?, ?)", 
                               (session_id, persona, time.time()))
            conn.commit()

    def clear(self, session_id):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            cursor.execute("UPDATE sessions SET persona = 'default', updated_at = ? WHERE session_id = ?", (time.time(), session_id))
            conn.commit()

    def session_count(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sessions")
            row = cursor.fetchone()
            return row[0] if row else 0


memory = ASUAgentMemory()
window_manager = ContextWindowManager(
    max_input_chars=int(os.getenv("ASU_MAX_INPUT_CHARS", "24000")),
    reserve_output_chars=int(os.getenv("ASU_RESERVE_OUTPUT_CHARS", "6000")),
    recent_turns=int(os.getenv("ASU_RECENT_TURNS", "6")),
    max_history_msg_chars=int(os.getenv("ASU_MAX_HISTORY_MSG_CHARS", "2200")),
)

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

            # 兼容层：支持新 context_envelope 与旧字段共存
            context_source = req.get('context_source', 'drag')
            context_meta = req.get('context_meta', {})
            envelope = normalize_context_envelope(req, text, context_source, context_meta)

            if is_new_task:
                memory.clear(session_id)
                memory.set_persona(session_id, action_type)

            ctx = memory.get_context(session_id)
            current_persona = ctx["persona"]
            persona_prompt = load_persona(current_persona)

            # 构建上下文前缀
            context_prefix = build_context_prefix(envelope.get("source", "drag"), envelope.get("meta", {}))

            # 将上下文前缀注入 system prompt
            if context_prefix:
                enriched_system = f"{context_prefix}\n\n{persona_prompt}"
            else:
                enriched_system = persona_prompt

            # P0: 用预算驱动的窗口管理替换“全量历史 + 全量正文”
            messages = window_manager.build_messages(
                system_prompt=enriched_system,
                envelope=envelope,
                history_messages=ctx["messages"],
            )

            image_base64 = req.get("image_base64")
            
            if image_base64:
                last_msg_content = messages[-1]["content"]
                messages[-1]["content"] = [
                    {"type": "text", "text": last_msg_content},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ]

            # 持久化原始用户输入，避免丢信息
            user_message_content = []
            user_content = envelope.get("content", text)
            
            if user_content:
                user_message_content.append({"type": "text", "text": user_content})
                
            if image_base64:
                user_message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                })

            if not user_message_content:
                user_message_content.append({"type": "text", "text": "你好"})

            # 将多模态结构直接传入 memory
            memory.add_message(session_id, "user", json.dumps(user_message_content, ensure_ascii=False) if len(user_message_content) > 1 else user_message_content[0]["text"])

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
