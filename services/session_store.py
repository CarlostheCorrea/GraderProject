from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Optional
from uuid import uuid4


@dataclass
class SessionRecord:
    session_id: str
    document_text: str
    rubric_id: str
    rubric_json: dict
    grading_result: Optional[dict] = None
    conversation: List[dict] = field(default_factory=list)


class InMemorySessionStore:
    """
    MVP in-memory store.
    Replace this with a persistent store (Postgres/Redis) for production durability.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionRecord] = {}
        self._lock = Lock()

    def create(self, document_text: str, rubric_id: str, rubric_json: dict) -> SessionRecord:
        sid = str(uuid4())
        record = SessionRecord(
            session_id=sid,
            document_text=document_text,
            rubric_id=rubric_id,
            rubric_json=rubric_json,
            conversation=[],
        )
        with self._lock:
            self._sessions[sid] = record
        return record

    def get(self, session_id: str) -> Optional[SessionRecord]:
        return self._sessions.get(session_id)

    def update(self, session: SessionRecord) -> None:
        with self._lock:
            self._sessions[session.session_id] = session
