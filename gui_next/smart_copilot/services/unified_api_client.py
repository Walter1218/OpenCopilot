from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict

import httpx


@dataclass(slots=True)
class UnifiedApiClient:
    base_url: str = ""
    timeout: float = 20.0
    client: Any | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.base_url:
            self.base_url = os.getenv("SMART_COPILOT_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

    def create_context_snapshot(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/vnext/context/snapshots", json=payload)

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/vnext/tasks", json=payload)

    def get_task(self, task_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/vnext/tasks/{task_id}")

    def list_task_events(self, task_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/vnext/tasks/{task_id}/events")

    def create_apply_preview(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/vnext/apply/preview", json=payload)

    def commit_apply(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/vnext/apply/commit", json=payload)

    def close(self) -> None:
        if self.client is not None:
            self.client.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        response = self._get_client().request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()

    def _get_client(self) -> Any:
        if self.client is None:
            self.client = httpx.Client(base_url=self.base_url, timeout=self.timeout)
        return self.client
