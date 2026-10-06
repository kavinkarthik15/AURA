from backend.experiments.research_behavior_diagnostics_17_10_c import (
    BehaviorDiagnosticExperiment,
    BEHAVIOR_VARIANTS,
    run_behavior_diagnostics,
)


def test_seed_42_behavior_diagnostics_exist_and_compare_mg_vs_mgb():
    result = BehaviorDiagnosticExperiment(seed=42).analyze_seed()

    assert result.seed == 42
    assert "MG" in result.model_metrics
    assert "MGB" in result.model_metrics
    assert result.mg_vs_mgb["mae_mg"] >= 0.0
    assert result.mg_vs_mgb["mae_mgb"] >= 0.0
    assert "mgb_minus_mg" in result.mg_vs_mgb
    assert result.by_category
    assert result.by_action
    assert result.by_skill
    assert set(BEHAVIOR_VARIANTS) == {"original", "normalized", "binary", "action_frequency", "state_transition_based"}


def test_five_seed_sweep_generates_artifact():
    path = "backend/experiments/results/research_17_10_c_behavior_diagnostics.json"
    result = run_behavior_diagnostics(seeds=[42, 123, 456, 789, 999], output_path=path)

    assert result["total_seeds"] == 5
    assert "42" in result["seed_results"]
    assert "999" in result["seed_results"]
    assert result["aggregate_summary"]["mean_mg_mae"] >= 0.0
    assert result["aggregate_summary"]["mean_mgb_mae"] >= 0.0
