from __future__ import annotations

from platform_next.gateway.agent_gateway.protocol import ProviderEvent
from stores_next.models import EventType


class HermesStreamAdapter:
    def adapt_run_events(self, raw_events: list[dict]) -> list[ProviderEvent]:
        if not raw_events:
            return [
                ProviderEvent(
                    event_type=EventType.TASK_STAGE_CHANGED,
                    payload={"stage": "executing", "message": "Waiting for Hermes events"},
                )
            ]
        events: list[ProviderEvent] = []
        for event in raw_events:
            event_name = event.get("event", "")
            if event_name in {"status", "tool.start", "tool.end", "reasoning.available"}:
                events.append(
                    ProviderEvent(
                        event_type=EventType.TASK_STAGE_CHANGED,
                        payload={
                            "stage": event.get("stage", event_name),
                            "message": event.get("message") or event.get("text") or event_name,
                            "raw": event,
                        },
                    )
                )
            elif event_name == "message.delta":
                events.append(
                    ProviderEvent(
                        event_type=EventType.TASK_DELTA,
                        payload={"delta": event.get("delta", ""), "raw": event},
                    )
                )
            elif event_name == "run.completed":
                events.append(
                    ProviderEvent(
                        event_type=EventType.TASK_COMPLETED,
                        payload={
                            "summary": event.get("output", ""),
                            "usage": event.get("usage", {}),
                            "raw": event,
                        },
                    )
                )
            elif event_name == "run.failed":
                events.append(
                    ProviderEvent(
                        event_type=EventType.TASK_FAILED,
                        payload={"error": event.get("error", "unknown provider error"), "raw": event},
                    )
                )
            else:
                events.append(
                    ProviderEvent(
                        event_type=EventType.TASK_WARNING,
                        payload={"message": "Unhandled Hermes event", "raw": event},
                    )
                )
        return events
