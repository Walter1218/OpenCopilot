"""gui/workers/ai.py module"""
import re
import threading
from PyQt6.QtCore import pyqtSignal, QThread
from opencopilot.agent.caller import call_agent_pipeline_sync
from llm_provider import load_config
import json
class AIWorker(QThread):
    text_updated = pyqtSignal(str)
    finished_signal = pyqtSignal()

    _next_id = 0  # 类变量，进程级自增

    def __init__(self, provider, prompt, action_type="auto", session_id="default",
                 context_source="drag", context_meta=None, context_envelope=None,
                 image_base64=None):
        super().__init__()
        AIWorker._next_id += 1
        self._wid = AIWorker._next_id
        self.provider = provider
        self.prompt = prompt
        self.action_type = action_type
        self.session_id = session_id
        self.context_source = context_source
        self.context_meta = context_meta or {}
        self.context_envelope = context_envelope
        self.image_base64 = image_base64
        self._is_running = True
        self._cancel_event = threading.Event()

    def run(self):
        from opencopilot.agent.observability import PipelineObservability
        obs = PipelineObservability.get_instance()
        obs.worker_log(self._wid, "AIWorker",
                       f"START | text={self.prompt[:30]} | action={self.action_type} | session={self.session_id[:8]}",
                       session_id=self.session_id)
        
        try:
            full_text = ""
            chunk_count = 0
            print(f"[ASU] AIWorker开始 | action={self.action_type} | session={self.session_id[:8]}... | source={self.context_source} | meta_keys={list(self.context_meta.keys())}")
            # 使用统一的 Agent Pipeline 调用器（provider.stream_agent_task 已废弃）
            for chunk in call_agent_pipeline_sync(
                self.prompt, action_type=self.action_type,
                session_id=self.session_id, is_new_task=True,
                context_source=self.context_source,
                context_meta=self.context_meta,
                context_envelope=self.context_envelope,
                image_base64=self.image_base64,
                cancel_event=self._cancel_event
            ):
                if not self._is_running:
                    obs.worker_log(self._wid, "AIWorker", f"CANCELLED | chunks={chunk_count}",
                                   session_id=self.session_id)
                    print(f"[ASU] AIWorker被中断 | chunks={chunk_count}")
                    break
                full_text += chunk
                chunk_count += 1
                
                # 过滤掉已闭合的 <think>...</think> 标签块
                display_text = re.sub(r'<think>.*?</think>', '', full_text, flags=re.DOTALL)
                
                # 如果存在未闭合的 <think> 标签，说明模型正在深度思考中
                if '<think>' in display_text:
                    display_text = display_text.split('<think>')[0] + "\n\n[🤔 AI正在深度思考中...]"
                    
                self.text_updated.emit(display_text.strip())
                
            obs.worker_log(self._wid, "AIWorker",
                           f"FINISHED | chunks={chunk_count} | output_len={len(full_text)}",
                           session_id=self.session_id)
            print(f"[ASU] AIWorker完成 | action={self.action_type} | chunks={chunk_count} | output_len={len(full_text)}")
            self.full_text = full_text
        except Exception as e:
            obs.worker_log(self._wid, "AIWorker", f"ERROR | {e}",
                           session_id=self.session_id)
            print(f"[ASU] AIWorker异常 | action={self.action_type} | error={str(e)}")
            self.text_updated.emit(f"\n[错误]: {str(e)}")
            self.full_text = ""
            
        obs.worker_log(self._wid, "AIWorker", "emit finished_signal",
                       session_id=self.session_id)
        self.finished_signal.emit()

    def stop(self):
        """停止 worker 并取消管线"""
        self._is_running = False
        self._cancel_event.set()

