# OpenCopilot 开发指南

> 版本 v4.0 | 2026-06-04

---

## 一、开发环境

### 1.1 前置要求

| 项目 | 要求 |
|------|------|
| OS | macOS 12+ |
| Python | 3.10+ |
| 权限 | 辅助功能 + 屏幕录制 |
| 依赖 | `pip install -r requirements.txt` 或 `pip install -e ".[all]"` |

### 1.2 启动开发环境

```bash
# 终端 1：API Gateway（内嵌 Agent Pipeline，支持热重载）
uvicorn smart_copilot_api:app --host 0.0.0.0 --port 8000 --reload

# 终端 2：Broker（需要 macOS 原生终端）
python opencopilot/broker/run.py

# 终端 3：UI
python smart_copilot.py

# 终端 4：运行测试
python -m pytest tests/ -v
```

---

## 二、代码组织

### 2.1 调用链条

```
用户交互 (PyQt6 GUI)
    │
    ├── smart_copilot.py
    │   └── AIWorker.run() → call_agent_pipeline_sync()
    │
    ▼
opencopilot/agent/caller.py  ← 唯一 AI 调用入口
    │
    ▼
opencopilot/agent/pipeline.py → MiddlewarePipeline.execute()
    │
    ▼
opencopilot/agent/middlewares.py (7 层)
    ├── SessionSetupMiddleware       → 会话初始化
    ├── SecurityGuardMiddleware      → 权限 + 限流
    ├── ImmuneSystemMiddleware       → 内容安全 + 危险命令检测
    ├── PlannerMiddleware            → 任务规划
    ├── StateTrackingMiddleware      → 状态追踪
    ├── CapabilityRouterMiddleware   → 能力路由
    └── LLMProviderMiddleware        → Agent Loop + LLM 调用
```

**关键规则**：所有模块通过 `call_agent_pipeline_sync()` / `call_agent_pipeline_async()` 调用 AI，不允许绕过 Pipeline 直接调用 Provider。

### 2.2 目录结构 (v4.0)

```
opencopilot/          # 主包 (pip install -e .)
├── agent/             # Agent 核心
├── capabilities/      # 能力模块 (coding · knowledge · search · memory · skill · ppt · tools)
├── safety/            # 安全模块 (security · immune · planner)
├── providers/         # LLM 提供者
├── broker/            # 系统代理
├── observability/     # 可观测性
├── config/            # 配置管理
└── shared/            # 共享工具
api/
├── app.py             # 路由工厂
├── models.py          # Pydantic 模型
└── routers/           # 12 个独立路由模块
gui/
├── main.py            # 入口 + CopilotManager
├── window.py          # AICardWindow
├── workspace.py       # AgentWorkspace
├── workers/           # 7 个 QThread
└── dialogs/           # 对话框
tests/                 # 166 个测试用例 (unit/e2e/ablation)
```

### 2.3 端口分配

| 服务 | 端口 | 启动方式 |
|------|------|----------|
| API Gateway | 8000 | `uvicorn smart_copilot_api:app --port 8000`（含 /platform + KG 自动启动） |
| Broker | 18889 | `python opencopilot/broker/run.py`（需原生终端） |
| Knowledge Graph | 8090 | API Gateway 启动时自动带起 |

---

## 三、添加新功能

### 3.1 添加新的 API 端点

在 `api/routers/` 中创建新路由模块：

```python
# api/routers/my_feature.py
from fastapi import APIRouter
from opencopilot.agent.caller import call_agent_pipeline_async

router = APIRouter(prefix="/api/my-feature", tags=["my-feature"])

@router.post("/")
async def my_endpoint(request: MyRequest):
    result = ""
    async for chunk in call_agent_pipeline_async(request.text, action_type="my_action"):
        result += chunk
    return {"response": result}
```

### 3.2 添加新 Skill

创建 Python Skill 类并注册：

```python
from opencopilot.capabilities.skill.base import BaseSkill

class MySkill(BaseSkill):
    @property
    def name(self) -> str:
        return "my_skill"
    
    async def execute(self, context):
        return await self._do_work(context)
```

