"""
Tests for 17.0B Research Experiment

Validates:
- Baseline system (no learning)
- Learning system (with calibration)
- Correct comparison and metrics
- Pass criterion: learning_mae < baseline_mae
"""

import unittest
from backend.experiments.research_benchmark_generator import (
    ResearchBenchmarkGenerator,
)
from backend.experiments.research_experiment_17_0_b import (
    ResearchExperiment17_0_B,
    run_research_experiment_17_0_b,
)


class ResearchExperiment17_0_BTests(unittest.TestCase):
    """Test 17.0B experiment runner."""

    def setUp(self):
        """Generate small dataset for testing."""
        gen = ResearchBenchmarkGenerator(seed=42)
        self.dataset = gen.generate_dataset(training_size=10, held_out_size=5)

    def test_experiment_runs_without_error(self):
        """Should complete experiment successfully."""
        experiment = ResearchExperiment17_0_B(self.dataset, learning_rate=0.1)
        result = experiment.run()

        self.assertIsNotNone(result)
        self.assertEqual(result.dataset_id, self.dataset.dataset_id)
        self.assertEqual(result.training_size, 10)
        self.assertEqual(result.held_out_size, 5)

    def test_baseline_results_have_correct_structure(self):
        """Baseline results should have all predictions."""
        experiment = ResearchExperiment17_0_B(self.dataset, learning_rate=0.1)
        result = experiment.run()

        baseline = result.baseline_results
        self.assertEqual(len(baseline.training_predictions), 10)
        self.assertEqual(len(baseline.held_out_predictions), 5)
        self.assertGreater(baseline.training_mae(), 0.0)
        self.assertGreater(baseline.held_out_mae(), 0.0)

    def test_learning_results_have_correct_structure(self):
        """Learning results should have all predictions."""
        experiment = ResearchExperiment17_0_B(self.dataset, learning_rate=0.1)
        result = experiment.run()

        learning = result.learning_results
        self.assertEqual(len(learning.training_predictions), 10)
        self.assertEqual(len(learning.held_out_predictions), 5)
        self.assertGreater(learning.training_mae(), 0.0)
        self.assertGreater(learning.held_out_mae(), 0.0)

    def test_comparison_metrics_calculated(self):
        """Comparison metrics should be computed."""
        experiment = ResearchExperiment17_0_B(self.dataset, learning_rate=0.1)
        result = experiment.run()

        self.assertIsNotNone(result.baseline_mae)
        self.assertIsNotNone(result.learning_mae)
        self.assertIsNotNone(result.absolute_improvement)
        self.assertIsNotNone(result.improvement_percent)
        self.assertIsNotNone(result.learning_is_better)

    def test_absolute_improvement_is_difference(self):
        """Absolute improvement should be baseline_mae - learning_mae."""
        experiment = ResearchExperiment17_0_B(self.dataset, learning_rate=0.1)
        result = experiment.run()

        expected_improvement = round(
            result.baseline_mae - result.learning_mae, 4
        )
        self.assertEqual(result.absolute_improvement, expected_improvement)

    def test_improvement_percent_calculated_correctly(self):
        """Improvement percent should be (improvement / baseline_mae) * 100."""
        experiment = ResearchExperiment17_0_B(self.dataset, learning_rate=0.1)
        result = experiment.run()

        if result.baseline_mae > 0:
            expected_percent = round(
                (result.absolute_improvement / result.baseline_mae) * 100, 2
            )
            self.assertEqual(result.improvement_percent, expected_percent)

    def test_success_criterion(self):
        """Success: learning_mae < baseline_mae."""
        experiment = ResearchExperiment17_0_B(self.dataset, learning_rate=0.1)
        result = experiment.run()

        expected_success = result.learning_mae < result.baseline_mae
        self.assertEqual(result.learning_is_better, expected_success)
        self.assertEqual(result.success(), expected_success)

    def test_deterministic_results_same_seed(self):
        """Same seed should produce same results."""
        gen1 = ResearchBenchmarkGenerator(seed=42)
        dataset1 = gen1.generate_dataset(training_size=5, held_out_size=3)

        experiment1 = ResearchExperiment17_0_B(dataset1, learning_rate=0.1)
        result1 = experiment1.run(experiment_id="exp_deterministic_1")

        gen2 = ResearchBenchmarkGenerator(seed=42)
        dataset2 = gen2.generate_dataset(training_size=5, held_out_size=3)

        experiment2 = ResearchExperiment17_0_B(dataset2, learning_rate=0.1)
        result2 = experiment2.run(experiment_id="exp_deterministic_1")

        # Results should be identical
        self.assertEqual(result1.baseline_mae, result2.baseline_mae)
        self.assertEqual(result1.learning_mae, result2.learning_mae)
        self.assertEqual(
            result1.absolute_improvement, result2.absolute_improvement
        )

    def test_learning_rate_affects_calibration(self):
        """Different learning rates should produce different results."""
        experiment_low = ResearchExperiment17_0_B(
            self.dataset, learning_rate=0.05
        )
        result_low = experiment_low.run(experiment_id="exp_lr_low")

        experiment_high = ResearchExperiment17_0_B(
            self.dataset, learning_rate=0.2
        )
        result_high = experiment_high.run(experiment_id="exp_lr_high")

        # Different learning rates should produce different learning MAE
        # (though they might converge)
        self.assertNotEqual(result_low.learning_mae, result_high.learning_mae)

    def test_baseline_mae_same_across_learning_rates(self):
        """Baseline should be unaffected by learning_rate."""
        experiment1 = ResearchExperiment17_0_B(
            self.dataset, learning_rate=0.05
        )
        result1 = experiment1.run()

        experiment2 = ResearchExperiment17_0_B(
            self.dataset, learning_rate=0.2
        )
        result2 = experiment2.run()

        # Baseline MAE should be identical
        self.assertEqual(result1.baseline_mae, result2.baseline_mae)

    def test_each_prediction_has_mae(self):
        """Each prediction record should have MAE calculated."""
        experiment = ResearchExperiment17_0_B(self.dataset, learning_rate=0.1)
        result = experiment.run()

        for pred in result.baseline_results.held_out_predictions:
            self.assertGreaterEqual(pred.mae, 0.0)
            self.assertLessEqual(pred.mae, 100.0)

        for pred in result.learning_results.held_out_predictions:
            self.assertGreaterEqual(pred.mae, 0.0)
            self.assertLessEqual(pred.mae, 100.0)

    def test_convenience_function_runs_experiment(self):
        """Convenience function should work without manual setup."""
        # This will use the generated dataset from setUp
        # For this test, we'll generate a small one
        gen = ResearchBenchmarkGenerator(seed=42)
        from backend.experiments.research_dataset_persistence import (
            ResearchDatasetPersistence,
        )

        persistence = ResearchDatasetPersistence()
        persistence.save_dataset(self.dataset)

        # Now call convenience function
        result = run_research_experiment_17_0_b(
            dataset_id=self.dataset.dataset_id,
            learning_rate=0.1,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.dataset_id, self.dataset.dataset_id)

    def test_experiment_result_is_valid(self):
        """Result should be a valid ResearchExperimentResult."""
        experiment = ResearchExperiment17_0_B(self.dataset, learning_rate=0.1)
        result = experiment.run()

        # Should serialize without error
        result_dict = result.model_dump()
        self.assertIsNotNone(result_dict)
        self.assertIn("experiment_id", result_dict)
        self.assertIn("baseline_mae", result_dict)
        self.assertIn("learning_mae", result_dict)


if __name__ == "__main__":
    unittest.main()
