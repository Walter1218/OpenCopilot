#!/bin/bash
# ============================================================
# ASU 统一服务守护进程 一键安装脚本
# 功能：同时启动 Broker 和知识图谱 API，注册为 LaunchAgent
# 使用：bash scripts/install_unified_daemon.sh
# ============================================================

set -e

# ---- 路径变量 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_TEMPLATE="$PROJECT_DIR/deploy/com.asu.unified.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.asu.unified.plist"
LOG_DIR="$HOME/Library/Logs/ASU"
PYTHON_EXEC="$(which python3)"
PYTHON_BIN_DIR="$(dirname "$PYTHON_EXEC")"
LABEL="com.asu.unified"

echo "============================================================"
echo "  ASU 统一服务守护进程安装"
echo "============================================================"
echo "  项目目录    : $PROJECT_DIR"
echo "  Python      : $PYTHON_EXEC"
echo "  日志目录    : $LOG_DIR"
echo ""
echo "  将启动以下服务："
echo "    - Broker 服务（端口 18889）"
echo "    - 知识图谱 API（端口 8090）"
echo ""

# ---- 检查模板 ----
if [ ! -f "$PLIST_TEMPLATE" ]; then
    echo "❌ 找不到 plist 模板文件: $PLIST_TEMPLATE"
    exit 1
fi

# ---- 检查启动脚本 ----
if [ ! -f "$PROJECT_DIR/start_broker_with_kg.py" ]; then
    echo "❌ 找不到 start_broker_with_kg.py，请确认项目结构正确。"
    exit 1
fi

# ---- 创建日志目录 ----
mkdir -p "$LOG_DIR"
echo "✅ 日志目录已就绪: $LOG_DIR"

# ---- 卸载旧的守护进程 ----
# 卸载旧的 Broker 守护进程
if launchctl list 2>/dev/null | grep -q "com.asu.broker"; then
    echo "🔄 检测到旧版 Broker 守护进程，正在卸载..."
    launchctl unload "$HOME/Library/LaunchAgents/com.asu.broker.plist" 2>/dev/null || true
    sleep 1
fi

# 卸载旧的统一守护进程
if launchctl list 2>/dev/null | grep -q "$LABEL"; then
    echo "🔄 检测到旧版统一守护进程，正在卸载..."
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
echo "✅ 统一守护进程已注册并启动"
echo ""

# ---- 等待 3 秒后探活确认 ----
echo "⏳ 等待服务启动..."
sleep 3

# 检查 Broker 健康状态
if [ -f "$HOME/.asu_broker_token" ]; then
    BROKER_TOKEN=$(cat "$HOME/.asu_broker_token")
    HEALTH_RESP=$(curl -s --max-time 3 -H "Authorization: Bearer $BROKER_TOKEN" "http://127.0.0.1:18889/health" 2>/dev/null || echo "")
    if echo "$HEALTH_RESP" | grep -q '"status".*"ok"'; then
        echo "🟢 Broker 服务在线，健康检查通过！"
    else
        echo "🟡 Broker 服务已注册，但尚未响应（可能正在初始化）。"
    fi
else
    echo "🟡 Broker 服务已注册。未找到 Token 文件，跳过健康检查。"
fi

# 检查知识图谱 API 健康状态
KG_HEALTH=$(curl -s --max-time 3 "http://127.0.0.1:8090/health" 2>/dev/null || echo "")
if echo "$KG_HEALTH" | grep -q '"status".*"healthy"'; then
    echo "🟢 知识图谱 API 在线，健康检查通过！"
else
    echo "🟡 知识图谱 API 已注册，但尚未响应（可能正在初始化）。"
fi

echo ""
echo "============================================================"
echo "  安装完成！下次开机 Broker + 知识图谱 API 将自动后台启动。"
echo ""
echo "  管理命令："
echo "    实时日志     : tail -f ~/Library/Logs/ASU/unified_out.log"
echo "    错误日志     : tail -f ~/Library/Logs/ASU/unified_err.log"
echo "    卸载         : bash scripts/uninstall_unified_daemon.sh"
echo "    Broker 状态  : curl -H \"Authorization: Bearer \$(cat ~/.asu_broker_token)\" http://127.0.0.1:18889/health"
echo "    知识图谱状态 : curl http://127.0.0.1:8090/health"
echo "============================================================"
