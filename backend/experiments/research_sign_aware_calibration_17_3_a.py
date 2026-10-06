"""Research experiment 17.3A: Sign-Aware Calibration Fix

This experiment implements the minimal fix for asymmetric learning:
- Add signed_state_errors to PredictionErrorResult
- Create sign-aware calibrator that uses directional information
- Compare both calibrators on the same benchmark

Changes made:
1. PredictionErrorResult now includes signed_state_errors (actual - predicted)
2. PredictionErrorEvaluator computes both absolute and signed errors
3. SignAwareCalibratorVariant uses signed errors for directional updates

Everything else unchanged:
- Learning rate (0.007)
- Benchmark and dataset (same as 17.2)
- Evaluation metrics (MAE, direction accuracy)
- Held-out validation split (80/20)

Research Question:
Does restoring error-sign information eliminate the asymmetric learning failure
(where negative-bias categories cannot learn corrections) without destroying the
prediction improvement established in 17.1?
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass

from pydantic import BaseModel, Field

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.services.sign_aware_calibrator import SignAwareCalibratorVariant
from backend.services.digital_twin_calibrator import DigitalTwinCalibrator
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator
from backend.services.simulation_engine import SimulationEngine
from backend.services.transition_engine import TransitionEngine
from backend.models.prediction_error_result import PredictionErrorResult


class CalibrationComparisonResult(BaseModel):
    """Results for one calibrator variant (existing or sign-aware)."""

    variant_name: str
    held_out_mae: float
    baseline_mae: float
    mae_improvement: float
    direction_accuracy: float
    category_accuracies: Dict[str, float]
    per_sample_errors: List[float] = Field(default_factory=list)
    final_expected_state_bias: Dict[str, float] = Field(default_factory=dict)


class ResearchSignAwareCalibration17_3_AResult(BaseModel):
    """Complete comparison: existing vs sign-aware calibration."""

    experiment_id: str = "research_sign_aware_calibration_17_3_a"
    dataset_id: str
    seed: int
    timestamp: str
    learning_rate: float
    bounds: Dict[str, float]
    
    existing_calibrator_result: CalibrationComparisonResult
    sign_aware_calibrator_result: CalibrationComparisonResult
    
    summary: str = ""
    
    def model_dump(self, **kwargs):
        """Override to handle dataclass conversion."""
        data = super().model_dump(**kwargs)
        return data


@dataclass
class _FeatureVector:
    """Internal helper for tracking feature values."""
    skill_practice_type: str
    skill_level: str
    motivation: str
    project_type: str


class ResearchSignAwareCalibration17_3_A:
    """Experiment: Compare existing vs sign-aware calibration on same benchmark."""

    def __init__(self, seed: int = 42, learning_rate: float = 0.007):
        self.seed = seed
        self.learning_rate = learning_rate
        self.benchmark_generator = ResearchBenchmarkGenerator(seed=seed)
        self.evaluator = PredictionErrorEvaluator()
        self.existing_calibrator = DigitalTwinCalibrator()
        self.sign_aware_calibrator = SignAwareCalibratorVariant()
        self.simulation_engine = SimulationEngine()
        self.dataset_id = f"research_benchmark_v1_seed_{seed}"
        self.bounds = {
            "state_adjustment_max": 0.12,
            "probability_bias_max": 0.012,
            "risk_bias_max": 0.012,
            "uncertainty_increment_max": 0.012,
            "confidence_increment_max": 0.012,
        }

    def run(self) -> ResearchSignAwareCalibration17_3_AResult:
        """Execute comparison: existing vs sign-aware calibration."""
        dataset = self.benchmark_generator.generate_dataset(training_size=80, held_out_size=20)
        train_experiences = dataset.training_experiences
        held_out_experiences = dataset.held_out_experiences

        # Compute baseline (uncalibrated) errors
        baseline_params = CalibrationParameters()
        baseline_errors = self._compute_held_out_errors(
            held_out_experiences, baseline_params
        )
        baseline_mae = sum(baseline_errors) / len(baseline_errors) if baseline_errors else 0.0

        # Test existing calibrator
        existing_params = self._train_calibrator(
            train_experiences, baseline_params, self.existing_calibrator
        )
        existing_errors = self._compute_held_out_errors(
            held_out_experiences, existing_params
        )
        existing_mae = sum(existing_errors) / len(existing_errors) if existing_errors else 0.0
        existing_accuracy = self._compute_direction_accuracy(
            held_out_experiences, existing_params
        )
        existing_category_accuracy = self._compute_category_accuracy(
            held_out_experiences, existing_params
        )

        # Test sign-aware calibrator
        sign_aware_params = self._train_calibrator(
            train_experiences, baseline_params, self.sign_aware_calibrator
        )
        sign_aware_errors = self._compute_held_out_errors(
            held_out_experiences, sign_aware_params
        )
        sign_aware_mae = sum(sign_aware_errors) / len(sign_aware_errors) if sign_aware_errors else 0.0
        sign_aware_accuracy = self._compute_direction_accuracy(
            held_out_experiences, sign_aware_params
        )
        sign_aware_category_accuracy = self._compute_category_accuracy(
            held_out_experiences, sign_aware_params
        )

        # Build result
        result = ResearchSignAwareCalibration17_3_AResult(
            dataset_id=self.dataset_id,
            seed=self.seed,
            timestamp=datetime.now(timezone.utc).isoformat(),
            learning_rate=self.learning_rate,
            bounds=self.bounds,
            existing_calibrator_result=CalibrationComparisonResult(
                variant_name="existing_magnitude_only",
                held_out_mae=round(existing_mae, 4),
                baseline_mae=round(baseline_mae, 4),
                mae_improvement=round(baseline_mae - existing_mae, 4),
                direction_accuracy=round(existing_accuracy, 4),
                category_accuracies=existing_category_accuracy,
                per_sample_errors=existing_errors,
                final_expected_state_bias=existing_params.expected_state_bias,
            ),
            sign_aware_calibrator_result=CalibrationComparisonResult(
                variant_name="sign_aware_directional",
                held_out_mae=round(sign_aware_mae, 4),
                baseline_mae=round(baseline_mae, 4),
                mae_improvement=round(baseline_mae - sign_aware_mae, 4),
                direction_accuracy=round(sign_aware_accuracy, 4),
                category_accuracies=sign_aware_category_accuracy,
                per_sample_errors=sign_aware_errors,
                final_expected_state_bias=sign_aware_params.expected_state_bias,
            ),
        )

        # Generate summary
        result.summary = self._generate_summary(result)
        return result

    def _train_calibrator(
        self,
        experiences,
        initial_params: CalibrationParameters,
        calibrator,
    ) -> CalibrationParameters:
        """Train calibrator on experiences."""
        params = CalibrationParameters(**initial_params.model_dump())
        transition_engine = TransitionEngine()
        
        for experience in experiences:
            # Simulate prediction with current parameters
            sim = SimulationEngine(
                transition_engine=transition_engine,
                calibration_parameters=params,
            )
            predicted = sim.simulate_action(experience.initial_state, experience.selected_action)
            
            # Create decision outcome with all required fields
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
            
            # Evaluate error
            error_result = self.evaluator.evaluate(decision)
            
            # Calibrate
            calibration = calibrator.calibrate(
                error_result, params, self.learning_rate, self.bounds
            )
            params = calibration.updated_parameters
        
        return params

    def _compute_held_out_errors(
        self, experiences, params: CalibrationParameters
    ) -> List[float]:
        """Compute MAE on held-out experiences."""
        errors = []
        transition_engine = TransitionEngine()
        
        for experience in experiences:
            # Simulate with calibrated parameters
            sim = SimulationEngine(
                transition_engine=transition_engine,
                calibration_parameters=params,
            )
            predicted = sim.simulate_action(experience.initial_state, experience.selected_action)
            predicted_state = predicted["predicted_future_state"]
            actual_state = experience.actual_future_state
            
            # Compute errors
            for key in set(predicted_state.keys()) | set(actual_state.keys()):
                pred = float(predicted_state.get(key, 0.0) or 0.0)
                true = float(actual_state.get(key, 0.0) or 0.0)
                error = abs(pred - true)
                errors.append(error)
        
        return errors

    def _compute_direction_accuracy(
        self, experiences, params: CalibrationParameters
    ) -> float:
        """Compute accuracy of bias direction learned."""
        correct = 0
        total = 0
        
        for experience in experiences:
            actual = experience.actual_future_state or {}
            predicted_raw = experience.initial_state or {}
            
            for key in set(predicted_raw.keys()) | set(actual.keys()):
                pred_val = float(predicted_raw.get(key, 0.0) or 0.0)
                actual_val = float(actual.get(key, 0.0) or 0.0)
                bias = params.expected_state_bias.get(key, 0.0)
                
                if actual_val > pred_val and bias > 0:  # Underestimate, positive bias
                    correct += 1
                elif actual_val < pred_val and bias < 0:  # Overestimate, negative bias
                    correct += 1
                
                total += 1
        
        return correct / total if total > 0 else 0.0

    def _compute_category_accuracy(
        self, experiences, params: CalibrationParameters
    ) -> Dict[str, float]:
        """Compute direction accuracy per category."""
        category_stats: Dict[str, List[bool]] = {}
        
        for experience in experiences:
            category = experience.category if hasattr(experience, 'category') else "unknown"
            if category not in category_stats:
                category_stats[category] = []
            
            actual = experience.actual_future_state or {}
            predicted_raw = experience.initial_state or {}
            
            for key in set(predicted_raw.keys()) | set(actual.keys()):
                pred_val = float(predicted_raw.get(key, 0.0) or 0.0)
                actual_val = float(actual.get(key, 0.0) or 0.0)
                bias = params.expected_state_bias.get(key, 0.0)
                
                is_correct = (
                    (actual_val > pred_val and bias > 0) or
                    (actual_val < pred_val and bias < 0)
                )
                category_stats[category].append(is_correct)
        
        result = {}
        for cat, decisions in category_stats.items():
            accuracy = sum(decisions) / len(decisions) if decisions else 0.0
            result[cat] = round(accuracy, 4)
        
        return result

    def _generate_summary(
        self, result: ResearchSignAwareCalibration17_3_AResult
    ) -> str:
        """Generate human-readable summary."""
        lines = [
            "=== Sign-Aware Calibration Fix (17.3A) ===",
            "",
            "Baseline MAE (no calibration):",
            f"  {result.existing_calibrator_result.baseline_mae}",
            "",
            "Existing Calibrator (magnitude-only):",
            f"  Held-out MAE: {result.existing_calibrator_result.held_out_mae}",
            f"  Improvement: {result.existing_calibrator_result.mae_improvement}",
            f"  Direction Accuracy: {result.existing_calibrator_result.direction_accuracy}",
            "",
            "Sign-Aware Calibrator (directional):",
            f"  Held-out MAE: {result.sign_aware_calibrator_result.held_out_mae}",
            f"  Improvement: {result.sign_aware_calibrator_result.mae_improvement}",
            f"  Direction Accuracy: {result.sign_aware_calibrator_result.direction_accuracy}",
            "",
            "Comparison:",
            f"  MAE Gain: {result.sign_aware_calibrator_result.mae_improvement - result.existing_calibrator_result.mae_improvement:.4f}",
            f"  Accuracy Gain: {result.sign_aware_calibrator_result.direction_accuracy - result.existing_calibrator_result.direction_accuracy:.4f}",
        ]
        
        # Add per-category comparison for critical categories
        for cat in ["high_skill_practice", "high_motivation"]:
            existing_acc = result.existing_calibrator_result.category_accuracies.get(cat, 0.0)
            sign_aware_acc = result.sign_aware_calibrator_result.category_accuracies.get(cat, 0.0)
            if existing_acc is not None or sign_aware_acc is not None:
                lines.append(f"\nCategory: {cat}")
                lines.append(f"  Existing: {existing_acc}")
                lines.append(f"  Sign-Aware: {sign_aware_acc}")
        
        return "\n".join(lines)


def run_research_sign_aware_calibration_17_3_a(seed: int = 42) -> ResearchSignAwareCalibration17_3_AResult:
    """Convenience function to run 17.3A experiment."""
    experiment = ResearchSignAwareCalibration17_3_A(seed=seed)
    return experiment.run()
