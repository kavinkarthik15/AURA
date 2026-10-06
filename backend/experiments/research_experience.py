"""
17.0A Research Experience Schema

A research experience captures a single prediction-learning scenario:
- Initial skill state
- Action selected by digital twin
- Predicted future state
- Actual future state (ground truth)
- Experience category (for analysis)
"""

from typing import Dict, Literal
from pydantic import BaseModel, Field


ExperienceCategoryType = Literal[
    "low_skill_practice",
    "medium_skill_practice",
    "high_skill_practice",
    "low_motivation",
    "high_motivation",
    "mixed_skills",
    "project_completion",
    "plateau",
]


class ResearchExperience(BaseModel):
    """
    A deterministic research experience for learning validation.

    Each experience is a tuple:
    - initial_state → action → predicted_future → actual_future
    """

    experience_id: str = Field(
        ..., description="Unique identifier for this experience"
    )
    category: ExperienceCategoryType = Field(
        ..., description="Category of experience (e.g., low_skill_practice)"
    )
    initial_state: Dict[str, int] = Field(
        ..., description="Initial skill state (e.g., {'python': 30, 'dsa': 20})"
    )
    selected_action: str = Field(
        ..., description="Action name selected by digital twin (e.g., 'Python Project')"
    )
    predicted_future_state: Dict[str, int] = Field(
        ..., description="Digital twin's prediction of future state"
    )
    actual_future_state: Dict[str, int] = Field(
        ..., description="Actual observed future state (ground truth)"
    )

    model_config = {"validate_assignment": True, "extra": "forbid"}

    def prediction_error(self) -> float:
        """
        Calculate mean absolute error (MAE) of the prediction.
        """
        keys = set(self.predicted_future_state.keys()) | set(
            self.actual_future_state.keys()
        )
        if not keys:
            return 0.0
        errors = [
            abs(
                self.predicted_future_state.get(k, 0)
                - self.actual_future_state.get(k, 0)
            )
            for k in keys
        ]
        return round(sum(errors) / len(errors), 2)


class ResearchDataset(BaseModel):
    """
    A split dataset for research validation.

    Training: 80 experiences for calibration
    Held-out: 20 experiences for evaluation
    """

    dataset_id: str = Field(
        ..., description="Unique identifier for this dataset"
    )
    seed: int = Field(
        ..., description="Random seed used for deterministic generation"
    )
    training_experiences: list[ResearchExperience] = Field(
        default_factory=list, description="80 training experiences"
    )
    held_out_experiences: list[ResearchExperience] = Field(
        default_factory=list, description="20 held-out evaluation experiences"
    )

    model_config = {"validate_assignment": True, "extra": "forbid"}

    def training_size(self) -> int:
        return len(self.training_experiences)

    def held_out_size(self) -> int:
        return len(self.held_out_experiences)

    def total_size(self) -> int:
        return self.training_size() + self.held_out_size()
