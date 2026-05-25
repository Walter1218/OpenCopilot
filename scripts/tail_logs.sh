#!/bin/bash
# ============================================================
# ASU Agent 日志实时查看
# 功能：tail -f 实时追踪 Agent 守护进程的标准输出和错误输出
# 使用：bash scripts/tail_logs.sh
# ============================================================

LOG_DIR="$HOME/Library/Logs/ASU"
OUT_LOG="$LOG_DIR/agent_out.log"
ERR_LOG="$LOG_DIR/agent_err.log"

echo "============================================================"
echo "  ASU Agent 实时日志（按 Ctrl+C 退出）"
echo "  标准输出: $OUT_LOG"
echo "  错误输出: $ERR_LOG"
echo "============================================================"
echo ""

if [ ! -d "$LOG_DIR" ]; then
    echo "❌ 日志目录不存在，请先运行 install_daemon.sh"
    exit 1
fi

# 同时 tail 两个日志文件，并在前面加上区分前缀
tail -f "$OUT_LOG" "$ERR_LOG" 2>/dev/null | awk '
    /^==> / { current=$0; next }
    { 
        if (current ~ /agent_out/) prefix="[OUT] "
        else prefix="[ERR] "
        print prefix $0
    }
'
