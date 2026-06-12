from __future__ import annotations

import json
from uuid import uuid4

import httpx

from platform_next.gateway.agent_gateway.protocol import ProviderEvent, UnifiedTaskRequest
from stores_next.models import EventType

from .config import build_headers
from .dto_mapper import HermesDtoMapper
from .error_mapper import HermesErrorMapper
from .healthcheck import check_health, load_runtime_config
from .runtime import ensure_gateway_ready
from .stream_adapter import HermesStreamAdapter


class HermesLocalAdapter:
    provider_id = "hermes_local"

    def __init__(self) -> None:
        self._dto_mapper = HermesDtoMapper()
        self._stream_adapter = HermesStreamAdapter()
        self._error_mapper = HermesErrorMapper()
        self._runtime = load_runtime_config()
        self._runs: dict[str, dict] = {}

    def healthcheck(self) -> bool:
        return check_health(self._runtime)

    def create_run(self, request: UnifiedTaskRequest) -> str:
        payload = self._dto_mapper.to_run_request(request)
        fallback_run_id = f"hermes_run_{uuid4().hex[:12]}"
        ensure_gateway_ready(self._runtime)
        # #region debug-point B:create-run-input
        try:
            import urllib.request; _p='.dbg/v5-hermes-runtime.env'; _u,_s='http://127.0.0.1:7777/event','v5-hermes-runtime'; exec("try:\n with open(_p) as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({"sessionId":_s,"runId":"pre-fix","hypothesisId":"B","location":"agents_next/providers/hermes_local/adapter.py:create_run","msg":"[DEBUG] Hermes create_run request","data":{"base_url":self._runtime.base_url,"provider_profile":self._runtime.provider_profile,"discovery_source":self._runtime.discovery_source,"payload_input_len":len(str(payload.get('input', ''))),"metadata":payload.get("metadata", {})}}).encode(), headers={"Content-Type":"application/json"})).read()
        except Exception:
            pass  # debug 插桩容错：debug server 未运行时静默跳过
        # #endregion
        try:
            response = httpx.post(
                f"{self._runtime.base_url}/v1/runs",
                headers=build_headers(self._runtime),
                json=payload,
                timeout=20.0,
            )
            response.raise_for_status()
            data = response.json()
            run_id = data.get("run_id") or fallback_run_id
            # #region debug-point B:create-run-success
            try:
                import urllib.request; _p='.dbg/v5-hermes-runtime.env'; _u,_s='http://127.0.0.1:7777/event','v5-hermes-runtime'; exec("try:\n with open(_p) as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({"sessionId":_s,"runId":"pre-fix","hypothesisId":"B","location":"agents_next/providers/hermes_local/adapter.py:create_run","msg":"[DEBUG] Hermes create_run success","data":{"run_id":run_id,"status_code":response.status_code}}).encode(), headers={"Content-Type":"application/json"})).read()
            except Exception:
                pass
            # #endregion
            self._runs[run_id] = {"mode": "remote", "result": None}
            return run_id
        except (httpx.HTTPError, ValueError) as exc:
            # #region debug-point D:create-run-fallback
            try:
                import urllib.request; _p='.dbg/v5-hermes-runtime.env'; _u,_s='http://127.0.0.1:7777/event','v5-hermes-runtime'; exec("try:\n with open(_p) as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({"sessionId":_s,"runId":"pre-fix","hypothesisId":"D","location":"agents_next/providers/hermes_local/adapter.py:create_run","msg":"[DEBUG] Hermes create_run fallback","data":{"error_type":type(exc).__name__,"error":str(exc),"base_url":self._runtime.base_url,"provider_profile":self._runtime.provider_profile,"discovery_source":self._runtime.discovery_source}}).encode(), headers={"Content-Type":"application/json"})).read()
            except Exception:
                pass
            # #endregion
            self._runs[fallback_run_id] = {
                "mode": "stub",
                "result": {"summary": "Hermes provider fallback result"},
                "events": [
                    {"event": "status", "stage": "executing", "message": f"Hermes unavailable, fallback for action={request.action}"},
                    {"event": "run.completed", "output": "Hermes provider fallback result"},
                ],
                "error": self._error_mapper.map_exception(exc),
            }
            return fallback_run_id

    def poll_events(self, run_id: str) -> list[ProviderEvent]:
        run_meta = self._runs.get(run_id)
        if run_meta is None:
            return []

        if run_meta.get("mode") == "stub":
            raw_events = run_meta.get("events", [])
            events = self._stream_adapter.adapt_run_events(raw_events)
            if raw_events:
                self._runs[run_id]["events"] = []
            return events

        raw_events: list[dict] = []
        try:
            with httpx.stream(
                "GET",
                f"{self._runtime.base_url}/v1/runs/{run_id}/events",
                headers=build_headers(self._runtime),
                timeout=35.0,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    payload = json.loads(line[6:])
                    raw_events.append(payload)
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            mapped = self._error_mapper.map_exception(exc)
            return [ProviderEvent(event_type=EventType.TASK_FAILED, payload=mapped)]

        events = self._stream_adapter.adapt_run_events(raw_events)
        for raw_event in raw_events:
            if raw_event.get("event") == "run.completed":
                self._runs[run_id]["result"] = {
                    "summary": raw_event.get("output", ""),
                    "usage": raw_event.get("usage", {}),
                }
            elif raw_event.get("event") == "run.failed":
                self._runs[run_id]["result"] = {
                    "summary": "",
                    "error": raw_event.get("error", "unknown provider error"),
                }
        return events

    def get_result(self, run_id: str) -> dict:
        run_meta = self._runs.get(run_id, {})
        result = run_meta.get("result") or {}
        return {"run_id": run_id, **result}
