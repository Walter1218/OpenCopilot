from __future__ import annotations

from .protocol import UnifiedTaskRequest


class RequestNormalizer:
    def normalize(self, request: UnifiedTaskRequest) -> UnifiedTaskRequest:
        return request
