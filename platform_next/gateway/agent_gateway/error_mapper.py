from __future__ import annotations


class ErrorMapper:
    def map_exception(self, exc: Exception) -> dict:
        return {
            "code": "AGENT_UNAVAILABLE",
            "message": str(exc),
            "retryable": True,
        }
