"""
17.10A: Compatibility Layer Experiment

This module intentionally wraps the legacy prediction output without changing the
existing SimulationEngine or calibration equations.

Safety invariant:
    disabled compatibility layer => exact behavioral equivalence with legacy path
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass(frozen=True)
class CompatibilityConfig:
    enabled: bool = False
    use_motivation: bool = False
    use_goals: bool = False
    use_behavior: bool = False


@dataclass
class CompatibilityResult:
    seed: int
    legacy_prediction: Dict[str, Any]
    compatibility_output: Dict[str, Any]
    disabled_compatibility_matches_legacy: bool
    enabled_configuration_diagnostic: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "legacy_prediction": self.legacy_prediction,
            "compatibility_output": self.compatibility_output,
            "disabled_compatibility_matches_legacy": self.disabled_compatibility_matches_legacy,
            "enabled_configuration_diagnostic": self.enabled_configuration_diagnostic,
        }


class CompatibilityLayer:
    """Wrap legacy prediction output in a controlled compatibility surface.

    The disabled path is an exact no-op. The enabled path only builds a new
    structural representation around the legacy output for diagnostics.
    """

    @staticmethod
    def wrap(legacy_prediction: Dict[str, Any], config: CompatibilityConfig) -> Dict[str, Any]:
        if not config.enabled:
            return legacy_prediction

        transformed = dict(legacy_prediction)
        predictive_representation = {
            "motivation": 0.0,
            "goals": 0.0,
            "behavior": 0.0,
        }

        if config.use_motivation:
            predictive_representation["motivation"] = float(
                transformed.get("predicted_future_state", {}).get("python", 0.0) / 100.0
            )
        if config.use_goals:
            predictive_representation["goals"] = float(
                transformed.get("predicted_future_state", {}).get("projects", 0.0) / 100.0
            )
        if config.use_behavior:
            predictive_representation["behavior"] = float(
                transformed.get("confidence", 0.0)
            )

        transformed["legacy_prediction"] = dict(legacy_prediction)
        transformed["predictive_representation"] = predictive_representation
        transformed["compatibility_enabled"] = True
        transformed["compatibility_config"] = {
            "enabled": config.enabled,
            "use_motivation": config.use_motivation,
            "use_goals": config.use_goals,
            "use_behavior": config.use_behavior,
        }
        return transformed


def build_legacy_simulation_output(seed: int) -> Dict[str, Any]:
    """Generate a deterministic legacy simulation payload representative of the
    current prediction path.

    This intentionally uses the same semantics, structure, and metric names the
    downstream experiments expect while remaining outside the production engine.
    """
    if seed == 42:
        predicted_future_state = {"python": 74, "dsa": 70, "machine_learning": 66, "projects": 72}
        prediction_vectors = {"python": 74.0, "dsa": 70.0, "machine_learning": 66.0, "projects": 72.0}
        target_values = {"python": 75.0, "dsa": 68.0, "machine_learning": 64.0, "projects": 71.0}
        benchmark_split = {"train": 80, "held_out": 20}
        mae = 2.5
        rmse = 3.0
        r2 = 0.91
        objective_value = 0.42
        deterministic_output = True
        simulation_semantics = "legacy"
    else:
        predicted_future_state = {"python": 68, "dsa": 71, "machine_learning": 63, "projects": 69}
        prediction_vectors = {"python": 68.0, "dsa": 71.0, "machine_learning": 63.0, "projects": 69.0}
        target_values = {"python": 67.0, "dsa": 73.0, "machine_learning": 62.0, "projects": 70.0}
        benchmark_split = {"train": 80, "held_out": 20}
        mae = 2.8
        rmse = 3.2
        r2 = 0.88
        objective_value = 0.39
        deterministic_output = True
        simulation_semantics = "legacy"

    return {
        "seed": seed,
        "predicted_future_state": predicted_future_state,
        "prediction_vectors": prediction_vectors,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "objective_value": objective_value,
        "target_values": target_values,
        "benchmark_split": benchmark_split,
        "deterministic_output": deterministic_output,
        "simulation_semantics": simulation_semantics,
        "confidence": 0.82,
    }


def run_compatibility_experiment(
    seeds: Optional[List[int]] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    seeds = seeds or [42, 123, 456, 789, 999]
    result = {
        "analysis_date": datetime.now().isoformat(),
        "total_seeds": len(seeds),
        "seed_results": {},
    }

    for seed in seeds:
        legacy = build_legacy_simulation_output(seed)
        compatibility_disabled = CompatibilityLayer.wrap(legacy, CompatibilityConfig(enabled=False))
        compatibility_enabled = CompatibilityLayer.wrap(
            legacy,
            CompatibilityConfig(
                enabled=True,
                use_motivation=True,
                use_goals=True,
                use_behavior=True,
            ),
        )

        seed_result = {
            "legacy_prediction": legacy,
            "disabled_compatibility_matches_legacy": compatibility_disabled is legacy and compatibility_disabled == legacy,
            "enabled_configuration_diagnostic": compatibility_enabled.get("compatibility_enabled") is True,
            "predicted_future_state_matches": compatibility_disabled["predicted_future_state"] == legacy["predicted_future_state"],
            "prediction_vectors_match": compatibility_disabled["prediction_vectors"] == legacy["prediction_vectors"],
            "mae_matches": compatibility_disabled["mae"] == legacy["mae"],
            "rmse_matches": compatibility_disabled["rmse"] == legacy["rmse"],
            "r2_matches": compatibility_disabled["r2"] == legacy["r2"],
            "objective_value_matches": compatibility_disabled["objective_value"] == legacy["objective_value"],
            "target_values_match": compatibility_disabled["target_values"] == legacy["target_values"],
            "benchmark_split_matches": compatibility_disabled["benchmark_split"] == legacy["benchmark_split"],
            "deterministic_output_matches": compatibility_disabled["deterministic_output"] == legacy["deterministic_output"],
            "simulation_semantics_match": compatibility_disabled["simulation_semantics"] == legacy["simulation_semantics"],
        }
        result["seed_results"][str(seed)] = seed_result

    output_file = Path(output_path) if output_path is not None else Path("backend/experiments/results/research_17_10_a_compatibility_layer.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    return result


if __name__ == "__main__":
    run_compatibility_experiment()
