"""Tests for 17.3A Sign-Aware Calibration Fix."""

import pytest
from datetime import datetime, timezone
from backend.experiments.research_sign_aware_calibration_17_3_a import (
    CalibrationComparisonResult,
    ResearchSignAwareCalibration17_3_AResult,
    ResearchSignAwareCalibration17_3_A,
    run_research_sign_aware_calibration_17_3_a,
)
from backend.models.prediction_error_result import PredictionErrorResult
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator
from backend.models.decision_outcome import DecisionOutcome


class TestPredictionErrorResultSignedErrors:
    """Tests for signed error computation in PredictionErrorResult."""

    def test_signed_errors_created_by_evaluator(self):
        """Evaluator creates signed_state_errors in addition to state_errors."""
        evaluator = PredictionErrorEvaluator()
        outcome = DecisionOutcome(
            decision_id="test_001",
            timestamp=datetime.now(timezone.utc).isoformat(),
            selected_action="test_action",
            predicted_state={"skill": 50.0},
            predicted_trajectory_score=0.5,
            predicted_probability=0.5,
            predicted_risk=0.3,
            predicted_uncertainty=0.2,
            actual_state={"skill": 55.0},
        )
        result = evaluator.evaluate(outcome)
        
        # Should have both absolute and signed errors
        assert "skill" in result.state_errors
        assert "skill" in result.signed_state_errors
        assert result.state_errors["skill"] == 5.0  # |55 - 50| = 5
        assert result.signed_state_errors["skill"] == 5.0  # 55 - 50 = 5

    def test_signed_errors_preserve_direction(self):
        """Signed errors distinguish overestimate from underestimate."""
        evaluator = PredictionErrorEvaluator()
        
        # Underestimate case
        underestimate = DecisionOutcome(
            decision_id="under",
            timestamp=datetime.now(timezone.utc).isoformat(),
            selected_action="test_action",
            predicted_state={"x": 30.0},
            predicted_trajectory_score=0.5,
            predicted_probability=0.5,
            predicted_risk=0.3,
            predicted_uncertainty=0.2,
            actual_state={"x": 40.0},
        )
        result_under = evaluator.evaluate(underestimate)
        assert result_under.state_errors["x"] == 10.0
        assert result_under.signed_state_errors["x"] == 10.0
        
        # Overestimate case
        overestimate = DecisionOutcome(
            decision_id="over",
            timestamp=datetime.now(timezone.utc).isoformat(),
            selected_action="test_action",
            predicted_state={"x": 40.0},
            predicted_trajectory_score=0.5,
            predicted_probability=0.5,
            predicted_risk=0.3,
            predicted_uncertainty=0.2,
            actual_state={"x": 30.0},
        )
        result_over = evaluator.evaluate(overestimate)
        assert result_over.state_errors["x"] == 10.0
        assert result_over.signed_state_errors["x"] == -10.0  # Negative!

    def test_signed_errors_can_be_negative(self):
        """signed_state_errors field accepts negative values."""
        result = PredictionErrorResult(
            decision_id="test",
            prediction_error=5.0,
            state_errors={"x": 5.0},
            signed_state_errors={"x": -5.0},  # Should be allowed
            actual_available=True,
        )
        assert result.signed_state_errors["x"] == -5.0


class TestCalibrationComparisonResult:
    """Tests for comparison result model."""

    def test_result_creation(self):
        """Can create valid comparison result."""
        result = CalibrationComparisonResult(
            variant_name="test_variant",
            held_out_mae=5.0,
            baseline_mae=6.0,
            mae_improvement=1.0,
            direction_accuracy=0.75,
            category_accuracies={"test": 0.8},
        )
        assert result.variant_name == "test_variant"
        assert result.mae_improvement == 1.0


