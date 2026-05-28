import asyncio
import os
import subprocess
import time
import logging
from asu_broker.probes.events_probe import start_events_probe

logging.basicConfig(level=logging.INFO)

async def main():
    print("==============================================")
    print("  E2E 真机集成测试: NSWorkspace 全局事件探针  ")
    print("  (完全禁止 Mock，通过 AppleScript 触发真实切换)")
    print("==============================================\n")
    
    events_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    
    print("[1] 正在启动底层事件探针线程...")
    success = start_events_probe(loop, events_queue)
    if not success:
        print("[!] 错误: PyObjC 环境未就绪或未授权，测试终止。")
        return
        
    print("[2] 探针已启动，正在将前台切换至 Finder 初始化状态...")
    await asyncio.create_subprocess_exec("osascript", "-e", 'tell application "Finder" to activate')
    await asyncio.sleep(1.0)
    
    # 清空可能存在的积压事件
    while not events_queue.empty():
        events_queue.get_nowait()
        
    print("[3] 使用 osascript 触发真实系统应用切换 (切换到 'System Settings')...")
    
    # 使用真实的 AppleScript 将"系统设置"调至前台，注意必须是异步调用，否则会阻塞主线程的 NSRunLoop Pump！
    await asyncio.create_subprocess_exec("osascript", "-e", 'tell application "System Settings" to activate')
    print("[OSAScript 完毕]")
    
    print("[4] 正在等待事件推送... (超时时间 5.0s)")
    
    try:
        # 等待事件，验证真机推送
        event = await asyncio.wait_for(events_queue.get(), timeout=5.0)
        print(f"\n[✓] 测试通过！成功捕获真实系统事件: \n    {event}")
        
        # 验证核心字段
        assert event["type"] == "app_activated", "事件类型不匹配"
        assert "com.apple.systempreferences" in event["bundle_id"], "Bundle ID 错误"
        
        print("\n[5] 切回当前终端以恢复原状...")
        # 恢复状态，避免打扰开发者当前窗口
        subprocess.run(["osascript", "-e", 'tell application "Terminal" to activate'])
        
    except asyncio.TimeoutError:
        print("\n[✗] 测试失败！3 秒内未能捕获到事件，请检查 macOS 辅助功能授权！")
    except AssertionError as e:
        print(f"\n[✗] 测试失败！数据断言不通过: {e}")

if __name__ == "__main__":
    asyncio.run(main())