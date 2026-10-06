from backend.experiments.research_controlled_redesign_17_9 import (
    ABLATION_MODELS,
    PRIMARY_CANDIDATES,
    ControlledRedesignAnalyzer,
    ResearchPhase17_9,
)


def test_structural_models_exist_for_seed_gate():
    assert "baseline" in PRIMARY_CANDIDATES
    assert "motivation_goals" in PRIMARY_CANDIDATES
    assert "all_three" in PRIMARY_CANDIDATES

    assert set(ABLATION_MODELS) == {"baseline", "M", "G", "B", "MG", "MB", "GB", "MGB"}


def test_seed42_numerical_and_causal_outputs_present():
    result = ControlledRedesignAnalyzer(seed=42).analyze_seed()

    assert result.seed == 42
    assert result.benchmark_invariant is True
    assert result.target_invariant is True
    assert result.simulation_semantics_invariant is True

    baseline = result.model_results["baseline"]
    mg = result.model_results["motivation_goals"]
    mgb = result.model_results["all_three"]

    assert baseline.heldout_mae >= 0.0
    assert mg.heldout_rmse >= 0.0
    assert isinstance(mgb.heldout_r2, float)
    assert isinstance(mg.prediction_delta_vs_baseline, float)

    for dim in ["motivation", "goals", "behavior"]:
        assert dim in mgb.intervention_effects


def test_phase_runs_and_writes_artifact(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    phase = ResearchPhase17_9(seeds=[42])
    output = phase.run()

    assert 42 in output.seed_results
    assert output.aggregate_summary is not None
    assert output.aggregate_summary.mean_metrics_by_model
