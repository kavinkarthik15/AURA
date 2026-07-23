from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class PlanningObjectives:
    goal_progress: float = 0.0
    python_growth: float = 0.0
    ml_growth: float = 0.0
    dsa_growth: float = 0.0
    project_growth: float = 0.0
    time_cost: float = 0.0
    difficulty: float = 0.0
    confidence: float = 0.0
    energy_cost: float = 0.0
    profile_score: float | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_progress": round(self.goal_progress, 2),
            "python_growth": round(self.python_growth, 2),
            "ml_growth": round(self.ml_growth, 2),
            "dsa_growth": round(self.dsa_growth, 2),
            "project_growth": round(self.project_growth, 2),
            "time_cost": round(self.time_cost, 2),
            "difficulty": round(self.difficulty, 2),
            "confidence": round(self.confidence, 2),
            "energy_cost": round(self.energy_cost, 2),
        }
