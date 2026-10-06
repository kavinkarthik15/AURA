from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryStatus(Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    MERGED = "MERGED"
    DEPRECATED = "DEPRECATED"

    @classmethod
    def coerce(cls, value: Any) -> "MemoryStatus":
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            normalized = value.strip().upper()
            for member in cls:
                if member.value == normalized:
                    return member
        return cls.ACTIVE


@dataclass
class KnowledgeRecord:
    knowledge_id: str = field(default_factory=lambda: f"KNW-{uuid4().hex[:12].upper()}")
    concept: str = ""
    statement: str = ""
    knowledge_type: str = "general"
    confidence: float = 0.5
    confidence_source: str | None = None
    importance: float = 0.5
    importance_source: str | None = None
    importance_reason: str | None = None
    status: MemoryStatus = field(default=MemoryStatus.ACTIVE)
    revision: int = 1
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_accessed: datetime = field(default_factory=utc_now)
    retrieval_count: int = 0
    supporting_episode_ids: list[str] = field(default_factory=list)
    related_knowledge_ids: list[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        self.retrieval_count += 1
        self.last_accessed = utc_now()
        self.updated_at = self.last_accessed


@dataclass
class MemoryRecord:
    memory_id: str = field(default_factory=lambda: f"MEM-{uuid4().hex[:12].upper()}")
    memory_type: str = "unknown"
    importance: float = 0.5
    confidence: float = 0.5
    retrieval_count: int = 0
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_accessed: datetime = field(default_factory=utc_now)
    data: Dict[str, Any] = field(default_factory=dict)
    experience_id: str | None = None
    revision: int = 1
    parent_memory_id: str | None = None
    related_memories: list[str] = field(default_factory=list)
    derived_from: list[str] = field(default_factory=list)
    merged_into: list[str] = field(default_factory=list)
    status: MemoryStatus = field(default=MemoryStatus.ACTIVE)
    confidence_source: str | None = None
    importance_reason: str | None = None
    importance_source: str | None = None

    def touch(self) -> None:
        self.retrieval_count += 1
        self.last_accessed = utc_now()
        self.updated_at = self.last_accessed
