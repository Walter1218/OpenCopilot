# OpenCopilot OS级常驻化与生命周期解耦方案 (Daemon Deployment Plan)

> **文档状态**: V2.1（已更新）  
> **更新日期**: 2026-05-30
> **状态**: UI组件阶段1-4已完成  
> **目标**: 指导 ASU 从"捆绑启动的单体应用"向"OS 级后台守护进程 (Daemon) + 轻量级无状态 UI"平滑演进。

---

## 1. 架构演进背景

> **此问题已完全解决。** 以下保留原始背景描述供参考。

~~当前 OpenCopilot 的启动逻辑是强耦合的：当用户启动 UI (`smart_copilot.py`) 时，UI 会尝试在后台通过子进程拉起 Agent (`asu_custom_agent.py`)。如果 UI 退出，Agent 通常也会被连带关闭。~~

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
   - **断连状态 (🔴)**：标题栏红色状态点 + 橙色横幅提示"OpenCopilot 核心守护服务未启动"。
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

---

## 6. 故障排查指南

### 6.1 Agent 无法启动

**症状**: `curl http://127.0.0.1:18888/health` 无响应

**排查步骤**:
```bash
# 1. 检查进程是否存在
ps aux | grep asu_custom_agent

# 2. 查看日志
tail -50 ~/Library/Logs/ASU/agent_err.log

# 3. 检查端口是否被占用
lsof -i :18888

# 4. 手动启动测试
python asu_custom_agent.py
```

**常见原因**:
- Python 虚拟环境未激活
- 依赖包缺失：`pip install -r requirements.txt`
- 端口被其他进程占用

### 6.2 Broker 无法启动

**症状**: `curl -H "Authorization: Bearer $(cat ~/.asu_broker_token)" http://127.0.0.1:18889/health` 无响应

**排查步骤**:
```bash
# 1. 检查进程是否存在
ps aux | grep asu_broker

# 2. 查看日志
tail -50 ~/Library/Logs/ASU/broker_err.log

# 3. 检查端口是否被占用
lsof -i :18889

# 4. 手动启动测试
cd asu_broker && python run.py
```

### 6.3 UI 显示红灯

**症状**: 启动 UI 后标题栏显示红色状态点

**排查步骤**:
1. 确认 Agent 是否运行：`curl http://127.0.0.1:18888/health`
2. 如果未运行，启动 Agent：`bash scripts/install_daemon.sh` 或 `python asu_custom_agent.py`
3. 如果已运行但 UI 仍显示红灯，重启 UI：`bash scripts/start_ui.sh`

### 6.4 守护进程崩溃重启

**症状**: 服务频繁重启

**排查步骤**:
```bash
# 1. 查看崩溃日志
tail -100 ~/Library/Logs/ASU/agent_err.log

# 2. 检查系统日志
log show --predicate 'process == "Python"' --last 1h

# 3. 检查资源使用
top -l 1 | head -20
```

---

## 7. 日志分析指南

### 7.1 日志位置

| 服务 | 标准输出 | 错误输出 |
|------|----------|----------|
| Agent | `~/Library/Logs/ASU/agent_out.log` | `~/Library/Logs/ASU/agent_err.log` |
| Broker | `~/Library/Logs/ASU/broker_out.log` | `~/Library/Logs/ASU/broker_err.log` |

### 7.2 日志级别

- **INFO**: 正常运行信息
- **WARNING**: 警告信息，不影响运行
- **ERROR**: 错误信息，可能影响功能
- **DEBUG**: 调试信息（仅开发模式）

### 7.3 常用日志分析命令

```bash
# 查看最近 100 行日志
tail -100 ~/Library/Logs/ASU/agent_out.log

# 实时查看日志
tail -f ~/Library/Logs/ASU/agent_out.log

# 搜索错误信息
grep -i "error" ~/Library/Logs/ASU/agent_err.log

# 搜索特定时间的日志
grep "2026-05-30" ~/Library/Logs/ASU/agent_out.log

# 统计错误数量
grep -c "ERROR" ~/Library/Logs/ASU/agent_err.log
```

---

## 8. 跨平台说明

### 8.1 macOS（当前支持）

- 使用 `launchctl` 管理守护进程
- 配置文件：`deploy/com.asu.agent.plist`、`deploy/com.asu.broker.plist`
- 管理脚本：`scripts/install_daemon.sh` 等

### 8.2 Linux（未来支持）

**systemd 服务示例**:
```ini
[Unit]
Description=OpenCopilot Agent
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/OpenCopilot
ExecStart=/path/to/python asu_custom_agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**管理命令**:
```bash
# 启用服务
sudo systemctl enable opencopilot-agent

# 启动服务
sudo systemctl start opencopilot-agent

# 查看状态
sudo systemctl status opencopilot-agent

# 查看日志
journalctl -u opencopilot-agent -f
```

### 8.3 Windows（未来支持）

**Windows 服务示例**:
- 使用 `pywin32` 创建 Windows 服务
- 或使用 `nssm` 将 Python 脚本注册为服务

---

## 9. 性能优化建议

### 9.1 资源限制

```bash
# 限制 Agent 内存使用（macOS）
# 在 plist 中添加
<key>SoftResourceLimits</key>
<dict>
    <key>Stack</key>
    <integer>8388608</integer>
</dict>
```

### 9.2 日志轮转

```bash
# 使用 logrotate 管理日志（Linux）
cat > /etc/logrotate.d/opencopilot << EOF
~/Library/Logs/ASU/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
}
EOF
```

### 9.3 监控脚本

```bash
#!/bin/bash
# monitor.sh - 监控 OpenCopilot 服务状态

check_service() {
    local name=$1
    local url=$2
    
    if curl -s -f "$url" > /dev/null; then
        echo "✅ $name is running"
    else
        echo "❌ $name is not running"
        # 自动重启
        if [ "$name" = "Agent" ]; then
            bash scripts/install_daemon.sh
        elif [ "$name" = "Broker" ]; then
            bash scripts/install_broker_daemon.sh
        fi
    fi
}

check_service "Agent" "http://127.0.0.1:18888/health"
check_service "Broker" "http://127.0.0.1:18889/health"
```

---

## 10. 安全注意事项

### 10.1 端口安全

- Agent (18888) 和 Broker (18889) 仅监听 `127.0.0.1`
- 不要暴露到公网
- 如需远程访问，使用 SSH 隧道

### 10.2 文件权限

```bash
# 确保配置文件权限正确
chmod 600 deploy/com.asu.agent.plist
chmod 600 deploy/com.asu.broker.plist
chmod 700 scripts/*.sh
```

### 10.3 Token 安全

```bash
# Broker Token 存储在用户主目录
ls -la ~/.asu_broker_token

# 确保只有当前用户可读
chmod 600 ~/.asu_broker_token
```