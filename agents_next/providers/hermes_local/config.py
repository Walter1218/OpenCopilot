from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import dotenv_values


DEFAULT_PROFILE = "coder"
DEFAULT_BASE_URL = "http://127.0.0.1:8642"
DISCOVERY_TIMEOUT_SEC = 1.0


@dataclass(frozen=True)
class HermesRuntimeConfig:
    provider_profile: str
    base_url: str
    api_key: str
    profile_env_file: str
    discovery_source: str = "fallback_default"


def _default_profile_env_file(profile: str) -> Path:
    return _profiles_root() / profile / ".env"


def _profiles_root() -> Path:
    return Path.home() / ".hermes" / "profiles"


def _load_profile_env(profile_env_path: Path) -> dict[str, str]:
    if not profile_env_path.exists():
        return {}
    return {str(key): str(value or "").strip() for key, value in dotenv_values(profile_env_path).items()}


def _build_runtime_config(
    *,
    provider_profile: str,
    base_url: str,
    api_key: str,
    profile_env_file: Path,
    discovery_source: str,
) -> HermesRuntimeConfig:
    return HermesRuntimeConfig(
        provider_profile=provider_profile,
        base_url=base_url.rstrip("/"),
        api_key=api_key.strip(),
        profile_env_file=str(profile_env_file),
        discovery_source=discovery_source,
    )


def _build_explicit_runtime_config(
    *,
    profile: str,
    profile_env_path: Path,
    explicit_base_url: str,
    explicit_api_key: str,
) -> HermesRuntimeConfig:
    return _build_runtime_config(
        provider_profile=profile,
        base_url=explicit_base_url,
        api_key=explicit_api_key,
        profile_env_file=profile_env_path,
        discovery_source="explicit_env",
    )


def _build_profile_runtime_config(
    *,
    profile: str,
    profile_env_path: Path,
    explicit_api_key: str,
    discovery_source: str,
) -> HermesRuntimeConfig | None:
    profile_env = _load_profile_env(profile_env_path)
    api_server_port = profile_env.get("API_SERVER_PORT", "")
    if not api_server_port:
        return None
    return _build_runtime_config(
        provider_profile=profile,
        base_url=f"http://127.0.0.1:{api_server_port}",
        api_key=explicit_api_key or profile_env.get("API_SERVER_KEY", ""),
        profile_env_file=profile_env_path,
        discovery_source=discovery_source,
    )


def _iter_candidate_profile_env_paths(preferred_profile: str, explicit_profile_env_file: str) -> list[tuple[str, Path, str]]:
    candidates: list[tuple[str, Path, str]] = []
    seen_paths: set[Path] = set()

    if explicit_profile_env_file:
        explicit_path = Path(explicit_profile_env_file).expanduser()
        explicit_profile = explicit_path.parent.name or preferred_profile
        candidates.append((explicit_profile, explicit_path, "explicit_profile_env"))
        seen_paths.add(explicit_path)

    preferred_path = _default_profile_env_file(preferred_profile)
    if preferred_path not in seen_paths:
        candidates.append((preferred_profile, preferred_path, "preferred_profile_env"))
        seen_paths.add(preferred_path)

    profiles_root = _profiles_root()
    if not profiles_root.exists():
        return candidates

    for profile_dir in sorted(profiles_root.iterdir(), key=lambda item: item.name):
        if not profile_dir.is_dir():
            continue
        profile_name = profile_dir.name
        profile_env_path = profile_dir / ".env"
        if profile_env_path in seen_paths:
            continue
        candidates.append((profile_name, profile_env_path, "auto_discovered_profile_env"))
        seen_paths.add(profile_env_path)

    return candidates


def _probe_runtime_config(config: HermesRuntimeConfig) -> bool:
    try:
        response = httpx.get(
            f"{config.base_url}/health",
            headers=build_headers(config),
            timeout=DISCOVERY_TIMEOUT_SEC,
        )
    except httpx.HTTPError:
        return False
    return response.is_success and "text/html" not in response.headers.get("content-type", "")


def load_runtime_config() -> HermesRuntimeConfig:
    profile = os.getenv("HERMES_PROVIDER_PROFILE", DEFAULT_PROFILE).strip() or DEFAULT_PROFILE
    explicit_profile_env_file = os.getenv("HERMES_PROFILE_ENV_FILE", "").strip()
    default_profile_env_path = (
        Path(explicit_profile_env_file).expanduser()
        if explicit_profile_env_file
        else _default_profile_env_file(profile)
    )
    explicit_base_url = os.getenv("HERMES_BASE_URL", "").strip()
    explicit_api_key = os.getenv("HERMES_API_KEY", "").strip()

    if explicit_base_url:
        return _build_explicit_runtime_config(
            profile=profile,
            profile_env_path=default_profile_env_path,
            explicit_base_url=explicit_base_url,
            explicit_api_key=explicit_api_key,
        )

    fallback_config: HermesRuntimeConfig | None = None
    for candidate_profile, candidate_path, discovery_source in _iter_candidate_profile_env_paths(
        profile,
        explicit_profile_env_file,
    ):
        candidate = _build_profile_runtime_config(
            profile=candidate_profile,
            profile_env_path=candidate_path,
            explicit_api_key=explicit_api_key,
            discovery_source=discovery_source,
        )
        if candidate is None:
            continue
        if fallback_config is None:
            fallback_config = candidate
        if _probe_runtime_config(candidate):
            return candidate

    if fallback_config is not None:
        return fallback_config

    return _build_runtime_config(
        provider_profile=profile,
        base_url=DEFAULT_BASE_URL,
        api_key=explicit_api_key,
        profile_env_file=default_profile_env_path,
        discovery_source="fallback_default",
    )


def build_headers(config: HermesRuntimeConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    return headers
