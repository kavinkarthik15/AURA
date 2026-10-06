"""
17.1A Ablation Study: Compare Condition A (Baseline) vs Condition B (Learning)

This is a formal ablation study that isolates the effect of calibration on
held-out prediction accuracy. Uses the 17.0 learnable benchmark to ensure a
controlled experimental setup.

Conditions:
  A: Baseline — No calibration applied, predictions use default SimulationEngine
  B: Learning — Calibration enabled with learning_rate=0.007, bounds tuned

Design:
  - Both conditions use identical training data (80 experiences)
  - Both test on identical held-out data (20 experiences)
  - Only difference: presence/absence of calibration
  - Metric: Mean Absolute Error on held-out predictions

Pass Criterion:
  Learning (Condition B) MAE < Baseline (Condition A) MAE
"""

from typing import Dict
from pydantic import BaseModel, Field
from datetime import datetime

from backend.experiments.research_experiment_17_0_b import (
    ResearchExperiment17_0_B,
)
from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.experiments.research_dataset_persistence import ResearchDatasetPersistence
from backend.experiments.research_experience import ResearchDataset


class AblationConditionResult(BaseModel):
    """Result from a single condition in the ablation study."""

    condition_name: str = Field(..., description="'Baseline' or 'Learning'")
    condition_description: str = Field(
        ..., description="Description of the condition"
    )
    held_out_mae: float = Field(..., description="MAE on held-out experiences")
    training_mae: float = Field(
        ..., description="MAE on training experiences (info only)"
    )


class AblationResult17_1_A(BaseModel):
    """Results from 17.1A ablation study comparing Condition A vs B."""

    experiment_id: str = Field(default="research_17_1_a_ablation")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dataset_id: str = Field(..., description="ID of dataset used")
    seed: int = Field(..., description="Random seed for reproducibility")

    # Individual results
    condition_a: AblationConditionResult = Field(
        ..., description="Baseline (no calibration)"
    )
    condition_b: AblationConditionResult = Field(..., description="Learning (calibration)")

    # Comparative metrics
    absolute_improvement: float = Field(
        ...,
        description="condition_a_mae - condition_b_mae (positive = learning better)",
    )
    improvement_percent: float = Field(
        ...,
        description="100 * (condition_a_mae - condition_b_mae) / condition_a_mae",
    )

    def success(self) -> bool:
        """Pass if learning MAE < baseline MAE."""
        return self.condition_b.held_out_mae < self.condition_a.held_out_mae


class ResearchAblation17_1_A:
    """Formal ablation study: Condition A (Baseline) vs Condition B (Learning)."""

    def __init__(
        self,
        dataset: ResearchDataset = None,
        seed: int = 42,
        learning_rate: float = 0.007,
        bounds: Dict[str, float] = None,
    ):
        """
        Initialize ablation study.

        Args:
            dataset: Pre-existing dataset to use. If None, generates from seed.
            seed: Random seed for determinism
            learning_rate: Learning rate for calibration (Condition B)
            bounds: Calibration bounds (Condition B)
        """
        self.seed = seed
        self.learning_rate = learning_rate

        # Tuned parameters from 17.0C
        self.bounds = bounds or {
            "state_adjustment_max": 0.12,
            "probability_bias_max": 0.012,
            "risk_bias_max": 0.012,
            "uncertainty_increment_max": 0.012,
            "confidence_increment_max": 0.012,
        }

        # Generate or use provided dataset
        if dataset is None:
            generator = ResearchBenchmarkGenerator(seed=seed)
            self.dataset = generator.generate_dataset()
        else:
            self.dataset = dataset

    def run(self, experiment_id: str = "research_17_1_a_ablation") -> AblationResult17_1_A:
        """
        Run ablation study: compare Condition A vs B.

        Returns:
            AblationResult17_1_A with comparative analysis
        """
        # CONDITION A: Baseline (no calibration)
        experiment_a = ResearchExperiment17_0_B(
            self.dataset, learning_rate=0.0, bounds=self.bounds
        )
        result_a = experiment_a.run()

        condition_a = AblationConditionResult(
            condition_name="Baseline",
            condition_description="No calibration; predictions from default simulation",
            held_out_mae=result_a.baseline_mae,
            training_mae=result_a.baseline_mae,  # baseline uses same prediction for all
        )

        # CONDITION B: Learning (calibration enabled)
        experiment_b = ResearchExperiment17_0_B(
            self.dataset, learning_rate=self.learning_rate, bounds=self.bounds
        )
        result_b = experiment_b.run()

        condition_b = AblationConditionResult(
            condition_name="Learning",
            condition_description=f"Calibration enabled (learning_rate={self.learning_rate})",
            held_out_mae=result_b.learning_mae,
            training_mae=result_b.baseline_mae,  # baseline for reference
        )

        # Calculate improvement
        absolute_improvement = condition_a.held_out_mae - condition_b.held_out_mae
        improvement_percent = (
            100.0 * absolute_improvement / condition_a.held_out_mae
            if condition_a.held_out_mae > 0
            else 0.0
        )

        return AblationResult17_1_A(
            experiment_id=experiment_id,
            timestamp=datetime.utcnow(),
            dataset_id=self.dataset.dataset_id,
            seed=self.seed,
            condition_a=condition_a,
            condition_b=condition_b,
            absolute_improvement=absolute_improvement,
            improvement_percent=improvement_percent,
        )


def run_research_ablation_17_1_a(
    dataset: ResearchDataset = None,
    seed: int = 42,
    learning_rate: float = 0.007,
    bounds: Dict[str, float] = None,
    experiment_id: str = "research_17_1_a_ablation",
) -> AblationResult17_1_A:
    """
    Convenience function to run 17.1A ablation study.

    Args:
        dataset: Pre-existing dataset (or generate from seed)
        seed: Random seed for reproducibility
        learning_rate: Learning rate for Condition B
        bounds: Calibration bounds for Condition B
        experiment_id: Name for this experiment

    Returns:
        AblationResult17_1_A with detailed comparison
    """
    ablation = ResearchAblation17_1_A(
        dataset=dataset, seed=seed, learning_rate=learning_rate, bounds=bounds
    )
    return ablation.run(experiment_id=experiment_id)
