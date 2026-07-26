import tempfile
import unittest
from pathlib import Path

from backend.ai.evaluate_policy import PolicyEvaluator
from backend.ai.planning_policy import PlanningPolicy, PolicySample
from backend.ai.policy_deployment import PolicyDeployment
from backend.ai.policy_drift import PolicyDriftDetector
from backend.ai.policy_registry import PolicyRegistry
from backend.ai.policy_visualization import PolicyVisualizer


class PolicyIntelligenceTests(unittest.TestCase):
    def test_entropy_distinguishes_exploration_and_exploitation(self) -> None:
        uncertain = PlanningPolicy().fit([
            PolicySample({}, "Goal", "A", success=True),
            PolicySample({}, "Goal", "B", success=True),
            PolicySample({}, "Goal", "C", success=True),
        ])
        certain = PlanningPolicy().fit([
            PolicySample({}, "Goal", "A", success=True),
            PolicySample({}, "Goal", "A", success=True),
            PolicySample({}, "Goal", "A", success=True),
            PolicySample({}, "Goal", "B", success=False),
        ])
        uncertain_entropy = uncertain.normalized_entropy({}, "Goal", ["A", "B", "C"])
        certain_entropy = certain.normalized_entropy({}, "Goal", ["A", "B", "C"])
        self.assertGreater(uncertain_entropy, certain_entropy)
        self.assertEqual(uncertain.exploration_mode({}, "Goal", ["A", "B", "C"]), "explore")
        self.assertEqual(certain.exploration_mode({}, "Goal", ["A", "B", "C"]), "exploit")

    def test_drift_recommends_retraining(self) -> None:
        previous = PlanningPolicy().fit([PolicySample({}, "Goal", "A", success=True) for _ in range(10)])
        current = PlanningPolicy().fit([PolicySample({}, "Goal", "B", success=True) for _ in range(10)])
        result = PolicyDriftDetector().compare(previous, current)
        self.assertTrue(result["significant"])
        self.assertTrue(result["retraining_recommended"])

    def test_coverage_has_state_and_goal_breakdowns(self) -> None:
        samples = [PolicySample({"python": 50, "dsa": 20}, "Placement", "Project", success=True)]
        metrics = PolicyEvaluator().evaluate(PlanningPolicy().fit(samples), samples)
        self.assertIn("python", metrics["coverage_by_state"])
        self.assertIn("Placement", metrics["coverage_by_goal"])

    def test_registry_rolls_back_rejected_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = PolicyRegistry(Path(tmpdir) / "registry.json")
            registry.register("policy_v1", "old", 10, {"top_action_accuracy": 0.8}, accepted=True)
            result = PolicyDeployment().deploy(
                {"policy_version": "policy_v2", "dataset_hash": "new", "sample_count": 12},
                {"top_action_accuracy": 0.7},
                registry,
            )
            self.assertFalse(result["deployed"])
            self.assertEqual(result["active_policy"], "policy_v1")

    def test_visualization_contains_policy_diagnostics(self) -> None:
        policy = PlanningPolicy().fit([PolicySample({}, "Goal", "Project", success=True)])
        dashboard = PolicyVisualizer().render_markdown(policy, {}, "Goal", ["Project"])
        self.assertIn("Probability", dashboard)
        self.assertIn("Policy entropy", dashboard)
        self.assertIn("Project", dashboard)


if __name__ == "__main__":
    unittest.main()
