"""
17.2C Sign-Aware Calibration Update

Controlled comparison of two expected_state_bias update mechanisms:

1. Current (Magnitude-Only): Adjusts bias based only on absolute error magnitude
   - Always increases bias (cannot reverse direction)
   - Led to asymmetric learning in 17.2A (negative biases fail)

2. Sign-Aware: Adjusts bias based on signed error
   - Increases bias if prediction < actual (underestimation)
   - Decreases bias if prediction > actual (overestimation)
   - Should correct directional learning failures

Research Question:
    Does sign-aware calibration correct the overestimation failure
    while preserving (or improving) prediction accuracy?

Experimental Design:
    - Same benchmark, training/held-out split, seed
    - Same learning rate and bounds (except update rule)
    - Identical prediction engine and evaluation
    - Only treatment variable: calibration update rule
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, Optional

from pydantic import BaseModel, Field

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.models.prediction_error_result import PredictionErrorResult
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator
from backend.services.simulation_engine import SimulationEngine
from backend.services.transition_engine import TransitionEngine


class CalibrationUpdateMetrics(BaseModel):
    """Metrics tracking a single calibration rule during training."""

    step: int
    experience_id: str
    category: str
    prediction_error: float
    signed_error: float
    expected_state_bias_learned: Dict[str, float] = Field(default_factory=dict)
    cumulative_mae: float


class SignAwareBiasComparisonResult(BaseModel):
    """Comparison metrics between current and sign-aware updates for one category."""

    category: str
    true_systematic_bias: float
    current_learned_bias_avg: float
    current_bias_distance: float
    current_direction_correct: bool
    sign_aware_learned_bias_avg: float
    sign_aware_bias_distance: float
    sign_aware_direction_correct: bool
    current_training_mae: float
    sign_aware_training_mae: float


class SignAwareCalibratedConditionResult(BaseModel):
    """Results for one calibration rule variant."""

    calibration_method: str  # "magnitude_only" or "sign_aware"
    held_out_mae: float
    mae_reduction: float
    overall_direction_accuracy: float
    underestimation_accuracy: float
    overestimation_accuracy: float
    convergence_rate: float
    training_mae: float
    category_direction_accuracy: Dict[str, float] = Field(default_factory=dict)


class SignAwareCalibratedComparison(BaseModel):
    """Full 17.2C comparison between calibration methods."""

    experiment_id: str
    dataset_id: str
    seed: int
    timestamp: str
    baseline_held_out_mae: float
    current_method: SignAwareCalibratedConditionResult
    sign_aware_method: SignAwareCalibratedConditionResult
    category_comparisons: Dict[str, SignAwareBiasComparisonResult] = Field(default_factory=dict)
    summary: str = ""


class CalibrationUpdateHelper:
    """Helper functions for computing calibration updates."""

    @staticmethod
    def magnitude_only_update(
        current_bias: float,
        absolute_error: float,
        learning_rate: float,
        max_delta: float,
    ) -> float:
        """Current algorithm: adjust by error magnitude (always positive)."""
        delta = learning_rate * float(absolute_error)
        applied = max(-max_delta, min(max_delta, delta))
        return current_bias + applied

    @staticmethod
    def sign_aware_update(
        current_bias: float,
        signed_error: float,
        learning_rate: float,
        max_delta: float,
    ) -> float:
        """Sign-aware: adjust by negative signed error (correct direction).
        
        If predicted > actual (overestimation): signed_error > 0 → apply negative delta to reduce bias
        If predicted < actual (underestimation): signed_error < 0 → apply positive delta to increase bias
        """
        delta = learning_rate * float(-signed_error)  # Invert sign for correct adjustment
        applied = max(-max_delta, min(max_delta, delta))
        return current_bias + applied


class ResearchSignAwareCalibration17_2_C:
    """Compare magnitude-only vs sign-aware calibration updates."""

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

        self.evaluator = PredictionErrorEvaluator()
        self.transition_engine = TransitionEngine()

    def _compute_signed_error(self, predicted_state: Dict, actual_state: Dict) -> Dict[str, float]:
        """Compute per-skill signed error (negative = underestimated, positive = overestimated)."""
        signed_errors = {}
        all_keys = sorted(set(predicted_state.keys()) | set(actual_state.keys()))
        for key in all_keys:
            pred_val = float(predicted_state.get(key, 0.0))
            actual_val = float(actual_state.get(key, 0.0))
            signed_errors[key] = pred_val - actual_val  # Positive means over, negative means under
        return signed_errors

    def _run_with_update_rule(
        self,
        update_rule: str,
        condition_name: str,
    ) -> tuple[SignAwareCalibratedConditionResult, list[CalibrationUpdateMetrics]]:
        """
        Train calibration using either magnitude_only or sign_aware update rule.

        Returns:
            (ConditionResult, trajectory of metrics)
        """
        current_params = CalibrationParameters()
        training_maes = []
        trajectory = []
        category_direction_tracking: Dict[str, list[bool]] = {cat: [] for cat in self.CATEGORY_SYSTEMATIC_BIAS.keys()}

        for step_idx, experience in enumerate(self.dataset.training_experiences):
            sim = SimulationEngine(
                transition_engine=self.transition_engine,
                calibration_parameters=current_params,
            )
            predicted = sim.simulate_action(experience.initial_state, experience.selected_action)
            predicted_state = predicted["predicted_future_state"]
            actual_state = experience.actual_future_state

            # Evaluate prediction error
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
            mae = float(error_result.prediction_error or 0.0)
            training_maes.append(mae)

            # Compute signed errors for direction-aware updates
            signed_errors = self._compute_signed_error(predicted_state, actual_state)
            mean_signed_error = sum(abs(se) for se in signed_errors.values()) / len(signed_errors) if signed_errors else 0.0

            # Apply calibration update using selected rule
            updated_bias = {}
            max_delta = float(self.bounds.get("state_adjustment_max", 0.12))

            if update_rule == "magnitude_only":
                # Current: use absolute error magnitude
                for key, abs_err in error_result.state_errors.items():
                    new_bias = CalibrationUpdateHelper.magnitude_only_update(
                        current_params.expected_state_bias.get(key, 0.0),
                        abs_err,
                        self.learning_rate,
                        max_delta,
                    )
                    updated_bias[key] = round(new_bias, 4)
            else:  # sign_aware
                # Sign-aware: use signed error
                for key, signed_err in signed_errors.items():
                    new_bias = CalibrationUpdateHelper.sign_aware_update(
                        current_params.expected_state_bias.get(key, 0.0),
                        signed_err,
                        self.learning_rate,
                        max_delta,
                    )
                    updated_bias[key] = round(new_bias, 4)

            current_params.expected_state_bias = updated_bias

            # Track direction accuracy for this category
            true_bias = self.CATEGORY_SYSTEMATIC_BIAS[experience.category]
            learned_bias_avg = sum(updated_bias.values()) / len(updated_bias) if updated_bias else 0.0
            direction_correct = (learned_bias_avg * true_bias) >= 0
            category_direction_tracking[experience.category].append(direction_correct)

            # Record trajectory
            trajectory.append(
                CalibrationUpdateMetrics(
                    step=step_idx,
                    experience_id=experience.experience_id,
                    category=experience.category,
                    prediction_error=mae,
                    signed_error=mean_signed_error,
                    expected_state_bias_learned=dict(updated_bias),
                    cumulative_mae=round(sum(training_maes) / len(training_maes), 4),
                )
            )

        # Evaluate on held-out set
        held_out_mae = 0.0
        held_out_errors = []
        if self.dataset.held_out_experiences:
            for experience in self.dataset.held_out_experiences:
                sim = SimulationEngine(
                    transition_engine=self.transition_engine,
                    calibration_parameters=current_params,
                )
                predicted = sim.simulate_action(experience.initial_state, experience.selected_action)
                decision = DecisionOutcome(
                    decision_id=experience.experience_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    selected_action=experience.selected_action,
                    predicted_state=predicted["predicted_future_state"],
                    predicted_trajectory_score=0.5,
                    predicted_probability=0.5,
                    predicted_risk=0.3,
                    predicted_uncertainty=0.2,
                    actual_state=experience.actual_future_state,
                )
                err = self.evaluator.evaluate(decision)
                held_out_errors.append(float(err.prediction_error or 0.0))
            held_out_mae = round(sum(held_out_errors) / len(held_out_errors), 4) if held_out_errors else 0.0

        # Compute final metrics
        training_mae = round(sum(training_maes) / len(training_maes), 4) if training_maes else 0.0

        # Overall direction accuracy across all experiences
        all_direction_results = []
        for cat_results in category_direction_tracking.values():
            all_direction_results.extend(cat_results)
        overall_direction_accuracy = (
            round((sum(1 for x in all_direction_results if x) / len(all_direction_results)) * 100.0, 2)
            if all_direction_results
            else 0.0
        )

        # Underestimation vs overestimation accuracy
        underestimation_accuracy = 0.0
        overestimation_accuracy = 0.0
        if self.dataset.training_experiences:
            under_results = []
            over_results = []
            for experience in self.dataset.training_experiences:
                true_bias = self.CATEGORY_SYSTEMATIC_BIAS[experience.category]
                if true_bias < 0:  # Negative bias means overestimation
                    over_results.append(category_direction_tracking[experience.category][-1])
                elif true_bias > 0:  # Positive bias means underestimation
                    under_results.append(category_direction_tracking[experience.category][-1])

            if under_results:
                underestimation_accuracy = round((sum(1 for x in under_results if x) / len(under_results)) * 100.0, 2)
            if over_results:
                overestimation_accuracy = round((sum(1 for x in over_results if x) / len(over_results)) * 100.0, 2)

        # Convergence rate (how much did MAE decrease)
        initial_training_mae = training_maes[0] if training_maes else 0.0
        convergence_rate = (
            round(((initial_training_mae - training_mae) / initial_training_mae) * 100.0, 2)
            if initial_training_mae > 0
            else 0.0
        )

        # Per-category direction accuracy
        category_direction_accuracy = {
            cat: round((sum(1 for x in results if x) / len(results)) * 100.0, 2) if results else 0.0
            for cat, results in category_direction_tracking.items()
        }

        result = SignAwareCalibratedConditionResult(
            calibration_method=update_rule,
            held_out_mae=held_out_mae,
            mae_reduction=round(5.7875 - held_out_mae, 4),  # Baseline from 17.2B
            overall_direction_accuracy=overall_direction_accuracy,
            underestimation_accuracy=underestimation_accuracy,
            overestimation_accuracy=overestimation_accuracy,
            convergence_rate=convergence_rate,
            training_mae=training_mae,
            category_direction_accuracy=category_direction_accuracy,
        )

        return result, trajectory

    def run(self, experiment_id: str = "research_sign_aware_calibration_17_2_c") -> SignAwareCalibratedComparison:
        """Run full sign-aware calibration comparison."""

        # Baseline (no calibration)
        baseline_errors = []
        for exp in self.dataset.held_out_experiences:
            sim = SimulationEngine(transition_engine=self.transition_engine, calibration_parameters=None)
            pred = sim.simulate_action(exp.initial_state, exp.selected_action)
            decision = DecisionOutcome(
                decision_id=exp.experience_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                selected_action=exp.selected_action,
                predicted_state=pred["predicted_future_state"],
                predicted_trajectory_score=0.5,
                predicted_probability=0.5,
                predicted_risk=0.3,
                predicted_uncertainty=0.2,
                actual_state=exp.actual_future_state,
            )
            err = self.evaluator.evaluate(decision)
            baseline_errors.append(float(err.prediction_error or 0.0))
        baseline_held_out_mae = round(sum(baseline_errors) / len(baseline_errors), 4) if baseline_errors else 0.0

        # Current (magnitude-only) method
        current_result, current_trajectory = self._run_with_update_rule("magnitude_only", "Current (Magnitude-Only)")

        # Sign-aware method
        sign_aware_result, sign_aware_trajectory = self._run_with_update_rule("sign_aware", "Sign-Aware")

        # Category-level comparison
        category_comparisons: Dict[str, SignAwareBiasComparisonResult] = {}
        for category in self.CATEGORY_SYSTEMATIC_BIAS:
            true_bias = self.CATEGORY_SYSTEMATIC_BIAS[category]
            current_learned = (
                sum(current_result.category_direction_accuracy.get(category, 0.0) for _ in [1]) / 1.0
                if category in current_result.category_direction_accuracy
                else 0.0
            )
            sign_aware_learned = (
                sum(sign_aware_result.category_direction_accuracy.get(category, 0.0) for _ in [1]) / 1.0
                if category in sign_aware_result.category_direction_accuracy
                else 0.0
            )

            category_comparisons[category] = SignAwareBiasComparisonResult(
                category=category,
                true_systematic_bias=float(true_bias),
                current_learned_bias_avg=0.0,
                current_bias_distance=0.0,
                current_direction_correct=current_learned > 50.0,
                sign_aware_learned_bias_avg=0.0,
                sign_aware_bias_distance=0.0,
                sign_aware_direction_correct=sign_aware_learned > 50.0,
                current_training_mae=current_result.training_mae,
                sign_aware_training_mae=sign_aware_result.training_mae,
            )

        summary = (
            f"Current method achieves {current_result.held_out_mae:.4f} MAE with {current_result.overall_direction_accuracy:.1f}% direction accuracy. "
            f"Sign-aware method achieves {sign_aware_result.held_out_mae:.4f} MAE with {sign_aware_result.overall_direction_accuracy:.1f}% direction accuracy. "
            f"Overestimation correction: current={current_result.overestimation_accuracy:.1f}%, sign-aware={sign_aware_result.overestimation_accuracy:.1f}%. "
        )

        return SignAwareCalibratedComparison(
            experiment_id=experiment_id,
            dataset_id=self.dataset_id,
            seed=self.seed,
            timestamp=datetime.now(timezone.utc).isoformat(),
            baseline_held_out_mae=baseline_held_out_mae,
            current_method=current_result,
            sign_aware_method=sign_aware_result,
            category_comparisons=category_comparisons,
            summary=summary,
        )


def run_research_sign_aware_calibration_17_2_c(
    dataset: Optional[object] = None,
    seed: int = 42,
    learning_rate: float = 0.007,
    bounds: Optional[Dict[str, float]] = None,
    experiment_id: str = "research_sign_aware_calibration_17_2_c",
) -> SignAwareCalibratedComparison:
    """Convenience wrapper for 17.2C sign-aware calibration comparison."""
    analyzer = ResearchSignAwareCalibration17_2_C(
        dataset=dataset,
        seed=seed,
        learning_rate=learning_rate,
        bounds=bounds,
    )
    return analyzer.run(experiment_id=experiment_id)
