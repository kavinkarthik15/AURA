import unittest

from backend.consolidation.knowledge_merger import KnowledgeMerger
from backend.consolidation.validation_models import ValidatedKnowledgeCandidate
from backend.memory.memory_models import KnowledgeRecord


class KnowledgeMergerTests(unittest.TestCase):
    def test_empty_candidates_returns_no_decisions(self) -> None:
        merger = KnowledgeMerger()
        self.assertEqual(merger.decide([]), [])

    def test_rejected_candidate_is_ignored(self) -> None:
        merger = KnowledgeMerger()
        candidate = ValidatedKnowledgeCandidate(candidate_id="VAL-1", decision="REJECT")

        decisions = merger.decide([candidate])
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].action, "IGNORE")

    def test_similar_existing_knowledge_merges(self) -> None:
        existing = [KnowledgeRecord(knowledge_id="KNW-1", statement="Useful knowledge", concept="knowledge")]
        merger = KnowledgeMerger(existing_knowledge=existing)
        candidate = ValidatedKnowledgeCandidate(
            candidate_id="VAL-2",
            decision="ACCEPT",
            metadata={"knowledge": "Useful knowledge", "evidence": ["ep_1", "ep_2"]},
        )

        decisions = merger.decide([candidate])
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].action, "MERGE")
        self.assertEqual(decisions[0].target_knowledge_id, "KNW-1")

    def test_no_match_creates_new_plan(self) -> None:
        merger = KnowledgeMerger(existing_knowledge=[])
        candidate = ValidatedKnowledgeCandidate(
            candidate_id="VAL-3",
            decision="ACCEPT",
            metadata={"knowledge": "Brand new knowledge", "evidence": ["ep_1"]},
        )

        decisions = merger.decide([candidate])
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].action, "CREATE")
