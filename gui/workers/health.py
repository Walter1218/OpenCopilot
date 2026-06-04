"""gui/workers/health.py module"""
from PyQt6.QtCore import pyqtSignal, QThread
class AgentHealthWorker(QThread):
    """异步探活 Agent 后台服务，不阻塞主线程。"""
    health_result = pyqtSignal(bool, int)  # (is_alive, active_sessions)

    AGENT_URL = "http://127.0.0.1:18888/health"

    def run(self):
        try:
            resp = httpx.get(self.AGENT_URL, timeout=1.5)
            if resp.status_code == 200:
                data = resp.json()
                self.health_result.emit(True, data.get("active_sessions", 0))
                return
        except Exception:
            pass
        self.health_result.emit(False, 0)


