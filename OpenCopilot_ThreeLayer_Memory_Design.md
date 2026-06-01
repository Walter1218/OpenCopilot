# OpenCopilot 伴生记忆与智能体进化方案

> **版本**: v2.0 | **日期**: 2026-06-02 | **状态**: Final  
> **设计哲学**: 记忆不是目的，是手段——目的是让你双击右键的那一瞬间，Agent 比你更清楚上下文。  
> **核心假设**: OpenCopilot 是唯一同时拥有"系统级感知"和"完全本地化"的 AI Agent。这个方案不是追平竞品，而是把我们独一无二的伴生数据——应用切换、文件关联、浏览器内容、知识图谱——编织成一张上下文感知网，让记忆成为这张网的有机部分。

---

## 〇、伴生智能：为什么 OpenCopilot 的记忆与别人不同

OpenClaw 和 Hermes 的记忆是"对话记忆"——它们只能记住你和 Agent 聊了什么。OpenCopilot 的记忆可以是"**伴生记忆**"——它在记住对话的同时，还知道你在什么应用里、在看什么文件、刚才从哪个浏览器切过来。

这不是一个功能差异，而是**数据源的维度差异**：

```
OpenClaw/Hermes 的记忆输入:
  用户消息 → LLM 回复 → 提炼 → 记忆文件

OpenCopilot 的记忆输入:
  用户消息 → LLM 回复 → 提炼
  + Broker 应用切换事件（你刚才在 Chrome 查了文档）
  + Broker 浏览器 URL（查的是 OpenClaw 架构文档）
  + IDE 当前文件（现在打开了 events_probe.py）
  + 知识图谱关联（events_probe ←depends_on→ server ←communicates_with→ BrokerEventsWorker）
  + 剪贴板内容（含 traceback 报错）
  → 共同写入今日日志，形成情境化的记忆
```

因此，三层记忆体系的主体设计（L1 SQLite → L2 每日日志 → L3 长期记忆）与 OpenClaw/Hermes 在结构上是相似的——这是经过验证的成熟模式。但记忆的**内容密度和情境丰富度**因 Broker 的伴生数据而根本不同。

**本方案在每一个记忆的读写节点上，都嵌入了伴生数据的注入路径。**

---

## 一、现状诊断

### 1.1 已有能力

OpenCopilot 当前在 `asu_custom_agent.py` 中通过 `ASUAgentMemory` 实现了 **SQLite 会话级持久化**：

```
asu_agent.db (项目根目录)
├── sessions 表    → session_id, persona, updated_at
└── messages 表    → id, session_id, role, content, timestamp
```

