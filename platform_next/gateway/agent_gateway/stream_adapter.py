from __future__ import annotations

from typing import Iterable, List

from .protocol import ProviderEvent


class StreamAdapter:
    def adapt(self, provider_events: Iterable[ProviderEvent]) -> List[ProviderEvent]:
        return list(provider_events)
