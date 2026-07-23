from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class SearchMetrics:
    plans_generated: int = 0
    plans_evaluated: int = 0
    search_depth: int = 0
    beam_width: int = 0
    search_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plans_generated": self.plans_generated,
            "plans_evaluated": self.plans_evaluated,
            "search_depth": self.search_depth,
            "beam_width": self.beam_width,
            "search_time_ms": round(self.search_time_ms, 2),
        }
