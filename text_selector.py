"""
⚠️  【已废弃】划词捕获程序 (Cmd+C 剪贴板方案)

本文件基于 pynput 监听鼠标拖拽并通过模拟 Cmd+C 获取选中文本。
由于 macOS 沙盒保护机制，模拟 Cmd+C 会导致 IDE/浏览器焦点丢失和光标消失。

当前 ASU 已采用 **原生拖拽 (Drag & Drop)** 方案替代此方案，
详见 smart_copilot.py 中的 AICardWindow.dropEvent()。

本文件保留仅供学习和参考，请勿在生产中使用。
"""

import time
import subprocess
import threading
import platform
from pynput import mouse, keyboard
import queue

class TextSelector:
    def __init__(self):
        self.is_dragging = False
        self.drag_start = None
        self.drag_end = None
        self.task_queue = queue.Queue()
        
        self.old_clipboard = self._get_clipboard()
        self.is_mac = platform.system() == 'Darwin'
        self.keyboard_controller = keyboard.Controller()

    def _get_clipboard(self):
        try:
            if platform.system() == 'Darwin':
                return subprocess.check_output(['pbpaste'], text=True)
            else:
                return ""
        except Exception:
            return ""

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
                            self.task_queue.put("CAPTURE")

    def capture_selected_text(self):
        try:
            if self.is_mac:
                with self.keyboard_controller.pressed(keyboard.Key.cmd):
                    self.keyboard_controller.press('c')
                    self.keyboard_controller.release('c')
            else:
                with self.keyboard_controller.pressed(keyboard.Key.ctrl):
                    self.keyboard_controller.press('c')
                    self.keyboard_controller.release('c')
            
            time.sleep(0.2)
            self._read_clipboard()
                
        except Exception as e:
            print(f"获取选中文本失败: {e}", flush=True)

    def _read_clipboard(self):
        try:
            new_clipboard = self._get_clipboard()
            
            if new_clipboard and new_clipboard != self.old_clipboard:
                print("\n" + "="*40)
                print("🎯 [成功捕获到选中文本]:")
                print(f"{new_clipboard}")
                print("="*40 + "\n", flush=True)
                self.old_clipboard = new_clipboard
            else:
                print("[Debug] 剪贴板内容未发生改变，或者未选中文本。", flush=True)
                
        except Exception as e:
            print(f"读取剪贴板失败: {e}", flush=True)

if __name__ == "__main__":
    print("⚠️  [已废弃] 划词捕获程序 (Cmd+C 方案)")
    print("   当前 ASU 已使用原生拖拽 (Drag & Drop) 替代此方案。")
    print()
    selector = TextSelector()
    
    print("📝 划词捕获程序(安全线程版)已启动...")
    print("操作方法：用鼠标左键在任意窗口【划选一段文本】，程序会自动捕获它。")
    print("🛑 按 Ctrl+C 停止监控。")
    
    # 启动后台监听线程
    listener = mouse.Listener(on_click=selector.on_click)
    listener.start()

    try:
        # 主线程循环处理任务
        while True:
            try:
                task = selector.task_queue.get(timeout=0.1)
                if task == "CAPTURE":
                    time.sleep(0.2)
                    selector.capture_selected_text()
            except queue.Empty:
                pass
    except KeyboardInterrupt:
        print("\n⏹️ 监控已停止。")
        listener.stop()
