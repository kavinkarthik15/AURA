from backend.experiments.research_parameter_causal_contribution_17_7_b import (
    ParameterCausalContributionAnalyzer,
    ResearchPhase17_7_B,
)


def test_single_parameter_analysis_returns_expected_slots():
    analyzer = ParameterCausalContributionAnalyzer(seed=42)
    dataset = analyzer.generator.generate_dataset(training_size=80, held_out_size=20)
    result = analyzer.analyze_seed()

    assert result.total_events == 80
    assert len(result.single_parameter_results) == 5
    assert len(result.pairwise_results) == 4
    assert {item.intervention_name for item in result.single_parameter_results} == {
        "expected_state_bias",
        "transition_probability_bias",
        "risk_bias",
        "uncertainty",
        "confidence",
    }
    assert all(item.baseline_mae >= 0.0 for item in result.single_parameter_results)


def test_phase_runs_and_saves_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    phase = ResearchPhase17_7_B(seeds=[42])
    result = phase.run()

    assert 42 in result.seed_results
    assert result.seed_results[42].seed == 42
    assert result.seed_results[42].single_parameter_results
    assert result.seed_results[42].pairwise_results
