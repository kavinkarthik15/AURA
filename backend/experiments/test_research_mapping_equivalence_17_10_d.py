from backend.experiments.research_mapping_equivalence_17_10_d import (
    MappingEquivalenceExperiment,
    run_mapping_equivalence_experiment,
)


def test_seed_42_mapping_equivalence_gates_exist():
    result = MappingEquivalenceExperiment(seed=42).analyze_seed()

    assert result.seed == 42
    assert result.mae_legacy >= 0.0
    assert result.mae_mg_17_9_mapping >= 0.0
    assert result.mae_mgb_17_9_mapping >= 0.0
    assert result.gate1_mapping_equivalence is not None
    assert result.gate2_legacy_invariance is not None
    assert result.gate3_mgb_reproduction is not None
    assert result.gate4_incremental_behavior is not None
    assert result.gate5_causal_activation is not None


def test_five_seed_sweep_generates_mapping_equivalence_artifact():
    path = "backend/experiments/results/research_17_10_d_mapping_equivalence.json"
    result = run_mapping_equivalence_experiment(seeds=[42, 123, 456, 789, 999], output_path=path)

    assert result["total_seeds"] == 5
    assert "42" in result["seed_results"]
    assert "999" in result["seed_results"]
    assert "aggregate_summary" in result
    assert "overall_17_9_reproduction" in result["aggregate_summary"]
