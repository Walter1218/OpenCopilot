import uvicorn
import os
import sys
import signal
import subprocess
import time
import secrets
from pathlib import Path

TOKEN_FILE = str(Path.home() / ".asu_broker_token")
try:
    with open(TOKEN_FILE) as f:
        EXPECTED_TOKEN = f.read().strip()
except FileNotFoundError:
    EXPECTED_TOKEN = secrets.token_hex(32)
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        f.write(EXPECTED_TOKEN)
    os.chmod(TOKEN_FILE, 0o600)

if __name__ == "__main__":
    MASKED = f"{EXPECTED_TOKEN[:8]}...{EXPECTED_TOKEN[-8:]}" if len(EXPECTED_TOKEN) > 16 else "***"
    BROKER_PORT = 18889

    # 自动释放占用端口
    try:
        result = subprocess.run(["lsof", "-i", f":{BROKER_PORT}", "-t"], capture_output=True, text=True, timeout=3)
        for pid in result.stdout.strip().split('\n'):
            if pid and pid != str(os.getpid()):
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    time.sleep(0.3)
                    os.kill(int(pid), 0)
                    os.kill(int(pid), signal.SIGKILL)
                    print(f"🔧 已释放端口 {BROKER_PORT}（原占用 PID={pid}）")
                except (ProcessLookupError, PermissionError):
                    pass
    except Exception:
        pass

    print("=" * 55)
    print("  ASU Privileged Broker v1.1.0")
    print("=" * 55)
    print(f"  Token 文件 : {TOKEN_FILE}")
    print(f"  Token      : {MASKED}")
    print(f"  监听地址   : 127.0.0.1:{BROKER_PORT}")
    print(f"  运行权限   : 原生终端 (非 IDE 沙盒)")
    print("-" * 55)
    print("  ⚠️  请确保在 macOS 原生 Terminal.app 中运行！")
    print("  ⚠️  IDE 内置终端会继承沙盒限制，导致(-10004)权限错误。")
    print("=" * 55 + "\n")

    # 注册信号处理，支持优雅关闭
    def _handle_exit(signum, frame):
        print("\n[Broker] 收到退出信号，正在关闭...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_exit)
    signal.signal(signal.SIGINT, _handle_exit)

    # 强制绑定到 127.0.0.1 保证安全性
    uvicorn.run(
        "core.server:app",
        host="127.0.0.1",
        port=18889,
        log_level="warning"  # 减少 uvicorn 内部日志噪音，主要日志由中间件输出
    )
