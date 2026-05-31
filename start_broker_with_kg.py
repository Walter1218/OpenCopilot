#!/usr/bin/env python3
"""
统一启动脚本：Broker + 知识图谱API

用法:
    python start_broker_with_kg.py [--kg-port 8090]

说明:
    - Broker 服务：端口 18889（特权代理，系统级操作）
    - 知识图谱 API：端口 8090（可配置）
    
    两个服务在同一进程中运行，共享生命周期管理。
"""

import argparse
import asyncio
import signal
import sys
import os
import threading
import time
from pathlib import Path

# 添加项目根目录到 path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def start_knowledge_graph_api(host: str = "0.0.0.0", port: int = 8090):
    """在后台线程启动知识图谱API"""
    import uvicorn
    from knowledge_graph import start_api_server
    
    print(f"[知识图谱] 启动中... 端口: {port}")
    try:
        start_api_server(host=host, port=port, project_root=str(project_root))
    except Exception as e:
        print(f"[知识图谱] 启动失败: {e}")


def start_broker(host: str = "127.0.0.1", port: int = 18889):
    """启动Broker服务（主线程）"""
    import uvicorn
    
    print("=" * 55)
    print("  ASU Privileged Broker v1.1.0 + 知识图谱")
    print("=" * 55)
    print(f"  Broker 监听    : {host}:{port}")
    print(f"  知识图谱 监听   : 0.0.0.0:8090")
    print(f"  运行权限        : 原生终端 (非 IDE 沙盒)")
    print("-" * 55)
    print("  ⚠️  请确保在 macOS 原生 Terminal.app 中运行！")
    print("=" * 55 + "\n")
    
    # 注册信号处理，支持优雅关闭
    def _handle_exit(signum, frame):
        print("\n[Broker] 收到退出信号，正在关闭...")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, _handle_exit)
    signal.signal(signal.SIGINT, _handle_exit)
    
    # 启动 Broker
    uvicorn.run(
        "asu_broker.core.server:app",
        host=host,
        port=port,
        log_level="warning"
    )


def main():
    parser = argparse.ArgumentParser(description="启动 Broker + 知识图谱 API 服务")
    parser.add_argument("--kg-port", type=int, default=8090, help="知识图谱 API 端口 (默认: 8090)")
    parser.add_argument("--broker-port", type=int, default=18889, help="Broker 服务端口 (默认: 18889)")
    parser.add_argument("--no-kg", action="store_true", help="不启动知识图谱 API")
    
    args = parser.parse_args()
    
    # 在后台线程启动知识图谱API
    if not args.no_kg:
        kg_thread = threading.Thread(
            target=start_knowledge_graph_api,
            kwargs={"port": args.kg_port},
            daemon=True  # 设为守护线程，主进程退出时自动结束
        )
        kg_thread.start()
        # 等待知识图谱API启动
        time.sleep(2)
    
    # 在主线程启动Broker
    start_broker(port=args.broker_port)


if __name__ == "__main__":
    main()