| 能力 | 状态 | 说明 |
|------|------|------|
| 按 session_id 存储对话 | ✅ | Agent 重启可恢复 |
| 时间戳记录 | ✅ | 每条消息带 timestamp |
| 上下文窗口裁剪 | ✅ | ContextWindowManager，69% 平均压缩率 |
| Persona 文件化 | ✅ | personas/*.md 热加载 |
| **每日日志** | ❌ | 无 `memory/YYYY-MM-DD.md` |
| **长期记忆** | ❌ | 无 `MEMORY.md` |
| **会话结束后自动提炼** | ❌ | 只存原始消息，不做摘要 |
| **语义记忆检索** | ❌ | 无 `memory_search` 工具 |
| **Broker 系统行为融合** | ❌ | 应用切换日志未进入记忆 |

### 1.2 核心差距

OpenClaw / WorkBuddy 的记忆哲学是 **"Agent 主动写日记"**：

```
会话结束 → session-memory hook → 提炼关键事实 → 追加到 memory/YYYY-MM-DD.md
定期扫描 → Dreaming 后台任务    → 压缩每日日志  → 更新 MEMORY.md
下次启动 → 自动加载今天+昨天日志 → 作为隐式背景上下文注入
```

OpenCopilot 目前是 **"被动记账"** —— 对话历史存在 SQLite 行里，但 Agent 既不主动提炼，也不会在跨天会话中自动加载"昨天的总结"。

---

## 二、三层记忆体系总体设计

### 2.1 架构概览

```
~/.asu_copilot/memory/
├── MEMORY.md                    # 第三层：长期记忆（跨月/年持久事实）
├── 2026-06-01.md                # 第二层：每日日志（今天）
├── 2026-05-31.md                # 第二层：每日日志（昨天，下次启动自动加载）
├── 2026-05-30.md                # 第二层：更早的每日日志（按需检索）
└── dreams.md                    # Dreaming 调度日志（可选，人类审计用）

asu_agent.db                     # 第一层：原始会话消息（保留现有 SQLite）
├── sessions 表
└── messages 表
```

### 2.2 三层职责

| 层级 | 存储 | 生命周期 | 写入者 | 读取时机 |
|------|------|----------|--------|----------|
| **L1 会话记忆** | SQLite `messages` 表 | 会话级（单次对话完整流水） | Agent 每轮对话自动追加 | 同 session_id 对话的上下文窗口 |
| **L2 每日日志** | `memory/YYYY-MM-DD.md` | 天级（当天关键摘要） | Session End Hook 自动提炼 | 下次启动：今天 + 昨天日志注入 System Prompt |
| **L3 长期记忆** | `memory/MEMORY.md` | 永久（跨月/年的核心事实） | Dreaming 定时压缩 | 每次启动：全量注入 System Prompt |

### 2.3 数据流向

```
用户发起对话
    │
    ▼
POST /v1/agent/chat  ←── 注入 L2（今天+昨天日志）+ L3（MEMORY.md）
    │
    ▼
对话进行中 ──→ 每轮写入 L1（SQLite messages）
    │
    ▼
会话结束（Session End Hook 触发）
    │
    ├── 1. Agent 回顾 L1 本次新增消息
    ├── 2. 提炼关键事实（偏好、决策、项目进展）
    ├── 3. 写入 L2 今日日志（memory/YYYY-MM-DD.md）
    │
    ▼
Dreaming 定时任务（每 N 小时或每天一次）
    │
    ├── 1. 读取最近 N 天 L2 每日日志
    ├── 2. LLM 压缩提炼为长期事实
    ├── 3. 合并写入 L3（MEMORY.md）
    └── 4. 写入 dreams.md（记录本次压缩操作，可审计）
```

---

## 三、各层详细设计

### 3.1 L1：会话记忆层（已有，保持核心逻辑不变，增加增量标记）

**实现位置**: `asu_custom_agent.py` → `ASUAgentMemory` 类

**现状**: SQLite 持久化，按 `session_id` 隔离，每轮对话自动追加 `user` 和 `assistant` 消息。

**本次方案对 L1 做最小增量修改**。L1 继续作为 L2 每日日志的**原始数据源**——Session End Hook 从 L1 读取本轮新增消息来做摘要提炼。

#### 3.1.1 最小增量：新增 `last_hook_id` 追踪

现有 `messages` 表已有自增 `id`，只需 Hook 记住上次提取到第几条，下次只读取 `id > last_id` 的消息：

```python
# asu_custom_agent.py → ASUAgentMemory 新增方法

def get_messages_since(self, session_id: str, since_id: int = 0):
    """获取指定 session 中 id > since_id 的新增消息"""
    with self._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, id FROM messages "
            "WHERE session_id = ? AND id > ? ORDER BY id ASC",
            (session_id, since_id)
        )
        return [{"role": r[0], "content": r[1], "id": r[2]} for r in cursor.fetchall()]

def get_last_message_id(self, session_id: str):
    """获取指定 session 最后一条消息的 id"""
    with self._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(id) FROM messages WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] else 0
```

Hook 状态文件 — 记录每个 session 上次提取到哪条消息：

```
~/.asu_copilot/memory/.hook_state.json
{
  "last_extracted_id": {"ASU_IDE_Session": 142, "ASU_Translate_Session": 89}
}
```

这样 Hook 不依赖轮数计数，也不依赖时间戳精度，只依赖 SQLite 自增 ID 的单调性——最简单可靠。

### 3.2 L2：每日日志层（新增，核心设计）

#### 3.2.1 文件格式

`memory/YYYY-MM-DD.md` 的模版结构：

```markdown
# 2026-06-01

## 对话摘要

### 14:30 ｜ IDE Session
- **主题**：修复 Broker 空指针异常
- **关键决策**：采用三层记忆体系对标 OpenClaw
- **偏好记录**：用户偏好先讨论再写代码，不喜欢直接动手

### 16:00 ｜ 翻译任务
- **主题**：技术文档中译英
- **偏好记录**：术语保持原文不翻译

## 系统行为摘要（Broker 协同）

| 时间段 | 活跃应用 | 说明 |
|--------|----------|------|
| 14:00-15:30 | VS Code | 主要开发时段 |
| 15:30-15:45 | Chrome | 查阅 OpenClaw 文档 |
| 15:45-16:00 | Terminal | 运行测试 |

## 待办事项
- [ ] 实现 Session End Hook
- [ ] 实现 Dreaming 定时压缩任务

## 标签
#broker #bugfix #memory-system #三层记忆
```

#### 3.2.2 写入时机 —— Session End Hook

这是一个**关键创新点**。Session End Hook 的触发策略：

```
触发条件（满足任一即触发）:
├── 方案 A: 每次 POST /v1/agent/chat 返回 SSE [DONE] 后立即触发
├── 方案 B: 用户切换 session_id（意味着上一轮对话结束）
└── 方案 C: Agent 空闲超过 5 分钟后触发（可选降级兜底）
```

**推荐采用方案 A + B 组合**：主路径用 A（每次对话结束即提炼），B 作为兜底（确保切换会话时上一会话被处理）。

#### 3.2.2.1 精确注入点

Hook 在 `AgentHTTPRequestHandler.do_POST` 中 `[DONE]` 发送后、`return` 前执行：

```python
# asu_custom_agent.py → AgentHTTPRequestHandler.do_POST（修改后）

# ... 现有 SSE 流式输出逻辑 ...
memory.add_message(session_id, "assistant", full_reply)
self.wfile.write(b"data: [DONE]\n\n")
self.wfile.flush()

# ===== 新增：Session End Hook =====
try:
    _run_session_end_hook(session_id)
except Exception:
    pass  # Hook 失败不阻塞用户响应
# ==================================
```

**关键决策：Hook 是 fire-and-forget 而非阻塞**。原因：
- 用户已经在 `[DONE]` 后看到完整回复，不应因为记忆提炼延迟几秒再关闭连接
- 如果提炼 LLM 调用失败，不应影响本轮对话的成功状态
- Hook 内部有独立的异常捕获和日志记录

#### 3.2.2.2 三级门控（控制 Token 消耗）

Hook 内部的三级过滤，每一步都在前一步通过后才进入下一步：

```python
def _should_extract(session_id: str, new_messages: list) -> bool:
    """三级门控：判断本轮对话是否值得提炼"""

    # 门控 1（免费）：本轮新增消息 < 3 条 → 跳过
    if len(new_messages) < 3:
        return False

    # 门控 2（免费）：纯结束语 / 单轮短对话 → 跳过
    user_texts = [m["content"] for m in new_messages if m["role"] == "user"]
    if all(_is_trivial(m) for m in user_texts):
        return False

    # 门控 3（低成本）：检测是否有「信息密度高」的关键词
    signal_words = [
        "决定", "偏好", "记住", "方案", "修复", "bug",
        "配置", "部署", "升级", "重构", "迁移", "架构",
        "remember", "decision", "prefer", "结论"
    ]
    combined = " ".join(user_texts).lower()
    if not any(w in combined for w in signal_words):
        return False

    return True


def _is_trivial(text: str) -> bool:
    """判断是否为无信息量的短消息"""
    trivial_patterns = ["谢谢", "好的", "ok", "bye", "再见", "嗯", "好", "可以"]
    stripped = text.strip().lower()
    return len(stripped) < 20 or any(
        stripped == p for p in trivial_patterns
    )


def _run_session_end_hook(session_id: str):
    """会话结束后尝试提炼关键事实"""
    # 1. 增量读取
    hook_state = _load_hook_state()
    since_id = hook_state.get("last_extracted_id", {}).get(session_id, 0)
    new_msgs = memory.get_messages_since(session_id, since_id)

    # 2. 三级门控
    if not _should_extract(session_id, new_msgs):
        return

    # 3. 提炼
    prompt = _build_extract_prompt(new_msgs)
    try:
        summary = llm.summarize(prompt)  # 使用低成本模型
    except Exception as e:
        logger.warning(f"记忆提炼失败: {e}")
        return  # 降级：跳过本次提炼，不写日志

    # 4. 写入 L2
    _append_to_daily_log(summary, session_id)

    # 5. 更新 Hook 状态
    last_id = max(m["id"] for m in new_msgs)
    hook_state.setdefault("last_extracted_id", {})[session_id] = last_id
    _save_hook_state(hook_state)
```

#### 3.2.2.3 文件并发写入安全

多个 SSE 连接可能同时结束并触发 Hook。Markdown 文件的追加操作用文件锁保护：

```python
import fcntl

def _append_to_daily_log(daily_path: str, entry: str, session_id: str):
    """线程/进程安全地追加到每日日志"""
    os.makedirs(os.path.dirname(daily_path), exist_ok=True)
    with open(daily_path, "a", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            timestamp = datetime.now().strftime("%H:%M")
            f.write(f"\n### {timestamp} | {session_id}\n{entry}\n")
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

#### 3.2.2.4 降级链路总览

```
Hook 触发
  ├── LLM 提炼 API 不可用 → 跳过，logger.warning → 不影响用户
  ├── 今日日志文件不可写（磁盘满/权限错误） → 跳过，logger.error → 不影响用户
  ├── Hook 状态文件损坏 → 从 0 重新开始 → 可能重复提炼，但不会丢数据
  └── 并发写入冲突 → fcntl 文件锁串行化 → 最后写入者不影响前者
```

**核心原则：Hook 的任何失败都不会传播给用户。**

#### 3.2.3 读取时机 —— 自动注入

Agent 在每次处理 `POST /v1/agent/chat` 时，自动加载 L2 + L3 作为隐式背景上下文：

```python
def load_memory_context() -> str:
    """加载每日日志和长期记忆作为隐式 System Prompt 追加"""
    parts = []
    
    # 长期记忆（L3）
    mem_path = os.path.expanduser("~/.asu_copilot/memory/MEMORY.md")
    if os.path.exists(mem_path):
        parts.append(f"## 长期记忆（来自 MEMORY.md）\n{read_file(mem_path)[:2000]}")
    
    # 今天的日志（L2）
    today_path = os.path.expanduser(f"~/.asu_copilot/memory/{today()}.md")
    if os.path.exists(today_path):
        parts.append(f"## 今日摘要\n{read_file(today_path)[:1500]}")
    
    # 昨天的日志（L2）
    yesterday_path = os.path.expanduser(f"~/.asu_copilot/memory/{yesterday()}.md")
    if os.path.exists(yesterday_path):
        parts.append(f"## 昨日摘要\n{read_file(yesterday_path)[:1000]}")
    
    return "\n\n---\n\n".join(parts) if parts else ""
```

### 3.3 L3：长期记忆层（新增，Dreaming 驱动）

#### 3.3.1 文件格式

`memory/MEMORY.md` 是一个**人工 + AI 共同维护**的精炼文件：

```markdown
# OpenCopilot 长期记忆

> 最后更新: 2026-06-01 18:30 (Dreaming v1)

## 用户偏好

- 编程语言偏好: Python 3.11，严格不使用 Python 3.13
- 工作风格: 讨论方案后再动手，不喜欢 AI 直接改代码
- 代码风格: 不写注释（除非明确要求）
- 沟通语言: 中文
- Git 规范: 在当前开发分支提交，合并 Master 需用户指令

## 项目上下文

### OpenCopilot
- 本地 AI 桌面助手项目，macOS 平台
- 架构: smart_copilot(UI) + asu_custom_agent(Agent) + asu_broker(探针)
- LLM: MiniMax API，本地 Ollama 备选
- 当前阶段: 实现三层记忆体系
- 已完成: Skill 化架构（7 个 Skill，61 个 API）

## 技术决策

- 2026-06-01: 决定采用 Markdown 文件化记忆，对标 OpenClaw 三层架构
- 2026-05-31: 完成 Skill 化综合方案，7 个 Skill 全部实现
- 2026-05-30: 确定全局上下文感知方案（规则引擎 FSM + SLM 混合架构）

## 关键联系人/资源

- MiniMax API Key: 已配置于 .env
- 项目路径: ~/Documents/trae_projects/OpenCopilot
```

#### 3.3.2 写入机制 —— Dreaming 定时压缩

```
触发频率:
├── 开发阶段: 每天 1 次（凌晨 3:00）
├── 或手动触发: 用户说 "总结一下最近的记忆"
└── 或智能触发: L2 累积超过 50KB 未处理日志

Dreaming 流程:
1. 读取自上次 Dreaming 以来新增的 L2 每日日志
2. 调用 LLM（低成本模型）提取可长期保留的事实
3. 合并到 MEMORY.md（去重、更新、冲突标记）
4. 写入 dreams.md 审计日志
```

**Dreaming 提炼 Prompt 模板**：

```
你是一个记忆管理员。请阅读以下最近几天的日志，更新长期记忆文件。

规则：
1. 从日志中提取"跨天仍然成立"的持久事实（偏好、项目信息、技术决策）
2. 不要提取临时的任务进度（如"今天写了 3 个测试用例"）
3. 如果新事实与 MEMORY.md 中已有事实冲突，保留新事实，将旧事实标记为 ~~删除线~~
4. 输出格式：直接输出更新后的完整 MEMORY.md 内容（只修改 DREAMING_AUTO 区域）
5. 控制输出在 2000 字以内

=== 当前长期记忆（MEMORY.md）===
{current_memory_md}

=== 近期日志 ===
{recent_daily_logs}

请输出更新后的 MEMORY.md：
```

#### 3.3.4 L2 用户手动编辑保护

Dreaming 只在 `DREAMING_AUTO_START/END` 注释之间写入。用户可在 `USER_MANUAL_START/END` 之间自由编辑，Dreaming 永不触碰。此外：

- **L2 每日日志**是追加型文件，Dreaming 只读不写
- **用户手动编辑 L2 后**：下次 Dreaming 读取时会包含用户的修改内容，形成"人工校正 → AI 再提炼"的反馈环
- **用户手动编辑 MEMORY.md 后被 Dreaming 覆盖的风险**：三段式分割完美解决——DREAMING 区覆盖、USER 区保留、冲突用删除线标记

### 3.4 MemorySkill：记忆检索 API（新增）

记忆能力以 Skill 形式暴露，但**不参与 IntentRouter**。它只作为 Agent 内部隐式能力 + 用户显式指令触发。

#### 3.4.1 API Schema

| 端点 | 触发方式 | 输入 | 输出 | 说明 |
|------|----------|------|------|------|
| `memory_search` | Agent 自动 tool-call / 用户说"搜索记忆" | `{"query": "...", "days": 30}` | `[{"file": "2026-06-01.md", "snippet": "...", "score": 0.91}]` | 关键词 + 文件名时间过滤 |
| `memory_remember` | 用户说"记住：..." | `{"fact": "偏好 Python 3.11"}` | `{"status": "written", "target": "MEMORY.md"}` | 直接写入 MEMORY.md USER_MANUAL 区 |
| `memory_forget` | 用户说"忘记关于X的记忆" | `{"pattern": "Python 3.13"}` | `{"status": "removed", "count": 2}` | 从所有 L2/L3 文件中删除匹配行 |
| `memory_today` | 用户说"今天做了什么" | `{}` | `{"date": "2026-06-01", "entries": [...]}` | 读取今日日志全文 |
| `memory_summary` | 用户说"总结最近一周的记忆" | `{"days": 7}` | `{"summary": "...", "key_facts": [...]}` | 手动触发 Dreaming |
| `memory_status` | 用户说"记忆状态" | `{}` | `{"l2_files": 14, "l2_total_size_kb": 45, "l3_size_kb": 8}` | 诊断信息，不调用 LLM |

#### 3.4.2 第一阶段实现策略

`memory_search` 先用**文件名 + 简单文本匹配**实现，暂不做向量嵌入：

```python
def memory_search(query: str, days: int = 30) -> list:
    """Phase 1：基于文件名时间过滤 + 关键词行匹配"""
    results = []
    cutoff = datetime.now() - timedelta(days=days)
    memory_dir = os.path.expanduser("~/.asu_copilot/memory/")
    
    for fname in os.listdir(memory_dir):
        if not fname.endswith(".md") or fname == "MEMORY.md":
            continue
        file_date = _parse_date_from_filename(fname)
        if file_date and file_date >= cutoff.date():
            with open(os.path.join(memory_dir, fname)) as f:
                for line in f:
                    if any(word in line.lower() for word in query.lower().split()):
                        results.append({"file": fname, "snippet": line.strip()[:200]})
    return results[:10]
```

Phase 2 再升级为 FTS5 / embedding 语义搜索。Phase 1 的关键词匹配对记忆检索场景（搜索"Broker"、"偏好"、"决定"）已经足够实用。

#### 3.3.3 去重与冲突处理

当新提取的事实与 MEMORY.md 既有条目冲突时：

```markdown
## 用户偏好

<!-- 最新事实优先，旧事实保留带标记 -->
- 编程语言偏好: Python 3.11 ← 2026-06-01 确认
- ~~编程语言偏好: Python 3.13~~ ← 2026-05-15 已过时
```

### 3.4 Broker 协同：系统行为上下文注入（伴生记忆的核心差异化）

这是 OpenCopilot 相较于 OpenClaw/WorkBuddy 的**根本性差异**。Broker 守护进程已经具备全局应用切换监听能力，这不仅是"另一个数据源"，而是**记忆的文件格式本身因它而不同**。

#### 3.4.1 一个记忆条目的对比

```
OpenClaw 的今日日志:
  ### 14:30 | Session XYZ
  - 用户正在修复 Broker 模块的空指针异常
  - 问题定位在 events_probe.py 第 42 行

OpenCopilot 的今日日志（含 Broker 伴生数据）:
  ### 14:30 | Session XYZ
  - 用户正在修复 Broker 模块的空指针异常
  - 问题定位在 events_probe.py 第 42 行
  - 系统行为: 用户在 Chrome（查阅 OpenClaw 架构文档）→ VS Code（events_probe.py）→ Terminal（pytest）
  - 知识图谱: events_probe ←depends_on→ server ←communicates_with→ BrokerEventsWorker
```

当用户一周后问"我上次修那个空指针时参考了哪篇文章？"，OpenCopilot 能回答"你在 Chrome 看了 OpenClaw 架构文档"——而 OpenClaw/Hermes 只能回答"你在某次对话中讨论了空指针修复"。

#### 3.4.2 数据采集

Broker 已有的 `events_probe.py` 和 `app_control_probe.py` 能够捕获：

```
{
  "timestamp": "2026-06-01T14:32:15",
  "event": "app_switch",
  "from_app": "Chrome",
  "to_app": "VS Code",
  "to_app_bundle": "com.microsoft.VSCode"
}
```

#### 3.4.3 注入方式

在 Session End Hook 生成每日日志时，同时拉取 Broker 记录的本日系统行为摘要：

```python
def generate_system_behavior_section():
    """从 Broker 获取当日系统行为，生成 Markdown 摘要表格"""
    events = broker_client.get_today_events()
    
    # 聚合为时间段-活跃应用映射
    timeline = _aggregate_app_timeline(events, interval_minutes=15)
    
    # 生成 Markdown
    md = "## 系统行为摘要\n\n"
    md += "| 时间段 | 活跃应用 | 说明 |\n"
    md += "|--------|----------|------|\n"
    for slot in timeline:
        md += f"| {slot.time} | {slot.app} | {slot.note} |\n"
    return md
```

#### 3.4.4 记忆搜索的未来增强

```
用户: "我上次修复那个空指针异常时，参考了哪篇文章来着？"

Agent: （搜索 memory/*.md）
→ 2026-06-01.md 系统行为摘要显示 15:30-15:45 在 Chrome 浏览
→ 2026-06-01.md 对话摘要显示当时在修 Broker 空指针
→ 答案: "你当时在 Chrome 查阅了 OpenClaw 的官方文档。"
```

---

## 四、实现路线图

### Phase 1: 基础三层记忆（1-2 周）

| 任务 | 产出 | 优先级 |
|------|------|--------|
| 创建 `memory/` 目录结构与文件模版 | `~/.asu_copilot/memory/` 目录 | P0 |
| 实现 Session End Hook | `memory_hook.py`，对话结束后自动提炼写入 L2 | P0 |
| 实现记忆自动注入 | Agent 启动 / chat 请求时加载 L2+L3 到 System Prompt | P0 |
| 实现手动记忆指令 | 支持用户说"记住..."直接写入 MEMORY.md | P0 |
| 单元测试 | Hook 触发、文件读写、注入正确性 | P0 |

### Phase 2: Dreaming 压缩（1 周）

| 任务 | 产出 | 优先级 |
|------|------|--------|
| Dreaming 定时任务 | 定时 cron / 后台线程，读取 L2 压缩到 L3 | P1 |
| 去重与冲突标记 | MEMORY.md 自动去重、旧条目标记 ~~删除线~~ | P1 |
| dreams.md 审计日志 | 每次 Dreaming 记录操作摘要 | P1 |
| 手动触发 Dreaming | 用户说"总结最近记忆"触发 | P1 |

### Phase 3: Broker 协同（1 周）

| 任务 | 产出 | 优先级 |
|------|------|--------|
| Broker 事件收集 API | Broker 提供 `GET /api/events/today` | P2 |
| 系统行为摘要生成 | 每日日志融入应用切换时间线 | P2 |
| 跨来源记忆检索 | 支持"我在 Chrome 看了什么 → 对话中做了什么"联合查询 | P2 |

---

## 五、关键设计决策与风险缓解

### 5.1 Token 成本控制与预算分配

#### 5.1.1 三层预算总览

| 环节 | 输入限制 | 输出限制 | 频率 | 月预估 Token（假设每天 20 轮对话） |
|------|----------|----------|------|----------------------------------|
| Session End Hook 提炼 | ≤ 3000 chars (~750 tokens) | ≤ 500 chars (~125 tokens) | 门控后约 5 次/天 | ~4,400 tokens/天 |
| Dreaming 压缩 | ≤ 15KB (~3,750 tokens) | ≤ 2000 chars (~500 tokens) | 1 次/天 | ~4,250 tokens/天 |
| L2+L3 注入 | ≤ 4,500 chars (~1,125 tokens) | — | 每轮对话 | ~22,500 tokens/天 |
| 记忆搜索 (memory_search) | — | — | 按需，约 3 次/天 | 0（无 LLM 调用） |

**月 Token 预估**：约 30 × (4,400 + 4,250 + 22,500) = **~930K tokens/月**

使用 MiniMax 低价模型（约 ¥0.5/100K tokens），月成本约 **¥4.65**。如果使用本地 Ollama，成本为 0。

#### 5.1.2 与 ContextWindowManager 的整合

L2+L3 注入需要从现有的 Token 预算中扣除，确保不超限：

```python
# asu_custom_agent.py → 修改 build_messages 调用
memory_context = load_memory_context()  # L2 + L3

# 将记忆上下文放在 System Prompt 前部，计入 budget
enriched_system = memory_context + "\n\n" + context_prefix + "\n\n" + persona_prompt

messages = window_manager.build_messages(
    system_prompt=enriched_system,  # 包含记忆上下文
    envelope=envelope,
    history_messages=ctx["messages"],  # L2/L3 不重复占历史预算
)
```

`ContextWindowManager._pick_recent_history()` 的 budget 计算中，`system_prompt` 长度增加了 `memory_context` 部分，历史消息的裁剪会自动更激进以补偿。不需要修改 `ContextWindowManager` 的代码，它的预算模型已经支持。

#### 5.1.3 记忆注入的策略

| 场景 | 注入内容 | 字符限额 |
|------|----------|----------|
| 每天首次对话 | L3 全文 + 今天 L2 + 昨天 L2 | MEMORY.md ≤ 2000 chars, 每天日志 ≤ 1500 chars |
| 同日后续对话 | L3 全文 + 今天 L2（不重复昨天） | 同上 |
| 超过 7 天未对话 | L3 全文 + 最近 7 天 L2 摘要 | MEMORY.md ≤ 2000 chars, 摘要 ≤ 2000 chars |

### 5.2 隐私与安全

| 策略 | 说明 |
|------|------|
| **纯本地存储** | 所有记忆文件仅存在于 `~/.asu_copilot/memory/`，永不上传云端 |
| **脱敏设计** | Session End Hook 的提炼 Prompt 应包含"不要记录密码、API Key 等敏感信息"指令 |
| **用户可审计** | Markdown 格式让用户随时打开文件查看、编辑、删除任何记忆条目 |

### 5.3 与现有 SQLite 的关系

```
SQLite (asu_agent.db)          Markdown (memory/)
─────────────────────          ──────────────────
原始数据源（不可读流）     →    提炼输出（人类可审计）
精确到每条消息             →    精炼到关键事实
高保真（用于上下文窗口）   →    低保真（用于长期记忆）
保留不改                   →    新增机制
```

**两者不是替代关系，而是上下游关系。** SQLite 是原始数据源，Markdown 是从中提炼的认知精华。

---

## 六、测试策略

| 测试场景 | 验证点 |
|----------|--------|
| Session End Hook 触发 | 对话结束后，今日日志文件有新条目 |
| 长对话提炼质量 | 5000 字对话提炼为 3-5 条关键事实，无遗漏核心信息 |
| 记忆注入正确性 | 下次聊天时切换 session_id，Agent 仍能引用昨天的关键事实 |
| Dreaming 压缩 | 连续 3 天日志 → 1 次 Dreaming → MEMORY.md 正确去重更新 |
| 手动"记住"指令 | 用户说"记住：我用 Python 3.11" → 写入 MEMORY.md |
| 并发安全 | 同时多次对话结束 → 日志文件不损坏、不丢条目 |
| Broker 协同 | 当日有应用切换记录 → 日志包含系统行为摘要表格 |

---

## 七、与现有功能的关系

```
                    ┌──────────────────────┐
                    │   smart_copilot.py   │
                    │   (UI 层，用户入口)   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  asu_custom_agent.py │
                    │  (Agent 核心)         │
                    │                      │
                    │  ┌────────────────┐  │
                    │  │ Session End    │  │  ← 新增
                    │  │ Hook           │  │
                    │  └───────┬────────┘  │
                    │          │           │
                    │  ┌───────▼────────┐  │
                    │  │ ASUAgentMemory │  │  ← 已有
                    │  │ (SQLite L1)    │  │
                    │  └───────┬────────┘  │
                    └──────────┼───────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
  ┌───────▼──────┐   ┌────────▼────────┐   ┌───────▼──────┐
  │ memory/      │   │ Dreaming        │   │ Broker       │
  │ YYYY-MM-DD   │   │ 定时任务         │   │ 系统事件      │
  │ (L2 每日日志) │   │ (L3 长期记忆)   │   │ (行为上下文)  │
  └──────────────┘   └─────────────────┘   └──────────────┘
```

---

## 八、端到端示例：一天的工作记忆流

以用户 6 月 1 日使用 OpenCopilot 的完整一天为例，展示三层记忆如何流转。

### 8.1 场景序列

```
09:30  用户唤醒 OpenCopilot，说 "帮我修一下 Broker 的空指针异常"
       → Agent 响应，对话 8 轮
       → 门控通过 ✅（8轮 > 3，含"修复"+"bug"关键词）
       → Hook 提炼写入 memory/2026-06-01.md:
         ### 09:30 | ASU_IDE_Session
         - 用户正在修复 Broker 模块的空指针异常
         - 问题定位在 events_probe.py 第 42 行

11:00  用户说 "翻译一段技术文档"
       → 对话 4 轮
       → 门控通过 ✅
       → Hook 追加:
         ### 11:00 | ASU_Translate_Session
         - 偏好：技术术语保留原文不翻译

14:30  用户说 "你好" → Agent 回复 "你好" → 结束
       → 门控拒绝 ❌（消息 < 3 条）

16:00  用户讨论 "三层记忆体系的架构设计"
       → 对话 12 轮，做出关键决策
       → Hook 追加:
         ### 16:00 | ASU_IDE_Session
         - 关键决策：采用 Markdown 文件化记忆，对标 OpenClaw
         - 技术选型：Session End Hook 用 fire-and-forget 模式
         - 偏好确认：用户倾向先讨论方案再动手写代码

03:00  Dreaming 定时任务触发
       → 读取 memory/2026-06-01.md（今日 3 条提炼）
       → 发现新事实：用户偏好先讨论再动手、术语保留原文
       → 写入 MEMORY.md:
         用户偏好:
         - 工作风格: 讨论方案后再动手 ← 2026-06-01
         - 技术翻译偏好: 术语保留原文 ← 2026-06-01
       → 写入 dreams.md:
         [2026-06-02 03:00] Dreaming v1: 2 条新事实，0 条冲突
```

### 8.2 次日唤醒验证

```
6 月 2 日 09:00  用户唤醒 OpenCopilot
```

Agent 启动时 `load_memory_context()` 返回：

```
## 长期记忆（来自 MEMORY.md）
- 用户偏好：讨论方案后再动手，不喜欢 AI 直接改代码
- 用户偏好：技术术语保留原文不翻译
- 项目：OpenCopilot 本地 AI 桌面助手，macOS + MiniMax

## 昨天摘要（2026-06-01.md）
- 修复了 Broker 空指针异常（events_probe.py#42）
- 决定采用三层记忆体系对标 OpenClaw
```

此时用户说 "Broker 那个空指针修好了吗？"——Agent 不再需要用户重新解释上下文，直接从记忆注入中定位到昨天的事件并给出准确回复。

### 8.3 一周后跨会话检索

```
6 月 8 日  用户说 "我们之前讨论的 Markdown 还是 SQLite 做记忆存储来着？"
          → Agent 调用 memory_search("Markdown 记忆 存储")
          → 命中 2026-06-01.md: "采用 Markdown 文件化记忆，对标 OpenClaw"
          → Agent: "6 月 1 日你决定用 Markdown 文件化记忆，对标 OpenClaw 三层架构"
```

---

**附录：参考资源**
- [OpenClaw Memory Overview](https://docs.openclaw.ai/concepts/memory) —— 三层记忆架构参考
- [WorkBuddy 知识库与记忆系统](https://github.com/KadenMc/work-buddy) —— SOUL.md + MEMORY.md 设计参考
- [AIOS: LLM Agent Operating System](https://arxiv.org/abs/2403.16971) —— 情节记忆（Episodic Memory）概念

---

# 附录：OpenCopilot × OpenClaw × Hermes Agent × WorkBuddy 能力差距全景对比

> 目的：识别 OpenCopilot 相对于同级 Agent 产品的缺失能力，确定后续功能补强优先级。

## A. 竞品概览

| 维度 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|------------|----------|-------------|-----------|
| 出品方 | 开源社区 | 开源社区（MIT） | Nous Research（MIT） | 腾讯云 CodeBuddy 团队 |
| 定位 | 桌面级 AI Copilot，系统级交互增强 | 通用 AI Agent Gateway，多消息渠道网关 | 自进化 AI Agent 框架，LLM 训练数据工厂 | AI 桌面智能体工作台，职场全场景 |
| 形态 | PyQt6 桌面 GUI，悬浮卡片 | 终端 + 多 IM 渠道（WhatsApp/Telegram/Discord 等） | CLI + 多 IM 渠道 | 桌面客户端 + 微信小程序 |
| GitHub Stars | — | 145K+ | 126K+ | 闭源 |
| 核心差异 | 系统级监听 + 右键悬浮唤出 + Broker 特权代理 | 多消息渠道网关 + 100+ Skill 生态 | 闭环学习循环 + 自动写 Skill + RL 训练管线 | 零部署 + 企业微信/QQ 打通 + Skills 市场 |

> **注意**：市面上"WorkBuddy"有两款同名产品——印度销售 App 和腾讯桌面 Agent。本文讨论的是**腾讯云 WorkBuddy**（AI 智能体桌面工作台）。

## B. 十二维度能力差距矩阵

### B1. 记忆系统

| 能力 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---------:|:--------:|:-----------:|:---------:|
| 会话持久化 | ✅ SQLite | ✅ SQLite/Markdown | ✅ Markdown 文件 | ✅ 云端 |
| 每日日志（memory/YYYY-MM-DD.md） | ❌ | ✅ | ✅ | ✅ |
| 长期记忆（MEMORY.md） | ❌ | ✅ | ✅ | ✅ |
| 记忆自动压缩/提炼（Dreaming） | ❌ | ✅ Dreaming | ✅ 学习循环 | ✅ 自动摘要 |
| 记忆语义搜索（memory_search） | ❌ | ✅ 混合搜索 | ✅ 嵌入搜索 | ✅ 知识库检索 |
| 可插拔记忆后端 | ❌ | ✅ SQLite/QMD/Honcho/LanceDB | ✅ Pluggable Provider（v0.7.0） | ❌ |
| 用户可审计（纯文本可编辑） | ❌（SQLite 黑盒） | ✅ Markdown | ✅ Markdown | ⚠️ 云端 |
| **差距等级** | **基准** | **🔴 大幅领先** | **🔴 大幅领先** | **🟡 领先** |

### B2. Skill / 自我进化

| 能力 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---------:|:--------:|:-----------:|:---------:|
| 技能系统 | ✅ 7 个 Skill（手动实现） | ✅ 100+ Skill 生态 | ✅ 40+ 内置 + ∞ 自动生成 | ✅ 20+ Skills 市场 |
| Agent 自动创建 Skill | ❌ | ❌ | ✅ **核心差异**（闭环学习） | ❌ |
| Skill 市场/社区共享 | ❌ | ✅ ClawHub | ✅ agentskills.io | ✅ Skills 市场 |
| Skill 版本控制 | ❌ | ✅（如 npm） | ✅ SKILL.md 标准 | ⚠️ |
| **差距等级** | **基准** | **🟡 领先** | **🔴 大幅领先** | **🟡 领先** |

### B3. 多消息渠道 / 跨端触达

| 能力 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---------:|:--------:|:-----------:|:---------:|
| 桌面 GUI | ✅ PyQt6 悬浮卡片 | ❌（终端/Web） | ❌（终端/Web） | ✅ 桌面客户端 |
| 微信/企微 | ❌ | ⚠️ 需自行对接 | ❌ | ✅ 原生支持 |
| Telegram / Discord / Slack | ❌ | ✅ 原生 10+ 渠道 | ✅ 原生多渠 | ❌ |
| 跨端消息续接 | ❌ | ✅ 跨渠道续接 | ✅ 跨渠道续接 | ✅ |
| 手机远程操控桌面 | ❌ | ✅ | ✅ | ✅ |
| **差距等级** | **基准** | **🔴 大幅领先** | **🔴 大幅领先** | **🟡 领先** |

> OpenCopilot 的悬浮卡片是**独特的"零摩擦"交互优势**。多消息渠道属于不同的产品定位（OpenClaw 的 Message-First 模型），OpenCopilot 不做远程触达——用户就在桌面，Agent 就在手边。

### B4. 定时调度 / 自主后台运行

| 能力 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---------:|:--------:|:-----------:|:---------:|
| Cron 定时任务 | ❌ | ✅ | ✅（自然语言 Cron） | ✅ |
| 后台自主运行 | ✅（LaunchAgent 常驻） | ✅ | ✅ | ✅ |
| 定时报告推送 | ❌ | ✅ | ✅ 早报/周报 | ✅ |
| 事件触发（文件变更等） | ⚠️（Broker 有基础事件） | ✅ | ✅ | ✅ |
| **差距等级** | **基准** | **🔴 领先** | **🔴 领先** | **🟡 领先** |

### B5. 多 Agent 协同

| 能力 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---------:|:--------:|:-----------:|:---------:|
| 并行 Sub-Agent | ❌ | ✅ 多智能体路由 | ✅ 独立 Sub-Agent | ✅ 多 Agent 并行 |
| Agent 间任务分发 | ❌ | ✅ 路由规则 | ✅ 编排器 | ✅ 引擎自动拆解 |
| 工作区隔离 | ❌ | ✅ 多工作区 | ✅ Session 隔离 | ✅ |
| **差距等级** | **基准** | **🔴 领先** | **🔴 领先** | **🟡 领先** |

### B6. 语音交互

| 能力 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---------:|:--------:|:-----------:|:---------:|
| 语音输入 | ❌ | ⚠️ 第三方 | ✅ CLI + Telegram + Discord | ✅ 微信语音 |
| TTS 输出 | ❌ | ⚠️ | ✅ | ⚠️ |
| **差距等级** | **基准** | **🟡 领先** | **🔴 大幅领先** | **🟡 领先** |

### B7. MCP 协议 / 工具生态

| 能力 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---------:|:--------:|:-----------:|:---------:|
| MCP 客户端 | ❌ | ✅ | ✅（含 ACP） | ✅ 内置 |
| 作为 MCP Server 对外暴露 | ❌ | ❌ | ✅（Claude Code/Cursor 可用） | ❌ |
| Tool 调用编排 | ⚠️（Skill 框架已有） | ✅ | ✅ 47 内置工具 | ✅ |
| 浏览器自动化 | ⚠️（DOM 提取，只读） | ✅ 完整浏览器操控 | ✅ Playwright + Camofox | ✅ |
| **差距等级** | **基准** | **🟡 领先** | **🔴 大幅领先** | **🟡 领先** |

### B8. 代码执行沙盒

| 能力 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---------:|:--------:|:-----------:|:---------:|
| 本地终端执行 | ❌（无沙盒） | ✅ Docker 沙盒 | ✅ 6 种后端（本地/Docker/SSH/模态等） | ✅ 沙盒隔离 |
| 远程执行 | ❌ | ❌ | ✅ SSH / Modal | ❌ |
| 安全拦截（命令审查） | ❌ | ⚠️ | ✅ Tirith 安全层 | ✅ 危险操作拦截 |
| **差距等级** | **基准** | **🟡 领先** | **🔴 大幅领先** | **🟡 领先** |

### B9. 身份/性格定义

| 能力 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---------:|:--------:|:-----------:|:---------:|
| Persona 定义 | ✅ personas/*.md 热加载 | ✅ SOUL.md | ✅ SOUL.md | ✅ |
| Agent 身份命名 | ❌ | ✅ IDENTITY.md | ✅ IDENTITY.md | ✅ |
| **差距等级** | **🟢 持平** | **🟢 →** | **🟢 →** | **🟢 →** |

> Persona 系统是 OpenCopilot 对齐业界标准的领域，仅缺 IDENTITY 命名文件。

### B10. 知识库 / RAG

| 能力 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---------:|:--------:|:-----------:|:---------:|
| 本地文档索引/RAG | ✅ KnowledgeSkill + 知识图谱 | ✅ | ⚠️ | ✅ 知识库（.md/.pdf/.docx） |
| 项目知识图谱 | ✅ 264 实体 + 166 关系 | ❌ | ❌ | ❌ |
| **差距等级** | **🟢 局部领先** | **🟢 →** | **🟢 →** | **🟢 →** |

> 知识图谱是 OpenCopilot 相对竞品的独特能力。

### B11. Provider 容错

| 能力 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---------:|:--------:|:-----------:|:---------:|
| 多 Provider | ✅ MiniMax + Ollama | ✅ 模型无关 | ✅ 200+ 模型 | ✅ 混元/DeepSeek/GLM |
| 故障转移 | 🔶 待开发 | ✅ 自动 | ✅ Credential Pools（v0.7.0） | ✅ |
| API Key 轮转 | ❌ | ❌ | ✅ 多 Key 自动轮换 | ⚠️ |
| **差距等级** | **基准** | **🟡 领先** | **🔴 大幅领先** | **🟡 领先** |

### B12. 安全模型

| 能力 | OpenCopilot | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---------:|:--------:|:-----------:|:---------:|
| 本地数据不出设备 | ✅ | ✅ | ✅ | ⚠️（云端） |
| 密钥泄露防护 | ❌ | ⚠️（曾有 CVE） | ✅ 密钥扫描 + 输出审查 | ✅ |
| 命令审批工作流 | ❌ | ⚠️ | ✅ Tirith 审批流 | ✅ |
| 容器硬化 | ❌ | ⚠️ | ✅ 只读 root / 丢 CAP | ✅ |
| **差距等级** | **基准** | **🟡 领先** | **🔴 大幅领先** | **🟡 领先** |

## C. 差距总览与优先级排序

| 优先级 | 缺失能力 | 影响面 | 实现难度 | 对标产品 |
|--------|----------|--------|----------|----------|
| **P0** | 三层记忆体系（每日日志 + 长期记忆 + Dreaming） | 用户体验核心——Agent 不记得昨天聊了什么 | 中 | OpenClaw / Hermes |
| **P1** | Provider 故障转移 + API Key 轮转 | 可用性——单 Key 挂掉 Agent 就不可用 | 低 | Hermes v0.7.0 |
| **P1** | Cron 定时调度 | 自主性——Agent 只能等用户唤醒，不能主动做事 | 中 | OpenClaw / Hermes |
| **P1** | 代码执行沙盒（Docker/沙盒隔离） | 安全性——当前直接执行无隔离 | 中高 | Hermes / WorkBuddy |
| **P2** | 语音交互 | 交互多样性——纯文本输入 | 中 | Hermes |
| **P2** | 多 Agent 协同 / Sub-Agent | 复杂任务拆解——单 Agent 线性执行 | 高 | Hermes v0.6.0 |
| **P2** | Skill 自动生成（PG8 半自动模式） | 从规则天花板突破到多步工作流生成 | 中高 | Hermes |
| **P1** | MCP 协议（Client + Server） | 从桌面闭环通往生态连接——连接外部工具 + 对外暴露独有能力 | 中 | Hermes / OpenClaw / WorkBuddy |
| **不做** | 多消息渠道（Telegram/微信） | 场景不匹配——桌面内生设计，不需要远程渠道 | — | — |

## D. OpenCopilot 的独特优势（不可替代性）

在识别差距的同时，需明确 OpenCopilot 已有的**结构性优势**，这些是竞品难以复制的：

| 优势 | 说明 | 竞品状态 |
|------|------|----------|
| **系统级无感交互** | 双击右键悬浮卡片，无需切换窗口、打开终端 | 竞品的 CLI/IM 模式需要上下文切换 |
| **Broker 特权代理** | 突破 macOS 沙盒，读取浏览器 DOM、系统选区、屏幕截图 | 竞品普遍无系统级权限 |
| **全局应用切换感知** | 知道用户在用什么应用，可以做上下文预测 | 竞品无此能力 |
| **知识图谱** | 264 实体 + 166 关系，结构化项目知识 | 竞品无此能力 |
| **Persona 文件化热加载** | 编辑 .md 即生效，无需重启 | 对齐业界标准 |
| **双图层光标特效** | 视觉反馈增强交互仪式感 | 竞品无此能力 |

## E. 结论

OpenCopilot 在**交互体验层**（悬浮卡片、系统级唤醒、Broker 特权探针）具有显著差异化优势，但在**Agent 基础设施层**（记忆、MCP、调度、沙盒、多渠道）存在系统性差距。

建议采用"**保住交互优势，补齐 Agent 基建**"的策略：
1. 首先完成三层记忆体系（P0）
2. 然后完成故障转移 + Cron + 沙盒 + MCP 协议（P1，可用性 + 生态连接）
3. 最后考虑 Skill 自动生成 + 多 Agent + 语音（P2，生态扩展）

记忆系统是整个差距清单中**影响最大、实现难度适中、竞品已充分验证**的方向——这也正是本设计方案聚焦的切入点。

---

# 附录二：智能体内核粒度深度对比

> 区别于附录一的产品级功能对比，本章聚焦**智能体引擎内部的代码级机制**——Skill 怎么加载、Persona 怎么注入、记忆怎么读写、Prompt 怎么拼装、Agent Loop 怎么跑。

## F. Skill 体系：注册、发现、加载、执行

### F1. SKILL 的物理形态

| 细节 | OpenCopilot | OpenClaw | Hermes Agent |
|------|------------|----------|-------------|
| Skill 载体 | Python 类（继承 `BaseSkill`） | 目录 + `SKILL.md`（YAML frontmatter + Markdown） | 目录 + `SKILL.md`（agentskills.io 标准） |
| 元数据 | 类属性 `intents` / `name` / `description` | frontmatter: `name`, `description`, `requires.{bins,env,config,os}` | frontmatter: `name`, `description`, `version`, `platforms` |
| Skill 体积控制 | 每个 Skill 一个 .py 文件（~300-400 行） | 每个 Skill 一个目录，含 SKILL.md + 可选 install.sh | 同 OpenClaw，agentskills.io 兼容 |
| 社区共享 | ❌ 无分发机制 | ✅ ClawHub 安装 + 同步 | ✅ agentskills.io + `hermes skills install` |

> **差距**：OpenCopilot 的 Skill 是"代码包"（Python 类），OpenClaw/Hermes 的 Skill 是"文档包"（SKILL.md）。前者需要写代码才能新增 Skill，后者只需写 Markdown。

### F2. Skill 发现与加载机制

| 细节 | OpenCopilot | OpenClaw | Hermes Agent |
|------|------------|----------|-------------|
| 发现方式 | `SkillDiscovery` 扫描 `skill_architecture/` 下 `*_skill.py` | 6 级优先级目录合并（workspace > project > personal > managed > bundled > extraDirs） | `~/.hermes/skills/` 目录扫描 |
| 加载时机 | Agent 启动时全量注册到 Registry | 每次 Run 时 build snapshot，按 eligibility 过滤 | 每次对话启动时 scan，按 `select_relevant()` 选择性注入 |
| 条件门控 | ❌ 无（所有 Skill 始终可用） | ✅ `requires.{bins,anyBins,env,config,os}` 运行时校验 | ✅ 基于 `platforms` / `prerequisites` 门控 |
| 热更新 | ❌ 需重启 Agent | ✅ Skill watcher 自动检测文件变更并刷新 | ✅ 编辑文件即刻生效 |
| **Token 消耗策略** | 全量 Skill 名注入 System Prompt | Progressive 三层：名称列表 → 描述摘要 → 全文按需加载 | Progressive 三层：轻量描述 ~3K tokens 覆盖全部 Skill → 仅匹配时才加载完整 SKILL.md |

> **差距**：OpenCopilot 缺三级门控和条件激活，所有 Skill 无论是否相关都全量在 Prompt 中声明。

### F3. Skill 执行与路由

| 细节 | OpenCopilot | OpenClaw | Hermes Agent |
|------|------------|----------|-------------|
| 路由机制 | `IntentRouter` 基于关键词 + 意图映射匹配 Skill | 无中心路由——Skill 以 tool 形式暴露给 LLM，LLM 自行决定调用哪个 | 无中心路由——Skill 以 slash command + tool 形式暴露 |
| 组合执行 | ✅ `SkillExecutor` 支持多 Skill 链式组合 | ⚠️ LLM 自己编排多 tool 调用序列 | ✅ Sub-agent 委托 + LLM 自行编排 |
| 执行隔离 | 同一进程内函数调用 | Docker 沙盒 / Wasm | 6 种后端（本地/Docker/SSH/Daytona/Singularity/Modal） |
| 错误处理 | SkillResult 返回 success/error | Tool 返回结构化错误，LLM 自行处理 | 同 OpenClaw |

> **差距**：OpenCopilot 的 IntentRouter 是中心化路由（人工定义意图 → Skill 映射），竞品是去中心化的（LLM 自行选择 tool）。前者确定性强但扩展性弱——新增 Skill 需要更新路由规则。

## G. Prompt 拼装机制

这是智能体内核最核心的"烹饪"环节——System Prompt 是怎么一层层组装出来的。

### G1. OpenCopilot 的 Prompt 拼装

```python
# asu_custom_agent.py → AgentHTTPRequestHandler.do_POST
enriched_system = context_prefix + "\n\n" + persona_prompt   # 上下文前缀 + Persona
messages = window_manager.build_messages(
    system_prompt=enriched_system,    # L1: persona + context_prefix
    envelope=envelope,                # 用户输入 + 历史消息
    history_messages=ctx["messages"]  # SQLite 提取的会话历史
)
```

**拼装层次**（只有 2 层）：
```
System Prompt = context_prefix（IDE/Browser 来源标记）
              + persona_prompt（personas/*.md 全文）
              
Messages = System Prompt + 裁剪后的历史消息 + 当前用户输入
```

### G2. Hermes Agent 的 Prompt 拼装

```
System Prompt 组装链（context_engine.py / prompt_builder.py）：

Layer 1: Base system prompt（硬编码的行为指令）
Layer 2: SEMANTIC MEMORY — USER.md + MEMORY.md（每轮必定注入，~2K-4K tokens）
Layer 3: SKILLS（轻量描述列表，~3K tokens 覆盖全部 Skill）
Layer 4: Active Skill FULL BODY（仅当当前任务匹配到特定 Skill 时才注入完整 SKILL.md）
Layer 5: Tool definitions（47 内置工具 + MCP 工具的 JSON Schema）
Layer 6: Session context（当前会话的最近 N 轮消息）
Layer 7: Episodic Memory 检索结果（从 sessions.db FTS5 搜索到的相关历史片段）

总计约 6-10K tokens 的 System Prompt，其中：
- 固定部分：Layer 1-3（约 5K tokens，可被 LLM Provider 缓存）
- 动态部分：Layer 4-7（约 1-5K tokens）
```

### G3. 关键差异

| 细节 | OpenCopilot | Hermes Agent |
|------|------------|-------------|
| Prompt 层数 | 2 层 | 7 层 |
| 记忆注入 | ❌ 无（L2/L3 尚未实现） | ✅ layer 2 必定注入 USER.md + MEMORY.md |
| Skill 注入策略 | 全量 Skill 名列表 | 渐进式：描述列表 → 匹配 Skill 全文 |
| Episodic 检索 | ❌ 无语义搜索 | ✅ FTS5 全文搜索历史会话 |
| Cache 友好 | ⚠️ 未考虑 | ✅ 固定层可被 LLM 缓存 |
| 上下文来源区分 | ✅ IDE/Browser/Drag 来源感知（独有） | ❌ 无系统级上下文来源感知 |

> **核心差距不在技术复杂度，而在"分层思维"**——Hermes 把 System Prompt 当成一个精心设计的七层蛋糕，每层有独立的读写策略和 Token 预算。OpenCopilot 目前是"把所有东西混在一起倒进 Prompt"。

## H. 记忆读写机制

### H1. 写入侧对比

| 细节 | OpenCopilot（当前） | OpenClaw | Hermes Agent |
|------|-------------------|----------|-------------|
| 写入触发 | 每轮对话后自动 SQLite INSERT | Session End Hook → 追加 memory/YYYY-MM-DD.md | `memory_manager.py` 在 turn 之间 nudge Agent 写入 MEMORY.md / USER.md |
| 写入粒度 | 全文逐条存储（user + assistant 完整消息） | 提炼后的关键事实摘要 | 提炼后的事实 + 偏好 + 决策 |
| 写入决策 | 无条件全部写入 | Session 结束后触发 | 启发式判断——Agent 自评"是否值得记住" |
| 去重 | ❌ | ⚠️ | ✅ 冲突标记 ~~删除线~~ |
| 用户手动写入 | ❌ | ✅ "Remember that..." | ✅ "Remember that..." |

### H2. 读取侧对比

| 细节 | OpenCopilot（当前） | OpenClaw | Hermes Agent |
|------|-------------------|----------|-------------|
| 会话启动时加载 | SQLite 按 session_id 加载历史消息 | 今天 + 昨天的 memory/*.md + MEMORY.md | USER.md + MEMORY.md 全量注入 + sessions.db FTS5 搜索相关片段 |
| 加载方式 | `ctx = memory.get_context(session_id)` 返回全部消息 | 文件系统读取 Markdown | `context_engine.py` 多层拼装 |
| 搜索能力 | ❌ 无（只能按 session_id 精确查） | ✅ `memory_search` 混合搜索（向量 + 关键词） | ✅ FTS5 全文搜索 |
| 上下文裁剪 | ✅ ContextWindowManager 预算驱动 | ✅ Compaction 压缩 | ✅ 自适应推理预算 |

> **核心差距**：OpenCopilot 的记忆是"被动存 + 精确读"（只能按 session_id 查），Hermes 是"主动写 + 语义搜"（Agent 自己决定什么时候写，跨会话语义搜索）。

## I. Agent Loop 主循环结构

### I1. OpenCopilot 的 Agent Loop

```
POST /v1/agent/chat
  → 解析请求参数（action_type, session_id...）
  → 从 SQLite 加载历史消息
  → 加载 Persona Markdown 文件
  → 拼装 System Prompt（persona + context_prefix）
  → ContextWindowManager 裁剪历史
  → 调用 LLM stream_chat_with_history()
  → SSE 流式输出 [DONE]
  → SQLite 追加本轮 user/assistant 消息
  → 返回
```

**特点**：请求-响应模型，一轮对话 = 一次 HTTP 请求。没有"对话后进行后处理"的步骤。

### I2. Hermes Agent 的 Agent Loop

```
User Message 到达（Telegram/Discord/CLI）
  → 1. Load context（分层拼装 System Prompt）
  → 2. LLM reasoning（tool calling loop）
  → 3. Tool execution（每 15 次 tool call 暂停自我评估）
  → 4. Response to user
  → 5. POST-TURN PROCESSING:
       ├── memory_manager decides: "Should I write to MEMORY.md?"
       ├── skill_creation heuristic: "Worth creating a SKILL.md?"
       └── Honcho user model update (dialectic USER.md refinement)
  → 6. Session snapshot 更新
  → 7. 返回
```

**特点**：
- 有明确的 **Post-Turn Processing** 阶段（step 5-6）
- **自我评估检查点**：每 15 次 tool call 暂停，自评"我做了什么？什么有效？什么失败？值得记录吗？"
- **Skill 创建启发式**：Prompt 中软性建议"5+ tool call 的复杂任务应该写 Skill"，非硬编码检测

### I3. 关键差异

| 细节 | OpenCopilot | Hermes Agent |
|------|------------|-------------|
| 循环模型 | 请求-响应（1 轮 = 1 HTTP） | 持久进程，有 post-turn 后处理 |
| Tool Call 自检 | ❌ | ✅ 每 15 次 tool call 自评 |
| Post-Turn 处理 | ❌ | ✅ 记忆回写 + Skill 创建判断 + 用户模型更新 |
| 自主写入 | ❌ Agent 不主动写任何东西 | ✅ Agent 决定是否写 MEMORY.md / USER.md / SKILL.md |

> **这是 OpenCopilot 最大的 Agent 级架构差距**：当前 Agent Loop 在 `[DONE]` 后就结束了。Hermes 的 `[DONE]` 后才是"真正的工作"——自我反思、记忆提炼、Skill 沉淀。

## J. Persona / Identity 粒度对比

| 细节 | OpenCopilot | OpenClaw | Hermes Agent |
|------|------------|----------|-------------|
| Persona 定义 | `personas/*.md` → 纯 Markdown 正文 | `SOUL.md` → Markdown | `SOUL.md` → Markdown |
| 热加载 | ✅ `load_persona()` 每次请求读文件 | ✅ 文件变更自动刷新 | ✅ 文件变更自动刷新 |
| Agent 身份命名 | ❌ 无单独 IDENTITY 文件 | ✅ `IDENTITY.md`（名字 + 定位） | ✅ `IDENTITY.md` |
| 用户模型 | ❌ 无（Persona 是"AI 角色"，不是"用户画像"） | ⚠️ 通过 MEMORY.md 间接表达 | ✅ `USER.md`（风格/专业水平/目标），Honcho 持续 dialectic 更新 |
| Agent 间 Persona 隔离 | N/A（单 Agent） | ✅ 每个 Agent 独立 SOUL.md + 工作区 | ✅ Profile 隔离 |

> **差距**：OpenCopilot 的 Persona 只定义了"AI 是什么角色"，没有"用户是谁"的用户画像（USER.md）。Hermes 的 Honcho 系统通过持续 dialectic 对话自动更新用户模型——比如"发现用户喜欢先讨论再动手"会自动写入 USER.md。

## K. 总结：OpenCopilot 智能体内核的五项结构性缺失

按重要性和可实现性排序：

| # | 缺失项 | 竞品做到什么程度 | 一句话解释 |
|---|--------|-----------------|-----------|
| 1 | **Post-Turn Processing** | Hermes：对话结束后自动自我评估 + 记忆回写 + Skill 沉淀 | Agent Loop 在 `[DONE]` 后啥也不做 |
| 2 | **分层 Prompt 拼装** | Hermes：7 层 System Prompt，固定层可缓存 | 当前只有 2 层：context_prefix + persona |
| 3 | **渐进式 Skill 加载** | OpenClaw/Hermes：名称列表 → 描述摘要 → 按需全文 | 所有 Skill 全量声明在 Prompt 中 |
| 4 | **Agent 自主记忆写入** | Hermes：memory_manager 在 turn 间 nudge Agent 写 MEMORY.md | SQLite 被动存，无提炼 |
| 5 | **用户画像模型** | Hermes：USER.md + Honcho 持续 dialectic 更新 | 只有 AI 角色定义，没有用户画像 |

**补救优先级**：

```
P0: Post-Turn Processing（为三层记忆体系提供执行时机）
    └── 本身也是三层记忆方案的 Phase 1 Session End Hook 的落地形式

P1: 分层 Prompt 拼装（降低 Token 消耗，提升缓存命中）
    └── 将 L2/L3 记忆注入到独立的 Prompt 层

P2: 渐进式 Skill 加载（Skill 数量增长后必需）
    └── 当前 7 个 Skill 问题不大，但 50+ Skill 后必需

P3: Agent 自主记忆写入（记忆提炼自动化）
    └── 即三层记忆方案中的 Dreaming / Session End Hook

P4: 用户画像模型（长期个性化）
    └── 需要 Honcho 级别的持续 dialectic 机制
```

---

# 附录三：搜索能力设计方案

> OpenCopilot 当前只有结构化的知识图谱检索，缺少非结构化搜索（对话历史、记忆文件）和外部联网搜索。本附录补齐这两块。

## L. 现状

| 搜索类型 | 状态 | 说明 |
|----------|:---:|------|
| 知识图谱实体搜索 | ✅ | 264 实体，`/entity/search` API |
| 翻译记忆搜索 | ✅ | 精确/模糊匹配 |
| 术语库搜索 | ✅ | 模糊/精确/前缀/后缀 |
| 对话历史搜索 | ❌ | SQLite 只能按 session_id 精确查 |
| 记忆文件搜索 | ❌ | memory_search 还在设计阶段 |
| **联网搜索** | ❌ | 无任何外部搜索工具 |

## M. 设计目标

1. Agent 能主动搜索自己的记忆——"我之前讨论过 Broker 的什么 bug？"
2. Agent 能联网查资料——"搜索最新的 Python 3.13 asyncio 变化"
3. 搜索结果是 tool 的返回值，Agent 基于搜索结果做后续推理
4. 成本可控、本地优先、隐私不泄露

## N. 三层搜索架构

```
┌─────────────────────────────────────────────┐
│              Layer 3: 联网搜索               │
│  LLM 判断需要外部信息 → web_search(query)    │
│  搜索结果以 tool result 形式注入对话         │
├─────────────────────────────────────────────┤
│              Layer 2: 记忆搜索               │
│  memory_search(query)                       │
│  搜索 L2 每日日志 + L3 MEMORY.md             │
│  Phase 1: 关键词匹配 → Phase 2: FTS5/向量    │
├─────────────────────────────────────────────┤
│              Layer 1: 对话历史搜索            │
│  history_search(session_id, query)          │
│  搜索 SQLite messages 表的对话内容            │
│  Phase 1: SQL LIKE → Phase 2: FTS5 全文索引  │
└─────────────────────────────────────────────┘
```

## O. Layer 1：对话历史搜索

### O1. SQLite FTS5 实现（Phase 1 即可做）

现有 `messages` 表没有全文索引。建立 FTS5 虚拟表实现毫秒级搜索：

```python
# asu_custom_agent.py → ASUAgentMemory 新增

def _init_fts(self):
    """初始化全文搜索索引"""
    with self._get_conn() as conn:
        conn.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts 
            USING fts5(content, role, session_id, 
                       tokenize='unicode61 remove_diacritics 2')
        ''')
        # 触发器：自动同步 messages → messages_fts
        conn.execute('''
            CREATE TRIGGER IF NOT EXISTS messages_ai_fts 
            AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts(rowid, content, role, session_id)
                VALUES (NEW.id, NEW.content, NEW.role, NEW.session_id);
            END
        ''')
        conn.execute('''
            CREATE TRIGGER IF NOT EXISTS messages_ad_fts 
            AFTER DELETE ON messages BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content, role, session_id)
                VALUES ('delete', OLD.id, OLD.content, OLD.role, OLD.session_id);
            END
        ''')

def search_history(self, query: str, session_id: str = None, limit: int = 10) -> list:
    """全文搜索对话历史"""
    with self._get_conn() as conn:
        if session_id:
            rows = conn.execute(
                "SELECT content, role, session_id, rank FROM messages_fts "
                "WHERE messages_fts MATCH ? AND session_id = ? "
                "ORDER BY rank LIMIT ?",
                (query, session_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT content, role, session_id, rank FROM messages_fts "
                "WHERE messages_fts MATCH ? "
                "ORDER BY rank LIMIT ?",
                (query, limit)
            ).fetchall()
    return [
        {"content": r[0][:300], "role": r[1], "session_id": r[2], "score": r[3]}
        for r in rows
    ]
```

### O2. 作为 Tool 暴露给 Agent

Agent 的 System Prompt 中新增一个 tool 定义：

```json
{
  "name": "search_history",
  "description": "搜索你与用户的对话历史，找到相关讨论",
  "parameters": {
    "query": "搜索关键词",
    "session_id": "可选，限定特定会话"
  }
}
```

Agent 在需要回忆时主动 tool-call `search_history("Broker 空指针")`。

## P. Layer 2：记忆搜索（已在 §3.4 设计）

即 MemorySkill 的 `memory_search` 端点。Phase 1 关键词匹配，Phase 2 FTS5/向量。与 Layer 1 的区别：Layer 1 搜原始对话，Layer 2 搜提炼后的每日日志和长期记忆。

## Q. Layer 3：联网搜索

### Q1. 设计原则

| 原则 | 说明 |
|------|------|
| **按需搜索** | LLM 自行判断是否需要搜索，类似 tool-call 决策 |
| **用户可感知** | 搜索动作在 UI 中展示（"🔍 正在搜索：Python 3.13 asyncio 变化..."） |
| **成本可控** | 每次搜索 ≤ 3 条结果，每条摘要 ≤ 500 字 |
| **隐私优先** | 搜索词通过 MiniMax API / SearXNG 自建实例，不经过第三方追踪 |

### Q2. 实现方案：SearXNG 自建 + LLM tool-call

```
用户: "Python 3.13 的 asyncio 有什么新变化？"
  → Agent 判断：训练数据截止日期前的知识可能不完整
  → Agent tool-call: web_search("Python 3.13 asyncio changes 2026")
  → SearXNG 返回前 5 条结果（标题 + URL + 摘要）
  → Agent 提取关键信息，组织回答
```

**为什么用 SearXNG 而非直接调 Google API**：
- 自托管，零外部依赖，不消耗 API 额度
- 聚合多搜索引擎（Google/Bing/DuckDuckGo）
- Docker 一键部署，与 OpenCopilot 本地优先理念一致
- 搜索结果无追踪、无广告

### Q3. Tool 定义

```json
{
  "name": "web_search",
  "description": "搜索互联网获取最新信息。当你需要的信息超出训练数据范围时使用",
  "parameters": {
    "query": "搜索关键词",
    "num_results": 3
  }
}
```

### Q4. 搜索结果注入

搜索结果作为 tool result 注入对话，不进入长期记忆（避免记忆污染）：

```
System: [Tool Result - web_search("Python 3.13 asyncio")]
1. What's New in Python 3.13 - asyncio
   https://docs.python.org/3.13/whatsnew/3.13.html#asyncio
   摘要：Python 3.13 引入了 asyncio.TaskGroup 的改进...

2. Python 3.13 asyncio changes - Real Python
   ...
```

## R. 实现路线图

| Phase | 内容 | 工作量 | 优先级 |
|-------|------|--------|--------|
| Search Phase 1 | SQLite FTS5 对话历史搜索 + MemorySkill 关键词搜索 | 1 周 | P0 |
| Search Phase 2 | SearXNG 部署 + web_search tool | 1 周 | P1 |
| Search Phase 3 | 嵌入向量语义搜索（memory + history） | 1 周 | P2 |

---

# 附录四：自主执行能力设计方案

> OpenCopilot 当前完全是"请求-响应"模式——Agent 永远不会主动做任何事。本附录设计 Cron 定时调度 + tool-calling loop + 事件驱动触发三层能力，赋予 Agent 独立执行任务的能力。

## S. 核心思路：三段式独立执行

```
被动模式（当前）：用户在桌面上唤醒 → 输入文字 → Agent 响应

主动模式（目标）：
  ├── Cron 触发：凌晨 3:00 → Agent 生成日报摘要 → 次日唤醒时展示在卡片中
  ├── 事件触发：Chrome→VS Code 切换 → Agent 自动采集浏览器上下文 → 静默注入上下文快照
  └── 桌面内生执行：用户在 VS Code 里写代码时，Agent 后台跑测试 → 桌面通知弹出结果
```

实现自主执行需要三层基础设施：

| 层 | 功能 | 依赖 |
|----|------|------|
| **触发器层** | Cron / 事件驱动 / 桌面上下文变化 → 生成 Agent 任务 | 无 |
| **执行层** | tool-calling loop → Agent 推理 + 调 tool + 看结果 + 再推理 | 工具集（沙盒/浏览器/文件） |
| **结果投递层** | 执行完成后 → 桌面通知 / 下一次唤出卡片时摘要展示 | macOS 通知 |

## T. Trigger 层：Cron 定时调度

### T1. 最小实现

不引入外部依赖，直接复用 Python 标准库：

```python
# agent_scheduler.py（新增文件，Agent 启动时加载）

import schedule
import time
import threading
from datetime import datetime

class AgentScheduler:
    """Agent 定时任务调度器"""
    
    def __init__(self, agent_client):
        self.client = agent_client
        self._thread = None
        self._running = False
    
    def start(self):
        """启动调度线程"""
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    
    def _run(self):
        while self._running:
            schedule.run_pending()
            time.sleep(30)  # 30 秒轮询，足够
    
    def add_daily(self, time_str: str, task_prompt: str):
        """添加每日定时任务
        
        Args:
            time_str: "08:00", "18:30"
            task_prompt: 触发时发送给 Agent 的提示词
        """
        schedule.every().day.at(time_str).do(
            self._execute, task_prompt
        )
    
    def add_interval(self, minutes: int, task_prompt: str):
        """添加间隔任务"""
        schedule.every(minutes).minutes.do(
            self._execute, task_prompt
        )
    
    def _execute(self, prompt: str):
        """执行定时任务：POST 一条消息到 Agent"""
        try:
            httpx.post(
                "http://127.0.0.1:18888/v1/agent/chat",
                json={
                    "text": prompt,
                    "session_id": f"cron_{datetime.now().strftime('%Y%m%d_%H%M')}",
                    "action_type": "auto",
                    "context_source": "cron",
                    "is_new_task": True
                },
                timeout=120
            )
        except Exception as e:
            logger.error(f"Cron task failed: {e}")
```

### T2. Hook 到 Agent 启动

```python
# asu_custom_agent.py → run_server() 新增

scheduler = AgentScheduler(None)  # self-referencing, inject after init
scheduler.add_daily("08:00", "[每日早报] 请总结昨天的工作，列出今天建议的待办事项")
scheduler.start()
```

### T3. Cron 任务配置化

V1 用代码配置，V2 用 `~/.asu_copilot/cron.json`：

```json
{
  "tasks": [
    {"schedule": "08:00", "prompt": "[每日早报] 请总结昨天的工作"},
    {"schedule": "18:00", "prompt": "[每日回顾] 今天完成了什么？有什么阻塞？"},
    {"interval_minutes": 60, "prompt": "[健康检查] Broker 和 Agent 状态是否正常？"}
  ]
}
```

## U. Execute 层：Tool-Calling Loop

这是自主执行最核心的缺失能力。当前 Agent 只会生成文本，当 Cron 触发它说"帮我跑一下测试并分析结果"时，它需要能够：

```
接收消息 → 推理(需要先跑 pytest) → tool_call: execute_command("pytest")
         → 收到 test output → 推理(2 个失败，1 个是空指针)
         → 生成最终回复: "测试结果：2/15 失败，主要问题是..."
```

### U1. 最小 Tool 集

| Tool | 功能 | 安全约束 |
|------|------|----------|
| `read_file(path)` | 读取文件内容 | 仅限项目目录 |
| `write_file(path, content)` | 写入文件 | 仅限项目目录，大文件需确认 |
| `execute_command(cmd)` | 执行终端命令 | 白名单命令（git/pytest/python/ls/cat/grep），危险命令拦截 |
| `search_history(query)` | 搜索对话历史 | — |
| `memory_search(query)` | 搜索记忆文件 | — |
| `web_search(query)` | 联网搜索 | 结果仅注入当前对话，不写入记忆 |

### U2. Tool-Calling Loop 实现

```python
# asu_custom_agent.py → 新增 tool_calling_loop

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "执行终端命令。支持：git, pytest, python, ls, cat, grep",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令"}
                },
                "required": ["command"]
            }
        }
    },
    # ... 其他 tool 定义
]

def run_with_tools(messages: list, llm) -> str:
    """带 tool-calling 的对话循环"""
    max_iterations = 10  # 防止无限循环
    
    for _ in range(max_iterations):
        response = llm.chat_with_tools(messages, TOOLS)
        
        if response.finish_reason == "stop":
            # 不需要 tool，直接返回文本
            return response.content
        
        elif response.finish_reason == "tool_calls":
            # 执行 tool，将结果追加到 messages 继续循环
            for tool_call in response.tool_calls:
                result = execute_tool(tool_call.name, tool_call.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            continue
    
    return "[Agent] 达到最大推理步数"

def execute_tool(name: str, args: dict) -> str:
    """执行 tool 并返回结果"""
    if name == "execute_command":
        cmd = args["command"]
        if not _is_safe_command(cmd):
            return f"[Blocked] 命令 '{cmd}' 不在白名单中"
        return subprocess.run(cmd, shell=True, capture_output=True, 
                              text=True, timeout=30).stdout[:2000]
    elif name == "search_history":
        return json.dumps(memory.search_history(args["query"]))
    elif name == "web_search":
        return _searxng_search(args["query"])
    # ...
```

## V. 事件驱动执行层

Broker 已经能通过 WebSocket 推送 `app_activated` 事件。加一层规则引擎让这些事件能触发 Agent：

```python
# event_trigger.py（新增）

EVENT_RULES = [
    {
        "name": "chrome_to_ide_with_error",
        "pattern": {
            "from_app": "Chrome",
            "to_app": "VS Code",
            "clipboard_contains": ["error", "exception", "traceback", "报错"]
        },
        "prompt": "用户刚从浏览器切换回 IDE，剪贴板中含报错信息。请分析这个报错并建议修复方案。\n\n报错内容：{clipboard}",
        "cooldown_seconds": 300  # 5 分钟内不重复触发
    },
    {
        "name": "morning_first_switch",
        "pattern": {
            "time_range": ["06:00", "10:00"],
            "to_app": "VS Code",
            "first_switch_of_day": True
        },
        "prompt": "[早上好] 今天有什么计划？需要我帮你回顾昨天的进度吗？",
        "cooldown_seconds": 3600  # 1 小时内不重复
    }
]

class EventTrigger:
    def __init__(self, agent_url="http://127.0.0.1:18888/v1/agent/chat"):
        self.agent_url = agent_url
        self._last_triggered = {}  # cooldown 管理
        self._first_switch_today = True
    
    def on_event(self, event: dict):
        """Broker WebSocket 事件到达时调用"""
        for rule in EVENT_RULES:
            if self._match(event, rule):
                if self._in_cooldown(rule["name"]):
                    continue
                self._trigger(rule["prompt"].format(
                    clipboard=_get_clipboard()
                ))
                self._last_triggered[rule["name"]] = time.time()
    
    def _trigger(self, prompt: str):
        """向 Agent 发送消息（非阻塞）"""
        threading.Thread(target=self._post_agent, args=(prompt,), daemon=True).start()
    
    def _post_agent(self, prompt: str):
        try:
            httpx.post(self.agent_url, json={
                "text": prompt,
                "session_id": f"event_{uuid.uuid4().hex[:8]}",
                "context_source": "system_event",
                "is_new_task": True
            }, timeout=120)
        except Exception:
            pass  # 事件驱动失败不阻塞
```

## W. 结果投递层

Cron 执行完后，结果到达用户的路径完全在桌面内闭环——不需要离开 OpenCopilot 的上下文：

```python
import subprocess

def deliver_result(title: str, body: str, context_snapshot: dict = None):
    """桌面内生结果投递：通知 + 下一次唤出卡片时自动展示"""
    # 方式 1: 立即桌面通知
    subprocess.run([
        "osascript", "-e",
        f'display notification "{body}" with title "{title}" sound name "Glass"'
    ])
    
    # 方式 2: 存入 context_snapshot，下一次双击右键时在卡片顶部展示
    # "💡 凌晨 3:00 日报已生成：昨天修复了 Broker 空指针异常..."
    if context_snapshot is not None:
        context_snapshot["pending_delivery"] = {
            "title": title,
            "body": body,
            "delivered_at": time.time()
        }
```

**为什么不用 Telegram 推送**：OpenCopilot 的核心假设是你人就在桌面。凌晨 Cron 跑了日报，第二天早上你双击右键时卡片自动显示摘要——不需要另外打开一个消息 App。这和 OpenClaw 的 Message-First 模型有本质区别：你不是在"等消息"，而是在"唤醒时自然看到"。

## X. 完整闭环示例

```
07:55  Cron 触发 → scheduler._execute("[每日早报] ...")
08:00  Agent tool-call loop:
         → search_history("昨天 修复 bug") → 找到 3 条相关对话
         → 生成日报摘要
         → deliver_result("OpenCopilot 日报", "3 个关键事项...", context_snapshot)
08:01  日报已存入 context_snapshot["pending_delivery"]

09:00  用户打开电脑
       → Broker 检测到早上首次切换到 VS Code
       → EventTrigger 触发: "[早上好] 今天有什么计划？"
       → 桌面通知弹出
       
09:05  用户双击右键唤出卡片
       → 卡片顶部显示: "💡 今早日报（06:01 生成）：昨天修复了 Broker 空指针异常..."
       → 用户不需要做任何操作，信息已在手边
```

## Y. 实现路线图

| Phase | 内容 | 依赖 | 优先级 |
|-------|------|------|--------|
| 自主 Phase 1 | Cron 调度器 + macOS 通知 | 无 | P1 |
| 自主 Phase 2 | tool-calling loop（6 个最小 tool） | Cron 到位后 | P1 |
| 自主 Phase 3 | 事件驱动触发器（5 条规则） | tool-calling 到位后 | P2 |
| 自主 Phase 4 | 桌面内生结果投递（唤醒时展示 + 通知） | 独立 | P2 |

---

# 附录五：统一优先级排序（整合版）

将记忆体系、搜索能力、自主执行三条线的所有 Phase 合并排序：

| # | 能力 | 所属线 | 优先级 | 一句话 |
|---|------|--------|--------|-------|
| 1 | 三层记忆 Phase 1（Hook + L2 + L3 注入） | 记忆 | **P0** | Agent 记不住昨天聊了什么 |
| 2 | FTS5 对话历史搜索 | 搜索 | **P0** | 搜不到过去的讨论 |
| 3 | 分层 Prompt 拼装 | 记忆/内核 | **P1** | Token 浪费 + 无缓存 |
| 4 | 记忆 Phase 2（Dreaming 压缩） | 记忆 | **P1** | 每日日志不压缩会无限增长 |
| 5 | Cron 定时调度 | 自主 | **P1** | Agent 不能主动做事 |
| 6 | tool-calling loop | 自主 | **P1** | Agent 不能调工具 |
| 7 | SearXNG 联网搜索 | 搜索 | **P1** | Agent 不能查最新资料 |
| 8 | 代码执行沙盒 | 安全 | **P1** | 安全隔离 |
| 9 | 渐进式 Skill 加载 | 内核 | **P2** | 7 个 Skill 问题不大，50+ 后必需 |
| 10 | 事件驱动触发器 | 自主 | **P2** | Broker 事件只显示不用 |
| 11 | 记忆 Phase 2.5（向量语义搜索） | 搜索 | **P2** | 关键词匹配够用，语义搜索锦上添花 |
| 12 | 桌面内生结果投递（唤醒时展示） | 自主 | **P2** | Cron 结果的优雅展示方式 |
| 13 | 多任务会话管理 | 交互 | **P2** | 只能单线程对话，无法切换任务 |
| 14 | Skill 自动生成（PG8 半自动） | 内核 | **P2** | 从规则天花板突破到多步工作流 |
| 15 | MCP 协议 | 扩展 | **P1** | 从桌面闭环通往生态连接 |

---

# 附录六：多任务会话管理设计方案

> 竞品（WorkBuddy/OpenClaw/Hermes）都具备"一个任务一个独立窗口/卡片"的能力，不同任务之间上下文完全隔离。OpenCopilot 目前是单卡片单会话——开始新话题要么污染旧上下文，要么丢失旧任务。本附录填补这一体验层面的结构性缺失。

## Z. 现状

| 能力 | OpenCopilot | WorkBuddy | Hermes Agent |
|------|:---:|:---:|:---:|
| 单次对话 | ✅ 悬浮卡片 | ✅ | ✅ |
| 任务工作台（全局背景注入） | ✅ 三击右键 | ✅ | ✅ |
| 多任务并行界面 | ❌ | ✅ 多窗口/卡片 | ✅ 多 session |
| 任务列表/首页面板 | ❌ | ✅ Dashboard | ✅ |
| 任务持久化（重启仍可见） | ❌ | ✅ | ✅ |
| 会话间上下文隔离 | ⚠️ 换 session_id 可达 | ✅ 自动隔离 | ✅ 自动隔离 |

当前 OpenCopilot 的 `session_id` 机制已经为隔离打下了**数据层**基础——不同的 session_id 在 SQLite 中完全隔离。瓶颈在**UI 层**：卡片只有一张，用户没有地方看到或切换历史对话。

## AA. 设计目标

```
当前：一张卡片 → 一次一个话题 → 换话题 = 丢上下文或污染上下文

目标：任务面板 → 多张任务卡 → 每张卡独立 session_id + 独立上下文
              → 切换卡片即切换对话
              → 关闭卡片 = 归档（数据保留）
              → Agent 重启后所有卡片仍可见
```

## AB. 任务面板 UI 设计

### AB1. 唤醒方式

```
双击右键 → 当前仍是悬浮卡片（快捷模式，向后兼容）
三击右键 → 从"单一工作台"升级为"任务面板"（多卡片视图）
```

### AB2. 面板布局

```
┌─────────────────────────────────────────────────┐
│  OpenCopilot 任务面板                    [+ 新建] │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ 🔧 Broker 修复 │  │ 🌐 技术翻译   │            │
│  │ 空指针异常     │  │ API 文档      │            │
│  │ 14:30 · 8 轮  │  │ 11:00 · 4 轮  │            │
│  │ #bug #broker  │  │ #翻译 #API    │            │
│  └──────────────┘  └──────────────┘            │
│                                                 │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ 📝 三层记忆   │  │ 📊 Q3 报告    │            │
│  │ 架构设计      │  │ PPT 生成      │            │
│  │ 16:00 · 12 轮 │  │ 昨天 · 6 轮   │            │
│  │ #架构 #记忆   │  │ #PPT #报告    │            │
│  └──────────────┘  └──────────────┘            │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │ 📋 已完成 · 归档                          │  │
│  │ · 5/28 代码审查  · 5/27 依赖升级         │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### AB3. 卡片信息

| 信息 | 来源 | 说明 |
|------|------|------|
| 标题 | AI 自动摘要 / 用户手动命名 | 首次对话后由 Hook 提炼，用户可编辑 |
| 状态行 | SQLite | 最近活跃时间 + 总消息轮数 |
| 标签 | AI 自动 / 用户手动 | 用于分类和快速检索 |
| 颜色条 | 自动根据标签 | 视觉区分不同任务 |

## AC. 生命周期管理

```
创建：点击 [+ 新建] → 生成 session_id → 打开独立卡片
活跃：点击任务卡 → 展开为完整对话界面 → 继续对话
闲置：关闭对话界面 → 卡片缩回任务面板 → 数据保留
归档：右键卡片 → 归档 → 移入「已完成」区
删除：右键卡片 → 删除 → 清除 SQLite 数据 + 卡片消失
```

## AD. 数据层：已有基础 + 少量扩展

### AD1. 复用现有 SQLite

```sql
-- 已有 sessions 表，追加少量字段
ALTER TABLE sessions ADD COLUMN title TEXT;        -- 任务标题
ALTER TABLE sessions ADD COLUMN tags TEXT;         -- JSON 数组 ["bug","broker"]
ALTER TABLE sessions ADD COLUMN status TEXT DEFAULT 'active';  -- active/archived
ALTER TABLE sessions ADD COLUMN created_at REAL;   -- 创建时间
```

### AD2. 任务列表 API

```python
# asu_custom_agent.py → AgentHTTPRequestHandler 新增 GET

def do_GET(self):
    if self.path == '/v1/agent/sessions':
        # 返回所有活跃任务卡片列表
        sessions = memory.get_all_sessions(status='active')
        self._send_json([{
            "session_id": s["session_id"],
            "title": s["title"] or _auto_title(s["session_id"]),
            "tags": json.loads(s.get("tags", "[]")),
            "message_count": s["message_count"],
            "last_active": s["updated_at"],
            "persona": s["persona"]
        } for s in sessions])
    
    elif self.path.startswith('/v1/agent/session/'):
        session_id = self.path.split('/')[-1]
        # 返回单个会话详情 + 历史消息
        ctx = memory.get_context(session_id)
        self._send_json(ctx)
```

## AE. 实现路线图

| Phase | 内容 | 依赖 | 优先级 |
|-------|------|------|--------|
| 任务 Phase 1 | sessions 表扩展（title/tags/status）+ 任务列表 API | 无 | P1 |
| 任务 Phase 2 | 任务面板 UI（多卡片网格 + 新建/归档/删除） | Phase 1 | P1 |
| 任务 Phase 3 | 卡片间切换 + 上下文隔离 + 自动标题（Hook 提炼） | Phase 2 + 记忆方案 | P2 |
| 任务 Phase 4 | 标签自动分类 + 任务搜索 + 归档管理 | Phase 3 | P2 |

---

# 附录七：竞品上下文组装与 LLM 交互深度解析

> OpenCopilot 当前的 Prompt 只有 2 层 flat 结构（context_prefix + persona）。要理解差距，需逐层拆解 OpenClaw、Hermes Agent、WorkBuddy 三家的上下文组装管道。

## AA. OpenClaw：Gateway 七阶段 Agentic Loop

OpenClaw 的核心是一个**单进程 Gateway**（`ws://127.0.0.1:18789`），所有消息经此流转。

### AA1. 端到端生命周期

```
Channel Adapter（标准化输入: WhatsApp/Telegram/Discord/iMessage/CLI）
  → Gateway（路由 + 鉴权 + Session 管理）
  → Lane Queue（同一 Session 消息串行化, 防止并发冲突）
  → Prompt Assembly（一次性快照，8 层注入）
  → Agentic Loop（Plan→Execute→Observe→Adjust, 最多 25 次 tool call）
  → Memory Flush（自动提炼 → memory/YYYY-MM-DD.md）
  → Response（通过原渠道返回）
```

### AA2. Prompt Assembly 8 层注入

```
Layer 1: SOUL.md      — Agent 身份 + 行为规则
Layer 2: USER.md      — 用户画像（时区、偏好、GitHub 等）
Layer 3: IDENTITY.md  — Agent 名称
Layer 4: MEMORY.md    — 长期记忆（含自动提炼的事实）
Layer 5: Skills Index — 轻量列表（仅名称+描述，非全文）
Layer 6: AGENTS.md    — 项目级行为规则
Layer 7: Session Messages — 最近 N 轮对话历史
Layer 8: Current Message  — 当前输入 + 附件
```

Prompt 是**一次性构建的快照**，tool call 循环中不重建 System Prompt——tool result 直接追加到 Messages 末尾。

### AA3. Agentic Loop

```
LLM 推理
  → finish_reason = "stop" → 回复文本 → 结束
  → finish_reason = "tool_calls" → Gateway 执行 tool → 结果追加到 Messages → LLM 再推理
  → 循环上限 ~25 steps
```

### AA4. Memory Flush（Post-Turn 自动提炼）

Tool 循环结束后 → Gateway 运行一个**静默 LLM turn**，命令 Agent "总结本轮关键信息写入 memory/YYYY-MM-DD.md"，在响应返回用户前完成。

### AA5. Session 隔离

Lane Queue 保证同一 Session 消息串行执行。不同 Session 有独立的 Workspace 目录和 skills 子集，Session 状态通过 SessionDB（SQLite）持久化。

---

## BB. Hermes Agent：三层缓存 Prompt 架构

Hermes 是三者中 Prompt 设计最透明的一个，官方文档完整开源。核心文件：`agent/prompt_builder.py`（1456 行）+ `agent/system_prompt.py`（333 行）。

### BB1. 最重要的设计：stable / context / volatile

```
system_prompt = stable + "\n\n" + context + "\n\n" + volatile
```

| 层 | 内容 | 会话内不变？ | LLM Prefix Cache 可命中？ |
|----|------|:---:|:---:|
| **stable** | Agent 身份 + 工具指令 + Skills 索引 + 平台提示 | ✅ | ✅ ~60% 命中 |
| **context** | 用户系统消息 + 项目上下文文件 | 大部分 | ✅ |
| **volatile** | MEMORY 快照 + USER 快照 + 时间戳 + Session ID | ⚠️ | ❌ |

**效果**：stable 层在对话中只构建一次 → `self._cached_system_prompt`。后续每轮对话只支付 volatile + Messages 的 Token。

### BB2. 完整 10 层组装（基于官方文档 + API 抓包）

```
Layer 1:  SOUL.md              — Agent 身份
Layer 2:  Tool-Use Enforcement — 按模型族过滤（GPT 收到更严格指令）
Layer 3:  Honcho Static Block  — 用户模型静态表示（可选）
Layer 4:  System Message       — 用户自定义 override
Layer 5:  Frozen MEMORY.md     — 会话开始时冻结快照
Layer 6:  Frozen USER.md       — 用户画像冻结快照
Layer 7:  Skills Index         — 渐进式 ~3K tokens
           <available_skills>
            code-review: Structured code review workflow
            arxiv: Search and summarize arXiv papers
           </available_skills>
           完整 SKILL.md 通过 tool_call skill_view(name) 按需加载
Layer 8:  Context Files        — .hermes.md→AGENTS.md→CLAUDE.md→.cursorrules (first match)
Layer 9:  Timestamp + Session ID
Layer 10: Platform Hint        — CLI/Telegram/Discord 各有不同提示
```

### BB3. 记忆冻结模式

```
会话开始时: 读取 MEMORY.md → 做快照 → 构建 System Prompt（含快照）→ 缓存
对话进行中: Agent 通过 memory tool 写入 MEMORY.md → 文件已更新 → 但会话仍用旧快照
Compaction 触发: 清除缓存 → 重新读 MEMORY.md → 新快照包含刚才写的内容
```

**设计意图**：防止 Agent 中途写记忆导致 System Prompt 变化破坏 Prefix Cache。

### BB4. 上下文注入安全

自 v0.7.0（2026-05-26）起，所有注入内容通过 `tools/threat_patterns.py`（252 行）扫描 prompt injection：

```
findings = scan_for_threats(content, scope="context")
if findings:
    content = "[BLOCKED: potential prompt injection detected]"
```

三类 scope（`all`/`context`/`content`）共享统一威胁库。

---

## CC. WorkBuddy：并行多 Agent + MCP 引擎

WorkBuddy 是闭源产品，公开信息相对有限，但可勾勒其上下文模型。

### CC1. 任务分解架构

```
用户: "分析销售数据，做 PPT"
  → 任务分解引擎 → 3 个子任务
  → Agent 1: 读 Excel、清洗数据、生成图表
  → Agent 2: 分析趋势、写结论
  → Agent 3: 组装 PPT、排版、导出
  → 结果聚合 → 交付
```

### CC2. 上下文模型

```
Prompt = 
  System: 激活的 Skill 指令 + MCP 工具定义
  Context: 授权文件夹清单（Agent 可读写范围）
  User: 用户指令
  （无 SOUL.md / MEMORY.md 身份层——身份由腾讯云账户定义）
```

### CC3. 系统交互

```
桌面文件: 授权目录下的直接读写
微信/企微: WebSocket + HTTP Webhook
扩展: MCP 协议 + Skills 市场
多 Agent: 引擎自动拆解，并行执行，统一看板
```

---

## DD. OpenCopilot vs 三家：上下文组装全景对比

| 维度 | OpenCopilot（当前） | OpenClaw | Hermes Agent | WorkBuddy |
|------|:---:|:---:|:---:|:---:|
| **Prompt 层数** | 2 层 | 8 层 | 10 层 | ~3 层 |
| **身份定义** | Persona .md | SOUL.md + IDENTITY.md | SOUL.md | 云账户 |
| **记忆注入** | ❌ | ✅ MEMORY.md 快照 | ✅ Frozen snapshot | ❌ |
| **用户画像** | ❌ | ✅ USER.md | ✅ USER.md + Honcho | ❌ |
| **技能加载** | 全量名称注入 | 渐进式（列表→按需全文） | 渐进式（index ~3K→tool_call 按需） | Skills 市场 + MCP |
| **Cache 分层** | ❌ 无 | ⚠️ 部分 | ✅ stable/context/volatile | ❌ |
| **Prefix Cache 命中** | 0%（每轮全量重建） | 部分 | ~60%（stable 层） | 未知 |
| **Tool Loop** | ❌ | ✅ 25 step 上限 | ✅ 含 15-step 自检 | ✅ 并行 Agent |
| **Session 隔离** | SQLite session_id | Lane Queue + Workspace | SessionDB | 账户级 |
| **注入安全扫描** | ❌ | ⚠️ | ✅ threat_patterns.py | ✅ 沙盒审查 |
| **Post-Turn 处理** | ❌ | ✅ Memory Flush | ✅ memory_manager | ✅ 自动保存 |

## EE. 对 OpenCopilot 的关键启示

### 1. 从 2 层 flat 到分层架构

当前：
```
enriched_system = context_prefix + persona_prompt
```

应演进为：
```
system_prompt = 
  stable（Cache 友好）:
    IDENTITY.md → Persona .md → Skills Index → Tool Guidance
  context:
    MEMORY.md（L3 冷冻快照）→ Context Files
  volatile:
    L2 今日+昨天日志 → Timestamp → Session ID
```

### 2. 记忆冻结 = 省钱

Hermes 的 frozen snapshot：会话中 Agent 写的记忆不立刻注入当前 Prompt，等 Compaction 后才刷新。这让 stable 层真正稳定。按每天 20 轮对话算，~60% stable 层每年可节省约 1.3M tokens。

### 3. 渐进式 Skill 加载

当前 7 个 Skill 全量注入问题不大，但应现在就设计 `skill_view(name)` tool_call 机制，让未来 50+ Skill 时无缝切换。

### 4. 上下文注入安全

三个竞品都有注入内容扫描层——因为 Agent 会读取网页、文档、邮件，这些东西可能含 prompt injection。OpenCopilot 的 Broker 在读浏览器 DOM 时应有同样的扫描。

### 5. Prompt 预构建 + Cache

不在每次 `POST /v1/agent/chat` 时重建整个 System Prompt。会话级缓存 stable 部分，只拼接动态的 volatile 层 + 新消息。

### 6. 落地执行路线

以上启示不能一次性全部实现。推荐分三步走，最小化对现有代码的冲击：

#### Step 1：stable/volatile 两层切割 + 注入扫描（本周可做）

```python
# asu_custom_agent.py → 新增缓存变量 + invalidate 方法

class AgentHTTPRequestHandler(BaseHTTPRequestHandler):

    _cached_stable_prompt: str = None

    def _get_or_build_stable_prompt(self):
        """构建 stable 层 Prompt，会话间缓存，Persona 热更后失效"""
        if self._cached_stable_prompt is None:
            identity = load_identity()      # 新增: ~/.asu_copilot/IDENTITY.md
            skills_index = _build_skills_one_liners()  # 仅名称+一行描述
            persona = load_persona("default")
            self._cached_stable_prompt = (
                f"{identity}\n\n{persona}\n\n## 可用能力\n{skills_index}"
            )
        return self._cached_stable_prompt

    def invalidate_stable_cache(self):
        """Persona 热更新后调用"""
        self._cached_stable_prompt = None

    def _build_volatile_prompt(self, envelope, session_id):
        """每次 POST 重建 volatile 层"""
        parts = [build_context_prefix(envelope)]
        memory_ctx = load_memory_frozen_snapshot(session_id)  # 冻结快照
        if memory_ctx:
            parts.append(memory_ctx)
        parts.append(f"当前时间: {datetime.now().isoformat()}")
        return "\n\n".join(parts)

    def do_POST(self):
        if self.path == '/v1/agent/chat':
            ...
            stable = handler._get_or_build_stable_prompt()
            volatile = handler._build_volatile_prompt(envelope, session_id)
            enriched_system = stable + "\n\n---\n\n" + volatile
            ...
```

**注入内容轻量扫描（~50 行，加在 build_context_prefix 附近）：**

```python
INJECTION_PATTERNS = [
    r"忽略.*(?:所有|上面|之前).*指令",
    r"ignore.*(?:all|above|previous).*instructions?",
    r"forget.*(?:everything|all)",
    r"你现在.*?是.*?(?:一个|新的)",
    r"you are now",
    r"\[SYSTEM\]",
    r"<\|im_start\|>",
]

def scan_injection_risk(content: str, source: str) -> str:
    """对注入源头做轻量扫描，不阻止只截断"""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            logger.warning(f"Injection risk: {source} matched {pattern}")
            return content[:500] + "\n\n[⚠️ 内容已被截断]"
    return content
```

调用位置：`build_context_prefix()` 对 browser/drag 来源调用；IDE 来源不扫描。

#### Step 2：记忆 frozen snapshot + Skill one-liner（与记忆方案同步）

```python
# 记忆冻结逻辑
_memory_snapshots: dict = {}   # session_id → 冻结的内存上下文
_frozen_at: dict = {}          # session_id → 冻结时间戳

def load_memory_frozen_snapshot(session_id: str) -> str:
    """加载记忆快照，30 分钟内不刷新"""
    now = time.time()
    if session_id in _memory_snapshots and \
       now - _frozen_at.get(session_id, 0) < 1800:
        return _memory_snapshots[session_id]

    ctx = load_memory_context()  # 实际读取 L2+L3 文件
    _memory_snapshots[session_id] = ctx
    _frozen_at[session_id] = now
    return ctx

def invalidate_memory_snapshot(session_id: str):
    """用户说'刷新记忆'或切换 session 时调用"""
    _memory_snapshots.pop(session_id, None)
    _frozen_at.pop(session_id, None)
```

```python
# Skill one-liner（SkillRegistry 新增方法）
class SkillRegistry:
    def get_one_liner(self, skill_name: str) -> str:
        """返回 Skill 的一行描述，用于渐进式注入"""
        skill = self._skills.get(skill_name)
        return f"- {skill_name}: {skill.metadata.description[:80]}"
```

#### Step 3：工具循环端点（记忆方案落地后）

不改现有 `/v1/agent/chat`——新增 `/v1/agent/task`，只给 Cron/事件驱动用：

```python
# asu_custom_agent.py → do_POST 新增分支

elif self.path == '/v1/agent/task':
    """工具循环端点：Cron/事件触发时使用"""
    req = json.loads(...)
    max_steps = 10
    messages = [{"role": "system", "content": system_prompt},
                 {"role": "user", "content": req["text"]}]
    
    self.send_response(200)
    self.send_header('Content-Type', 'text/event-stream')
    ...
    
    while max_steps > 0:
        response = llm.chat_with_tools(messages, TOOLS)
        if response.has_tool_call:
            result = execute_tool(response.tool_call)
            messages.append({"role": "tool", "content": result})
            self.wfile.write(f"data: {json.dumps({'tool_result': result[:200]})}\n\n".encode())
            max_steps -= 1
            continue
        else:
            # 最终文本回复
            self.wfile.write(f"data: {json.dumps({'chunk': response.text})}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            break
```

#### 总体推进顺序

```
本周:
  ├── stable/volatile 两层切割 + _cached_stable_prompt
  ├── 注入内容轻量扫描
  └── IDENTITY.md 新文件 + load_identity()

与记忆方案同步:
  ├── frozen snapshot 记忆注入
  └── SkillRegistry.get_one_liner()

记忆方案落地后:
  ├── /v1/agent/task 工具循环端点
  └── 渐进式 Skill 加载切换（从全量→skill_view tool_call）
```

---

# 结语：改造完成后，OpenCopilot 是谁？

> 当所有改造完成后——三层记忆到位、Prompt 分层缓存就绪、搜索+自主执行+多任务管理全部落地——OpenCopilot 和竞品之间还剩什么差距？更重要的是，我们到底在做一款什么样的产品？

## 一、改造完成后的能力矩阵

| 能力维度 | OpenCopilot（改造后） | OpenClaw | Hermes Agent | WorkBuddy |
|----------|:---:|:---:|:---:|:---:|
| 三层记忆体系 | ✅ | ✅ | ✅ | ✅ |
| 分层 Prompt（stable/volatile） | ✅ | ⚠️ 部分 | ✅ | ❌ |
| 渐进式 Skill 加载 | ✅ | ✅ | ✅ | ✅ |
| 对话历史搜索（FTS5） | ✅ | ✅ | ✅ | ✅ |
| 联网搜索（SearXNG） | ✅ | ✅ | ✅ | ✅ |
| Cron 定时调度 | ✅ | ✅ | ✅ | ✅ |
| tool-calling loop | ✅ | ✅ | ✅ | ✅ |
| 多任务会话管理 | ✅ | ✅ | ✅ | ✅ |
| **事件驱动触发（独有）** | **✅** | ❌ | ❌ | ❌ |
| **知识图谱（独有）** | **✅** | ❌ | ❌ | ❌ |
| **系统级右键悬浮交互（独有）** | **✅** | ❌ | ❌ | ❌ |
| **系统级探针 DOM/选区/截图（独有）** | **✅** | ❌ | ❌ | ❌ |
| **全局应用切换感知（独有）** | **✅** | ❌ | ❌ | ❌ |
| 多消息渠道（Telegram等） | ❌ 不做 | ✅ | ✅ | ✅ |
| Skill 自动生成（学习循环） | ❌ | ❌ | ✅ | ❌ |
| 语音交互 | ❌ P2 | ⚠️ | ✅ | ✅ |
| 多 Agent 并行 | ❌ P2 | ✅ | ✅ | ✅ |

**结论**：改造完成后，OpenCopilot 在 Agent 基础设施层追平三家竞品，同时保有 **5 项结构性独有能力**。差距集中在 P2 层（多渠道、语音、多 Agent、自动 Skill）——这些都是有意识推迟的。

## 二、四款产品的本质差异：不在同一个赛道

```
                       高摩擦（需离开当前工作上下文）
                           ↑
        OpenClaw ─── ●    │    ● ─── WorkBuddy
        "手机上发消息       │    "独立桌面工作台，
         让 Agent 干活"     │     像 Photoshop 一样操作 AI"
                           │
        ───────────────────────────────────→
        异步/离线           │          同步/即时
                           │
        Hermes Agent ── ●  │    ● ─── OpenCopilot
        "终端里持续自进化   │    "你在哪 AI 在哪，
         的后台智能体"      │     右键即出，零切换"
                           ↓
                       零摩擦（不离开当前应用）
```

| 产品 | 核心交互模型 | 一句话描述 |
|------|------------|-----------|
| **OpenClaw** | 消息优先（Message-First） | 在 WhatsApp 里给 Agent 发消息，它替你干活 |
| **Hermes Agent** | 终端优先（Terminal-First） | 后台持续自进化的 CLI 智能体，越用越强 |
| **WorkBuddy** | 工作台优先（Workbench-First） | 独立桌面工作台，企业微信/QQ 原生打通 |
| **OpenCopilot** | **上下文优先（Context-First）** | 你在哪工作，AI 就出现在哪；它看你所看，知你所用 |

## 三、OpenCopilot 的设计哲学：我们选择做什么，不做什么

### 3.1 核心假设：最好的 AI 交互是"不交互"

OpenClaw 需要你打开 WhatsApp 打字。Hermes 需要你切到终端。WorkBuddy 需要你切到它的桌面客户端。

OpenCopilot 的根假设：**用户大部分的认知摩擦不在"AI 不够聪明"，而在"叫出 AI 太麻烦"**。

- 在 VS Code 里看一段报错 → 选中 → 双击右键 → AI 已经在分析，你没离开编辑器
- 浏览器读技术文章 → 选中关键段落 → 双击右键 → AI 自动注入"来自 Safari 网页"的上下文
- Broker 检测到 Chrome→IDE 切换 → 事件触发静默记录 → 下次唤醒时 AI 已知道刚才在查什么

这是三家竞品都做不到的——因为它们不知道你现在在用什么应用。

### 3.2 取舍原则：每项"不做"背后都有理由

| 不做的东西 | 理由 |
|-----------|------|
| **多消息渠道**（Telegram/WhatsApp） | 场景不匹配。OpenCopilot 的核心场景是"桌面工作时即时辅助"，不是"在外面远程操控电脑"。后者是 OpenClaw 的领地，不在同维度竞争 |
| **Skill 自动生成**（Hermes 学习循环） | 质量风险 > 收益。7 个精心维护的高质量 Skill 比 50 个自动生成的低质量 Skill 更有价值。且自动生成依赖深度 Prompt 工程改造，ROI 不对等 |
| **语音交互** | 桌面办公场景中语音边际收益低。打字比说话更精准、更私密、更不会打扰同事 |
| **多 Agent 并行** | 单用户场景暂不需要。等任务面板成熟、用户真正需要"同时跑测试 + 翻译文档"时再考虑 |
| **RL 训练管线** | 学术研究方向，不是个人桌面工具该做的事。Nous Research 做 RL 是因为他们有训练数据工厂的定位 |

### 3.3 不可复制性：四层物理架构 + Broker 系统级权限

OpenCopilot 有一个竞品极难复制的架构优势——**Broker 层**：

```
交互层: PyQt6 悬浮卡片（全局 Overlay，不抢焦点，不离开当前应用）
  ↕
Agent 层: asu_custom_agent.py（本地 HTTP + SSE，LLM 推理）
  ↕
Broker 层: asu_broker（macOS 特权进程，辅助功能权限 + 屏幕录制权限）
  ↕
系统层: macOS Accessibility API + NSWorkspace 通知 + AppleScript
```

OpenClaw/Hermes 没有 Broker 层——只能通过标准 API 和文件系统交互，无法做到：
- 无感读取浏览器当前标签页 DOM
- 静默获取系统高亮选区（不需要 Cmd+C）
- 截取前台任意应用窗口进行 OCR
- 监听系统级应用切换事件

WorkBuddy 有桌面权限，但受限于**腾讯云体系**——数据在云端、模型路由在云端、身份在云端。

**OpenCopilot 是唯一同时具备"系统级感知"和"完全本地化"的产品。**

### 3.4 知识图谱：被低估的差异化武器

264 个实体 + 166 个关系看起来只是一个功能点，但它的真正价值在于**让 Agent 理解项目结构**：

```
用户: "Broker 的 WebSocket 是怎么连到 UI 的？"

OpenCopilot（有知识图谱）:
  → 查询: Broker ←communicates_with→ UI
  → 查询: events_probe.py ←depends_on→ server.py
  → 回答: "Broker 的 events_probe.py 通过 server.py 的 WebSocket 端点
           /api/v1/events 向 UI 层 BrokerEventsWorker 推送 app_activated 事件"

OpenClaw/Hermes（无知识图谱）:
  → 最多搜索文档文件名 → 可能找到相关代码 → 没有结构化的实体关系
```

竞品要补这个能力，需要从零构建项目知识图谱——这和一个 tool 的工程量不在同一级别。

## 四、最终定位

```
OpenClaw    = 自动驾驶出租车（手机上叫，替你跑腿，你不用管它怎么开的）
Hermes      = 自动驾驶实验室（持续进化，自我改进，适合技术深度玩家）
WorkBuddy   = 自动驾驶班车（企业级，腾讯云轨道上跑，稳定但受限）
OpenCopilot = 自动驾驶摩托（你在骑，它辅助；你看路，它看周围；你不离开驾驶位）
```

**OpenCopilot 不试图取代任何一个竞品。它占据的是一个还没有人做好的位置——不离开当前窗口、不改变工作节奏、不需要打开另一个 App。**

> 一款伴生在你工作流中的 AI：你在 VS Code 里写代码，它知道。你在 Chrome 里查文档，它知道。你从 Chrome 切回 VS Code，它知道这次切换意味着什么。你什么都不用做——它看你所看，记你所记，然后在你双击右键的那一刻，已经比你更清楚上下文所在。

**记忆是这个定位的基石，不是目标本身。** 三层记忆 + Broker 伴生数据 + Context Weaver + 校准台阶 + Rule 孵化——这五个模块共同构成了一条完整的"伴生数据 → 结构化上下文 → 零摩擦智能"链路。记忆是输入，上下文是输出，双击右键是交付时刻。

## 五、特色强化路线图：从"有"到"不可替代"

> 5 项独有能力目前的状态相当于"发现了金矿但只挖了表层"——它们都存在，但各自独立运行，没有形成协同效应。强化不是加新功能，而是**把它们编织成一张上下文感知网**。

### 5.1 当前状态诊断：五个孤立的能力孤岛

| 独有能力 | 当前状态 | 问题 |
|----------|----------|------|
| **右键悬浮卡片** | ✅ 双击右键唤出，自动读取选区 | 卡片出现时带的是"通用 AI"而非"感知到当前场景的 AI" |
| **Broker 探针** | ✅ 能读 DOM、选区、截图 | 手动触发——用户必须主动点"读取浏览器"按钮 |
| **应用切换感知** | ✅ `app_activated` 事件收到，存入 `recent_apps` | 仅用于 print 日志 + 托盘图标变色，从未注入 Agent 上下文 |
| **知识图谱** | ✅ 264 实体 + 166 关系，27 个 API | Agent 对话时不知道有知识图谱——除非用户明确问"搜索实体" |
| **完全本地化** | ✅ 数据不出设备 | 用户无感知——没有在交互中体现"本地"的价值 |

**核心问题**：五个能力都是"被动的工具"，不是"主动编织上下文的网"。

### 5.2 协同强化：把五座孤岛连成大陆

```
强化后的上下文感知闭环：

Broker 探针                          应用切换感知
(读取 DOM/选区)                     (app_activated 事件)
      │                                    │
      ▼                                    ▼
┌─────────────────────────────────────────────────┐
│           上下文编织层 (Context Weaver)           │
│                                                  │
│  "用户在 Chrome 看了 OpenClaw 内存文档           │
│   15:30 切回 VS Code                             │
│   当前打开文件: events_probe.py                  │
│   知识图谱显示: events_probe ←depends_on→ server  │
│   剪贴板含: '空指针异常 at line 42'"             │
└─────────────────────────────────────────────────┘
      │
      ▼
  右键悬浮卡片出现时，System Prompt 不再是空白的 context_prefix
  而是: "用户刚从 Chrome（正在看 OpenClaw 内存设计文档）切回 VS Code
        （正在编辑 events_probe.py，该文件通过 server.py 的 WebSocket
        向 UI 推送事件）。剪贴板含报错信息。请据此提供精准帮助。"
```

### 5.3 五项具体强化措施

#### 强化 1：上下文编织层（Context Weaver）——最关键的缺失环节

当前 `build_context_prefix()` 只在用户**主动操作**时触发（拖拽文本、点击按钮），且只含单一来源（IDE 或 Browser 或 Drag）。

**改造**：新增一个后台 Context Weaver，在以下时刻**静默更新上下文快照**：

```python
# smart_copilot.py → SmartCopilot 类新增

class SmartCopilot:
    def __init__(self):
        ...
        self.context_snapshot = {}  # 全局上下文快照
        self.broker_events_worker.app_activated.connect(self._on_app_switched)
        
    def _on_app_switched(self, app_name, bundle_id):
        """每次应用切换时，静默更新上下文快照（不调 LLM，零 Token 消耗）"""
        snapshot = {
            "active_app": app_name,
            "bundle_id": bundle_id,
            "timestamp": time.time(),
            "previous_app": self.context_snapshot.get("active_app"),
            "switch_count": self.context_snapshot.get("switch_count", 0) + 1
        }
        
        # 如果是切到 IDE，追加 IDE 上下文
        if bundle_id in ["com.microsoft.VSCode", "com.trae.app"]:
            snapshot["ide_context"] = self._get_ide_context()
        
        # 如果是切到浏览器，追加浏览器 URL
        if bundle_id in ["com.google.Chrome", "com.apple.Safari"]:
            snapshot["browser_context"] = self._get_browser_url()
        
        # 追加知识图谱关联（如果文件匹配到已知实体）
        if snapshot.get("ide_context", {}).get("active_file"):
            file_name = snapshot["ide_context"]["active_file"]
            kg_entities = self._query_kg_for_file(file_name)
            if kg_entities:
                snapshot["knowledge_graph"] = kg_entities
            else:
                # 兜底：返回项目总体摘要
                snapshot["knowledge_graph"] = self._query_kg("components AND depends_on", limit=3)
        
        self.context_snapshot = snapshot
    
    def _query_kg_for_file(self, filename):
        """查知识图谱：这个文件关联了哪些实体"""
        # 返回实体名 + 关系 + 相关实体
        return {
            "entity": "events_probe",
            "type": "PROBE",
            "relations": [
                {"relation": "depends_on", "target": "server.py"},
                {"relation": "communicates_with", "target": "BrokerEventsWorker"}
            ]
        }
    
    def _query_kg(self, q, limit=3):
        """知识图谱轻量查询，不调 LLM"""
        # 触发时返回相关实体列表
        ...
```

**效果**：用户双击右键时，`context_snapshot` 已经有了完整的多源上下文——不需要等待任何网络请求，直接拼接 Prompt。

#### 强化 2：右键卡片从"通用 AI"变为"感知当前场景的 AI"

当前卡片唤出时，System Prompt 中只有来源标记（"来自 IDE"）。改造后：

```python
def _build_context_prefix_from_snapshot(self):
    """基于上下文的快照生成智能前缀"""
    snap = self.context_snapshot
    
    if not snap.get("active_app"):
        return ""  # 快照为空，回退到旧逻辑
    
    parts = []
    
    # 应用上下文
    parts.append(f"用户当前正在使用: {snap['active_app']}")
    if snap.get("previous_app") and snap["previous_app"] != snap["active_app"]:
        parts.append(f"（刚从 {snap['previous_app']} 切换过来）")
    
    # 知识图谱关联
    if snap.get("knowledge_graph"):
        kg = snap["knowledge_graph"]
        if isinstance(kg, dict):
            parts.append(f"\n项目知识: 当前文件 `{kg['entity']}` ({kg['type']})")
            rels = "; ".join(f"{r['relation']} → {r['target']}" for r in kg.get("relations", []))
            if rels:
                parts.append(f"关联: {rels}")
    
    # 如果刚切换，附加上一个应用的上下文
    if snap.get("previous_app") == "Google Chrome" and snap.get("switch_count", 0) < 3:
        parts.append("\n用户刚从浏览器切换过来，可能正在查阅资料后回到代码。")
        if snap.get("browser_context"):
            parts.append(f"浏览器最后活跃 URL: {snap['browser_context']}")
    
    return "\n".join(parts)
```

**效果**：相同的问题"这段代码为什么报错"，AI 在强化后会给出不同回答——因为它知道了你在看什么文件、刚从浏览器查了什么、这个文件在知识图谱里和哪些组件关联。

#### 强化 3：知识图谱从"27 个被动 API"变为"Agent 对话中的隐式知识层"

当前知识图谱需要用户主动调用 `/api/knowledge/query`。改造后：

```python
# 在 _build_volatile_prompt() 中，每次对话自动注入

def _inject_kg_context(self, user_text: str):
    """从用户问题中提取关键词，查知识图谱，注入到 Prompt"""
    keywords = extract_keywords(user_text)  # 简单分词 + 停用词过滤
    results = []
    for kw in keywords[:3]:  # 最多查 3 个关键词
        entities = kg.search_entities(kw)
        for e in entities[:2]:  # 每个关键词最多 2 个结果
            related = kg.get_related(e.name)
            results.append(f"- {e.name} ({e.type}): {e.description[:100]}")
            for r in related[:2]:
                results.append(f"  {r.relation} → {r.target}")
    
    if results:
        return "## 项目知识图谱（自动匹配）\n" + "\n".join(results[:10])
    return ""
```

注入到 volatile 层，作为隐式上下文。Agent 不需要被问"搜索实体"就能用到知识图谱。

#### 强化 4：Broker 探针从"手动触发"变为"事件驱动自动采集"

当前 Browser DOM 读取需要用户手动点击按钮。改造后：

```python
# smart_copilot.py → 新增自动采集逻辑

class SmartCopilot:
    def __init__(self):
        ...
        # 应用切换后延迟 3 秒自动采集（避免用户还在切换时发请求）
        self._pending_collection = None
    
    def _on_app_switched(self, app_name, bundle_id):
        ...
        # 如果是浏览器 → IDE 的切换模式，触发自动采集
        if self.context_snapshot.get("previous_app") in BROWSERS and \
           bundle_id in IDES:
            # 延迟 3 秒，让用户真正开始工作后再采集
            if self._pending_collection:
                self._pending_collection.cancel()
            self._pending_collection = QTimer.singleShot(3000, self._auto_collect)
    
    def _auto_collect(self):
        """自动采集上一个应用的上下文"""
        snap = self.context_snapshot
        if snap.get("previous_app") in BROWSERS:
            # 后台静默读浏览器 DOM（不阻塞 UI）
            self.browser_reader = BrowserReaderWorker(snap["previous_app"])
            self.browser_reader.finished.connect(self._on_browser_auto_read)
            self.browser_reader.start()
```

**效果**：用户从 Chrome 切到 VS Code 3 秒后，Broker 自动读取浏览器内容并存入快照。下次唤出卡片时，Agent 已经知道用户在浏览器看了什么。

#### 强化 5：本地化从"技术事实"变为"用户感知的信任标志"

当前"完全本地化"只是代码层面的实现，用户无感知。改造后：

```python
# 设置面板新增 "数据主权" 面板

class PrivacyDashboard:
    """
    在设置 → 隐私面板中展示：
    
    ┌───────────────────────────────────┐
    │  🔒 数据主权                        │
    │                                    │
    │  所有数据存储在本地                 │
    │  ✅ LLM 请求: 仅发送当前对话上下文  │
    │  ✅ 记忆文件: ~/.asu_copilot/memory/│
    │  ✅ 知识图谱: 本地 SQLite           │
    │  ✅ 零遥测，零云端存储              │
    │                                    │
    │  今日统计:                          │
    │  · 发送到 LLM 的请求: 23 次         │
    │  · 本地存储的对话数: 142 条         │
    │  · 记忆提炼次数: 3 次              │
    │  · 从未离开设备的数据: 100%        │
    └───────────────────────────────────┘
    """
```

### 5.4 强化后的差异对比

| 维度 | 强化前 | 强化后 |
|------|--------|--------|
| **上下文来源** | 单一（当前激活的来源标记） | 多源融合（应用切换历史 + 知识图谱 + 浏览器内容 + IDE 文件关系） |
| **上下文时效** | 用户操作时才构建 | 应用切换时静默更新，唤出时零延迟 |
| **知识图谱** | 27 个被动 API | Agent 每次对话自动注入相关实体 |
| **Broker 探针** | 手动点击按钮 | 浏览器→IDE 切换时自动采集 |
| **本地化** | 无感知 | 隐私面板 + 统计数据可视化 |
| **整体体验** | "我告诉 AI 上下文" | "AI 自己知道上下文" |

### 5.5 强化优先级

```
P0（立即可做，不改架构）:
  ├── 强化 3: 知识图谱隐式注入到 volatile 层
  └── 强化 5: 隐私面板

P1（需要上下文编织层，1-2 周）:
  ├── 强化 1: Context Weaver（应用切换 → 自动更新快照）
  └── 强化 2: 右键卡片感知化（基于快照生成智能前缀）

P2（需要事件驱动 + 自动采集，2-3 周）:
  └── 强化 4: Broker 自动采集（浏览器→IDE 切换触发）
```

---

# 附录八：用户意图捕捉能力设计

> Context Weaver 落地后最直接的应用——不是等用户说"帮我翻译"，而是在用户还没开口时就猜到他要什么。OpenCopilot 拥有竞品无法触及的意图信号源：应用切换、剪贴板内容、文件类型、浏览器 URL、时间模式。

## LA. 意图捕捉的分层模型

### LA1. 四层意图深度

```
Level 0: 显式意图（当前已实现）
  └── 用户说出/输入具体指令："帮我翻译这段代码"
  └── 用户选择 action_type: translate / code / polish
  └── 准确率 100%，但摩擦最大

Level 1: 内容推断意图（增强 IntentRouter 即可）
  └── 选中文本包含 import/def/class → coding intent
  └── 选中文本含大量英文且无代码特征 → translate intent
  └── 选中文本含语法错误/口语化 → polish intent
  └── 准确率 ~85%，零额外摩擦

Level 2: 上下文推断意图（Context Weaver 驱动）
  └── 当前在 VS Code + 文件 .py → coding mode
  └── 当前在 Chrome + URL 含 arxiv.org → research mode
  └── 当前在 Terminal + 剪贴板含 "error" → debugging mode
  └── 准确率 ~70%，零摩擦

Level 3: 行为模式推断意图（事件序列分析）
  └── Chrome→VS Code 切换（2分钟内）+ 剪贴板含报错 → "查资料→修bug" 模式
  └── Figma→VS Code→Terminal 序列 → "前端开发启动" 模式
  └── 每天 9:00 VS Code + 17:00 Terminal → "早开发晚部署" 节奏
  └── 准确率 ~55%，但越用越准（个人化学习）
```

### LA2. 四层之间的协作关系

```
Level 3（行为模式）
    │ 提供先验概率："你有 70% 的概率要做代码相关的事"
    ▼
Level 2（上下文推断）
    │ 缩小范围："当前文件是 events_probe.py，在修 Broker"
    ▼
Level 1（内容推断）
    │ 确认意图："选中文本确实含 traceback + null pointer"
    ▼
Level 0（显式确认）
    │ 用户双击右键 → 卡片模式已预选 code，Agent 已注入项目上下文
    │ 用户不需要选择 action_type，不需要解释背景，直接看结果
```

核心逻辑：Level 3→2→1 的逐层收敛让 Level 0 的用户操作降到最低。理想状态下用户只需"选中 + 双击右键"两个动作。

## LB. Level 1：内容推断——增强 IntentRouter

当前 IntentRouter 只做关键词→Skill 映射。加入内容特征检测：

```python
# skill_architecture/router.py → IntentRouter 新增

CONTENT_SIGNATURES = {
    "code": {
        "patterns": [
            r'\b(def|class|import|from|return|async|await)\b',
            r'\{[^}]*\}',  # JSON/JS 对象
            r'<[^>]+>',    # HTML/XML
            r'^\s*(#|//|/\*)',  # 注释
        ],
        "min_lines": 3,
        "weight": 0.9
    },
    "translate": {
        "patterns": [],
        "lang_detect": True,  # 非母语比例 > 60%
        "no_code": True,      # 不含代码特征
        "weight": 0.7
    },
    "polish": {
        "patterns": [
            r'\b(语法错误|语病|不通顺|啰嗦)\b',
        ],
        "native_lang": True,  # 母语文本
        "long_text": True,    # > 100 字符
        "weight": 0.6
    },
    "debug": {
        "patterns": [
            r'\b(error|exception|traceback|报错|异常)\b',
            r'File ".*", line \d+',
            r'^\s*at\s+\S+\(.*:\d+\)',  # JS stack trace
        ],
        "weight": 0.95  # 高置信度——报错信息非常明确
    },
    "research": {
        "patterns": [],
        "url_patterns": [r'arxiv\.org', r'github\.com', r'docs\.', r'paper'],
        "weight": 0.5  # 低置信度——需要更多上下文
    }
}

def detect_intent_from_content(self, text: str, context_snapshot: dict = None) -> dict:
    """
    从文本内容 + 系统上下文综合推断用户意图。
    返回: {"intent": "code", "confidence": 0.85, "reason": "检测到 Python 代码特征"}
    """
    scores = {}
    reasons = {}
    
    for intent, sig in CONTENT_SIGNATURES.items():
        score = 0.0
        reason_parts = []
        
        # 正则匹配
        for pattern in sig.get("patterns", []):
            matches = re.findall(pattern, text, re.MULTILINE)
            if matches:
                score += 0.3 * min(len(matches), 3) / 3
                reason_parts.append(f"匹配 {pattern[:30]}")
        
        # 语言检测
        if sig.get("lang_detect"):
            non_native_ratio = _detect_non_native_ratio(text)
            if non_native_ratio > 0.6:
                score += 0.4
                reason_parts.append(f"非母语比例 {non_native_ratio:.0%}")
        
        # 行数检查
        if sig.get("min_lines"):
            lines = text.count('\n') + 1
            if lines >= sig["min_lines"]:
                score += 0.2
        
        # 长度检查
        if sig.get("long_text") and len(text) > 100:
            score += 0.2
        
        scores[intent] = min(score * sig["weight"], 1.0)
        reasons[intent] = "; ".join(reason_parts)
    
    # 取最高分
    best = max(scores, key=scores.get)
    return {
        "intent": best,
        "confidence": scores[best],
        "reason": reasons.get(best, "无明确特征"),
        "all_scores": scores
    }
```

**注入点**：卡片唤出时，如果用户没有手动选 `action_type`，用内容推断结果自动预选。

## LC. Level 2：上下文推断——Context Weaver 的意图层

这在 §五 Context Weaver 中已经设计了基础设施。这里是它的意图输出：

```python
# smart_copilot.py → Context Weaver 新增 intent 字段

def _on_app_switched(self, app_name, bundle_id):
    ...
    # 追加意图推断
    snapshot["inferred_intent"] = self._infer_intent_from_context(snapshot)
    
def _infer_intent_from_context(self, snapshot: dict) -> dict:
    """从系统上下文推断用户意图（不调 LLM，零 Token 消耗）"""
    signals = []
    
    app = snapshot.get("active_app", "")
    bundle = snapshot.get("bundle_id", "")
    prev_app = snapshot.get("previous_app", "")
    
    # 信号 1: 当前应用
    if bundle in IDE_BUNDLES:
        signals.append({"intent": "code", "weight": 0.6, "reason": f"活跃于 {app}"})
    elif bundle in BROWSER_BUNDLES:
        signals.append({"intent": "research", "weight": 0.5, "reason": f"活跃于 {app}"})
    elif bundle in ["com.apple.Terminal", "com.googlecode.iterm2"]:
        signals.append({"intent": "devops", "weight": 0.5, "reason": f"活跃于 {app}"})
    
    # 信号 2: 切换模式
    if prev_app in BROWSER_NAMES and bundle in IDE_BUNDLES:
        signals.append({"intent": "debug", "weight": 0.7, 
                        "reason": f"浏览器→IDE 切换模式"})
    if prev_app in ["Figma", "Sketch"] and bundle in IDE_BUNDLES:
        signals.append({"intent": "frontend", "weight": 0.65,
                        "reason": "设计→开发 切换模式"})
    
    # 信号 3: 时间模式
    hour = datetime.now().hour
    if 6 <= hour < 10 and bundle in IDE_BUNDLES:
        signals.append({"intent": "code_review", "weight": 0.3,
                        "reason": "早间首次打开 IDE"})
    if 16 <= hour < 19 and bundle in ["com.apple.Terminal", "com.googlecode.iterm2"]:
        signals.append({"intent": "deploy", "weight": 0.3,
                        "reason": "傍晚终端活跃"})
    
    # 聚合
    if not signals:
        return {"intent": "chat", "confidence": 0.3}
    
    best = max(signals, key=lambda s: s["weight"])
    return {
        "intent": best["intent"],
        "confidence": best["weight"],
        "supporting_signals": len(signals),
        "all_signals": signals
    }
```

**效果**：用户从 Chrome 切到 VS Code 时，卡片已经知道自己应该进入 "debug" 模式而不是 "translate" 模式。

## LD. Level 3：行为模式——随时间学习的个性化意图

Level 3 的核心思路不是规则引擎，而是**记录用户的行为序列，然后做简单的模式匹配**：

```python
# smart_copilot.py → PatternLearner

class PatternLearner:
    """
    记录用户的 (切换前应用, 切换后应用, 时间段, 是否唤出卡片, 卡片用什么 action_type)
    当积累了足够的样本（如 5+ 次相同模式），下次再出现时直接预判。
    
    不调任何 LLM，纯统计。
    """
    
    def __init__(self):
        self.patterns = defaultdict(lambda: defaultdict(int))  # pattern → action_type → count
        self._load()
    
    def record(self, context_snapshot: dict, action_type: str):
        """记录一次行为模式"""
        key = self._make_key(context_snapshot)
        self.patterns[key][action_type] += 1
        self._save()
    
    def predict(self, context_snapshot: dict) -> Optional[str]:
        """预测用户这次可能想做什么"""
        key = self._make_key(context_snapshot)
        actions = self.patterns.get(key, {})
        if not actions:
            return None
        
        # 至少 3 次相同模式 + 该 action 占 60%+ 才触发预测
        total = sum(actions.values())
        best_action, best_count = max(actions.items(), key=lambda x: x[1])
        if total >= 3 and best_count / total >= 0.6:
            return best_action
        return None
    
    def _make_key(self, snapshot: dict) -> str:
        """把上下文压缩成可匹配的 key"""
        prev = snapshot.get("previous_app", "unknown")
        curr = snapshot.get("active_app", "unknown")
        hour = datetime.now().hour
        time_slot = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
        return f"{prev}→{curr}@{time_slot}"
```

**一个落地的例子**：

```
第 1 天: Chrome→VS Code@morning → 用户唤出卡片 → action_type=code → 记录
第 2 天: Chrome→VS Code@morning → 用户唤出卡片 → action_type=code → 记录
第 3 天: Chrome→VS Code@morning → 用户唤出卡片 → action_type=debug → 记录
第 4 天: Chrome→VS Code@morning → PatternLearner 检测到 3 次匹配，code 占 66%
       → 用户双击右键时，卡片自动预选 code 模式
       → 用户不需要手动选，直接看结果
```

**核心价值**：不需要用户任何操作，系统越用越"懂"用户。

## LE. 六个具体的应用落地场景

### 场景 1：零选择唤醒

```
当前流程: 选中报错 → 双击右键 → 看到卡片 → 手动点"代码解析" → 等结果
优化流程: 选中报错 → 双击右键 → 卡片自动以 code/debug 模式呈现 → 结果已在加载
          （内容推断置信度 > 85% 时完全跳过 action_type 选择）
```

### 场景 2：主动意图提示（不唤出卡片）

```
用户: Chrome→VS Code 切换, 剪贴板含 traceback
Agent: 桌面通知弹出 "🔍 检测到报错信息，需要帮你分析吗？[分析] [忽略]"
      用户点 [分析] → 卡片自动出现，已加载上下文和报错
      用户点 [忽略] → PatternLearner 记录"此时不要"
```

这个场景的价值在于：**用户甚至不需要双击右键**——Agent 主动感知到"你可能需要帮助"。

### 场景 3：上下文预加载

```
用户: 在 Chrome 看了一篇 OpenClaw 架构文档 → 切回 VS Code
Agent: 静默采集浏览器内容 → 存入 context_snapshot
      用户 5 分钟后双击右键 → 卡片出现时 System Prompt 已包含:
      "用户刚从 Chrome（阅读 OpenClaw 架构文档）切回 IDE，
       可能正在参考该文档进行实现。"
      用户问"这个 Gateway 怎么设计的？" → Agent 已有上下文
```

### 场景 4：工作流自动化建议

```
PatternLearner 检测到:
  用户连续 5 天在 9:00 打开 VS Code → 9:05 打开 Terminal → 9:10 打开 Chrome

第 6 天 9:00:
  Agent: 桌面通知 "☕ 早上好！要帮你打开 Terminal 和项目 Dashboard 吗？"
```

### 场景 5：智能防打扰

```
Level 3 检测到:
  用户在 VS Code 中连续停留 > 45 分钟，且文件切换频率高（每分钟 > 3 个文件）
  → "深度编码"模式
  → Agent 将所有非紧急通知静音
  → 仅当剪贴板出现 "error/exception" 时才打破静音

用户切回 Slack/微信:
  → Agent: "过去 45 分钟拦截了 3 条非紧急消息，需要查看摘要吗？"
```

### 场景 6：意图纠正学习

```
Level 1 推断: intent=code (因为选中文本含 class/def)
用户实际选择: action_type=translate
  → PatternLearner 记录: "截取到这段代码 → 用户想要的是翻译而不是代码分析"
  → 权重更新: 当选中文本同时含 (代码特征 + 非母语注释) 时, translate > code

下次相似场景:
  → Level 1 修正推断为 translate
  → 用户不需要手动纠正
```

## LF. 意图捕捉的克制原则

**每项"不做"同样重要：**

| 不做的 | 理由 |
|--------|------|
| **不替用户做决定** | 推断结果只用于预选/建议，永远留一个"切换模式"的入口。置信度 < 70% 时不自动预选 |
| **不调用 LLM 做意图推断** | 全部用规则 + 统计。LLM 做意图推断是杀鸡用牛刀——慢、贵、且黑盒 |
| **不跨用户学习** | PatternLearner 的模型只存在本地，不上传。不同用户的"Chrome→VS Code"含义完全不同 |
| **不会"学错不改"** | PatternLearner 的权重随时间衰减——如果用户的习惯变了，旧模式自然淡出 |

## LG. 实现优先级

```
P0（利用现有基础设施，本周可做）:
  └── Level 1 内容推断（增强 IntentRouter，加入 CONTENT_SIGNATURES）

P1（需要 Context Weaver 到位）:
  ├── Level 2 上下文推断（_infer_intent_from_context）
  └── 场景 1（零选择唤醒）+ 场景 3（上下文预加载）

P2（需要 PatternLearner 积累数据）:
  ├── Level 3 行为模式学习
  ├── 场景 2（主动意图提示）+ 场景 5（智能防打扰）
  └── 场景 4（工作流建议）+ 场景 6（意图纠正学习）
```

## LH. 分步实现指南

> 以下每一步都是**独立可交付的小增量**，只需修改 1-2 个文件，不改架构。

### Step 1：内容推断 —— 给 trigger_ai 加自动意图检测（P0，2 小时）

**改法**：`smart_copilot.py` 的 `trigger_ai()` 第 2838 行，在开头加 30 行。

当前逻辑（L2838-2841）：
```python
def trigger_ai(self, action_type, custom_instruction=None, image_base64=None):
    if not self.current_text and not image_base64:
        return
    # ... action_type 直接由按钮传入，或者 custom_instruction → "custom"
```

改为：
```python
def trigger_ai(self, action_type, custom_instruction=None, image_base64=None):
    if not self.current_text and not image_base64:
        return
    
    # ===== 🆕 新增：内容推断 Level 1 =====
    # 仅当用户未手动选模式（action_type=="auto" 且无自定义指令）时触发
    if action_type == "auto" and not custom_instruction:
        detected = self._detect_intent_from_content(self.current_text)
        if detected["confidence"] >= 0.7:  # 阈值：足够确信才预选
            action_type = detected["intent"]
            print(f"[ASU] 自动推断意图: {action_type} (置信度 {detected['confidence']:.0%}, {detected['reason']})")
        else:
            print(f"[ASU] 意图不明确 ({detected['reason']}), 使用默认 auto 模式")
    # ========================================
    
    # 读取自定义指令（如果有）
    if not custom_instruction:
        custom_instruction = self.instruction_input.text().strip()
    if custom_instruction:
        action_type = "custom"
    ...
```

**新增方法**（加在 SmartCopilot 类内，`_on_app_activated` 旁边即可）：
```python
# 加在 smart_copilot.py 的 import 区（文件头）
import re

# 加在 SmartCopilot 类内（约 L790 附近）
CONTENT_SIGNATURES = {
    "debug": {
        "patterns": [
            r'\b(error|exception|traceback)\b', r'报错', r'异常',
            r'File ".*", line \d+', r'^\s*at\s+\S+\(.*:\d+\)',
        ],
        "weight": 0.95
    },
    "code": {
        "patterns": [
            r'\b(def|class|import|from|return|async|await)\b',
            r'\{[^}]*\}', r'^\s*(#|//|/\*)',
        ],
        "min_lines": 3,
        "weight": 0.85
    },
    "translate": {
        "patterns": [],
        "lang_detect": True,
        "no_code": True,
        "weight": 0.7
    },
}

def _detect_intent_from_content(self, text: str) -> dict:
    """Level 1 内容推断：根据选中文本特征猜测用户意图（不调 LLM）"""
    scores = {}
    reasons = {}

    for intent, sig in self.CONTENT_SIGNATURES.items():
        score = 0.0
        reason_parts = []

        # 正则匹配
        for pattern in sig.get("patterns", []):
            matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
            if matches:
                score += 0.3 * min(len(matches), 3) / 3
                reason_parts.append(f"匹配 {pattern[:25]}")

        # 行数检查
        if sig.get("min_lines"):
            if text.count('\n') + 1 >= sig["min_lines"]:
                score += 0.2

        # 语言检测（简单版：非中文字符比例 > 60%）
        if sig.get("lang_detect"):
            non_cn = sum(1 for c in text if c > '\u4e00' or c < '\u9fff')
            if non_cn / max(len(text), 1) > 0.6:
                score += 0.4
                reason_parts.append("非中文为主")

        # 排除代码特征
        if sig.get("no_code"):
            code_score = scores.get("code", 0)
            if code_score < 0.3:
                score += 0.2
                reason_parts.append("无代码特征")

        scores[intent] = min(score * sig["weight"], 1.0)
        reasons[intent] = "; ".join(reason_parts) if reason_parts else "无明确特征"

    best = max(scores, key=scores.get)
    return {"intent": best, "confidence": scores[best], "reason": reasons.get(best, "")}
```

**验证**：选中一段 Python 代码 → 双击右键 → 终端应打印 `[ASU] 自动推断意图: code (置信度 85%)`。不需要任何 UI 改动。

---

### Step 2：Context Weaver —— 应用切换事件注入上下文（P1，3 小时）

**改法**：`smart_copilot.py`，增强 `_on_app_activated()` 方法（当前 L772-784）。

当前逻辑：收到应用切换 → 存 `recent_apps` → print 日志。不产生任何上下文价值。

改为：每次应用切换 → 更新 `context_snapshot` 字典 → 右键唤出时直接读取快照。

**新增字段**（SmartCopilot.__init__，约 L760 后）：
```python
# smart_copilot.py → SmartCopilot.__init__() 新增

self.active_app = ""
self.previous_app = ""
self.context_snapshot = {}      # 🆕 多源上下文快照
self.switch_count = 0           # 🆕 当日切换次数（用于判断"首次打开"）
self._last_switch_time = 0      # 🆕 上次切换时间戳
```

**增强 _on_app_activated**（替换 L772-784）：
```python
def _on_app_activated(self, app_name, bundle_id):
    now = time.time()
    
    # 🆕 记录切换前状态
    self.previous_app = self.active_app
    self.active_app = app_name
    self.switch_count += 1
    
    # 🆕 构建上下文快照
    self.context_snapshot = {
        "active_app": app_name,
        "bundle_id": bundle_id,
        "previous_app": self.previous_app,
        "switch_count": self.switch_count,
        "timestamp": now,
        "time_since_last_switch": now - self._last_switch_time if self._last_switch_time else 0,
        "is_first_switch_today": self.switch_count == 1,
    }
    self._last_switch_time = now
    
    # 🆕 推断意图（Level 2）
    self.context_snapshot["inferred_intent"] = self._infer_intent_from_context()
    
    # 保留原有日志（向后兼容）
    if self.previous_app and self.previous_app != app_name:
        print(f"[ASU] {self.previous_app} → {app_name} | 推断意图: {self.context_snapshot['inferred_intent'].get('intent', 'unknown')}")
    
    # 维护最近应用列表（保留原有逻辑）
    if app_name in self.recent_apps:
        self.recent_apps.remove(app_name)
    self.recent_apps.append(app_name)
    self.recent_apps = self.recent_apps[-10:]
```

**新增 _infer_intent_from_context**（加在 `_on_app_activated` 下方）：
```python
# 应用分类常量（加在 SmartCopilot 类外，文件顶部）
IDE_APPS = {"VS Code", "Trae", "Cursor", "Xcode", "PyCharm", "IntelliJ IDEA"}
BROWSER_APPS = {"Google Chrome", "Safari", "Brave Browser", "Arc", "Microsoft Edge"}
TERMINAL_APPS = {"Terminal", "iTerm2", "Warp", "Hyper"}

def _infer_intent_from_context(self) -> dict:
    """Level 2：从当前应用+切换模式推断意图（不调 LLM）"""
    snap = self.context_snapshot
    app = snap.get("active_app", "")
    prev = snap.get("previous_app", "")
    signals = []
    
    # 信号：当前应用
    if app in IDE_APPS:
        signals.append(("code", 0.6))
    elif app in BROWSER_APPS:
        signals.append(("research", 0.5))
    elif app in TERMINAL_APPS:
        signals.append(("devops", 0.5))
    
    # 信号：切换模式
    if prev in BROWSER_APPS and app in IDE_APPS:
        signals.append(("debug", 0.7))
    if prev in TERMINAL_APPS and app in IDE_APPS:
        signals.append(("debug", 0.55))
    
    # 信号：当日首次打开 IDE
    if snap.get("is_first_switch_today") and app in IDE_APPS:
        signals.append(("code_review", 0.3))
    
    if not signals:
        return {"intent": "chat", "confidence": 0.3}
    
    best = max(signals, key=lambda s: s[1])
    return {"intent": best[0], "confidence": best[1], "signals": len(signals)}
```

**触发点**：在 `trigger_ai()` 中，内容推断之前先查快照的意图：
```python
# trigger_ai() 中，Level 1 之前插入 Level 2 查询
if action_type == "auto" and not custom_instruction:
    # 🆕 Level 2: 先查上下文快照的推断意图
    inferred = self.context_snapshot.get("inferred_intent", {})
    if inferred.get("intent") == "debug" and inferred.get("confidence", 0) >= 0.6:
        # 快速路径：切浏览器 → IDE 模式，直接 pre-select debug
        has_error = bool(re.search(r'(error|exception|traceback|报错)', self.current_text, re.I))
        if has_error:
            action_type = "code"  # debug intent → code action
            print("[ASU] Context Weaver: 浏览器→IDE 切换 + 报错文本 → 自动选择 code 模式")
        else:
            print(f"[ASU] Context Weaver: {inferred['intent']} intent (confidence {inferred['confidence']:.0%})")
    
    # Level 1: 内容推断（前面 Step 1 加的）
    if action_type == "auto":  # 仍为 auto（Level 2 未命中或置信度不够）
        detected = self._detect_intent_from_content(self.current_text)
        if detected["confidence"] >= 0.7:
            action_type = detected["intent"]
            print(f"[ASU] 内容推断: {action_type} (置信度 {detected['confidence']:.0%})")
```

**验证**：Chrome → VS Code 切换 → 选中含报错的文本 → 双击右键 → 终端打印 `[ASU] Context Weaver: 浏览器→IDE 切换 + 报错文本 → 自动选择 code 模式`。

---

### Step 3：PatternLearner —— 个性化意图学习（P2，4 小时）

**新建文件**：`core/pattern_learner.py`（~100 行）

```python
# core/pattern_learner.py

import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Optional


class PatternLearner:
    """个人化行为模式学习器。纯统计，不调 LLM。"""

    def __init__(self, data_path="~/.asu_copilot/patterns.json"):
        self.data_path = os.path.expanduser(data_path)
        self.patterns = defaultdict(lambda: defaultdict(int))
        self._load()

    def _load(self):
        if os.path.exists(self.data_path):
            with open(self.data_path) as f:
                raw = json.load(f)
                for key, actions in raw.items():
                    self.patterns[key] = defaultdict(int, actions)

    def _save(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        serialized = {k: dict(v) for k, v in self.patterns.items()}
        with open(self.data_path, "w") as f:
            json.dump(serialized, f, indent=2)

    def record(self, context_snapshot: dict, action_type: str):
        """记录一次行为：用户在 XX 场景下选择了 YY action"""
        key = self._make_key(context_snapshot)
        self.patterns[key][action_type] += 1
        # 衰减旧数据（每次 record 时对所有 patterns 做 0.5% 衰减）
        for k in self.patterns:
            for act in self.patterns[k]:
                self.patterns[k][act] *= 0.995
        self._save()

    def predict(self, context_snapshot: dict) -> Optional[str]:
        """预测用户可能选择的 action"""
        key = self._make_key(context_snapshot)
        actions = self.patterns.get(key, {})
        if not actions:
            return None
        total = sum(actions.values())
        best_action, best_count = max(actions.items(), key=lambda x: x[1])
        if total >= 3 and best_count / total >= 0.6:
            return best_action
        return None

    def _make_key(self, snapshot: dict) -> str:
        prev = snapshot.get("previous_app", "unknown")
        curr = snapshot.get("active_app", "unknown")
        hour = datetime.now().hour
        time_slot = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
        return f"{prev}→{curr}@{time_slot}"

    def record_correction(self, context_snapshot: dict, predicted: str, actual: str):
        """记录一次意图纠正：系统预测了 X 但用户选择了 Y"""
        key = self._make_key(context_snapshot)
        # 降低预测错误的 action 权重
        self.patterns[key][predicted] = max(0, self.patterns[key][predicted] - 1)
        self.patterns[key][actual] += 2  # 纠正权重更高
        self._save()
```

**Hook 到 smart_copilot.py**：

```python
# smart_copilot.py → SmartCopilot.__init__() 新增（约 L765 后）
from core.pattern_learner import PatternLearner

self.pattern_learner = PatternLearner()

# smart_copilot.py → trigger_ai() 中，在 Level 1/2 之后插入 Level 3
# （加在 action_type 最终确定后、调用 AIWorker 之前）

# ===== 🆕 Level 3: PatternLearner 预测 =====
if action_type == "auto" and not custom_instruction:
    predicted = self.pattern_learner.predict(self.context_snapshot)
    if predicted:
        action_type = predicted
        print(f"[ASU] PatternLearner: {self.context_snapshot.get('previous_app')}→{self.active_app} 预测 {action_type}")
# =========================================

# 🆕 记录到 PatternLearner（用户确认 action_type 后）
final_action = action_type  # 记录最终使用的 action
# ... AIWorker 调用 ...

# ===== 🆕 在 AIWorker.finished_signal 连接的回调中追记 =====
def _on_ai_finished_with_learning(self):
    """AI 完成后的回调，记录行为模式"""
    self.pattern_learner.record(self.context_snapshot, self._last_action_type)
```

**验证**：连续 3 天在早上 Chrome→VS Code 切换后选择 code 模式 → 第 4 天同一场景 → 双击右键 → 终端打印 `[ASU] PatternLearner: Chrome→VS Code@morning 预测 code`。

---

### Step 4：主动意图提示（P2，2 小时，依赖 Step 2-3 到位）

**改法**：`smart_copilot.py`，`_on_app_activated()` 末尾加触发检查：

```python
# _on_app_activated() 末尾新增

# 🆕 主动意图检测（不唤出卡片，仅弹通知）
if self._should_proactive_suggest():
    QTimer.singleShot(2000, self._show_proactive_suggestion)

def _should_proactive_suggest(self) -> bool:
    """判断是否应该主动提示用户（基于当前上下文）"""
    snap = self.context_snapshot
    
    # 场景：浏览器→IDE + 剪贴板含报错
    if snap.get("previous_app") in BROWSER_APPS and \
       snap.get("active_app") in IDE_APPS:
        try:
            clipboard = subprocess.check_output(["pbpaste"], text=True)[:500]
            if re.search(r'(error|exception|traceback|报错)', clipboard, re.I):
                self._proactive_clipboard = clipboard
                return True
        except Exception:
            pass
    return False

def _show_proactive_suggestion(self):
    """弹出主动建议（macOS 通知）"""
    subprocess.run([
        "osascript", "-e",
        f'display notification "检测到报错信息，需要帮你分析吗？" '
        f'with title "OpenCopilot" sound name "Glass"'
    ])
    # 同时更新 UI 状态（托盘闪烁或卡片预加载）
```

---

### 实现检查清单

| # | 步骤 | 改哪个文件 | 加多少行 | 验证方式 |
|---|------|-----------|----------|----------|
| 1 | Level 1 内容推断 | `smart_copilot.py` | +60 | 选中代码→双击右键→终端打印 code |
| 2 | Context Weaver 上下文编织 | `smart_copilot.py` | +50 | Chrome→VS Code→终端打印 debug intent |
| 3 | PatternLearner | `core/pattern_learner.py` (新) + `smart_copilot.py` | +110 | 连续 3 天→第 4 天自动预测 |
| 4 | 主动意图提示 | `smart_copilot.py` | +35 | Chrome→VS Code+报错→桌面通知弹出 |

**总计**：约 255 行新增代码，修改 1 个现有文件 + 创建 1 个新文件。不涉及任何架构变更。

---

# 附录九：乐高式模块与现有代码兼容指南

> 每个模块的集成策略：插在哪、包住谁、拔掉会怎样、如何用 feature flag 控制。

## 核心原则

```
1. 只新增代码路径，不修改已有代码路径
2. 每个模块一个 feature flag，默认关，开启即生效
3. 所有新模块的入口都是包装器（Wrapper），不是替换器
4. 新文件 > 新类 > 新方法 —— 已有类和方法的修改最小化
```

## MA. 现有代码结构中的插入点地图

```
smart_copilot.py (3999 行)
  ├── SmartCopilot.__init__()       [L710]   ← 新模块初始化注册点
  ├── SmartCopilot._on_app_activated() [L772] ← Context Weaver 插入点
  ├── SmartCopilot.trigger_ai()     [L2838]  ← 内容推断 + PatternLearner 插入点
  ├── SmartCopilot._on_right_clicked()        ← 卡片唤出入口（右键感知化）
  └── AIWorker.run()                [L532]   ← AI 完成后回调（PatternLearner 记录点）

asu_custom_agent.py (552 行)
  ├── ASUAgentMemory                [L323]   ← FTS5 搜索 + 增量标记插入点
  ├── AgentHTTPRequestHandler.do_POST [L447] ← 分层 Prompt + 注入扫描 + Session End Hook
  ├── AgentHTTPRequestHandler.do_GET [L432]  ← 新端点注册点
  └── ContextWindowManager          [L16]    ← 不变，仅 budget 参数被 L5 影响

settings_dialog.py (389 行)
  └── _create_advanced_tab() / 新增 tab     ← 隐私面板插入点
```

## MB. 七个零依赖模块的兼容策略

### MB1. L1 内容意图推断

| 项目 | 细节 |
|------|------|
| **插入位置** | `smart_copilot.py` → `trigger_ai()` 方法，第 5 行之后（`if not self.current_text` 检查之后） |
| **包装方式** | **Wrapper**——在 `action_type` 被使用之前，有条件地覆盖它 |
| **Feature Flag** | `self._feature_content_intent = True`（默认 True，因为它是纯规则，无副作用） |
| **禁用后行为** | `action_type` 保持原值 → 完全退化为现有行为 |
| **对现有代码** | 不修改任何现有行，只在现有逻辑之前插入 10 行 if 块 |

```python
# trigger_ai() 中的实际注入代码 —— 只加不删

def trigger_ai(self, action_type, custom_instruction=None, image_base64=None):
    if not self.current_text and not image_base64:
        return                         # ← 现有，不动
    
    # ───── 🧱 乐高块: L1 内容推断 ─────
    # 拔掉方法：注释下面 10 行，行为完全退化为旧版
    if getattr(self, '_feature_content_intent', True):
        if action_type == "auto" and not custom_instruction:
            detected = self._detect_intent_from_content(self.current_text)
            if detected["confidence"] >= 0.7:
                action_type = detected["intent"]
    # ─────────────────────────────────
    
    # 以下全是现有代码，不动 ——
    if not custom_instruction:
        custom_instruction = self.instruction_input.text().strip()
    ...
```

**UI 兼容**：无 UI 变更。用户看到的卡片和之前完全一样——只是模式按钮的默认选中可能不同。

---

### MB2. L2 注入安全扫描

| 项目 | 细节 |
|------|------|
| **插入位置** | `asu_custom_agent.py` → `build_context_prefix()` 函数的**返回语句之前** |
| **包装方式** | **Wrapper**——wrap 现有的 `build_context_prefix` 返回值 |
| **Feature Flag** | `_feature_injection_scan = True`（默认 True，纯规则无副作用） |
| **禁用后行为** | 浏览器 DOM 内容原样传入 Prompt |
| **对现有代码** | 只在 `build_context_prefix` 返回前套一层，不改函数签名 |

```python
# asu_custom_agent.py → build_context_prefix() 末尾

def build_context_prefix(source, meta):
    # ... 现有逻辑不变 ...
    prefix = ...  # 现有产出
    
    # ───── 🧱 L2: 注入安全扫描 ─────
    # 仅对 browser/drag 来源扫描，IDE 来源信任
    if source in ("browser", "drag"):
        content = meta.get("content", "") or meta.get("url", "")
        prefix = _scan_injection_risks(prefix, content, source)
    # ──────────────────────────────
    
    return prefix
```

**UI 兼容**：无 UI 变更。仅在检测到风险时截断内容，返回结果中用户看到 `[⚠️ 内容已被截断]`。

---

### MB3. L3 知识图谱隐式注入

| 项目 | 细节 |
|------|------|
| **插入位置** | `asu_custom_agent.py` → `do_POST()` 中 `enriched_system` 拼装之后 |
| **包装方式** | **追加**——在 System Prompt 末尾追加一节 |
| **Feature Flag** | `_feature_kg_injection = True` |
| **禁用后行为** | System Prompt 不含知识图谱内容 |
| **对现有代码** | 只在 System Prompt 拼装后加一行 `enriched_system += "\n\n" + _kg_context(text)` |

```python
# asu_custom_agent.py → do_POST() —— enriched_system 拼装后

enriched_system = ...  # 现有: context_prefix + persona_prompt

# ───── 🧱 L3: 知识图谱隐式注入 ─────
if getattr(handler, '_feature_kg_injection', True):
    try:
        kg_ctx = _inject_kg_context(text)  # 关键词→实体→关系，不调 LLM
        if kg_ctx:
            enriched_system += "\n\n## 项目知识\n" + kg_ctx
    except Exception:
        pass  # 知识图谱不可用 → 静默跳过
# ──────────────────────────────────
```

**依赖说明**：依赖 `knowledge_graph/` 模块已经存在。如果 `import` 失败，catch 异常后静默跳过——**不阻塞 Agent 启动**。

**UI 兼容**：无 UI 变更。知识图谱内容对用户透明（在 System Prompt 里）。

---

### MB4. L4 FTS5 对话历史搜索

| 项目 | 细节 |
|------|------|
| **插入位置** | `asu_custom_agent.py` → `ASUAgentMemory` 类，新增方法 |
| **包装方式** | **追加**——新增 `_init_fts()` + `search_history()` 方法，不改现有方法签名 |
| **Feature Flag** | `_feature_fts_search = True` |
| **禁用后行为** | `messages` 表没有 FTS5 索引，只能按 `session_id` 精确查 |
| **对现有代码** | `_init_db()` 末尾追加 FTS5 初始化；其余全是新方法 |

```python
# asu_custom_agent.py → ASUAgentMemory._init_db() 末尾

def _init_db(self):
    # ... 全部现有逻辑不变 ...
    conn.commit()
    
    # ───── 🧱 L4: FTS5 索引 ─────
    if getattr(self, '_feature_fts', True):
        try:
            self._init_fts(conn)
        except Exception:
            pass  # SQLite 版本不支持 FTS5 → 静默跳过
    # ───────────────────────────
```

**关键兼容点**：FTS5 是 SQLite 3.9.0+ 的内置特性，macOS 自带的 SQLite 版本完全支持。如果用户系统极老，try/except 保证不崩。

**UI 兼容**：无 UI 变更。`search_history()` 以 tool 形式暴露给 Agent，由 Agent 自行决定何时调用。

---

### MB5. L5 分层 Prompt（stable/volatile）

| 项目 | 细节 |
|------|------|
| **插入位置** | `asu_custom_agent.py` → `AgentHTTPRequestHandler.do_POST()` 中 `enriched_system` 拼装处 |
| **包装方式** | **替换**——用新的拼装逻辑替换现有的 3 行 |
| **Feature Flag** | `_feature_layered_prompt = True` |
| **禁用后行为** | 完全回到现有 2 层 flat 结构 |
| **对现有代码** | 替换 L474-476 的 3 行拼装逻辑为条件分支 |

```python
# asu_custom_agent.py → do_POST() —— 替换 enriched_system 拼装

# 现有（L474-476）:
# enriched_system = f"{context_prefix}\n\n{persona_prompt}"

# ───── 🧱 L5: 分层 Prompt ─────
if getattr(handler, '_feature_layered_prompt', True):
    stable = handler._get_or_build_stable_prompt()
    volatile = handler._build_volatile_prompt(envelope, session_id)
    enriched_system = stable + "\n\n---\n\n" + volatile
else:
    # 退化：原有 2 层逻辑
    if context_prefix:
        enriched_system = f"{context_prefix}\n\n{persona_prompt}"
    else:
        enriched_system = persona_prompt
# ──────────────────────────────
```

**关键**：else 分支就是现有代码的精确复制。Feature flag 关掉 = 一行代码都没变。

**UI 兼容**：无 UI 变更。Token 节省对用户透明（但终端可打印 `[Cache] stable层命中`）。

---

### MB6. L6 PatternLearner 个人化学习

| 项目 | 细节 |
|------|------|
| **插入位置** | 新建 `core/pattern_learner.py` + `smart_copilot.py` 两处 hook |
| **包装方式** | **追加**——新类 + 新方法，不改已有方法 |
| **Feature Flag** | `self._feature_pattern_learner = True` |
| **禁用后行为** | 不记录行为，不预测意图；退化为仅用 L1 L2 |
| **对现有代码** | `__init__()` 加 3 行初始化；`trigger_ai()` 加 8 行；AI 完成回调加 2 行 |

```python
# smart_copilot.py → __init__() —— 加在 skill 初始化之后

self._init_skills()

# ───── 🧱 L6: PatternLearner ─────
self.pattern_learner = None
if getattr(self, '_feature_pattern_learner', True):
    try:
        from core.pattern_learner import PatternLearner
        self.pattern_learner = PatternLearner()
    except ImportError:
        pass
# ────────────────────────────────

# smart_copilot.py → trigger_ai() —— 加在 L1 L2 之后
if action_type == "auto" and self.pattern_learner:
    predicted = self.pattern_learner.predict(self.context_snapshot)
    if predicted:
        action_type = predicted

# smart_copilot.py → AIWorker.finished 的回调中
if self.pattern_learner:
    self.pattern_learner.record(self.context_snapshot, self._last_action_type)
```

**文件隔离**：`core/pattern_learner.py` 可以独立存在，不修改 `smart_copilot.py` 也能单独测试。

---

### MB7. L7 隐私面板

| 项目 | 细节 |
|------|------|
| **插入位置** | `widgets/settings_dialog.py` → `_create_advanced_tab()` 之后新增 tab |
| **包装方式** | **追加**——新增独立 tab 页，不影响现有设置 |
| **Feature Flag** | `_feature_privacy_dashboard = True` |
| **禁用后行为** | 设置窗口没有隐私 tab，其余 tab 正常 |
| **对现有代码** | 只在 settings_dialog 的 `__init__` 中加一行 `self.addTab(PrivacyDashboard(), "🔒 隐私")` |

```python
# widgets/settings_dialog.py → __init__()

self.addTab(self._create_appearance_tab(), "外观")
self.addTab(self._create_behavior_tab(), "行为")
self.addTab(self._create_office_tab(), "办公")
self.addTab(self._create_advanced_tab(), "高级")

# ───── 🧱 L7: 隐私面板 ─────
if getattr(self, '_feature_privacy_dashboard', True):
    try:
        from widgets.privacy_dashboard import PrivacyDashboard
        self.addTab(PrivacyDashboard(), "🔒 隐私")
    except ImportError:
        pass
# ─────────────────────────────
```

---

## MC. 六个独立模块的兼容策略

### MC1. M1 三层记忆体系

| 项目 | 细节 |
|------|------|
| **涉及文件** | `asu_custom_agent.py`（改）+ 新建 `memory_hook.py` + 新建 `dreaming.py` |
| **关键兼容点** | 不改 `ASUAgentMemory` 现有方法签名，只加 `get_messages_since()` / `get_last_message_id()` 两个新方法 |
| **Session End Hook** | 在 `do_POST()` 的 `[DONE]` 后 fire-and-forget。失败 → 静默跳过，不阻塞 SSE 响应 |
| **Dreaming** | 独立线程/进程。Agent 关掉了 Dreaming 照样跑。Dreaming 挂了 Agent 照样服务 |
| **L2+L3 文件不存在** | `load_memory_context()` 返回空字符串 → System Prompt 不包含记忆层 |
| **Feature Flag** | `_feature_memory = True` |

```python
# asu_custom_agent.py → do_POST() —— [DONE] 之后

self.wfile.write(b"data: [DONE]\n\n")
self.wfile.flush()

# ───── 🧱 M1: Session End Hook (Fire-and-Forget) ─────
if getattr(handler, '_feature_memory', True):
    try:
        _run_session_end_hook_in_background(session_id)  # 不阻塞
    except Exception:
        pass
# ──────────────────────────────────────────────────
```

### MC2. M2 Context Weaver

同 Step 2（附录八 LH），已在 §MB 中覆盖。核心：增强 `_on_app_activated()`，不替换任何现有方法。

### MC3. M3 右键卡片感知化

| 项目 | 细节 |
|------|------|
| **插入位置** | `smart_copilot.py` → 卡片唤出入口（双击右键回调） |
| **包装方式** | 卡片出现**后**立即更新 `context_prefix`，不改变卡片创建逻辑 |
| **退化** | 如果 `context_snapshot` 为空（Broker 未连接），退化为旧的 `build_context_prefix` |
| **Feature Flag** | `_feature_context_card = True` |

### MC4. M4 Cron 调度器

| 项目 | 细节 |
|------|------|
| **文件** | 新建 `agent_scheduler.py`，Agent 启动时 `import` |
| **隔离度** | 完全独立文件。删掉 `import` 就完全消失 |
| **失败处理** | Cron 任务 POST 到 Agent 失败 → logger.error → 不影响下次触发 |
| **Feature Flag** | `_feature_cron = True` |

### MC5. M5 SearXNG 联网搜索

| 项目 | 细节 |
|------|------|
| **文件** | 新建 `tools/web_search.py` + Docker Compose（独立容器） |
| **隔离度** | 搜索是独立 tool，Agent tool-call 时才触发。SearXNG 不在本地 → 退化为"搜索不可用" |
| **Feature Flag** | `_feature_web_search = True` + 检查 SearXNG 是否可达 |

### MC6. M6 多任务面板

| 项目 | 细节 |
|------|------|
| **文件** | 新建 `widgets/task_panel.py`，`smart_copilot.py` 中注册 |
| **隔离度** | 完全独立 Widget。`self.tabs` 中加一个新 tab，不影响现有两个 tab |
| **触发** | 三击右键 → 切换到任务面板 tab（取代当前"工作台"窗口） |
| **Feature Flag** | `_feature_task_panel = True` |

---

## MD. Feature Flag 总览

所有模块共享一个配置文件，用户可在 UI 中一键开关：

```json
// ~/.asu_copilot/features.json（模块开关）
{
  "content_intent": true,      // L1  选中文本自动推断意图
  "injection_scan": true,      // L2  prompt injection 扫描
  "kg_injection": true,        // L3  知识图谱隐式注入
  "fts_search": true,          // L4  对话历史全文搜索
  "layered_prompt": true,      // L5  分层 Prompt stable/volatile
  "pattern_learner": true,     // L6  个人化行为学习
  "privacy_dashboard": true,   // L7  隐私面板
  "memory": true,              // M1  三层记忆体系
  "context_weaver": true,      // M2  上下文编织层
  "context_card": true,        // M3  右键卡片感知化
  "cron": false,               // M4  定时调度（默认关，显式开启）
  "web_search": false,         // M5  联网搜索（默认关，需先部署 SearXNG）
  "task_panel": false,         // M6  多任务面板（默认关，UI 改动大）
  "proactive_trigger": false,  // M7  主动意图提示（默认关，需 PatternLearner + Weaver 就位）
  "skill_generation": false,   // PG8 Skill 半自动生成（默认关，需五道防线就位）
  "rule_incubator": false,     // PG4 Rule Incubator（默认关，需 PatternLearner 积累数据）
  "sandbox": false,            // 代码执行沙盒（默认关，安全敏感）
  "provider_failover": false,  // Provider 故障转移（默认关，需多 API Key 配置）
  "mcp_client": false,         // MCP Client（默认关，需用户显式配置 mcp_servers.json）
  "mcp_server": false          // MCP Server（默认关，需被外部工具显式调用）
}
```

在 smart_copilot.py 和 asu_custom_agent.py 中统一读取：

```python
# 文件头，Agent/UI 启动时各加载一次
import json, os
FEATURES_PATH = os.path.expanduser("~/.asu_copilot/features.json")
_features = {}
if os.path.exists(FEATURES_PATH):
    with open(FEATURES_PATH) as f:
        _features = json.load(f)

def is_feature_on(name: str) -> bool:
    return _features.get(name, True)  # 未配置的默认开启（保守策略）
```

---

## ME. 向后兼容检查清单

每个模块合并前必须通过：

| 检查项 | 通过标准 |
|--------|----------|
| **Feature flag 关 = 旧行为** | 关闭模块，所有现有测试仍 100% 通过 |
| **新文件删掉 = 不崩** | 删除 `core/pattern_learner.py`，UI 仍正常启动（`ImportError` 被 catch） |
| **依赖不存在 = 降级** | 知识图谱未加载 → L3 静默跳过；Broker 未连接 → M2 快照为空 |
| **异常不传播** | 所有新模块的 try/except 都不向外抛异常 |
| **UI 不破坏** | 新 tab/按钮只在 feature flag 开启时创建；关闭后窗口布局不变 |
| **Agent API 不破坏** | `POST /v1/agent/chat` 的请求/响应格式不变；新增端点用新路径 |

---

# 附录十：100% API 覆盖率矩阵

> 当前 4 个服务 ~119 个端点，但 14 个乐高模块中有 **10 个没有对外暴露任何 API**——它们的逻辑埋在 GUI 内部，只能通过 UI 操作 + 终端日志验证。要让我能通过 API 组合验证所有核心功能，需要补的是一套**统一的内部测试面（Internal Test Surface）**。

## NA. 现状盘点

### NA1. 现有端点分布

| 服务 | 端口 | 端点数 | 定位 |
|------|------|--------|------|
| `asu_custom_agent.py` | 18888 | **2** | Agent 核心：健康检查 + 对话 |
| `asu_broker/core/server.py` | 18889 | **16** | 特权探针：系统事件 + DOM + 截图 + 剪贴板 + 文件 |
| `smart_copilot_platform.py` | 8089 | **15** | 能力平台：上下文管理 + 动作执行 + 探测 |
| `smart_copilot_api.py` | 8088 | **60** | 综合 API：聊天/PPT/文件/格式化/Persona/评估/知识/代码 |
| `knowledge_graph/api.py` | 8090 | **26** | 知识图谱独立服务 |
| **合计** | **5 服务** | **~119** | |

### NA2. 乐高模块 × API 覆盖率矩阵

| 模块 | 有 API？ | 现状 |
|------|:---:|------|
| L1 内容意图推断 | ❌ | `trigger_ai()` 内部逻辑，无端点 |
| L2 注入安全扫描 | ❌ | `build_context_prefix()` 内部逻辑 |
| L3 知识图谱隐式注入 | ⚠️ | KG API 可用，但注入验证无端点 |
| L4 FTS5 对话搜索 | ❌ | 尚未实现，且无端点设计 |
| L5 分层 Prompt | ❌ | `do_POST()` 内部逻辑 |
| L6 PatternLearner | ❌ | 新模块，需新端点 |
| L7 隐私面板 | ❌ | 纯 UI，但面板数据来源无 API |
| M1 三层记忆 | ❌ | 尚未实现，零端点 |
| M2 Context Weaver | ❌ | `_on_app_activated()` 内部逻辑 |
| M3 右键卡片感知化 | ❌ | GUI 内部逻辑 |
| M4 Cron 调度器 | ❌ | 新模块，需新端点 |
| M5 SearXNG 联网搜索 | ❌ | 新模块，需 tool 端点 |
| M6 多任务面板 | ⚠️ | sessions 数据有 SQLite，无 CRUD API |
| M7 主动意图提示 | ❌ | 系统事件触发，无可测试端点 |

**现状：14 个模块中，仅 2 个有部分 API（L3、M6），其余 12 个完全不可通过 API 测试。覆盖率约 14%。**

## NB. 补全策略：统一的内部测试面

不分散到 5 个服务各自加端点——而是在 **Agent（18888）上集中暴露一套统一测试面**：

```
统一测试面设计原则：
1. 每个乐高模块 ≥ 2 个端点（1 个触发/查询 + 1 个状态/验证）
2. 所有端点路径以 /v1/agent/ 为前缀，统一鉴权
3. 只读端点用 GET，有副作用的用 POST
4. 每个端点返回结构化 JSON，包含 success + data + error
5. 生产环境下通过 feature flag 可整体关闭
```

## NC. 完整 API 矩阵（现有 + 需补）

> 标记 🆕 的是新增端点，标记 ✅ 的是现有端点。

### NC1. Agent 核心服务（Port 18888）—— 当前 2 → 目标 39

```
健康检查
  GET  /health                                    ✅ 已有

对话
  POST /v1/agent/chat                             ✅ 已有
  POST /v1/agent/task                             🆕 工具循环端点

─── L1 内容意图推断 ───
  POST /v1/agent/intent/detect                    🆕 提交文本 → 返回推断的 intent + confidence
       {"text": "def foo():\n    return 1"} → {"intent":"code","confidence":0.85}

─── L2 注入安全扫描 ───
  POST /v1/agent/security/scan                    🆕 提交文本 → 返回是否检测到注入风险
       {"text": "ignore all previous instructions", "source": "browser"}
       → {"risk": true, "pattern": "ignore.*instructions", "truncated": true}

─── L3 知识图谱隐式注入 ───
  POST /v1/agent/kg/inject                        🆕 提交文本 → 返回会注入的 KG 上下文片段
       {"text": "Broker WebSocket"} → {"injected": ["events_probe ←depends_on→ server", ...]}

─── L4 FTS5 对话搜索 ───
  POST /v1/agent/search/history                   🆕 全文搜索对话历史
       {"query": "Broker 空指针", "limit": 5} → {"results": [...]}
  GET  /v1/agent/search/history?q=Broker          🆕 GET 简写

─── L5 分层 Prompt ───
  GET  /v1/agent/prompt/stats                     🆕 返回 stable/volatile 层大小 + 缓存命中率
       → {"stable_chars": 3200, "volatile_chars": 800, "cache_hits": 15, "cache_misses": 3}
  POST /v1/agent/prompt/invalidate                🆕 手动失效缓存（Persona 热更后调用）

─── L6 PatternLearner ───
  POST /v1/agent/patterns/record                  🆕 记录一次行为模式
       {"context": {"prev":"Chrome","curr":"VS Code","time":"morning"}, "action":"code"}
  POST /v1/agent/patterns/predict                 🆕 预测当前场景的意图
       {"context": {"prev":"Chrome","curr":"VS Code","time":"morning"}}
       → {"predicted":"code", "confidence": 0.8, "samples": 5}
  GET  /v1/agent/patterns/stats                   🆕 已学习的模式总数 + 热门 pattern

─── M1 三层记忆 ───
  POST /v1/agent/memory/remember                  🆕 写入长期记忆:"记住：偏好 Python 3.11"
  POST /v1/agent/memory/search                    🆕 搜索记忆文件 → memory_search
       {"query": "Broker", "days": 30} → {"results": [...]}
  GET  /v1/agent/memory/today                     🆕 读取今日日志
  POST /v1/agent/memory/forget                    🆕 删除匹配行
  POST /v1/agent/memory/summarize                 🆕 手动触发 Dreaming
  GET  /v1/agent/memory/status                    🆕 L2 文件数 + L3 大小 + Hook 状态
  POST /v1/agent/memory/invalidate                🆕 失效记忆快照（强制刷新）

─── M2 Context Weaver ───
  GET  /v1/agent/context/weaver                   🆕 读当前 context_snapshot
       → {"active_app":"VS Code", "previous_app":"Chrome", "inferred_intent":"debug", ...}
  POST /v1/agent/context/weaver/update            🆕 模拟应用切换事件（测试用）
       {"app_name": "VS Code", "bundle_id": "com.microsoft.VSCode"}
  POST /v1/agent/context/weaver/reset             🆕 清空快照

─── M4 Cron 调度器 ───
  GET  /v1/agent/cron                             🆕 列出所有定时任务
  POST /v1/agent/cron                             🆕 添加定时任务
       {"schedule": "08:00", "prompt": "[每日早报] 总结昨天的工作"}
  DELETE /v1/agent/cron/{task_id}                 🆕 删除定时任务
  POST /v1/agent/cron/trigger/{task_id}           🆕 手动触发一次（测试用）

─── M5 联网搜索 ───
  POST /v1/agent/search/web                       🆕 联网搜索
       {"query": "Python 3.13 asyncio", "num_results": 3} → {"results": [...]}
  GET  /v1/agent/search/web/status                🆕 SearXNG 可达性检查

─── M6 多任务面板 ───
  GET  /v1/agent/sessions                         🆕 列出所有 session（任务卡片）
       → [{"session_id":"abc", "title":"Broker修复", "message_count":8, "status":"active"}, ...]
  GET  /v1/agent/session/{id}                     🆕 单个 session 详情 + 历史消息
  POST /v1/agent/session/{id}/archive             🆕 归档
  POST /v1/agent/session/{id}/delete              🆕 删除
  POST /v1/agent/session/{id}/rename              🆕 重命名: {"title": "新标题"}

─── M7 主动意图提示 ───
  POST /v1/agent/intent/proactive                 🆕 基于当前快照判断"是否该主动提示"
       → {"should_suggest": true, "reason": "浏览器→IDE + 剪贴板含报错", "suggestion": "需要分析报错吗?"}

─── L7 隐私面板 ───
  GET  /v1/agent/privacy/stats                    🆕 隐私面板数据
       → {"llm_requests_today": 23, "messages_stored": 142, "memory_extractions": 3, ...}

─── 全局控制 ───
  GET  /v1/agent/features                         🆕 读取所有 feature flag 状态
  POST /v1/agent/features                         🆕 批量开关 feature
       {"content_intent": true, "memory": false, ...}

─── MCP 协议 ───
  GET  /v1/agent/mcp/servers                      🆕 列出已配置的 MCP Server 及其工具
  POST /v1/agent/mcp/refresh                      🆕 重新加载 mcp_servers.json + 重连
  GET  /v1/agent/mcp/{server}/tools               🆕 单个 MCP Server 的工具列表
  POST /v1/agent/mcp/{server}/call                🆕 手动测试 MCP tool 调用
       {"tool": "create_issue", "arguments": {"title": "test"}}
```

### NC2. Broker 服务（Port 18889）—— 当前 16，无需增补

Broker 端点已经完整覆盖系统探针能力。无需为乐高模块新增端点。

### NC3. Platform 服务（Port 8089）—— 当前 15，可选增补

| 端点 | 说明 |
|------|------|
| `POST /api/context/weaver` | 🆕 传递 proxy——读 Agent 的 context_snapshot（M2 集成到 Platform 场景） |

其余乐高模块的 API 面统一走 Agent 18888。

### NC4. smart_copilot_api.py（Port 8088）—— 当前 60，不增补

这个服务已经有 60 个端点，覆盖了 Skill 执行、文件操作、格式化、Persona、评估、知识图谱、代码审查等全部已有功能。**不需要为乐高模块新增端点**——乐高模块的测试面统一走 Agent 18888。

## ND. 端点总数对比

| 阶段 | Agent (18888) | Broker (18889) | Platform (8089) | API (8088) | KG (8090) | **总计** |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| **当前** | 2 | 16 | 15 | 60 | 26 | **119** |
| **补全后** | 39 | 16 | 16 | 60 | 26 | **157** |
| **新增** | +37 | 0 | +1 | 0 | 0 | **+38** |

## NE. 核心验证场景 × API 调用链

让我能通过 API 组合验证每个关键场景：

### 场景 1：内容推断 + 记忆回写 端到端

```bash
# 1. 模拟用户选中文本，检测意图
curl -X POST 127.0.0.1:18888/v1/agent/intent/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "def calculate(x):\n    return x * 2"}'
# → {"intent": "code", "confidence": 0.85}

# 2. 发起代码对话
curl -X POST 127.0.0.1:18888/v1/agent/chat \
  -d '{"text": "def calculate(x):\n    return x * 2", "action_type": "code", "session_id": "test-001"}'

# 3. 验证对话结束后记忆已回写
curl 127.0.0.1:18888/v1/agent/memory/today
# → 应包含刚才对话的提炼摘要

# 4. 搜索对话历史验证 FTS5
curl -X POST 127.0.0.1:18888/v1/agent/search/history \
  -d '{"query": "calculate"}'
# → 应命中刚才的对话
```

### 场景 2：Context Weaver + 意图预测 端到端

```bash
# 1. 模拟 Chrome → VS Code 切换
curl -X POST 127.0.0.1:18888/v1/agent/context/weaver/update \
  -d '{"app_name": "Google Chrome", "bundle_id": "com.google.Chrome"}'

curl -X POST 127.0.0.1:18888/v1/agent/context/weaver/update \
  -d '{"app_name": "VS Code", "bundle_id": "com.microsoft.VSCode"}'

# 2. 读取快照验证
curl 127.0.0.1:18888/v1/agent/context/weaver
# → {"active_app":"VS Code", "previous_app":"Google Chrome", "inferred_intent":"debug", ...}

# 3. 验证主动意图提示
curl -X POST 127.0.0.1:18888/v1/agent/intent/proactive \
  -d '{"has_clipboard_error": true}'
# → {"should_suggest": true, "reason": "浏览器→IDE + 剪贴板含报错"}
```

### 场景 3：三层记忆完整闭环

```bash
# 1. 发起多轮对话触发记忆提炼
curl -X POST 127.0.0.1:18888/v1/agent/chat \
  -d '{"text": "我偏好 Python 3.11", "session_id": "mem-test", "action_type": "auto"}'

# 2. 手动记住关键偏好
curl -X POST 127.0.0.1:18888/v1/agent/memory/remember \
  -d '{"fact": "用户偏好先讨论方案再动手，不喜欢 AI 直接改代码"}'

# 3. 检查今日日志
curl 127.0.0.1:18888/v1/agent/memory/today

# 4. 搜索记忆
curl -X POST 127.0.0.1:18888/v1/agent/memory/search \
  -d '{"query": "Python 3.11", "days": 7}'

# 5. 手动触发 Dreaming
curl -X POST 127.0.0.1:18888/v1/agent/memory/summarize \
  -d '{"days": 7}'

# 6. 验证 MEMORY.md 已更新
curl 127.0.0.1:18888/v1/agent/memory/status
# → {"l2_files": 3, "l3_size_kb": 2.1, "last_dreaming": "2026-06-01T18:30:00"}
```

### 场景 4：自主执行完整链路

```bash
# 1. 添加每日早报任务
curl -X POST 127.0.0.1:18888/v1/agent/cron \
  -d '{"schedule": "08:00", "prompt": "[每日早报] 总结昨天的工作，列出今天建议"}''

# 2. 查看任务列表
curl 127.0.0.1:18888/v1/agent/cron

# 3. 手动触发测试
curl -X POST 127.0.0.1:18888/v1/agent/cron/trigger/task-001

# 4. 验证 Agent 用到了 tool-calling: 先 search_history → 生成早报
#    （检查 /v1/agent/memory/today 看早报是否已记录）
```

### 场景 5：多任务面板生命周期

```bash
# 1. 创建新对话（模拟 [+ 新建] 按钮）
curl -X POST 127.0.0.1:18888/v1/agent/chat \
  -d '{"text": "修复 Broker 空指针", "session_id": "task-broker-fix", "is_new_task": true}'

curl -X POST 127.0.0.1:18888/v1/agent/chat \
  -d '{"text": "翻译技术文档", "session_id": "task-translate", "is_new_task": true}'

# 2. 查看任务列表
curl 127.0.0.1:18888/v1/agent/sessions
# → 应包含 task-broker-fix, task-translate 两个活跃 session

# 3. 重命名任务
curl -X POST 127.0.0.1:18888/v1/agent/session/task-broker-fix/rename \
  -d '{"title": "🔧 Broker 空指针异常修复"}'

# 4. 归档完成的任务
curl -X POST 127.0.0.1:18888/v1/agent/session/task-translate/archive

# 5. 验证归档
curl 127.0.0.1:18888/v1/agent/sessions
# → 只包含 task-broker-fix
```

### 场景 6：完整工作流 —— 搜索 + 对话 + 记忆

```bash
# 模拟完整的一天：
# 早上 → 搜索昨天的记忆 → 继续昨天的工作 → 联网查资料 → 写代码 → 记忆自动提炼

# 1. 搜索昨天的讨论
curl -X POST 127.0.0.1:18888/v1/agent/search/history \
  -d '{"query": "Broker 空指针"}'

# 2. 继续讨论
curl -X POST 127.0.0.1:18888/v1/agent/chat \
  -d '{"text": "上次讨论的空指针修好了吗？", "session_id": "task-broker-fix"}'

# 3. 联网搜索相关方案
curl -X POST 127.0.0.1:18888/v1/agent/search/web \
  -d '{"query": "Python null pointer exception fix pattern"}'

# 4. 验证今天的工作已记录
curl 127.0.0.1:18888/v1/agent/memory/today

# 5. 查看 PatternLearner 是否学到了模式
curl 127.0.0.1:18888/v1/agent/patterns/stats
```

## NF. 新增端点汇总清单

| # | 端点 | 对应模块 | 方法 | 用途 |
|---|------|----------|------|------|
| 1 | `/v1/agent/task` | 自主执行 | POST | 工具循环端点 |
| 2 | `/v1/agent/intent/detect` | L1 | POST | 内容推断 |
| 3 | `/v1/agent/security/scan` | L2 | POST | 注入扫描 |
| 4 | `/v1/agent/kg/inject` | L3 | POST | KG 隐式注入结果 |
| 5 | `/v1/agent/search/history` | L4 | POST/GET | FTS5 对话搜索 |
| 6 | `/v1/agent/prompt/stats` | L5 | GET | 分层 Prompt 统计 |
| 7 | `/v1/agent/prompt/invalidate` | L5 | POST | 失效缓存 |
| 8 | `/v1/agent/patterns/record` | L6 | POST | 记录行为 |
| 9 | `/v1/agent/patterns/predict` | L6 | POST | 预测意图 |
| 10 | `/v1/agent/patterns/stats` | L6 | GET | 学习统计 |
| 11 | `/v1/agent/memory/remember` | M1 | POST | 写长期记忆 |
| 12 | `/v1/agent/memory/search` | M1 | POST | 搜记忆文件 |
| 13 | `/v1/agent/memory/today` | M1 | GET | 今日日志 |
| 14 | `/v1/agent/memory/forget` | M1 | POST | 删除记忆 |
| 15 | `/v1/agent/memory/summarize` | M1 | POST | 手动 Dreaming |
| 16 | `/v1/agent/memory/status` | M1 | GET | 记忆统计 |
| 17 | `/v1/agent/memory/invalidate` | M1 | POST | 失效快照 |
| 18 | `/v1/agent/context/weaver` | M2 | GET | 读快照 |
| 19 | `/v1/agent/context/weaver/update` | M2 | POST | 模拟切换 |
| 20 | `/v1/agent/context/weaver/reset` | M2 | POST | 清空快照 |
| 21 | `/v1/agent/cron` | M4 | GET | 列任务 |
| 22 | `/v1/agent/cron` | M4 | POST | 加任务 |
| 23 | `/v1/agent/cron/{id}` | M4 | DELETE | 删任务 |
| 24 | `/v1/agent/cron/trigger/{id}` | M4 | POST | 手动触发 |
| 25 | `/v1/agent/search/web` | M5 | POST | 联网搜索 |
| 26 | `/v1/agent/search/web/status` | M5 | GET | SearXNG 状态 |
| 27 | `/v1/agent/sessions` | M6 | GET | 任务列表 |
| 28 | `/v1/agent/session/{id}` | M6 | GET | 任务详情 |
| 29 | `/v1/agent/session/{id}/archive` | M6 | POST | 归档 |
| 30 | `/v1/agent/session/{id}/delete` | M6 | POST | 删除 |
| 31 | `/v1/agent/session/{id}/rename` | M6 | POST | 重命名 |
| 32 | `/v1/agent/intent/proactive` | M7 | POST | 主动提示判断 |
| 33 | `/v1/agent/privacy/stats` | L7 | GET | 隐私面板数据 |
| 34 | `/v1/agent/features` | 全局 | GET/POST | Feature flag 管理 |
| 35 | `/v1/agent/mcp/servers` | MCP | GET | 列出已配置的 MCP Server |
| 36 | `/v1/agent/mcp/refresh` | MCP | POST | 重连所有 MCP Server |
| 37 | `/v1/agent/mcp/{server}/tools` | MCP | GET | 单个 MCP Server 工具列表 |
| 38 | `/v1/agent/mcp/{server}/call` | MCP | POST | 测试调用 MCP tool |

**总计：38 个新增端点，全部集中在 Agent 18888。**

## NG. 实现策略

```
1. 新增端点只在 Agent (18888) 的 do_GET/do_POST 中追加 elif 分支
2. 每个端点 10-30 行代码，总计 ~600 行
3. 生产环境下通过 /v1/agent/features 可整体关闭测试面
4. 所有新增端点不修改现有 /health 和 /v1/agent/chat 的任何逻辑
5. 新增端点独立于 GUI——Agent 启动即注册，UI 不开也能通过 curl 测试
```

这样你可以在没有 GUI 的环境下（SSH 到机器、CI pipeline、脚本批量测试），通过 API 组合验证从"内容推断 → 意图路由 → 对话执行 → 记忆回写 → 搜索验证 → Pattern 学习"的完整链路。

---

# 附录十一：LLM 能力边界与扩展决策框架

> 这是整个设计方案的底层哲学。当 LLM 撞到能力墙时——算不对数、不知道时间、不认识项目文件、记不住昨天聊了什么——我们该用 Rule、Skill、Coding Agent 还是 Prompt Injection 来填？这个框架给出每类缺口的最优解法及其决策逻辑。

## PA. LLM 的七类天然边界

LLM 不是一个通用计算引擎。它有七类**结构性的**能力缺口，不是"模型不够大"的问题，而是"Transformer 架构本身做不了"的问题：

| # | 边界类型 | 为什么 LLM 做不了 | 例 |
|---|---------|-------------------|-----|
| 1 | **实时数据访问** | 训练数据有截止日期 | "今天天气"、"Python 3.14 的新特性" |
| 2 | **精确计算** | 概率生成，非数值计算 | 复杂数学、数据统计、金额计算 |
| 3 | **系统 I/O** | 无法逃脱沙盒执行环境 | 读写文件、执行命令、访问 API |
| 4 | **持久状态** | 无状态推理，无自主存储 | 跨会话记忆、用户偏好 |
| 5 | **项目结构知识** | 训练数据不带你的项目文件 | "这个函数在哪个文件里"、"Broker 和 UI 怎么通信" |
| 6 | **确定性规则** | 概率输出，不可靠 | "每次翻译后不要加解释"（偶尔还是会加） |
| 7 | **多步推理执行** | 单次推理无反馈循环 | "跑测试 → 看结果 → 修代码 → 再跑" |

## PB. 四种扩展机制及其适用边界

OpenCopilot 有四种机制来填补这些缺口。每种有不同的成本、确定性、灵活性和适用场景：

| 机制 | 成本 | 确定性 | 灵活性 | 适用缺口的本质 |
|------|:---:|:---:|:---:|------|
| **规则 (Rule)** | 零 Token，零延迟 | 100% | 低 | 模式匹配、安全拦截、快速分类 |
| **Prompt 注入** | 低 Token（每次注入） | 中（LLM 可能忽略） | 中 | 上下文信息、项目知识、记忆 |
| **Skill** | 中 Token（tool_call + 执行） | 中（结构化输出） | 高 | 领域工作流、结构化操作 |
| **Coding Agent** | 高 Token（生成 + 执行） | 低（代码可能出错） | 最高 | 动态计算、探索性操作 |

## PC. 逐类边界的扩展策略

### 边界 1：实时数据访问

**缺口**：LLM 不知道 2026 年 6 月 2 日发生了什么。

| 策略 | 机制 | 具体做法 |
|------|------|----------|
| **首选** | Tool + Rule | SearXNG 联网搜索（M5），LLM tool-call `web_search("Python 3.14 release")`，搜索结果作为 tool result 注入 |
| **不用** | Prompt 注入 | ——永远不要提前把所有"可能需要的实时信息"注入 Prompt，浪费 Token |
| **不用** | Coding Agent | ——实时数据应该先取回再处理，不是让 LLM 写爬虫代码 |

### 边界 2：精确计算

**缺口**：LLM 可能算错"1234567 × 7654321"。

| 策略 | 机制 | 具体做法 |
|------|------|----------|
| **首选** | Coding Agent | LLM 生成 `python -c "print(1234567 * 7654321)"` → 沙盒执行 → 结果注入 |
| **备选** | Skill | FileSkill 读 CSV → Python 脚本做数据聚合 → 返回 |
| **不用** | Rule | ——数值计算种类无限，规则覆盖不了 |
| **不用** | Prompt | ——不要让 LLM "心算" |

> **判定线**：如果任务需要"执行代码并获取输出"（计算、数据清洗、图表生成），用 Coding Agent。如果任务只是"用已知工具处理结构化数据"（翻译、格式转换），用 Skill。

### 边界 3：系统 I/O

**缺口**：LLM 不能自己读文件、写文件、跑命令。

| 策略 | 机制 | 具体做法 |
|------|------|----------|
| **读操作** | Rule + Broker | Broker 已经封装了文件读取、DOM 提取、截图。这些都是**预定义的受控操作**，不需要 LLM 生成代码 |
| **写操作** | Skill | FileSkill.write()，内置路径检查（仅限项目目录）+ 大小限制 |
| **命令执行** | Coding Agent + 沙盒 | `execute_command("pytest tests/")`，白名单命令 + 30s 超时 |
| **不用** | Prompt | ——不要把文件内容全部塞入 Prompt 让 LLM 自己"找到需要的部分" |

> **判定线**：预定义的 I/O（读文件、读 DOM、复制剪贴板）用 Rule/Broker。LLM 决定"需要什么"但不由 LLM 生成实现代码。非预定义、需要动态组合的命令（pipeline）用 Coding Agent。

### 边界 4：持久状态

**缺口**：LLM 重启后记不住任何东西。

| 策略 | 机制 | 具体做法 |
|------|------|----------|
| **首选** | Prompt 注入 | 三层记忆体系（M1）：L2 每日日志 + L3 长期记忆 → 冻结快照 → 注入 System Prompt volatile 层 |
| **辅助** | Skill | MemorySkill：`memory_search("Broker bug")`、`memory_remember("偏好 Python 3.11")` |
| **支撑** | Rule | Session End Hook（门控 + 提炼）、Dreaming（定时压缩）——这些是自动化的规则流程 |
| **不用** | Coding Agent | ——记忆不需要动态代码，需要的是可靠的读写 + 定期的提炼压缩 |

> **判定线**：记忆的本质是"存事实 + 在需要时提取"，最适合的是 Prompt 注入（自动注入到每次对话）+ Skill（用户/Agent 主动搜索）+ Rule（自动提炼和压缩的触发逻辑）。

### 边界 5：项目结构知识

**缺口**：LLM 不知道 `events_probe.py` 和 `server.py` 的关系。

| 策略 | 机制 | 具体做法 |
|------|------|----------|
| **首选** | Prompt 注入 | 知识图谱隐式注入（L3）：从用户问题中提取关键词 → 查 KG → 注入 System Prompt |
| **辅助** | Rule | Context Weaver（M2）：应用切换到 IDE 时自动查当前文件的 KG 关联 |
| **最高精度** | Skill | KnowledgeSkill：用户显式问"Broker 的依赖是什么"时，精确查询 |

> **这里不用 Coding Agent**——让 LLM 自己"理解项目结构"不如直接给它结构化的实体关系。

### 边界 6：确定性规则

**缺口**：LLM 是概率生成，没法 100% 保证"不要解释，只输出翻译结果"。

| 策略 | 机制 | 具体做法 |
|------|------|----------|
| **Prompt 层** | Persona .md | "你是金牌翻译官。只输出翻译结果，不带任何解释。"（减少但不能消除） |
| **输出层** | Rule（后处理） | 正则剥离翻译结果前后的解释性文字 |
| **安全层** | Rule | 注入扫描（L2）：防止 prompt injection。命令白名单：防止危险命令 |
| **不用** | Coding Agent | ——"保证 LLM 行为"不应该依赖 LLM 生成代码来约束自己 |

> **判定线**：如果需求是"阻止坏行为"（安全扫描、命令白名单）→ Rule。如果需求是"引导好行为"（翻译质量）→ Persona Prompt + Feature Flag 规则约束。

### 边界 7：多步推理执行

**缺口**：单次 `POST /v1/agent/chat` 只做一次推理。

| 策略 | 机制 | 具体做法 |
|------|------|----------|
| **首选** | Coding Agent | tool-calling loop（附录四 U）：Agent 推理 → tool_call → 看结果 → 再推理 |
| **备选** | Rule（编排） | Cron（M4）自动触发、事件驱动规则（M7）自动触发 |
| **组合** | Skill 编排 | SkillExecutor.execute_plan()：多个 Skill 串行执行 |

## PD. 四种机制的协作关系

四种机制不是替代关系，而是分层关系：

```
┌──────────────────────────────────────────────────┐
│                   用户请求                        │
└──────────────────────┬───────────────────────────┘
                       │
              ┌────────▼────────┐
              │  Rule 层（门控） │  ← 意图推断、注入扫描、门控检查
              │  快速、确定性    │     这些不需要 LLM
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  Prompt 注入层   │  ← 记忆快照、KG 实体、项目上下文
              │  隐式、低摩擦    │     自动注入，用户无感
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  Skill 层        │  ← 翻译、PPT、代码审查、知识查询
              │  结构化、可复用   │     确定的领域工作流
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  Coding Agent    │  ← 动态计算、多步推理、探索性操作
              │  灵活、高成本     │     LLM 生成代码 → 沙盒执行
              └──────────────────┘
```

每一层只处理自己最适合的问题。Rule 层犯错了不会浪费 Token；Coding Agent 层只用于 Rule + Skill 都处理不了的动态需求。

## PE. 实际边界判断清单

当你面对一个新需求时，按此决策树选择机制：

```
Q1: 这个需求是不是"阻止坏行为"（安全、合规）？
    → 是 → Rule（注入扫描、命令白名单、路径校验）
    → 否 → Q2

Q2: 这个需求是不是"给 LLM 补充当前不知道的信息"？
    → 是 → Prompt 注入（记忆、KG、项目上下文）
    → 否 → Q3

Q3: 这个需求是不是"一个已知的、可结构化的工作流"？
    → 是 → Skill（翻译、PPT、格式化、知识查询、代码审查）
    → 否 → Q4

Q4: 这个需求是不是"需要动态计算、多步探索、生成并执行代码"？
    → 是 → Coding Agent（tool-calling loop 或 LLM 生成 Python → 沙盒执行）
    → 否 → 回到 Q2——你可能漏掉了某些上下文信息
```

## PF. 在现有乐高模块中的体现

| 乐高模块 | 用了哪种机制 | 为什么 |
|----------|------------|--------|
| L1 内容推断 | **Rule** | 正则匹配文本特征，无需 LLM |
| L2 注入扫描 | **Rule** | 安全拦截必须确定性，不能用概率 |
| L3 知识图谱注入 | **Prompt 注入** | 结构化关系直接注入 Prompt |
| L4 FTS5 搜索 | **Rule**（SQLite）+ **Skill**（tool 暴露） | 搜索是确定性操作，Skill 是暴露层 |
| L5 分层 Prompt | **Rule**（缓存逻辑）+ **Prompt 注入**（记忆层） | 缓存是工程优化，注入是信息补充 |
| L6 PatternLearner | **Rule** | 纯统计，不调 LLM |
| L7 隐私面板 | **Rule** | 统计数据显示，无需 AI |
| M1 三层记忆 | **Rule**（Hook+门控+Dreaming）+ **Prompt 注入**（记忆快照）+ **Skill**（检索） | 三种机制协作 |
| M2 Context Weaver | **Rule** | 事件驱动快照，全规则引擎 |
| M4 Cron | **Rule**（调度）+ **Coding Agent**（执行） | 调度是规则，但任务执行可能需要工具循环 |
| M5 联网搜索 | **Coding Agent**（tool 暴露，LLM 决策何时调用） | 搜索时机由 LLM 判断 |
| M7 主动意图提示 | **Rule** | 模式匹配 + 通知，不需要 LLM |
| MCP Client | **Coding Agent**（tool 暴露，LLM 决策调用）+ **Rule**（安全审查） | MCP 工具由 LLM 自行决定调用，但调什么需白名单 |
| MCP Server | **Rule** | stdio JSON-RPC 消息循环，无 LLM 参与 |

你看，14 个模块中 **8 个用 Rule、6 个用 Prompt 注入、4 个用 Skill、3 个用 Coding Agent**（多选）。Rule 是最常用的机制——因为它零成本、零延迟、100% 确定。Coding Agent 只在真正需要"动态推理→执行→反馈"的地方使用。

这就是我们设计 OpenCopilot 的底层哲学：**能用规则不用模型，能注入 Prompt 不调 tool，能调 tool 不跑代码。只有前面三层都解决不了的问题，才交给 Coding Agent。**

### PG. 规则的泛化困境与三层孵化管道

上述哲学有一个显而易见的弱点：**规则的泛化能力最弱**。正则匹配内容推断能识别 `def foo():` 是代码，但它永远学不会"用户每次从 Figma 切过来时其实想做的是另一件事"。Rule 是手写的、静态的、无法自进化的。

但这个弱点不是 Rule 本身的问题——是**我们写了 Rule 之后把它忘了**。Rule 需要一套自我新陈代谢机制。

#### PG1. 核心思路：PatternLearner 作为 Rule 的孵化器

当前 PatternLearner（L6）只做意图预测——"用户在这个场景下可能选哪个 action_type"。把它往上抽象一层：

```
PatternLearner 不只是"预测意图"，而是"发现可规则化的行为模式"。
当某个模式置信度足够高 → 可提升为正式 Rule → 零成本、确定性执行。
当已有 Rule 的命中率持续走低 → 标记退化 → 降级回 PatternLearner 重新学习。
```

这就是 **Rule 的诞生与消亡循环**：统计发现 → 规则固结 → 命中监控 → 退化降级 → 重新学习。

#### PG2. Rule 的生命周期

```
                     PatternLearner 发现模式
                     （置信度 > 90%，样本 > 20）
                              │
                              ▼
                     ┌──────────────────┐
                     │  Rule Candidate   │  ← 建议规则，待用户确认
                     │  (存储于 rules.yml)│
                     └────────┬─────────┘
                              │ 用户确认（或自动满 50 样本）
                              ▼
                     ┌──────────────────┐
                     │  Active Rule      │  ← 生效中，零成本直接命中
                     │  (L1/L2/M7 等)    │
                     └────────┬─────────┘
                              │ 命中率持续 < 50%（7 天内）
                              ▼
                     ┌──────────────────┐
                     │  Degraded Rule    │  ← 标记退化，回退到 PatternLearner
                     │  (保留历史，写日志) │     观察新的模式
                     └──────────────────┘
```

#### PG3. 三个具体的 Rule 孵化场景

**场景 1：新的内容推断规则**

当前 CONTENT_SIGNATURES 只覆盖 code / debug / translate 三种。用户可能有自己的模式——比如"用户总是用日语写设计文档"。

```
PatternLearner 观测到:
  → 用户连续 15 次在 Figma 中选中含日语文本 → action_type=translate
  → 置信度 93%，样本量 15

系统自动生成 Rule Candidate:
  "figma_japanese": {
    "context": {"previous_app": ["Figma"], "lang_detect": "ja"},
    "intent": "translate"
  }

用户下次打开设置 → 隐私/规则面板 → 看到建议:
  "📊 系统发现: 你在 Figma 中选中日语文本时，93% 会使用翻译模式。
   要添加这条自动规则吗？[添加] [忽略]"
```

**场景 2：新的主动提示规则**

当前 M7 只有两条硬编码规则（浏览器→IDE + 报错 / 早上首次开 IDE）。规则永远不够。

```
PatternLearner 观测到:
  → 用户连续 8 天在 Terminal 中停留 > 30 分钟后 → 手动唤出卡片 → action_type=debug
  → 置信度 88%，样本 8

系统生成 Rule Candidate:
  "terminal_long_session": {
    "trigger": {"current_app": "Terminal", "duration": ">30min"},
    "suggestion": "你在 Terminal 工作很久了，需要帮忙排查问题吗？"
  }

用户收到通知:
  "💡 发现新模式: 你在终端长时间工作后常会排查问题，需要我主动提示吗？"
```

**场景 3：已有规则的退化检测**

```
当前 Rule: BROWSER→IDE + 剪贴板含 error → 主动提示 (M7)
  近 7 天命中：12 次触发 → 用户只采纳了 2 次（采纳率 16%）

系统标记退化:
  → PatternLearner 记录: 用户最近 7 天在 BROWSER→IDE 切换时
    剪贴板虽然含 error，但用户不再使用主动分析
  → 可能原因: 用户换了工作流、报错类型变了、用户学会了不需要 AI 帮忙
  
Rule 降级:
  → 从 Active Rule 退化为 Degraded Rule
  → PatternLearner 开始重新观察 "BROWSER→IDE + 报错" 现在的真实模式
  → 可能会发现新规则: "Chrome→VS Code + copilot 相关报错" 才是真正需要的触发条件
```

#### PG4. 最小实现：`RuleIncubator`

```python
# core/rule_incubator.py（~150 行，可集成到 PatternLearner 中）

import json
import os
from datetime import datetime, timedelta
from typing import Optional


class RuleIncubator:
    """
    Rule 的孵化与生命周期管理器。
    
    三层状态:
      candidate → active → degraded
    
    数据存储: ~/.asu_copilot/rules.json
    """
    
    def __init__(self):
        self.rules_path = os.path.expanduser("~/.asu_copilot/rules.json")
        self.rules = self._load()
        self.hit_log = {}  # rule_name → [(timestamp, hit/miss), ...]
    
    def suggest_candidate(self, pattern_key: str, pattern_data: dict, 
                          confidence: float, sample_count: int) -> Optional[dict]:
        """PatternLearner 发现高置信度模式 → 建议是否生成 Rule Candidate"""
        if confidence >= 0.9 and sample_count >= 20:
            return {
                "key": pattern_key,
                "data": pattern_data,
                "confidence": confidence,
                "samples": sample_count,
                "status": "candidate",
                "created": datetime.now().isoformat(),
                "auto_promote_at": sample_count + 30  # 再积累 30 个样本自动提升
            }
        return None
    
    def promote_to_active(self, rule_key: str):
        """用户确认（或样本达标）→ 提升为 Active Rule"""
        if rule_key in self.rules:
            self.rules[rule_key]["status"] = "active"
            self.rules[rule_key]["promoted_at"] = datetime.now().isoformat()
            self._save()
    
    def record_hit(self, rule_name: str, was_useful: bool):
        """记录一次 Rule 命中：用户是否采纳了这个规则的输出"""
        if rule_name not in self.hit_log:
            self.hit_log[rule_name] = []
        self.hit_log[rule_name].append((datetime.now(), was_useful))
        
        # 仅保留最近 7 天的记录
        cutoff = datetime.now() - timedelta(days=7)
        self.hit_log[rule_name] = [
            (t, h) for t, h in self.hit_log[rule_name] if t > cutoff
        ]
        
        # 检测退化
        if len(self.hit_log[rule_name]) >= 10:
            hit_rate = sum(1 for _, h in self.hit_log[rule_name] if h) / len(
                self.hit_log[rule_name]
            )
            if hit_rate < 0.5:
                self._degrade(rule_name, hit_rate)
    
    def _degrade(self, rule_name: str, hit_rate: float):
        """Rule 命中率持续走低 → 降级"""
        self.rules[rule_name]["status"] = "degraded"
        self.rules[rule_name]["degraded_at"] = datetime.now().isoformat()
        self.rules[rule_name]["last_hit_rate"] = hit_rate
        self._save()
        # 清除命中日志，让 PatternLearner 重新开始观察
        self.hit_log.pop(rule_name, None)
    
    def get_active_rules(self) -> list:
        """返回所有 Active 状态的规则（Rule 层加载使用）"""
        return [
            r for r in self.rules.values() 
            if r.get("status") == "active"
        ]
    
    def get_candidates_for_review(self) -> list:
        """返回所有 Candidate 状态的规则（UI 面板展示给用户确认）"""
        return [
            r for r in self.rules.values() 
            if r.get("status") == "candidate"
        ]
    
    def _load(self) -> dict:
        if os.path.exists(self.rules_path):
            with open(self.rules_path) as f:
                return json.load(f)
        return {}
    
    def _save(self):
        os.makedirs(os.path.dirname(self.rules_path), exist_ok=True)
        with open(self.rules_path, "w") as f:
            json.dump(self.rules, f, indent=2, ensure_ascii=False)
```

#### PG5. 与现有乐高模块的集成点

| 集成点 | 怎么集成 |
|--------|----------|
| **L1 内容推断** | CONTENT_SIGNATURES 字典从 `RuleIncubator.get_active_rules()` 动态加载，而非硬编码 |
| **M7 主动提示规则** | EVENT_RULES 列表从 `RuleIncubator.get_active_rules()` 动态加载 |
| **M2 Context Weaver** | 意图推断信号从 `RuleIncubator.get_active_rules()` 补充个性化规则 |
| **L6 PatternLearner** | 当 `predict()` 的置信度 > 0.9 且样本 > 20 → 调 `RuleIncubator.suggest_candidate()` |
| **L7 隐私面板** | 新增 "规则管理" 子面板，列出所有 Active/Candidate/Degraded 规则 |

#### PG6. 规则的社区共享（Phase 2）

单个用户的 PatternLearner 发现速度有限。如果 100 个 OpenCopilot 用户都在用，可以形成规则共享：

```
~/.asu_copilot/rules/
├── local.yml        # 个人规则（含个性化，不上传）
└── community.yml    # 社区规则包（下载的，只读）
```

社区规则包不包含个人数据——只包含泛化后的 Pattern → Intent 映射。比如 `{"BROWSER→IDE + error_clipboard": "debug"}`——这个规则对所有人都通用，不涉及隐私。

**这是 Rule 从"弱泛化"到"强泛化"的关键**：个人 PatternLearner 解决个性化 → 共性模式提取为社区 Rule 包 → 新用户开箱即用。

#### PG7. 为什么不做 Hermes 那样的自动 Skill 生成

这里必须澄清一个重要区别：Hermes 用 LLM 自动生成 Skill（Skill.md），我们的 Rule Incubator 用统计自动发现 Rule（rules.yml）。

两者的差异：

| 维度 | Hermes Skill 自动生成 | OpenCopilot Rule 孵化 |
|------|----------------------|----------------------|
| **发现方式** | LLM 自我评估："5+ tool call 的复杂任务应写 Skill" | 统计："用户在这个场景下 90% 选 code" |
| **产物格式** | SKILL.md（Markdown 指令文档） | rules.yml（键值规则） |
| **质量风险** | 高（LLM 幻觉可能生成错误 Skill） | 低（规则是统计推断，不会"编造"） |
| **成本** | 高（每次 Skill 创建都要调 LLM） | 零（纯统计，不收 Token） |
| **适用范围** | 复杂工作流（多步推理） | 确定性分类/预测（意图推断、主动提示） |

**结论**：Rule 孵化适合解决"可观测行为模式"的泛化问题——用户选了什么、从哪切到哪、什么时候唤出卡片。它是 PatternLearner 的自然延伸，而不是 Hermes 学习循环的复制品。

但规则有天花板——它是键值对，表达能力有限。当 PatternLearner 发现的行为模式超出了"预选 action_type"的范畴——比如"用户每次做 PR review 都要走 Coding Agent 分析 → 格式化 → 手动贴到 GitHub 这个五步操作"——规则无力表达这种多步工作流。这就是为什么需要 PG8。

### PG8. Skill 自动生成：沙盒 + 验证管道 + 原子 API 覆盖

> 规则解决 80% 的日常意图推断，Skill 解决剩下 20% 的复杂工作流。当前 7 个手写 Skill 够用，但随着 PatternLearner 积累数据，必然发现规则无法覆盖的模式。半自动 Skill 生成（AI 写代码框架 → 验证管道把关 → 人类确认 → staging 上线）是补充规则天花板的必要机制。

#### PG8.1 为什么规则不够用

```
规则能表达的:                     Skill 才能表达的:

用户在这个场景 → 选这个 action      用户在这个场景 → 走这 5 步操作
BROWSER→IDE + error → debug       1. 读 GitHub PR diff
Figma + 日语 → translate           2. Coding Agent 分析代码变更
Terminal 30min+ → debug_hint       3. 格式化审查结果
                                  4. 打开 GitHub PR 页面
                                  5. 贴入审查评论
```

规则是"单步决策"，Skill 是"多步工作流"。当 Rule Incubator 累积的样本显示某个模式已经稳定到可以用 Skill 固化时，就需要自动生成的能力。

#### PG8.2 整体流程：生成 → 验证 → 确认 → staging

```
Rule Incubator 发现模式稳定（置信度 > 90%，样本 > 30）
  且现有 7 个 Skill 无匹配
  且该模式涉及 ≥ 3 步 User Action（如: 唤出卡片 → 选 Coding → 复制结果 → 贴到 GitHub）
          │
          ▼
┌─────────────────────────────────────────────┐
│  Step 1: LLM 生成 Skill 代码框架             │
│  (注入 BaseSkill API 参考 + 样例 Skill)      │
│  输出: 完整的 Python 类文件                   │
└──────────────────────┬──────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐
│ 防线 1   │  │ 防线 2   │  │ 防线 3        │
│ AST 语法 │  │ 沙盒执行 │  │ Schema 校验   │
│ ast.parse│  │ 样例输入 │  │ SkillResult   │
│          │  │ 超时 5s  │  │ 字段完整性    │
└────┬─────┘  └────┬─────┘  └──────┬───────┘
     │             │              │
     └─────────────┼──────────────┘
                   │ 三道防线全过
                   ▼
          ┌──────────────────┐
          │ 防线 4: API 覆盖 │
          │ 生成的可通过哪些 │
          │ 端点组合验证？   │
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │ 防线 5: 冲突检查 │
          │ 与现有 Skill 的   │
          │ intents 重叠度    │
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │  用户审查 + 确认  │
          │  展示 diff + 测试 │
          │  结果 + API 链路  │
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │  Staging 注册     │
          │  仅当前 Session   │
          │  3 次使用后转正   │
          └──────────────────┘
```

#### PG8.3 防线详解

**防线 1：AST 语法检查（零成本，ms 级）**

```python
import ast

def validate_syntax(code: str) -> tuple[bool, str]:
    """AST 语法检查：不通过 → 退回 LLM 重新生成"""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"语法错误: {e.msg} at line {e.lineno}"
```

**防线 2：沙盒 dry-run（隔离执行，5s 超时）**

```python
import subprocess, tempfile, os

def sandbox_dry_run(code: str, test_input: dict) -> tuple[bool, str]:
    """在子进程中执行 Skill，超时 5s，崩溃不影响 Agent"""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
        f.write(code + f"\n\n# Test harness\n"
                f"import json, asyncio\n"
                f"skill = GeneratedSkill()\n"
                f"ctx = type('ctx', (), {{'intent': 'test', 'input_data': {test_input}}})()\n"
                f"result = asyncio.run(skill.execute(ctx))\n"
                f"print(json.dumps({{'success': result.success, 'data': str(result.data)[:500]}}))")
        temp_path = f.name
    
    try:
        result = subprocess.run(
            ["python3", temp_path], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0, result.stdout[:500] if result.returncode == 0 else result.stderr[:200]
    except subprocess.TimeoutExpired:
        return False, "沙盒超时: Skill 执行超过 5 秒"
    finally:
        os.unlink(temp_path)
```

**防线 3：Schema 校验（SkillResult 字段完整性）**

```python
def validate_skill_result(sample_output: dict) -> tuple[bool, str]:
    """确保 Skill 的返回值符合 SkillResult 的 schema"""
    required = {"success", "data"}
    missing = required - set(sample_output.keys())
    if missing:
        return False, f"SkillResult 缺少必填字段: {missing}"
    
    if not isinstance(sample_output.get("success"), bool):
        return False, "success 字段必须是 bool 类型"
    
    return True, ""
```

**防线 4：原子 API 覆盖宣言（每个 Skill 必须有对应的测试链路）**

这是你强调的核心——每个生成的 Skill 必须声明它可以通过哪些 API 端点组合来验证。Skill 生成时，LLM 同时输出一个 **API 覆盖宣言**：

```yaml
# 随 SKILL.md 一起生成的 api_coverage.yml
skill_name: pr_review
intents: [code_review, pr_analysis]
api_coverage:
  verify_chain:
    - endpoint: POST /v1/agent/sessions
      purpose: "创建新会话模拟 PR review 请求"
    - endpoint: POST /v1/agent/intent/detect
      purpose: "验证 PR diff 文本被正确推断为 code_review intent"
      expected: {"intent": "code_review", "confidence": {">=": 0.7}}
    - endpoint: POST /v1/agent/chat
      purpose: "发送 PR diff + 触发 Coding Agent 分析"
    - endpoint: POST /v1/agent/search/history
      purpose: "验证审查结果被正确记录到对话历史"
    - endpoint: POST /v1/agent/memory/search
      purpose: "验证审查工作流被提炼到记忆"
  regression:
    - "所有现有 Skill 的 intents 路由不受新 Skill 影响"
    - "IntentRouter 的 cache 命中率在新 Skill 注册后不下降 > 5%"
```

这个宣言同时是一份自动化测试脚本——CI 管道直接读取 `api_coverage.yml`，按 `verify_chain` 顺序调 API，逐个断言 `expected` 结果。任何一步失败 → Skill 不通过验证。

**防线 5：冲突检查（intents 重叠度）**

```python
def check_intent_conflict(new_skill_intents: list, existing_skills: dict) -> dict:
    """新 Skill 的 intents 和现有 Skill 的重叠度"""
    conflicts = {}
    for name, skill in existing_skills.items():
        overlap = set(new_skill_intents) & set(skill.metadata.intents)
        if overlap:
            conflicts[name] = {
                "overlapping": list(overlap),
                "ratio": len(overlap) / len(new_skill_intents)
            }
    
    total_overlap = sum(c["ratio"] for c in conflicts.values())
    return {
        "conflicts": conflicts,
        "total_overlap": total_overlap,
        "safe": total_overlap < 0.7  # 重叠度 < 70% 视为安全
    }
```

#### PG8.4 Staging 模式：三层晋升

```
Generated Skill 通过五道防线
  → Stage 1: Sandbox（仅当前 Session 可见）
      Agent 在本次对话中可调用
      对话结束 → 自动卸载
      用户主动说"保留这个 Skill" → 进入 Stage 2
  
  → Stage 2: Provisional（本地持久化，Feature Flag 标记为 experimental）
      用户连续 3 次使用且未手动关闭 → 进入 Stage 3
      任何一次崩溃 → 回退到 Stage 1，标记为 unstable
  
  → Stage 3: Active（正式注册到 SkillRegistry）
      表现与手写 Skill 完全一致
      API 覆盖宣言的回归测试加入 CI
```

#### PG8.5 与现有 Skill 体系的关系

自动生成的 Skill 和手写的 7 个 Skill 使用**完全相同的基类和接口**：

```python
# 生成的 Skill 同样继承 BaseSkill
class GeneratedPRReviewSkill(BaseSkill):
    def __init__(self):
        super().__init__(SkillMetadata(
            name="pr_review",
            display_name="PR Review Assistant",
            category="development",
            intents=["code_review", "pr_analysis"],
            tags=["github", "review", "automation", "generated"],
            is_generated=True  # ← 标记为自动生成
        ))
```

唯一的区别是 `is_generated=True`——这让 UI 和 SkillRegistry 能区分手写和生成的 Skill，用户可在设置中单独控制"是否启用 AI 生成的 Skill"。

#### PG8.6 API 覆盖率闭环：生成即验证

回到附录十的 34 个 Agent 端点设计——Skill 自动生成让这套 API 矩阵的价值翻倍：

```
手写 Skill（7 个）    → 34 个 API 端点 → 覆盖代码/知识/格式/PPT/评估
规则（L1/L2/M2/M7等）→ 34 个 API 端点 → 覆盖意图/安全/上下文/提示
生成 Skill（未来 N 个）→ 34 个 API 端点 → 同一条验证链，生成即测试
```

每一种能力扩展都走同一套 API 验证面。不是"先做功能再加测试"——是功能产出的同时，API 覆盖宣言就是测试。这也是为什么附录十的 34 个端点设计覆盖了所有乐高模块：它们不只是给手写代码用的测试面，也是给生成代码的验证基准。

#### PG8.7 实现优先级

```
Phase 1（依赖记忆 + 规则体系就位）:
  ├── 防线 1: AST 语法检查（1h）
  ├── 防线 2: 沙盒 dry-run（2h）
  └── 防线 3: Schema 校验（1h）

Phase 2（依赖 Phase 1 + PatternLearner 积累数据）:
  ├── 防线 4: API 覆盖宣言 + 自动验证（3h）
  ├── 防线 5: 冲突检查（1h）
  └── LLM 生成 Prompt 模板 + BaseSkill API 参考注入（2h）

Phase 3（依赖 Phase 2）:
  └── Staging 三层晋升 + 用户审查 UI（3h）
```

### PH. 规则与模型的深层协作：置信度校准台阶

上面的 Rule 孵化解决了"规则从哪来"的问题，但没解决更根本的一个矛盾：**规则确定性高但泛化弱，模型泛化强但确定性低——它们不应该是对手关系，而是接力关系。**

当前设计的问题是，Rule 和 LLM 之间是一条硬边界：匹配到规则就跳过 LLM，匹配不到就调用 LLM。这造成了两个问题：

1. **规则过度自信**：一个置信度 51% 的规则和置信度 99% 的规则被同等对待——都直接跳过 LLM。前者有 49% 的概率用错了。
2. **模型冷启动**：每次规则没匹配到就直接调 LLM，LLM 没有从规则的"部分匹配"中获得任何提示——即使规则已经缩小了可能性空间。

解决的思路是 **置信度校准台阶（Confidence-Calibrated Escalation Ladder）**——不为规则和模型之间划一条线，而是设四级台阶。

#### PH1. 四级台阶

```
用户选中文本 + 系统上下文
          │
          ▼
┌─────────────────────────────────────────────┐
│            Rule 层（多级输出）                │
│                                              │
│  每个规则不只是 true/false，而是输出:         │
│    {intent, confidence, evidence, suggestion} │
└──────────────────────┬──────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     confidence    confidence    confidence
      > 90%        60-90%       < 60%
          │            │            │
          ▼            ▼            ▼
    ┌─────────┐  ┌─────────┐  ┌──────────┐
    │ Level 0 │  │ Level 1 │  │ Level 2  │
    │ 直达    │  │ 预选+   │  │ LLM 判   │
    │ 零 Token │  │ 验证    │  │ 定       │
    └─────────┘  └────┬────┘  └────┬─────┘
                      │            │
                      ▼            ▼
                 ┌──────────────────────┐
                 │    LLM 最终判定       │
                 │    (看到规则候选 +    │
                 │     用户输入)        │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   反馈回路            │
                 │   Rule 采纳 → 加权重   │
                 │   Rule 驳回 → 减权重   │
                 │   LLM 新发现 → 候选规则 │
                 └──────────────────────┘
```

| 台阶 | 触发条件 | 行为 | Token 成本 | 确定性 |
|------|----------|------|:---:|:---:|
| **Level 0** | 规则置信度 > 90%，且该规则 7 天内未被 LLM 驳回 | 规则直接执行，不调 LLM | 零 | 极高（规则 + 历史验证双重保险） |
| **Level 1** | 规则置信度 60-90%，或 > 90% 但近 7 天有驳回记录 | 规则结果作为预选填入 UI + 作为候选注入 LLM Prompt。LLM 做最终判定 | 有（但 LLM 看到候选后推理更快） | 高（LLM 二次确认） |
| **Level 2** | 无规则匹配 或 置信度 < 60% | 全量交给 LLM。但将匹配度最高的前 3 个规则作为 "建议参考" 注入 Prompt | 全量 | 中（纯模型判定） |
| **Level X** | 所有规则置信度 < 30%，且过去 3 次相似场景 LLM 也低置信度 | 完全交给 LLM + 标记 "不确定性高"，UI 展示更多选项让用户选 | 全量 | 低（让用户决定） |

#### PH2. 关键：LLM 反馈校准规则权重

Level 1 是最关键的台阶——它让规则和 LLM 形成了**相互校准**的关系：

```
场景: 用户选中一段含 SQL 的文本

Rule 层输出:
  → code: 0.72 (匹配 def/class: 否; 匹配 SELECT/FROM/JOIN: 是)
  → translate: 0.55 (非中文为主)
  → top 候选: code (0.72, Level 1 触发)

LLM 收到:
  "用户选中了以下文本。系统初步判断这可能是一段代码(code,置信度72%)，
   或需要翻译(translate,置信度55%)。请做最终判定。
   
   文本内容: SELECT * FROM users WHERE status = 'active'"
  
LLM 判定:
  → "这是 SQL 查询语句，属于 code 类别"

反馈回路:
  → Rule 预测正确 → code 规则的 SQL 子模式权重 +0.1
  → 下次相似 SQL 文本 → code 置信度 0.82 → 仍 Level 1，但更接近 Level 0
  
  ├── 如果 LLM 连续 5 次确认该规则的同类预测 → 权重累积 → 升到 Level 0
  └── 如果 LLM 某次驳回 → 规则权重 -0.3 + 记录驳回案例到 PatternLearner
```

**反馈公式**（简单移动平均）：

```python
def calibrate_rule_weight(rule_name: str, pattern_key: str, 
                          rule_predicted: str, llm_confirmed: bool):
    """每次 LLM 确认或驳回后，更新规则的置信度权重"""
    rule = rules[rule_name]
    current = rule.get("calibrated_weight", rule.get("initial_weight", 0.7))
    
    if llm_confirmed:
        new_weight = current * 0.9 + 1.0 * 0.1  # 向 1.0 靠拢
    else:
        new_weight = current * 0.9 + 0.0 * 0.1  # 向 0.0 靠拢（但很慢）
    
    rule["calibrated_weight"] = new_weight
    rule["calibration_samples"] = rule.get("calibration_samples", 0) + 1
```

这个公式的含义是：**规则不是写死了就定了，它的有效权重随着 LLM 的每一次确认或驳回在缓慢漂移。** 确认多了 → 权重升 → 最终进入 Level 0（零 Token）。驳回多了 → 权重降 → 退到 Level 2（交给 LLM 判定）。

#### PH3. Rule Incubator 与校准台阶的关系

Rule Incubator（PG4）和校准台阶（PH）是两个正交的维度：

```
                    Incubator 决定"有没有规则"
                    ─────────────────────────
                    候选 → 活跃 → 退化

                    校准台阶 决定"怎么用规则"
                    ─────────────────────────
                    Level 0 → Level 1 → Level 2
```

一条规则可以从 Incubator 提升为 Active，同时因为缺乏校准样本而起始于 Level 1。随着 LLM 持续确认，它在校准台阶上升至 Level 0。当用户行为变化导致 LLM 开始驳回时，它在校准台阶下降回 Level 1，最终可能退化（Incubator 降级）。

**两条管线各管各的，但在同一个规则对象上交叉运行。**

#### PH4. 成本自适应策略

校准台阶还可以响应外部约束——API 额度、网络延迟、用户偏好：

```python
def get_effective_thresholds(cost_policy: str) -> dict:
    """根据当前成本策略调整台阶阈值"""
    defaults = {"level0": 0.90, "level1": 0.60}
    
    if cost_policy == "aggressive_save":
        # API 额度紧张 → 更激进用规则
        return {"level0": 0.75, "level1": 0.45}
    elif cost_policy == "calibration_mode":
        # 配额充裕 → 更激进用 LLM（收集校准数据）
        return {"level0": 0.95, "level1": 0.70}
    
    return defaults
```

成本自适应不是用户手动调的——系统根据 API 用量自动切换。比如本月底还剩 80% 配额 → `calibration_mode`，多调 LLM 校准规则。只剩 10% → `aggressive_save`，能省则省。

#### PH5. Broker 上下文对校准台阶的增强

校准台阶的输入不只是"选中文本"，而是 Context Weaver 的完整快照。这意味着同一个文本在不同场景下可以走不同的台阶：

```
选中文本: "ERROR: Connection refused"
  
场景 A: 用户在 Terminal（当前活跃）, 刚从 VS Code 切过来
  → Rule 层看到: 文本含 error + 当前 app = Terminal + prev_app = VS Code
  → 综合置信度: 0.94 → Level 0 直达，跳过 LLM，直接判定为 debug

场景 B: 用户在 Chrome（当前活跃）, 正在浏览 GitHub Issue
  → Rule 层看到: 文本含 error + 当前 app = Chrome
  → 综合置信度: 0.65 → Level 1，预选 debug 但让 LLM 二次确认
  → LLM 可能判定: "用户在浏览器看 Issue，可能想搜索这个错误而非修代码"

场景 C: 用户在微信（当前活跃）, 聊天中
  → Rule 层看到: 文本含 error + 当前 app = 微信
  → 综合置信度: 0.40 → Level 2，全量交给 LLM
```

**伴生数据不只是多了一种信号——它让同一个规则在不同上下文中有不同的置信度。** 这是纯文本规则做不到的，也是 OpenCopilot 独有的能力。

#### PH6. 校准台阶在整个体系中的位置

回到附录十一 §PD 的四层架构，校准台阶在 **Rule 层和 Prompt 注入层之间的边界**上工作：

```
Rule 层（门控）
  │
  │  校准台阶位于这里——决定"过还是不过"
  │  ├── Level 0: 不过（规则直接执行，不惊动下游）
  │  ├── Level 1: 部分过（规则预选 + LLM 二次确认）
  │  └── Level 2: 完全过（交给 LLM 全权判定）
  │
Prompt 注入层
  │
Skill 层
  │
Coding Agent
```

这就是对"规则高确定弱泛化 × 模型低确定强泛化"这一矛盾的根本解法：**不为两者划硬边界，而是让它们在同一个连续台阶上协作——规则给出带置信度的先验，模型做出最终判定，判定的结果反过来校准规则的置信度。规则从模型中学习泛化，模型从规则中获得提速。**

---

# 附录十二：MCP 协议集成设计

> MCP 是 OpenCopilot 从"桌面内闭环"通向"生态系统连接"的桥梁。当前 OpenCopilot 的 7 个 Skill + Broker 探针全部是内建能力——Agent 无法连接外部数据库、第三方 API、或者其他 AI 工具。MCP 分为两个方向：MCP Client（Agent 调用外部工具）和 MCP Server（OpenCopilot 对外暴露独有能力）。

## PA. 为什么是现在：MCP 的战略定位

OpenClaw、Hermes、WorkBuddy 三家都已有 MCP 支持。但我们不做 MCP 的理由不是"我们没有他们需要的东西"——恰恰相反：

| OpenCopilot 的独有能力 | 当前只能通过 | 有了 MCP Server 后 |
|------------------------|------------|-------------------|
| 知识图谱（264 实体 + 166 关系） | 右键卡片内 Agent 使用 | Claude Code / Cursor 也能查询项目结构 |
| 伴生记忆（L2+L3） | 右键卡片内 Agent 读取 | 任何 MCP 兼容工具都能检索你的工作记忆 |
| Broker 系统探针 | 仅 OpenCopilot 内部消费 | 外部 AI 工具可获取当前应用、选区、DOM |
| 对话历史（FTS5） | SQLite 内部查询 | 其他 AI 工具可搜索你的对话记录 |

**MCP 是 OpenCopilot 从"被使用"到"被依赖"的转折点**——别人的工具开始依赖你的数据。

同时，MCP Client 补齐 OpenCopilot 最大的结构性弱点：**我们只能操作本机文件和浏览器 DOM，无法连接外部世界。**

## PB. MCP Client：Agent 调用外部工具

### PB1. 架构

```
Agent (asu_custom_agent.py)
  │
  ├── 内建工具（当前 6 个 tool）
  │   ├── execute_command
  │   ├── read_file / write_file
  │   ├── search_history
  │   ├── memory_search
  │   └── web_search (SearXNG)
  │
  └── 🆕 MCP Client 桥接层
      │
      ├── MCP Server: Linear (Issue 管理)
      ├── MCP Server: PostgreSQL (数据库查询)
      ├── MCP Server: GitHub (PR/Issue/Repo 管理)
      ├── MCP Server: Slack (消息发送)
      └── MCP Server: 自定义 (任何 MCP 兼容服务)
```

### PB2. 最小实现

```python
# tools/mcp_client.py（~150 行，新增文件）

import json
import subprocess
from typing import Optional

class MCPClientBridge:
    """
    MCP Client 桥接层。
    
    MCP 协议的核心是 JSON-RPC over stdio/sse。
    Client 启动 MCP Server 进程 → 通过 stdin/stdout 发送 JSON-RPC 调用。
    
    支持的传输方式:
      - stdio: 启动本地进程，通过标准输入/输出通信
      - sse: HTTP SSE 长连接（远程 MCP Server）
    """
    
    def __init__(self, mcp_config_path="~/.asu_copilot/mcp_servers.json"):
        self.config_path = os.path.expanduser(mcp_config_path)
        self.servers = {}       # server_name → subprocess.Popen
        self.capabilities = {}  # server_name → {"tools": [...], "resources": [...]}
        self._load_config()
    
    def _load_config(self):
        """加载 MCP Server 配置，格式与 Claude Desktop / Cursor 兼容"""
        if os.path.exists(self.config_path):
            with open(self.config_path) as f:
                self._config = json.load(f).get("mcpServers", {})
    
    def start(self):
        """Agent 启动时初始化所有配置的 MCP Server（懒加载：首次 tool_call 时才启动）"""
        pass  # 懒加载，不阻塞 Agent 启动
    
    def _ensure_server(self, name: str) -> bool:
        """确保 MCP Server 进程已启动"""
        if name in self.servers and self.servers[name].poll() is None:
            return True  # 已在运行
        
        conf = self._config.get(name, {})
        cmd = conf.get("command", "")
        args = conf.get("args", [])
        
        try:
            self.servers[name] = subprocess.Popen(
                [cmd] + args,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True
            )
            # 初始化握手: initialize → initialized
            self._send_json_rpc(name, "initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "OpenCopilot", "version": "2.0"}
            })
            # 获取工具列表: tools/list
            resp = self._send_json_rpc(name, "tools/list", {})
            self.capabilities[name] = resp.get("result", {}).get("tools", [])
            return True
        except Exception as e:
            logger.error(f"Failed to start MCP server '{name}': {e}")
            return False
    
    def get_tool_schemas(self) -> list:
        """返回所有已连接 MCP Server 的 tool schema，供 Agent 的 tool-calling 使用"""
        schemas = []
        for name in self._config:
            if self._ensure_server(name):
                tools = self.capabilities.get(name, [])
                for tool in tools:
                    tool["mcp_server"] = name  # 标记来源
                    schemas.append(tool)
        return schemas
    
    def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        """调用 MCP 工具"""
        if not self._ensure_server(server_name):
            return json.dumps({"error": f"MCP Server '{server_name}' not available"})
        
        resp = self._send_json_rpc(server_name, "tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if "error" in resp:
            return json.dumps(resp["error"])
        return json.dumps(resp.get("result", {}).get("content", []))
    
    def _send_json_rpc(self, server_name: str, method: str, params: dict) -> dict:
        """发送 JSON-RPC 请求并接收响应"""
        proc = self.servers[server_name]
        request = json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": method, "params": params
        })
        proc.stdin.write(request + "\n")
        proc.stdin.flush()
        response_line = proc.stdout.readline()
        return json.loads(response_line)
```

### PB3. 配置格式（与 Claude Desktop / Cursor 兼容）

```json
// ~/.asu_copilot/mcp_servers.json
{
  "mcpServers": {
    "linear": {
      "command": "npx",
      "args": ["-y", "@linear/mcp-server"],
      "env": {"LINEAR_API_KEY": "xxx"}
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-postgres"],
      "args": ["postgresql://localhost/mydb"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-github"],
      "env": {"GITHUB_TOKEN": "xxx"}
    }
  }
}
```

### PB4. Agent 注入点

```python
# asu_custom_agent.py → tool-calling 初始化时

mcp_client = MCPClientBridge()

def build_all_tool_schemas():
    """合并内建 tools + MCP tools，生成完整的 tool schema 列表"""
    built_in = TOOLS  # 6 个内建 tool
    mcp_tools = mcp_client.get_tool_schemas()
    return built_in + mcp_tools

def execute_tool(name: str, args: dict) -> str:
    """统一 tool 执行：先查内建，再查 MCP"""
    # 内建工具
    if name == "execute_command":
        return _execute_command(args["command"])
    elif name == "search_history":
        return json.dumps(memory.search_history(args["query"]))
    elif name == "web_search":
        return _searxng_search(args["query"])
    
    # MCP 工具
    for server_name, tools in mcp_client.capabilities.items():
        if name in [t["name"] for t in tools]:
            return mcp_client.call_tool(server_name, name, args)
    
    return json.dumps({"error": f"Unknown tool: {name}"})
```

---

## PC. MCP Server：OpenCopilot 对外暴露独有能力

### PC1. 暴露的能力矩阵

| 资源 (Resource) | 底层来源 | 对 AI 工具的价值 |
|-----------------|----------|-----------------|
| `ocp://knowledge/entity/{name}` | 知识图谱 | Claude Code 查项目架构 |
| `ocp://knowledge/related/{name}` | 知识图谱关系查询 | Cursor 理解代码依赖 |
| `ocp://memory/today` | 今日日志 L2 | 其他 AI 工具了解你今天的上下文 |
| `ocp://memory/search?q={query}` | 记忆搜索 | 跨工具检索工作记忆 |
| `ocp://system/frontmost` | Broker 探针 | 其他 AI 工具知道你现在在什么应用 |
| `ocp://system/selection` | Broker 选区提取 | 其他 AI 工具读取你选中的文本 |
| `ocp://history/search?q={query}` | FTS5 对话搜索 | 其他 AI 工具搜索你与 Agent 的对话 |

| 工具 (Tool) | 功能 | 对 AI 工具的价值 |
|------------|------|-----------------|
| `ocp.memory.remember` | 写入长期记忆 | 其他 AI 工具代你记录偏好 |
| `ocp.browser.dom` | 读取浏览器 DOM | 其他 AI 工具获取网页内容 |
| `ocp.knowledge.query` | 知识图谱查询 | 结构化项目知识检索 |

### PC2. 最小实现

```python
# tools/mcp_server.py（~200 行，新增文件）

import json
import sys
from typing import Any

# MCP Server 的 JSON-RPC 消息循环
# 启动方式: python tools/mcp_server.py
# Claude Desktop / Cursor / Codex 配置中指定此脚本为 MCP Server

HANDLERS = {}

def handle(method: str):
    """装饰器：注册 JSON-RPC method 处理器"""
    def decorator(func):
        HANDLERS[method] = func
        return func
    return decorator

@handle("initialize")
def handle_initialize(params: dict) -> dict:
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {},
            "resources": {"subscribe": False}
        },
        "serverInfo": {
            "name": "OpenCopilot Memory & Knowledge Bridge",
            "version": "1.0"
        }
    }

@handle("tools/list")
def handle_tools_list(params: dict) -> dict:
    return {
        "tools": [
            {
                "name": "ocp_knowledge_entity",
                "description": "查询 OpenCopilot 知识图谱中的实体。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "实体名称"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "ocp_memory_today",
                "description": "读取 OpenCopilot 今日记忆日志。",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "ocp_memory_remember",
                "description": "写入长期记忆。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "fact": {"type": "string", "description": "要记住的事实"}
                    },
                    "required": ["fact"]
                }
            },
            {
                "name": "ocp_system_frontmost",
                "description": "获取用户当前正在使用的应用名称。",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]
    }

@handle("tools/call")
def handle_tools_call(params: dict) -> dict:
    name = params.get("name", "")
    args = params.get("arguments", {})
    
    if name == "ocp_knowledge_entity":
        from knowledge_graph.query import QueryEngine
        entities = QueryEngine().find_entity(args["name"])
        return {"content": [{"type": "text", "text": json.dumps(
            [e.to_dict() for e in entities[:5]], ensure_ascii=False
        )}]}
    
    elif name == "ocp_memory_today":
        today_path = os.path.expanduser(f"~/.asu_copilot/memory/{datetime.now().strftime('%Y-%m-%d')}.md")
        if os.path.exists(today_path):
            with open(today_path) as f:
                content = f.read()[:3000]
        else:
            content = "今日暂无日志。"
        return {"content": [{"type": "text", "text": content}]}
    
    elif name == "ocp_memory_remember":
        mem_path = os.path.expanduser("~/.asu_copilot/memory/MEMORY.md")
        os.makedirs(os.path.dirname(mem_path), exist_ok=True)
        with open(mem_path, "a") as f:
            f.write(f"\n- {args['fact']} ← {datetime.now().strftime('%Y-%m-%d')} (via MCP)\n")
        return {"content": [{"type": "text", "text": f"已记住: {args['fact']}"}]}
    
    elif name == "ocp_system_frontmost":
        import subprocess
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of first application process whose frontmost is true'],
            capture_output=True, text=True, timeout=3
        )
        app = result.stdout.strip()
        return {"content": [{"type": "text", "text": f"当前活跃应用: {app}"}]}
    
    return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}

# JSON-RPC 主循环
def main():
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            method = request.get("method", "")
            params = request.get("params", {})
            req_id = request.get("id")
            
            if method == "notifications/initialized":
                continue
            
            handler = HANDLERS.get(method)
            if handler:
                result = handler(params)
                response = {"jsonrpc": "2.0", "id": req_id, "result": result}
            else:
                response = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
            
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
```

### PC3. 配置方式（用户视角）

```json
// Claude Desktop 的 claude_desktop_config.json 中
{
  "mcpServers": {
    "opencopilot": {
      "command": "python3",
      "args": ["~/Documents/trae_projects/OpenCopilot/tools/mcp_server.py"]
    }
  }
}
```

或在 Cursor 中：
```json
// .cursor/mcp.json
{
  "mcpServers": {
    "opencopilot": {
      "command": "python3",
      "args": ["tools/mcp_server.py"],
      "cwd": "/path/to/OpenCopilot"
    }
  }
}
```

---

## PD. MCP 与现有乐高模块的协同

### PD1. MCP + PG8 (Skill 自动生成)

这是 MCP 的杀手级场景。有了 MCP Client，自动生成的 Skill 不只是纯 Python 逻辑，而是 **"编排 MCP 工具调用的工作流"**：

```python
# 自动生成的 Skill 内部调用 MCP 工具

class GeneratedIssueTrackerSkill(BaseSkill):
    async def execute(self, context):
        # 1. 分析代码中的 TODO/FIXME
        analysis = await self.code_agent.analyze(context.input_data["code"])
        
        # 2. 通过 MCP 在 Linear 中创建 Issue
        mcp_result = mcp_client.call_tool("linear", "create_issue", {
            "title": f""Fix: {analysis['issue_summary']}",
            "description": analysis["detail"],
            "priority": analysis["severity"]
        })
        
        # 3. 记录到记忆
        memory.remember(f"为 {analysis['file']} 创建了 Linear issue: {mcp_result['id']}")
        
        return SkillResult(success=True, data={"issue_url": mcp_result["url"]})
```

**Skill 自动生成的 Prompt 模板需要注入可用的 MCP 工具列表**，让 LLM 在生成代码时直接引用这些工具。

### PD2. MCP Server + 伴生记忆

其他 AI 工具通过 MCP 读取 OpenCopilot 的记忆，形成一个"跨工具的记忆总线"。你在 Claude Code 中写代码时，Claude Code 通过 MCP 查询 OpenCopilot 的记忆，知道"用户偏好 Python 3.11"、"正在修 Broker 的空指针"——不需要你重新解释。

### PD3. MCP + API 覆盖率

MCP 的 tool-call 和 resource-read 都可以走附录十的 34 个端点验证面。`api_coverage.yml` 中加入 MCP 验证链：

```yaml
api_coverage:
  mcp_verify_chain:
    - mcp_tool: ocp_knowledge_entity
      params: {"name": "Broker"}
      expected: {"entities[0].name": "Broker"}
    - mcp_tool: ocp_memory_today
      params: {}
      expected: {"content": "not_empty"}
```

---

## PE. MCP 的"不做"边界

| 不做的 | 理由 |
|--------|------|
| **不实现完整的 MCP Resource 订阅** | 当前版本只做 tools + basic resources，不做 `resources/subscribe` 推送 |
| **不内置 MCP Server 进程常驻** | MCP Server 由外部工具按需启动（stdio 模式），OpenCopilot 不需要常驻一个 MCP Server 进程 |
| **不做 MCP 的远程暴露** | `mcp_server.py` 只监听 stdin/stdout，不开放网络端口——安全性优先 |
| **MCP Client 不做自动发现** | 需要用户在 `mcp_servers.json` 中显式配置——避免 Agent 被第三方 MCP Server 劫持 |

---

## PF. 实现优先级与工时

| Phase | 内容 | 工时 | 依赖 |
|-------|------|------|------|
| MCP Phase 1 | MCP Client 基础框架（启动进程 + JSON-RPC + tool schema 合并） | 4h | 无 |
| MCP Phase 2 | MCP Server（暴露知识图谱 + 记忆 + 前台应用） | 3h | 记忆体系 + 知识图谱就位 |
| MCP Phase 3 | PG8 Skill 生成 Prompt 中加入 MCP 工具列表 | 2h | PG8 就位 |
| MCP Phase 4 | API 覆盖宣言的 MCP 验证链 | 2h | 附录十 API 矩阵就位 |

**总计 11 工时，P1 优先级**。与所有乐高模块无依赖关系——可以先做 MCP Client 让 Agent 连接外部工具，再做 MCP Server 让外部工具连接 OpenCopilot。

---

# 附录十三：可执行优先级总表

> 这是从设计到代码的最终交付清单。每个模块都是独立乐高——按此表顺序执行或自由组合均可。上半表是必选基建，下半表是可选增强。

## 十三A. P0 必选基建（做完后 Agent 具备基础记忆 + 搜索能力）

| # | 模块 | 文件 | 改/新增 | 工时 | API 端点 | 完成标准 |
|---|------|------|:---:|------|----------|----------|
| P0-1 | L1 内容意图推断 | `smart_copilot.py` L2838 | 改 +60 | 2h | POST `/v1/agent/intent/detect` | curl 提交代码文本 → 返回 `{"intent":"code","confidence":0.85}` |
| P0-2 | L5 分层 Prompt | `asu_custom_agent.py` L474 | 改 +40 | 1.5h | GET `/v1/agent/prompt/stats` | stable 层同一 Session 只构建 1 次，终端打印 `[Cache] stable层命中` |
| P0-3 | M1 三层记忆体系 | `asu_custom_agent.py` + 新建 `memory/` | 改 + 新 +200 | 2.5d | /v1/agent/memory/{remember,search,today,forget,summarize,status,invalidate} | curl 对话 → memory/today 含提炼摘要；次日唤醒引用昨天摘要 |
| P0-4 | L4 FTS5 对话搜索 | `asu_custom_agent.py` L323 | 改 +50 | 2h | POST/GET `/v1/agent/search/history` | curl 搜"空指针" → 命中三个月前的对话 |
| P0-5 | L2 注入安全扫描 | `asu_custom_agent.py` build_context_prefix | 改 +50 | 1h | POST `/v1/agent/security/scan` | browser 来源含 "ignore all instructions" → 截断标记 |
| P0-6 | M2 Context Weaver | `smart_copilot.py` L772 | 改 +50 | 3h | GET `/v1/agent/context/weaver` | Chrome→VS Code → 终端打印 `debug intent, confidence 0.7` |
| P0-7 | L3 知识图谱隐式注入 | `asu_custom_agent.py` do_POST | 改 +40 | 1.5h | POST `/v1/agent/kg/inject` | 对话"Broker 的 WebSocket" → KG 关联自动注入 System Prompt |

**P0 小计：7 模块 · ~490 行 · ~4 天 · 0 个新文件（memory/ 目录内全部新文件） · 通过 34+ API 端点验证**

做完后 OpenCopilot 具备：跨天记忆 + 全文搜索 + 分层缓存 + 安全扫描 + 上下文编织 + 知识图谱隐式注入。

---

## 十三B. P1 能力增强（做完后 Agent 能自主执行 + 联网搜索 + 外部工具连接）

| # | 模块 | 文件 | 改/新增 | 工时 | API 端点 | 完成标准 |
|---|------|------|:---:|------|----------|----------|
| P1-1 | M4 Cron 调度器 | 新建 `agent_scheduler.py` | 新 +80 | 3h | /v1/agent/cron{,,/{id},/trigger/{id}} | curl 添加 08:00 任务 → 手动触发 → 检查早报已生成 |
| P1-2 | tool-calling loop | `asu_custom_agent.py` 新增端点 | 改 +60 | 3h | POST `/v1/agent/task` | curl POST task 端点 → Agent 调 tool → 看结果 → 再推理 → 返回最终文本 |
| P1-3 | 代码执行沙盒 | `asu_custom_agent.py` + 子进程隔离 | 改 +40 | 2h | 内建 tool `execute_command` | `execute_command("rm -rf /")` → `[Blocked]`; `execute_command("pytest")` → 通过 |
| P1-4 | Provider 故障转移 | `llm_provider.py` | 改 +30 | 1.5h | — (内部逻辑) | 主 Provider 返回 429 → 自动切备选 → 终端打印 `[Failover]` |
| P1-5 | M5 SearXNG 搜索 | 新建 `tools/web_search.py` + Docker | 新 +60 | 4h | POST `/v1/agent/search/web` + GET status | curl 搜"Python 3.14" → 返回 3 条搜索结果摘要 |
| P1-6 | MCP Client | 新建 `tools/mcp_client.py` | 新 +160 | 4h | /v1/agent/mcp/{servers,refresh,{s}/tools,{s}/call} | 配置 GitHub MCP Server → Agent tool_call "create_issue" → 成功创建 |
| P1-7 | M3 右键卡片感知化 | `smart_copilot.py` trigger_ai | 改 +40 | 2h | — (UI 交互) | Chrome→VS Code + 唤出卡片 → 卡片前缀含"刚从 Chrome 切过来" |
| P1-8 | L6 PatternLearner | 新建 `core/pattern_learner.py` | 新 + SM 改 | 3h | /v1/agent/patterns/{record,predict,stats} | 连续 3 天 Chrome→VS Code + code → 第 4 天自动预测 code |

**P1 小计：8 模块 · ~470 行 · ~22.5h (~3 天) · 3 个新文件 · 通过 10+ API 端点验证**

做完后 OpenCopilot 具备：自主定时执行 + 工具循环 + 安全沙盒 + 故障转移 + 联网搜索 + 外部 MCP 工具 + 卡片场景感知 + 个人化学习。

---

## 十三C. P2 体验扩展（做完后 OpenCopilot 从"能用"到"好用"）

| # | 模块 | 文件 | 改/新增 | 工时 | API 端点 | 完成标准 |
|---|------|------|:---:|------|----------|----------|
| P2-1 | 事件驱动触发器 | `smart_copilot.py` _on_app_activated | 改 +35 | 2h | POST `/v1/agent/intent/proactive` | Chrome→VS Code + 剪贴板含报错 → 桌面通知弹出 |
| P2-2 | M6 多任务面板 | 新建 `widgets/task_panel.py` | 新 +300 | 4d | /v1/agent/sessions + /session/{id}/{archive,delete,rename} | 三击右键 → 多卡片网格 → 新建/切换/归档 |
| P2-3 | MCP Server | 新建 `tools/mcp_server.py` | 新 +200 | 3h | stdio JSON-RPC | Claude Desktop 配置 MCP → 可查 OpenCopilot 知识图谱 + 今日记忆 |
| P2-4 | PG4 Rule Incubator | 新建 `core/rule_incubator.py` | 新 +150 | 3h | — (内建于 L6 + API) | PatternLearner 置信度 > 90% + 20 样本 → rules.json 中生成 candidate |
| P2-5 | PG8 Skill 半自动生成 | `asu_custom_agent.py` + 防线模块 | 改 + 新 +200 | 1d | — (防线内建 + SkillRegistry 注册) | Rule Incubator 触发 → LLM 生成代码 → 五道防线全过 → staging 注册 |
| P2-6 | L7 隐私面板 | 新建 `widgets/privacy_dashboard.py` | 新 +50 | 2h | GET `/v1/agent/privacy/stats` | 设置 → 隐私 tab → 展示今日 LLM 请求数/记忆条数/本地化 100% |
| P2-7 | 渐进式 Skill 加载 | `skill_architecture/registry.py` | 改 +40 | 1.5h | — (内部逻辑) | System Prompt 仅含 Skill 一行描述，完整 SKILL.md 通过 tool_call 按需拉取 |
| P2-8 | 记忆向量语义搜索 | `memory/` 目录 + embedding | 新 + 改 +80 | 1d | — (替换关键词匹配) | "那个关于架构设计的讨论" → 语义命中 "三层记忆体系" 而非仅靠关键词 |

**P2 小计：8 模块 · ~1055 行 · ~9 天 · 4 个新文件 · 通过 10+ API 端点验证**

---

## 十三D. 不做（主动选择）

| 模块 | 理由 |
|------|------|
| 多消息渠道（Telegram/WhatsApp） | OpenCopilot 是桌面内生工具——你在桌面，AI 就在手边。不需要手机通知 |
| Skill 全自动生成上线（Hermes 模式） | 代码类 Skill 无人审查即上线，质量风险不可接受 |
| RL 训练管线 | 学术方向，非桌面工具该做的事 |
| 语音交互 | 桌面办公打字更精准私密，边际收益低 |

---

## 十三E. 三条推荐组装路线

不需要按 P0→P1→P2 串行。选一条金线开始，每条金线的模块都零依赖：

```
金线 A：让 AI 更懂当前场景（2 天）
  L1 内容推断 → L3 知识图谱注入 → M2 Context Weaver → M3 卡片感知化 → L6 PatternLearner

金线 B：让 AI 记住一切（3 天）
  M1 三层记忆 → L5 分层 Prompt → L4 FTS5 搜索 → L2 注入扫描 → L7 隐私面板

金线 C：让 AI 能独立做事（3 天）
  M4 Cron → tool-calling loop → 代码沙盒 → M5 搜索 → MCP Client → Provider 故障转移
```

---

## 十三F. 乐高独立性校验

| 模块 | 只有这些硬依赖 | 如果依赖未就位 |
|------|-------------|--------------|
| L1 内容推断 | 无 | — |
| L2 注入扫描 | 无 | — |
| L3 知识图谱注入 | `knowledge_graph/` 目录存在 | 静默跳过 KG 注入，Prompt 无 KG 层 |
| L4 FTS5 搜索 | SQLite 3.9.0+ | try/except → 静默跳过，不影响对话 |
| L5 分层 Prompt | 无 | — |
| L6 PatternLearner | 无（数据积累自然发生） | `self.pattern_learner` 为 None → 不预测 |
| L7 隐私面板 | UI 框架 PyQt6 | ImportError → 设置窗口无隐私 tab |
| M1 三层记忆 | 无（L1 SQLite 已有，L2/L3 纯文件） | 文件不存在 → 返回空，无记忆注入 |
| M2 Context Weaver | BrokerEventsWorker 已连接 | context_snapshot 为空 → 退化为旧逻辑 |
| M3 右键卡片感知化 | M2（读 context_snapshot） | 快照为空 → 退化为旧 context_prefix |
| M4 Cron | `schedule` 库 (pip install) | import 失败 → 不启动调度器 |
| M5 联网搜索 | Docker 运行的 SearXNG 实例 | 不可达 → tool 返回 "搜索服务不可用" |
| M6 多任务面板 | PyQt6 | 独立 Widget，其他 tab 不受影响 |
| M7 主动提示 | M2 + L6 | 快照为空或 PatternLearner 未就位 → 不弹通知 |
| PG4 Rule Incubator | L6（数据来源） | patterns 文件为空 → 无 candidate |
| PG8 Skill 自动生成 | PG4 + 沙盒 + 防线 1-3 | 沙盒不可用 → 不触发生成 |
| MCP Client | `mcp_servers.json` 存在 + MCP Server 进程可达 | 文件不存在/MCP Server 起不来 → tool schema 列表仅含内建 tool |
| MCP Server | 外部工具调用 | 无人调用 → `mcp_server.py` 不启动，零资源消耗 |
| Provider 故障转移 | 多个 API Key 配置 | 单 Key → 退化为单 Provider 模式 |
| 代码沙盒 | `subprocess` (Python 标准库) | — |
| tool-calling loop | LLM Provider 支持 tool_call 响应格式 | 不支持 → 退化为纯文本回复 |
| 渐进式 Skill 加载 | SkillRegistry 已有 | — |
| 向量语义搜索 | embedding 模型或 API | 不可用 → 退化为关键词匹配 |

---

## 十三G. API 覆盖率收盘检查

| 维度 | 现有端点 | 新增端点 | 总计 | 覆盖乐高模块 |
|------|:---:|:---:|:---:|------|
| Agent (18888) | 2 | 38 | 40 | 全部 L1-L7, M1-M7, PG4, PG8, MCP, 全局 |
| Broker (18889) | 16 | 0 | 16 | 系统探针完整 |
| Platform (8089) | 15 | 1 | 16 | 上下文管理 + 动作执行 |
| API (8088) | 60 | 0 | 60 | 现有 Skill 完整 |
| KG (8090) | 26 | 0 | 26 | 知识图谱完整 |
| **总计** | **119** | **+38** | **157** | **100%** |