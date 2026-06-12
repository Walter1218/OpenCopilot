from __future__ import annotations


class HermesErrorMapper:
    def map_exception(self, exc: Exception) -> dict:
        return {
            "code": "PROVIDER_STREAM_ERROR",
            "message": str(exc),
            "retryable": True,
            "provider": "hermes_local",
        }
