"""
Tests for 17.0A Research Dataset Persistence

Validates saving and loading of research datasets.
"""

import unittest
import tempfile
from pathlib import Path
from backend.experiments.research_benchmark_generator import (
    ResearchBenchmarkGenerator,
)
from backend.experiments.research_dataset_persistence import (
    ResearchDatasetPersistence,
)


class ResearchDatasetPersistenceTests(unittest.TestCase):
    """Test 17.0A dataset persistence."""

    def setUp(self):
        """Create a temporary directory for test data."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.persistence = ResearchDatasetPersistence(self.temp_dir.name)

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_save_and_load_dataset(self):
        """Should be able to save and load dataset without data loss."""
        # Generate original dataset
        gen = ResearchBenchmarkGenerator(seed=42)
        original_dataset = gen.generate_dataset(training_size=80, held_out_size=20)

        # Save it
        filepath = self.persistence.save_dataset(original_dataset)
        self.assertTrue(filepath.exists())

        # Load it back
        loaded_dataset = self.persistence.load_dataset(str(filepath))

        # Verify they match
        self.assertEqual(original_dataset.dataset_id, loaded_dataset.dataset_id)
        self.assertEqual(original_dataset.seed, loaded_dataset.seed)
        self.assertEqual(
            original_dataset.training_size(), loaded_dataset.training_size()
        )
        self.assertEqual(
            original_dataset.held_out_size(), loaded_dataset.held_out_size()
        )

        # Verify experiences match
        for orig, loaded in zip(
            original_dataset.training_experiences,
            loaded_dataset.training_experiences,
        ):
            self.assertEqual(orig.experience_id, loaded.experience_id)
            self.assertEqual(orig.initial_state, loaded.initial_state)
            self.assertEqual(
                orig.predicted_future_state, loaded.predicted_future_state
            )
            self.assertEqual(
                orig.actual_future_state, loaded.actual_future_state
            )

    def test_load_by_dataset_id(self):
        """Should be able to load dataset by ID without full path."""
        gen = ResearchBenchmarkGenerator(seed=42)
        original_dataset = gen.generate_dataset(training_size=80, held_out_size=20)

        # Save it
        self.persistence.save_dataset(original_dataset)

        # Load by ID only
        loaded_dataset = self.persistence.load_dataset(original_dataset.dataset_id)

        self.assertEqual(original_dataset.dataset_id, loaded_dataset.dataset_id)
        self.assertEqual(original_dataset.seed, loaded_dataset.seed)

    def test_list_datasets(self):
        """Should list all saved datasets."""
        gen = ResearchBenchmarkGenerator(seed=42)

        dataset1 = gen.generate_dataset(training_size=80, held_out_size=20)
        self.persistence.save_dataset(dataset1)

        gen2 = ResearchBenchmarkGenerator(seed=43)
        dataset2 = gen2.generate_dataset(training_size=80, held_out_size=20)
        self.persistence.save_dataset(dataset2)

        datasets = self.persistence.list_datasets()
        self.assertEqual(len(datasets), 2)
        self.assertIn(dataset1.dataset_id, datasets)
        self.assertIn(dataset2.dataset_id, datasets)

    def test_get_latest_dataset(self):
        """Should retrieve the most recently saved dataset."""
        gen = ResearchBenchmarkGenerator(seed=42)
        dataset1 = gen.generate_dataset(training_size=80, held_out_size=20)
        self.persistence.save_dataset(dataset1)

        import time

        time.sleep(0.1)  # Ensure different mtime

        gen2 = ResearchBenchmarkGenerator(seed=43)
        dataset2 = gen2.generate_dataset(training_size=80, held_out_size=20)
        self.persistence.save_dataset(dataset2)

        latest = self.persistence.get_latest_dataset()
        self.assertEqual(latest.dataset_id, dataset2.dataset_id)

    def test_load_nonexistent_dataset_raises_error(self):
        """Should raise FileNotFoundError for missing dataset."""
        with self.assertRaises(FileNotFoundError):
            self.persistence.load_dataset("nonexistent_dataset")

    def test_saved_file_is_valid_json(self):
        """Saved file should be valid JSON that can be inspected."""
        gen = ResearchBenchmarkGenerator(seed=42)
        dataset = gen.generate_dataset(training_size=2, held_out_size=1)

        filepath = self.persistence.save_dataset(dataset)

        # Load as raw JSON
        with open(filepath, "r") as f:
            data = json.load(f)

        # Verify structure
        self.assertIn("dataset_id", data)
        self.assertIn("seed", data)
        self.assertIn("training_experiences", data)
        self.assertIn("held_out_experiences", data)
        self.assertEqual(len(data["training_experiences"]), 2)
        self.assertEqual(len(data["held_out_experiences"]), 1)

        # Verify first experience has all fields
        exp = data["training_experiences"][0]
        self.assertIn("experience_id", exp)
        self.assertIn("category", exp)
        self.assertIn("initial_state", exp)
        self.assertIn("selected_action", exp)
        self.assertIn("predicted_future_state", exp)
        self.assertIn("actual_future_state", exp)


import json


if __name__ == "__main__":
    unittest.main()
