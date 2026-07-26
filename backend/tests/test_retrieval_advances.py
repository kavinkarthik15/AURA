import tempfile
import unittest
from pathlib import Path

from backend.ai.experience_retriever import ExperienceRetriever


class RetrievalAdvanceTests(unittest.TestCase):
    def test_recent_successful_experiences_rank_higher_with_age_decay(self) -> None:
        records = [
            {
                "experience_id": "old",
                "initial_state": {"python": 50},
                "goal_name": "Python Growth",
                "actions": ["Project"],
                "completed_actions": ["Project"],
                "success": True,
                "goal_completion": 0.9,
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "experience_id": "new",
                "initial_state": {"python": 50},
                "goal_name": "Python Growth",
                "actions": ["Project"],
                "completed_actions": ["Project"],
                "success": True,
                "goal_completion": 0.95,
                "timestamp": "2026-01-01T00:00:00Z",
            },
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = ExperienceRetriever(records, index_path=Path(tmpdir) / "index.json")
            retriever.build_index(records)
            result = retriever.retrieve({"python": 50}, "Python Growth", ["Project"], top_k=2)
            self.assertEqual(result["matches"][0].experience_id, "new")

    def test_adaptive_weighting_and_diversity_are_supported(self) -> None:
        records = [
            {"experience_id": "one", "initial_state": {"python": 50}, "goal_name": "Python Growth", "actions": ["Project"], "completed_actions": ["Project"], "success": True, "goal_completion": 0.9},
            {"experience_id": "two", "initial_state": {"python": 50}, "goal_name": "Python Growth", "actions": ["Project"], "completed_actions": ["Project"], "success": True, "goal_completion": 0.92},
            {"experience_id": "three", "initial_state": {"python": 49}, "goal_name": "Python Growth", "actions": ["Project"], "completed_actions": ["Project"], "success": False, "goal_completion": 0.7},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = ExperienceRetriever(records, index_path=Path(tmpdir) / "index.json")
            retriever.build_index(records)
            weight = retriever.compute_adaptive_weight(policy_confidence=0.2, retrieval_confidence=0.8, goal_type="exploration")
            self.assertGreaterEqual(weight, 0.0)
            self.assertLessEqual(weight, 1.0)
            result = retriever.retrieve({"python": 50}, "Python Growth", ["Project"], top_k=2)
            self.assertLessEqual(len(result["matches"]), 2)

    def test_analytics_snapshot_records_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = ExperienceRetriever([], index_path=Path(tmpdir) / "index.json")
            retriever.record_analytics("exp_1", 0.95, 0.12, 0.5, 0.8)
            analytics = retriever.get_analytics_summary()
            self.assertGreater(analytics["retrieval_count"], 0)
            self.assertGreater(analytics["average_similarity"], 0.0)


if __name__ == "__main__":
    unittest.main()
