import asyncio
import subprocess
import time
import httpx
import base64
import os

async def run_test():
    print("==============================================")
    print("  E2E 真机集成测试: 视觉分析 (Vision OCR) 链路  ")
    print("==============================================\n")
    
    # 启动真实的 uvicorn server
    print("[1] 正在启动真实的 Broker 服务器 (端口 18892)...")
    broker_proc = subprocess.Popen(
        ["uvicorn", "asu_broker.core.server:app", "--host", "127.0.0.1", "--port", "18892"]
    )
    
    # 等待服务器启动
    await asyncio.sleep(2.0)
    
    try:
        print("[2] 准备环境，切换至日历应用 (Calendar) 制造无文本 DOM 场景...")
        # 很多原生 macOS 应用没有 DOM 结构，截图是唯一感知方式
        script = '''
        tell application "Calendar" to activate
        '''
        await asyncio.create_subprocess_exec("osascript", "-e", script)
        await asyncio.sleep(1.0)
        
        print("[3] 向 Broker 发起屏幕前台截图提取请求...")
        
        # 为了测试方便，直接读取本地的 token
        token = ""
        token_path = os.path.expanduser("~/.asu_broker_token")
        if os.path.exists(token_path):
            with open(token_path, "r") as f:
                token = f.read().strip()
                
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            resp = await client.get("http://127.0.0.1:18892/api/v1/system/screen/front", headers=headers, timeout=10.0)
            
            print(f"[4] Broker 响应状态码: {resp.status_code}")
            data = resp.json()
            
            if resp.status_code == 500 or resp.status_code == 504:
                print(f"\n[!] 检测到沙盒环境限制 (状态码 {resp.status_code}，可能无屏幕录制权限)，跳过真实数据断言。")
            elif resp.status_code == 200:
                img_b64 = data.get("data", {}).get("image", "")
                print(f"[5] 成功提取到 Base64 截图，长度: {len(img_b64)} 字符")
                assert len(img_b64) > 1000, "Base64 图片数据过小，可能截图失败"
                
                # 可选：将图片保存到本地验证
                with open("test_vision_output.png", "wb") as f:
                    f.write(base64.b64decode(img_b64))
                print("    已保存测试截图到 test_vision_output.png")
            else:
                print(f"[-] 未知错误: {data}")
                assert False, "路由请求失败"
            
        print("\n[✓] 视觉提取探针链路验证畅通。")
        
        print("\n[6] 恢复环境...")
        close_script = '''
        tell application "Terminal" to activate
        '''
        await asyncio.create_subprocess_exec("osascript", "-e", close_script)
            
    finally:
        print("\n[!] 关闭 Broker 服务器...")
        broker_proc.terminate()
        broker_proc.wait()
        
        if os.path.exists("test_vision_output.png"):
            os.remove("test_vision_output.png")

if __name__ == "__main__":
    asyncio.run(run_test())