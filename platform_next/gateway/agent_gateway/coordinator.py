from __future__ import annotations

from dataclasses import replace

from agents_next.providers.hermes_local.adapter import HermesLocalAdapter
from agents_next.providers.self_hosted.adapter import SelfHostedAgentAdapter

from .error_mapper import ErrorMapper
from .registry import ProviderRegistry
from .request_normalizer import RequestNormalizer
from .selector import ProviderSelector
from .stream_adapter import StreamAdapter
from .protocol import ProviderEvent, UnifiedTaskRequest


class AgentGatewayCoordinator:
    def __init__(self) -> None:
        self.registry = ProviderRegistry()
        self.selector = ProviderSelector()
        self.request_normalizer = RequestNormalizer()
        self.stream_adapter = StreamAdapter()
        self.error_mapper = ErrorMapper()
        self.registry.register(HermesLocalAdapter())
        self.registry.register(SelfHostedAgentAdapter())

    def resolve_provider(self, request: UnifiedTaskRequest) -> str:
        normalized = self.request_normalizer.normalize(request)
        return self.selector.choose_provider(normalized)

    def create_run(self, request: UnifiedTaskRequest) -> str:
        normalized = self.request_normalizer.normalize(request)
        provider_id = self.selector.choose_provider(normalized)
        provider = self.registry.get(provider_id)
        return provider.create_run(replace(normalized, provider=provider_id))

    def poll_events(self, *, provider_id: str, provider_run_id: str) -> list[ProviderEvent]:
        provider = self.registry.get(provider_id)
        return self.stream_adapter.adapt(provider.poll_events(provider_run_id))

    def get_result(self, *, provider_id: str, provider_run_id: str) -> dict:
        provider = self.registry.get(provider_id)
        return provider.get_result(provider_run_id)