class TestResearchSignAwareCalibration17_3_A:
    """Tests for sign-aware calibration experiment."""

    def test_experiment_initialization(self):
        """Can initialize experiment."""
        experiment = ResearchSignAwareCalibration17_3_A(seed=42)
        assert experiment.seed == 42
        assert experiment.learning_rate == 0.007

    def test_experiment_initialization_custom(self):
        """Can initialize with custom parameters."""
        experiment = ResearchSignAwareCalibration17_3_A(seed=123, learning_rate=0.01)
        assert experiment.seed == 123
        assert experiment.learning_rate == 0.01

    def test_run_produces_valid_result(self):
        """Running experiment produces valid result."""
        experiment = ResearchSignAwareCalibration17_3_A(seed=42)
        result = experiment.run()
        
        assert isinstance(result, ResearchSignAwareCalibration17_3_AResult)
        assert result.seed == 42
        assert result.existing_calibrator_result is not None
        assert result.sign_aware_calibrator_result is not None

    def test_result_has_both_variants(self):
        """Result includes both existing and sign-aware variants."""
        experiment = ResearchSignAwareCalibration17_3_A(seed=42)
        result = experiment.run()
        
        assert result.existing_calibrator_result.variant_name == "existing_magnitude_only"
        assert result.sign_aware_calibrator_result.variant_name == "sign_aware_directional"

    def test_existing_variant_has_metrics(self):
        """Existing variant result includes all metrics."""
        experiment = ResearchSignAwareCalibration17_3_A(seed=42)
        result = experiment.run()
        
        existing = result.existing_calibrator_result
        assert existing.held_out_mae > 0
        assert existing.baseline_mae > 0
        assert existing.mae_improvement is not None
        assert existing.direction_accuracy >= 0 and existing.direction_accuracy <= 1

    def test_sign_aware_variant_has_metrics(self):
        """Sign-aware variant result includes all metrics."""
        experiment = ResearchSignAwareCalibration17_3_A(seed=42)
        result = experiment.run()
        
        sign_aware = result.sign_aware_calibrator_result
        assert sign_aware.held_out_mae > 0
        assert sign_aware.baseline_mae > 0
        assert sign_aware.mae_improvement is not None
        assert sign_aware.direction_accuracy >= 0 and sign_aware.direction_accuracy <= 1

    def test_baseline_mae_is_same_for_both(self):
        """Both variants evaluate against the same baseline."""
        experiment = ResearchSignAwareCalibration17_3_A(seed=42)
        result = experiment.run()
        
        assert (
            result.existing_calibrator_result.baseline_mae
            == result.sign_aware_calibrator_result.baseline_mae
        )

    def test_results_are_deterministic(self):
        """Same seed produces identical results."""
        result1 = run_research_sign_aware_calibration_17_3_a(seed=42)
        result2 = run_research_sign_aware_calibration_17_3_a(seed=42)
        
        # Check key metrics match
        assert (
            result1.existing_calibrator_result.held_out_mae
            == result2.existing_calibrator_result.held_out_mae
        )
        assert (
            result1.sign_aware_calibrator_result.held_out_mae
            == result2.sign_aware_calibrator_result.held_out_mae
        )

    def test_summary_generated(self):
        """Result includes human-readable summary."""
        experiment = ResearchSignAwareCalibration17_3_A(seed=42)
        result = experiment.run()
        
        assert len(result.summary) > 0
        assert "Sign-Aware" in result.summary
        assert "Existing" in result.summary

    def test_category_accuracies_computed(self):
        """Per-category accuracy computed for each variant."""
        experiment = ResearchSignAwareCalibration17_3_A(seed=42)
        result = experiment.run()
        
        existing_cats = result.existing_calibrator_result.category_accuracies
        sign_aware_cats = result.sign_aware_calibrator_result.category_accuracies
        
        # Should have categories
        assert len(existing_cats) > 0
        assert len(sign_aware_cats) > 0
        
        # All values should be in [0, 1]
        for acc in existing_cats.values():
            assert 0 <= acc <= 1
        for acc in sign_aware_cats.values():
            assert 0 <= acc <= 1

    def test_final_expected_state_bias_recorded(self):
        """Final expected_state_bias values recorded for analysis."""
        experiment = ResearchSignAwareCalibration17_3_A(seed=42)
        result = experiment.run()
        
        existing_bias = result.existing_calibrator_result.final_expected_state_bias
        sign_aware_bias = result.sign_aware_calibrator_result.final_expected_state_bias
        
        # Should have biases for dimensions
        assert len(existing_bias) > 0
        assert len(sign_aware_bias) > 0


class TestConvenienceFunction:
    """Tests for convenience wrapper."""

    def test_run_function_produces_result(self):
        """Convenience function produces valid result."""
        result = run_research_sign_aware_calibration_17_3_a(seed=42)
        assert isinstance(result, ResearchSignAwareCalibration17_3_AResult)
        assert result.seed == 42
