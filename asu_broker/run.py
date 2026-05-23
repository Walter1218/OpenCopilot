import uvicorn
import os
import sys

# 打印生成的 Token 路径，方便测试
from core.auth import TOKEN_FILE, EXPECTED_TOKEN

if __name__ == "__main__":
    print("="*50)
    print("🚀 ASU Privileged Broker 启动中...")
    print(f"🔒 安全 Token 已保存至: {TOKEN_FILE}")
    print(f"🔑 当前 Token: {EXPECTED_TOKEN}")
    print("⚠️  请确保此进程在非沙盒的 macOS 原生终端中运行！")
    print("="*50)
    
    # 强制绑定到 127.0.0.1 保证安全性
    uvicorn.run("core.server:app", host="127.0.0.1", port=18889, log_level="info")
