from __future__ import annotations

from dataclasses import asdict
import threading
import time
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from platform_next.gateway.agent_gateway.protocol import UnifiedTaskRequest
from stores_next.models import EventType, TaskEvent, TaskRecord, TaskResult, TaskStatus

from .dependencies import get_agent_gateway, get_context_store, get_event_store, get_task_store
from .models import CreateTaskRequest, TaskResponse, TaskResultResponse

router = APIRouter(prefix="/vnext/tasks", tags=["vnext-tasks"])
_TASK_MONITOR_THREADS: dict[str, threading.Thread] = {}
_TASK_MONITOR_LOCK = threading.Lock()
_TASK_POLL_INTERVAL_SEC = 0.35


def _is_terminal_status(status: TaskStatus) -> bool:
    return status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED}


def _build_apply_operations(context_selection: str, summary: str) -> list[dict]:
    if not context_selection or not summary:
        return []
    return [
        {
            "type": "replace_selection",
            "target": {"type": "selection"},
            "before": context_selection,
            "after": summary,
        }
    ]


def _append_task_event(task_id: str, event_type: EventType, payload: dict) -> TaskEvent:
    event = TaskEvent(
        event_id=f"evt_{uuid4().hex[:12]}",
        task_id=task_id,
        type=event_type,
        sequence=get_event_store().next_sequence(task_id),
        payload=payload,
    )
    get_event_store().append(event)
    return event


def _finalize_task_result(task: TaskRecord) -> None:
    result_payload = get_agent_gateway().get_result(
        provider_id=task.provider,
        provider_run_id=task.provider_run_id or "",
    )
    context = get_context_store().get(task.context_snapshot_id)
    summary = result_payload.get("summary", "")
    result = TaskResult(
        summary=summary,
        artifacts=result_payload.get("artifacts", []),
        evidence=result_payload.get("evidence", []),
        warnings=[f"provider={task.provider}"],
        next_actions=result_payload.get("next_actions", []),
        apply_operations=_build_apply_operations(
            context.selection_text if context is not None else "",
            summary,
        ),
    )
    get_task_store().set_result(task.task_id, result)


def _should_skip_stage_event(task_id: str, payload: dict) -> bool:
    last_event = get_event_store().last_for_task(task_id)
    if last_event is None or last_event.type != EventType.TASK_STAGE_CHANGED:
        return False
    last_stage = last_event.payload.get("stage")
    last_message = last_event.payload.get("message")
    return last_stage == payload.get("stage") and last_message == payload.get("message")


def _apply_provider_event(task_id: str, provider_event) -> None:
    payload = provider_event.payload
    event_type = provider_event.event_type
    if event_type == EventType.TASK_STAGE_CHANGED and _should_skip_stage_event(task_id, payload):
        return

    _append_task_event(task_id, event_type, payload)
    task = get_task_store().get(task_id)
    if task is None:
        return

    if event_type == EventType.TASK_STAGE_CHANGED:
        get_task_store().update_status(
            task_id,
            TaskStatus.RUNNING,
            stage=payload.get("stage", task.progress_stage),
            message=payload.get("message", task.progress_message),
        )
    elif event_type == EventType.TASK_COMPLETED:
        _finalize_task_result(task)
    elif event_type == EventType.TASK_FAILED:
        message = (
            payload.get("error")
            or payload.get("message")
            or "unknown provider error"
        )
        get_task_store().set_error(
            task_id,
            {
                "code": "PROVIDER_RUN_FAILED",
                "message": message,
                "provider": task.provider,
            },
        )


def _monitor_task_events(task_id: str) -> None:
    try:
        while True:
            task = get_task_store().get(task_id)
            if task is None or _is_terminal_status(task.status):
                return
            if not task.provider_run_id:
                time.sleep(_TASK_POLL_INTERVAL_SEC)
                continue

            provider_events = get_agent_gateway().poll_events(
                provider_id=task.provider,
                provider_run_id=task.provider_run_id,
            )
            for provider_event in provider_events:
                _apply_provider_event(task_id, provider_event)

            task = get_task_store().get(task_id)
            if task is None or _is_terminal_status(task.status):
                return
            time.sleep(_TASK_POLL_INTERVAL_SEC)
    finally:
        with _TASK_MONITOR_LOCK:
            _TASK_MONITOR_THREADS.pop(task_id, None)


def _ensure_task_monitor(task_id: str) -> None:
    with _TASK_MONITOR_LOCK:
        thread = _TASK_MONITOR_THREADS.get(task_id)
        if thread is not None and thread.is_alive():
            return
        thread = threading.Thread(
            target=_monitor_task_events,
            args=(task_id,),
            daemon=True,
            name=f"vnext-task-monitor-{task_id}",
        )
        _TASK_MONITOR_THREADS[task_id] = thread
        thread.start()


@router.post("")
def create_task(request: CreateTaskRequest) -> dict:
    context = get_context_store().get(request.context_snapshot_id)
    if context is None:
        raise HTTPException(status_code=404, detail="context snapshot not found")

    task = TaskRecord(
        task_id=f"task_{uuid4().hex[:12]}",
        action=request.action,
        context_snapshot_id=request.context_snapshot_id,
        provider=request.agent_preferences.provider,
    )
    get_task_store().create(task)
    event = TaskEvent(
        event_id=f"evt_{uuid4().hex[:12]}",
        task_id=task.task_id,
        type=EventType.TASK_CREATED,
        sequence=get_event_store().next_sequence(task.task_id),
        payload={"action": task.action},
    )
    get_event_store().append(event)

    unified_request = UnifiedTaskRequest(
        task_id=task.task_id,
        action=request.action,
        user_input=request.user_input,
        context_snapshot_id=request.context_snapshot_id,
        provider=request.agent_preferences.provider,
        context_payload={
            "source_app": context.source_app,
            "selection_text": context.selection_text,
            "document_title": context.document_title,
            "metadata": context.metadata,
        },
        constraints=request.constraints.model_dump(),
    )
    provider_run_id = get_agent_gateway().create_run(unified_request)
    get_task_store().set_provider_run_id(task.task_id, provider_run_id)
    get_task_store().update_status(
        task.task_id,
        TaskStatus.RUNNING,
        stage="executing",
        message="Task accepted by provider",
    )
    _append_task_event(
        task.task_id,
        EventType.TASK_STAGE_CHANGED,
        {"stage": "executing", "message": "Task accepted by provider"},
    )
    _ensure_task_monitor(task.task_id)
    return {"task_id": task.task_id, "status": TaskStatus.RUNNING.value, "provider": task.provider}


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str) -> TaskResponse:
    task = get_task_store().get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    result = None
    if task.result is not None:
        result = TaskResultResponse(**asdict(task.result))
    return TaskResponse(
        task_id=task.task_id,
        status=task.status.value,
        action=task.action,
        provider=task.provider,
        progress_stage=task.progress_stage,
        progress_message=task.progress_message,
        provider_run_id=task.provider_run_id,
        result=result,
        error=task.error,
    )


@router.get("/{task_id}/events")
def list_task_events(task_id: str) -> dict:
    task = get_task_store().get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if not _is_terminal_status(task.status):
        _ensure_task_monitor(task_id)

    return {
        "task_id": task_id,
        "events": [
            {
                "event_id": event.event_id,
                "type": event.type.value,
                "sequence": event.sequence,
                "payload": event.payload,
            }
            for event in get_event_store().list_for_task(task_id)
        ],
    }
