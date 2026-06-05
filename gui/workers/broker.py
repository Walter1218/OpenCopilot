"""gui/workers/broker.py module"""
import asyncio, json, websockets
from PyQt6.QtCore import pyqtSignal, QThread
class BrokerEventsWorker(QThread):
    app_activated = pyqtSignal(str, str)
    connection_status = pyqtSignal(bool)

    def __init__(self, broker_url="ws://127.0.0.1:18889/api/v1/events"):
        super().__init__()
        self.broker_url = broker_url
        self._is_running = True
        
    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._listen())
        finally:
            loop.close()
            
    async def _listen(self):
        while self._is_running:
            try:
                async with websockets.connect(self.broker_url, close_timeout=1.0) as ws:
                    self.connection_status.emit(True)
                    print("[ASU Client] 已连接到 Broker WebSocket.")
                    while self._is_running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        if data.get("type") == "app_activated":
                            self.app_activated.emit(data.get("app_name", ""), data.get("bundle_id", ""))
            except Exception as e:
                self.connection_status.emit(False)
                await asyncio.sleep(2)

