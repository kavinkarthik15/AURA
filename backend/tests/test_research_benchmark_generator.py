"""
Tests for 17.0A Research Benchmark Generator

Validates:
- Deterministic generation (same seed → same dataset)
- Correct train/held-out split
- Diverse experience categories
- Reasonable prediction error across all experiences
"""

import unittest
from backend.experiments.research_benchmark_generator import (
    ResearchBenchmarkGenerator,
    generate_research_dataset,
)


class ResearchBenchmarkGeneratorTests(unittest.TestCase):
    """Test 17.0A benchmark generation."""

    def test_deterministic_generation_same_seed_produces_same_dataset(self):
        """Same seed should produce identical datasets."""
        gen1 = ResearchBenchmarkGenerator(seed=42)
        dataset1 = gen1.generate_dataset(training_size=80, held_out_size=20)

        gen2 = ResearchBenchmarkGenerator(seed=42)
        dataset2 = gen2.generate_dataset(training_size=80, held_out_size=20)

        # Compare training experiences
        self.assertEqual(len(dataset1.training_experiences), len(dataset2.training_experiences))
        for exp1, exp2 in zip(
            dataset1.training_experiences, dataset2.training_experiences
        ):
            self.assertEqual(exp1.experience_id, exp2.experience_id)
            self.assertEqual(exp1.initial_state, exp2.initial_state)
            self.assertEqual(exp1.predicted_future_state, exp2.predicted_future_state)
            self.assertEqual(exp1.actual_future_state, exp2.actual_future_state)

        # Compare held-out experiences
        self.assertEqual(len(dataset1.held_out_experiences), len(dataset2.held_out_experiences))
        for exp1, exp2 in zip(
            dataset1.held_out_experiences, dataset2.held_out_experiences
        ):
            self.assertEqual(exp1.experience_id, exp2.experience_id)
            self.assertEqual(exp1.initial_state, exp2.initial_state)
            self.assertEqual(exp1.predicted_future_state, exp2.predicted_future_state)
            self.assertEqual(exp1.actual_future_state, exp2.actual_future_state)

    def test_different_seed_produces_different_dataset(self):
        """Different seeds should produce different datasets."""
        gen1 = ResearchBenchmarkGenerator(seed=42)
        dataset1 = gen1.generate_dataset(training_size=80, held_out_size=20)

        gen2 = ResearchBenchmarkGenerator(seed=43)
        dataset2 = gen2.generate_dataset(training_size=80, held_out_size=20)

        # At least some experiences should differ
        diffs = sum(
            1
            for exp1, exp2 in zip(
                dataset1.training_experiences, dataset2.training_experiences
            )
            if exp1.initial_state != exp2.initial_state
            or exp1.predicted_future_state != exp2.predicted_future_state
            or exp1.actual_future_state != exp2.actual_future_state
        )
        self.assertGreater(diffs, 0)

    def test_correct_train_held_out_split(self):
        """Dataset should have 80 training and 20 held-out experiences."""
        gen = ResearchBenchmarkGenerator(seed=42)
        dataset = gen.generate_dataset(training_size=80, held_out_size=20)

        self.assertEqual(dataset.training_size(), 80)
        self.assertEqual(dataset.held_out_size(), 20)
        self.assertEqual(dataset.total_size(), 100)

    def test_all_experience_categories_represented(self):
        """All 8 categories should be represented in the dataset."""
        gen = ResearchBenchmarkGenerator(seed=42)
        dataset = gen.generate_dataset(training_size=80, held_out_size=20)

        all_experiences = dataset.training_experiences + dataset.held_out_experiences
        categories = {exp.category for exp in all_experiences}

        expected_categories = {
            "low_skill_practice",
            "medium_skill_practice",
            "high_skill_practice",
            "low_motivation",
            "high_motivation",
            "mixed_skills",
            "project_completion",
            "plateau",
        }
        self.assertEqual(categories, expected_categories)

    def test_experiences_have_valid_prediction_errors(self):
        """All experiences should have measurable prediction errors."""
        gen = ResearchBenchmarkGenerator(seed=42)
        dataset = gen.generate_dataset(training_size=80, held_out_size=20)

        all_experiences = dataset.training_experiences + dataset.held_out_experiences
        for exp in all_experiences:
            error = exp.prediction_error()
            self.assertGreaterEqual(error, 0.0)
            self.assertLessEqual(error, 100.0)

    def test_prediction_errors_vary_by_category(self):
        """Different categories should have different error distributions."""
        gen = ResearchBenchmarkGenerator(seed=42)
        dataset = gen.generate_dataset(training_size=80, held_out_size=20)

        all_experiences = dataset.training_experiences + dataset.held_out_experiences

        # Group by category
        by_category = {}
        for exp in all_experiences:
            if exp.category not in by_category:
                by_category[exp.category] = []
            by_category[exp.category].append(exp.prediction_error())

        # Low motivation should have higher average errors
        low_motivation_errors = by_category.get("low_motivation", [])
        high_motivation_errors = by_category.get("high_motivation", [])
        if low_motivation_errors and high_motivation_errors:
            avg_low = sum(low_motivation_errors) / len(low_motivation_errors)
            avg_high = sum(high_motivation_errors) / len(high_motivation_errors)
            # Low motivation typically has higher errors
            self.assertGreater(avg_low, avg_high)

    def test_all_experiences_have_required_fields(self):
        """Each experience should have all required fields."""
        gen = ResearchBenchmarkGenerator(seed=42)
        dataset = gen.generate_dataset(training_size=80, held_out_size=20)

        all_experiences = dataset.training_experiences + dataset.held_out_experiences
        for exp in all_experiences:
            self.assertIsNotNone(exp.experience_id)
            self.assertIsNotNone(exp.category)
            self.assertIsNotNone(exp.initial_state)
            self.assertIsNotNone(exp.selected_action)
            self.assertIsNotNone(exp.predicted_future_state)
            self.assertIsNotNone(exp.actual_future_state)

            self.assertGreater(len(exp.initial_state), 0)
            self.assertGreater(len(exp.selected_action), 0)
            self.assertGreater(len(exp.predicted_future_state), 0)
            self.assertGreater(len(exp.actual_future_state), 0)

    def test_convenience_function(self):
        """Test generate_research_dataset convenience function."""
        dataset = generate_research_dataset(seed=42, training_size=80, held_out_size=20)

        self.assertEqual(dataset.training_size(), 80)
        self.assertEqual(dataset.held_out_size(), 20)
        self.assertIn("research_benchmark_v1", dataset.dataset_id)

    def test_skills_bounded_between_1_and_100(self):
        """All skill values should be between 1 and 100."""
        gen = ResearchBenchmarkGenerator(seed=42)
        dataset = gen.generate_dataset(training_size=80, held_out_size=20)

        all_experiences = dataset.training_experiences + dataset.held_out_experiences
        for exp in all_experiences:
            for skill, value in exp.initial_state.items():
                self.assertGreaterEqual(value, 1)
                self.assertLessEqual(value, 100)
            for skill, value in exp.predicted_future_state.items():
                self.assertGreaterEqual(value, 1)
                self.assertLessEqual(value, 100)
            for skill, value in exp.actual_future_state.items():
                self.assertGreaterEqual(value, 1)
                self.assertLessEqual(value, 100)

    def test_large_dataset_generation(self):
        """Should be able to generate large datasets efficiently."""
        gen = ResearchBenchmarkGenerator(seed=42)
        dataset = gen.generate_dataset(training_size=500, held_out_size=100)

        self.assertEqual(dataset.training_size(), 500)
        self.assertEqual(dataset.held_out_size(), 100)


if __name__ == "__main__":
    unittest.main()
