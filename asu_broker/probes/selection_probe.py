import asyncio
import subprocess
import logging

logger = logging.getLogger(__name__)

try:
    from AppKit import NSWorkspace
    import ApplicationServices
    HAS_PYOBJC = True
except ImportError:
    HAS_PYOBJC = False

async def get_selected_text_via_axapi() -> str:
    """
    通过 macOS Accessibility API (AXUIElement) 尝试直接读取当前系统焦点的高亮文本。
    这种方法完全不会污染剪贴板，也不会导致 IDE (如 VS Code/Trae) 的光标丢失。
    """
    if not HAS_PYOBJC:
        logger.warning("PyObjC not installed, AXUIElement extraction skipped.")
        return ""
        
    try:
        # 1. 确保系统授权了辅助功能权限
        if not ApplicationServices.AXIsProcessTrusted():
            logger.warning("Accessibility permission is missing. Cannot use AXUIElement.")
            return ""

        # 2. 获取当前最前台应用
        workspace = NSWorkspace.sharedWorkspace()
        front_app = workspace.frontmostApplication()
        if not front_app:
            return ""
            
        pid = front_app.processIdentifier()
        
        # 3. 获取前台应用的系统级 UI 元素 (AXUIElement)
        app_ref = ApplicationServices.AXUIElementCreateApplication(pid)
        
        # 4. 获取当前焦点元素 (Focused UI Element)
        err, focused_elem = ApplicationServices.AXUIElementCopyAttributeValue(
            app_ref, "AXFocusedUIElement", None
        )
        if err != 0 or not focused_elem:
            return ""
            
        # 5. 尝试从焦点元素中获取选中的文本 (AXSelectedText)
        err, selected_text = ApplicationServices.AXUIElementCopyAttributeValue(
            focused_elem, "AXSelectedText", None
        )
        if err == 0 and selected_text:
            return str(selected_text)
            
        return ""
    except Exception as e:
        logger.error(f"AXAPI Selection Extraction failed: {e}")
        return ""

async def get_selected_text() -> str:
    """
    智能选区提取入口：
    优先使用原生的 AXUIElement 读取选区（无副作用）；
    如果失败或应用不支持 AXSelectedText（如某些非标 Electron 应用），则优雅降级到模拟 Cmd+C。
    """
    # 尝试无感提取
    text = await get_selected_text_via_axapi()
    if text and text.strip():
        logger.info("Successfully extracted selection via AXAPI.")
        return text.strip()
        
    # 降级方案
    logger.info("Falling back to Cmd+C extraction.")
    return await get_selected_text_via_applescript()

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
