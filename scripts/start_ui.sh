#!/bin/bash
# ============================================================
# ASU Smart Copilot UI 启动脚本
# 自动设置 Qt 环境变量，避免 "cocoa plugin not found" 问题
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 自动探测 PyQt6 的 platforms 插件目录
PYQT6_PLATFORMS=$(python3 -c "
import os, PyQt6
qt6_dir = os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6', 'plugins', 'platforms')
print(qt6_dir if os.path.isdir(qt6_dir) else '')
" 2>/dev/null)

if [ -n "$PYQT6_PLATFORMS" ]; then
    export QT_QPA_PLATFORM_PLUGIN_PATH="$PYQT6_PLATFORMS"
    echo "✅ Qt 插件路径: $PYQT6_PLATFORMS"
else
    echo "⚠️  未能自动探测 PyQt6 插件路径，尝试继续..."
fi

echo "🚀 启动 ASU Smart Copilot UI..."
cd "$PROJECT_DIR"
exec python3 smart_copilot.py "$@"
