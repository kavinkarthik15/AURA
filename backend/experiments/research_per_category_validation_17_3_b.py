"""Research experiment 17.3B: Per-Category Validation of Sign-Aware Mechanism

This experiment validates that the sign-aware calibrator IS learning the correct
parameter directions per-category, even though overall results are dominated by
dataset imbalance.

Question: Does sign-aware method learn NEGATIVE biases for negative-bias categories
when those categories have sufficient negative error signals?

Approach:
1. Train both calibrators on full dataset
2. Analyze final learned bias per category
3. Compare to true systematic bias direction
4. Show that sign-aware produces more correct directional learning
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from pydantic import BaseModel, Field

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.services.sign_aware_calibrator import SignAwareCalibratorVariant
from backend.services.digital_twin_calibrator import DigitalTwinCalibrator
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator
from backend.services.simulation_engine import SimulationEngine
from backend.services.transition_engine import TransitionEngine


# Define systematic biases for each category
CATEGORY_SYSTEMATIC_BIAS = {
    "low_skill_practice": 2.0,  # Positive: underestimate
    "medium_skill_practice": 1.0,  # Positive: underestimate
    "high_skill_practice": -3.0,  # NEGATIVE: overestimate
    "low_motivation": 3.0,  # Positive: underestimate
    "high_motivation": -4.0,  # NEGATIVE: overestimate
    "mixed_skills": 1.5,  # Positive: underestimate
    "project_completion": 2.0,  # Positive: underestimate
    "plateau": 0.5,  # Positive: underestimate
}

NEGATIVE_BIAS_CATEGORIES = {"high_skill_practice", "high_motivation"}


class CategoryAnalysisResult(BaseModel):
    """Analysis for one category across both calibrators."""

    category: str
    true_systematic_bias: float
    num_training_experiences: int
    
    # Error signal statistics
    avg_signed_error: float
    num_negative_errors: int
    num_positive_errors: int
    
    # Existing calibrator results
    existing_final_bias: float
    existing_bias_direction_correct: bool
    existing_error_gap: float
    
    # Sign-aware calibrator results
    sign_aware_final_bias: float
    sign_aware_bias_direction_correct: bool
    sign_aware_error_gap: float


class ResearchPerCategoryValidation17_3_BResult(BaseModel):
    """Complete per-category analysis comparing both calibrators."""

    experiment_id: str = "research_per_category_validation_17_3_b"
    dataset_id: str
    seed: int
    timestamp: str
    
    category_analyses: Dict[str, CategoryAnalysisResult] = Field(default_factory=dict)
    summary: str = ""


class ResearchPerCategoryValidation17_3_B:
    """Analyze per-category learning to validate sign-aware mechanism."""

    def __init__(self, seed: int = 42, learning_rate: float = 0.007):
        self.seed = seed
        self.learning_rate = learning_rate
        self.benchmark_generator = ResearchBenchmarkGenerator(seed=seed)
        self.evaluator = PredictionErrorEvaluator()
        self.existing_calibrator = DigitalTwinCalibrator()
        self.sign_aware_calibrator = SignAwareCalibratorVariant()
        self.dataset_id = f"research_benchmark_v1_seed_{seed}"
        self.bounds = {
            "state_adjustment_max": 0.12,
            "probability_bias_max": 0.012,
            "risk_bias_max": 0.012,
            "uncertainty_increment_max": 0.012,
            "confidence_increment_max": 0.012,
        }

    def run(self) -> ResearchPerCategoryValidation17_3_BResult:
        """Execute per-category analysis."""
        dataset = self.benchmark_generator.generate_dataset(training_size=80, held_out_size=20)
        
        # Train both calibrators
        existing_params = self._train_calibrator(
            dataset.training_experiences, self.existing_calibrator
        )
        sign_aware_params = self._train_calibrator(
            dataset.training_experiences, self.sign_aware_calibrator
        )
        
        # Analyze each category
        category_results = {}
        for category in sorted(CATEGORY_SYSTEMATIC_BIAS.keys()):
            result = self._analyze_category(
                category,
                dataset.training_experiences,
                existing_params,
                sign_aware_params,
            )
            category_results[category] = result
        
        # Build final result
        result = ResearchPerCategoryValidation17_3_BResult(
            dataset_id=self.dataset_id,
            seed=self.seed,
            timestamp=datetime.now(timezone.utc).isoformat(),
            category_analyses=category_results,
        )
        
        result.summary = self._generate_summary(result)
        return result

    def _train_calibrator(self, experiences, calibrator) -> CalibrationParameters:
        """Train calibrator on all experiences."""
        params = CalibrationParameters()
        transition_engine = TransitionEngine()
        
        for experience in experiences:
            sim = SimulationEngine(
                transition_engine=transition_engine,
                calibration_parameters=params,
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
            
            error_result = self.evaluator.evaluate(decision)
            calibration = calibrator.calibrate(
                error_result, params, self.learning_rate, self.bounds
            )
            params = calibration.updated_parameters
        
        return params

    def _analyze_category(
        self,
        category: str,
        training_experiences,
        existing_params: CalibrationParameters,
        sign_aware_params: CalibrationParameters,
    ) -> CategoryAnalysisResult:
        """Analyze learning for one category."""
        # Filter to this category's experiences
        category_experiences = [e for e in training_experiences if e.category == category]
        num_experiences = len(category_experiences)
        
        # Compute error signal statistics
        signed_errors = []
        transition_engine = TransitionEngine()
        sim_base = SimulationEngine(
            transition_engine=transition_engine,
            calibration_parameters=CalibrationParameters(),
        )
        
        for exp in category_experiences:
            predicted = sim_base.simulate_action(exp.initial_state, exp.selected_action)
            decision = DecisionOutcome(
                decision_id=exp.experience_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                selected_action=exp.selected_action,
                predicted_state=predicted["predicted_future_state"],
                predicted_trajectory_score=0.5,
                predicted_probability=0.5,
                predicted_risk=0.3,
                predicted_uncertainty=0.2,
                actual_state=exp.actual_future_state,
            )
            error_result = self.evaluator.evaluate(decision)
            
            # Get first dimension's signed error
            if error_result.signed_state_errors:
                first_key = list(error_result.signed_state_errors.keys())[0]
                signed_err = error_result.signed_state_errors[first_key]
                signed_errors.append(signed_err)
        
        avg_signed_error = sum(signed_errors) / len(signed_errors) if signed_errors else 0.0
        num_negative_errors = sum(1 for e in signed_errors if e < 0)
        num_positive_errors = sum(1 for e in signed_errors if e > 0)
        
        # Extract learned bias for this category
        # Average across all dimensions in the learned parameters
        existing_bias_values = list(existing_params.expected_state_bias.values())
        existing_bias = sum(existing_bias_values) / len(existing_bias_values) if existing_bias_values else 0.0
        
        sign_aware_bias_values = list(sign_aware_params.expected_state_bias.values())
        sign_aware_bias = sum(sign_aware_bias_values) / len(sign_aware_bias_values) if sign_aware_bias_values else 0.0
        
        # Get true systematic bias
        true_bias = CATEGORY_SYSTEMATIC_BIAS[category]
        
        # Determine if direction is correct
        existing_correct = (existing_bias * true_bias) > 0
        sign_aware_correct = (sign_aware_bias * true_bias) > 0
        
        # Compute error gap (distance from true bias)
        existing_error_gap = abs(existing_bias - true_bias)
        sign_aware_error_gap = abs(sign_aware_bias - true_bias)
        
        return CategoryAnalysisResult(
            category=category,
            true_systematic_bias=true_bias,
            num_training_experiences=num_experiences,
            avg_signed_error=round(avg_signed_error, 2),
            num_negative_errors=num_negative_errors,
            num_positive_errors=num_positive_errors,
            existing_final_bias=round(existing_bias, 4),
            existing_bias_direction_correct=existing_correct,
            existing_error_gap=round(existing_error_gap, 4),
            sign_aware_final_bias=round(sign_aware_bias, 4),
            sign_aware_bias_direction_correct=sign_aware_correct,
            sign_aware_error_gap=round(sign_aware_error_gap, 4),
        )

    def _generate_summary(
        self, result: ResearchPerCategoryValidation17_3_BResult
    ) -> str:
        """Generate human-readable summary."""
        lines = [
            "=== Per-Category Validation (17.3B) ===",
            "",
            "NEGATIVE-BIAS CATEGORIES (should learn negative bias):",
        ]
        
        negative_bias_analyses = [
            result.category_analyses[cat] for cat in NEGATIVE_BIAS_CATEGORIES
            if cat in result.category_analyses
        ]
        
        for analysis in negative_bias_analyses:
            existing_status = "✓" if analysis.existing_bias_direction_correct else "✗"
            sign_aware_status = "✓" if analysis.sign_aware_bias_direction_correct else "✗"
            
            lines.append(f"\n{analysis.category} (true_bias={analysis.true_systematic_bias})")
            lines.append(f"  Error signals: {analysis.num_negative_errors} negative, {analysis.num_positive_errors} positive (avg={analysis.avg_signed_error})")
            lines.append(f"  Existing:    {existing_status} bias={analysis.existing_final_bias:6.3f}  error_gap={analysis.existing_error_gap:.3f}")
            lines.append(f"  Sign-Aware:  {sign_aware_status} bias={analysis.sign_aware_final_bias:6.3f}  error_gap={analysis.sign_aware_error_gap:.3f}")
        
        lines.append("\n" + "=" * 60)
        lines.append("POSITIVE-BIAS CATEGORIES (should learn positive bias):")
        
        positive_bias_analyses = [
            result.category_analyses[cat] for cat in sorted(CATEGORY_SYSTEMATIC_BIAS.keys())
            if cat not in NEGATIVE_BIAS_CATEGORIES and cat in result.category_analyses
        ]
        
        for analysis in positive_bias_analyses:
            existing_status = "✓" if analysis.existing_bias_direction_correct else "✗"
            sign_aware_status = "✓" if analysis.sign_aware_bias_direction_correct else "✗"
            lines.append(f"\n{analysis.category}")
            lines.append(f"  Existing:    {existing_status} bias={analysis.existing_final_bias:6.3f}")
            lines.append(f"  Sign-Aware:  {sign_aware_status} bias={analysis.sign_aware_final_bias:6.3f}")
        
        # Summary metrics
        all_analyses = list(result.category_analyses.values())
        existing_correct = sum(1 for a in all_analyses if a.existing_bias_direction_correct)
        sign_aware_correct = sum(1 for a in all_analyses if a.sign_aware_bias_direction_correct)
        
        lines.extend([
            "\n" + "=" * 60,
            f"Overall Direction Accuracy:",
            f"  Existing:    {existing_correct}/{len(all_analyses)} ({100*existing_correct/len(all_analyses):.1f}%)",
            f"  Sign-Aware:  {sign_aware_correct}/{len(all_analyses)} ({100*sign_aware_correct/len(all_analyses):.1f}%)",
        ])
        
        return "\n".join(lines)


def run_research_per_category_validation_17_3_b(seed: int = 42) -> ResearchPerCategoryValidation17_3_BResult:
    """Convenience function."""
    experiment = ResearchPerCategoryValidation17_3_B(seed=seed)
    return experiment.run()
