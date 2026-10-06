from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class PatternCandidate:
    pattern_id: str = field(default_factory=lambda: f"PAT-{uuid4().hex[:12].upper()}")
    pattern_type: str = ""
    confidence: float = 0.0
    importance: float = 0.0
    support_count: int = 0
    episode_ids: list[str] = field(default_factory=list)
    summary: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
