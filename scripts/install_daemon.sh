#!/bin/bash
# ============================================================
# 【⚠️ 废弃警告 DEPRECATED】
# 该脚本在 P1 阶段架构重构前用于安装 Agent 守护进程。
# 目前 UI 与 Agent 已合并，不再需要作为独立守护进程运行。
# 生产环境请使用 `bash scripts/install_broker_daemon.sh` 安装底层探针。
# ============================================================

echo "❌ [DEPRECATED] 该脚本已废弃。"
echo "💡 生产环境只需安装底层特权探针，请运行: bash scripts/install_broker_daemon.sh"
echo "💡 前端 UI (smart_copilot.py) 将在后续 P3 阶段直接打包为 macOS .app 应用程序。"
exit 1
