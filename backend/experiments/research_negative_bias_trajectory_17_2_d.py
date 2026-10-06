"""
17.2D Negative-Bias Constraint/Trajectory Analysis

Diagnostic experiment to trace where the negative-bias learning failure originates.

Research Question:
    Does expected_state_bias actually become negative for negative-bias categories,
    or is it prevented from doing so somewhere in the calibration/prediction pipeline?

Three Possible Cases:

    Case A: Parameter becomes negative, but prediction stays wrong
            → Problem is downstream (prediction integration)
    
    Case B: Parameter stays positive despite negative error signals
            → Problem is in update rule (constraint/bounds)
    
    Case C: Parameter oscillates (+ → 0 → + → 0)
            → Problem is instability or competing updates

Methodology:
    - Track expected_state_bias trajectory at every training step
    - Focus on negative-bias categories (true_bias < 0)
    - Record: initial, final, min, max, cumulative signed update
    - Measure: error signals vs parameter changes
    - Compare: learned_bias vs true_bias vs prediction behavior
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, Optional, List

from pydantic import BaseModel, Field

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.services.digital_twin_calibrator import DigitalTwinCalibrator
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator
from backend.services.simulation_engine import SimulationEngine
from backend.services.transition_engine import TransitionEngine


class BiasTrajectorySample(BaseModel):
    """Single point in the expected_state_bias trajectory."""

    step: int
    experience_id: str
    predicted_state_value: float
    actual_state_value: float
    signed_error: float  # actual - predicted
    expected_state_bias_before: float
    expected_state_bias_after: float
    bias_update_delta: float
    calibration_confidence: float


class NegativeBiasCategoryTrajectory(BaseModel):
    """Complete trajectory for one negative-bias category."""

    category: str
    true_systematic_bias: float
    initial_bias: float
    final_bias: float
    minimum_bias_reached: float
    maximum_bias_reached: float
    total_signed_update: float
    num_negative_error_signals: int
    num_positive_error_signals: int
    trajectory_samples: List[BiasTrajectorySample] = Field(default_factory=list)
    diagnosis: str = "PENDING"  # "A", "B", or "C" based on patterns


class TrajectoryAnalysisResult(BaseModel):
    """Results from 17.2D trajectory analysis."""

    experiment_id: str
    dataset_id: str
    seed: int
    timestamp: str
    learning_rate: float
    bounds: Dict[str, float]
    negative_bias_categories: Dict[str, NegativeBiasCategoryTrajectory] = Field(
        default_factory=dict,
        description="Trajectory analysis per negative-bias category",
    )
    summary: str = ""


class ResearchNegativeBiasTrajectory17_2_D:
    """Analyze expected_state_bias trajectory for negative-bias categories."""

    NEGATIVE_BIAS_CATEGORIES = {"high_skill_practice", "high_motivation"}
    CATEGORY_SYSTEMATIC_BIAS = {
        "low_skill_practice": 4,
        "medium_skill_practice": 3,
        "high_skill_practice": -3,
        "low_motivation": 5,
        "high_motivation": -4,
        "mixed_skills": 3,
        "project_completion": 5,
        "plateau": 0,
    }

    def __init__(
        self,
        dataset: Optional[object] = None,
        seed: int = 42,
        learning_rate: float = 0.007,
        bounds: Optional[Dict[str, float]] = None,
    ):
        self.seed = seed
        self.learning_rate = learning_rate
        self.bounds = bounds or {
            "state_adjustment_max": 0.12,
            "probability_bias_max": 0.012,
            "risk_bias_max": 0.012,
            "uncertainty_increment_max": 0.012,
            "confidence_increment_max": 0.012,
        }

        if dataset is not None:
            self.dataset = dataset
            self.dataset_id = dataset.dataset_id
        else:
            generator = ResearchBenchmarkGenerator(seed=seed)
            self.dataset = generator.generate_dataset(training_size=80, held_out_size=20)
            self.dataset_id = self.dataset.dataset_id

        self.calibrator = DigitalTwinCalibrator()
        self.evaluator = PredictionErrorEvaluator()
        self.transition_engine = TransitionEngine()

    def run(self, experiment_id: str = "research_negative_bias_trajectory_17_2_d") -> TrajectoryAnalysisResult:
        """Run trajectory analysis for negative-bias categories."""

        # Track trajectories per negative-bias category
        trajectories: Dict[str, NegativeBiasCategoryTrajectory] = {
            cat: NegativeBiasCategoryTrajectory(
                category=cat,
                true_systematic_bias=float(self.CATEGORY_SYSTEMATIC_BIAS[cat]),
                initial_bias=0.0,
                final_bias=0.0,
                minimum_bias_reached=0.0,
                maximum_bias_reached=0.0,
                total_signed_update=0.0,
                num_negative_error_signals=0,
                num_positive_error_signals=0,
            )
            for cat in self.NEGATIVE_BIAS_CATEGORIES
        }

        current_params = CalibrationParameters()

        for step_idx, experience in enumerate(self.dataset.training_experiences):
            if experience.category not in self.NEGATIVE_BIAS_CATEGORIES:
                continue

            # Record bias BEFORE calibration
            bias_before = current_params.expected_state_bias.copy()

            # Simulate prediction
            sim = SimulationEngine(
                transition_engine=self.transition_engine,
                calibration_parameters=current_params,
            )
            predicted = sim.simulate_action(experience.initial_state, experience.selected_action)
            predicted_state = predicted["predicted_future_state"]
            actual_state = experience.actual_future_state

            # Evaluate error
            decision = DecisionOutcome(
                decision_id=experience.experience_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                selected_action=experience.selected_action,
                predicted_state=predicted_state,
                predicted_trajectory_score=0.5,
                predicted_probability=0.5,
                predicted_risk=0.3,
                predicted_uncertainty=0.2,
                actual_state=actual_state,
            )
            error_result = self.evaluator.evaluate(decision)

            # Compute signed error (negative = underestimated, positive = overestimated)
            all_keys = sorted(set(predicted_state.keys()) | set(actual_state.keys()))
            signed_errors = [
                float(actual_state.get(key, 0)) - float(predicted_state.get(key, 0))
                for key in all_keys
            ]
            mean_signed_error = sum(signed_errors) / len(signed_errors) if signed_errors else 0.0

            # Apply calibration
            calibration_result = self.calibrator.calibrate(
                error_result=error_result,
                current_parameters=current_params,
                learning_rate=self.learning_rate,
                bounds=self.bounds,
            )
            current_params = calibration_result.updated_parameters

            # Record bias AFTER calibration
            bias_after = current_params.expected_state_bias.copy()

            # Compute bias change
            bias_values_before = list(bias_before.values()) if bias_before else [0.0]
            bias_values_after = list(bias_after.values()) if bias_after else [0.0]
            bias_before_avg = sum(bias_values_before) / len(bias_values_before) if bias_values_before else 0.0
            bias_after_avg = sum(bias_values_after) / len(bias_values_after) if bias_values_after else 0.0
            bias_delta = bias_after_avg - bias_before_avg

            # Track for this category
            category = experience.category
            if category in trajectories:
                if step_idx == 0 or len(trajectories[category].trajectory_samples) == 0:
                    trajectories[category].initial_bias = bias_before_avg

                trajectories[category].final_bias = bias_after_avg
                trajectories[category].minimum_bias_reached = min(
                    trajectories[category].minimum_bias_reached,
                    bias_after_avg,
                )
                trajectories[category].maximum_bias_reached = max(
                    trajectories[category].maximum_bias_reached,
                    bias_after_avg,
                )
                trajectories[category].total_signed_update += bias_delta

                if mean_signed_error < 0:
                    trajectories[category].num_negative_error_signals += 1
                else:
                    trajectories[category].num_positive_error_signals += 1

                # Record sample
                sample = BiasTrajectorySample(
                    step=step_idx,
                    experience_id=experience.experience_id,
                    predicted_state_value=float(sum(predicted_state.values()) / len(predicted_state)) if predicted_state else 0.0,
                    actual_state_value=float(sum(actual_state.values()) / len(actual_state)) if actual_state else 0.0,
                    signed_error=mean_signed_error,
                    expected_state_bias_before=bias_before_avg,
                    expected_state_bias_after=bias_after_avg,
                    bias_update_delta=bias_delta,
                    calibration_confidence=float(calibration_result.confidence or 0.0),
                )
                trajectories[category].trajectory_samples.append(sample)

        # Diagnose each negative-bias category
        for category, trajectory in trajectories.items():
            true_bias = self.CATEGORY_SYSTEMATIC_BIAS[category]

            # Determine diagnosis based on trajectory pattern
            diagnosis = self._determine_diagnosis(
                trajectory=trajectory,
                true_bias=true_bias,
            )
            trajectory.diagnosis = diagnosis

        # Generate summary
        summary_lines = []
        for cat, traj in trajectories.items():
            summary_lines.append(
                f"{cat}: final_bias={traj.final_bias:.4f} (true={traj.true_systematic_bias}), "
                f"min={traj.minimum_bias_reached:.4f}, diagnosis={traj.diagnosis}"
            )

        summary = "\n".join(summary_lines)

        return TrajectoryAnalysisResult(
            experiment_id=experiment_id,
            dataset_id=self.dataset_id,
            seed=self.seed,
            timestamp=datetime.now(timezone.utc).isoformat(),
            learning_rate=self.learning_rate,
            bounds=self.bounds,
            negative_bias_categories=trajectories,
            summary=summary,
        )

    def _determine_diagnosis(self, trajectory: NegativeBiasCategoryTrajectory, true_bias: float) -> str:
        """Determine which case (A, B, or C) the trajectory represents."""

        if not trajectory.trajectory_samples:
            return "INCONCLUSIVE"

        # Check if bias ever went negative
        min_reached = trajectory.minimum_bias_reached
        went_negative = min_reached < 0

        # Check if bias oscillated (multiple direction changes)
        direction_changes = 0
        for i in range(1, len(trajectory.trajectory_samples)):
            delta_prev = trajectory.trajectory_samples[i - 1].bias_update_delta
            delta_curr = trajectory.trajectory_samples[i].bias_update_delta
            if (delta_prev > 0 and delta_curr < 0) or (delta_prev < 0 and delta_curr > 0):
                direction_changes += 1

        oscillates = direction_changes >= 3

        # Check if final bias is still positive despite negative true bias
        stays_positive = trajectory.final_bias > 0.0 and true_bias < 0

        # Diagnose based on patterns
        if oscillates:
            return "C"  # Oscillation/instability
        elif went_negative:
            return "A"  # Parameter became negative (downstream problem)
        elif stays_positive:
            return "B"  # Parameter constrained positive (update constraint)
        else:
            return "AMBIGUOUS"


def run_research_negative_bias_trajectory_17_2_d(
    dataset: Optional[object] = None,
    seed: int = 42,
    learning_rate: float = 0.007,
    bounds: Optional[Dict[str, float]] = None,
    experiment_id: str = "research_negative_bias_trajectory_17_2_d",
) -> TrajectoryAnalysisResult:
    """Convenience wrapper for 17.2D trajectory analysis."""
    analyzer = ResearchNegativeBiasTrajectory17_2_D(
        dataset=dataset,
        seed=seed,
        learning_rate=learning_rate,
        bounds=bounds,
    )
    return analyzer.run(experiment_id=experiment_id)
