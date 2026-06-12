from __future__ import annotations

from functools import lru_cache

from stores_next import ApplyPreviewStore, ContextStore, EventStore, SessionStore, TaskStore
from platform_next.gateway.agent_gateway.coordinator import AgentGatewayCoordinator
from platform_next.gateway.broker_gateway.apply_service import ApplyService
from platform_next.gateway.broker_gateway.context_service import ContextService


@lru_cache(maxsize=1)
def get_task_store() -> TaskStore:
    return TaskStore()


@lru_cache(maxsize=1)
def get_event_store() -> EventStore:
    return EventStore()


@lru_cache(maxsize=1)
def get_context_store() -> ContextStore:
    return ContextStore()


@lru_cache(maxsize=1)
def get_session_store() -> SessionStore:
    return SessionStore()


@lru_cache(maxsize=1)
def get_apply_preview_store() -> ApplyPreviewStore:
    return ApplyPreviewStore()


@lru_cache(maxsize=1)
def get_agent_gateway() -> AgentGatewayCoordinator:
    return AgentGatewayCoordinator()


@lru_cache(maxsize=1)
def get_context_service() -> ContextService:
    return ContextService(context_store=get_context_store())


@lru_cache(maxsize=1)
def get_apply_service() -> ApplyService:
    return ApplyService(apply_store=get_apply_preview_store(), task_store=get_task_store())
