from __future__ import annotations


class BrokerErrorMapper:
    def map_exception(self, exc: Exception) -> dict:
        return {
            "code": "BROKER_DENIED",
            "message": str(exc),
            "retryable": False,
        }
