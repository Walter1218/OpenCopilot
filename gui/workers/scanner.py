"""gui/workers/scanner.py module"""
from PyQt6.QtCore import pyqtSignal, QThread
import httpx
class ModelScannerWorker(QThread):
    scan_finished = pyqtSignal(list, str)  # 返回模型列表或错误信息

    def __init__(self, api_base):
        super().__init__()
        self.api_base = api_base.strip().rstrip('/')

    def run(self):
        models = []
        error_msg = ""
        try:
            with httpx.Client(timeout=5.0, verify=False) as client:
                # 策略 1: 标准 OpenAI 兼容接口 /models
                try:
                    url = f"{self.api_base}/models"
                    response = client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        if "data" in data:
                            models = [m.get("id") for m in data["data"] if "id" in m]
                except Exception:
                    pass

                # 策略 2: Ollama 原生接口 /api/tags
                if not models:
                    try:
                        base_url = self.api_base.replace('/v1', '')
                        url = f"{base_url}/api/tags"
                        response = client.get(url)
                        if response.status_code == 200:
                            data = response.json()
                            if "models" in data:
                                models = [m.get("name") for m in data["models"] if "name" in m]
                    except Exception:
                        pass

                if not models:
                    error_msg = "连接成功，但未扫描到任何模型。请确保第三方服务已加载模型。"
        except Exception as e:
            error_msg = f"连接失败: {str(e)}\n请检查 API Base URL 是否正确以及服务是否启动。"

        self.scan_finished.emit(models, error_msg)

# ==========================================
# 设置对话框 UI
# ==========================================
