from backend.experiments.research_mg_validation_17_11 import (
    MotivationGoalsValidator,
    run_mg_validation,
)


def test_seed_42_mg_validation_gates_exist():
    result = MotivationGoalsValidator(seed=42).validate_seed()

    assert result.seed == 42
    assert result.metrics["Legacy"].heldout_mae >= 0.0
    assert result.metrics["M"].heldout_mae >= 0.0
    assert result.metrics["G"].heldout_mae >= 0.0
    assert result.metrics["MG"].heldout_mae >= 0.0
    assert result.gate1_legacy_invariance is not None
    assert result.gate2_motivation_activation is not None
    assert result.gate3_goals_activation is not None
    assert result.gate4_mg_improves_legacy is not None
    assert result.gate5_mg_improves_singletons is not None
    assert result.gate6_coefficient_stability is not None
    assert result.gate7_no_simulation_contamination is not None


def test_five_seed_sweep_generates_mg_validation_artifact():
    path = "backend/experiments/results/research_17_11_mg_validation.json"
    result = run_mg_validation(seeds=[42, 123, 456, 789, 999], output_path=path)

    assert result["total_seeds"] == 5
    assert "42" in result["seed_results"]
    assert "999" in result["seed_results"]
    assert "aggregate_summary" in result
    assert "mg_is_stable_and_reproducible" in result["aggregate_summary"]
