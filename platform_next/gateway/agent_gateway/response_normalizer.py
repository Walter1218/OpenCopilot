from __future__ import annotations

from stores_next.models import TaskResult


class ResponseNormalizer:
    def normalize(self, raw_result: dict) -> TaskResult:
        return TaskResult(summary=raw_result.get("summary", ""))
