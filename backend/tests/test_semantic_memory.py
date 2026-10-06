import tempfile
import unittest
from pathlib import Path

from backend.memory.memory_manager import MemoryManager
from backend.memory.memory_models import MemoryStatus
from backend.memory.semantic_memory import SemanticMemory


class SemanticMemoryTests(unittest.TestCase):
    def test_create_retrieve_update_revision_archive_and_delete(self) -> None:
        memory = SemanticMemory()
        stored = memory.store(
            {
                "concept": "Backend",
                "statement": "Learns backend technologies quickly.",
                "knowledge_type": "skill",
                "confidence": 0.9,
                "importance": 0.95,
                "confidence_source": "Reasoner",
                "importance_reason": "Repeated Success",
                "importance_source": "Reflection",
            }
        )

        self.assertEqual(stored["status"], MemoryStatus.ACTIVE.value)
        retrieved = memory.retrieve({"query": "backend"})
        self.assertEqual(retrieved[0]["concept"], "Backend")

        updated = memory.update(stored["knowledge_id"], {"statement": "Learns backend and API design quickly."})
        self.assertIn("API", updated["statement"])

        revised = memory.revise(stored["knowledge_id"], {"statement": "Learns backend and API design reliably."})
        self.assertEqual(revised["revision"], 2)
        self.assertEqual(memory._find(stored["knowledge_id"]).status, MemoryStatus.DEPRECATED)

        self.assertTrue(memory.archive(stored["knowledge_id"]))
        self.assertTrue(memory.delete(revised["knowledge_id"]))

    def test_relationships_and_statistics(self) -> None:
        memory = SemanticMemory()
        first = memory.store({"concept": "Exercise", "statement": "Exercise consistency drops during exams.", "knowledge_type": "pattern"})
        second = memory.store({"concept": "Study", "statement": "Exam weeks reduce workout frequency.", "knowledge_type": "pattern"})

        self.assertTrue(memory.relate(first["knowledge_id"], second["knowledge_id"]))
        stats = memory.statistics()

        self.assertEqual(stats["count"], 2)
        self.assertEqual(stats["active_count"], 2)
        self.assertIn("ACTIVE", stats["status_distribution"])

    def test_manager_integration_and_retrieval(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(registry_path=Path(tmpdir) / "registry.json")
            stored = manager.store_knowledge(
                {
                    "concept": "Programming",
                    "statement": "The user learns backend technologies quickly.",
                    "knowledge_type": "skill",
                }
            )
            result = manager.retrieve_knowledge("backend")
            stats = manager.knowledge_statistics()

        self.assertEqual(stored["concept"], "Programming")
        self.assertEqual(result[0]["concept"], "Programming")
        self.assertEqual(stats["count"], 1)


if __name__ == "__main__":
    unittest.main()
