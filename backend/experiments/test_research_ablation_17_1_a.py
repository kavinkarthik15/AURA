"""
Tests for 17.1A Ablation Study

Validates that the ablation study correctly compares Condition A (Baseline)
vs Condition B (Learning) and measures calibration effectiveness.
"""

import unittest
from backend.experiments.research_ablation_17_1_a import (
    ResearchAblation17_1_A,
    AblationConditionResult,
    AblationResult17_1_A,
    run_research_ablation_17_1_a,
)
from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator


class TestAblationConditionResult(unittest.TestCase):
    """Test AblationConditionResult model."""

    def test_condition_result_fields(self):
        """Verify all required fields exist and validate correctly."""
        result = AblationConditionResult(
            condition_name="Baseline",
            condition_description="No calibration",
            held_out_mae=5.5,
            training_mae=5.4,
        )
        self.assertEqual(result.condition_name, "Baseline")
        self.assertEqual(result.held_out_mae, 5.5)


class TestAblationResult17_1_A(unittest.TestCase):
    """Test AblationResult17_1_A model."""

    def test_result_structure(self):
        """Verify result contains all required fields."""
        cond_a = AblationConditionResult(
            condition_name="Baseline",
            condition_description="No calibration",
            held_out_mae=6.0,
            training_mae=6.0,
        )
        cond_b = AblationConditionResult(
            condition_name="Learning",
            condition_description="With calibration",
            held_out_mae=5.4,
            training_mae=5.8,
        )
        result = AblationResult17_1_A(
            dataset_id="test_dataset",
            seed=42,
            condition_a=cond_a,
            condition_b=cond_b,
            absolute_improvement=0.6,
            improvement_percent=10.0,
        )
        self.assertEqual(result.condition_a.held_out_mae, 6.0)
        self.assertEqual(result.condition_b.held_out_mae, 5.4)
        self.assertEqual(result.absolute_improvement, 0.6)

    def test_success_when_learning_better(self):
        """Success if learning MAE < baseline MAE."""
        cond_a = AblationConditionResult(
            condition_name="Baseline",
            condition_description="No calibration",
            held_out_mae=6.0,
            training_mae=6.0,
        )
        cond_b = AblationConditionResult(
            condition_name="Learning",
            condition_description="With calibration",
            held_out_mae=5.4,
            training_mae=5.8,
        )
        result = AblationResult17_1_A(
            dataset_id="test_dataset",
            seed=42,
            condition_a=cond_a,
            condition_b=cond_b,
            absolute_improvement=0.6,
            improvement_percent=10.0,
        )
        self.assertTrue(result.success())

    def test_failure_when_learning_worse(self):
        """Fail if learning MAE >= baseline MAE."""
        cond_a = AblationConditionResult(
            condition_name="Baseline",
            condition_description="No calibration",
            held_out_mae=5.4,
            training_mae=5.4,
        )
        cond_b = AblationConditionResult(
            condition_name="Learning",
            condition_description="With calibration",
            held_out_mae=6.0,
            training_mae=5.8,
        )
        result = AblationResult17_1_A(
            dataset_id="test_dataset",
            seed=42,
            condition_a=cond_a,
            condition_b=cond_b,
            absolute_improvement=-0.6,
            improvement_percent=-11.1,
        )
        self.assertFalse(result.success())


