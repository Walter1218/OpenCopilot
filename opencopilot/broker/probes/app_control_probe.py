import asyncio
import subprocess

async def get_notes_content(note_name: str = "") -> str:
    """
    [预埋] 读取 Apple 备忘录 (Notes) 内容。
    如果提供了 note_name，则读取特定备忘录；否则读取当前选中的备忘录。
    """
    if note_name:
        script = f'''
        tell application "Notes"
            set myNote to first note whose name contains "{note_name}"
            return body of myNote
        end tell
        '''
    else:
        script = '''
        tell application "Notes"
            if (count of selection) > 0 then
                return body of item 1 of selection
            else
                return "No note selected"
            end if
        end tell
        '''
        
    try:
        process = await asyncio.create_subprocess_exec(
            'osascript', '-e', script,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=3.0)
        
        if process.returncode == 0:
            # Notes 返回的通常是 HTML 格式，可能需要进一步清洗
            return stdout.decode('utf-8').strip()
        else:
            raise Exception(f"读取备忘录失败: {stderr.decode('utf-8').strip()}")
    except Exception as e:
        raise e

async def create_note(title: str, body: str) -> bool:
    """[预埋] 后台静默创建一个新的 Apple 备忘录。"""
    script = f'''
    tell application "Notes"
        tell account "iCloud"
            make new note at folder "Notes" with properties {{name:"{title}", body:"{body}"}}
        end tell
    end tell
    '''
    try:
        process = await asyncio.create_subprocess_exec(
            'osascript', '-e', script,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await asyncio.wait_for(process.communicate(), timeout=3.0)
        return process.returncode == 0
    except Exception as e:
        raise Exception(f"创建备忘录失败: {str(e)}")
