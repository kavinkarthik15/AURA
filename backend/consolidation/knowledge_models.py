from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class KnowledgeCandidate:
    candidate_id: str = field(default_factory=lambda: f"KGC-{uuid4().hex[:12].upper()}")
    knowledge: str = ""
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    generated_from: str = ""
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
