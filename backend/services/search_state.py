from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class SearchState:
    actions: List[str] = field(default_factory=list)
    current_state: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    depth: int = 0
    goal_progress: float = 0.0
    confidence: float = 0.0
