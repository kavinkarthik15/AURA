import unittest
from backend.ai.context_builder import ContextBuilder
from backend.ai.decision_reasoner import DecisionReasoner
from backend.memory.memory_manager import MemoryManager


class DecisionReasonerUpdatedTests(unittest.TestCase):
    def test_decision_candidate_metadata_includes_utility_and_constraints(self) -> None:
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
        manager.create_working_session()
        manager.add_candidate_plan(
            [{"action": "Practice Python", "type": "task", "value": "Practice Python for 30 minutes"}],
            manager.working_memory.active_session_id,
        )

        builder = ContextBuilder(memory_manager=manager)
        context = builder.build(goal="Become ML Engineer", current_state={"python": 3}, session_id=manager.working_memory.active_session_id)
        reasoner = DecisionReasoner(memory_manager=manager)
        candidates = reasoner.generate_candidates(context)

        self.assertGreaterEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertTrue(candidate.decision_id.startswith("DEC-"))
        self.assertEqual(candidate.goal_supported, "Become ML Engineer")
        self.assertGreaterEqual(candidate.expected_reward, 0.0)
        self.assertGreaterEqual(candidate.expected_cost, 0.0)
        self.assertGreaterEqual(candidate.expected_risk, 0.0)
        self.assertGreaterEqual(candidate.confidence, 0.0)
        self.assertGreaterEqual(candidate.utility_score, 0.0)
        self.assertTrue(candidate.reasoning)
        self.assertTrue(candidate.supporting_knowledge)
        self.assertTrue(candidate.assumptions)
        self.assertIsInstance(candidate.expected_state_change, dict)
        self.assertIsInstance(candidate.goal_alignment, dict)
        self.assertTrue(candidate.created_at)

    def test_generate_candidates_returns_empty_list_when_no_context(self) -> None:
        from backend.ai.context_builder import ContextBuilder

        context = ContextBuilder().build(goal="", current_state={})
        reasoner = DecisionReasoner()
        candidates = reasoner.generate_candidates(context)
        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
