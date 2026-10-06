from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class ValidatedKnowledgeCandidate:
    validation_id: str = field(default_factory=lambda: f"VAL-{uuid4().hex[:12].upper()}")
    candidate_id: str = ""
    validation_score: float = 0.0
    decision: str = "REJECT"
    reasons: list[str] = field(default_factory=list)
    failed_rules: list[str] = field(default_factory=list)
    passed_rules: list[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
