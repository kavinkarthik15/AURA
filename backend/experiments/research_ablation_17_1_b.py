"""
17.1B Ablation Robustness: Run 17.1A across multiple seeds

Simple multi-seed validation that the ablation results (Condition A vs B)
are consistent across different random datasets.

Pass Criterion: Learning wins on majority of seeds
"""

from typing import List
from pydantic import BaseModel, Field
from datetime import datetime
import statistics

from backend.experiments.research_ablation_17_1_a import run_research_ablation_17_1_a


class SeedAblationResult(BaseModel):
    """Result from one seed's ablation study."""

    seed: int = Field(..., description="Random seed")
    condition_a_mae: float = Field(..., description="Baseline MAE")
    condition_b_mae: float = Field(..., description="Learning MAE")
    improvement_percent: float = Field(..., description="Learning improvement %")
    learning_wins: bool = Field(
        ..., description="True if condition_b < condition_a"
    )


class RobustnessResult17_1_B(BaseModel):
    """Results from 17.1B multi-seed ablation robustness test."""

    experiment_id: str = Field(default="research_17_1_b_ablation_robustness")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_seeds: int = Field(..., description="Number of seeds tested")
    seed_results: List[SeedAblationResult] = Field(..., description="Per-seed results")

    # Statistics
    learning_wins_count: int = Field(
        ..., description="Number of seeds where learning won"
    )
    learning_win_rate: float = Field(
        ..., description="Percentage of seeds where learning won"
    )
    average_improvement: float = Field(..., description="Average improvement %")
    median_improvement: float = Field(..., description="Median improvement %")
    min_improvement: float = Field(..., description="Minimum improvement %")
    max_improvement: float = Field(..., description="Maximum improvement %")
    std_dev_improvement: float = Field(
        ..., description="Standard deviation of improvements"
    )

    def success(self) -> bool:
        """Pass if learning wins on majority of seeds."""
        return self.learning_win_rate >= 80.0


def run_research_ablation_17_1_b(
    seeds: List[int] = None,
    learning_rate: float = 0.007,
) -> RobustnessResult17_1_B:
    """
    Run ablation study across multiple seeds.

    Args:
        seeds: List of seeds to test (default: [42, 123, 456, 789, 999])
        learning_rate: Learning rate for calibration

    Returns:
        RobustnessResult17_1_B with cross-seed statistics
    """
    if seeds is None:
        seeds = [42, 123, 456, 789, 999]

    seed_results = []

    # Run ablation for each seed
    for seed in seeds:
        ablation_result = run_research_ablation_17_1_a(seed=seed, learning_rate=learning_rate)

        learning_wins = ablation_result.success()

        seed_result = SeedAblationResult(
            seed=seed,
            condition_a_mae=ablation_result.condition_a.held_out_mae,
            condition_b_mae=ablation_result.condition_b.held_out_mae,
            improvement_percent=ablation_result.improvement_percent,
            learning_wins=learning_wins,
        )
        seed_results.append(seed_result)

    # Calculate statistics
    improvements = [r.improvement_percent for r in seed_results]
    learning_wins_count = sum(1 for r in seed_results if r.learning_wins)
    learning_win_rate = 100.0 * learning_wins_count / len(seeds)

    robustness_result = RobustnessResult17_1_B(
        experiment_id="research_17_1_b_ablation_robustness",
        timestamp=datetime.utcnow(),
        total_seeds=len(seeds),
        seed_results=seed_results,
        learning_wins_count=learning_wins_count,
        learning_win_rate=learning_win_rate,
        average_improvement=float(statistics.mean(improvements)),
        median_improvement=float(statistics.median(improvements)),
        min_improvement=float(min(improvements)),
        max_improvement=float(max(improvements)),
        std_dev_improvement=float(
            statistics.stdev(improvements) if len(improvements) > 1 else 0.0
        ),
    )

    return robustness_result
