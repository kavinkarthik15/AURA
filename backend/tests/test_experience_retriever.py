import tempfile
import unittest
from pathlib import Path

from backend.ai.experience_retriever import ExperienceRetriever


class ExperienceRetrieverTests(unittest.TestCase):
    def test_builds_index_and_returns_top_matches(self) -> None:
        records = [
            {"experience_id": "one", "initial_state": {"python": 50}, "goal_name": "Python Growth", "actions": ["Project"], "completed_actions": ["Project"], "success": True, "goal_completion": 0.9},
            {"experience_id": "two", "initial_state": {"python": 10}, "goal_name": "Other", "actions": ["Course"], "completed_actions": [], "success": False},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = ExperienceRetriever(records, index_path=Path(tmpdir) / "index.json")
            retriever.build_index()
            result = retriever.retrieve({"python": 52}, "Python Growth", ["Project"], top_k=1)
            self.assertEqual(result["matches"][0].experience_id, "one")
            self.assertGreater(result["matches"][0].similarity, 0.8)
            cached = retriever.retrieve({"python": 52}, "Python Growth", ["Project"], top_k=1)
            self.assertTrue(cached["cache_hit"])


if __name__ == "__main__":
    unittest.main()
