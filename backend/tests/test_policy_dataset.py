import unittest

from backend.ai.policy_dataset import PolicyDatasetBuilder
from backend.models.experience_log import ExperienceLog


class PolicyDatasetTests(unittest.TestCase):
    def test_builds_policy_samples_from_experience(self) -> None:
        samples = PolicyDatasetBuilder().build_samples([
            ExperienceLog(
                goal_name="Placement",
                initial_state={"python": 50},
                actions=["Python Project", "DSA Practice"],
                completed_actions=["Python Project"],
                success=True,
            )
        ])
        self.assertEqual(len(samples), 2)
        self.assertTrue(samples[0].success)
        self.assertFalse(samples[1].success)
        self.assertEqual(samples[0].goal, "Placement")


if __name__ == "__main__":
    unittest.main()
