"""Tests for 17.2D Negative-Bias Trajectory Analysis."""

import pytest
from backend.experiments.research_negative_bias_trajectory_17_2_d import (
    BiasTrajectorySample,
    NegativeBiasCategoryTrajectory,
    TrajectoryAnalysisResult,
    ResearchNegativeBiasTrajectory17_2_D,
    run_research_negative_bias_trajectory_17_2_d,
)


class TestBiasTrajectorySample:
    """Tests for individual trajectory sample model."""

    def test_sample_creation(self):
        """Can create a valid trajectory sample."""
        sample = BiasTrajectorySample(
            step=0,
            experience_id="exp_000",
            predicted_state_value=50.0,
            actual_state_value=55.0,
            signed_error=5.0,
            expected_state_bias_before=0.0,
            expected_state_bias_after=0.05,
            bias_update_delta=0.05,
            calibration_confidence=0.8,
        )
        assert sample.step == 0
        assert sample.signed_error == 5.0
        assert sample.bias_update_delta == 0.05


class TestNegativeBiasCategoryTrajectory:
    """Tests for category trajectory model."""

    def test_trajectory_creation(self):
        """Can create a valid category trajectory."""
        traj = NegativeBiasCategoryTrajectory(
            category="high_skill_practice",
            true_systematic_bias=-3.0,
            initial_bias=0.0,
            final_bias=-0.5,
            minimum_bias_reached=-0.8,
            maximum_bias_reached=0.2,
            total_signed_update=-0.5,
            num_negative_error_signals=8,
            num_positive_error_signals=2,
        )
        assert traj.category == "high_skill_practice"
        assert traj.true_systematic_bias == -3.0
        assert traj.final_bias == -0.5

    def test_trajectory_with_samples(self):
        """Can add samples to trajectory."""
        traj = NegativeBiasCategoryTrajectory(
            category="high_motivation",
            true_systematic_bias=-4.0,
            initial_bias=0.0,
            final_bias=0.0,
            minimum_bias_reached=0.0,
            maximum_bias_reached=0.0,
            total_signed_update=0.0,
            num_negative_error_signals=0,
            num_positive_error_signals=0,
        )
        sample = BiasTrajectorySample(
            step=0,
            experience_id="exp_001",
            predicted_state_value=50.0,
            actual_state_value=55.0,
            signed_error=5.0,
            expected_state_bias_before=0.0,
            expected_state_bias_after=0.02,
            bias_update_delta=0.02,
            calibration_confidence=0.7,
        )
        traj.trajectory_samples.append(sample)
        assert len(traj.trajectory_samples) == 1


class TestTrajectoryAnalysisResult:
    """Tests for complete analysis result."""

    def test_result_creation(self):
        """Can create a valid analysis result."""
        result = TrajectoryAnalysisResult(
            experiment_id="test",
            dataset_id="test_dataset",
            seed=42,
            timestamp="2026-08-13T00:00:00",
            learning_rate=0.007,
            bounds={"state_adjustment_max": 0.12},
        )
        assert result.seed == 42
        assert result.learning_rate == 0.007
        assert result.negative_bias_categories == {}


class TestResearchNegativeBiasTrajectory17_2_D:
    """Tests for trajectory analyzer."""

    def test_analyzer_initialization_default(self):
        """Can initialize with default parameters."""
        analyzer = ResearchNegativeBiasTrajectory17_2_D(seed=42)
        assert analyzer.seed == 42
        assert analyzer.learning_rate == 0.007
        assert analyzer.dataset_id is not None

    def test_analyzer_initialization_custom(self):
        """Can initialize with custom parameters."""
        analyzer = ResearchNegativeBiasTrajectory17_2_D(
            seed=123,
            learning_rate=0.01,
        )
        assert analyzer.seed == 123
        assert analyzer.learning_rate == 0.01

    def test_negative_bias_categories_defined(self):
        """Analyzer has negative-bias categories defined."""
        analyzer = ResearchNegativeBiasTrajectory17_2_D(seed=42)
        assert "high_skill_practice" in analyzer.NEGATIVE_BIAS_CATEGORIES
        assert "high_motivation" in analyzer.NEGATIVE_BIAS_CATEGORIES

    def test_run_produces_valid_result(self):
        """Running analyzer produces valid trajectory result."""
        analyzer = ResearchNegativeBiasTrajectory17_2_D(seed=42)
        result = analyzer.run()
        assert isinstance(result, TrajectoryAnalysisResult)
        assert result.seed == 42
        assert result.dataset_id is not None

    def test_result_includes_negative_bias_categories(self):
        """Result includes trajectories for negative-bias categories."""
        analyzer = ResearchNegativeBiasTrajectory17_2_D(seed=42)
        result = analyzer.run()
        # At least one negative-bias category should appear in training data
        assert len(result.negative_bias_categories) > 0

    def test_trajectory_has_diagnosis(self):
        """Each category trajectory has a diagnosis."""
        analyzer = ResearchNegativeBiasTrajectory17_2_D(seed=42)
        result = analyzer.run()
        for category, trajectory in result.negative_bias_categories.items():
            assert trajectory.diagnosis in ["A", "B", "C", "INCONCLUSIVE", "AMBIGUOUS", "PENDING"]

    def test_results_are_deterministic(self):
        """Same seed produces identical results."""
        result1 = run_research_negative_bias_trajectory_17_2_d(seed=42)
        result2 = run_research_negative_bias_trajectory_17_2_d(seed=42)
        
        # Check structure matches
        assert set(result1.negative_bias_categories.keys()) == set(result2.negative_bias_categories.keys())
        
        # Check key metrics match
        for cat in result1.negative_bias_categories:
            assert (
                result1.negative_bias_categories[cat].final_bias
                == result2.negative_bias_categories[cat].final_bias
            )

    def test_trajectory_samples_recorded(self):
        """Trajectory samples are recorded for negative-bias categories."""
        analyzer = ResearchNegativeBiasTrajectory17_2_D(seed=42)
        result = analyzer.run()
        for category, trajectory in result.negative_bias_categories.items():
            # At least some samples should be recorded
            assert len(trajectory.trajectory_samples) > 0

    def test_summary_generated(self):
        """Analysis produces a summary."""
        analyzer = ResearchNegativeBiasTrajectory17_2_D(seed=42)
        result = analyzer.run()
        assert len(result.summary) > 0
        assert "high_skill_practice" in result.summary or "high_motivation" in result.summary


class TestConvenienceFunction:
    """Tests for convenience wrapper."""

    def test_run_function_produces_result(self):
        """Convenience function produces valid trajectory result."""
        result = run_research_negative_bias_trajectory_17_2_d(seed=42)
        assert isinstance(result, TrajectoryAnalysisResult)
        assert result.seed == 42
