#!/bin/bash
# ============================================================
# OpenCopilot 统一后台服务一键启动脚本
# ============================================================
# 启动 Agent (18888) + Broker (18889) + 知识图谱 (8090)
#
# ⚠️ 请在 macOS 原生 Terminal.app 或 iTerm2 中运行
#    不要用 IDE 内置终端（无法获取系统级权限）
# ============================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 未找到 venv，请先创建虚拟环境: python3 -m venv venv"
    exit 1
fi

source venv/bin/activate

# 检查必要依赖
if ! python -c "import uvicorn, httpx" &> /dev/null; then
    echo "📦 安装缺失依赖..."
    pip install uvicorn httpx python-dotenv
fi

echo ""
python start_backend.py "$@"
