from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .models import utc_now_iso


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    mode: str = "smart_copilot"
    task_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionRecord] = {}

    def create(self, session: SessionRecord) -> SessionRecord:
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Optional[SessionRecord]:
        return self._sessions.get(session_id)
