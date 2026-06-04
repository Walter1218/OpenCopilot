"""gui/workers/chat.py module"""
import re
from PyQt6.QtCore import pyqtSignal, QThread
from opencopilot.agent.caller import call_agent_pipeline_sync
import json
class ChatWorker(QThread):
    text_updated = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, provider, text, session_id="default",
                 context_source="chat", context_meta=None):
        super().__init__()
        self.provider = provider
        self.text = text
        self.session_id = session_id
        self.context_source = context_source
        self.context_meta = context_meta or {}
        self._is_running = True

    def run(self):
        try:
            full_text = ""
            chunk_count = 0
            has_source = "source_text" in self.context_meta
            print(f"[ASU] ChatWorker开始 | session={self.session_id[:8]}... | has_source_text={has_source} | meta_keys={list(self.context_meta.keys())}")
            for chunk in self.provider.stream_agent_task(
                self.text, action_type="chat", session_id=self.session_id,
                is_new_task=False, context_source=self.context_source,
                context_meta=self.context_meta
            ):
                if not self._is_running:
                    print(f"[ASU] ChatWorker被中断 | chunks={chunk_count}")
                    break
                full_text += chunk
                chunk_count += 1
                
                # 过滤掉已闭合的 <think>...</think> 标签块
                display_text = re.sub(r'<think>.*?</think>', '', full_text, flags=re.DOTALL)
                
                # 如果存在未闭合的 <think> 标签，说明模型正在深度思考中
                if '<think>' in display_text:
                    display_text = display_text.split('<think>')[0] + "\n\n[🤔 AI正在深度思考中...]"
                    
                self.text_updated.emit(display_text.strip())
                
            print(f"[ASU] ChatWorker完成 | chunks={chunk_count} | output_len={len(full_text)}")
            self.full_text = full_text
        except Exception as e:
            print(f"[ASU] ChatWorker异常 | error={str(e)}")
            self.text_updated.emit(f"\n[错误]: {str(e)}")
            self.full_text = ""
            
        self.finished_signal.emit()

    def stop(self):
        self._is_running = False


