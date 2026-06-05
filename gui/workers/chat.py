"""gui/workers/chat.py module"""
import re
import threading
from PyQt6.QtCore import pyqtSignal, QThread
from opencopilot.agent.caller import call_agent_pipeline_sync
import json
class ChatWorker(QThread):
    text_updated = pyqtSignal(str)
    finished_signal = pyqtSignal()

    _next_id = 0  # 类变量，进程级自增

    def __init__(self, provider, text, session_id="default",
                 context_source="chat", context_meta=None):
        super().__init__()
        ChatWorker._next_id += 1
        self._wid = ChatWorker._next_id
        self.provider = provider
        self.text = text
        self.session_id = session_id
        self.context_source = context_source
        self.context_meta = context_meta or {}
        self._is_running = True
        self._cancel_event = threading.Event()
        self.full_text = ""

    def run(self):
        from opencopilot.agent.observability import PipelineObservability
        obs = PipelineObservability.get_instance()
        obs.worker_log(self._wid, "ChatWorker", f"START | text={self.text[:30]} | session={self.session_id[:8]}")
        
        try:
            full_text = ""
            chunk_count = 0
            has_source = "source_text" in self.context_meta
            print(f"[ASU] ChatWorker开始 | session={self.session_id[:8]}... | has_source_text={has_source} | meta_keys={list(self.context_meta.keys())}")
            # 使用统一的 Agent Pipeline 调用器（provider.stream_agent_task 已废弃）
            for chunk in call_agent_pipeline_sync(
                self.text, action_type="chat", session_id=self.session_id,
                is_new_task=False, context_source=self.context_source,
                context_meta=self.context_meta,
                cancel_event=self._cancel_event
            ):
                if not self._is_running:
                    obs.worker_log(self._wid, "ChatWorker", f"CANCELLED | chunks={chunk_count}")
                    print(f"[ASU] ChatWorker被中断 | chunks={chunk_count}")
                    break
                full_text += chunk
                chunk_count += 1
                
                # 过滤掉已闭合的 <think>...</think> 标签块
                display_text = re.sub(r'<think>.*?</think>', '', full_text, flags=re.DOTALL)
                
                # 如果存在未闭合的 <think> 标签，说明模型正在深度思考中
                if '<think>' in display_text:
                    display_text = display_text.split('<think>')[0] + "\n\n[🤔 AI正在深度思考中...]"
                
                obs.worker_log(self._wid, "ChatWorker", f"emit text_updated | chunk#{chunk_count} len={len(display_text)}")
                self.text_updated.emit(display_text.strip())
            
            obs.worker_log(self._wid, "ChatWorker", f"FINISHED | chunks={chunk_count} | output_len={len(full_text)}")
            print(f"[ASU] ChatWorker完成 | chunks={chunk_count} | output_len={len(full_text)}")
            self.full_text = full_text
        except Exception as e:
            obs.worker_log(self._wid, "ChatWorker", f"ERROR | {e}")
            print(f"[ASU] ChatWorker异常 | error={str(e)}")
            self.text_updated.emit(f"\n[错误]: {str(e)}")
            self.full_text = ""
        
        obs.worker_log(self._wid, "ChatWorker", "emit finished_signal")
        self.finished_signal.emit()

    def stop(self):
        """停止 worker 并取消管线"""
        self._is_running = False
        self._cancel_event.set()


