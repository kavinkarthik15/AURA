import unittest

from backend.consolidation.knowledge_models import KnowledgeCandidate
from backend.consolidation.knowledge_validator import KnowledgeValidator


class KnowledgeValidatorTests(unittest.TestCase):
    def test_empty_candidate_list_returns_no_results(self) -> None:
        validator = KnowledgeValidator()
        self.assertEqual(validator.validate([]), [])

    def test_acceptable_candidate_is_accepted(self) -> None:
        validator = KnowledgeValidator(min_support_count=2, min_confidence=0.6)
        candidate = KnowledgeCandidate(
            candidate_id="KGC-1",
            knowledge="Useful knowledge",
            confidence=0.8,
            evidence=["ep_1", "ep_2"],
            generated_from="Repeated Success",
            metadata={"support_count": 2},
        )

        results = validator.validate([candidate])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].decision, "ACCEPT")
        self.assertGreaterEqual(results[0].validation_score, 0.75)

    def test_weak_candidate_is_rejected(self) -> None:
        validator = KnowledgeValidator(min_support_count=2, min_confidence=0.6)
        candidate = KnowledgeCandidate(
            candidate_id="KGC-2",
            knowledge="Weak knowledge",
            confidence=0.4,
            evidence=["ep_1"],
            generated_from="Repeated Success",
            metadata={"support_count": 1},
        )

        results = validator.validate([candidate])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].decision, "REJECT")
        self.assertLess(results[0].validation_score, 0.75)
