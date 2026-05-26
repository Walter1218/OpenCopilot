import uvicorn
import os
import sys
import signal

from core.auth import TOKEN_FILE, EXPECTED_TOKEN

if __name__ == "__main__":
    MASKED = f"{EXPECTED_TOKEN[:8]}...{EXPECTED_TOKEN[-8:]}" if len(EXPECTED_TOKEN) > 16 else "***"

    print("=" * 55)
    print("  ASU Privileged Broker v1.1.0")
    print("=" * 55)
    print(f"  Token 文件 : {TOKEN_FILE}")
    print(f"  Token      : {MASKED}")
    print(f"  监听地址   : 127.0.0.1:18889")
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
