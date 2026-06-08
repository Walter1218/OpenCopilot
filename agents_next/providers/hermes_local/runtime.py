from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path

from .config import HermesRuntimeConfig, _probe_runtime_config


_LOCK = threading.Lock()
_STARTED_BY_PROFILE: dict[str, subprocess.Popen[str]] = {}


def ensure_gateway_ready(config: HermesRuntimeConfig, *, timeout_sec: float = 15.0) -> bool:
    if _probe_runtime_config(config):
        return True

    with _LOCK:
        if _probe_runtime_config(config):
            return True

        process = _STARTED_BY_PROFILE.get(config.provider_profile)
        if process is None or process.poll() is not None:
            log_dir = Path("/tmp") / "opencopilot-hermes"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = (log_dir / "opencopilot-gateway.log").open("a", encoding="utf-8")
            env = {**os.environ, "FEISHU_APP_ID": "", "FEISHU_APP_SECRET": ""}
            process = subprocess.Popen(
                ["hermes", "-p", config.provider_profile, "gateway", "run", "--replace"],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
                env=env,
            )
            _STARTED_BY_PROFILE[config.provider_profile] = process

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if _probe_runtime_config(config):
            return True
        process = _STARTED_BY_PROFILE.get(config.provider_profile)
        if process is not None and process.poll() is not None:
            return False
        time.sleep(0.4)
    return False
