import asyncio
import subprocess

async def get_selected_text_via_applescript() -> str:
    """
    [预埋] 通过 AppleScript 发送 Cmd+C 然后读取剪贴板。
    注意：此方法为兜底方案，在某些 IDE 中仍可能导致光标丢失。
    更优雅的底层方案是未来集成 pyobjc 直接调用 AXUIElementCopyAttribute。
    """
    script = '''
    tell application "System Events"
        keystroke "c" using command down
        delay 0.1
    end tell
    return the clipboard as text
    '''
    
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
            raise Exception(f"获取选中内容失败: {stderr.decode('utf-8').strip()}")
    except Exception as e:
        raise e

async def get_clipboard_content() -> str:
    """[预埋] 静默读取系统剪贴板当前内容（纯文本）。"""
    try:
        process = await asyncio.create_subprocess_exec(
            'pbpaste',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=1.0)
        return stdout.decode('utf-8').strip()
    except Exception as e:
        raise Exception(f"读取剪贴板失败: {str(e)}")

async def set_clipboard_content(text: str) -> bool:
    """[预埋] 静默将内容写入系统剪贴板（用于 AI 自动回写代码等场景）。"""
    try:
        process = await asyncio.create_subprocess_exec(
            'pbcopy',
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await asyncio.wait_for(process.communicate(input=text.encode('utf-8')), timeout=1.0)
        return process.returncode == 0
    except Exception as e:
        raise Exception(f"写入剪贴板失败: {str(e)}")
