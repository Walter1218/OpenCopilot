import asyncio
import subprocess
import time
import websockets
import json

async def run_test():
    print("==============================================")
    print("  E2E 真机集成测试: WebSocket 事件广播链路  ")
    print("==============================================\n")
    
    # 启动真实的 uvicorn server
    print("[1] 正在启动真实的 Broker 服务器 (端口 18890)...")
    broker_proc = subprocess.Popen(
        ["uvicorn", "asu_broker.core.server:app", "--host", "127.0.0.1", "--port", "18890"]
    )
    
    # 等待服务器启动
    await asyncio.sleep(2.0)
    
    try:
        print("[2] 连接 WebSocket...")
        async with websockets.connect("ws://127.0.0.1:18890/api/v1/events") as websocket:
            print("[3] 正在将前台切换至 Finder 初始化状态...")
            await asyncio.create_subprocess_exec("osascript", "-e", 'tell application "Finder" to activate')
            
            # 清空历史事件
            await asyncio.sleep(1.0)
            while True:
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=0.1)
                except asyncio.TimeoutError:
                    break
                    
            print("[4] 使用 osascript 触发真实系统应用切换 (切换到 'System Settings')...")
            await asyncio.create_subprocess_exec("osascript", "-e", 'tell application "System Settings" to activate')
            
            print("[5] 正在等待 WebSocket 推送...")
            msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            event = json.loads(msg)
            
            print(f"\n[✓] 测试通过！成功通过 WebSocket 接收到真实系统事件: \n    {event}")
            
            assert event["type"] == "app_activated"
            assert "com.apple.systempreferences" in event["bundle_id"]
            
            print("\n[6] 切回当前终端以恢复原状...")
            await asyncio.create_subprocess_exec("osascript", "-e", 'tell application "Terminal" to activate')
            
    finally:
        print("\n[!] 关闭 Broker 服务器...")
        broker_proc.terminate()
        broker_proc.wait()

if __name__ == "__main__":
    asyncio.run(run_test())