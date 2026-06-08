from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE_URL = os.getenv("SMART_COPILOT_API_BASE_URL", "http://127.0.0.1:8010").rstrip("/")
FALLBACK_BASE_URL = "http://127.0.0.1:8000"


def _health_check(base_url: str) -> bool:
    try:
        response = httpx.get(f"{base_url}/health", timeout=1.5)
    except httpx.HTTPError:
        return False
    return response.is_success


def _vnext_check(base_url: str) -> bool:
    try:
        response = httpx.post(
            f"{base_url}/vnext/context/snapshots",
            json={"trigger": "probe"},
            timeout=2.0,
        )
        return response.is_success or response.status_code == 422
    except httpx.HTTPStatusError as exc:
        return exc.response.status_code == 422
    except httpx.HTTPError:
        return False


def _is_local_address(base_url: str) -> bool:
    parsed = urlparse(base_url)
    return parsed.hostname in {"127.0.0.1", "localhost"}


def _port_of(base_url: str) -> int:
    parsed = urlparse(base_url)
    return parsed.port or (443 if parsed.scheme == "https" else 80)


@dataclass(slots=True)
class SmartCopilotApiRuntime:
    preferred_base_url: str = DEFAULT_BASE_URL
    started_process: subprocess.Popen[str] | None = field(default=None, init=False, repr=False)
    active_base_url: str = field(default="", init=False)
    log_file: Path = field(default=Path("/tmp/opencopilot-vnext-api.log"), init=False)

    def ensure_ready(self) -> str:
        candidate = self.preferred_base_url.rstrip("/")
        if _health_check(candidate) and _vnext_check(candidate):
            self.active_base_url = candidate
            return candidate

        if _health_check(candidate) and not _vnext_check(candidate):
            if candidate == DEFAULT_BASE_URL:
                candidate = FALLBACK_BASE_URL
            else:
                raise RuntimeError(f"API 已存在但未挂载 vnext 路由: {self.preferred_base_url}")

        if self.started_process is None:
            self._start_api(candidate)

        if not self._wait_until_ready(candidate):
            raise RuntimeError(f"无法启动可用的 vnext API: {candidate}")

        self.active_base_url = candidate
        return candidate

    def shutdown(self) -> None:
        if self.started_process is None:
            return
        if self.started_process.poll() is None:
            self.started_process.terminate()
            try:
                self.started_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.started_process.kill()
        self.started_process = None

    def _start_api(self, base_url: str) -> None:
        if not _is_local_address(base_url):
            raise RuntimeError(f"仅支持自动启动本机 API，当前地址不受支持: {base_url}")
        host = urlparse(base_url).hostname or "127.0.0.1"
        port = str(_port_of(base_url))
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = self.log_file.open("a", encoding="utf-8")
        self.started_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "smart_copilot_api:app",
                "--host",
                host,
                "--port",
                port,
            ],
            cwd=str(PROJECT_ROOT),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )

    def _wait_until_ready(self, base_url: str) -> bool:
        deadline = time.time() + 15.0
        while time.time() < deadline:
            if _health_check(base_url) and _vnext_check(base_url):
                return True
            if self.started_process is not None and self.started_process.poll() is not None:
                return False
            time.sleep(0.4)
        return False
