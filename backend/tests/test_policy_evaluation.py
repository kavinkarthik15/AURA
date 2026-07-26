import unittest

from backend.ai.evaluate_policy import PolicyEvaluator
from backend.ai.planning_policy import PlanningPolicy, PolicySample


class PolicyEvaluationTests(unittest.TestCase):
    def test_policy_benchmark_returns_metrics(self) -> None:
        samples = [PolicySample(state={"python": 50}, goal="Placement", action="Project", success=True)]
        metrics = PolicyEvaluator().evaluate(PlanningPolicy().fit(samples), samples)
        self.assertEqual(metrics["samples"], 1)
        self.assertIn("top_action_accuracy", metrics)
        self.assertIn("average_probability", metrics)
        self.assertIn("coverage", metrics)
        self.assertIn("policy_version", metrics)
        self.assertIn("training_date", metrics)


if __name__ == "__main__":
    unittest.main()
