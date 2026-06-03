#!/usr/bin/env python3
"""
统一后台服务启动脚本：Agent + Broker + 知识图谱 API

用法:
    python start_backend.py [--agent-port 18888] [--broker-port 18889] [--kg-port 8090]

后台服务:
    - Agent 服务 (port 18888): AI 管线（中间件链 → LLM），SSE 流式接口
    - Broker 服务 (port 18889): 特权代理（系统焦点监听、无感划词、屏幕抓取）
    - 知识图谱 API (port 8090): 项目知识查询

特性:
    - 自动清理占用端口的旧进程（避免端口冲突）
    - 每个服务启动后健康检查（最多等待 10s）
    - Ctrl+C 优雅关闭所有服务
    - PID 文件管理（.backend_services.pid）
    - 每个服务支持崩溃自动重启（Agent 最多3次，KG 最多3次）
    - 支持选择性启动（--no-agent / --no-kg / --no-broker）
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
from typing import Optional

# 添加项目根目录到 path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)-12s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('BackendStarter')

# 常量
PID_FILE = project_root / '.backend_services.pid'
MAX_RESTART = 3
RESTART_DELAY = 2  # 秒
HEALTH_WAIT = 10   # 健康检查最长等待时间（秒）


# ============================================================
# 端口管理
# ============================================================

def kill_port_process(port: int) -> bool:
    """检查并强制释放指定端口"""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True, text=True, timeout=5
        )
        pids = [p for p in result.stdout.strip().split('\n') if p]
        if not pids:
            return True

        for pid in pids:
            logger.info(f"  端口 {port} 被 PID={pid} 占用，正在终止...")
            try:
                os.kill(int(pid), signal.SIGTERM)
                time.sleep(0.3)
                os.kill(int(pid), 0)           # 还活着 → SIGKILL
                os.kill(int(pid), signal.SIGKILL)
                logger.info(f"  PID={pid} 已强制终止")
            except ProcessLookupError:
                pass
            except PermissionError:
                logger.error(f"  无权限终止 PID={pid}（端口 {port}），请手动处理")
                return False

        time.sleep(0.5)
        return True
    except Exception as e:
        logger.error(f"  检查端口 {port} 时出错: {e}")
        return False


def is_port_free(port: int) -> bool:
    """判断端口是否空闲"""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}", "-t"],
            capture_output=True, text=True, timeout=3
        )
        return not result.stdout.strip()
    except Exception:
        return False


# ============================================================
# 健康检查
# ============================================================

def health_check(port: int, name: str, timeout: float = HEALTH_WAIT) -> bool:
    """轮询等待服务就绪"""
    import urllib.request
    start = time.time()
    url = f"http://127.0.0.1:{port}/health"
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


# ============================================================
# PID 管理
# ============================================================

def save_pid(agent_pid=None, kg_pid=None):
    """写入 PID 文件"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(f"main_pid={os.getpid()}\n")
            f.write(f"started_at={datetime.now().isoformat()}\n")
            if agent_pid:
                f.write(f"agent_pid={agent_pid}\n")
            if kg_pid:
                f.write(f"kg_pid={kg_pid}\n")
    except Exception as e:
        logger.warning(f"PID 写入失败: {e}")


def cleanup_pid():
    """删除 PID 文件"""
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception:
        pass


# ============================================================
# 服务启动器
# ============================================================

