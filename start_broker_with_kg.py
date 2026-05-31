#!/usr/bin/env python3
"""
统一启动脚本：Broker + 知识图谱API

用法:
    python start_broker_with_kg.py [--kg-port 8090] [--broker-port 18889]

说明:
    - Broker 服务：端口 18889（特权代理，系统级操作）
    - 知识图谱 API：端口 8090（可配置）
    
    两个服务在同一进程中运行，共享生命周期管理。
    
特性:
    - 自动清理占用端口的旧进程
    - 知识图谱 API 崩溃自动重启（最多3次）
    - 健康检查机制
    - 结构化日志输出
    - PID 文件管理
"""

import argparse
import logging
import signal
import subprocess
import sys
import os
import threading
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('UnifiedStarter')

# 常量
PID_FILE = project_root / '.unified_services.pid'
MAX_RESTART_ATTEMPTS = 3
RESTART_DELAY = 2  # 秒
HEALTH_CHECK_INTERVAL = 30  # 秒


def kill_port_process(port: int) -> bool:
    """检查端口占用，如果有进程占用则杀掉它"""
    try:
        # 使用 lsof 查找占用端口的进程
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True, text=True, timeout=5
        )
        pids = result.stdout.strip().split('\n')
        pids = [pid for pid in pids if pid]  # 过滤空行
        
        if not pids:
            return True  # 端口空闲
        
        for pid in pids:
            logger.info(f"端口 {port} 被进程 {pid} 占用，正在终止...")
            try:
                os.kill(int(pid), signal.SIGTERM)
                time.sleep(0.5)
                # 检查进程是否还活着
                os.kill(int(pid), 0)
                # 还活着，强制杀掉
                os.kill(int(pid), signal.SIGKILL)
                logger.info(f"进程 {pid} 已强制终止")
            except ProcessLookupError:
                logger.info(f"进程 {pid} 已终止")
            except PermissionError:
                logger.error(f"无权限终止进程 {pid}，请手动处理")
                return False
        
        time.sleep(0.5)  # 等待端口释放
        return True
    except Exception as e:
        logger.error(f"检查端口 {port} 时出错: {e}")
        return False


def check_health(port: int, service_name: str) -> bool:
    """检查服务健康状态"""
    try:
        import urllib.request
        url = f"http://127.0.0.1:{port}/health"
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def save_pid(kg_pid: int = None):
    """保存进程ID到文件"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(f"main_pid={os.getpid()}\n")
            if kg_pid:
                f.write(f"kg_pid={kg_pid}\n")
            f.write(f"started_at={datetime.now().isoformat()}\n")
    except Exception as e:
        logger.warning(f"保存PID文件失败: {e}")


def cleanup_pid():
    """清理PID文件"""
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception:
        pass


def start_knowledge_graph_api(host: str = "0.0.0.0", port: int = 8090):
    """在后台线程启动知识图谱API"""
    import uvicorn
    from knowledge_graph import start_api_server
    
    logger.info(f"知识图谱 API 启动中... 端口: {port}")
    try:
        start_api_server(host=host, port=port, project_root=str(project_root))
    except Exception as e:
        logger.error(f"知识图谱 API 启动失败: {e}")
        raise


def start_kg_with_restart(host: str = "0.0.0.0", port: int = 8090):
    """启动知识图谱API，支持崩溃自动重启"""
    restart_count = 0
    
    while restart_count < MAX_RESTART_ATTEMPTS:
        try:
            start_knowledge_graph_api(host=host, port=port)
        except Exception as e:
            restart_count += 1
            if restart_count < MAX_RESTART_ATTEMPTS:
                logger.warning(f"知识图谱 API 崩溃，{RESTART_DELAY}秒后第{restart_count}次重启...")
                time.sleep(RESTART_DELAY)
            else:
                logger.error(f"知识图谱 API 已崩溃{MAX_RESTART_ATTEMPTS}次，不再重启")


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
        logger.info("收到退出信号，正在关闭...")
        cleanup_pid()
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
    parser.add_argument("--no-cleanup", action="store_true", help="不自动清理占用端口的进程")
    parser.add_argument("--no-restart", action="store_true", help="不自动重启崩溃的知识图谱 API")
    
    args = parser.parse_args()
    
    # 自动清理占用端口的旧进程
    if not args.no_cleanup:
        logger.info("检查端口占用...")
        if not args.no_kg:
            kill_port_process(args.kg_port)
        kill_port_process(args.broker_port)
        logger.info("端口清理完成")
    
    # 保存PID
    save_pid()
    
    # 在后台线程启动知识图谱API
    if not args.no_kg:
        if args.no_restart:
            kg_thread = threading.Thread(
                target=start_knowledge_graph_api,
                kwargs={"port": args.kg_port},
                daemon=True
            )
        else:
            kg_thread = threading.Thread(
                target=start_kg_with_restart,
                kwargs={"port": args.kg_port},
                daemon=True
            )
        kg_thread.start()
        
        # 等待知识图谱API启动并检查健康
        logger.info("等待知识图谱 API 启动...")
        time.sleep(3)
        if check_health(args.kg_port, "知识图谱"):
            logger.info("知识图谱 API 启动成功 ✓")
        else:
            logger.warning("知识图谱 API 健康检查失败，但进程仍在运行")
    
    # 在主线程启动Broker
    start_broker(port=args.broker_port)


if __name__ == "__main__":
    main()
