from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from backend.memory.memory_interfaces import MemoryStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkingMemoryRecord:
    memory_id: str
    type: str
    value: Any
    importance: float = 0.5
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "type": self.type,
            "value": self.value,
            "importance": self.importance,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class WorkingMemorySession:
    working_memory_id: str
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    records: Dict[str, WorkingMemoryRecord] = field(default_factory=dict)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "working_memory_id": self.working_memory_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "records": [record.to_dict() for record in self.records.values()],
        }


class WorkingMemory(MemoryStore):
    memory_type = "working"

    def __init__(self) -> None:
        self._sessions: Dict[str, WorkingMemorySession] = {}
        self._active_session_id: str | None = None

    @property
    def active_session_id(self) -> str | None:
        return self._active_session_id

    def create_session(self) -> str:
        session_id = f"WM-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{uuid4().hex[:6].upper()}"
        self._sessions[session_id] = WorkingMemorySession(working_memory_id=session_id)
        self._active_session_id = session_id
        return session_id

    def end_session(self, session_id: str | None = None, retain: bool = False) -> Dict[str, Any] | None:
        session_id = session_id or self._active_session_id
        if session_id is None:
            return None
        snapshot = self.snapshot(session_id)
        if not retain:
            self._sessions.pop(session_id, None)
        if self._active_session_id == session_id:
            self._active_session_id = None
        return snapshot

    def clear_session(self, session_id: str | None = None) -> None:
        self.clear(session_id)

    def store(self, record: Dict[str, Any]) -> Dict[str, Any]:
        record = dict(record)
        session_id = record.pop("working_memory_id", None) or self._active_session_id
        if session_id is None:
            session_id = self.create_session()
        if session_id not in self._sessions:
            self._sessions[session_id] = WorkingMemorySession(working_memory_id=session_id)
        session = self._sessions[session_id]
        memory_id = record.pop("memory_id", None) or f"WMR-{uuid4().hex[:10].upper()}"
        item = WorkingMemoryRecord(
            memory_id=memory_id,
            type=str(record.pop("type", "context")),
            value=record.pop("value", record),
            importance=float(record.pop("importance", 0.5)),
        )
        session.records[item.memory_id] = item
        session.updated_at = item.updated_at
        return {**item.to_dict(), "working_memory_id": session_id}

    def retrieve(self, query: Dict[str, Any] | None = None, top_k: int = 10) -> List[Dict[str, Any]]:
        query = query or {}
        session_id = query.get("working_memory_id") or self._active_session_id
        if session_id is None or session_id not in self._sessions:
            return []
        records = list(self._sessions[session_id].records.values())
        record_type = query.get("type")
        if record_type:
            records = [record for record in records if record.type == record_type]
        return [record.to_dict() for record in records[-top_k:]]

    def update(self, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any] | None:
        for session in self._sessions.values():
            item = session.records.get(memory_id)
            if item is None:
                continue
            if "type" in updates:
                item.type = str(updates["type"])
            if "value" in updates:
                item.value = updates["value"]
            if "importance" in updates:
                item.importance = float(updates["importance"])
            item.updated_at = _now()
            session.updated_at = item.updated_at
            return item.to_dict()
        return None

    def delete(self, memory_id: str) -> bool:
        for session in self._sessions.values():
            if session.records.pop(memory_id, None) is not None:
                session.updated_at = _now()
                return True
        return False

    def clear(self, session_id: str | None = None) -> None:
        session_id = session_id or self._active_session_id
        if session_id in self._sessions:
            self._sessions[session_id].records.clear()
            self._sessions[session_id].updated_at = _now()

    def set_goal(self, goal: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_cognitive("goal", goal, session_id, 0.95)

    def add_experience(self, experience: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_cognitive("experience", experience, session_id, 0.7)

    def add_candidate_plan(self, plan: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_cognitive("candidate_plan", plan, session_id, 0.8)

    def set_strategy(self, strategy: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_cognitive("strategy", strategy, session_id, 0.75)

    def add_constraint(self, constraint: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_cognitive("constraint", constraint, session_id, 0.85)

    def set_confidence(self, confidence: float, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_cognitive("confidence", confidence, session_id, 0.8)

    def store_reflection(self, reflection: Any, session_id: str | None = None) -> Dict[str, Any]:
        return self._store_cognitive("reflection", reflection, session_id, 0.9)

    def remove(self, memory_id: str) -> bool:
        return self.delete(memory_id)

    def snapshot(self, session_id: str | None = None) -> Dict[str, Any]:
        session_id = session_id or self._active_session_id
        if session_id is None or session_id not in self._sessions:
            return {"working_memory_id": session_id, "records": []}
        return self._sessions[session_id].snapshot()

    def health(self) -> Dict[str, Any]:
        return {
            "healthy": True,
            "active_session_id": self._active_session_id,
            "active_sessions": len(self._sessions),
        }

    def _require_session(self, session_id: str) -> WorkingMemorySession:
        if session_id not in self._sessions:
            raise ValueError(f"Unknown working memory session: {session_id}")
        return self._sessions[session_id]

    def _store_cognitive(
        self, record_type: str, value: Any, session_id: str | None, importance: float
    ) -> Dict[str, Any]:
        record = {"type": record_type, "value": value, "importance": importance}
        if session_id is not None:
            record["working_memory_id"] = session_id
        return self.store(record)
