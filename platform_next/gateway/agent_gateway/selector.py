from __future__ import annotations

from .protocol import UnifiedTaskRequest


class ProviderSelector:
    def choose_provider(self, request: UnifiedTaskRequest) -> str:
        return request.provider or "hermes_local"
