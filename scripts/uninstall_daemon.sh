#!/bin/bash
# ============================================================
# 【⚠️ 废弃警告 DEPRECATED】
# 该脚本在 P1 阶段架构重构前用于卸载 Agent 守护进程。
# ============================================================

set -e

LABEL="com.asu.agent"
PLIST_DEST="$HOME/Library/LaunchAgents/com.asu.agent.plist"

echo "============================================================"
echo "  卸载旧版 ASU Agent 守护进程"
echo "============================================================"

# 如果已加载，则卸载
if launchctl list 2>/dev/null | grep -q "$LABEL"; then
    echo "🔄 正在卸载 $LABEL..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    echo "✅ 卸载成功"
else
    echo "ℹ️ 未检测到运行中的旧版 Agent 守护进程。"
fi

# 删除 plist 文件
if [ -f "$PLIST_DEST" ]; then
    rm "$PLIST_DEST"
    echo "✅ 已删除配置文件: $PLIST_DEST"
fi

echo "============================================================"
echo "  卸载完成！"
echo "============================================================"
