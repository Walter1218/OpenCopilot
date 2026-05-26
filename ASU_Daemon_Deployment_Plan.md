# ASU OS级常驻化与生命周期解耦方案 (Daemon Deployment Plan)

> **文档状态**: V1.2（已更新）  
> **更新日期**: 2026-05-26  
> **目标**: 指导 ASU 从"捆绑启动的单体应用"向"OS 级后台守护进程 (Daemon) + 轻量级无状态 UI"平滑演进。

---

## 1. 架构演进背景

> **此问题已完全解决。** 以下保留原始背景描述供参考。

~~当前 ASU 的启动逻辑是强耦合的：当用户启动 UI (`smart_copilot.py`) 时，UI 会尝试在后台通过子进程拉起 Agent (`asu_custom_agent.py`)。如果 UI 退出，Agent 通常也会被连带关闭。~~

**已实现的最终形态：**
- **Agent 服务**：开机即静默运行，始终在后台监控系统状态、维护持久化记忆，不依赖任何 UI 的存活。
- **UI 卡片**：纯粹的 View 层，呼之即来挥之即去，仅在唤出时向后台探活并展示状态。

---

## 2. 核心改造模块（均已完成）

### 模块一：UI 层的优雅降级 ✅ 已完成
**目标：UI 不再强依赖后台，能够独立存活并反馈状态。**

1. **移除强制拉起逻辑**：已彻底删除 `smart_copilot.py` 中 `subprocess.Popen` 拉起 `asu_custom_agent.py` 的代码，同时移除 `subprocess` import。
2. **异步探活 + 状态反馈 UI**：
   - 新增 `AgentHealthWorker(QThread)`，UI 唤出时异步向 `http://127.0.0.1:18888/health` Ping。
   - **健康状态 (🟢)**：标题栏绿色状态点，正常交互。
   - **断连状态 (🔴)**：标题栏红色状态点 + 橙色横幅提示"ASU 核心守护服务未启动"。
3. **安全退出机制**：`cleanup()` 只终止鼠标监听线程，绝对不干涉 18888 端口的存活。

### 模块二：macOS 守护进程标准化 ✅ 已完成
**目标：让 Agent 符合苹果后台服务规范，实现开机自启与防崩溃。**

1. **配置文件**：`deploy/com.asu.agent.plist`，含占位符，由 `install_daemon.sh` 在安装时替换为实际路径。
   - `RunAtLoad = true`：开机自启。
   - `KeepAlive = true`：进程崩溃后系统自动拉起。
2. **日志路径规范化**：统一输出至 `~/Library/Logs/ASU/agent_out.log` 和 `agent_err.log`。

### 模块三：开发者工具链 ✅ 已完成
**目标：提供快速部署和调试脚本，避免手动配置造成的环境混乱。**

| 脚本 | 作用 |
|------|------|
| `scripts/install_daemon.sh` | 一键生成日志目录，替换 plist 占位符，`launchctl load` 注册并探活确认 |
| `scripts/uninstall_daemon.sh` | 一键 `launchctl unload` 并清理配置，随时切回终端调试模式 |
| `scripts/tail_logs.sh` | 实时 `tail -f` Agent 日志，等价于在终端直接看输出 |
| `scripts/start_ui.sh` | 自动探测 PyQt6 插件路径并设置 `QT_QPA_PLATFORM_PLUGIN_PATH`，解决 macOS cocoa 插件找不到的问题 |

---

## 3. 实施路线图（已全部完成）

### Phase 1：UI 解耦与独立调试 ✅ 已完成
- **动作**：剥离 `smart_copilot.py` 的启动依赖，新增 `AgentHealthWorker`、状态灯和离线横幅。
- **验证**：`test_lifecycle_decoupling.py` **10/10 通过**。
- **验证方式**：
  1. 不开 Agent，双击右键呼出 UI → 红灯 + 断连横幅，不崩溃。✅
  2. 手动运行 `python asu_custom_agent.py` 后再呼出 UI → 绿灯，恢复对话。✅

### Phase 2：LaunchAgent 部署 ✅ 已完成
- **动作**：编写 `deploy/com.asu.agent.plist` 和 `scripts/` 下的三个管理脚本，新增 `start_ui.sh` 修复 Qt 环境问题。
- **验证**：`test_daemon_scripts.py` **14/14 通过**。
- **一键部署**：
  ```bash
  bash scripts/install_daemon.sh
  ```

---

## 4. 预期收益（已实现）

完成该方案后，ASU 已成为一个真正意义上的 OS 级智能体底座：
- ✅ Agent 开机自启、崩溃自愈
- ✅ UI 生命周期完全独立、断连优雅降级
- ✅ **Broker 同步完成常驻化**（`deploy/com.asu.broker.plist` + `scripts/install_broker_daemon.sh`）
- Broker WebSocket 焦点监听待后续实现

---

## 5. 快速参考：日常启动命令

| 操作 | 命令 |
|------|------|
| 安装 Agent 守护进程（一次性） | `bash scripts/install_daemon.sh` |
| 安装 Broker 守护进程（一次性） | `bash scripts/install_broker_daemon.sh` |
| 启动 UI | `bash scripts/start_ui.sh` |
| 启动 Agent（开发调试） | `python asu_custom_agent.py` |
| 启动 Broker（开发调试） | `cd asu_broker && python run.py` |
| 查看 Agent 实时日志 | `bash scripts/tail_logs.sh` |
| 查看 Broker 实时日志 | `tail -f ~/Library/Logs/ASU/broker_out.log` |
| 卸载 Agent 守护进程 | `bash scripts/uninstall_daemon.sh` |
| 卸载 Broker 守护进程 | `bash scripts/uninstall_broker_daemon.sh` |
| 检查 Agent 是否在线 | `curl http://127.0.0.1:18888/health` |
| 检查 Broker 是否在线 | `curl -H "Authorization: Bearer $(cat ~/.asu_broker_token)" http://127.0.0.1:18889/health` |