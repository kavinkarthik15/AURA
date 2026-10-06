"""
17.0D Robustness Testing: Verify learned improvement survives different seeds.

This experiment runs the learnable benchmark and calibration learning
across multiple random seeds to verify that the improvement is not an
artifact of one particular synthetic dataset, but rather a consistent
property of the learning system.

Success Criterion:
- Learning shows positive improvement (learning_mae < baseline_mae) on
  majority of seeds (e.g., 70%+ of tested seeds)
- Improvement magnitude is consistent (not high variance across seeds)
- No single seed shows catastrophic divergence (>300% worse)
"""

from typing import Dict, List
from pydantic import BaseModel, Field
from datetime import datetime
import json

from backend.experiments.research_experiment_17_0_b import (
    ResearchExperiment17_0_B,
    ResearchExperimentResult,
)
from backend.experiments.research_benchmark_17_0_a import ResearchBenchmarkGenerator
from backend.experiments.research_dataset_persistence import ResearchDatasetPersistence


class SeedResult(BaseModel):
    """Result from a single seed's experiment."""

    seed: int = Field(..., description="Random seed used for dataset generation")
    baseline_mae: float = Field(..., description="Baseline prediction MAE on held-out")
    learning_mae: float = Field(..., description="Learning system MAE on held-out")
    improvement_percent: float = Field(
        ..., description="Relative improvement: 100*(baseline-learning)/baseline"
    )
    improvement_status: str = Field(
        ...,
        description="'positive' if learning < baseline, else 'negative'",
    )


class RobustnessResult17_0_D(BaseModel):
    """Results from 17.0D robustness testing across multiple seeds."""

    experiment_id: str = Field(default="research_17_0_d_robustness")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_seeds_tested: int = Field(..., description="Number of seeds tested")
    seed_results: List[SeedResult] = Field(..., description="Results for each seed")

    # Statistics
    positive_improvement_count: int = Field(
        ..., description="Number of seeds with learning_mae < baseline_mae"
    )
    average_improvement_percent: float = Field(
        ..., description="Average improvement across all seeds"
    )
    median_improvement_percent: float = Field(
        ..., description="Median improvement across seeds"
    )
    improvement_std_dev: float = Field(
        ..., description="Standard deviation of improvement across seeds"
    )
    max_improvement_percent: float = Field(
        ..., description="Best improvement seen"
    )
    min_improvement_percent: float = Field(
        ..., description="Worst improvement (most negative) seen"
    )
    robustness_score: float = Field(
        ...,
        description="Percentage of seeds showing positive improvement",
    )

    def success(self) -> bool:
        """Pass if majority of seeds show positive improvement."""
        return self.robustness_score >= 70.0


class ResearchExperiment17_0_D:
    """Run robustness testing across multiple seeds."""

    def __init__(
        self,
        seeds: List[int] = None,
        learning_rate: float = 0.007,
        bounds: Dict[str, float] = None,
    ):
        """
        Initialize 17.0D robustness test.

        Args:
            seeds: List of random seeds to test. Default: [42, 123, 456, 789, 999]
            learning_rate: Learning rate for calibration (default: 0.007 from 17.0C)
            bounds: Calibration bounds (default: tuned values from 17.0C)
        """
        self.seeds = seeds or [42, 123, 456, 789, 999]
        self.learning_rate = learning_rate

        # Tuned parameters from 17.0C
        self.bounds = bounds or {
            "state_adjustment_max": 0.12,
            "probability_bias_max": 0.012,
            "risk_bias_max": 0.012,
            "uncertainty_increment_max": 0.012,
            "confidence_increment_max": 0.012,
        }

        self.persistence = ResearchDatasetPersistence()

    def run(self, experiment_id: str = "research_17_0_d_robustness") -> RobustnessResult17_0_D:
        """
        Run experiment across all seeds.

        Returns:
            RobustnessResult17_0_D with statistics across seeds
        """
        seed_results = []

        # Test each seed
        for seed in self.seeds:
            result = self._run_single_seed(seed)
            seed_results.append(result)

        # Calculate statistics
        improvements = [r.improvement_percent for r in seed_results]
        positive_count = sum(1 for r in seed_results if r.improvement_status == "positive")

        import statistics

        robustness_result = RobustnessResult17_0_D(
            experiment_id=experiment_id,
            timestamp=datetime.utcnow(),
            total_seeds_tested=len(self.seeds),
            seed_results=seed_results,
            positive_improvement_count=positive_count,
            average_improvement_percent=float(statistics.mean(improvements)),
            median_improvement_percent=float(statistics.median(improvements)),
            improvement_std_dev=float(
                statistics.stdev(improvements) if len(improvements) > 1 else 0.0
            ),
            max_improvement_percent=float(max(improvements)),
            min_improvement_percent=float(min(improvements)),
            robustness_score=100.0 * positive_count / len(self.seeds),
        )

        return robustness_result

    def _run_single_seed(self, seed: int) -> SeedResult:
        """Run experiment with a single seed."""
        # Generate dataset (dataset_id is set by generator)
        generator = ResearchBenchmarkGenerator(seed=seed)
        dataset = generator.generate_dataset()

        # Save it for reproducibility
        self.persistence.save_dataset(dataset)

        # Run experiment
        experiment = ResearchExperiment17_0_B(
            dataset, learning_rate=self.learning_rate, bounds=self.bounds
        )
        result = experiment.run()

        # Record seed result
        improvement_status = "positive" if result.improvement_percent > 0 else "negative"

        return SeedResult(
            seed=seed,
            baseline_mae=result.baseline_mae,
            learning_mae=result.learning_mae,
            improvement_percent=result.improvement_percent,
            improvement_status=improvement_status,
        )


def run_research_experiment_17_0_d(
    seeds: List[int] = None,
    learning_rate: float = 0.007,
    bounds: Dict[str, float] = None,
    experiment_id: str = "research_17_0_d_robustness",
) -> RobustnessResult17_0_D:
    """
    Convenience function to run 17.0D robustness testing.

    Args:
        seeds: Random seeds to test across
        learning_rate: Learning rate for calibration
        bounds: Calibration bounds
        experiment_id: Name for this experiment run

    Returns:
        RobustnessResult17_0_D with cross-seed statistics
    """
    experiment = ResearchExperiment17_0_D(
        seeds=seeds, learning_rate=learning_rate, bounds=bounds
    )
    return experiment.run(experiment_id=experiment_id)
