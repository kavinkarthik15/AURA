"""
17.13B Prediction Lineage Diagnostic

Purpose:
Trace one seed (42) through the exact pipeline to identify where the MG correction
is lost or transformed between:
  1. Legacy prediction
  2. Motivation signal
  3. Goals signal
  4. MG correction
  5. MGCompatibilityLayer output
  6. SimulationEngine output
  7. Objective

Compare 17.12A MG prediction against 17.13B MG prediction at the individual
experience level to identify the first divergence.

FROZEN:
  - MG coefficients (exact 17.12A values)
  - benchmark generation (same seed, same 80/20 split)
  - simulation semantics
  - 17.12A mapping
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional

import numpy as np

from backend.compatibility.mg_compatibility import MGCompatibilityLayer
from backend.compatibility.mg_config import MGCompatibilityConfig
from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.experiments.research_mg_shadow_integration_17_12 import MGShadowIntegrationValidator
from backend.services.simulation_engine import SimulationEngine

SEED = 42
COEFFICIENTS = {"motivation": 0.45, "goals": 0.38, "intercept": 0.05}

ACTION_SIGNAL = {
    "Python Project": 0.9,
    "DSA Practice": 0.75,
    "ML Course": 0.8,
    "Interview Prep": 0.75,
    "Build Portfolio": 1.0,
    "Research Paper": 0.8,
}

SKILLS = ["python", "dsa", "machine_learning", "projects"]


@dataclass
class PredictionLineage:
    """Complete prediction lineage for one experience."""

    experience_id: str
    selected_action: str
    initial_state: Dict[str, int]
    actual_future_state: Dict[str, int]

    # 17.12A (reference)
    t12a_motivation: float
    t12a_goals: float
    t12a_correction: float
    t12a_mg_prediction: Dict[str, float]
    t12a_mae_delta: float

    # 17.13B (production)
    t13b_legacy_prediction: Dict[str, Any]
    t13b_motivation: float
    t13b_goals: float
    t13b_correction: float
    t13b_layer_output: Dict[str, Any]
    t13b_engine_output: Dict[str, Any]
    t13b_mae_delta: float

    # Analysis
    motivation_match: bool
    goals_match: bool
    correction_match: bool
    layer_output_match: bool
    prediction_match: bool
    mae_match: bool
    first_divergence: Optional[str]  # Which stage first differs

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _extract_17_12a_signals(state: Dict[str, int], action: str) -> tuple[float, float, float]:
    """Extract 17.12A signals using the frozen validated mapping."""
    # 17.12A motivation_signal: category-based (0.0 for low, 0.5 for medium, 1.0 for high)
    # For benchmark experiences, we need to infer from state
    mean_skill = mean([float(state.get(skill, 0.0)) for skill in SKILLS])
    # Approximation: low < 30, high > 60, else medium
    if mean_skill < 30:
        motivation = 0.0
    elif mean_skill > 60:
        motivation = 1.0
    else:
        motivation = 0.5

    # 17.12A goals_signal
    goals = float(mean([float(state.get(skill, 0.0)) for skill in SKILLS]) / 100.0) * ACTION_SIGNAL.get(
        action, 0.5
    )

    # 17.12A correction
    correction = COEFFICIENTS["intercept"] + (
        COEFFICIENTS["motivation"] * motivation + COEFFICIENTS["goals"] * goals
    )

    return float(motivation), float(goals), float(correction)


def _mae(predicted: Dict[str, Any], actual: Dict[str, Any]) -> float:
    keys = sorted(set(predicted) | set(actual))
    if not keys:
        return 0.0
    return float(
        sum(abs(float(predicted.get(k, 0)) - float(actual.get(k, 0))) for k in keys)
        / len(keys)
    )


def run_lineage_diagnostic(exp_idx: int = 0) -> PredictionLineage:
    """
    Trace one held-out experience through both 17.12A and 17.13B.

    Args:
        exp_idx: Index within held-out experiences (0-based)
    """
    # Generate benchmark
    generator = ResearchBenchmarkGenerator(seed=SEED)
    dataset = generator.generate_dataset(training_size=80, held_out_size=20)

    # Select one held-out experience
    if exp_idx >= len(dataset.held_out_experiences):
        raise ValueError(
            f"exp_idx {exp_idx} out of range (max {len(dataset.held_out_experiences) - 1})"
        )

    exp = dataset.held_out_experiences[exp_idx]
    state = dict(exp.initial_state)
    action = exp.selected_action
    actual = exp.actual_future_state

    print(f"\n{'='*80}")
    print(f"PREDICTION LINEAGE TRACE")
    print(f"{'='*80}")
    print(f"Experience: {exp.experience_id}")
    print(f"Seed: {SEED}")
    print(f"Initial state: {state}")
    print(f"Action: {action}")
    print(f"Actual future state: {actual}")

    # =========================================================================
    # 17.12A (Reference Behavior)
    # =========================================================================
    print(f"\n{'-'*80}")
    print("17.12A REFERENCE CALCULATION")
    print(f"{'-'*80}")

    t12a_motivation, t12a_goals, t12a_correction = _extract_17_12a_signals(state, action)
    print(f"Motivation signal (17.12A): {t12a_motivation:.6f}")
    print(f"Goals signal (17.12A): {t12a_goals:.6f}")
    print(f"MG correction (17.12A): {t12a_correction:.6f}")

    # For 17.12A, we use a shadow-mode calculation on legacy baseline
    legacy_engine = SimulationEngine()
    legacy_pred = legacy_engine.simulate_action(state, action)
    print(f"Legacy prediction (17.12A ref): {legacy_pred['predicted_future_state']}")

    # Apply 17.12A correction
    t12a_mg_pred = dict(legacy_pred["predicted_future_state"])
    for skill in SKILLS:
        if skill in t12a_mg_pred:
            original = float(t12a_mg_pred[skill])
            corrected_val = original + t12a_correction
            t12a_mg_pred[skill] = max(0.0, min(100.0, corrected_val))

    print(f"17.12A MG prediction: {t12a_mg_pred}")

    t12a_mae_legacy = _mae(legacy_pred["predicted_future_state"], actual)
    t12a_mae_mg = _mae(t12a_mg_pred, actual)
    t12a_mae_delta = t12a_mae_legacy - t12a_mae_mg

    print(f"17.12A Legacy MAE: {t12a_mae_legacy:.6f}")
    print(f"17.12A MG MAE: {t12a_mae_mg:.6f}")
    print(f"17.12A MAE improvement: {t12a_mae_delta:.6f}")

    # =========================================================================
    # 17.13B (Production Implementation)
    # =========================================================================
    print(f"\n{'-'*80}")
    print("17.13B PRODUCTION IMPLEMENTATION")
    print(f"{'-'*80}")

    # Create 17.13B engine with MG enabled
    config = MGCompatibilityConfig.stage_2_controlled(
        rollout_percentage=100.0,
        motivation_coefficient=COEFFICIENTS["motivation"],
        goals_coefficient=COEFFICIENTS["goals"],
        intercept_coefficient=COEFFICIENTS["intercept"],
    )
    engine_13b = SimulationEngine(mg_config=config)

    # Get legacy prediction (for comparison)
    t13b_legacy_pred = legacy_engine.simulate_action(state, action)
    print(f"Legacy prediction (17.13B baseline): {t13b_legacy_pred['predicted_future_state']}")

    # Manually extract signals using the layer's logic (what 17.13B actually does)
    layer = MGCompatibilityLayer(config)
    t13b_motivation = layer._extract_motivation_signal(state, action)
    t13b_goals = layer._extract_goals_signal(state, action)
    print(f"Motivation signal (17.13B): {t13b_motivation:.6f}")
    print(f"Goals signal (17.13B): {t13b_goals:.6f}")

    t13b_correction = layer._compute_correction(t13b_motivation, t13b_goals)
    print(f"MG correction (17.13B): {t13b_correction:.6f}")

    # Get layer output
    t13b_layer_output, t13b_metadata = layer.apply(t13b_legacy_pred, state, action)
    print(f"Layer output: {t13b_layer_output['predicted_future_state']}")
    print(f"Layer metadata: source={t13b_metadata.source}, applied={t13b_metadata.correction_applied}")

    # Get engine output
    t13b_engine_output = engine_13b.simulate_action(state, action)
    print(f"Engine output: {t13b_engine_output['predicted_future_state']}")
    print(f"Engine metadata: source={t13b_engine_output.get('_mg_metadata', {}).get('source')}")

    t13b_mae_legacy = _mae(t13b_legacy_pred["predicted_future_state"], actual)
    t13b_mae_mg = _mae(t13b_engine_output["predicted_future_state"], actual)
    t13b_mae_delta = t13b_mae_legacy - t13b_mae_mg

    print(f"17.13B Legacy MAE: {t13b_mae_legacy:.6f}")
    print(f"17.13B MG MAE: {t13b_mae_mg:.6f}")
    print(f"17.13B MAE improvement: {t13b_mae_delta:.6f}")

    # =========================================================================
    # Analysis
    # =========================================================================
    print(f"\n{'-'*80}")
    print("PREDICTION LINEAGE ANALYSIS")
    print(f"{'-'*80}")

    motivation_match = abs(t12a_motivation - t13b_motivation) < 1e-6
    goals_match = abs(t12a_goals - t13b_goals) < 1e-6
    correction_match = abs(t12a_correction - t13b_correction) < 1e-6

    print(f"Motivation signals match: {motivation_match} (17.12A={t12a_motivation:.6f}, 17.13B={t13b_motivation:.6f})")
    print(f"Goals signals match: {goals_match} (17.12A={t12a_goals:.6f}, 17.13B={t13b_goals:.6f})")
    print(f"Correction values match: {correction_match} (17.12A={t12a_correction:.6f}, 17.13B={t13b_correction:.6f})")

    # Check if layer output matches 17.12A MG prediction
    layer_output_match = all(
        abs(float(t13b_layer_output["predicted_future_state"].get(skill, 0)) - t12a_mg_pred.get(skill, 0))
        < 1e-6
        for skill in SKILLS
    )
    print(f"Layer output matches 17.12A MG prediction: {layer_output_match}")

    # Check if engine output matches layer output
    prediction_match = all(
        abs(
            float(t13b_engine_output["predicted_future_state"].get(skill, 0))
            - float(t13b_layer_output["predicted_future_state"].get(skill, 0))
        )
        < 1e-6
        for skill in SKILLS
    )
    print(f"Engine output matches layer output: {prediction_match}")

    mae_match = abs(t12a_mae_delta - t13b_mae_delta) < 1e-6
    print(f"MAE improvements match: {mae_match} (17.12A={t12a_mae_delta:.6f}, 17.13B={t13b_mae_delta:.6f})")

    # Identify first divergence
    first_divergence = None
    if not motivation_match:
        first_divergence = "motivation_signal"
    elif not goals_match:
        first_divergence = "goals_signal"
    elif not correction_match:
        first_divergence = "correction_value"
    elif not layer_output_match:
        first_divergence = "layer_output"
    elif not prediction_match:
        first_divergence = "engine_output"
    elif not mae_match:
        first_divergence = "mae"

    if first_divergence:
        print(f"\n[WARNING] FIRST DIVERGENCE: {first_divergence}")
    else:
        print(f"\n[OK] NO DIVERGENCE - 17.13B reproduces 17.12A")

    return PredictionLineage(
        experience_id=exp.experience_id,
        selected_action=action,
        initial_state=state,
        actual_future_state=actual,
        t12a_motivation=t12a_motivation,
        t12a_goals=t12a_goals,
        t12a_correction=t12a_correction,
        t12a_mg_prediction=t12a_mg_pred,
        t12a_mae_delta=t12a_mae_delta,
        t13b_legacy_prediction=t13b_legacy_pred["predicted_future_state"],
        t13b_motivation=t13b_motivation,
        t13b_goals=t13b_goals,
        t13b_correction=t13b_correction,
        t13b_layer_output=t13b_layer_output["predicted_future_state"],
        t13b_engine_output=t13b_engine_output["predicted_future_state"],
        t13b_mae_delta=t13b_mae_delta,
        motivation_match=motivation_match,
        goals_match=goals_match,
        correction_match=correction_match,
        layer_output_match=layer_output_match,
        prediction_match=prediction_match,
        mae_match=mae_match,
        first_divergence=first_divergence,
    )


if __name__ == "__main__":
    lineage = run_lineage_diagnostic(exp_idx=0)

    # Save artifact
    artifact_dir = Path(__file__).resolve().parent / "results"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "research_17_13_b_prediction_lineage.json"

    with open(artifact_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "seed": SEED,
                "test_name": "17.13B Prediction Lineage Diagnostic",
                "lineage": lineage.to_dict(),
            },
            handle,
            indent=2,
        )

    print(f"\n{'='*80}")
    print(f"Artifact saved to: {artifact_path}")
    print(f"{'='*80}")

    # Summary
    if lineage.first_divergence:
        print(f"\nDIAGNOSIS: Production diverges at '{lineage.first_divergence}'")
    else:
        print(f"\nDIAGNOSIS: Production matches reference (17.12A)")
