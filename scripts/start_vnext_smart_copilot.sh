#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
API_BASE_URL="${SMART_COPILOT_API_BASE_URL:-http://127.0.0.1:8010}"
START_API_AUTO=1
FORWARD_ARGS=()
API_PID=""
API_BASE_URL_EXPLICIT=0

for arg in "$@"; do
    case "$arg" in
        --api-base-url=*)
            API_BASE_URL="${arg#*=}"
            API_BASE_URL_EXPLICIT=1
            FORWARD_ARGS+=("$arg")
            ;;
        --no-start-api)
            START_API_AUTO=0
            ;;
        *)
            FORWARD_ARGS+=("$arg")
            ;;
    esac
done

health_check() {
    local url="$1"
    python - <<PY
import sys
import urllib.request

url = "${url}".rstrip("/") + "/health"
try:
    with urllib.request.urlopen(url, timeout=1.5) as response:
        sys.exit(0 if response.status == 200 else 1)
except Exception:
    sys.exit(1)
PY
}

vnext_check() {
    local url="$1"
    python - <<PY
import json
import sys
import urllib.error
import urllib.request

url = "${url}".rstrip("/") + "/vnext/context/snapshots"
payload = json.dumps({"trigger": "probe"}).encode("utf-8")
request = urllib.request.Request(
    url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=2.0) as response:
        sys.exit(0 if response.status in (200, 422) else 1)
except urllib.error.HTTPError as exc:
    sys.exit(0 if exc.code == 422 else 1)
except Exception:
    sys.exit(1)
PY
}

cleanup() {
    if [ -n "$API_PID" ] && kill -0 "$API_PID" >/dev/null 2>&1; then
        kill "$API_PID" >/dev/null 2>&1 || true
        wait "$API_PID" >/dev/null 2>&1 || true
    fi
}

trap cleanup EXIT

cd "$PROJECT_DIR"

PYQT6_PLATFORMS=$(python -c "
import os, PyQt6
qt6_dir = os.path.join(os.path.dirname(PyQt6.__file__), 'Qt6', 'plugins', 'platforms')
print(qt6_dir if os.path.isdir(qt6_dir) else '')
" 2>/dev/null)

if [ -n "$PYQT6_PLATFORMS" ]; then
    export QT_QPA_PLATFORM_PLUGIN_PATH="$PYQT6_PLATFORMS"
fi

export SMART_COPILOT_API_BASE_URL="${API_BASE_URL%/}"

if ! health_check "$SMART_COPILOT_API_BASE_URL" || ! vnext_check "$SMART_COPILOT_API_BASE_URL"; then
    if [ "$START_API_AUTO" -eq 1 ]; then
        TARGET_URL="$SMART_COPILOT_API_BASE_URL"
        TARGET_PORT="8010"
        if health_check "$SMART_COPILOT_API_BASE_URL" && ! vnext_check "$SMART_COPILOT_API_BASE_URL"; then
            if [ "$SMART_COPILOT_API_BASE_URL" = "http://127.0.0.1:8010" ]; then
                echo "ℹ️  检测到 :8010 已有 API，但未挂载 vnext 路由，改用本地 :8000 继续探测"
                TARGET_URL="http://127.0.0.1:8000"
                TARGET_PORT="8000"
            else
                echo "❌ 当前 API 缺少 vnext 路由: $SMART_COPILOT_API_BASE_URL"
                exit 1
            fi
        else
            echo "ℹ️  未检测到可用 vnext API，自动启动 smart_copilot_api:app"
        fi
        if ! health_check "$TARGET_URL" || ! vnext_check "$TARGET_URL"; then
            python -m uvicorn smart_copilot_api:app --host 127.0.0.1 --port "$TARGET_PORT" >/tmp/vnext-smart-copilot-api.log 2>&1 &
            API_PID=$!
        fi
        export SMART_COPILOT_API_BASE_URL="$TARGET_URL"
        for _ in {1..30}; do
            if health_check "$SMART_COPILOT_API_BASE_URL" && vnext_check "$SMART_COPILOT_API_BASE_URL"; then
                break
            fi
            sleep 0.5
        done
    fi
fi

if ! health_check "$SMART_COPILOT_API_BASE_URL" || ! vnext_check "$SMART_COPILOT_API_BASE_URL"; then
    echo "❌ Unified API 不可用或未挂载 vnext: ${SMART_COPILOT_API_BASE_URL}"
    echo "请先启动正确的 API，或使用默认地址并允许脚本自动启动。"
    exit 1
fi

echo "✅ Unified API 已就绪: $SMART_COPILOT_API_BASE_URL"
echo "🚀 启动 Smart Copilot vNext Interactive Test UI..."
if [ "$API_BASE_URL_EXPLICIT" -eq 0 ]; then
    FORWARD_ARGS+=("--api-base-url=$SMART_COPILOT_API_BASE_URL")
fi
python -m gui_next.smart_copilot.app "${FORWARD_ARGS[@]}"
