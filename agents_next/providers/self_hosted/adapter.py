from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from opencopilot.agent.caller import call_agent_pipeline_sync
from platform_next.gateway.agent_gateway.protocol import ProviderEvent, UnifiedTaskRequest
from stores_next.models import EventType


def _filter_think_tags(text: str) -> str:
    display = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    if "<think>" in display:
        display = display.split("<think>")[0]
    return display.strip()


@dataclass(slots=True)
class _RunState:
    request: UnifiedTaskRequest
    events: list[ProviderEvent] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    next_offset: int = 0
    completed: bool = False
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)


class SelfHostedAgentAdapter:
    provider_id = "self_hosted"

    def __init__(self) -> None:
        self._runs: dict[str, _RunState] = {}
        self._lock = threading.RLock()

    def healthcheck(self) -> bool:
        return True

    def create_run(self, request: UnifiedTaskRequest) -> str:
        run_id = f"self_run_{uuid4().hex[:12]}"
        state = _RunState(request=request)
        with self._lock:
            self._runs[run_id] = state
        worker = threading.Thread(
            target=self._execute_run,
            args=(run_id, state),
            daemon=True,
            name=f"self-hosted-run-{run_id}",
        )
        worker.start()
        return run_id

    def poll_events(self, run_id: str) -> list[ProviderEvent]:
        state = self._runs.get(run_id)
        if state is None:
            return []
        with state.lock:
            fresh = state.events[state.next_offset :]
            state.next_offset = len(state.events)
            return list(fresh)

    def get_result(self, run_id: str) -> dict:
        state = self._runs.get(run_id)
        if state is None:
            return {"run_id": run_id, "summary": "", "warnings": ["run_not_found"]}
        with state.lock:
            result = dict(state.result)
            if state.error and "error" not in result:
                result["error"] = state.error.get("message", "")
            return {"run_id": run_id, **result}

    def _execute_run(self, run_id: str, state: _RunState) -> None:
        request = state.request
        context_payload = request.context_payload or {}
        metadata = context_payload.get("metadata", {}) or {}
        context_meta = metadata.get("context_meta", {}) or {}
        runtime_flags = metadata.get("runtime_flags", {}) or {}
        if runtime_flags and "runtime_flags" not in context_meta:
            context_meta = {**context_meta, "runtime_flags": runtime_flags}
        if context_payload.get("selection_text") and "source_text" not in context_meta:
            context_meta = {**context_meta, "source_text": context_payload.get("selection_text", "")}

        context_source = metadata.get("context_source", "selection") or "selection"
        stage_timings: dict[str, float] = {}
        start_ts = time.time()
        full_text = ""
        chunk_count = 0

        try:
            self._append_stage(
                state,
                "context",
                "Loading context and preparing runtime inputs",
            )
            if not runtime_flags.get("disable_planner", False):
                self._append_stage(
                    state,
                    "planning",
                    "Building execution plan in runtime orchestrator",
                )
            self._append_stage(
                state,
                "executing",
                "Executing self-hosted agent pipeline",
            )
            stage_timings["bootstrap_ms"] = round((time.time() - start_ts) * 1000, 2)

            for chunk in call_agent_pipeline_sync(
                text=request.user_input,
                action_type=request.action,
                session_id=request.task_id,
                context_source=context_source,
                context_meta=context_meta,
                is_new_task=True,
                timeout=max(30.0, request.constraints.get("max_latency_ms", 12000) / 1000.0),
            ):
                full_text += chunk
                chunk_count += 1
                self._append_event(
                    state,
                    EventType.TASK_DELTA,
                    {"delta": chunk},
                )

            self._append_stage(
                state,
                "synthesizing",
                "Normalizing result and building artifacts",
            )
            summary = _filter_think_tags(full_text)
            total_ms = round((time.time() - start_ts) * 1000, 2)
            stage_timings["total_ms"] = total_ms
            with state.lock:
                state.result = {
                    "summary": summary,
                    "artifacts": [
                        {
                            "type": "text",
                            "label": "final_answer",
                            "content": summary,
                        }
                    ],
                    "evidence": [
                        {"type": "provider", "provider": self.provider_id, "run_id": run_id},
                        {"type": "runtime", "stage_timings": stage_timings, "chunk_count": chunk_count},
                        {"type": "request", "action": request.action, "runtime_flags": runtime_flags},
                    ],
                    "warnings": [f"chunk_count={chunk_count}"] if chunk_count else [],
                    "next_actions": [{"label": "apply_result", "type": "apply"}],
                }
                state.completed = True
            self._append_event(
                state,
                EventType.TASK_COMPLETED,
                {"summary": summary},
            )
        except Exception as exc:
            with state.lock:
                state.error = {
                    "code": "SELF_HOSTED_RUN_FAILED",
                    "message": str(exc),
                }
                state.result = {
                    "summary": "",
                    "artifacts": [],
                    "evidence": [
                        {"type": "provider", "provider": self.provider_id, "run_id": run_id},
                        {"type": "request", "action": request.action, "runtime_flags": runtime_flags},
                    ],
                    "warnings": [f"runtime_error={type(exc).__name__}"],
                    "next_actions": [],
                }
                state.completed = True
            self._append_event(
                state,
                EventType.TASK_FAILED,
                {"error": str(exc)},
            )

    def _append_stage(self, state: _RunState, stage: str, message: str) -> None:
        self._append_event(
            state,
            EventType.TASK_STAGE_CHANGED,
            {"stage": stage, "message": message},
        )

    def _append_event(
        self,
        state: _RunState,
        event_type: EventType,
        payload: dict[str, Any],
    ) -> None:
        with state.lock:
            state.events.append(ProviderEvent(event_type=event_type, payload=payload))
