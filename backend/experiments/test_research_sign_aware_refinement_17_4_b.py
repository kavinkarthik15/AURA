"""Tests for 17.4B Sign-Aware Learning Rate Refinement."""

import pytest
from backend.experiments.research_sign_aware_refinement_17_4_b import (
    LearningRateSeedResult,
    LearningRateComparisonResult,
    ResearchSignAwareRefinement17_4_BResult,
    ResearchSignAwareRefinement17_4_B,
)


class TestLearningRateSeedResult:
    """Tests for individual seed result."""

    def test_creation(self):
        """Can create seed result."""
        result = LearningRateSeedResult(
            learning_rate=0.005,
            seed=42,
            baseline_mae=5.7875,
            original_mae=5.4125,
            sign_aware_mae=5.3125,
            sign_aware_wins=True,
            original_improvement=0.375,
            sign_aware_improvement=0.475,
            improvement_delta=0.1,
            original_direction_accuracy=0.75,
            sign_aware_direction_accuracy=0.75,
            direction_accuracy_delta=0.0,
            original_negative_bias_accuracy=0.5,
            sign_aware_negative_bias_accuracy=0.5,
            max_bias_change=0.5,
            any_bias_sign_flip=False,
        )
        assert result.learning_rate == 0.005
        assert result.improvement_delta == 0.1


class TestLearningRateComparisonResult:
    """Tests for aggregated learning rate result."""

    def test_creation(self):
        """Can create comparison result."""
        seed_results = [
            LearningRateSeedResult(
                learning_rate=0.005,
                seed=42,
                baseline_mae=5.7875,
                original_mae=5.4125,
                sign_aware_mae=5.3125,
                sign_aware_wins=True,
                original_improvement=0.375,
                sign_aware_improvement=0.475,
                improvement_delta=0.1,
                original_direction_accuracy=0.75,
                sign_aware_direction_accuracy=0.75,
                direction_accuracy_delta=0.0,
                original_negative_bias_accuracy=0.5,
                sign_aware_negative_bias_accuracy=0.5,
                max_bias_change=0.5,
                any_bias_sign_flip=False,
            )
        ]

        result = LearningRateComparisonResult(
            learning_rate=0.005,
            seed_results=seed_results,
            mean_improvement_delta=0.1,
            std_improvement_delta=0.0,
            win_count=1,
            win_rate=1.0,
            seeds_with_degradation=0,
            seeds_with_severe_dir_acc_loss=0,
            max_direction_accuracy_loss=0.0,
            meets_robustness_criterion=True,
        )
        assert result.learning_rate == 0.005
        assert result.meets_robustness_criterion is True

    def test_robustness_criterion(self):
        """Robustness criterion correctly evaluated."""
        # Criterion: win_count >= 4 and degradation == 0
        robust = LearningRateComparisonResult(
            learning_rate=0.005,
            seed_results=[],
            mean_improvement_delta=0.0,
            std_improvement_delta=0.0,
            win_count=4,
            win_rate=0.8,
            seeds_with_degradation=0,
            seeds_with_severe_dir_acc_loss=0,
            max_direction_accuracy_loss=0.0,
            meets_robustness_criterion=True,
        )
        assert robust.meets_robustness_criterion is True

        not_robust = LearningRateComparisonResult(
            learning_rate=0.005,
            seed_results=[],
            mean_improvement_delta=0.0,
            std_improvement_delta=0.0,
            win_count=3,
            win_rate=0.6,
            seeds_with_degradation=0,
            seeds_with_severe_dir_acc_loss=0,
            max_direction_accuracy_loss=0.0,
            meets_robustness_criterion=False,
        )
        assert not_robust.meets_robustness_criterion is False


class TestResearchSignAwareRefinement17_4_BResult:
    """Tests for complete refinement result."""

    def test_creation_defaults(self):
        """Can create with defaults."""
        result = ResearchSignAwareRefinement17_4_BResult()
        assert result.seeds == [42, 123, 456, 789, 999]
        assert result.learning_rates == [0.007, 0.005, 0.003, 0.002, 0.001]
        assert result.timestamp != ""

    def test_custom_seeds_and_rates(self):
        """Can create with custom seeds and rates."""
        custom_seeds = [42, 100]
        custom_rates = [0.005, 0.003]
        result = ResearchSignAwareRefinement17_4_BResult(
            seeds=custom_seeds, learning_rates=custom_rates
        )
        assert result.seeds == custom_seeds
        assert result.learning_rates == custom_rates

    def test_to_dict_serializable(self):
        """Can serialize to dict."""
        result = ResearchSignAwareRefinement17_4_BResult()
        result_dict = result.to_dict()
        assert "experiment_name" in result_dict
        assert "learning_rates" in result_dict
        assert "recommended_learning_rate" in result_dict


class TestResearchSignAwareRefinement17_4_B:
    """Tests for refinement experiment."""

    def test_initialization(self):
        """Can initialize experiment."""
        experiment = ResearchSignAwareRefinement17_4_B()
        assert experiment.seeds == [42, 123, 456, 789, 999]
        assert experiment.learning_rates == [0.007, 0.005, 0.003, 0.002, 0.001]

    def test_std_dev_calculation(self):
        """Standard deviation calculated correctly."""
        experiment = ResearchSignAwareRefinement17_4_B()
        values = [1.0, 2.0, 3.0]
        std_dev = experiment._std_dev(values)
        assert 0.81 < std_dev < 0.82

    def test_category_subset_accuracy(self):
        """Can compute category subset accuracy."""
        experiment = ResearchSignAwareRefinement17_4_B()
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

    def test_custom_parameters(self):
        """Can initialize with custom parameters."""
        custom_seeds = [42, 123]
        custom_rates = [0.005, 0.003, 0.001]
        experiment = ResearchSignAwareRefinement17_4_B(
            seeds=custom_seeds, learning_rates=custom_rates
        )
        assert experiment.seeds == custom_seeds
        assert experiment.learning_rates == custom_rates
