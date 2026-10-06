"""
Phase 3: Disabled-Mode Equivalence Experiment

Strict backward-compatibility check for 17.13B.

Decision rule:
    Pre-17.13 output == 17.13B / MG disabled output
for all five seeds.

This is intentionally stricter than G2: it validates system-level invariance,
not only the MG layer's fallback behavior.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from backend.compatibility.mg_config import MGCompatibilityConfig
from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.services.simulation_engine import SimulationEngine

SEEDS = [42, 123, 456, 789, 999]
TOLERANCE = 1e-9


@dataclass
class SeedComparisonResult:
    seed: int
    dataset_id: str
    legacy_predictions: int
    disabled_predictions: int
    identical_core_predictions: bool
    identical_current_state: bool
    identical_future_state: bool
    identical_objective_values: bool
    identical_benchmark_split: bool
    no_mg_correction_applied: bool
    metadata_source_is_legacy: bool
    differences: List[str]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _legacy_simulate_action(engine: SimulationEngine, current_state: Dict[str, int], action: str) -> Dict[str, Any]:
    """Replicate the exact pre-17.13 prediction path without MG hooks."""
    predicted_growth = engine.transition_engine.predict_skill_growth(current_state, action)
    predicted_success = engine.transition_engine.predict_success_probability(current_state, action)

    future_state = dict(current_state)
    for skill, gain in predicted_growth.items():
        future_state[skill] = int(current_state.get(skill, 0) + gain)

    confidence = max(0.0, min(1.0, 0.5 + predicted_success * 0.4))
    if engine.calibration_parameters is not None:
        future_state, confidence = engine._apply_calibration_bias(future_state, confidence)

    expected_outcome = engine._classify_outcome(predicted_success)
    return {
        "current_state": dict(current_state),
        "predicted_future_state": future_state,
        "confidence": round(confidence, 2),
        "expected_outcome": expected_outcome,
    }


def _strip_metadata(prediction: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(prediction)
    result.pop("_mg_metadata", None)
    return result


def _assert_equal_or_tolerant(left: Any, right: Any, tol: float = TOLERANCE) -> bool:
    if isinstance(left, dict) and isinstance(right, dict):
        if left.keys() != right.keys():
            return False
        for key in left:
            if not _assert_equal_or_tolerant(left[key], right[key], tol):
                return False
        return True

    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) <= tol

    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(_assert_equal_or_tolerant(a, b, tol) for a, b in zip(left, right))

    return left == right


def _compare_prediction_pair(legacy_prediction: Dict[str, Any], disabled_prediction: Dict[str, Any]) -> Dict[str, Any]:
    legacy_core = _strip_metadata(legacy_prediction)
    disabled_core = _strip_metadata(disabled_prediction)

    metadata = disabled_prediction.get("_mg_metadata", {})
    comparison = {
        "identical_core_predictions": _assert_equal_or_tolerant(legacy_core, disabled_core),
        "identical_current_state": _assert_equal_or_tolerant(
            legacy_prediction.get("current_state", {}),
            disabled_prediction.get("current_state", {}),
        ),
        "identical_future_state": _assert_equal_or_tolerant(
            legacy_prediction.get("predicted_future_state", {}),
            disabled_prediction.get("predicted_future_state", {}),
        ),
        "identical_objective_values": _assert_equal_or_tolerant(
            legacy_prediction.get("expected_outcome"),
            disabled_prediction.get("expected_outcome"),
        ),
        "no_mg_correction_applied": (
            metadata.get("source") == "legacy"
            and metadata.get("correction_applied") is False
            and _assert_equal_or_tolerant(
                legacy_prediction.get("predicted_future_state", {}),
                disabled_prediction.get("predicted_future_state", {}),
            )
        ),
        "metadata_source_is_legacy": metadata.get("source") == "legacy",
        "metadata_correction_applied": metadata.get("correction_applied", False),
    }
    return comparison


def run_seed_equivalence(seed: int) -> SeedComparisonResult:
    generator = ResearchBenchmarkGenerator(seed=seed)
    dataset = generator.generate_dataset(training_size=80, held_out_size=20)

    legacy_engine = SimulationEngine()
    disabled_config = MGCompatibilityConfig(
        enabled=False,
        use_motivation=False,
        use_goals=False,
        rollout_percentage=0.0,
        fallback_enabled=True,
        fallback_on_invalid_signals=True,
        fallback_on_computation_error=True,
        fallback_on_coefficient_drift=True,
        emit_diagnostic_metadata=True,
        log_fallback_events=True,
    )
    disabled_engine = SimulationEngine(mg_config=disabled_config)

    differences: List[str] = []
    per_experience_checks: List[Dict[str, Any]] = []

    for idx, experience in enumerate(dataset.held_out_experiences):
        state = dict(experience.initial_state)
        legacy_prediction = _legacy_simulate_action(legacy_engine, state, experience.selected_action)
        disabled_prediction = disabled_engine.simulate_action(state, experience.selected_action)
        comparison = _compare_prediction_pair(legacy_prediction, disabled_prediction)
        per_experience_checks.append(
            {
                "experience_id": experience.experience_id,
                "selected_action": experience.selected_action,
                "comparison": comparison,
            }
        )

        if not comparison["identical_core_predictions"]:
            differences.append(f"experience {idx}: core prediction mismatch")
        if not comparison["identical_current_state"]:
            differences.append(f"experience {idx}: current_state mismatch")
        if not comparison["identical_future_state"]:
            differences.append(f"experience {idx}: predicted_future_state mismatch")
        if not comparison["identical_objective_values"]:
            differences.append(f"experience {idx}: expected_outcome mismatch")
        if not comparison["no_mg_correction_applied"]:
            differences.append(f"experience {idx}: MG correction or source not properly disabled")
        if not comparison["metadata_source_is_legacy"]:
            differences.append(f"experience {idx}: metadata source not legacy")

    benchmark_split_identical = (
        len(dataset.training_experiences) == 80
        and len(dataset.held_out_experiences) == 20
        and dataset.dataset_id == f"research_benchmark_v1_seed_{seed}"
    )

    all_identical = (
        all(check["comparison"]["identical_core_predictions"] for check in per_experience_checks)
        and all(check["comparison"]["identical_current_state"] for check in per_experience_checks)
        and all(check["comparison"]["identical_future_state"] for check in per_experience_checks)
        and all(check["comparison"]["identical_objective_values"] for check in per_experience_checks)
        and all(check["comparison"]["no_mg_correction_applied"] for check in per_experience_checks)
        and all(check["comparison"]["metadata_source_is_legacy"] for check in per_experience_checks)
        and benchmark_split_identical
    )

    summary = {
        "seed": seed,
        "dataset_id": dataset.dataset_id,
        "train_size": len(dataset.training_experiences),
        "held_out_size": len(dataset.held_out_experiences),
        "benchmark_split_identical": benchmark_split_identical,
        "all_identical": all_identical,
        "experience_checks": per_experience_checks,
    }

    return SeedComparisonResult(
        seed=seed,
        dataset_id=dataset.dataset_id,
        legacy_predictions=len(dataset.held_out_experiences),
        disabled_predictions=len(dataset.held_out_experiences),
        identical_core_predictions=all(check["comparison"]["identical_core_predictions"] for check in per_experience_checks),
        identical_current_state=all(check["comparison"]["identical_current_state"] for check in per_experience_checks),
        identical_future_state=all(check["comparison"]["identical_future_state"] for check in per_experience_checks),
        identical_objective_values=all(check["comparison"]["identical_objective_values"] for check in per_experience_checks),
        identical_benchmark_split=benchmark_split_identical,
        no_mg_correction_applied=all(check["comparison"]["no_mg_correction_applied"] for check in per_experience_checks),
        metadata_source_is_legacy=all(check["comparison"]["metadata_source_is_legacy"] for check in per_experience_checks),
        differences=differences,
        summary=summary,
    )


def run_phase_3_disabled_equivalence() -> bool:
    print("\n" + "=" * 80)
    print("PHASE 3: DISABLED-MODE EQUIVALENCE")
    print("=" * 80)

    results: List[SeedComparisonResult] = []
    all_pass = True

    for seed in SEEDS:
        result = run_seed_equivalence(seed)
        results.append(result)

        status = "PASS" if (
            result.identical_core_predictions
            and result.identical_current_state
            and result.identical_future_state
            and result.identical_objective_values
            and result.identical_benchmark_split
            and result.no_mg_correction_applied
            and result.metadata_source_is_legacy
        ) else "FAIL"

        print(f"Seed {seed}: {status}")
        print(f"  core predictions identical: {result.identical_core_predictions}")
        print(f"  current state identical: {result.identical_current_state}")
        print(f"  future state identical: {result.identical_future_state}")
        print(f"  objective values identical: {result.identical_objective_values}")
        print(f"  benchmark split identical: {result.identical_benchmark_split}")
        print(f"  no MG correction applied: {result.no_mg_correction_applied}")
        print(f"  metadata source is legacy: {result.metadata_source_is_legacy}")

        if result.differences:
            print(f"  differences: {result.differences[:3]}")

        all_pass = all_pass and (
            result.identical_core_predictions
            and result.identical_current_state
            and result.identical_future_state
            and result.identical_objective_values
            and result.identical_benchmark_split
            and result.no_mg_correction_applied
            and result.metadata_source_is_legacy
        )

    artifact = {
        "timestamp": datetime.now().isoformat(),
        "test_name": "17.13B Disabled-Mode Equivalence",
        "decision_rule": "Pre-17.13 output == 17.13B / MG disabled output",
        "seeds": SEEDS,
        "tolerance": TOLERANCE,
        "all_pass": all_pass,
        "results": [result.to_dict() for result in results],
    }

    artifact_path = Path(__file__).parent / "research_17_13_b_disabled_equivalence.json"
    with open(artifact_path, "w", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2)

    print("\n" + "=" * 80)
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
    print(f"Artifact saved to: {artifact_path}")
    print("=" * 80)
    return all_pass


if __name__ == "__main__":
    success = run_phase_3_disabled_equivalence()
    raise SystemExit(0 if success else 1)
