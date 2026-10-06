import json
from pathlib import Path

from backend.experiments.research_compatibility_layer_17_10_a import (
    CompatibilityConfig,
    CompatibilityLayer,
    build_legacy_simulation_output,
    run_compatibility_experiment,
)

SEEDS = [42, 123, 456, 789, 999]


def test_disabled_layer_is_exact_equivalence_for_seed_42():
    legacy = build_legacy_simulation_output(42)
    compatibility = CompatibilityLayer.wrap(legacy, CompatibilityConfig(enabled=False))

    assert compatibility is legacy
    assert compatibility == legacy
    assert compatibility["predicted_future_state"] == legacy["predicted_future_state"]
    assert compatibility["prediction_vectors"] == legacy["prediction_vectors"]
    assert compatibility["mae"] == legacy["mae"]
    assert compatibility["rmse"] == legacy["rmse"]
    assert compatibility["r2"] == legacy["r2"]
    assert compatibility["objective_value"] == legacy["objective_value"]
    assert compatibility["target_values"] == legacy["target_values"]
    assert compatibility["benchmark_split"] == legacy["benchmark_split"]
    assert compatibility["deterministic_output"] == legacy["deterministic_output"]
    assert compatibility["simulation_semantics"] == legacy["simulation_semantics"]


def test_disabled_layer_is_equivalent_for_all_required_seeds():
    for seed in SEEDS:
        legacy = build_legacy_simulation_output(seed)
        compatibility = CompatibilityLayer.wrap(legacy, CompatibilityConfig())

        assert compatibility is legacy
        assert compatibility == legacy
        assert compatibility["predicted_future_state"] == legacy["predicted_future_state"]
        assert compatibility["prediction_vectors"] == legacy["prediction_vectors"]
        assert compatibility["mae"] == legacy["mae"]
        assert compatibility["rmse"] == legacy["rmse"]
        assert compatibility["r2"] == legacy["r2"]
        assert compatibility["objective_value"] == legacy["objective_value"]
        assert compatibility["target_values"] == legacy["target_values"]
        assert compatibility["benchmark_split"] == legacy["benchmark_split"]
        assert compatibility["deterministic_output"] == legacy["deterministic_output"]
        assert compatibility["simulation_semantics"] == legacy["simulation_semantics"]


def test_enabled_configuration_is_diagnostic_only():
    legacy = build_legacy_simulation_output(42)
    compatibility = CompatibilityLayer.wrap(
        legacy,
        CompatibilityConfig(
            enabled=True,
            use_motivation=True,
            use_goals=True,
            use_behavior=True,
        ),
    )

    assert compatibility["legacy_prediction"] == legacy
    assert compatibility["predicted_future_state"] == legacy["predicted_future_state"]
    assert compatibility["predictive_representation"]["motivation"] >= 0.0
    assert compatibility["predictive_representation"]["goals"] >= 0.0
    assert compatibility["predictive_representation"]["behavior"] >= 0.0


def test_experiment_writes_artifact(tmp_path):
    output_path = tmp_path / "research_17_10_a_compatibility_layer.json"
    result = run_compatibility_experiment(seeds=[42], output_path=output_path)

    assert output_path.exists()
    assert result["total_seeds"] == 1
    assert result["seed_results"]["42"]["disabled_compatibility_matches_legacy"] is True

    with open(output_path, "r", encoding="utf-8") as handle:
        saved = json.load(handle)
    assert saved["seed_results"]["42"]["disabled_compatibility_matches_legacy"] is True
