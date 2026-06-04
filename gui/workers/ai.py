"""gui/workers/ai.py module"""
from PyQt6.QtCore import pyqtSignal, QThread
from opencopilot.agent.caller import call_agent_pipeline_sync
from llm_provider import load_config
import json
class AIWorker(QThread):
    text_updated = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, provider, prompt, action_type="auto", session_id="default",
                 context_source="drag", context_meta=None, context_envelope=None,
                 image_base64=None):
        super().__init__()
        self.provider = provider
        self.prompt = prompt
        self.action_type = action_type
        self.session_id = session_id
        self.context_source = context_source
        self.context_meta = context_meta or {}
        self.context_envelope = context_envelope
        self.image_base64 = image_base64
        self._is_running = True

    def run(self):
        try:
            full_text = ""
            chunk_count = 0
            print(f"[ASU] AIWorker开始 | action={self.action_type} | session={self.session_id[:8]}... | source={self.context_source} | meta_keys={list(self.context_meta.keys())}")
            for chunk in self.provider.stream_agent_task(
                self.prompt, action_type=self.action_type,
                session_id=self.session_id, is_new_task=True,
                context_source=self.context_source,
                context_meta=self.context_meta,
                context_envelope=self.context_envelope,
                image_base64=self.image_base64
            ):
                if not self._is_running:
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
                
            print(f"[ASU] AIWorker完成 | action={self.action_type} | chunks={chunk_count} | output_len={len(full_text)}")
            self.full_text = full_text
        except Exception as e:
            print(f"[ASU] AIWorker异常 | action={self.action_type} | error={str(e)}")
            self.text_updated.emit(f"\n[错误]: {str(e)}")
            self.full_text = ""
            
        self.finished_signal.emit()

    def stop(self):
        self._is_running = False

