# ASU OS级常驻化与生命周期解耦方案 (Daemon Deployment Plan)

> **文档状态**: V1.0  
> **更新日期**: 2026-05-24  
> **目标**: 指导 ASU 从“捆绑启动的单体应用”向“OS 级后台守护进程 (Daemon) + 轻量级无状态 UI”平滑演进。

---

## 1. 架构演进背景

当前 ASU 的启动逻辑是强耦合的：当用户启动 UI (`smart_copilot.py`) 时，UI 会尝试在后台通过子进程拉起 Agent (`asu_custom_agent.py`)。如果 UI 退出，Agent 通常也会被连带关闭。

**这违背了 ASU “随时待命、隐身感知” 的核心设计初衷。** 

理想的最终形态是：
- **Agent 服务**：开机即静默运行，始终在后台监控系统状态、维护持久化记忆，不依赖任何 UI 的存活。
- **UI 卡片**：变成一个纯粹的 View 层，呼之即来挥之即去，仅在唤出时向后台拉取状态并展示。

为保证重构过程可控、不破坏现有调试体验，特制定此三模块平滑过渡方案。

---

## 2. 核心改造模块

### 模块一：UI 层的优雅降级 (Graceful Degradation)
**目标：UI 不再强依赖后台，能够独立存活并反馈状态。**

1. **移除强制拉起逻辑**：
   - 彻底删除 `smart_copilot.py` 中 `subprocess.Popen` 拉起 `asu_custom_agent.py` 的代码。
2. **新增探活与状态反馈 UI**：
   - UI 唤出时，异步向 `http://127.0.0.1:18888/health` 发起 Ping。
   - **健康状态 (🟢)**：UI 正常交互。
   - **断连状态 (🔴)**：UI 正常弹出，但禁用输入框，在界面上明确提示：“ASU 核心守护服务未启动”。
3. **安全退出机制**：
   - UI 退出时，只销毁自身窗口，绝对不干涉 18888 端口的存活。

### 模块二：macOS 守护进程标准化 (LaunchAgent)
**目标：让 Agent 符合苹果后台服务规范，实现开机自启与防崩溃。**

1. **创建配置文件 (`com.asu.agent.plist`)**：
   - 配置 `RunAtLoad = true`，实现开机自启。
   - 配置 `KeepAlive = true`，实现进程崩溃后系统自动拉起。
2. **日志路径规范化**：
   - 后台静默运行后终端不可见，需在 plist 中配置 `StandardOutPath` 和 `StandardErrorPath`。
   - 统一输出至 macOS 标准应用日志路径：`~/Library/Logs/ASU/agent_out.log` 和 `agent_err.log`。

### 模块三：开发者工具链 (Tooling)
**目标：提供快速部署和调试脚本，避免手动配置造成的环境混乱。**

在项目新建 `scripts/` 目录，提供以下 Bash 脚本：
1. **`install_daemon.sh`**：一键生成日志目录，复制 plist 到 `~/Library/LaunchAgents/`，并执行 `launchctl load`。
2. **`uninstall_daemon.sh`**：一键执行 `launchctl unload` 并清理配置，方便随时切回“终端 python 运行”的调试模式。
3. **`tail_logs.sh`**：一键执行 `tail -f ~/Library/Logs/ASU/agent_out.log`，方便在后台运行模式下观测 LLM 交互流。

---

## 3. 分阶段实施路线图 (Phases)

为了控制架构调整的风险，确保每一步都有退路，建议分两阶段执行：

### Phase 1：UI 解耦与独立调试 (推荐首先执行)
- **动作**：仅执行“模块一”，剥离 `smart_copilot.py` 的启动依赖，增加 UI 状态灯提示。
- **验证方式**：
  1. 不开 Agent，双击右键呼出 UI，应看到红灯和断连提示，不崩溃。
  2. 手动在终端运行 `python asu_custom_agent.py`。
  3. 再次呼出 UI，应看到绿灯并恢复正常对话。

### Phase 2：LaunchAgent 部署 (确认 Phase 1 无误后执行)
- **动作**：执行“模块二”和“模块三”，编写 plist 和自动化脚本。
- **验证方式**：
  1. 运行 `install_daemon.sh`。
  2. 杀掉现有的所有 python 终端窗口。
  3. 呼出 UI，依然是绿灯可用状态。
  4. 在终端使用 `kill -9` 强杀 Agent 进程，几秒内 UI 重新变绿（触发 KeepAlive 自动重启）。

---

## 4. 预期收益

完成该方案后，ASU 将成为一个真正意义上的 OS 级智能体底座，不再只是一个带有 Python 后端的 GUI 工具。这为下一步进行**全局 WebSocket 焦点监听**和**长期挂机任务**彻底扫清了工程障碍。