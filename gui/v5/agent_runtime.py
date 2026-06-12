from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config_manager import ConfigManager

CAPABILITY_ROUTE_ACTIONS = (
    ("chat", "Chat"),
    ("explain", "Explain"),
    ("coding", "Coding"),
    ("ppt", "PPT"),
    ("translate", "Translate"),
)

ROUTE_PRESET_DEFAULT = "default"
ROUTE_PRESET_SELF_AGENT = "self_agent"
ROUTE_PRESET_HERMES_LOCAL = "hermes_local"


@dataclass(frozen=True, slots=True)
class AgentExecutionRoute:
    backend: str
    provider: str
    model: str
    routing_mode: str

    @property
    def agent_backend(self) -> str:
        if self.backend == "self_agent":
            return "self_agent"
        if self.backend == "vnext_provider":
            return f"{self.provider}_vnext"
        return self.backend


@dataclass(frozen=True, slots=True)
class AgentFallbackDecision:
    enabled: bool
    target_backend: str
    target_provider: str
    reason: str


def build_route_from_preset(preset: str) -> dict[str, str]:
    if preset == ROUTE_PRESET_SELF_AGENT:
        return {"backend": "self_agent", "provider": "self_agent"}
    if preset == ROUTE_PRESET_HERMES_LOCAL:
        return {"backend": "vnext_provider", "provider": "hermes_local"}
    return {}


def infer_route_preset(route: dict[str, Any] | None) -> str:
    if not isinstance(route, dict):
        return ROUTE_PRESET_DEFAULT
    backend = route.get("backend")
    provider = route.get("provider")
    if backend == "self_agent":
        return ROUTE_PRESET_SELF_AGENT
    if backend == "vnext_provider" and provider == "hermes_local":
        return ROUTE_PRESET_HERMES_LOCAL
    return ROUTE_PRESET_DEFAULT


def resolve_agent_route(action_type: str) -> AgentExecutionRoute:
    config = ConfigManager.get_instance().get_agent_runtime()
    capability_routes = config.get("capability_routes", {})
    route = capability_routes.get(action_type)
    routing_mode = "default"

    if isinstance(route, dict):
        routing_mode = "capability_override"
        backend = route.get("backend", config["default_backend"])
        provider = route.get("provider", config["default_provider"])
        model = route.get("model", config["default_model"])
    else:
        backend = config["default_backend"]
        provider = config["default_provider"]
        model = config["default_model"]

    if backend == "self_agent":
        provider = "self_agent"

    return AgentExecutionRoute(
        backend=backend,
        provider=provider,
        model=model,
        routing_mode=routing_mode,
    )


def resolve_fallback_decision(error: Exception, current_route: AgentExecutionRoute) -> AgentFallbackDecision:
    config = ConfigManager.get_instance().get_agent_runtime()
    fallback_policy = config.get("fallback_policy", {})
    if (
        current_route.backend == "self_agent"
        or not isinstance(fallback_policy, dict)
        or not fallback_policy.get("enabled", False)
    ):
        return AgentFallbackDecision(False, "", "", "")

    message = str(error).lower()
    if _is_timeout_error(error, message):
        target = fallback_policy.get("on_timeout", "")
        if target == "self_agent":
            return AgentFallbackDecision(True, "self_agent", "self_agent", "timeout")

    if _is_protocol_error(error, message):
        target = fallback_policy.get("on_protocol_error", "")
        if target == "self_agent":
            return AgentFallbackDecision(True, "self_agent", "self_agent", "protocol_error")

    return AgentFallbackDecision(False, "", "", "")


def _is_timeout_error(_error: Exception, message: str) -> bool:
    timeout_types = ("timeout", "timed out", "readtimeout", "connecttimeout", "超时")
    return any(token in message for token in timeout_types)


def _is_protocol_error(error: Exception, message: str) -> bool:
    protocol_types = ("json", "protocol", "payload", "schema", "格式", "协议")
    return isinstance(error, (ValueError, KeyError)) or any(token in message for token in protocol_types)
