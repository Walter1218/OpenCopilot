import subprocess
import asyncio

SUPPORTED_BROWSERS = ["Google Chrome", "Safari", "Brave Browser", "Microsoft Edge", "Arc"]

async def get_browser_tabs() -> str:
    """获取所有支持的基于 Chromium 的浏览器的标签页信息。"""
    # 这里我们优先探测 Google Chrome，后续可扩展为遍历所有活跃浏览器
    script = '''
    tell application "Google Chrome"
        set tabInfo to ""
        repeat with w in windows
            repeat with t in tabs of w
                set tabInfo to tabInfo & title of t & " | " & URL of t & "\\n"
            end repeat
        end repeat
        return tabInfo
    end tell
    '''
    
    # 异步执行 osascript，避免阻塞 FastAPI 主事件循环
    try:
        process = await asyncio.create_subprocess_exec(
            'osascript', '-e', script,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
        
        if process.returncode == 0:
            return stdout.decode('utf-8').strip()
        else:
            raise Exception(f"AppleScript error: {stderr.decode('utf-8').strip()}")
    except asyncio.TimeoutError:
        raise Exception("Timeout executing AppleScript")
    except Exception as e:
        raise e

async def get_active_tab_dom(browser_name: str) -> str:
    """获取指定浏览器当前激活标签页的全文 (innerText)。"""
    if browser_name not in SUPPORTED_BROWSERS:
        raise ValueError(f"Unsupported browser: {browser_name}")
        
    script = ""
    if browser_name in ["Google Chrome", "Brave Browser", "Microsoft Edge", "Arc"]:
        script = f'''
        tell application "{browser_name}"
            execute front window's active tab javascript "document.body.innerText;"
        end tell
        '''
    elif browser_name == "Safari":
        script = '''
        tell application "Safari"
            do JavaScript "document.body.innerText;" in document 1
        end tell
        '''
        
    try:
        process = await asyncio.create_subprocess_exec(
            'osascript', '-e', script,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
        
        if process.returncode == 0:
            return stdout.decode('utf-8').strip()
        else:
            err_msg = stderr.decode('utf-8').strip()
            if "JavaScript" in err_msg or "privilege" in err_msg.lower():
                raise Exception("权限被拒绝：请确保在浏览器开发者菜单中开启了 'Allow JavaScript from Apple Events'。")
            raise Exception(f"AppleScript error: {err_msg}")
    except asyncio.TimeoutError:
        raise Exception("读取 DOM 超时，浏览器可能无响应。")
    except Exception as e:
        raise e
