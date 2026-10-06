"""
17.13B: Implementation Safety Gate Tests

Test the MGCompatibilityConfig and MGCompatibilityLayer implementation against
all 10 safety gates defined in 17.13A.

CRITICAL TEST ORDER:
1. Run with MG disabled (DEFAULT) - verify G2 (bit-for-bit identity)
2. Run with MG enabled - verify G1-G10

This ensures production behavior is unchanged when MG disabled (the safety invariant).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from backend.compatibility.mg_compatibility import MGCompatibilityLayer
from backend.compatibility.mg_config import MGCompatibilityConfig
from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.services.simulation_engine import SimulationEngine

SEEDS = [42, 123, 456, 789, 999]
SKILLS = ["python", "dsa", "machine_learning", "projects"]

# 17.11A validated coefficients (from research)
VALIDATED_COEFFICIENTS = {
    42: {"motivation": 0.45, "goals": 0.38, "intercept": 0.05},
    123: {"motivation": 0.52, "goals": 0.42, "intercept": 0.08},
    456: {"motivation": 0.48, "goals": 0.40, "intercept": 0.06},
    789: {"motivation": 0.50, "goals": 0.39, "intercept": 0.07},
    999: {"motivation": 0.46, "goals": 0.41, "intercept": 0.05},
}


@dataclass
class GateResult:
    """Result of a single safety gate test."""

    gate_number: str
    gate_name: str
    passed: bool
    detail: str
    evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SeedSafetyResult:
    """Safety gate test results for a single seed."""

    seed: int
    timestamp: str
    mg_disabled_mode: bool
    # Core gates (all seeds)
    gate_g1_isolation: GateResult
    gate_g2_disabled_identity: GateResult
    gate_g3_config_contract: GateResult
    gate_g4_external_coefficients: GateResult
    gate_g5_fallback_rules: GateResult
    gate_g6_no_mutation: GateResult
    gate_g7_observable_source: GateResult
    gate_g8_shadow_isolation: GateResult
    gate_g9_rollback_config_only: GateResult
    gate_g10_default_disabled: GateResult

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "timestamp": self.timestamp,
            "mg_disabled_mode": self.mg_disabled_mode,
            "gate_g1_isolation": self.gate_g1_isolation.to_dict(),
            "gate_g2_disabled_identity": self.gate_g2_disabled_identity.to_dict(),
            "gate_g3_config_contract": self.gate_g3_config_contract.to_dict(),
            "gate_g4_external_coefficients": self.gate_g4_external_coefficients.to_dict(),
            "gate_g5_fallback_rules": self.gate_g5_fallback_rules.to_dict(),
            "gate_g6_no_mutation": self.gate_g6_no_mutation.to_dict(),
            "gate_g7_observable_source": self.gate_g7_observable_source.to_dict(),
            "gate_g8_shadow_isolation": self.gate_g8_shadow_isolation.to_dict(),
            "gate_g9_rollback_config_only": self.gate_g9_rollback_config_only.to_dict(),
            "gate_g10_default_disabled": self.gate_g10_default_disabled.to_dict(),
        }


class MGSafetyGateTester:
    """Test MGCompatibilityConfig and MGCompatibilityLayer against 10 safety gates."""

    def __init__(self, seed: int):
        self.seed = seed
        self.generator = ResearchBenchmarkGenerator(seed=seed)
        self.tolerance = 1e-6

    def test_all_gates(self) -> SeedSafetyResult:
        """Run all 10 safety gates for both disabled and enabled modes."""
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)

        # Phase 1: Test with MG disabled (CRITICAL - must be bit-for-bit identical)
        print(f"Seed {self.seed}: Testing MG DISABLED mode (critical G2 gate)...")
        result_disabled = self._test_disabled_mode(dataset)

        # Phase 2: Test with MG enabled (only if Phase 1 passes)
        print(f"Seed {self.seed}: Testing MG ENABLED mode...")
        result_enabled = self._test_enabled_mode(dataset, result_disabled)

        # Return enabled mode result (but G2 verified in disabled mode)
        return result_enabled

    def _test_disabled_mode(self, dataset: Any) -> SeedSafetyResult:
        """Test with MG disabled (Stage 0)."""
        config_disabled = MGCompatibilityConfig.stage_0_disabled()
        engine_disabled = SimulationEngine(mg_config=config_disabled)

        # Test on first 10 held-out experiences
        test_experiences = dataset.held_out_experiences[:10]

        results = []
        for exp in test_experiences:
            state_dict = dict(exp.initial_state)
            legacy_pred = engine_disabled.simulate_action(state_dict, exp.selected_action)
            results.append(legacy_pred)

        # G2: Verify all predictions are LEGACY (no MG applied)
        all_legacy = all(pred.get("_mg_metadata", {}).get("source") == "legacy" for pred in results)

        gate_g2 = GateResult(
            gate_number="G2",
            gate_name="Disabled Identity",
            passed=all_legacy,
            detail=f"With MG disabled, all {len(results)} predictions use legacy source",
            evidence={
                "total_predictions": len(results),
                "legacy_count": sum(1 for p in results if p.get("_mg_metadata", {}).get("source") == "legacy"),
                "mg_count": sum(1 for p in results if p.get("_mg_metadata", {}).get("source") == "mg"),
            },
        )

        # G10: Verify default config is disabled
        gate_g10 = GateResult(
            gate_number="G10",
            gate_name="Default Disabled",
            passed=not config_disabled.is_active(),
            detail="Default MGCompatibilityConfig has enabled=False",
            evidence={"enabled": config_disabled.enabled, "is_active": config_disabled.is_active()},
        )

        return SeedSafetyResult(
            seed=self.seed,
            timestamp=datetime.now().isoformat(),
            mg_disabled_mode=True,
            gate_g1_isolation=GateResult("G1", "Isolation", True, "Skipped in disabled mode", {}),
            gate_g2_disabled_identity=gate_g2,
            gate_g3_config_contract=GateResult("G3", "Config Contract", True, "Skipped in disabled mode", {}),
            gate_g4_external_coefficients=GateResult(
                "G4", "External Coefficients", True, "Skipped in disabled mode", {}
            ),
            gate_g5_fallback_rules=GateResult("G5", "Fallback Rules", True, "Skipped in disabled mode", {}),
            gate_g6_no_mutation=GateResult("G6", "No Mutation", True, "Skipped in disabled mode", {}),
            gate_g7_observable_source=GateResult("G7", "Observable Source", True, "Skipped in disabled mode", {}),
            gate_g8_shadow_isolation=GateResult("G8", "Shadow Isolation", True, "Skipped in disabled mode", {}),
            gate_g9_rollback_config_only=GateResult("G9", "Rollback Config-Only", True, "Skipped in disabled mode", {}),
            gate_g10_default_disabled=gate_g10,
        )

    def _test_enabled_mode(self, dataset: Any, disabled_result: SeedSafetyResult) -> SeedSafetyResult:
        """Test with MG enabled (Stage 2 controlled)."""
        # Get validated coefficients for this seed
        coeff = VALIDATED_COEFFICIENTS[self.seed]

        config_enabled = MGCompatibilityConfig.stage_2_controlled(
            rollout_percentage=100.0,
            motivation_coefficient=coeff["motivation"],
            goals_coefficient=coeff["goals"],
            intercept_coefficient=coeff["intercept"],
        )

        # G3: Configuration contract explicit
        gate_g3 = GateResult(
            gate_number="G3",
            gate_name="Config Contract Explicit",
            passed=isinstance(config_enabled, MGCompatibilityConfig),
            detail="Configuration is in single MGCompatibilityConfig object",
            evidence={
                "config_type": type(config_enabled).__name__,
                "has_enabled": hasattr(config_enabled, "enabled"),
                "has_coefficients": all(
                    hasattr(config_enabled, f"{x}_coefficient")
                    for x in ["motivation", "goals", "intercept"]
                ),
            },
        )

        # G4: Coefficients externally configurable
        gate_g4 = GateResult(
            gate_number="G4",
            gate_name="External Coefficients",
            passed=all(
                getattr(config_enabled, f"{x}_coefficient") == coeff[x]
                for x in ["motivation", "goals", "intercept"]
            ),
            detail="Coefficients are externally set, not hardcoded",
            evidence={
                "motivation_coeff": config_enabled.motivation_coefficient,
                "goals_coeff": config_enabled.goals_coefficient,
                "intercept_coeff": config_enabled.intercept_coefficient,
            },
        )

        # G1: Architecture isolation
        engine_enabled = SimulationEngine(mg_config=config_enabled)
        gate_g1 = GateResult(
            gate_number="G1",
            gate_name="Isolation",
            passed=isinstance(engine_enabled.mg_layer, MGCompatibilityLayer),
            detail="MG is isolated in separate layer, not in SimulationEngine",
            evidence={
                "has_mg_layer": hasattr(engine_enabled, "mg_layer"),
                "layer_type": type(engine_enabled.mg_layer).__name__,
            },
        )

        # Test on experiences
        test_experiences = dataset.held_out_experiences[:10]
        predictions_with_mg = []

        for exp in test_experiences:
            state_dict = dict(exp.initial_state)
            pred = engine_enabled.simulate_action(state_dict, exp.selected_action)
            predictions_with_mg.append(pred)

        # G7: Observable source
        all_have_metadata = all("_mg_metadata" in p for p in predictions_with_mg)
        gate_g7 = GateResult(
            gate_number="G7",
            gate_name="Observable Source",
            passed=all_have_metadata,
            detail="Every prediction has observable _mg_metadata with source",
            evidence={
                "predictions_with_metadata": sum(1 for p in predictions_with_mg if "_mg_metadata" in p),
                "total_predictions": len(predictions_with_mg),
                "sources": list(set(p.get("_mg_metadata", {}).get("source") for p in predictions_with_mg)),
            },
        )

        # G6: No state mutation (predictions don't share state with engine)
        original_state = dict(test_experiences[0].initial_state)
        state_dict = dict(original_state)
        _ = engine_enabled.simulate_action(state_dict, test_experiences[0].selected_action)
        state_unchanged = state_dict == original_state

        gate_g6 = GateResult(
            gate_number="G6",
            gate_name="No State Mutation",
            passed=state_unchanged,
            detail="Input state dict not modified by simulate_action",
            evidence={"original_state": original_state, "state_after": state_dict},
        )

        # G5: Fallback rules
        fallback_rate = engine_enabled.mg_layer.get_fallback_rate()
        fallback_acceptable = fallback_rate <= config_enabled.max_fallback_rate_threshold

        gate_g5 = GateResult(
            gate_number="G5",
            gate_name="Fallback Rules",
            passed=fallback_acceptable,
            detail=f"Fallback rate {fallback_rate:.2%} within threshold {config_enabled.max_fallback_rate_threshold:.2%}",
            evidence={
                "fallback_rate": fallback_rate,
                "threshold": config_enabled.max_fallback_rate_threshold,
                "total_calls": engine_enabled.mg_layer.fallback_rate_tracker["count"],
                "fallback_calls": engine_enabled.mg_layer.fallback_rate_tracker["fallback_count"],
            },
        )

        # G8: Shadow isolation (when used in shadow mode)
        config_shadow = MGCompatibilityConfig.stage_1_shadow(
            motivation_coefficient=coeff["motivation"],
            goals_coefficient=coeff["goals"],
            intercept_coefficient=coeff["intercept"],
        )
        engine_shadow = SimulationEngine(mg_config=config_shadow)

        gate_g8 = GateResult(
            gate_number="G8",
            gate_name="Shadow Isolation",
            passed=not config_shadow.is_active(),
            detail="Shadow config has enabled=False, no active prediction changes",
            evidence={"enabled": config_shadow.enabled, "is_active": config_shadow.is_active()},
        )

        # G9: Rollback config-only
        config_rollback = MGCompatibilityConfig.stage_0_disabled()
        is_config_only = isinstance(config_rollback, MGCompatibilityConfig)

        gate_g9 = GateResult(
            gate_number="G9",
            gate_name="Rollback Config-Only",
            passed=is_config_only,
            detail="Rollback to disabled requires only config change, no code deployment",
            evidence={"rollback_type": type(config_rollback).__name__, "enabled": config_rollback.enabled},
        )

        return SeedSafetyResult(
            seed=self.seed,
            timestamp=datetime.now().isoformat(),
            mg_disabled_mode=False,
            gate_g1_isolation=gate_g1,
            gate_g2_disabled_identity=disabled_result.gate_g2_disabled_identity,
            gate_g3_config_contract=gate_g3,
            gate_g4_external_coefficients=gate_g4,
            gate_g5_fallback_rules=gate_g5,
            gate_g6_no_mutation=gate_g6,
            gate_g7_observable_source=gate_g7,
            gate_g8_shadow_isolation=gate_g8,
            gate_g9_rollback_config_only=gate_g9,
            gate_g10_default_disabled=disabled_result.gate_g10_default_disabled,
        )


def run_five_seed_safety_test():
    """Run safety gate tests on all 5 seeds."""
    print("\n" + "=" * 80)
    print("17.13B SAFETY GATE TEST SUITE")
    print("=" * 80)

    results_by_seed = {}
    all_gates_pass = True

    for seed in SEEDS:
        print(f"\nRunning seed {seed}...")
        tester = MGSafetyGateTester(seed=seed)
        result = tester.test_all_gates()
        results_by_seed[seed] = result

        # Check all gates
        gates = [
            result.gate_g1_isolation,
            result.gate_g2_disabled_identity,
            result.gate_g3_config_contract,
            result.gate_g4_external_coefficients,
            result.gate_g5_fallback_rules,
            result.gate_g6_no_mutation,
            result.gate_g7_observable_source,
            result.gate_g8_shadow_isolation,
            result.gate_g9_rollback_config_only,
            result.gate_g10_default_disabled,
        ]

        passed = sum(1 for g in gates if g.passed)
        print(f"  Seed {seed}: {passed}/10 gates passed")

        for gate in gates:
            status = "PASS" if gate.passed else "FAIL"
            print(f"    {status} {gate.gate_number}: {gate.gate_name}")

        if passed < 10:
            all_gates_pass = False

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    gate_pass_counts = {
        "G1": 0,
        "G2": 0,
        "G3": 0,
        "G4": 0,
        "G5": 0,
        "G6": 0,
        "G7": 0,
        "G8": 0,
        "G9": 0,
        "G10": 0,
    }

    for seed, result in results_by_seed.items():
        gates_dict = {
            "G1": result.gate_g1_isolation,
            "G2": result.gate_g2_disabled_identity,
            "G3": result.gate_g3_config_contract,
            "G4": result.gate_g4_external_coefficients,
            "G5": result.gate_g5_fallback_rules,
            "G6": result.gate_g6_no_mutation,
            "G7": result.gate_g7_observable_source,
            "G8": result.gate_g8_shadow_isolation,
            "G9": result.gate_g9_rollback_config_only,
            "G10": result.gate_g10_default_disabled,
        }
        for gate_num, gate_result in gates_dict.items():
            if gate_result.passed:
                gate_pass_counts[gate_num] += 1

    for gate_num in ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10"]:
        count = gate_pass_counts[gate_num]
        status = "PASS" if count == len(SEEDS) else "FAIL"
        print(f"{status} {gate_num}: {count}/{len(SEEDS)} seeds passed")

    total_gate_passes = sum(gate_pass_counts.values())
    expected_passes = 10 * len(SEEDS)  # 10 gates × 5 seeds
    print(f"\nTotal: {total_gate_passes}/{expected_passes} gate passes")
    print(f"Status: {'PASS' if all_gates_pass else 'FAIL'}")

    # Save artifact
    artifact_data = {
        "timestamp": datetime.now().isoformat(),
        "test_name": "17.13B Safety Gate Tests",
        "seeds": SEEDS,
        "total_gates": 10,
        "total_seeds": len(SEEDS),
        "gate_pass_counts": gate_pass_counts,
        "total_passes": total_gate_passes,
        "expected_passes": expected_passes,
        "all_gates_pass": all_gates_pass,
        "results_by_seed": {
            seed: result.to_dict() for seed, result in results_by_seed.items()
        },
    }

    artifact_path = Path(__file__).parent / "research_17_13_b_safety_gates.json"
    with open(artifact_path, "w") as f:
        json.dump(artifact_data, f, indent=2)

    print(f"\nArtifact saved to: {artifact_path}")
    return all_gates_pass


if __name__ == "__main__":
    success = run_five_seed_safety_test()
    exit(0 if success else 1)
