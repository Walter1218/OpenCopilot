from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter

from stores_next.models import ContextSnapshot

from .dependencies import get_context_service
from .models import CreateContextSnapshotRequest

router = APIRouter(prefix="/vnext/context", tags=["vnext-context"])


@router.post("/snapshots")
def create_context_snapshot(request: CreateContextSnapshotRequest) -> dict:
    snapshot = ContextSnapshot(
        context_snapshot_id=f"ctx_{uuid4().hex[:12]}",
        trigger=request.trigger,
        source_app=request.source_app,
        selection_text=request.selection_text,
        document_title=request.document_title,
        metadata=request.metadata,
    )
    created = get_context_service().create_snapshot(snapshot)
    return {
        "context_snapshot_id": created.context_snapshot_id,
        "created_at": created.created_at,
        "summary": {
            "source_app": created.source_app,
            "document_title": created.document_title,
            "selection_chars": len(created.selection_text),
        },
    }
