#!/bin/bash

# =================================================================
# ASU Privileged Broker 一键启动脚本
# =================================================================
# 请不要在 IDE (如 Trae/VSCode) 的内置终端中运行此脚本。
# 必须双击此文件，或者在 macOS 原生 Terminal.app 中运行，
# 以确保 Broker 能够脱离沙盒，获取正确的系统级权限。

# 获取当前脚本所在目录的绝对路径
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "==========================================================="
echo "🚀 正在准备启动 ASU Privileged Broker (特权代理)..."
echo "==========================================================="

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "❌ 错误: 未找到虚拟环境 (venv)。请先运行 python3 -m venv venv 并安装依赖。"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查必要依赖
if ! python -c "import fastapi, uvicorn" &> /dev/null; then
    echo "📦 正在安装缺失的依赖 (fastapi, uvicorn)..."
    pip install fastapi uvicorn httpx
fi

# 启动 Broker
echo "✅ 环境检查通过！正在拉起后台服务..."
python asu_broker/run.py
