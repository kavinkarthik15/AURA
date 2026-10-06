from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from typing import Any, Dict, Optional

from backend.planning.candidate_selector import CandidateActionResult


@dataclass
class DigitalTwinDecisionSignal:
    action: Optional[str]
    trajectory_score: float
    normalized_score: float
    adjustment: float
    confidence: float
    branch_probability: float
    risk: float
    uncertainty: float
    reason: str
    valid: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlannerAdjustment:
    action: Optional[str]
    adjustment: float
    confidence: float
    enabled: bool
    reason: str


class DigitalTwinScoreTranslator:
    def __init__(
        self,
        adjustment_scale: float = 0.1,
        invalid_reasons: Optional[set[str]] = None,
    ) -> None:
        self.adjustment_scale = max(0.0, float(adjustment_scale))
        self.invalid_reasons = invalid_reasons or {
            "empty_candidates",
            "no_valid_candidates",
            "disabled",
            "fallback",
        }

    def translate(
        self,
        selection: Optional[CandidateActionResult],
    ) -> DigitalTwinDecisionSignal:
        if selection is None:
            return self._invalid_signal(reason="no_selection")

        valid = self._is_valid(selection)
        if not valid:
            return self._invalid_signal(reason=selection.selection_reason or "invalid_selection")

        normalized_score = self._normalize_score(selection.score)
        confidence = self._infer_confidence(selection)
        adjustment = self._calculate_adjustment(normalized_score, selection, valid)

        return DigitalTwinDecisionSignal(
            action=selection.action,
            trajectory_score=float(selection.score),
            normalized_score=round(normalized_score, 4),
            adjustment=round(adjustment, 4),
            confidence=round(confidence, 4),
            branch_probability=float(selection.probability),
            risk=float(selection.risk),
            uncertainty=float(selection.uncertainty),
            reason=selection.selection_reason or "unknown",
            valid=valid,
            metadata=dict(selection.metadata or {}),
        )

    def _is_valid(self, selection: CandidateActionResult) -> bool:
        if selection.action is None or not isinstance(selection.action, str) or not selection.action.strip():
            return False
        if selection.selection_reason in self.invalid_reasons:
            return False
        return True

    def _normalize_score(self, score: float) -> float:
        # Map arbitrary trajectory scores into a planner-compatible [0, 1] range.
        try:
            scaled = 1.0 / (1.0 + exp(-float(score)))
        except OverflowError:
            scaled = 1.0 if score > 0 else 0.0
        return max(0.0, min(1.0, scaled))

    def _infer_confidence(self, selection: CandidateActionResult) -> float:
        return max(0.0, min(1.0, float(selection.probability) if selection.probability is not None else 0.0))

    def _calculate_adjustment(
        self,
        normalized_score: float,
        selection: CandidateActionResult,
        valid: bool,
    ) -> float:
        if not valid:
            return 0.0

        risk_penalty = min(1.0, max(0.0, float(selection.risk) / 2.0))
        uncertainty_penalty = min(1.0, max(0.0, float(selection.uncertainty) / 2.0))
        penalty = max(risk_penalty, uncertainty_penalty)
        adjustment = (normalized_score - 0.5) * self.adjustment_scale * (1.0 - penalty)
        return adjustment

    def _invalid_signal(self, reason: str) -> DigitalTwinDecisionSignal:
        return DigitalTwinDecisionSignal(
            action=None,
            trajectory_score=0.0,
            normalized_score=0.0,
            adjustment=0.0,
            confidence=0.0,
            branch_probability=0.0,
            risk=0.0,
            uncertainty=0.0,
            reason=reason,
            valid=False,
            metadata={},
        )

    def translate_to_planner_adjustment(
        self,
        signal: Optional[DigitalTwinDecisionSignal],
        enabled: bool = True,
        adjustment_scale: float | int = 0.1,
        max_adjustment: float | int = 0.2,
    ) -> PlannerAdjustment:
        if not enabled or signal is None or not signal.valid:
            return PlannerAdjustment(
                action=None,
                adjustment=0.0,
                confidence=0.0,
                enabled=False,
                reason=signal.reason if signal is not None else "disabled",
            )

        confidence = max(0.0, min(1.0, float(signal.confidence)))
        risk = max(0.0, min(1.0, float(signal.risk)))
        uncertainty = max(0.0, min(1.0, float(signal.uncertainty)))
        normalized_score = max(0.0, min(1.0, float(signal.normalized_score)))
        effective_signal = normalized_score * confidence * (1.0 - risk) * (1.0 - uncertainty)
        adjustment = effective_signal * float(adjustment_scale)
        bounded = max(-abs(float(max_adjustment)), min(abs(float(max_adjustment)), adjustment))
        return PlannerAdjustment(
            action=signal.action,
            adjustment=round(bounded, 4),
            confidence=confidence,
            enabled=True,
            reason=signal.reason,
        )
