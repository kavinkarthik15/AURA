"""Tests for 17.2C Sign-Aware Calibration Comparison."""

import pytest
from backend.experiments.research_sign_aware_calibration_17_2_c import (
    CalibrationUpdateHelper,
    CalibrationUpdateMetrics,
    SignAwareBiasComparisonResult,
    SignAwareCalibratedConditionResult,
    SignAwareCalibratedComparison,
    ResearchSignAwareCalibration17_2_C,
    run_research_sign_aware_calibration_17_2_c,
)


class TestCalibrationUpdateHelper:
    """Tests for calibration update helper functions."""

    def test_magnitude_only_update_positive_error(self):
        """Magnitude-only: positive error produces positive adjustment."""
        result = CalibrationUpdateHelper.magnitude_only_update(
            current_bias=0.0,
            absolute_error=2.0,
            learning_rate=0.1,
            max_delta=1.0,
        )
        assert result > 0.0

    def test_magnitude_only_update_bounded(self):
        """Magnitude-only: respects max_delta bound."""
        result = CalibrationUpdateHelper.magnitude_only_update(
            current_bias=0.0,
            absolute_error=100.0,
            learning_rate=0.5,
            max_delta=0.05,
        )
        assert abs(result) <= 0.05

    def test_sign_aware_update_underestimation(self):
        """Sign-aware: negative signed error (underestimation) produces positive adjustment."""
        result = CalibrationUpdateHelper.sign_aware_update(
            current_bias=0.0,
            signed_error=-2.0,  # Negative: pred < actual (underestimation)
            learning_rate=0.1,
            max_delta=1.0,
        )
        assert result > 0.0  # We should increase bias to match actual

    def test_sign_aware_update_overestimation(self):
        """Sign-aware: positive signed error (overestimation) produces negative adjustment."""
        result = CalibrationUpdateHelper.sign_aware_update(
            current_bias=0.0,
            signed_error=2.0,  # Positive: pred > actual (overestimation)
            learning_rate=0.1,
            max_delta=1.0,
        )
        assert result < 0.0  # We should decrease bias to match actual

    def test_sign_aware_update_bounded(self):
        """Sign-aware: respects max_delta bound."""
        result = CalibrationUpdateHelper.sign_aware_update(
            current_bias=0.0,
            signed_error=-100.0,
            learning_rate=0.5,
            max_delta=0.05,
        )
        assert abs(result) <= 0.05


class TestSignAwareCalibratedConditionResult:
    """Tests for condition result model."""

    def test_condition_result_creation(self):
        """Can create a valid condition result."""
        result = SignAwareCalibratedConditionResult(
            calibration_method="magnitude_only",
            held_out_mae=5.4,
            mae_reduction=0.3875,
            overall_direction_accuracy=70.0,
            underestimation_accuracy=80.0,
            overestimation_accuracy=50.0,
            convergence_rate=15.0,
            training_mae=5.5,
        )
        assert result.calibration_method == "magnitude_only"
        assert result.held_out_mae == 5.4
        assert result.overall_direction_accuracy == 70.0


class TestSignAwareCalibratedComparison:
    """Tests for full comparison result."""

    def test_comparison_creation(self):
        """Can create a valid comparison result."""
        current = SignAwareCalibratedConditionResult(
            calibration_method="magnitude_only",
            held_out_mae=5.4,
            mae_reduction=0.3875,
            overall_direction_accuracy=70.0,
            underestimation_accuracy=80.0,
            overestimation_accuracy=50.0,
            convergence_rate=15.0,
            training_mae=5.5,
        )
        sign_aware = SignAwareCalibratedConditionResult(
            calibration_method="sign_aware",
            held_out_mae=5.3,
            mae_reduction=0.4875,
            overall_direction_accuracy=85.0,
            underestimation_accuracy=90.0,
            overestimation_accuracy=75.0,
            convergence_rate=20.0,
            training_mae=5.4,
        )
        comparison = SignAwareCalibratedComparison(
            experiment_id="test",
            dataset_id="test_dataset",
            seed=42,
            timestamp="2026-08-13T00:00:00",
            baseline_held_out_mae=5.7875,
            current_method=current,
            sign_aware_method=sign_aware,
        )
        assert comparison.seed == 42
        assert comparison.current_method.calibration_method == "magnitude_only"
        assert comparison.sign_aware_method.calibration_method == "sign_aware"


