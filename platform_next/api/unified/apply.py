from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .dependencies import get_apply_service
from .models import ApplyCommitRequest, ApplyPreviewRequest

router = APIRouter(prefix="/vnext/apply", tags=["vnext-apply"])


@router.post("/preview")
def create_apply_preview(request: ApplyPreviewRequest) -> dict:
    preview = get_apply_service().create_preview(task_id=request.task_id, operation=request.apply_operation)
    return {
        "preview_id": preview.preview_id,
        "target": {"type": "selection"},
        "diff": preview.diff,
        "safe_to_commit": True,
        "warnings": preview.warnings,
    }


@router.post("/commit")
def commit_apply(request: ApplyCommitRequest) -> dict:
    if not request.confirmed_by_user:
        raise HTTPException(status_code=400, detail="user confirmation required")
    status = get_apply_service().commit_preview(request.preview_id)
    return {"status": status, "applied_at": "pending"}
