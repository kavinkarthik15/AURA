import tempfile
import unittest
from pathlib import Path

from backend.ai.context_builder import ContextBuilder
from backend.memory.memory_manager import MemoryManager


class UnifiedContextBuilderTests(unittest.TestCase):
    def test_build_context_collects_goal_state_and_memories(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(registry_path=Path(tmpdir) / "registry.json")
            manager.set_working_goal("Build reliable backend services", session_id="session-1")
            manager.add_working_experience(
                {"goal": "Build reliable backend services", "actions": ["write tests"], "completed_actions": ["write tests"], "success": True},
                session_id="session-1",
            )
            manager.store_knowledge(
                {
                    "knowledge_id": "KNW-1",
                    "concept": "backend",
                    "statement": "Testing improves reliability",
                    "confidence": 0.9,
                    "importance": 0.8,
                    "status": "ACTIVE",
                    "supporting_episode_ids": ["ep-1"],
                    "revision": 1,
                }
            )
            manager.store_reflection(
                {"goal": "Build reliable backend services", "decision": "accept", "confidence": 0.8}
            )

            builder = ContextBuilder(memory_manager=manager)
            context = builder.build(
                goal="Build reliable backend services",
                current_state={"python": 3, "testing": 2},
                session_id="session-1",
            )

            self.assertEqual(context.goal, "Build reliable backend services")
            self.assertEqual(context.current_state["python"], 3)
            self.assertGreaterEqual(len(context.relevant_experiences), 1)
            self.assertGreaterEqual(len(context.relevant_knowledge), 1)
            self.assertGreaterEqual(len(context.relevant_reflections), 1)
            self.assertIn("backend", context.context_summary.lower())
            self.assertGreaterEqual(context.confidence, 0.0)
            self.assertGreaterEqual(len(context.evidence), 1)


if __name__ == "__main__":
    unittest.main()
