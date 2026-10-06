from backend.experiments.research_minimal_structure_17_8_c import (
    CANDIDATE_MODELS,
    MinimalStructureAnalyzer,
    ResearchPhase17_8_C,
)


def test_candidate_model_set_contains_required_minimality_rows():
    names = {m["name"] for m in CANDIDATE_MODELS}
    required = {
        "current_bias_only",
        "plus_motivation",
        "plus_goals",
        "plus_behavior",
        "motivation_goals",
        "motivation_behavior",
        "goals_behavior",
        "all_three",
        "aggregate_signal",
        "minimal_linear",
    }
    assert required.issubset(names)


def test_seed42_analysis_produces_gate_and_metrics():
    analyzer = MinimalStructureAnalyzer(seed=42)
    result = analyzer.analyze_seed()

    assert result.total_events_train == 80
    assert result.total_events_heldout == 20
    assert result.baseline_model == "current_bias_only"
    assert "current_bias_only" in result.candidate_metrics
    assert "minimal_linear" in result.candidate_metrics

    baseline = result.candidate_metrics["current_bias_only"]
    assert baseline.parameter_count == 1
    assert baseline.delta_mae_vs_baseline == 0.0


def test_phase_runs_and_saves_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    phase = ResearchPhase17_8_C(seeds=[42])
    result = phase.run()

    assert 42 in result.seed_results
    assert result.seed_results[42].seed == 42
    assert result.seed_results[42].candidate_metrics
