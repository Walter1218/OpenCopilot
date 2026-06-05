#!/bin/bash

# Smart Copilot API 启动脚本

echo "🚀 启动 Smart Copilot API 服务..."
echo ""

# 检查 Python 环境
if ! command -v python &> /dev/null; then
    echo "❌ 未找到 Python，请先安装 Python"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
python -c "import fastapi; import uvicorn; import httpx" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  缺少依赖，正在安装..."
    pip install fastapi uvicorn httpx python-dotenv python-pptx
fi

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 启动参数
HOST=${1:-"0.0.0.0"}
PORT=${2:-8000}

echo ""
echo "📖 API 文档: http://localhost:${PORT}/docs"
echo "📖 ReDoc: http://localhost:${PORT}/redoc"
echo ""
echo "🛑 按 Ctrl+C 停止服务"
echo ""

# 启动服务
python -m uvicorn smart_copilot_api:app --host $HOST --port $PORT --reload
