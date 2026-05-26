#!/bin/bash
# ============================================================
# ASU Broker 守护进程 一键卸载脚本
# 功能：停止守护进程并从 LaunchAgents 中移除注册
# 使用：bash scripts/uninstall_broker_daemon.sh
# ============================================================

set -e

PLIST_DEST="$HOME/Library/LaunchAgents/com.asu.broker.plist"
LABEL="com.asu.broker"

echo "============================================================"
echo "  ASU Privileged Broker 守护进程卸载"
echo "============================================================"

# ---- 停止并卸载 ----
if [ -f "$PLIST_DEST" ]; then
    echo "🔄 正在停止守护进程..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    rm -f "$PLIST_DEST"
    echo "✅ plist 已移除: $PLIST_DEST"
else
    echo "🟡 未找到已安装的守护进程配置，跳过卸载。"
fi

# ---- 二次确认进程已停止 ----
if launchctl list 2>/dev/null | grep -q "$LABEL"; then
    echo "⚠️  进程可能仍在运行，尝试强制停止..."
    launchctl remove "$LABEL" 2>/dev/null || true
fi

echo ""
echo "============================================================"
echo "  卸载完成！Broker 守护进程已停止并从开机启动中移除。"
echo "  日志文件保留在: ~/Library/Logs/ASU/broker_*.log"
echo "  Token 文件保留在: ~/.asu_broker_token"
echo ""
echo "  如需重新安装，请运行: bash scripts/install_broker_daemon.sh"
echo "============================================================"
