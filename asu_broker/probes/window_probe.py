import asyncio
import subprocess

async def get_frontmost_app() -> str:
    """获取当前系统处于最前台（焦点）的应用程序名称。"""
    script = 'tell application "System Events" to get name of first application process whose frontmost is true'
    
    try:
        process = await asyncio.create_subprocess_exec(
            'osascript', '-e', script,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=2.0)
        
        if process.returncode == 0:
            return stdout.decode('utf-8').strip()
        else:
            raise Exception(f"Failed to get frontmost app: {stderr.decode('utf-8').strip()}")
    except Exception as e:
        raise e
