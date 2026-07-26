import tempfile
import unittest
from pathlib import Path

from backend.services.experiment_tracker import ExperimentTracker
from backend.services.goal_plan_service import GoalPlanService
from backend.services.beam_search_planner import BeamSearchPlanner
from backend.models.goal_state import GoalState


class AblationAndReproducibilityTests(unittest.TestCase):
    def test_run_retrieval_ablation_returns_policy_retrieval_and_hybrid(self) -> None:
        service = GoalPlanService(beam_search_planner=BeamSearchPlanner())
        result = service.run_retrieval_ablation(
            {"python": 40, "dsa": 10, "projects": 1},
            GoalState(goal="Python Growth", target_skills={"python": 80}),
            seed=7,
        )
        self.assertIn("policy_only", result["results"])
        self.assertIn("retrieval_only", result["results"])
        self.assertIn("hybrid", result["results"])
        self.assertIn("comparison", result)

    def test_experiment_tracker_records_reproducibility_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = ExperimentTracker(root_path=Path(tmpdir))
            path = tracker.record(
                "exp_001",
                {
                    "random_seed": 7,
                    "retrieval_configuration": {"top_k": 2},
                    "planner_configuration": {"beam_width": 3},
                    "policy_version": "policy_v2",
                    "retrieval_version": "retrieval_v2",
                    "model_version": "model_v3",
                },
            )
            payload = path.read_text(encoding="utf-8")
            self.assertIn("random_seed", payload)
            self.assertIn("retrieval_configuration", payload)
            self.assertIn("policy_version", payload)
            self.assertIn("retrieval_version", payload)
            self.assertIn("model_version", payload)


if __name__ == "__main__":
    unittest.main()
