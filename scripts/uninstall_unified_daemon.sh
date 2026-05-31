#!/bin/bash
# ============================================================
# ASU 统一服务守护进程 卸载脚本
# 功能：卸载统一守护进程（Broker + 知识图谱 API）
# 使用：bash scripts/uninstall_unified_daemon.sh
# ============================================================

set -e

PLIST_DEST="$HOME/Library/LaunchAgents/com.asu.unified.plist"
LABEL="com.asu.unified"

echo "============================================================"
echo "  ASU 统一服务守护进程卸载"
echo "============================================================"

# ---- 卸载守护进程 ----
if launchctl list 2>/dev/null | grep -q "$LABEL"; then
    echo "🔄 正在卸载统一守护进程..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    echo "✅ 统一守护进程已卸载"
else
    echo "ℹ️  统一守护进程未运行，跳过卸载。"
fi

# ---- 删除 plist 文件 ----
if [ -f "$PLIST_DEST" ]; then
    rm -f "$PLIST_DEST"
    echo "✅ plist 文件已删除: $PLIST_DEST"
fi

echo ""
echo "============================================================"
echo "  卸载完成！"
echo ""
echo "  提示："
echo "    - Broker 和知识图谱 API 已停止"
echo "    - 日志文件保留在 ~/Library/Logs/ASU/"
echo "    - 如需重新安装：bash scripts/install_unified_daemon.sh"
echo "============================================================"
