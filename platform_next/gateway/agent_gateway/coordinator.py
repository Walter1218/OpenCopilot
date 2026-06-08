from __future__ import annotations

from agents_next.providers.hermes_local.adapter import HermesLocalAdapter

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

    def create_run(self, request: UnifiedTaskRequest) -> str:
        normalized = self.request_normalizer.normalize(request)
        provider = self.registry.get(self.selector.choose_provider(normalized))
        return provider.create_run(normalized)

    def poll_events(self, *, provider_id: str, provider_run_id: str) -> list[ProviderEvent]:
        provider = self.registry.get(provider_id)
        return self.stream_adapter.adapt(provider.poll_events(provider_run_id))

    def get_result(self, *, provider_id: str, provider_run_id: str) -> dict:
        provider = self.registry.get(provider_id)
        return provider.get_result(provider_run_id)
