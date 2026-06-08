from __future__ import annotations

from typing import Dict, Optional

from .models import ApplyPreview, ApplyStatus


class ApplyPreviewStore:
    def __init__(self) -> None:
        self._previews: Dict[str, ApplyPreview] = {}

    def create(self, preview: ApplyPreview) -> ApplyPreview:
        self._previews[preview.preview_id] = preview
        return preview

    def get(self, preview_id: str) -> Optional[ApplyPreview]:
        return self._previews.get(preview_id)

    def mark_confirmed(self, preview_id: str) -> ApplyPreview:
        preview = self._require(preview_id)
        preview.status = ApplyStatus.CONFIRMED
        return preview

    def _require(self, preview_id: str) -> ApplyPreview:
        preview = self.get(preview_id)
        if preview is None:
            raise KeyError(f"Unknown preview_id: {preview_id}")
        return preview
