import unittest

from backend.consolidation.knowledge_generator import KnowledgeGenerator
from backend.consolidation.pattern_models import PatternCandidate


class KnowledgeGeneratorTests(unittest.TestCase):
    def test_empty_pattern_list_returns_no_candidates(self) -> None:
        generator = KnowledgeGenerator()
        self.assertEqual(generator.generate([]), [])

    def test_repeated_success_pattern_generates_candidate(self) -> None:
        generator = KnowledgeGenerator()
        pattern = PatternCandidate(
            pattern_type="Repeated Success",
            confidence=0.82,
            importance=0.9,
            support_count=3,
            episode_ids=["ep_1", "ep_2", "ep_3"],
            summary="Repeated success",
        )

        candidates = generator.generate([pattern])
        self.assertEqual(len(candidates), 1)
        self.assertIn("Successful outcomes", candidates[0].knowledge)
        self.assertEqual(candidates[0].generated_from, "Repeated Success")
        self.assertEqual(candidates[0].evidence, ["ep_1", "ep_2", "ep_3"])

    def test_repeated_failure_pattern_generates_candidate(self) -> None:
        generator = KnowledgeGenerator()
        pattern = PatternCandidate(
            pattern_type="Repeated Failure",
            confidence=0.74,
            support_count=2,
            episode_ids=["ep_1", "ep_2"],
            summary="Repeated failure",
        )

        candidates = generator.generate([pattern])
        self.assertEqual(len(candidates), 1)
        self.assertIn("Repeated failures", candidates[0].knowledge)

    def test_registry_statistics_are_recorded(self) -> None:
        generator = KnowledgeGenerator()
        pattern = PatternCandidate(
            pattern_type="Habit",
            confidence=0.68,
            support_count=2,
            episode_ids=["ep_1", "ep_2"],
            summary="Habit",
        )

        generator.generate([pattern])
        stats = generator.registry.statistics()
        self.assertGreaterEqual(stats["knowledge_candidates_generated"], 1)
        self.assertGreaterEqual(stats["average_confidence"], 0.0)
