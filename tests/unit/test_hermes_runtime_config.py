from __future__ import annotations

from pathlib import Path

from agents_next.providers.hermes_local import config as hermes_config


def _write_profile_env(root: Path, profile: str, content: str) -> None:
    profile_dir = root / profile
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / ".env").write_text(content, encoding="utf-8")


def test_load_runtime_config_auto_discovers_healthy_profile(monkeypatch, tmp_path):
    _write_profile_env(tmp_path, "coder", "API_SERVER_ENABLED=true\nAPI_SERVER_PORT=8642\nAPI_SERVER_KEY=coder-key\n")
    _write_profile_env(tmp_path, "ops", "API_SERVER_ENABLED=true\nAPI_SERVER_PORT=9751\nAPI_SERVER_KEY=ops-key\n")

    monkeypatch.setattr(hermes_config, "_profiles_root", lambda: tmp_path)
    monkeypatch.setattr(
        hermes_config,
        "_probe_runtime_config",
        lambda runtime: runtime.base_url == "http://127.0.0.1:9751",
    )
    monkeypatch.setenv("HERMES_PROVIDER_PROFILE", "coder")
    monkeypatch.delenv("HERMES_PROFILE_ENV_FILE", raising=False)
    monkeypatch.delenv("HERMES_BASE_URL", raising=False)
    monkeypatch.delenv("HERMES_API_KEY", raising=False)

    runtime = hermes_config.load_runtime_config()

    assert runtime.provider_profile == "ops"
    assert runtime.base_url == "http://127.0.0.1:9751"
    assert runtime.api_key == "ops-key"
    assert runtime.discovery_source == "auto_discovered_profile_env"


def test_load_runtime_config_keeps_explicit_base_url(monkeypatch, tmp_path):
    monkeypatch.setattr(hermes_config, "_profiles_root", lambda: tmp_path)
    monkeypatch.setenv("HERMES_PROVIDER_PROFILE", "coder")
    monkeypatch.setenv("HERMES_BASE_URL", "http://127.0.0.1:19090")
    monkeypatch.setenv("HERMES_API_KEY", "explicit-key")
    monkeypatch.delenv("HERMES_PROFILE_ENV_FILE", raising=False)

    runtime = hermes_config.load_runtime_config()

    assert runtime.provider_profile == "coder"
    assert runtime.base_url == "http://127.0.0.1:19090"
    assert runtime.api_key == "explicit-key"
    assert runtime.discovery_source == "explicit_env"


def test_load_runtime_config_falls_back_to_preferred_profile_when_no_probe_succeeds(monkeypatch, tmp_path):
    _write_profile_env(tmp_path, "coder", "API_SERVER_PORT=8644\nAPI_SERVER_KEY=coder-key\n")
    _write_profile_env(tmp_path, "ops", "API_SERVER_PORT=9751\nAPI_SERVER_KEY=ops-key\n")

    monkeypatch.setattr(hermes_config, "_profiles_root", lambda: tmp_path)
    monkeypatch.setattr(hermes_config, "_probe_runtime_config", lambda runtime: False)
    monkeypatch.setenv("HERMES_PROVIDER_PROFILE", "coder")
    monkeypatch.delenv("HERMES_PROFILE_ENV_FILE", raising=False)
    monkeypatch.delenv("HERMES_BASE_URL", raising=False)
    monkeypatch.delenv("HERMES_API_KEY", raising=False)

    runtime = hermes_config.load_runtime_config()

    assert runtime.provider_profile == "coder"
    assert runtime.base_url == "http://127.0.0.1:8644"
    assert runtime.api_key == "coder-key"
    assert runtime.discovery_source == "preferred_profile_env"
