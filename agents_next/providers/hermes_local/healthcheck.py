from __future__ import annotations

import httpx

from .config import HermesRuntimeConfig, build_headers, load_runtime_config


def check_health(config: HermesRuntimeConfig | None = None) -> bool:
    runtime = config or load_runtime_config()
    try:
        response = httpx.get(
            f"{runtime.base_url}/health",
            headers=build_headers(runtime),
            timeout=2.0,
        )
        return response.is_success and "text/html" not in response.headers.get("content-type", "")
    except httpx.HTTPError:
        return False