class TestResearchAblation17_1_A(unittest.TestCase):
    """Test ablation study implementation."""

    def test_ablation_runs_without_error(self):
        """Ablation study should execute successfully."""
        ablation = ResearchAblation17_1_A(seed=42)
        result = ablation.run()
        self.assertIsNotNone(result)
        self.assertEqual(result.seed, 42)

    def test_ablation_improvement_calculation(self):
        """Verify improvement metrics are calculated correctly."""
        ablation = ResearchAblation17_1_A(seed=42)
        result = ablation.run()

        # Check that improvement is correct
        expected_absolute = (
            result.condition_a.held_out_mae - result.condition_b.held_out_mae
        )
        self.assertAlmostEqual(result.absolute_improvement, expected_absolute, places=4)

        # Check that percentage is correct
        if result.condition_a.held_out_mae > 0:
            expected_percent = (
                100.0 * expected_absolute / result.condition_a.held_out_mae
            )
            self.assertAlmostEqual(
                result.improvement_percent, expected_percent, places=2
            )

    def test_ablation_determinism_same_seed(self):
        """Same seed should produce identical results (deterministic)."""
        result1 = run_research_ablation_17_1_a(seed=42)
        result2 = run_research_ablation_17_1_a(seed=42)

        self.assertAlmostEqual(
            result1.condition_a.held_out_mae,
            result2.condition_a.held_out_mae,
            places=4,
        )
        self.assertAlmostEqual(
            result1.condition_b.held_out_mae,
            result2.condition_b.held_out_mae,
            places=4,
        )
        self.assertAlmostEqual(
            result1.improvement_percent,
            result2.improvement_percent,
            places=2,
        )

    def test_ablation_different_seeds_produce_variation(self):
        """Different seeds should produce different but similar results."""
        result1 = run_research_ablation_17_1_a(seed=42)
        result2 = run_research_ablation_17_1_a(seed=123)

        # Results should be different
        self.assertNotAlmostEqual(
            result1.condition_b.held_out_mae,
            result2.condition_b.held_out_mae,
            places=2,
        )

        # But both should show learning benefit
        self.assertTrue(result1.success())
        self.assertTrue(result2.success())

    def test_ablation_with_provided_dataset(self):
        """Ablation study should work with a pre-existing dataset."""
        generator = ResearchBenchmarkGenerator(seed=42)
        dataset = generator.generate_dataset()

        ablation = ResearchAblation17_1_A(dataset=dataset, seed=42)
        result = ablation.run()

        self.assertEqual(result.dataset_id, dataset.dataset_id)
        self.assertTrue(result.success())

    def test_condition_names_are_correct(self):
        """Condition names should clearly identify the treatment."""
        ablation = ResearchAblation17_1_A(seed=42)
        result = ablation.run()

        self.assertEqual(result.condition_a.condition_name, "Baseline")
        self.assertEqual(result.condition_b.condition_name, "Learning")

    def test_ablation_dataset_consistency(self):
        """Both conditions should use the same dataset."""
        ablation = ResearchAblation17_1_A(seed=42)
        result = ablation.run()

        # Dataset ID should be consistent
        self.assertTrue(result.dataset_id.startswith("research_benchmark_v1_seed_"))
        self.assertEqual(result.seed, 42)

    def test_improvement_metrics_coherence(self):
        """Absolute and percentage improvement should be coherent."""
        ablation = ResearchAblation17_1_A(seed=42)
        result = ablation.run()

        # If absolute improvement is positive, percentage should be positive
        if result.absolute_improvement > 0:
            self.assertGreater(result.improvement_percent, 0)

        # If absolute improvement is negative, percentage should be negative
        if result.absolute_improvement < 0:
            self.assertLess(result.improvement_percent, 0)

        # If absolute improvement is zero, percentage should be zero
        if abs(result.absolute_improvement) < 0.001:
            self.assertAlmostEqual(result.improvement_percent, 0.0, places=1)


class TestRunResearchAblation17_1_A(unittest.TestCase):
    """Test convenience function."""

    def test_convenience_function_runs(self):
        """Convenience function should execute and return valid result."""
        result = run_research_ablation_17_1_a(seed=42)
        self.assertIsInstance(result, AblationResult17_1_A)
        self.assertTrue(result.success())

    def test_convenience_function_with_custom_params(self):
        """Should accept custom learning_rate and bounds."""
        custom_bounds = {
            "state_adjustment_max": 0.15,
            "probability_bias_max": 0.015,
            "risk_bias_max": 0.015,
            "uncertainty_increment_max": 0.015,
            "confidence_increment_max": 0.015,
        }
        result = run_research_ablation_17_1_a(
            seed=42, learning_rate=0.008, bounds=custom_bounds
        )
        self.assertIsInstance(result, AblationResult17_1_A)


if __name__ == "__main__":
    unittest.main()
