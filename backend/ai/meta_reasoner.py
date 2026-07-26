from __future__ import annotations

from typing import Any, Dict, List


class MetaReasoner:
    def __init__(self) -> None:
        self.version = "meta_reasoner_v1"

    def evaluate(
        self,
        reasoning_trace: Dict[str, Any],
        reasoning_metadata: Dict[str, Any],
        confidence_breakdown: Dict[str, float],
        retrieved_experiences: List[Dict[str, Any]],
        goal: str,
        assumptions: List[Dict[str, Any]] | None = None,
        contributors: List[str] | None = None,
    ) -> Dict[str, Any]:
        assumptions = assumptions or []
        contributors = contributors or []
        confidence = float(reasoning_trace.get("confidence", 0.0))
        coverage = float(reasoning_trace.get("coverage", 0.0))
        consistency = bool(reasoning_metadata.get("consistency_status", {}).get("consistent", True))
        evidence_count = len(retrieved_experiences)
        evidence_sufficiency = min(1.0, 0.3 + 0.2 * evidence_count + 0.3 * coverage)
        evidence_quality = 1.0 if retrieved_experiences else 0.1
        reflection_score = round(
            min(1.0, 0.35 * confidence + 0.25 * evidence_sufficiency + 0.2 * coverage + 0.2 * evidence_quality),
            4,
        )
        strengths = []
        weaknesses = []
        decision_reason = ""
        if confidence >= 0.75:
            strengths.append("high confidence")
        else:
            weaknesses.append("low confidence")
            decision_reason = "low_confidence"
        if consistency:
            strengths.append("consistent reasoning")
        else:
            weaknesses.append("contradictory evidence")
            decision_reason = "contradictory_evidence"
        if evidence_count >= 2:
            strengths.append("evidence sufficiency")
        else:
            weaknesses.append("insufficient evidence")
            if not decision_reason:
                decision_reason = "insufficient_evidence"
        if not assumptions:
            weaknesses.append("missing assumptions")
            decision_reason = "missing_assumptions"
        missing_evidence = []
        if not retrieved_experiences:
            missing_evidence.append("No successful experience for this goal")
        if evidence_sufficiency < 0.5:
            missing_evidence.append("Evidence sufficiency below threshold")
        if not assumptions:
            decision = "request_more_information"
            recommended_action = "gather_additional_information"
        elif not consistency:
            decision = "reject"
            recommended_action = "revise"
        else:
            decision = "accept" if reflection_score >= 0.75 and evidence_sufficiency >= 0.6 else "replan"
            recommended_action = "continue" if decision == "accept" else "revise"
        return {
            "goal": goal,
            "confidence": round(confidence, 4),
            "reflection_score": reflection_score,
            "decision": decision,
            "decision_reason": decision_reason or "standard_evaluation",
            "recommended_action": recommended_action,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "missing_evidence": missing_evidence,
            "evidence_sufficiency": round(evidence_sufficiency, 4),
            "confidence_breakdown": confidence_breakdown,
            "assumptions": assumptions,
            "contributors": contributors,
        }
