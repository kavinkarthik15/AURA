"""
Tests for 17.12: MG Shadow Integration Validation
"""

import pytest
from backend.experiments.research_mg_shadow_integration_17_12 import MGShadowIntegrationValidator, run_mg_shadow_validation


def test_seed_42_mg_shadow_gates_exist():
    """Test that seed 42 shadow integration validation produces valid gate results."""
    validator = MGShadowIntegrationValidator(seed=42)
    result = validator.validate_seed()

    # Verify all 10 gates exist and have valid structure
    assert result.gate_g1_legacy_identity is not None
    assert result.gate_g1_legacy_identity.gate_number == "G1"
    assert isinstance(result.gate_g1_legacy_identity.passed, bool)

    assert result.gate_g2_simulation_semantics is not None
    assert result.gate_g2_simulation_semantics.gate_number == "G2"

    assert result.gate_g3_benchmark_split is not None
    assert result.gate_g3_benchmark_split.gate_number == "G3"

    assert result.gate_g4_mg_activation is not None
    assert result.gate_g4_mg_activation.gate_number == "G4"

    assert result.gate_g5_mg_improves_all_seeds is not None
    assert result.gate_g5_mg_improves_all_seeds.gate_number == "G5"

    assert result.gate_g6_coefficient_stability is not None
    assert result.gate_g6_coefficient_stability.gate_number == "G6"

    assert result.gate_g7_improvement_agreement is not None
    assert result.gate_g7_improvement_agreement.gate_number == "G7"

    assert result.gate_g8_no_mutation is not None
    assert result.gate_g8_no_mutation.gate_number == "G8"

    assert result.gate_g9_no_regression is not None
    assert result.gate_g9_no_regression.gate_number == "G9"

    assert result.gate_g10_artifact_completeness is not None
    assert result.gate_g10_artifact_completeness.gate_number == "G10"

    # Verify metrics exist
    assert result.legacy_metrics is not None
    assert result.mg_metrics is not None
    assert result.legacy_metrics.heldout_mae > 0
    assert result.mg_metrics.heldout_mae > 0

    print("✓ Seed 42 all 10 gates exist with valid structure")


def test_five_seed_sweep_generates_shadow_artifact():
    """Test that 5-seed sweep generates complete shadow integration artifact."""
    result = run_mg_shadow_validation(seeds=[42, 123, 456, 789, 999], output_path='backend/experiments/results/research_17_12_mg_shadow_integration.json')

    assert result is not None
    assert "aggregate_summary" in result
    assert "seed_results" in result

    # Verify aggregate summary
    summary = result["aggregate_summary"]
    assert "gate_pass_counts" in summary
    assert "all_gates_full_pass" in summary
    assert "recommendation" in summary

    # Verify all seeds have results
    assert len(result["seed_results"]) == 5

    for seed in [42, 123, 456, 789, 999]:
        assert str(seed) in result["seed_results"]
        seed_result = result["seed_results"][str(seed)]
        assert "legacy_metrics" in seed_result
        assert "mg_metrics" in seed_result
        assert "gate_g1_legacy_identity" in seed_result
        assert "gate_g10_artifact_completeness" in seed_result

    print(f"✓ 5-seed sweep artifact generated: {result['aggregate_summary']['recommendation']}")
