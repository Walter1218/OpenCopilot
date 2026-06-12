from __future__ import annotations

from typing import Final

from .protocol import UnifiedTaskRequest


class ProviderSelector:
    _STRUCTURED_PROVIDER_ACTIONS: Final[set[str]] = {"ppt"}
    _AUTO_PROVIDER_ALIASES: Final[set[str]] = {"", "auto", "default"}

    def choose_provider(self, request: UnifiedTaskRequest) -> str:
        requested = (request.provider or "").strip()
        if requested not in self._AUTO_PROVIDER_ALIASES:
            return requested

        action = (request.action or "").strip().lower()
        if action in self._STRUCTURED_PROVIDER_ACTIONS:
            return "hermes_local"
        return "self_hosted"
