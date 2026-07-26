import tempfile
import unittest
from pathlib import Path

from backend.ai.evaluate_retrieval import RetrievalEvaluator
from backend.ai.experience_retriever import ExperienceRetriever
from backend.ai.retrieval_registry import RetrievalRegistry


class RetrievalBenchmarkTests(unittest.TestCase):
    def test_benchmark_and_registry(self) -> None:
        records = [{"experience_id": "exp_1", "initial_state": {"python": 50}, "goal_name": "Python", "actions": ["Project"], "completed_actions": ["Project"], "success": True}]
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = ExperienceRetriever(records, index_path=Path(tmpdir) / "index.json")
            retriever.build_index()
            metrics = RetrievalEvaluator().evaluate(retriever, [{"state": {"python": 51}, "goal": "Python", "actions": ["Project"], "relevant_experience_ids": ["exp_1"]}])
            self.assertEqual(metrics["retrieval_precision"], 1.0)
            self.assertIn("retrieval_time_ms", metrics)
            registry = RetrievalRegistry(Path(tmpdir) / "retrieval_registry.json")
            record = registry.register("retrieval_v1", "hybrid", 0.4, "v1", metrics)
            self.assertEqual(registry.latest()["version"], record["version"])


if __name__ == "__main__":
    unittest.main()