def start_agent_subprocess(port: int = 18888) -> Optional[subprocess.Popen]:
    """以子进程启动 Agent 服务"""
    logger.info(f"Agent 服务启动中... 端口: {port}")
    try:
        proc = subprocess.Popen(
            [sys.executable, str(project_root / "asu_custom_agent.py")],
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return proc
    except Exception as e:
        logger.error(f"Agent 启动失败: {e}")
        return None


def start_agent_with_restart(port: int = 18888):
    """带重启保护的 Agent 启动（子进程）"""
    for attempt in range(MAX_RESTART):
        proc = start_agent_subprocess(port)
        if proc is None:
            if attempt < MAX_RESTART - 1:
                logger.warning(f"  {RESTART_DELAY}s 后第 {attempt+1} 次重试...")
                time.sleep(RESTART_DELAY)
                continue
            else:
                break
        # 等待子进程结束（崩溃时退出）
        ret = proc.wait()
        logger.error(f"Agent 进程退出 (code={ret})")
        if attempt < MAX_RESTART - 1:
            logger.warning(f"  {RESTART_DELAY}s 后第 {attempt+1} 次重启...")
            time.sleep(RESTART_DELAY)
        else:
            logger.error(f"Agent 已崩溃 {MAX_RESTART} 次，不再重启")
            break


def start_broker_blocking(host: str = "127.0.0.1", port: int = 18889):
    """启动 Broker（主线程阻塞，直到收到退出信号）"""
    import uvicorn
    logger.info(f"Broker 启动中... 端口: {port}")

    uvicorn.run(
        "asu_broker.core.server:app",
        host=host,
        port=port,
        log_level="warning"
    )


def start_kg(host: str = "0.0.0.0", port: int = 8090):
    """在子线程启动知识图谱 API"""
    logger.info(f"知识图谱 API 启动中... 端口: {port}")
    from knowledge_graph import start_api_server
    start_api_server(host=host, port=port, project_root=str(project_root))


def start_kg_with_restart(host: str = "0.0.0.0", port: int = 8090):
    """带重启保护的知识图谱启动"""
    for attempt in range(MAX_RESTART):
        try:
            start_kg(host=host, port=port)
        except Exception as e:
            logger.error(f"知识图谱崩溃: {e}")
            if attempt < MAX_RESTART - 1:
                logger.warning(f"  {RESTART_DELAY}s 后第 {attempt+1} 次重启...")
                time.sleep(RESTART_DELAY)
            else:
                logger.error(f"知识图谱已崩溃 {MAX_RESTART} 次，不再重启")
                break


# ============================================================
# 主流程
# ============================================================

def print_banner(broker_port, agent_port, kg_port, no_agent, no_kg):
    """打印启动横幅"""
    print()
    print("=" * 58)
    print("  OpenCopilot 统一后台服务 v1.0")
    print("=" * 58)
    services = []
    if not no_agent:
        services.append(f"  ✅ Agent       → 127.0.0.1:{agent_port}  (AI 管线)")
    else:
        services.append(f"  ❌ Agent        (已跳过)")
    services.append(f"  ✅ Broker      → 127.0.0.1:{broker_port}  (特权代理)")
    if not no_kg:
        services.append(f"  ✅ 知识图谱    → 0.0.0.0:{kg_port}  (项目知识)")
    else:
        services.append(f"  ❌ 知识图谱     (已跳过)")
    for s in services:
        print(s)
    print("-" * 58)
    print("  ⚠️  请在 macOS 原生 Terminal.app / iTerm2 中运行")
    print("  🛑 按 Ctrl+C 停止所有服务")
    print("=" * 58)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="统一启动 OpenCopilot 后台服务（Agent + Broker + KG）"
    )
    parser.add_argument("--agent-port", type=int, default=18888, help="Agent 端口 (默认 18888)")
    parser.add_argument("--broker-port", type=int, default=18889, help="Broker 端口 (默认 18889)")
    parser.add_argument("--kg-port", type=int, default=8090, help="知识图谱 API 端口 (默认 8090)")
    parser.add_argument("--no-agent", action="store_true", help="不启动 Agent")
    parser.add_argument("--no-kg", action="store_true", help="不启动知识图谱")
    parser.add_argument("--no-broker", action="store_true", help="不启动 Broker")
    parser.add_argument("--no-cleanup", action="store_true", help="不自动清理端口占用")
    parser.add_argument("--no-restart", action="store_true", help="崩溃不自动重启")

    args = parser.parse_args()

    agent_port = args.agent_port
    broker_port = args.broker_port
    kg_port = args.kg_port

    # ---- 端口清理 ----
    if not args.no_cleanup:
        logger.info("检查端口占用...")
        all_ok = True
        if not args.no_agent:
            all_ok &= kill_port_process(agent_port)
        if not args.no_broker:
            all_ok &= kill_port_process(broker_port)
        if not args.no_kg:
            all_ok &= kill_port_process(kg_port)
        if not all_ok:
            logger.error("端口清理失败，请手动处理后重试")
            sys.exit(1)
        logger.info("端口清理完成 ✓")

    # 打印横幅
    if not args.no_broker:
        print_banner(broker_port, agent_port, kg_port, args.no_agent, args.no_kg)

    # ---- 信号处理 ----
    shutdown_event = threading.Event()

    def _shutdown(signum, frame):
        if not shutdown_event.is_set():
            shutdown_event.set()
            logger.info("收到退出信号，正在关闭所有服务...")
            # 杀掉 Agent 子进程
            kill_port_process(agent_port)
            cleanup_pid()
            sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # ---- 保存 PID ----
    save_pid()

    # ---- 启动服务 ----
    threads = {}

    # 1) Agent（子线程 → 子进程）
    if not args.no_agent:
        target = start_agent_subprocess if args.no_restart else start_agent_with_restart
        t = threading.Thread(
            target=target, kwargs={"port": agent_port}, daemon=True, name="Agent"
        )
        t.start()
        threads["agent"] = t

    # 2) 知识图谱（子线程）
    if not args.no_kg:
        target = start_kg if args.no_restart else start_kg_with_restart
        t = threading.Thread(
            target=target, kwargs={"port": kg_port}, daemon=True, name="KG"
        )
        t.start()
        threads["kg"] = t

    # ---- 启动后健康检查 ----
    time.sleep(2)  # 留一点启动窗口

    if not args.no_agent:
        logger.info("等待 Agent 就绪...")
        if health_check(agent_port, "Agent"):
            logger.info("Agent 就绪 ✓")
        else:
            logger.warning("Agent 健康检查超时（进程可能仍在启动中）")

    if not args.no_kg:
        logger.info("等待知识图谱就绪...")
        if health_check(kg_port, "知识图谱"):
            logger.info("知识图谱就绪 ✓")
        else:
            logger.warning("知识图谱健康检查超时（进程可能仍在启动中）")

    # ---- 主线程：Broker（阻塞） ----
    if not args.no_broker:
        try:
            start_broker_blocking(port=broker_port)
        except KeyboardInterrupt:
            pass
    else:
        # 没有 Broker 阻塞，主线程等待 Ctrl+C
        logger.info("所有服务已启动，按 Ctrl+C 停止")
        try:
            while not shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    # ---- 清理 ----
    if not args.no_agent:
        kill_port_process(agent_port)
    cleanup_pid()
    logger.info("所有服务已关闭")


if __name__ == "__main__":
    main()
