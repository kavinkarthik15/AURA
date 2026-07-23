from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ObjectiveProfile:
    name: str
    weights: Dict[str, float] = field(default_factory=dict)

    def score(self, objectives: Dict[str, float]) -> float:
        score = 0.0
        for key, weight in self.weights.items():
            score += weight * objectives.get(key, 0.0)
        return round(score, 3)
