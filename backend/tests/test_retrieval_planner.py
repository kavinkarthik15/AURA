import tempfile
import unittest
from pathlib import Path

from backend.ai.experience_retriever import ExperienceRetriever
from backend.models.goal_state import GoalState
from backend.services.beam_search_planner import BeamSearchPlanner


class RetrievalPlannerTests(unittest.TestCase):
    def test_beam_search_uses_retrieved_experiences(self) -> None:
        records = [{"experience_id": "exp_42", "initial_state": {"python": 50, "dsa": 20, "projects": 10}, "goal_name": "Python Growth", "actions": ["Python Project"], "completed_actions": ["Python Project"], "success": True, "goal_completion": 0.92}]
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = ExperienceRetriever(records, index_path=Path(tmpdir) / "index.json")
            retriever.build_index()
            result = BeamSearchPlanner(retriever=retriever).search(
                {"python": 50, "dsa": 20, "projects": 10},
                GoalState(goal="Python Growth", target_skills={"python": 80}),
                beam_width=3,
                max_depth=2,
            )
            self.assertTrue(result["retrieval_enabled"])
            self.assertTrue(result["retrieved_experiences"])
            self.assertIn("exp_42", {item["experience_id"] for item in result["retrieved_experiences"]})
            self.assertIn("similar previous execution", result["retrieval_explanation"])


if __name__ == "__main__":
    unittest.main()
