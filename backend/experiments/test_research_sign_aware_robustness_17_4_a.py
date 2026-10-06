"""Tests for 17.4A Multi-Seed Robustness Validation."""

import pytest
from backend.experiments.research_sign_aware_robustness_17_4_a import (
    SeedComparisonResult,
    RobustnessStatistics,
    ResearchSignAwareRobustness17_4_AResult,
    ResearchSignAwareRobustness17_4_A,
    run_research_sign_aware_robustness_17_4_a,
)


class TestSeedComparisonResult:
    """Tests for individual seed comparison results."""

    def test_creation(self):
        """Can create seed comparison result."""
        result = SeedComparisonResult(
            seed=42,
            baseline_mae=5.7875,
            original_mae=5.4125,
            sign_aware_mae=5.3125,
            original_improvement=0.375,
            sign_aware_improvement=0.475,
            original_direction_accuracy=0.75,
            sign_aware_direction_accuracy=0.75,
            original_negative_bias_accuracy=0.6,
            sign_aware_negative_bias_accuracy=0.6,
            sign_aware_wins=True,
        )
        assert result.seed == 42
        assert result.sign_aware_wins is True
        assert result.sign_aware_improvement > result.original_improvement

    def test_sign_aware_wins_logic(self):
        """Win logic is correct."""
        result_win = SeedComparisonResult(
            seed=42,
            baseline_mae=5.7875,
            original_mae=5.5,
            sign_aware_mae=5.4,
            original_improvement=0.2875,
            sign_aware_improvement=0.3875,
            original_direction_accuracy=0.75,
            sign_aware_direction_accuracy=0.75,
            original_negative_bias_accuracy=0.6,
            sign_aware_negative_bias_accuracy=0.6,
            sign_aware_wins=True,
        )
        assert result_win.sign_aware_wins is True

        result_loss = SeedComparisonResult(
            seed=42,
            baseline_mae=5.7875,
            original_mae=5.4,
            sign_aware_mae=5.5,
            original_improvement=0.3875,
            sign_aware_improvement=0.2875,
            original_direction_accuracy=0.75,
            sign_aware_direction_accuracy=0.75,
            original_negative_bias_accuracy=0.6,
            sign_aware_negative_bias_accuracy=0.6,
            sign_aware_wins=False,
        )
        assert result_loss.sign_aware_wins is False


class TestRobustnessStatistics:
    """Tests for aggregate robustness statistics."""

    def test_creation(self):
        """Can create statistics."""
        stats = RobustnessStatistics(
            mean_original_improvement=0.375,
            mean_sign_aware_improvement=0.40,
            mean_improvement_delta=0.025,
            median_improvement_delta=0.02,
            min_improvement_delta=-0.01,
            max_improvement_delta=0.05,
            std_dev_improvement_delta=0.025,
            sign_aware_win_count=4,
            sign_aware_win_rate=0.8,
            all_seeds_no_regression=True,
        )
        assert stats.sign_aware_win_count == 4
        assert stats.sign_aware_win_rate == 0.8


class TestResearchSignAwareRobustness17_4_AResult:
    """Tests for complete robustness result."""

    def test_creation_defaults(self):
        """Can create result with defaults."""
        result = ResearchSignAwareRobustness17_4_AResult()
        assert result.seeds == [42, 123, 456, 789, 999]
        assert result.seed_results == {}
        assert result.timestamp != ""

    def test_to_dict_serializable(self):
        """Result can be converted to dict for JSON."""
        result = ResearchSignAwareRobustness17_4_AResult()
        result.seed_results = {
            42: SeedComparisonResult(
                seed=42,
                baseline_mae=5.7875,
                original_mae=5.4125,
                sign_aware_mae=5.3125,
                original_improvement=0.375,
                sign_aware_improvement=0.475,
                original_direction_accuracy=0.75,
                sign_aware_direction_accuracy=0.75,
                original_negative_bias_accuracy=0.6,
                sign_aware_negative_bias_accuracy=0.6,
                sign_aware_wins=True,
            )
        }
        result.statistics = RobustnessStatistics(
            mean_original_improvement=0.375,
            mean_sign_aware_improvement=0.40,
            mean_improvement_delta=0.025,
            median_improvement_delta=0.02,
            min_improvement_delta=-0.01,
            max_improvement_delta=0.05,
            std_dev_improvement_delta=0.025,
            sign_aware_win_count=1,
            sign_aware_win_rate=1.0,
            all_seeds_no_regression=True,
        )

        result_dict = result.to_dict()
        assert result_dict["experiment_name"] == "17.4A: Multi-Seed Sign-Aware Calibration Robustness"
        assert "42" in result_dict["seed_results"]
        assert result_dict["statistics"]["sign_aware_win_rate"] == 1.0


class TestResearchSignAwareRobustness17_4_A:
    """Tests for robustness experiment."""

    def test_initialization(self):
        """Can initialize experiment."""
        experiment = ResearchSignAwareRobustness17_4_A()
        assert experiment.seeds == [42, 123, 456, 789, 999]

    def test_custom_seeds(self):
        """Can specify custom seeds."""
        custom_seeds = [42, 100]
        experiment = ResearchSignAwareRobustness17_4_A(seeds=custom_seeds)
        assert experiment.seeds == custom_seeds

    def test_std_dev_calculation(self):
        """Standard deviation calculated correctly."""
        experiment = ResearchSignAwareRobustness17_4_A()
        values = [1.0, 2.0, 3.0]
        std_dev = experiment._std_dev(values)
        # For [1, 2, 3]: mean=2, var=((1-2)^2 + (2-2)^2 + (3-2)^2)/3 = 2/3
        # std_dev = sqrt(2/3) ≈ 0.816
        assert 0.81 < std_dev < 0.82

    def test_std_dev_empty(self):
        """Standard deviation of empty list is 0."""
        experiment = ResearchSignAwareRobustness17_4_A()
        assert experiment._std_dev([]) == 0.0

    def test_category_subset_accuracy(self):
        """Can compute accuracy for category subset."""
        experiment = ResearchSignAwareRobustness17_4_A()
        category_accuracies = {
            "high_skill_practice": 0.5,
            "high_motivation": 0.7,
            "low_skill_practice": 0.8,
            "medium_skill_practice": 0.9,
        }
        target = {"high_skill_practice", "high_motivation"}
        
        result = experiment._compute_category_subset_accuracy(
            category_accuracies, target
        )
        assert result == 0.6  # (0.5 + 0.7) / 2


class TestConvenienceFunction:
    """Tests for convenience function."""

    def test_convenience_function_returns_result(self):
        """Convenience function returns result object."""
        # Test with subset of seeds for speed
        result = run_research_sign_aware_robustness_17_4_a(seeds=[42])
        assert isinstance(result, ResearchSignAwareRobustness17_4_AResult)
        assert 42 in result.seed_results
