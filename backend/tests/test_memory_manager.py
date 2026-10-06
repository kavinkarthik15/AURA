import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from backend.ai.experience_retriever import ExperienceRetriever
from backend.ai.reflection_memory import ReflectionMemory
from backend.memory.episodic_memory import EpisodicMemory
from backend.memory.memory_manager import MemoryManager
from backend.memory.memory_policies import MemoryPolicies, RetrievalPolicy
from backend.memory.memory_registry import MemoryRegistry
from backend.memory.reflection_memory_store import ReflectionMemoryStore


class MemoryManagerTests(unittest.TestCase):
    def test_registry_initializes_all_memory_stores(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(registry_path=Path(tmpdir) / "registry.json")
            registry = manager.registry.get()

        self.assertEqual(
            registry["active_stores"],
            ["working", "episodic", "semantic", "procedural", "reflection", "context"],
        )
        self.assertEqual(registry["version"], "memory_v1")
        self.assertEqual(registry["configuration"]["episodic_status"], "active")
        self.assertEqual(registry["configuration"]["benchmark_status"], "available")

    def test_episodic_retrieval_delegates_through_manager(self) -> None:
        records = [
            {
                "experience_id": "exp-42",
                "initial_state": {"python": 50},
                "goal_name": "Python Growth",
                "actions": ["Python Project"],
                "success": True,
            }
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            retriever = ExperienceRetriever(records, index_path=Path(tmpdir) / "index.json")
            retriever.build_index()
            manager = MemoryManager(
                episodic_store=EpisodicMemory(retriever),
                registry_path=Path(tmpdir) / "registry.json",
            )
            result = manager.retrieve_experiences({"python": 50}, "Python Growth", ["Python Project"])

        self.assertEqual(result["matches"][0].experience_id, "exp-42")
        self.assertEqual(manager.metrics["retrieve"], 1)

    def test_reflection_memory_is_reached_through_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            reflection = ReflectionMemory(Path(tmpdir) / "reflection.json")
            manager = MemoryManager(
                reflection_store=ReflectionMemoryStore(reflection),
                registry_path=Path(tmpdir) / "registry.json",
            )
            stored = manager.store_reflection({"reflection_id": "ref-1", "decision": "accept"})
            records = manager.retrieve_reflections()

        self.assertEqual(stored["reflection_id"], "ref-1")
        self.assertEqual(records[-1]["decision"], "accept")

    def test_placeholder_stores_are_safe_and_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(registry_path=Path(tmpdir) / "registry.json")

        self.assertEqual(manager.retrieve("semantic"), [])
        self.assertEqual(manager.retrieve("procedural"), [])
        self.assertEqual(manager.retrieve("context"), [])
        self.assertEqual(manager.consolidate()["semantic"]["consolidated"], 0)

    def test_manager_owns_policies_and_exposes_them_in_health(self) -> None:
        policies = MemoryPolicies(retrieval=RetrievalPolicy())
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(policies=policies, registry_path=Path(tmpdir) / "registry.json")
            health = manager.health()
            registry = manager.registry.get()

        self.assertIs(manager.policies, policies)
        self.assertEqual(health["policies"], ["retrieval", "importance", "consolidation", "forgetting"])
        self.assertEqual(registry["configuration"]["policies"], health["policies"])

    def test_retrieve_without_type_uses_retrieval_policy(self) -> None:
        class EpisodicOnlyPolicy(RetrievalPolicy):
            def __init__(self):
                self.queries = []

            def select_memory_types(self, query):
                self.queries.append(query)
                return ["episodic"]

        with tempfile.TemporaryDirectory() as tmpdir:
            retrieval_policy = EpisodicOnlyPolicy()
            manager = MemoryManager(
                policies=MemoryPolicies(retrieval=retrieval_policy),
                registry_path=Path(tmpdir) / "registry.json",
            )
            result = manager.retrieve(query={"goal": "anything"})

        self.assertEqual(retrieval_policy.queries, [{"goal": "anything"}])
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
