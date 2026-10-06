"""
Tests for 17.1B Ablation Robustness

Validates the multi-seed robustness test implementation.
"""

import unittest
from backend.experiments.research_ablation_17_1_b import (
    run_research_ablation_17_1_b,
    RobustnessResult17_1_B,
    SeedAblationResult,
)


class TestSeedAblationResult(unittest.TestCase):
    """Test SeedAblationResult model."""

    def test_seed_result_structure(self):
        """Verify seed result has all required fields."""
        result = SeedAblationResult(
            seed=42,
            condition_a_mae=5.7875,
            condition_b_mae=5.4125,
            improvement_percent=6.48,
            learning_wins=True,
        )
        self.assertEqual(result.seed, 42)
        self.assertTrue(result.learning_wins)


class TestRobustnessResult17_1_B(unittest.TestCase):
    """Test RobustnessResult17_1_B model."""

    def test_robustness_result_structure(self):
        """Verify robustness result has all required fields."""
        seed_results = [
            SeedAblationResult(
                seed=42,
                condition_a_mae=5.7875,
                condition_b_mae=5.4125,
                improvement_percent=6.48,
                learning_wins=True,
            ),
            SeedAblationResult(
                seed=123,
                condition_a_mae=6.0,
                condition_b_mae=5.5,
                improvement_percent=8.33,
                learning_wins=True,
            ),
        ]
        result = RobustnessResult17_1_B(
            total_seeds=2,
            seed_results=seed_results,
            learning_wins_count=2,
            learning_win_rate=100.0,
            average_improvement=7.405,
            median_improvement=7.405,
            min_improvement=6.48,
            max_improvement=8.33,
            std_dev_improvement=0.925,
        )
        self.assertEqual(result.total_seeds, 2)
        self.assertEqual(result.learning_wins_count, 2)

    def test_success_when_learning_wins_majority(self):
        """Success if learning wins on >= 80% of seeds."""
        seed_results = [
            SeedAblationResult(
                seed=42,
                condition_a_mae=5.7875,
                condition_b_mae=5.4125,
                improvement_percent=6.48,
                learning_wins=True,
            ),
            SeedAblationResult(
                seed=123,
                condition_a_mae=6.0,
                condition_b_mae=5.5,
                improvement_percent=8.33,
                learning_wins=True,
            ),
            SeedAblationResult(
                seed=456,
                condition_a_mae=5.9,
                condition_b_mae=5.3,
                improvement_percent=10.17,
                learning_wins=True,
            ),
            SeedAblationResult(
                seed=789,
                condition_a_mae=5.8,
                condition_b_mae=5.2,
                improvement_percent=10.34,
                learning_wins=True,
            ),
            SeedAblationResult(
                seed=999,
                condition_a_mae=6.1,
                condition_b_mae=5.6,
                improvement_percent=8.20,
                learning_wins=True,
            ),
        ]
        result = RobustnessResult17_1_B(
            total_seeds=5,
            seed_results=seed_results,
            learning_wins_count=5,
            learning_win_rate=100.0,
            average_improvement=8.704,
            median_improvement=8.33,
            min_improvement=6.48,
            max_improvement=10.34,
            std_dev_improvement=1.604,
        )
        self.assertTrue(result.success())

    def test_failure_when_learning_loses_majority(self):
        """Fail if learning wins on < 80% of seeds."""
        seed_results = [
            SeedAblationResult(
                seed=42,
                condition_a_mae=5.7875,
                condition_b_mae=5.4125,
                improvement_percent=6.48,
                learning_wins=True,
            ),
            SeedAblationResult(
                seed=123,
                condition_a_mae=5.5,
                condition_b_mae=6.0,
                improvement_percent=-9.09,
                learning_wins=False,
            ),
            SeedAblationResult(
                seed=456,
                condition_a_mae=5.9,
                condition_b_mae=6.2,
                improvement_percent=-5.08,
                learning_wins=False,
            ),
            SeedAblationResult(
                seed=789,
                condition_a_mae=5.8,
                condition_b_mae=5.2,
                improvement_percent=10.34,
                learning_wins=True,
            ),
            SeedAblationResult(
                seed=999,
                condition_a_mae=6.1,
                condition_b_mae=6.5,
                improvement_percent=-6.56,
                learning_wins=False,
            ),
        ]
        result = RobustnessResult17_1_B(
            total_seeds=5,
            seed_results=seed_results,
            learning_wins_count=2,
            learning_win_rate=40.0,
            average_improvement=1.218,
            median_improvement=-5.08,
            min_improvement=-9.09,
            max_improvement=10.34,
            std_dev_improvement=8.254,
        )
        self.assertFalse(result.success())


class TestRunResearchAblation17_1_B(unittest.TestCase):
    """Test the multi-seed robustness function."""

    def test_robustness_runs_successfully(self):
        """Robustness test should execute and return valid results."""
        result = run_research_ablation_17_1_b(seeds=[42, 123])
        self.assertIsInstance(result, RobustnessResult17_1_B)
        self.assertEqual(result.total_seeds, 2)
        self.assertEqual(len(result.seed_results), 2)

    def test_robustness_calculates_statistics(self):
        """Statistics should be calculated correctly."""
        result = run_research_ablation_17_1_b(seeds=[42, 123])
        
        # Verify all statistics are present
        self.assertIsNotNone(result.average_improvement)
        self.assertIsNotNone(result.median_improvement)
        self.assertIsNotNone(result.min_improvement)
        self.assertIsNotNone(result.max_improvement)
        self.assertIsNotNone(result.std_dev_improvement)
        self.assertIsNotNone(result.learning_win_rate)

    def test_robustness_with_default_seeds(self):
        """Should work with default seed list."""
        result = run_research_ablation_17_1_b()
        self.assertEqual(result.total_seeds, 5)
        self.assertEqual(len(result.seed_results), 5)

    def test_robustness_improvement_statistics_coherent(self):
        """Min/max/median improvements should be coherent."""
        result = run_research_ablation_17_1_b(seeds=[42, 123, 456])
        
        improvements = [r.improvement_percent for r in result.seed_results]
        
        # Min should be minimum of all improvements
        self.assertAlmostEqual(result.min_improvement, min(improvements), places=2)
        
        # Max should be maximum of all improvements
        self.assertAlmostEqual(result.max_improvement, max(improvements), places=2)
        
        # Average should match mean
        import statistics
        expected_mean = statistics.mean(improvements)
        self.assertAlmostEqual(result.average_improvement, expected_mean, places=2)

    def test_learning_win_rate_calculation(self):
        """Win rate should be calculated correctly."""
        result = run_research_ablation_17_1_b(seeds=[42, 123])
        
        wins = sum(1 for r in result.seed_results if r.learning_wins)
        expected_rate = 100.0 * wins / len(result.seed_results)
        
        self.assertAlmostEqual(result.learning_win_rate, expected_rate, places=1)


if __name__ == "__main__":
    unittest.main()
