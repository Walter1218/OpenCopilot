import time
import pyperclip
import threading
import platform
import pyautogui
from pynput import mouse

class TextSelector:
    def __init__(self):
        self.is_dragging = False
        self.drag_start = None
        self.drag_end = None
        
        self.old_clipboard = pyperclip.paste()
        self.is_mac = platform.system() == 'Darwin'

    def on_click(self, x, y, button, pressed):
        if button == mouse.Button.left:
            if pressed:
                self.is_dragging = True
                self.drag_start = (x, y)
            else:
                if self.is_dragging:
                    self.drag_end = (x, y)
                    self.is_dragging = False
                    
                    if self.drag_start and self.drag_end:
                        dx = abs(self.drag_end[0] - self.drag_start[0])
                        dy = abs(self.drag_end[1] - self.drag_start[1])
                        
                        if dx > 10 or dy > 10:
                            print(f"[Debug] 检测到拖拽动作，距离: dx={dx:.1f}, dy={dy:.1f}，准备获取文本...", flush=True)
                            threading.Timer(0.2, self.capture_selected_text).start()

    def capture_selected_text(self):
        try:
            # 使用 pyautogui 来模拟按键，它通常更可靠且跨平台
            if self.is_mac:
                pyautogui.hotkey('command', 'c')
            else:
                pyautogui.hotkey('ctrl', 'c')
            
            # 等待剪贴板写入完成
            time.sleep(0.2)
            
            new_clipboard = pyperclip.paste()
            
            if new_clipboard and new_clipboard != self.old_clipboard:
                print("\n" + "="*40)
                print("🎯 [成功捕获到选中文本]:")
                print(f"{new_clipboard}")
                print("="*40 + "\n", flush=True)
                self.old_clipboard = new_clipboard
            else:
                print("[Debug] 剪贴板内容未发生改变，或者未选中文本。", flush=True)
                
        except Exception as e:
            print(f"获取选中文本失败: {e}", flush=True)

if __name__ == "__main__":
    selector = TextSelector()
    
    print("📝 划词捕获程序(PyAutoGUI版)已启动...")
    print("操作方法：用鼠标左键在任意窗口【划选一段文本】，程序会自动捕获它。")
    print("🛑 按 Ctrl+C 停止监控。")
    
    try:
        with mouse.Listener(on_click=selector.on_click) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\n⏹️ 监控已停止。")
