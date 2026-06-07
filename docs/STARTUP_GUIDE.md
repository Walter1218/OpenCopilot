# OpenCopilot 启动方式说明

> 本文档已按当前 v5 实现更新。  
> 关键修正：**v5 桌面主链路不只依赖 API Gateway，还依赖独立的 Agent Pipeline 服务 `:18888`。**

## 一、先理解 4 个进程

| 服务 | 端口 | 是否必需 | 当前职责 |
|------|------|----------|----------|
| **Agent Pipeline** | `18888` | 推荐常驻 | 独立 Agent 服务，供健康检查、HTTP 兼容链路和部分服务路径使用 |
| **Broker** | `18889` | 桌面交互强依赖 | 获取选区、活动文档、浏览器内容、文本回写 |
| **API Gateway** | `8000` | 可选但建议启动 | HTTP/OpenAPI 入口，承载 `/api/*` 路由和部分 v5 Studio API |
| **UI** | - | 必需 | `smart_copilot.py` 启动桌面界面，进入 v5 导航层 |

## 二、最小启动 vs 完整启动

### 1. 最小启动

适合验证 v5 桌面主链路与常见桌面场景：`Work / Chat / 基础 Settings / 基础 Studio 外壳`

```bash
# 终端 1：Agent Pipeline
python3 asu_custom_agent.py

# 终端 2：Broker（必须在 macOS 原生 Terminal.app / iTerm2 中运行）
bash start_broker.sh

# 终端 3：UI
bash scripts/start_ui.sh
```

### 2. 完整启动

适合联调 API、Swagger、Studio 路由、旧入口兼容链路

```bash
# 终端 1：Agent Pipeline
python3 asu_custom_agent.py

# 终端 2：Broker
bash start_broker.sh

# 终端 3：API Gateway
python3 -m uvicorn smart_copilot_api:app --host 0.0.0.0 --port 8000 --reload

# 终端 4：UI
bash scripts/start_ui.sh
```

## 三、推荐开发方式

### 1. 环境变量

通过 `APP_ENV` 区分开发/生产模式：

```bash
export APP_ENV=dev
# 或
export APP_ENV=prod
```

### 2. 开发模式

```bash
# 默认就是开发模式
bash scripts/start_ui.sh

# 等价写法
APP_ENV=dev bash scripts/start_ui.sh
```

特点：

- 控制台输出更详细
- 便于直接观察 UI / Broker / Agent 日志
- 更适合联调 v5 交互和 Agent 主链路

### 3. 生产模式

```bash
bash scripts/start_ui.sh --prod

# 或
APP_ENV=prod bash scripts/start_ui.sh
```

特点：

- UI 启动提示更偏生产化
- 适合验证生产配置和异常兜底行为
- 不等于“后端服务都已守护化”，仍需按下文核对各服务部署方式

## 四、脚本现状说明

### 1. `start_backend.sh`

```bash
bash start_backend.sh
```

当前脚本只会启动：

- Broker `:18889`
- API Gateway `:8000`

**不会启动 Agent Pipeline `:18888`**，因此它不是“带完整服务探活和 HTTP 兼容链路”的完整后端组合。

### 2. `start_api.sh`

```bash
bash start_api.sh
```

只启动 API Gateway，不负责 Agent Pipeline。

### 3. `scripts/start_ui.sh`

```bash
bash scripts/start_ui.sh
```

这是当前推荐的 UI 启动方式，会自动设置 Qt 插件路径并进入 `smart_copilot.py`。

## 五、生产部署现状

### 1. Broker 守护进程

当前可以安装：

```bash
bash scripts/install_broker_daemon.sh
```

用于后台常驻 Broker。

### 2. 统一守护进程

当前脚本：

```bash
bash scripts/install_unified_daemon.sh
```

主要覆盖：

- Broker
- 知识图谱 API

**不等同于完整的 v5 四进程方案**。

### 3. 废弃脚本

`scripts/install_daemon.sh` 当前已标记为 **DEPRECATED**，不要再按旧文档把它当成 Agent 安装脚本使用。

## 六、当前依赖关系

### 1. v5 桌面主链路

```text
UI (smart_copilot.py -> gui/main.py)
  ├── Broker :18889
  │     ├── 获取选区
  │     ├── 获取活动文档 / 浏览器内容
  │     └── 文本回写
  │
  └── 共享 Pipeline 实现
        ├── 桌面侧通过 caller 进程内调用
        └── 服务侧可由 Agent Pipeline :18888 暴露 HTTP / health
```

### 2. API 扩展链路

```text
API Gateway :8000
  ├── 对外 HTTP / OpenAPI
  ├── 旧入口兼容
  └── 部分 v5 路由（如 /api/studio/*）
```

## 七、常见问题

### Q1: 我只启动了 `start_backend.sh`，为什么 v5 Work/Chat 还是不工作？

因为它没有启动 `Agent Pipeline :18888`，所以缺少独立服务探活和 HTTP 兼容链路。  
推荐再单独运行：

```bash
python3 asu_custom_agent.py
```

### Q2: 我什么时候必须启动 API Gateway？

以下场景建议启动：

- 你要调 Swagger / ReDoc
- 你要走 `/api/*` HTTP 接口
- 你要联调 v5 Studio 的相关 API 路由
- 你要验证旧入口兼容链路

如果你只验证 v5 桌面端的基础主链路，最小集合通常是：`UI + Broker`。  
如果你还要稳定使用健康检查、HTTP 路由或兼容链路，推荐使用：`UI + Broker + Agent`。

### Q3: 如何确认当前运行模式？

`scripts/start_ui.sh` 启动时会显示：

- 开发模式：`🔧 开发模式启动`
- 生产模式：`🏭 生产模式启动`

### Q4: Broker 启动报权限不足怎么办？

Broker 需要 macOS 辅助功能权限：

1. 打开「系统设置 → 隐私与安全性 → 辅助功能」
2. 添加并勾选当前终端应用（`Terminal.app` 或 `iTerm2`）
3. 如涉及截图/视觉能力，再补充授予「屏幕录制」
4. 完全退出终端后重新启动

### Q5: Agent / API / Broker 分别怎么探活？

```bash
# Agent
curl http://127.0.0.1:18888/health

# Broker（需要 token）
curl -H "Authorization: Bearer $(cat ~/.asu_broker_token)" http://127.0.0.1:18889/health

# API Gateway
curl http://127.0.0.1:8000/health
```