### 3.3 添加 Pipeline 中间件

```python
from opencopilot.agent.pipeline import BaseMiddleware, PipelineContext

class MyMiddleware(BaseMiddleware):
    async def process(self, ctx: PipelineContext, next_fn):
        # 前置处理
        await next_fn()  # 调用下一层
        # 后置处理
```

---

## 四、测试

### 4.1 运行测试

```bash
# 质量评估体系（推荐）
python quality_check.py          # 代码正确性 (166 用例, 6 套件)
python output_quality.py         # 输出内容质量 (18 项评分)

# 原始 pytest
python -m pytest tests/ -v
python -m pytest tests/unit/ -v
python -m pytest tests/e2e/ -v  # 端到端 + 消融实验

# 带覆盖率
python -m pytest tests/ --cov=opencopilot --cov-report=html
```

### 4.2 测试层级

| 层级 | 目录 | 数量 | 说明 |
|------|------|------|------|
| 单元测试 | `tests/unit/` | 10 | 核心模块功能正确性 |
| 集成测试 | `tests/integration/` | 1 | API 端点 |
| E2E 链路 | `tests/e2e/test_real_business.py` | 20 | 完整业务链路 |
| 结果评估 | `tests/e2e/test_result_evaluation.py` | 29 | 输出 benchmark 对比 |
| 消融实验 | `tests/e2e/test_ablation_*.py` | 32 | 修复效果量化 |

### 4.3 测试原则

1. **真实代码验证**：不使用 mock，使用真实模块和 API
2. **端到端优先**：输入→完整业务链路→输出校对
3. **消融验证**：每次修复提供 Before/After 量化对比

---

## 五、配置管理

### 5.1 配置文件

- `config.json` — LLM Provider、模型参数
- `.env` — API Key（MiMo/MiniMax/Ollama）
- `~/.asu_copilot/config.json` — 用户级配置

### 5.2 环境变量

```env
XIAOMI_API_KEY=your-mimo-key        # MiMo
MINIMAX_API_KEY=your-minimax-key    # MiniMax
OLLAMA_BASE_URL=http://localhost:11434  # Ollama
API_PORT=8000                       # Gateway 端口
```

### 5.3 Web Search 配置

在 `config.json` 中：
```json
{
  "web_search": {
    "enabled": false,
    "force": false
  }
}
```

---

## 六、开发路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| P0-P2 | 基础交互、多引擎 AI、Broker、PPT 共创、知识图谱 | ✅ |
| P3 | Agent Loop 重构、OpenClaw 迁移、Pipeline 统一 | ✅ |
| P4 | v4.0 分层架构、代码治理、质量提升(14项修复) | ✅ |
| P5 | IDE Extension v2、Broker 产品化 | 🔶 |
| P6 | 上下文主动感知、多 Agent 协作 | 📋 |

**近期优先**：
1. IDE Extension 增强（诊断接口）
2. 跨平台支持探索
3. 多模态输入（图片/语音）

---

## 七、调试技巧

```bash
# 查看 Pipeline 日志
tail -f ~/.asu_copilot/logs/agent.log

# 检查端口
lsof -i :8000   # API Gateway
lsof -i :18889  # Broker

# API 健康检查
curl http://127.0.0.1:8000/health

# 直接测试 Pipeline
python -c "
from agent_pipeline import call_agent_pipeline_sync
for c in call_agent_pipeline_sync('Hello', action_type='chat'):
    print(c, end='')
"
```

---

## 八、常见问题

| 问题 | 解决 |
|------|------|
| Pipeline 调用超时 | 检查 LLM API Key 配置，默认超时 120s |
| Broker 权限不足 | 在 macOS 原生终端启动 Broker |
| UI 闪退 | 使用 `bash scripts/start_ui.sh` 设置 Qt 路径 |
| 端口冲突 | API Gateway 启动时会自动清理，或手动 `lsof -i :PORT` |
