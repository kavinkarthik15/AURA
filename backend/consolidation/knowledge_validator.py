from __future__ import annotations

from typing import Any, List

from backend.consolidation.knowledge_models import KnowledgeCandidate
from backend.consolidation.validation_models import ValidatedKnowledgeCandidate


class KnowledgeValidator:
    def __init__(self, min_support_count: int = 2, min_confidence: float = 0.6, min_importance: float = 0.5) -> None:
        self.min_support_count = min_support_count
        self.min_confidence = min_confidence
        self.min_importance = min_importance

    def validate(self, candidates: List[KnowledgeCandidate]) -> List[ValidatedKnowledgeCandidate]:
        results: List[ValidatedKnowledgeCandidate] = []
        for candidate in candidates:
            validation = self._evaluate(candidate)
            results.append(validation)
        return results

    def _evaluate(self, candidate: KnowledgeCandidate) -> ValidatedKnowledgeCandidate:
        passed_rules: List[str] = []
        failed_rules: List[str] = []
        reasons: List[str] = []

        support_count = len(candidate.evidence)
        if support_count >= self.min_support_count:
            passed_rules.append("minimum_support_count")
        else:
            failed_rules.append("minimum_support_count")
            reasons.append("Insufficient supporting evidence")

        if candidate.confidence >= self.min_confidence:
            passed_rules.append("minimum_confidence")
        else:
            failed_rules.append("minimum_confidence")
            reasons.append("Confidence below threshold")

        if candidate.metadata.get("support_count", 0) >= self.min_support_count:
            passed_rules.append("pattern_support")
        else:
            failed_rules.append("pattern_support")
            reasons.append("Pattern support is too weak")

        if candidate.metadata.get("support_count", 0) >= self.min_support_count:
            passed_rules.append("eligible_pattern_type")
        else:
            failed_rules.append("eligible_pattern_type")
            reasons.append("Pattern type is not eligible for promotion")

        score = 0.0
        if "minimum_support_count" in passed_rules:
            score += 0.25
        if "minimum_confidence" in passed_rules:
            score += 0.25
        if "pattern_support" in passed_rules:
            score += 0.25
        if "eligible_pattern_type" in passed_rules:
            score += 0.25

        decision = "REJECT"
        if score >= 0.75:
            decision = "ACCEPT"
        elif score >= 0.5:
            decision = "REVIEW"

        return ValidatedKnowledgeCandidate(
            candidate_id=candidate.candidate_id,
            validation_score=round(score, 2),
            decision=decision,
            reasons=reasons,
            failed_rules=failed_rules,
            passed_rules=passed_rules,
            metadata={"knowledge": candidate.knowledge, "generated_from": candidate.generated_from},
        )
