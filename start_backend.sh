#!/bin/bash
# ============================================================
# OpenCopilot 后台服务一键启动脚本
# ============================================================
# API Gateway (8000) + Broker (18889) + 知识图谱 (8090, 自动)
#
# ⚠️ 请在 macOS 原生 Terminal.app 或 iTerm2 中运行
#    不要用 IDE 内置终端（无法获取系统级权限）
# ============================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# 自动释放冲突端口
for PORT in 8000 18889 8090; do
    PIDS=$(lsof -i :$PORT -t 2>/dev/null)
    for PID in $PIDS; do
        if [ -n "$PID" ]; then
            echo "🔧 释放端口 $PORT（PID=$PID）..."
            kill $PID 2>/dev/null && sleep 0.3
            kill -0 $PID 2>/dev/null && kill -9 $PID 2>/dev/null
        fi
    done
done

# 检查虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo ""
echo "========================================================="
echo "  OpenCopilot 后台服务启动"
echo "========================================================="
echo "  ✅ API Gateway → 0.0.0.0:8000 (Agent Pipeline + 平台 + KG)"
echo "  ✅ Broker      → 127.0.0.1:18889 (系统探针)"
echo "  ⚠️  请确保在 macOS 原生终端中运行"
echo "  🛑 按 Ctrl+C 停止"
echo "========================================================="
echo ""

# 启动 Broker（后台）
python asu_broker/run.py &
BROKER_PID=$!

# 启动 API Gateway（前台，Ctrl+C 全部停止）
uvicorn smart_copilot_api:app --host 0.0.0.0 --port 8000

# 清理
kill $BROKER_PID 2>/dev/null
echo ""
echo "所有服务已停止"
