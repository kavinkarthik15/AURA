from __future__ import annotations

from typing import Dict, Any, Optional

from pydantic import BaseModel, Field


class ExperimentConfig(BaseModel):
    pairs: int = Field(..., gt=0, description="Number of experience pairs (N,N+1) to generate")
    learning_rate: float = Field(0.1)
    bounds: Optional[Dict[str, Any]] = Field(default=None)
    apply_accepted: bool = Field(True)
    output_dir: Optional[str] = Field(None)
    experiment_id: Optional[str] = Field(None)
    seed: Optional[int] = Field(0)
    noise_scale: float = Field(1.0, description="Scale for synthetic actual deviations")

    model_config = {"validate_assignment": True, "extra": "forbid"}
