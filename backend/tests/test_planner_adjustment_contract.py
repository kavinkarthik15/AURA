from backend.planning.candidate_selector import CandidateActionResult
from backend.planning.digital_twin_score_translator import (
    DigitalTwinDecisionSignal,
    DigitalTwinScoreTranslator,
)


def make_signal(
    action: str = "study",
    normalized_score: float = 0.8,
    confidence: float = 0.7,
    risk: float = 0.1,
    uncertainty: float = 0.1,
    reason: str = "trajectory_score",
    valid: bool = True,
) -> DigitalTwinDecisionSignal:
    return DigitalTwinDecisionSignal(
        action=action,
        trajectory_score=1.5,
        normalized_score=normalized_score,
        adjustment=0.0,
        confidence=confidence,
        branch_probability=0.8,
        risk=risk,
        uncertainty=uncertainty,
        reason=reason,
        valid=valid,
        metadata={"top_k": 1},
    )


def test_positive_valid_signal_produces_positive_bounded_adjustment() -> None:
    translator = DigitalTwinScoreTranslator()
    signal = make_signal(normalized_score=0.9, confidence=0.9, risk=0.0, uncertainty=0.0)

    adjustment = translator.translate_to_planner_adjustment(signal, enabled=True, adjustment_scale=0.2, max_adjustment=0.2)

    assert adjustment.enabled is True
    assert adjustment.adjustment > 0.0
    assert adjustment.adjustment <= 0.2
    assert adjustment.reason == "trajectory_score"


def test_negative_poor_signal_reduces_or_inverts_adjustment() -> None:
    translator = DigitalTwinScoreTranslator()
    signal = make_signal(normalized_score=0.1, confidence=0.5, risk=0.0, uncertainty=0.0)

    adjustment = translator.translate_to_planner_adjustment(signal, enabled=True, adjustment_scale=0.2, max_adjustment=0.2)

    assert adjustment.adjustment < 0.1
    assert adjustment.adjustment >= 0.0


def test_high_risk_reduces_adjustment() -> None:
    translator = DigitalTwinScoreTranslator()
    low_risk = make_signal(normalized_score=0.8, confidence=0.8, risk=0.0, uncertainty=0.0)
    high_risk = make_signal(normalized_score=0.8, confidence=0.8, risk=0.9, uncertainty=0.0)

    low_adj = translator.translate_to_planner_adjustment(low_risk, enabled=True, adjustment_scale=0.2, max_adjustment=0.2)
    high_adj = translator.translate_to_planner_adjustment(high_risk, enabled=True, adjustment_scale=0.2, max_adjustment=0.2)

    assert high_adj.adjustment < low_adj.adjustment


def test_high_uncertainty_reduces_adjustment() -> None:
    translator = DigitalTwinScoreTranslator()
    low_uncertainty = make_signal(normalized_score=0.8, confidence=0.8, risk=0.0, uncertainty=0.0)
    high_uncertainty = make_signal(normalized_score=0.8, confidence=0.8, risk=0.0, uncertainty=0.9)

    low_adj = translator.translate_to_planner_adjustment(low_uncertainty, enabled=True, adjustment_scale=0.2, max_adjustment=0.2)
    high_adj = translator.translate_to_planner_adjustment(high_uncertainty, enabled=True, adjustment_scale=0.2, max_adjustment=0.2)

    assert high_adj.adjustment < low_adj.adjustment


def test_confidence_scales_adjustment() -> None:
    translator = DigitalTwinScoreTranslator()
    low_conf = make_signal(normalized_score=0.8, confidence=0.2, risk=0.0, uncertainty=0.0)
    high_conf = make_signal(normalized_score=0.8, confidence=0.9, risk=0.0, uncertainty=0.0)

    low_adj = translator.translate_to_planner_adjustment(low_conf, enabled=True, adjustment_scale=0.2, max_adjustment=0.2)
    high_adj = translator.translate_to_planner_adjustment(high_conf, enabled=True, adjustment_scale=0.2, max_adjustment=0.2)

    assert high_adj.adjustment > low_adj.adjustment


def test_adjustment_never_exceeds_bounds() -> None:
    translator = DigitalTwinScoreTranslator()
    signal = make_signal(normalized_score=1.0, confidence=1.0, risk=0.0, uncertainty=0.0)

    adjustment = translator.translate_to_planner_adjustment(signal, enabled=True, adjustment_scale=1.0, max_adjustment=0.2)

    assert adjustment.adjustment == 0.2


def test_disabled_digital_twin_returns_zero_adjustment() -> None:
    translator = DigitalTwinScoreTranslator()
    signal = make_signal()

    adjustment = translator.translate_to_planner_adjustment(signal, enabled=False, adjustment_scale=0.2, max_adjustment=0.2)

    assert adjustment.enabled is False
    assert adjustment.adjustment == 0.0


def test_invalid_signal_returns_zero_adjustment() -> None:
    translator = DigitalTwinScoreTranslator()
    invalid_signal = make_signal(valid=False, reason="disabled")

    adjustment = translator.translate_to_planner_adjustment(invalid_signal, enabled=True, adjustment_scale=0.2, max_adjustment=0.2)

    assert adjustment.enabled is False
    assert adjustment.adjustment == 0.0


def test_translate_to_planner_adjustment_is_deterministic() -> None:
    translator = DigitalTwinScoreTranslator()
    signal = make_signal(normalized_score=0.7, confidence=0.7, risk=0.2, uncertainty=0.1)

    first = translator.translate_to_planner_adjustment(signal, enabled=True, adjustment_scale=0.3, max_adjustment=0.3)
    second = translator.translate_to_planner_adjustment(signal, enabled=True, adjustment_scale=0.3, max_adjustment=0.3)

    assert first == second


def test_original_decision_signal_remains_unchanged() -> None:
    translator = DigitalTwinScoreTranslator()
    signal = make_signal(normalized_score=0.7, confidence=0.7, risk=0.2, uncertainty=0.1)
    original = signal.__dict__.copy()

    translator.translate_to_planner_adjustment(signal, enabled=True, adjustment_scale=0.3, max_adjustment=0.3)

    assert signal.__dict__ == original
