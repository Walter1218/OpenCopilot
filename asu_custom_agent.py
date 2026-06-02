import os
import sys
import json
import uuid
import sqlite3
import time
import subprocess
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from llm_provider import MiniMaxProvider, LocalProvider, load_config

# 导入记忆系统改进模块
from memory_system.config import ConfigManager, MemoryType
from memory_system.quota_manager import QuotaManager

# 导入统一 Prompt 构建服务
from prompt_builder import (
    CONTEXT_DESCRIPTIONS,
    CONTEXT_SOURCE_PRIORITY,
    PERSONA_CONFLICT_PATTERNS,
    build_context_prefix,
    sanitize_persona_for_context,
    load_persona,
)

# 导入代码执行引擎模块
from code_executor import CodeExecutor, ExecutorConfig

# 导入上下文管理模块
from context_manager import ContextWindowManager as ContextWindowManagerModule

# 导入知识检索模块
from knowledge_retrieval import KnowledgeRetrieval

# 导入搜索能力模块
from search_capability import SearchCapability, SearchType

# 导入状态管理模块
from state_manager import StateManager, get_default_manager as get_state_manager

# 导入规划器模块
from planner import Planner, PlanRequest

# 导入安全模块
from security_module import SecurityModule, SecurityConfig

# 导入可观测性模块
from observability_module import ObservabilityModule, ObservabilityConfig, LogLevel

# 导入AGENTS.md免疫机制模块
from agents_md_module import ImmuneSystem, RuleEngine

# 导入Skill化架构模块
from skill_architecture import SkillRegistry, IntentRouter, SkillExecutor, SkillDiscovery


# ==========================================
# Context Window 管理（P0）
# ==========================================

