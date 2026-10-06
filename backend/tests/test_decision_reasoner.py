import unittest
from backend.ai.context_builder import ContextBuilder
from backend.ai.decision_reasoner import DecisionReasoner
from backend.memory.memory_manager import MemoryManager
from backend.models.goal_state import GoalState


class DecisionReasonerTests(unittest.TestCase):
    def test_decision_reasoner_generates_candidates_from_planning_context(self) -> None:
        manager = MemoryManager()
        manager.store_knowledge(
            {
                "knowledge_id": "KNW-1",
                "concept": "Python",
                "statement": "Python practice every day improves skill",
                "confidence": 0.9,
                "importance": 0.8,
                "status": "ACTIVE",
                "supporting_episode_ids": ["ep-1"],
                "revision": 1,
            }
        )
        manager.store_knowledge(
            {
                "knowledge_id": "KNW-2",
                "concept": "Study",
                "statement": "Morning study increases retention",
                "confidence": 0.8,
                "importance": 0.7,
                "status": "ACTIVE",
                "supporting_episode_ids": ["ep-2"],
                "revision": 1,
            }
        )
        manager.create_working_session()
        manager.add_candidate_plan(["Practice Python", "Review notes"], manager.working_memory.active_session_id)
        builder = ContextBuilder(memory_manager=manager)
        context = builder.build(goal="Become ML Engineer", current_state={"python": 3}, session_id=manager.working_memory.active_session_id)

        reasoner = DecisionReasoner(memory_manager=manager)
        candidates = reasoner.generate_candidates(context)

        self.assertGreaterEqual(len(candidates), 1)
        self.assertTrue(any("Practice Python" in str(candidate.action) for candidate in candidates))
        self.assertGreaterEqual(candidates[0].confidence, 0.0)
        self.assertTrue(candidates[0].reasoning)
        self.assertTrue(candidates[0].expected_outcome)
        self.assertTrue(candidates[0].supporting_knowledge)

    def test_decision_reasoner_returns_empty_list_when_no_context(self) -> None:
        context = ContextBuilder().build(goal="", current_state={})
        reasoner = DecisionReasoner()
        candidates = reasoner.generate_candidates(context)

        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
