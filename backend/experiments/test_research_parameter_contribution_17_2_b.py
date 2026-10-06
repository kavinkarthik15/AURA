"""Tests for 17.2B parameter contribution decomposition."""

from backend.experiments.research_parameter_contribution_17_2_b import (
    ParameterConditionResult,
    ParameterContributionAnalysis,
    run_research_parameter_contribution_17_2_b,
)


class TestParameterConditionResult:
    def test_condition_result_creation(self):
        result = ParameterConditionResult(
            condition_name="full_calibration",
            condition_description="Full calibrated model",
            held_out_mae=5.4,
            mae_reduction=0.9,
            direction_learning_accuracy=70.0,
            contribution_to_full_model=1.0,
            overestimation_failure_present=False,
        )
        assert result.condition_name == "full_calibration"
        assert result.held_out_mae == 5.4
        assert result.overestimation_failure_present is False


class TestParameterContributionAnalysis:
    def test_run_returns_required_conditions(self):
        result = run_research_parameter_contribution_17_2_b(seed=42)
        assert result.seed == 42
        assert "full_calibration" in result.condition_results
        assert "expected_state_bias_only" in result.condition_results
        assert "uncertainty_only" in result.condition_results
        assert "confidence_only" in result.condition_results
        assert "risk_bias_only" in result.condition_results
        assert "transition_probability_bias_only" in result.condition_results
        assert "full_minus_expected_state_bias" in result.condition_results
        assert "full_minus_uncertainty" in result.condition_results
        assert "full_minus_confidence" in result.condition_results
        assert "full_minus_risk_bias" in result.condition_results
        assert "full_minus_transition_probability_bias" in result.condition_results

    def test_full_model_is_referenced(self):
        result = run_research_parameter_contribution_17_2_b(seed=42)
        assert result.full_model_reference_name == "full_calibration"
        assert result.condition_results["full_calibration"].held_out_mae > 0

    def test_all_conditions_have_valid_mae(self):
        result = run_research_parameter_contribution_17_2_b(seed=42)
        for name, condition in result.condition_results.items():
            assert condition.held_out_mae > 0
            assert condition.mae_reduction >= 0
            assert 0.0 <= condition.direction_learning_accuracy <= 100.0
            assert 0.0 <= condition.contribution_to_full_model <= 1.5

    def test_results_are_deterministic(self):
        result1 = run_research_parameter_contribution_17_2_b(seed=42)
        result2 = run_research_parameter_contribution_17_2_b(seed=42)
        assert result1.seed == result2.seed
        for name in result1.condition_results:
            assert result1.condition_results[name].held_out_mae == result2.condition_results[name].held_out_mae
