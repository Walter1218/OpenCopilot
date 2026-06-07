#!/bin/bash
# ============================================================
# ASU Smart Copilot UI 启动脚本
# 自动设置 Qt 环境变量，避免 "cocoa plugin not found" 问题
#
# 用法:
#   bash scripts/start_ui.sh         # 开发模式（默认）
#   bash scripts/start_ui.sh --prod  # 生产模式
#   APP_ENV=prod bash scripts/start_ui.sh  # 显式设置环境变量
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 解析模式参数
MODE="dev"
for arg in "$@"; do
    if [ "$arg" = "--prod" ]; then
        MODE="prod"
    fi
done

# 如果环境变量已设置，优先使用环境变量
if [ -n "$APP_ENV" ]; then
    MODE="$APP_ENV"
fi

export APP_ENV="$MODE"

if [ "$MODE" = "prod" ]; then
    echo "🏭 生产模式启动"
else
    echo "🔧 开发模式启动"
fi

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
