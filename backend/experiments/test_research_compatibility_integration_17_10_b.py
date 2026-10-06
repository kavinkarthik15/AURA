from backend.experiments.research_compatibility_integration_17_10_b import (
    MODEL_FEATURES,
    CompatibilityIntegrationExperiment,
    run_compatibility_integration_experiment,
)


def test_model_matrix_matches_expected_candidates():
    assert set(MODEL_FEATURES) == {"Legacy", "M", "G", "B", "M+G", "M+B", "G+B", "M+G+B"}


def test_seed42_gate_invariants():
    seed_result = CompatibilityIntegrationExperiment(seed=42).analyze_seed()

    assert seed_result.seed == 42
    assert seed_result.gate1_integration is True
    assert seed_result.gate2_legacy_equivalence is True
    assert seed_result.gate6_no_simulation_contamination is True

    assert "Legacy" in seed_result.metrics
    assert "M+G" in seed_result.metrics
    assert "M+G+B" in seed_result.metrics

    assert seed_result.metrics["Legacy"].heldout_mae >= 0.0
    assert seed_result.metrics["M+G"].heldout_mae >= 0.0
    assert seed_result.metrics["M+G+B"].heldout_mae >= 0.0


def test_five_seed_artifact_generation(tmp_path):
    output_path = tmp_path / "research_17_10_b_compatibility_integration.json"
    result = run_compatibility_integration_experiment(seeds=[42, 123, 456, 789, 999], output_path=output_path)

    assert output_path.exists()
    assert result["total_seeds"] == 5
    assert result["seed_results"]["42"]["gate2_legacy_equivalence"] is True
    assert result["aggregate_summary"]["gate2_legacy_equivalence_pass_count"] == 5


def test_objective_improvement_and_incremental_gain_direction():
    result = run_compatibility_integration_experiment(seeds=[42], output_path=None)
    seed_result = result["seed_results"]["42"]

    legacy_mae = seed_result["metrics"]["Legacy"]["heldout_mae"]
    mg_mae = seed_result["metrics"]["M+G"]["heldout_mae"]
    mgb_mae = seed_result["metrics"]["M+G+B"]["heldout_mae"]

    assert mg_mae < legacy_mae
    assert mgb_mae < mg_mae
