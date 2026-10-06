import tempfile
import unittest
from pathlib import Path

from backend.ai.experience_retriever import ExperienceRetriever
from backend.memory.episodic_memory import ARCHIVED, DEPRECATED, MERGED, EpisodicMemory
from backend.memory.experience_index import ExperienceIndex
from backend.memory.memory_models import MemoryStatus


class EpisodicMemoryTests(unittest.TestCase):
    def _memory(self, tmpdir: str) -> EpisodicMemory:
        records = [
            {
                "experience_id": "exp-1",
                "initial_state": {"python": 50},
                "goal_name": "Python Growth",
                "actions": ["Project"],
                "completed_actions": ["Project"],
                "success": True,
                "goal_completion": 0.9,
                "importance": 0.8,
            },
            {
                "experience_id": "exp-2",
                "initial_state": {"python": 45},
                "goal_name": "Python Growth",
                "actions": ["Course"],
                "success": False,
                "goal_completion": 0.4,
            },
        ]
        retriever = ExperienceRetriever(records, index_path=Path(tmpdir) / "legacy.json")
        return EpisodicMemory(retriever, ExperienceIndex(Path(tmpdir) / "index.json"))

    def test_creation_metadata_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = self._memory(tmpdir)
            stored = memory.store({"experience_id": "exp-3", "state_before": {"python": 60}, "goal": "Growth", "actions": ["Project"], "success": True})
            stats = memory.statistics()

        self.assertTrue(stored["memory_id"].startswith("EXP-"))
        self.assertEqual(stored["status"], MemoryStatus.ACTIVE.value)
        self.assertEqual(stored["revision"], 1)
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["index"]["entries"], 3)

    def test_status_enum_and_provenance_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = self._memory(tmpdir)
            stored = memory.store(
                {
                    "experience_id": "exp-3",
                    "initial_state": {"python": 60},
                    "goal": "Growth",
                    "actions": ["Project"],
                    "success": True,
                    "importance": 0.92,
                    "confidence": 0.88,
                    "confidence_source": "Reasoner",
                    "importance_reason": "Repeated Success",
                    "importance_source": "Reflection",
                }
            )
            record = memory._find(stored["memory_id"])

        self.assertIs(record.status, MemoryStatus.ACTIVE)
        self.assertEqual(record.confidence_source, "Reasoner")
        self.assertEqual(record.importance_reason, "Repeated Success")
        self.assertEqual(record.importance_source, "Reflection")

    def test_events_and_retrieval_results_are_emitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = self._memory(tmpdir)
            memory.store({"experience_id": "exp-3", "initial_state": {"python": 60}, "goal": "Growth", "actions": ["Project"], "success": True})
            result = memory.retrieve_experiences({"python": 51}, "Python Growth", ["Project"], top_k=1)

        self.assertTrue(any(event["event_type"] == "MemoryCreated" for event in memory.events))
        self.assertTrue(any(event["event_type"] == "MemoryRetrieved" for event in memory.events))
        self.assertIn("retrieval_results", result)
        self.assertEqual(len(result["retrieval_results"]), 1)
        self.assertIn(result["retrieval_results"][0].retrieval_strategy, {"similarity", "hybrid"})

    def test_experience_index_contract_supports_rebuild_update_remove_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            index = ExperienceIndex(Path(tmpdir) / "index.json")
            index.index({"memory_id": "EXP-1", "experience_id": "exp-1", "goal": "Growth"})
            self.assertEqual(index.search({"user_id": "default_user"})[0]["memory_id"], "EXP-1")
            index.update({"memory_id": "EXP-1", "experience_id": "exp-1", "goal": "Updated"})
            index.rebuild([{"memory_id": "EXP-2", "experience_id": "exp-2", "goal": "Other"}])
            self.assertEqual(index.statistics()["entries"], 1)
            self.assertTrue(index.remove("EXP-2"))

        self.assertEqual(index.statistics()["entries"], 0)

    def test_retrieval_updates_metadata_and_preserves_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = self._memory(tmpdir)
            result = memory.retrieve_experiences({"python": 51}, "Python Growth", ["Project"], top_k=1)
            source = memory._find(result["matches"][0].experience_id)

        self.assertEqual(result["matches"][0].experience_id, "exp-1")
        self.assertEqual(source.retrieval_count, 1)
        self.assertIsNotNone(source.last_accessed)

    def test_update_revision_merge_archive_and_soft_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = self._memory(tmpdir)
            revised = memory.revise("exp-1", {"goal_completion": 1.0})
            memory.store({"experience_id": "exp-3", "initial_state": {"python": 55}, "goal": "Growth", "actions": ["Project"], "success": True})
            merged = memory.merge(["exp-2", "exp-3"], {"goal": "Merged Growth"})
            archived = memory.archive("exp-2")
            deleted = memory.delete(revised["memory_id"])
            statuses = memory.status_distribution()

        self.assertEqual(revised["revision"], 2)
        self.assertEqual(memory._find("exp-1").status, MemoryStatus.DEPRECATED)
        self.assertEqual(merged["status"], MemoryStatus.ACTIVE.value)
        self.assertIn(memory._find("exp-2").memory_id, merged["related_memories"])
        self.assertTrue(archived)
        self.assertTrue(deleted)
        self.assertGreaterEqual(statuses[MERGED], 1)
        self.assertGreaterEqual(statuses[ARCHIVED], 1)

    def test_archived_and_deleted_experiences_leave_default_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = self._memory(tmpdir)
            memory.archive("exp-1")
            memory.delete("exp-2")
            result = memory.retrieve_experiences({"python": 50}, "Python Growth", ["Project"])

        self.assertEqual(result["matches"], [])

    def test_relationships_and_analytics(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = self._memory(tmpdir)
            self.assertTrue(memory.relate("exp-1", "exp-2"))
            record = memory._find("exp-1")
            analytics = memory.statistics()

        self.assertEqual(record.related_memories, [memory._find("exp-2").memory_id])
        self.assertGreaterEqual(analytics["active_count"], 2)
        self.assertIn("1", analytics["revision_distribution"])
        self.assertIn("ACTIVE", analytics["status_distribution"])
        self.assertGreater(memory.average_importance(), 0.0)


if __name__ == "__main__":
    unittest.main()
