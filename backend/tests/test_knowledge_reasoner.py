import unittest
from backend.ai.context_builder import ContextBuilder
from backend.ai.knowledge_reasoner import KnowledgeReasoner
from backend.memory.memory_manager import MemoryManager
from backend.models.goal_state import GoalState


class KnowledgeReasonerTests(unittest.TestCase):
    def test_knowledge_reasoner_returns_insights_from_planning_context(self) -> None:
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
        builder = ContextBuilder(memory_manager=manager)
        context = builder.build(goal="Become ML Engineer", current_state={"python": 3}, session_id=None)

        reasoner = KnowledgeReasoner(memory_manager=manager)
        insight = reasoner.reason(context)

        self.assertGreater(insight.confidence, 0.0)
        self.assertTrue(insight.applicable_rules)
        self.assertTrue(insight.inferred_opportunities)
        self.assertTrue(insight.supporting_knowledge)
        self.assertIn("KNW-1", insight.supporting_knowledge)

    def test_knowledge_reasoner_handles_missing_knowledge_gracefully(self) -> None:
        context = ContextBuilder().build(goal="Become ML Engineer", current_state={})
        reasoner = KnowledgeReasoner()
        insight = reasoner.reason(context)

        self.assertEqual(insight.applicable_rules, [])
        self.assertEqual(insight.inferred_constraints, [])
        self.assertEqual(insight.inferred_opportunities, [])
        self.assertEqual(insight.inferred_risks, [])
        self.assertEqual(insight.supporting_knowledge, [])
        self.assertGreaterEqual(insight.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
