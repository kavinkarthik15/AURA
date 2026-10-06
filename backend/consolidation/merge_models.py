from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class MergeDecision:
    decision_id: str = field(default_factory=lambda: f"MRG-{uuid4().hex[:12].upper()}")
    action: str = "IGNORE"
    target_knowledge_id: str | None = None
    similarity: float = 0.0
    merge_reason: str = ""
    confidence_change: float = 0.0
    revision_increment: int = 0
    updated_evidence: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