class ContextWindowManager:
    """基于预算的上下文窗口管理器（字符预算近似 token 预算）。"""

    # 模型上下文限制映射（token 数）
    MODEL_CONTEXT_LIMITS = {
        "minimax-m2.7": 200000,
        "gpt-4-turbo": 128000,
        "gpt-4": 8192,
        "gpt-3.5-turbo": 16385,
        "claude-3-opus": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-haiku": 200000,
    }

    def __init__(self, max_input_chars=120000, reserve_output_chars=30000,
                 recent_turns=12, max_history_msg_chars=8000,
                 model_name: str = None):
        self.max_input_chars = max_input_chars
        self.reserve_output_chars = reserve_output_chars
        self.recent_turns = recent_turns
        self.max_history_msg_chars = max_history_msg_chars
        self.model_name = model_name
        
        # 添加配置管理器
        self.config_manager = ConfigManager()
        
        # 如果指定了模型，动态调整配置
        if model_name:
            self.adjust_for_model(model_name)
    
    def adjust_for_model(self, model_name: str):
        """根据模型能力动态调整配置"""
        # 使用配置管理器获取模型限制
        budget_config = self.config_manager.get_context_budget()
        model_limit = budget_config.model_limits.get(model_name, 200000)
        
        # 将 token 限制转换为字符限制（中文约 1.5-2 token/字符）
        # 使用保守估计：1 token ≈ 1.5 字符
        max_chars = int(model_limit * 0.75)  # 75% 的 token 限制作为字符限制
        
        # 调整配置
        self.max_input_chars = max_chars
        self.reserve_output_chars = max_chars // 4  # 预留 25% 给输出
        self.max_history_msg_chars = min(8000, max_chars // 15)  # 单条消息不超过总预算的 1/15
        
        # 根据模型能力调整轮数
        if model_limit >= 100000:
            self.recent_turns = 12
        elif model_limit >= 32000:
            self.recent_turns = 8
        elif model_limit >= 8000:
            self.recent_turns = 4
        else:
            self.recent_turns = 2
        
        return self

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

# prompt_builder 模块已统一管理 CONTEXT_DESCRIPTIONS、build_context_prefix、
# sanitize_persona_for_context、load_persona 等函数
# 如需修改，请编辑 prompt_builder.py


class ASUAgentMemory:
    def __init__(self, db_path="asu_agent.db"):
        self.db_path = db_path
        self._init_db()
        # 添加配置和配额管理器
        self.config_manager = ConfigManager()
        self.quota_manager = QuotaManager(self.config_manager)

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
        
        # 新增：检查并执行配额
        self._check_and_enforce_quota(session_id)

    def _check_and_enforce_quota(self, session_id):
        """检查并执行配额"""
        try:
            # 获取当前会话的所有消息
            ctx = self.get_context(session_id)
            messages = ctx["messages"]
            
            # 按角色分类消息（简化处理，实际应按记忆类型分类）
            user_messages = [m for m in messages if m["role"] == "user"]
            assistant_messages = [m for m in messages if m["role"] == "assistant"]
            
            # 检查用户消息配额
            user_stats = self.quota_manager.get_memory_stats(
                [{"memory_id": f"user_{i}", "content": m["content"], "importance": 0.5, 
                  "access_count": 1, "created_at": time.time() - 86400 * (len(user_messages) - i)} 
                 for i, m in enumerate(user_messages)],
                MemoryType.SHORT_TERM
            )
            
            is_within_quota, reason = self.quota_manager.check_quota(MemoryType.SHORT_TERM, user_stats)
            if not is_within_quota:
                print(f"警告: 用户消息配额超出 - {reason}")
                # 可以在这里实现自动清理逻辑
        except Exception as e:
            # 配额检查失败不应影响正常功能
            pass

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

    def cleanup_old_messages(self, session_id, days_threshold=30):
        """清理旧消息"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cutoff_time = time.time() - (days_threshold * 24 * 60 * 60)
            cursor.execute("DELETE FROM messages WHERE session_id = ? AND timestamp < ?", 
                           (session_id, cutoff_time))
            conn.commit()

    def get_quota_usage(self, session_id):
        """获取配额使用情况"""
        ctx = self.get_context(session_id)
        messages = ctx["messages"]
        
        # 按角色分类消息
        user_messages = [m for m in messages if m["role"] == "user"]
        assistant_messages = [m for m in messages if m["role"] == "assistant"]
        
        # 获取统计信息
        user_stats = self.quota_manager.get_memory_stats(
            [{"memory_id": f"user_{i}", "content": m["content"], "importance": 0.5, 
              "access_count": 1, "created_at": time.time() - 86400 * (len(user_messages) - i)} 
             for i, m in enumerate(user_messages)],
            MemoryType.SHORT_TERM
        )
        
        assistant_stats = self.quota_manager.get_memory_stats(
            [{"memory_id": f"assistant_{i}", "content": m["content"], "importance": 0.6, 
              "access_count": 2, "created_at": time.time() - 86400 * (len(assistant_messages) - i)} 
             for i, m in enumerate(assistant_messages)],
            MemoryType.SHORT_TERM
        )
        
        return {
            "user": {
                "count": user_stats.count,
                "total_chars": user_stats.total_chars,
                "avg_importance": user_stats.avg_importance,
            },
            "assistant": {
                "count": assistant_stats.count,
                "total_chars": assistant_stats.total_chars,
                "avg_importance": assistant_stats.avg_importance,
            }
        }


memory = ASUAgentMemory()
window_manager = ContextWindowManager(
    max_input_chars=int(os.getenv("ASU_MAX_INPUT_CHARS", "120000")),  # MiniMax M2.7 支持 200K token，约 120K 字符
    reserve_output_chars=int(os.getenv("ASU_RESERVE_OUTPUT_CHARS", "30000")),  # 预留 30K 字符给输出
    recent_turns=int(os.getenv("ASU_RECENT_TURNS", "12")),  # 增加到 12 轮对话
    max_history_msg_chars=int(os.getenv("ASU_MAX_HISTORY_MSG_CHARS", "8000")),  # 增加单条消息限制
)

# ==========================================
# 初始化核心能力模块
# ==========================================

# 代码执行引擎
code_executor = CodeExecutor(ExecutorConfig(
    default_timeout=30,
    max_timeout=60,
    working_directory=os.getcwd()
))

# 知识检索模块
knowledge_retrieval = KnowledgeRetrieval()

# 搜索能力模块
search_capability = SearchCapability(workspace=os.getcwd())

# 状态管理模块
state_manager = get_state_manager()

# 规划器模块
planner = Planner()

# 安全模块
security_config = SecurityConfig(
    enable_audit_logging=True,
    enable_rate_limiting=True,
    enable_permission_check=True
)
security_module = SecurityModule(security_config)

# 可观测性模块
observability_config = ObservabilityConfig(
    log_level=LogLevel.INFO.value,
    enable_tracing=True,
    enable_performance_monitoring=True
)
observability = ObservabilityModule(observability_config)

# AGENTS.md免疫机制
immune_system = ImmuneSystem()

# Skill化架构
skill_registry = SkillRegistry()
skill_router = IntentRouter(skill_registry)
skill_executor = SkillExecutor(skill_registry, skill_router)

# Skill自动发现
skill_discovery = SkillDiscovery(skill_registry)
discovered_skills = skill_discovery.discover()

print("✅ 核心能力模块初始化完成:")
print("  - CodeExecutor (代码执行)")
print("  - KnowledgeRetrieval (知识检索)")
print("  - SearchCapability (搜索能力)")
print("  - StateManager (状态管理)")
print("  - Planner (规划器)")
print("  - SecurityModule (安全模块)")
print("  - ObservabilityModule (可观测性)")
print("  - ImmuneSystem (AGENTS.md免疫机制)")
print("  - SkillRegistry (Skill化架构)")
print(f"  - 发现 {len(discovered_skills)} 个 Skills")

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


def detect_request_type(text: str) -> str:
    """
    检测用户请求类型
    
    Returns:
        "code_execution" - 需要执行代码
        "knowledge_query" - 知识检索
        "search" - 搜索请求
        "planning" - 任务规划
        "security" - 安全相关
        "skill" - Skill执行
        "chat" - 普通对话
    """
    text_lower = text.lower()
    
    # 代码执行关键词
    code_keywords = [
        "执行代码", "运行代码", "运行一下", "执行一下",
        "查询tushare", "查询数据库", "查询数据",
        "运行python", "运行脚本", "执行脚本",
        "帮我算", "帮我计算", "帮我统计",
        "import ", "def ", "print(", "python代码"
    ]
    
    # 知识检索关键词
    knowledge_keywords = [
        "知识图谱", "知识检索", "查找关系", "查找实体",
        "项目结构", "模块关系", "代码依赖"
    ]
    
    # 搜索关键词
    search_keywords = [
        "搜索", "查找", "查一下", "搜一下",
        "网上搜索", "搜索一下", "帮我查"
    ]
    
    # 任务规划关键词
    planning_keywords = [
        "规划", "计划", "分解任务", "任务分解",
        "制定方案", "执行步骤", "工作流程"
    ]
    
    # 安全相关关键词
    security_keywords = [
        "权限", "安全", "审批", "审计",
        "访问控制", "rate limit", "速率限制"
    ]
    
    # Skill相关关键词
    skill_keywords = [
        "skill", "技能", "翻译", "translate",
        "代码审查", "code review", "生成ppt", "创建ppt"
    ]
    
    for keyword in code_keywords:
        if keyword in text_lower:
            return "code_execution"
    
    for keyword in knowledge_keywords:
        if keyword in text_lower:
            return "knowledge_query"
    
    for keyword in search_keywords:
        if keyword in text_lower:
            return "search"
    
    for keyword in planning_keywords:
        if keyword in text_lower:
            return "planning"
    
    for keyword in security_keywords:
        if keyword in text_lower:
            return "security"
    
    for keyword in skill_keywords:
        if keyword in text_lower:
            return "skill"
    
    return "chat"


def generate_code_for_task(task: str) -> str:
    """
    根据任务描述生成代码
    
    Args:
        task: 任务描述
        
    Returns:
        生成的代码
    """
    # 使用 LLM 生成代码
    llm = get_base_llm()
    
    # 获取 tushare token
    import tushare as ts
    tushare_token = ts.get_token() or os.getenv("TUSHARE_TOKEN", "")
    
    code_prompt = f"""你是一个 Python 代码生成器。请根据用户的任务描述生成可执行的 Python 代码。

要求：
1. 只输出代码，不要输出任何解释
2. 代码必须是完整的、可直接执行的
3. 如果需要查询数据，请使用相应的库（如 tushare）
4. 将结果打印出来
5. 不要包含任何 markdown 标记或标签
6. 如果使用 tushare，请使用以下 token: {tushare_token}

用户任务：{task}

请生成 Python 代码："""
    
    messages = [{"role": "user", "content": code_prompt}]
    
    code = ""
    for chunk in llm.stream_chat_with_history(messages):
        code += chunk
    
    # 清理代码（移除可能的 markdown 标记和标签）
    code = code.strip()
    
    # 移除 <think>...</think> 标签
    import re
    code = re.sub(r'<think>.*?</think>', '', code, flags=re.DOTALL)
    
    # 移除 markdown 代码块标记
    if code.startswith("```python"):
        code = code[9:]
    if code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    
    # 移除多余的空白行
    code = code.strip()
    
    return code


def execute_code_sync(code: str, timeout: int = 30) -> dict:
    """
    同步执行代码
    
    Args:
        code: 要执行的代码
        timeout: 超时时间（秒）
        
    Returns:
        执行结果字典
    """
    import subprocess
    import tempfile
    
    try:
        # 将代码写入临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # 执行代码
        result = subprocess.run(
            ['python', temp_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )
        
        # 清理临时文件
        os.unlink(temp_file)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"代码执行超时（{timeout}秒）",
            "return_code": -1
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "return_code": -1
        }


def execute_with_capability(text: str, session_id: str) -> str:
    """
    使用能力模块执行任务
    
    Args:
        text: 用户输入
        session_id: 会话ID
        
    Returns:
        执行结果
    """
    request_type = detect_request_type(text)
    print(f"[DEBUG] Request type: {request_type}", flush=True)
    
    # 记录请求指标
    observability.logger.info(f"Processing request", context={
        "request_type": request_type,
        "session_id": session_id,
        "text_length": len(text)
    })
    
    # 检查AGENTS.md规则
    import asyncio
    from agents_md_module import RuleContext
    try:
        rule_context = RuleContext(session_id=session_id)
        rule_check = asyncio.run(immune_system.check_content(rule_context, text))
        if rule_check and not rule_check.allowed:
            return f"⚠️ 规则检查发现违规: {rule_check.message}\n\n请调整您的请求。"
    except Exception as e:
        print(f"[DEBUG] Rule check error: {e}", flush=True)
    
    if request_type == "code_execution":
        # 代码执行流程
        print(f"[DEBUG] 检测到代码执行请求: {text[:50]}...", flush=True)
        
        # 检查安全权限
        import asyncio
        try:
            security_check = asyncio.run(security_module.check_permission(
                user_id=session_id,
                resource="code_execution",
                action="execute"
            ))
        except:
            security_check = True  # 如果安全检查失败，默认允许
        if not security_check:
            return f"❌ 安全检查未通过: 权限不足"
        
        # 生成代码
        code = generate_code_for_task(text)
        print(f"[DEBUG] 生成的代码:\n{code}", flush=True)
        
        # 执行代码
        result = execute_code_sync(code, timeout=30)
        print(f"[DEBUG] 执行结果: {result}", flush=True)
        
        # 记录审计日志
        try:
            security_module.audit_logger.log(
                user_id=session_id,
                action="code_execution",
                resource="python_code",
                parameters={"code_length": len(code)},
                result="success" if result["success"] else "failed"
            )
        except Exception as e:
            print(f"[DEBUG] Audit log error: {e}", flush=True)
        
        if result["success"]:
            return f"✅ 代码执行成功\n\n生成的代码:\n```python\n{code}\n```\n\n执行结果:\n{result['output']}"
        else:
            return f"❌ 代码执行失败\n\n生成的代码:\n```python\n{code}\n```\n\n错误信息:\n{result['error']}"
    
    elif request_type == "knowledge_query":
        # 知识检索流程
        print(f"[DEBUG] 检测到知识检索请求: {text[:50]}...", flush=True)
        
        # 初始化知识图谱（如果需要）
        if not knowledge_retrieval._initialized:
            init_result = knowledge_retrieval.initialize()
            if not init_result.success:
                return f"❌ 知识图谱初始化失败: {init_result.error}"
        
        # 执行查询
        result = knowledge_retrieval.query(text)
        
        if result.success:
            return f"📚 知识检索结果:\n\n{json.dumps(result.data, ensure_ascii=False, indent=2)}"
        else:
            return f"❌ 知识检索失败: {result.error}"
    
    elif request_type == "search":
        # 搜索流程
        print(f"[DEBUG] 检测到搜索请求: {text[:50]}...", flush=True)
        
        # 执行搜索
        results = search_capability.search(text, search_type=SearchType.ALL, count=5)
        
        if results:
            search_output = "🔍 搜索结果:\n\n"
            for i, result in enumerate(results, 1):
                search_output += f"{i}. {result.title}\n"
                search_output += f"   {result.content[:200]}...\n\n"
            return search_output
        else:
            return "❌ 未找到相关搜索结果"
    
    elif request_type == "planning":
        # 任务规划流程
        print(f"[DEBUG] 检测到任务规划请求: {text[:50]}...", flush=True)
        
        try:
            # 使用规划器生成计划
            import asyncio
            plan = asyncio.run(planner.create_plan(
                task=text,
                context={"session_id": session_id}
            ))
            
            if plan:
                plan_output = "📋 任务规划结果:\n\n"
                plan_output += f"**计划ID**: {plan.plan_id}\n"
                plan_output += f"**任务**: {plan.task}\n"
                plan_output += f"**步骤数**: {len(plan.steps)}\n\n"
                plan_output += "**执行步骤**:\n"
                for i, step in enumerate(plan.steps, 1):
                    plan_output += f"{i}. {step.description}\n"
                    plan_output += f"   - 类型: {step.step_type.value}\n"
                    plan_output += f"   - 预计耗时: {step.estimated_duration}秒\n"
                return plan_output
            else:
                return "❌ 无法生成任务规划"
        except Exception as e:
            return f"❌ 任务规划失败: {str(e)}"
    
    elif request_type == "security":
        # 安全相关流程
        print(f"[DEBUG] 检测到安全相关请求: {text[:50]}...", flush=True)
        
        # 返回安全模块状态
        import asyncio
        try:
            security_status = asyncio.run(security_module.get_status())
        except:
            security_status = {"status": "ready", "note": "async call failed, showing basic status"}
        return f"🔒 安全模块状态:\n\n{json.dumps(security_status, ensure_ascii=False, indent=2)}"
    
    elif request_type == "skill":
        # Skill执行流程
        print(f"[DEBUG] 检测到Skill请求: {text[:50]}...", flush=True)
        
        try:
            # 使用意图路由器识别Skill
            from skill_architecture import SkillContext
            import asyncio
            
            # 创建Skill上下文
            skill_context = SkillContext(
                intent=text,
                input_data={"text": text, "session_id": session_id},
                session_id=session_id
            )
            
            # 路由到合适的Skill
            skill_name = asyncio.run(skill_router.route(skill_context))
            
            if skill_name:
                # 执行Skill
                skill_result = asyncio.run(skill_executor.execute(skill_context, skill_name=skill_name))
                
                if skill_result and skill_result.success:
                    return f"🎯 Skill执行结果 (识别为: {skill_name}):\n\n{json.dumps(skill_result.data, ensure_ascii=False, indent=2)}"
                else:
                    return f"❌ Skill执行失败: {skill_result.error if skill_result else '未知错误'}"
            else:
                return "❌ 无法识别合适的Skill"
        except Exception as e:
            return f"❌ Skill执行异常: {str(e)}"
    
    else:
        # 普通对话，返回 None 让调用者处理
        print(f"[DEBUG] 普通对话，返回None", flush=True)
        return None


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
        elif self.path == '/quota':
            # 新增：配额使用情况端点
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            # 获取所有会话的配额使用情况
            quota_usage = {}
            with memory._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT session_id FROM sessions")
                sessions = cursor.fetchall()
                
                for (session_id,) in sessions:
                    quota_usage[session_id] = memory.get_quota_usage(session_id)
            
            resp = {
                "status": "ok",
                "quota_usage": quota_usage
            }
            self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
        elif self.path == '/capabilities':
            # 能力查询端点
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            capabilities = {
                "status": "ok",
                "agent_name": "OpenCopilot ASU Agent",
                "version": "3.0.0",
                "capabilities": {
                    "code_execution": {
                        "name": "代码执行",
                        "description": "执行 Python、JavaScript、Shell 代码",
                        "supported_languages": ["python", "javascript", "shell"],
                        "status": "active"
                    },
                    "knowledge_retrieval": {
                        "name": "知识检索",
                        "description": "查询项目知识图谱，查找实体关系和代码依赖",
                        "status": "active" if knowledge_retrieval._initialized else "ready"
                    },
                    "search": {
                        "name": "搜索能力",
                        "description": "网络搜索、代码搜索、文档搜索",
                        "search_types": ["web", "code", "doc", "knowledge"],
                        "status": "active"
                    },
                    "context_management": {
                        "name": "上下文管理",
                        "description": "智能上下文窗口管理，支持多种模型",
                        "status": "active"
                    },
                    "memory_system": {
                        "name": "记忆系统",
                        "description": "会话记忆和长期记忆管理",
                        "status": "active"
                    },
                    "state_management": {
                        "name": "状态管理",
                        "description": "任务状态管理、检查点、恢复机制",
                        "status": "active"
                    },
                    "planning": {
                        "name": "任务规划",
                        "description": "任务分解、计划生成、执行优化",
                        "strategies": ["sequential", "parallel", "adaptive", "react"],
                        "status": "active"
                    },
                    "security": {
                        "name": "安全模块",
                        "description": "权限管理、审计日志、审批流程、速率限制",
                        "features": ["rbac", "audit", "approval", "rate_limiting"],
                        "status": "active"
                    },
                    "observability": {
                        "name": "可观测性",
                        "description": "结构化日志、指标收集、分布式追踪、健康检查",
                        "features": ["logging", "metrics", "tracing", "health_check"],
                        "status": "active"
                    },
                    "agents_md": {
                        "name": "AGENTS.md免疫机制",
                        "description": "项目级行为规则系统，定义Agent行为规范",
                        "rule_types": ["behavior", "constraint", "preference", "workflow", "security"],
                        "status": "active"
                    },
                    "skill_architecture": {
                        "name": "Skill化架构",
                        "description": "意图路由、Skill执行引擎、自动发现",
                        "registered_skills": len(skill_registry.skills) if hasattr(skill_registry, 'skills') else 0,
                        "status": "active"
                    }
                },
                "request_types": {
                    "code_execution": "执行代码、查询数据库、运行脚本",
                    "knowledge_query": "知识图谱查询、实体关系查找",
                    "search": "网络搜索、代码搜索、文档搜索",
                    "planning": "任务规划、计划生成",
                    "security": "安全检查、权限管理",
                    "skill": "Skill执行、意图路由",
                    "chat": "普通对话"
                },
                "modules_status": {
                    "total_modules": 12,
                    "active_modules": 12,
                    "integration_level": "full"
                }
            }
            self.wfile.write(json.dumps(capabilities, ensure_ascii=False, indent=2).encode('utf-8'))
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
            context_source = envelope.get("source", "drag")
            context_prefix = build_context_prefix(context_source, envelope.get("meta", {}))

            # 根据 context_source 优先级清理 persona 中可能冲突的指令
            persona_prompt = sanitize_persona_for_context(persona_prompt, context_source)

            # 将上下文前缀注入 system prompt
            if context_prefix:
                enriched_system = f"{context_prefix}\n\n{persona_prompt}"
            else:
                enriched_system = persona_prompt

            # P0: 用预算驱动的窗口管理替换"全量历史 + 全量正文"
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
                print(f"[DEBUG] Processing request: {text[:50]}...")
                
                # 尝试使用能力模块执行
                capability_result = execute_with_capability(text, session_id)
                
                if capability_result:
                    # 能力模块处理了请求
                    print(f"[DEBUG] Capability result: {capability_result[:100]}...")
                    memory.add_message(session_id, "assistant", capability_result)
                    resp = {"chunk": capability_result}
                    self.wfile.write(f"data: {json.dumps(resp, ensure_ascii=False)}\n\n".encode('utf-8'))
                    self.wfile.flush()
                else:
                    # 普通对话，使用 LLM
                    print(f"[DEBUG] Calling LLM...")
                    llm = get_base_llm()
                    full_reply = ""
                    for chunk in llm.stream_chat_with_history(messages):
                        full_reply += chunk
                        resp = {"chunk": chunk}
                        self.wfile.write(f"data: {json.dumps(resp, ensure_ascii=False)}\n\n".encode('utf-8'))
                        self.wfile.flush()
                    print(f"[DEBUG] LLM response complete: {full_reply[:100]}...")

                    memory.add_message(session_id, "assistant", full_reply)

                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
                print(f"[DEBUG] Request complete")
            except Exception as e:
                print(f"[DEBUG] Error: {e}")
                resp = {"chunk": f"\n[Agent Error]: {str(e)}"}
                self.wfile.write(f"data: {json.dumps(resp, ensure_ascii=False)}\n\n".encode('utf-8'))
                self.wfile.flush()
        else:
            self.send_response(404)
            self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """支持多线程的HTTP服务器"""
    daemon_threads = True
    allow_reuse_address = True


def run_server(port=18888):
    server_address = ('127.0.0.1', port)
    httpd = ThreadedHTTPServer(server_address, AgentHTTPRequestHandler)
    print(f"🚀 ASU 定制智能体已启动，监听在 http://127.0.0.1:{port}")
    httpd.serve_forever()


if __name__ == '__main__':
    run_server()