class TestResearchSignAwareCalibration17_2_C:
    """Tests for the comparison experiment."""

    def test_analyzer_initialization_default(self):
        """Can initialize with default parameters."""
        analyzer = ResearchSignAwareCalibration17_2_C(seed=42)
        assert analyzer.seed == 42
        assert analyzer.learning_rate == 0.007
        assert analyzer.dataset_id is not None

    def test_analyzer_initialization_custom(self):
        """Can initialize with custom parameters."""
        analyzer = ResearchSignAwareCalibration17_2_C(
            seed=123,
            learning_rate=0.01,
        )
        assert analyzer.seed == 123
        assert analyzer.learning_rate == 0.01

    def test_magnitude_only_run_completes(self):
        """Magnitude-only variant runs without error."""
        analyzer = ResearchSignAwareCalibration17_2_C(seed=42)
        result, trajectory = analyzer._run_with_update_rule("magnitude_only", "Current")
        assert result.calibration_method == "magnitude_only"
        assert result.held_out_mae > 0
        assert len(trajectory) == 80

    def test_sign_aware_run_completes(self):
        """Sign-aware variant runs without error."""
        analyzer = ResearchSignAwareCalibration17_2_C(seed=42)
        result, trajectory = analyzer._run_with_update_rule("sign_aware", "Sign-Aware")
        assert result.calibration_method == "sign_aware"
        assert result.held_out_mae > 0
        assert len(trajectory) == 80

    def test_full_comparison_returns_valid_result(self):
        """Running full comparison produces valid result."""
        analyzer = ResearchSignAwareCalibration17_2_C(seed=42)
        result = analyzer.run()
        assert isinstance(result, SignAwareCalibratedComparison)
        assert result.seed == 42
        assert result.baseline_held_out_mae > 0
        assert result.current_method.held_out_mae > 0
        assert result.sign_aware_method.held_out_mae > 0

    def test_both_methods_improve_over_baseline(self):
        """Both calibration methods should improve over baseline."""
        analyzer = ResearchSignAwareCalibration17_2_C(seed=42)
        result = analyzer.run()
        assert result.current_method.held_out_mae < result.baseline_held_out_mae
        assert result.sign_aware_method.held_out_mae < result.baseline_held_out_mae

    def test_direction_accuracy_is_measured(self):
        """Both methods report direction-learning accuracy."""
        analyzer = ResearchSignAwareCalibration17_2_C(seed=42)
        result = analyzer.run()
        assert result.current_method.overall_direction_accuracy > 0
        assert result.sign_aware_method.overall_direction_accuracy > 0

    def test_overestimation_accuracy_is_measured(self):
        """Both methods report overestimation accuracy."""
        analyzer = ResearchSignAwareCalibration17_2_C(seed=42)
        result = analyzer.run()
        assert result.current_method.overestimation_accuracy >= 0
        assert result.sign_aware_method.overestimation_accuracy >= 0

    def test_results_are_deterministic(self):
        """Same seed produces identical results."""
        result1 = run_research_sign_aware_calibration_17_2_c(seed=42)
        result2 = run_research_sign_aware_calibration_17_2_c(seed=42)
        assert result1.current_method.held_out_mae == result2.current_method.held_out_mae
        assert result1.sign_aware_method.held_out_mae == result2.sign_aware_method.held_out_mae


class TestConvenienceFunction:
    """Tests for the convenience wrapper."""

    def test_run_function_produces_result(self):
        """Convenience function produces valid comparison."""
        result = run_research_sign_aware_calibration_17_2_c(seed=42)
        assert isinstance(result, SignAwareCalibratedComparison)
        assert result.seed == 42
        assert result.current_method.calibration_method == "magnitude_only"
        assert result.sign_aware_method.calibration_method == "sign_aware"
