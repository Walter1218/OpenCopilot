from config_manager import ConfigManager
from gui.v5.agent_runtime import (
    ROUTE_PRESET_DEFAULT,
    ROUTE_PRESET_HERMES_LOCAL,
    ROUTE_PRESET_SELF_AGENT,
    build_route_from_preset,
    infer_route_preset,
    resolve_agent_route,
    resolve_fallback_decision,
)


def test_resolve_agent_route_uses_default_self_agent():
    ConfigManager.reset_instance()
    route = resolve_agent_route("chat")
    assert route.backend == "self_agent"
    assert route.provider == "self_agent"
    assert route.agent_backend == "self_agent"
    assert route.routing_mode == "default"


def test_resolve_agent_route_supports_capability_override():
    ConfigManager.reset_instance()
    cfg = ConfigManager.get_instance()
    original = cfg.get_raw()
    cfg._config["agent_runtime"] = {
        "default_backend": "vnext_provider",
        "default_provider": "hermes_local",
        "capability_routes": {
            "chat": {
                "backend": "self_agent",
                "provider": "self_agent",
            }
        },
    }

    route = resolve_agent_route("chat")

    assert route.backend == "self_agent"
    assert route.provider == "self_agent"
    assert route.agent_backend == "self_agent"
    assert route.routing_mode == "capability_override"

    cfg._config = original


def test_route_preset_helpers_roundtrip():
    assert build_route_from_preset(ROUTE_PRESET_DEFAULT) == {}
    assert build_route_from_preset(ROUTE_PRESET_SELF_AGENT)["backend"] == "self_agent"
    assert infer_route_preset({"backend": "vnext_provider", "provider": "hermes_local"}) == ROUTE_PRESET_HERMES_LOCAL


def test_resolve_fallback_decision_for_timeout():
    ConfigManager.reset_instance()
    cfg = ConfigManager.get_instance()
    original = cfg.get_raw()
    cfg._config["agent_runtime"] = {
        "default_backend": "vnext_provider",
        "default_provider": "hermes_local",
        "fallback_policy": {
            "enabled": True,
            "on_timeout": "self_agent",
            "on_protocol_error": "",
        }
    }
    route = resolve_agent_route("chat")
    assert route.backend == "vnext_provider"
    decision = resolve_fallback_decision(RuntimeError("request timeout"), route)
    assert decision.enabled is True
    assert decision.target_backend == "self_agent"
    assert decision.reason == "timeout"
    cfg._config = original


def test_resolve_fallback_decision_for_protocol_error():
    ConfigManager.reset_instance()
    cfg = ConfigManager.get_instance()
    original = cfg.get_raw()
    cfg._config["agent_runtime"] = {
        "default_backend": "vnext_provider",
        "default_provider": "hermes_local",
        "fallback_policy": {
            "enabled": True,
            "on_timeout": "",
            "on_protocol_error": "self_agent",
        }
    }
    route = resolve_agent_route("chat")
    assert route.backend == "vnext_provider"
    decision = resolve_fallback_decision(ValueError("invalid protocol payload"), route)
    assert decision.enabled is True
    assert decision.target_backend == "self_agent"
    assert decision.reason == "protocol_error"
    cfg._config = original
