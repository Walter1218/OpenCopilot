#!/bin/bash
# ============================================================
# ASU Broker 守护进程 一键安装脚本
# 功能：注册 LaunchAgent，实现开机自启和崩溃自动重启
# 使用：bash scripts/install_broker_daemon.sh
# ============================================================

set -e

# ---- 路径变量 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BROKER_DIR="$PROJECT_DIR/asu_broker"
PLIST_TEMPLATE="$PROJECT_DIR/deploy/com.asu.broker.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.asu.broker.plist"
LOG_DIR="$HOME/Library/Logs/ASU"
PYTHON_EXEC="$(which python3)"
PYTHON_BIN_DIR="$(dirname "$PYTHON_EXEC")"
LABEL="com.asu.broker"

echo "============================================================"
echo "  ASU Privileged Broker 守护进程安装"
echo "============================================================"
echo "  项目目录    : $PROJECT_DIR"
echo "  Broker 目录 : $BROKER_DIR"
echo "  Python      : $PYTHON_EXEC"
echo "  日志目录    : $LOG_DIR"
echo ""

# ---- 检查模板 ----
if [ ! -f "$PLIST_TEMPLATE" ]; then
    echo "❌ 找不到 plist 模板文件: $PLIST_TEMPLATE"
    exit 1
fi

# ---- 检查 Broker 入口文件 ----
if [ ! -f "$BROKER_DIR/run.py" ]; then
    echo "❌ 找不到 asu_broker/run.py，请确认项目结构正确。"
    exit 1
fi

# ---- 创建日志目录 ----
mkdir -p "$LOG_DIR"
echo "✅ 日志目录已就绪: $LOG_DIR"

# ---- 如果已加载，先卸载旧版本 ----
if launchctl list 2>/dev/null | grep -q "$LABEL"; then
    echo "🔄 检测到旧版本守护进程，正在卸载..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    sleep 1
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
# 读取 Broker Token 用于鉴权
if [ -f "$HOME/.asu_broker_token" ]; then
    BROKER_TOKEN=$(cat "$HOME/.asu_broker_token")
    HEALTH_RESP=$(curl -s --max-time 3 -H "Authorization: Bearer $BROKER_TOKEN" "http://127.0.0.1:18889/health" 2>/dev/null || echo "")
    if echo "$HEALTH_RESP" | grep -q '"status".*"ok"'; then
        echo "🟢 Broker 守护进程在线，健康检查通过！"
    else
        echo "🟡 守护进程已注册，但 Broker 尚未响应（可能正在初始化）。"
        echo "   响应内容: $HEALTH_RESP"
    fi
else
    echo "🟡 守护进程已注册。未找到 Token 文件，跳过健康检查。"
    echo "   首次启动后 Broker 会自动生成 ~/.asu_broker_token"
fi

echo ""
echo "============================================================"
echo "  安装完成！下次开机 Broker 将自动后台启动。"
echo ""
echo "  管理命令："
echo "    实时日志 : tail -f ~/Library/Logs/ASU/broker_out.log"
echo "    错误日志 : tail -f ~/Library/Logs/ASU/broker_err.log"
echo "    卸载     : bash scripts/uninstall_broker_daemon.sh"
echo "============================================================"
