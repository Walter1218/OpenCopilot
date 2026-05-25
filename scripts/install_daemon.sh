#!/bin/bash
# ============================================================
# ASU Agent 守护进程 一键安装脚本
# 功能：注册 LaunchAgent，实现开机自启和崩溃自动重启
# 使用：bash scripts/install_daemon.sh
# ============================================================

set -e

# ---- 路径变量 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_TEMPLATE="$PROJECT_DIR/deploy/com.asu.agent.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.asu.agent.plist"
LOG_DIR="$HOME/Library/Logs/ASU"
PYTHON_EXEC="$(which python3)"
PYTHON_BIN_DIR="$(dirname "$PYTHON_EXEC")"
LABEL="com.asu.agent"

echo "============================================================"
echo "  ASU Agent 守护进程安装"
echo "============================================================"
echo "  项目目录  : $PROJECT_DIR"
echo "  Python    : $PYTHON_EXEC"
echo "  日志目录  : $LOG_DIR"
echo ""

# ---- 检查模板 ----
if [ ! -f "$PLIST_TEMPLATE" ]; then
    echo "❌ 找不到 plist 模板文件: $PLIST_TEMPLATE"
    exit 1
fi

# ---- 检查 Agent 入口文件 ----
if [ ! -f "$PROJECT_DIR/asu_custom_agent.py" ]; then
    echo "❌ 找不到 asu_custom_agent.py，请确认项目根目录正确。"
    exit 1
fi

# ---- 创建日志目录 ----
mkdir -p "$LOG_DIR"
echo "✅ 日志目录已就绪: $LOG_DIR"

# ---- 如果已加载，先卸载旧版本 ----
if launchctl list | grep -q "$LABEL" 2>/dev/null; then
    echo "🔄 检测到旧版本守护进程，正在卸载..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# ---- 替换模板占位符，生成最终 plist ----
sed \
    -e "s|__PYTHON_EXECUTABLE__|$PYTHON_EXEC|g" \
    -e "s|__ASU_PROJECT_DIR__|$PROJECT_DIR|g" \
    -e "s|__HOME__|$HOME|g" \
    -e "s|__PYTHON_BIN_DIR__|$PYTHON_BIN_DIR|g" \
    "$PLIST_TEMPLATE" > "$PLIST_DEST"

echo "✅ plist 已生成: $PLIST_DEST"

# ---- 加载并启动 ----
launchctl load "$PLIST_DEST"
echo "✅ 守护进程已注册并启动"
echo ""

# ---- 等待 2 秒后探活确认 ----
sleep 2
if curl -s --max-time 2 "http://127.0.0.1:18888/health" | grep -q '"status"'; then
    echo "🟢 ASU Agent 守护进程在线，健康检查通过！"
else
    echo "🟡 守护进程已注册，但 Agent 尚未响应（可能正在初始化）。"
    echo "   稍后运行以下命令查看日志："
    echo "   bash scripts/tail_logs.sh"
fi

echo ""
echo "============================================================"
echo "  安装完成！下次开机 ASU Agent 将自动后台启动。"
echo "  卸载请运行: bash scripts/uninstall_daemon.sh"
echo "============================================================"
