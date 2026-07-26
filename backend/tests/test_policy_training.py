import tempfile
import unittest
from pathlib import Path

from backend.ai.policy_dataset import PolicyDatasetBuilder
from backend.ai.policy_registry import PolicyRegistry
from backend.ai.policy_trainer import PolicyTrainer
from backend.models.experience_log import ExperienceLog


class PolicyTrainingTests(unittest.TestCase):
    def test_trains_and_persists_policy_artifact(self) -> None:
        samples = PolicyDatasetBuilder().build_samples([
            ExperienceLog(goal_name="Placement", initial_state={"python": 40}, actions=["Project"], completed_actions=["Project"], success=True)
        ])
        with tempfile.TemporaryDirectory() as tmpdir:
            result = PolicyTrainer().train(samples, output_path=Path(tmpdir) / "policy.json")
            self.assertEqual(result["sample_count"], 1)
            self.assertTrue((Path(tmpdir) / "policy.json").exists())

    def test_policy_registry_records_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PolicyRegistry(Path(tmpdir) / "registry.json")
            record = registry.register("v1", "hash", 2, {"top_action_accuracy": 1.0})
            self.assertEqual(record["policy_version"], "v1")
            self.assertEqual(registry.latest()["sample_count"], 2)


if __name__ == "__main__":
    unittest.main()
