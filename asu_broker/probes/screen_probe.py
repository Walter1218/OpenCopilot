import asyncio
import subprocess
import os
import base64
import tempfile

async def capture_screen_area(x: int, y: int, width: int, height: int) -> str:
    """
    [预埋] 视觉能力：静默截取屏幕特定区域，并返回 Base64 编码的图像数据。
    用途：当某些软件（如 PDF、设计软件、远程桌面）无法通过 DOM 或 AXAPI 获取文本时，
    ASU Copilot 可以直接截图并调用具备 Vision 能力的多模态 LLM（如 GPT-4o 或 MiniMax-Vision）进行 OCR 或视觉理解。
    """
    try:
        # 使用临时文件保存截图
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        
        # screencapture 参数:
        # -x: 静音，无快门声
        # -R: 指定截图区域 "x,y,width,height"
        rect_str = f"{x},{y},{width},{height}"
        
        process = await asyncio.create_subprocess_exec(
            'screencapture', '-x', '-R', rect_str, temp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await asyncio.wait_for(process.communicate(), timeout=3.0)
        
        if process.returncode != 0:
            raise Exception("截图失败")
            
        # 读取并进行 Base64 编码
        with open(temp_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
        # 清理临时文件
        os.remove(temp_path)
        
        return encoded_string
    except Exception as e:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        raise Exception(f"视觉探针捕获失败: {str(e)}")

async def capture_front_window() -> str:
    """
    [预埋] 视觉能力：静默截取当前最前台的窗口。
    """
    try:
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        
        # screencapture 参数: -x (静音), -l (指定窗口 ID, 配合 AppleScript 可获取当前窗口 ID, 这里使用更直接的基于焦点的截取方案)
        # 注意：由于权限限制，全屏或跨窗口截图需要 "屏幕录制" 权限
        process = await asyncio.create_subprocess_exec(
            'screencapture', '-x', '-W', temp_path, # -W 截取整个窗口
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await asyncio.wait_for(process.communicate(), timeout=3.0)
        
        with open(temp_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
        os.remove(temp_path)
        return encoded_string
    except Exception as e:
        raise Exception(f"捕获前台窗口失败: {str(e)}")
