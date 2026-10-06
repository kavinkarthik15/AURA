from backend.experiments.research_parameter_activation_17_7_c import (
    ParameterActivationAnalyzer,
    ResearchPhase17_7_C,
)


def test_parameter_activation_analysis_has_expected_structure():
    analyzer = ParameterActivationAnalyzer(seed=42)
    result = analyzer.analyze_seed()

    assert set(result.activation_map) == {
        "expected_state_bias",
        "transition_probability_bias",
        "risk_bias",
        "uncertainty",
        "confidence",
    }
    assert result.activation_map["expected_state_bias"].is_activated is True
    assert result.activation_map["transition_probability_bias"].is_activated is False
    assert result.activation_map["risk_bias"].is_activated is False
    assert result.activation_map["uncertainty"].is_activated in {True, False}
    assert result.activation_map["confidence"].is_activated in {True, False}


def test_phase_runs_and_saves_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    phase = ResearchPhase17_7_C(seeds=[42])
    result = phase.run()

    assert 42 in result.seed_results
    assert result.seed_results[42].seed == 42
    assert set(result.seed_results[42].activation_map) == {
        "expected_state_bias",
        "transition_probability_bias",
        "risk_bias",
        "uncertainty",
        "confidence",
    }
