"""gui/workers/browser.py module"""
from PyQt6.QtCore import pyqtSignal, QThread
import httpx
class BrowserReaderWorker(QThread):
    """后台线程：通过特权代理读取浏览器 DOM，避免阻塞 UI 并穿透沙盒。"""
    finished = pyqtSignal(str, str)   # browser_name, text (empty on error)
    error = pyqtSignal(str)           # error message

    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.client = SystemProbeClient()

    def run(self):
        try:
            # 检查代理是否在线
            if not self.client.is_broker_alive():
                self.error.emit(
                    "❌ 无法连接到 Privileged Broker。\n\n"
                    "在 Trae 等沙盒终端内无法直接读取浏览器内容。\n"
                    "请打开 macOS 原生 Terminal.app，执行：\n"
                    "python3 asu_broker/run.py"
                )
                return
                
            text = self.client.get_browser_dom(self.browser)
            if text:
                self.finished.emit(self.browser, text)
            else:
                self.error.emit(f"❌ 从 {self.browser} 读取的内容为空。")
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.error.emit(f"❌ 读取失败: {e}")


# ==========================================
# 2. 鼠标监听线程（双击 + 三击右键）
# ==========================================
