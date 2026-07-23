import tempfile
import unittest
from pathlib import Path

from backend.ai.continual_dataset_builder import ContinualDatasetBuilder
from backend.ai.continual_learning import ContinualLearningPipeline
from backend.ai.experience_replay import ExperienceReplayBuffer
from backend.ai.model_registry import ModelRegistry
from backend.models.experience_log import ExperienceLog


class ContinualLearningTests(unittest.TestCase):
    def test_replay_buffer_filters_and_samples(self) -> None:
        buffer = ExperienceReplayBuffer(
            [
                ExperienceLog(execution_id="a", experience_id="1", success=True, prediction_error=0.4),
                ExperienceLog(execution_id="a", experience_id="1", success=True, prediction_error=0.4),
                ExperienceLog(execution_id="b", experience_id="2", success=False, prediction_error=1.2),
            ]
        )
        sample = buffer.sample(batch_size=2, shuffle=False)
        self.assertEqual(len(sample), 2)
        self.assertTrue(sample[0].success)

    def test_dataset_builder_converts_experiences(self) -> None:
        builder = ContinualDatasetBuilder()
        samples = builder.build_samples([
            ExperienceLog(
                initial_state={"python": 40},
                actual_state={"python": 55},
                actions=["Python Project"],
                completed_actions=["Python Project"],
            )
        ])
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["target_delta"]["python"], 15)

    def test_pipeline_runs_and_reports_deployment(self) -> None:
        pipeline = ContinualLearningPipeline()
        experiences = [
            ExperienceLog(
                execution_id="exec_001",
                experience_id="exp_001",
                initial_state={"python": 30},
                actual_state={"python": 40},
                actions=["Python Project"],
                completed_actions=["Python Project"],
                success=True,
            )
        ]
        result = pipeline.run(experiences, base_dataset=[])
        self.assertIn("candidate", result)
        self.assertIn("benchmark", result)
        self.assertIn("deployment", result)

    def test_registry_records_lineage_and_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            pipeline = ContinualLearningPipeline()
            pipeline.registry = ModelRegistry(registry_path=registry_path)
            pipeline.trainer.registry = pipeline.registry
            pipeline.registry.register_model(
                model_version="v2",
                algorithm="RandomForestRegressor",
                dataset_size=10,
                mae=0.2,
                mse=0.1,
                r2=0.9,
                training_data_hash="baseline",
                dataset_version="v1",
            )
            result = pipeline.run([
                ExperienceLog(
                    execution_id="exec_002",
                    experience_id="exp_002",
                    initial_state={"python": 40},
                    actual_state={"python": 50},
                    actions=["Python Project"],
                    completed_actions=["Python Project"],
                    success=True,
                )
            ], base_dataset=[])
            self.assertEqual(result["registered"]["parent_model"], "v2")
            self.assertEqual(result["registered"]["training_source"], "experience_replay")
            self.assertEqual(result["registered"]["experience_count"], 1)
            self.assertIn("benchmark", result["registered"])

    def test_replay_stats_and_cycle_report(self) -> None:
        buffer = ExperienceReplayBuffer([
            ExperienceLog(execution_id="a", experience_id="1", success=True, prediction_error=0.3, actions=["A"], completed_actions=["A"]),
            ExperienceLog(execution_id="a", experience_id="1", success=True, prediction_error=0.3, actions=["A"], completed_actions=["A"]),
            ExperienceLog(execution_id="b", experience_id="2", success=False, prediction_error=0.8, actions=["B"], completed_actions=[]),
        ])
        stats = buffer.get_statistics()
        self.assertEqual(stats["total_experiences"], 3)
        self.assertEqual(stats["duplicates_removed"], 1)
        self.assertEqual(stats["successful"], 1)
        self.assertEqual(stats["failed"], 1)
        self.assertEqual(stats["sampled"], 2)
        self.assertIn("average_goal_progress", stats)

        pipeline = ContinualLearningPipeline()
        result = pipeline.run([
            ExperienceLog(
                execution_id="exec_003",
                experience_id="exp_003",
                initial_state={"python": 25},
                actual_state={"python": 35},
                actions=["Python Project"],
                completed_actions=["Python Project"],
                success=True,
            )
        ], base_dataset=[])
        self.assertIn("Continual Learning Cycle", result["report"])
        self.assertIn("Decision:", result["report"])


if __name__ == "__main__":
    unittest.main()
