from backend.planning.candidate_selector import CandidateActionResult
from backend.planning.digital_twin_score_translator import DigitalTwinScoreTranslator


def test_translate_valid_selection_to_decision_signal() -> None:
    selection = CandidateActionResult(
        action="study",
        score=1.5,
        probability=0.8,
        risk=0.2,
        uncertainty=0.1,
        selection_reason="trajectory_score",
        metadata={"top_k": 3},
    )
    translator = DigitalTwinScoreTranslator(adjustment_scale=0.2)

    signal = translator.translate(selection)

    assert signal.action == "study"
    assert signal.valid is True
    assert 0.0 <= signal.normalized_score <= 1.0
    assert signal.confidence == 0.8
    assert signal.adjustment != 0.0
    assert signal.reason == "trajectory_score"
    assert signal.metadata == {"top_k": 3}


def test_translate_invalid_selection_returns_invalid_signal() -> None:
    selection = CandidateActionResult(
        action=None,
        score=0.0,
        probability=0.0,
        risk=0.0,
        uncertainty=0.0,
        selection_reason="disabled",
    )
    translator = DigitalTwinScoreTranslator()

    signal = translator.translate(selection)

    assert signal.valid is False
    assert signal.adjustment == 0.0
    assert signal.normalized_score == 0.0
    assert signal.confidence == 0.0
    assert signal.reason == "disabled"


def test_translate_none_selection_returns_invalid_signal() -> None:
    translator = DigitalTwinScoreTranslator()
    signal = translator.translate(None)

    assert signal.valid is False
    assert signal.action is None
    assert signal.reason == "no_selection"
    assert signal.adjustment == 0.0
    assert signal.normalized_score == 0.0
