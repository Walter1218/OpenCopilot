from __future__ import annotations

from typing import Dict

from .protocol import AgentProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, AgentProvider] = {}

    def register(self, provider: AgentProvider) -> None:
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> AgentProvider:
        if provider_id not in self._providers:
            raise KeyError(f"Unknown provider: {provider_id}")
        return self._providers[provider_id]
