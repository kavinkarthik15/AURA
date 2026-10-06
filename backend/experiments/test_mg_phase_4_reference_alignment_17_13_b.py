"""Phase 4: Reference Alignment Investigation for 17.13B.

Purpose:
    Validate that 17.13B enabled predictions exactly match the reconstructed 17.12A
    MG correction applied to the SAME live legacy prediction baseline used by both
    paths.

Key principle:
    - Same benchmark dataset
    - Same held-out experiences
    - Same live legacy SimulationEngine prediction (baseline)
    - 17.12A reconstruction applied to that baseline
    - 17.13B production applied to that baseline
    - Strict per-experience comparison

This ensures we are comparing like-for-like, not comparing against a mismatched
reference artifact.

Gates:
    - All signals match (motivation, goals) within 1e-9
    - All corrections match within 1e-9
    - All final predictions match within 1e-6
    - No coefficient deviations
    - No fallback in production
    - No state mutations
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from backend.compatibility.mg_config import MGCompatibilityConfig
from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.services.simulation_engine import SimulationEngine

SEEDS = [42, 123, 456, 789, 999]
SKILLS = ["python", "dsa", "machine_learning", "projects"]
ACTION_SIGNAL = {
    "Python Project": 0.9,
    "DSA Practice": 0.75,
    "ML Course": 0.8,
    "Interview Prep": 0.75,
    "Build Portfolio": 1.0,
    "Research Paper": 0.8,
}

VALIDATED_COEFFICIENTS = {
    42: {"motivation": -3.2807449219261597, "goals": -4.990929117526626, "intercept": 5.347402291610499},
    123: {"motivation": -2.926512025045623, "goals": -5.966840681018364, "intercept": 5.4524982305536485},
    456: {"motivation": -3.5430610773518003, "goals": -4.761399462830821, "intercept": 5.364756696601368},
    789: {"motivation": -3.102887120621425, "goals": -5.896878903382189, "intercept": 5.595060650317936},
    999: {"motivation": -3.4943725920572044, "goals": -5.102878916446432, "intercept": 5.383562400207635},
}


@dataclass
class ExperienceComparisonRecord:
    """Per-experience comparison between 17.12A reconstruction and 17.13B production."""

    experience_id: str
    selected_action: str
    legacy_prediction: Dict[str, float]
    
    # Signals
    motivation_17_12a: float
    goals_17_12a: float
    motivation_17_13b: float
    goals_17_13b: float
    motivation_match: bool
    goals_match: bool
    
    # Correction
    correction_17_12a: float
    correction_17_13b: float
    correction_match: bool
    
    # Final predictions
    prediction_17_12a: Dict[str, float]
    prediction_17_13b: Dict[str, float]
    prediction_match: bool
    
    # Metadata
    source_17_13b: str
    fallback_17_13b: bool
    
    # Divergence summary
    first_divergence: Optional[str]  # Which stage first differs

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SeedAlignmentResult:
    """Per-seed alignment result."""

    seed: int
    experiences_compared: int
    all_signals_match: bool
    all_corrections_match: bool
    all_predictions_match: bool
    all_no_fallback: bool
    all_no_coefficient_deviation: bool
    no_state_mutations: bool
    all_gates_pass: bool
    first_divergence_seed_level: Optional[str]
    experience_records: List[ExperienceComparisonRecord]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seed": self.seed,
            "experiences_compared": self.experiences_compared,
            "all_signals_match": self.all_signals_match,
            "all_corrections_match": self.all_corrections_match,
            "all_predictions_match": self.all_predictions_match,
            "all_no_fallback": self.all_no_fallback,
            "all_no_coefficient_deviation": self.all_no_coefficient_deviation,
            "no_state_mutations": self.no_state_mutations,
            "all_gates_pass": self.all_gates_pass,
            "first_divergence_seed_level": self.first_divergence_seed_level,
            "experience_records": [rec.to_dict() for rec in self.experience_records],
        }


def _motivation_signal_17_12a(category: str) -> float:
    """Extract motivation from category using 17.12A frozen mapping."""
    if category in {"high_motivation", "project_completion"}:
        return 1.0
    if category in {"low_motivation", "low_skill_practice"}:
        return 0.0
    return 0.5


def _goals_signal_17_12a(state: Dict[str, int], action: str) -> float:
    """Extract goals from flat state using 17.12A frozen mapping."""
    mean_skill = sum(float(state.get(skill, 0.0)) for skill in SKILLS) / len(SKILLS)
    action_signal = ACTION_SIGNAL.get(action, 0.5)
    return float((mean_skill / 100.0) * action_signal)


def _correction_17_12a(coeff: Dict[str, float], motivation: float, goals: float) -> float:
    """Compute MG correction using 17.12A formula: β₀ + β_M·M + β_G·G."""
    return float(coeff["intercept"] + coeff["motivation"] * motivation + coeff["goals"] * goals)


def _apply_correction_to_prediction(
    legacy_pred: Dict[str, Any], correction: float
) -> Dict[str, float]:
    """Apply correction to legacy prediction, clipping to [0, 100]."""
    corrected = dict(legacy_pred)
    for skill in SKILLS:
        if skill in corrected:
            corrected[skill] = max(0.0, min(100.0, float(corrected[skill]) + correction))
    return {str(k): float(v) for k, v in corrected.items()}


def run_seed_alignment(seed: int) -> SeedAlignmentResult:
    """Run per-seed reference alignment investigation."""
    coeffs = VALIDATED_COEFFICIENTS[seed]
    
    # Generate dataset
    generator = ResearchBenchmarkGenerator(seed=seed)
    dataset = generator.generate_dataset(training_size=80, held_out_size=20)
    
    # Create engines
    legacy_engine = SimulationEngine(mg_config=MGCompatibilityConfig.stage_0_disabled())
    cfg = MGCompatibilityConfig.stage_2_controlled(
        rollout_percentage=100.0,
        motivation_coefficient=coeffs["motivation"],
        goals_coefficient=coeffs["goals"],
        intercept_coefficient=coeffs["intercept"],
    )
    enabled_engine = SimulationEngine(mg_config=cfg)
    
    # Trace each experience
    experience_records: List[ExperienceComparisonRecord] = []
    all_signals_match = True
    all_corrections_match = True
    all_predictions_match = True
    all_no_fallback = True
    all_no_coefficient_deviation = True
    no_state_mutations = True
    
    for exp in dataset.held_out_experiences:
        state = dict(exp.initial_state)
        action = exp.selected_action
        
        # Get the shared legacy baseline (category passed for frozen 17.12A mapping)
        legacy_result = legacy_engine.simulate_action(state, action, category=str(exp.category))
        legacy_pred = legacy_result["predicted_future_state"]
        legacy_pred_canonical = {str(k): float(v) for k, v in legacy_pred.items()}
        
        # 17.12A reconstruction
        motivation_12a = _motivation_signal_17_12a(str(exp.category))
        goals_12a = _goals_signal_17_12a(state, action)
        correction_12a = _correction_17_12a(coeffs, motivation_12a, goals_12a)
        prediction_12a = _apply_correction_to_prediction(legacy_pred_canonical, correction_12a)
        
        # 17.13B production (category passed for frozen 17.12A mapping compatibility)
        enabled_result = enabled_engine.simulate_action(state, action, category=str(exp.category))
        prediction_13b = {str(k): float(v) for k, v in enabled_result["predicted_future_state"].items()}
        metadata = enabled_result.get("_mg_metadata", {})
        
        # Extract 17.13B signals and correction from metadata
        motivation_13b = float(metadata.get("motivation_signal", 0.0))
        goals_13b = float(metadata.get("goals_signal", 0.0))
        correction_13b = float(metadata.get("correction_value", 0.0))
        source_13b = str(metadata.get("source", "legacy"))
        fallback_13b = bool(metadata.get("fallback_triggered", False))
        
        # Check state mutation
        if state != dict(exp.initial_state):
            no_state_mutations = False
        
        # Determine first divergence in this experience
        first_div: Optional[str] = None
        
        if abs(motivation_12a - motivation_13b) > 1e-9:
            first_div = "motivation_signal"
            all_signals_match = False
        elif abs(goals_12a - goals_13b) > 1e-9:
            first_div = "goals_signal"
            all_signals_match = False
        elif abs(correction_12a - correction_13b) > 1e-9:
            first_div = "correction_value"
            all_corrections_match = False
        elif not all(
            abs(float(prediction_12a.get(skill, 0.0)) - float(prediction_13b.get(skill, 0.0))) <= 1e-6
            for skill in SKILLS
        ):
            first_div = "prediction"
            all_predictions_match = False
        
        if fallback_13b:
            all_no_fallback = False
            first_div = first_div or "fallback_triggered"
        
        if cfg.motivation_coefficient != coeffs["motivation"]:
            all_no_coefficient_deviation = False
            first_div = first_div or "motivation_coefficient_deviated"
        if cfg.goals_coefficient != coeffs["goals"]:
            all_no_coefficient_deviation = False
            first_div = first_div or "goals_coefficient_deviated"
        if cfg.intercept_coefficient != coeffs["intercept"]:
            all_no_coefficient_deviation = False
            first_div = first_div or "intercept_coefficient_deviated"
        
        record = ExperienceComparisonRecord(
            experience_id=exp.experience_id,
            selected_action=action,
            legacy_prediction=legacy_pred_canonical,
            motivation_17_12a=motivation_12a,
            goals_17_12a=goals_12a,
            motivation_17_13b=motivation_13b,
            goals_17_13b=goals_13b,
            motivation_match=abs(motivation_12a - motivation_13b) <= 1e-9,
            goals_match=abs(goals_12a - goals_13b) <= 1e-9,
            correction_17_12a=correction_12a,
            correction_17_13b=correction_13b,
            correction_match=abs(correction_12a - correction_13b) <= 1e-9,
            prediction_17_12a=prediction_12a,
            prediction_17_13b=prediction_13b,
            prediction_match=all(
                abs(float(prediction_12a.get(skill, 0.0)) - float(prediction_13b.get(skill, 0.0))) <= 1e-6
                for skill in SKILLS
            ),
            source_17_13b=source_13b,
            fallback_17_13b=fallback_13b,
            first_divergence=first_div,
        )
        experience_records.append(record)
    
    # Compute seed-level summary
    all_gates_pass = (
        all_signals_match
        and all_corrections_match
        and all_predictions_match
        and all_no_fallback
        and all_no_coefficient_deviation
        and no_state_mutations
    )
    
    first_div_seed: Optional[str] = None
    if not all_signals_match:
        first_div_seed = "signals_mismatch"
    elif not all_corrections_match:
        first_div_seed = "corrections_mismatch"
    elif not all_predictions_match:
        first_div_seed = "predictions_mismatch"
    elif not all_no_fallback:
        first_div_seed = "fallback_triggered"
    elif not all_no_coefficient_deviation:
        first_div_seed = "coefficient_deviation"
    elif not no_state_mutations:
        first_div_seed = "state_mutation"
    
    return SeedAlignmentResult(
        seed=seed,
        experiences_compared=len(experience_records),
        all_signals_match=all_signals_match,
        all_corrections_match=all_corrections_match,
        all_predictions_match=all_predictions_match,
        all_no_fallback=all_no_fallback,
        all_no_coefficient_deviation=all_no_coefficient_deviation,
        no_state_mutations=no_state_mutations,
        all_gates_pass=all_gates_pass,
        first_divergence_seed_level=first_div_seed,
        experience_records=experience_records,
    )


def run_phase_4_alignment_suite() -> bool:
    """Run Phase 4 reference alignment investigation for all seeds."""
    print("\n" + "=" * 80)
    print("PHASE 4: REFERENCE ALIGNMENT INVESTIGATION")
    print("=" * 80)
    
    results: List[SeedAlignmentResult] = []
    overall_pass = True
    
    for seed in SEEDS:
        result = run_seed_alignment(seed)
        results.append(result)
        
        status = "PASS" if result.all_gates_pass else "FAIL"
        overall_pass = overall_pass and result.all_gates_pass
        
        print(f"\nSeed {seed}: {status}")
        print(f"  Experiences: {result.experiences_compared}")
        print(f"  Signals match: {result.all_signals_match}")
        print(f"  Corrections match: {result.all_corrections_match}")
        print(f"  Predictions match: {result.all_predictions_match}")
        print(f"  No fallback: {result.all_no_fallback}")
        print(f"  No coefficient deviation: {result.all_no_coefficient_deviation}")
        print(f"  No state mutations: {result.no_state_mutations}")
        print(f"  All gates pass: {result.all_gates_pass}")
        if result.first_divergence_seed_level:
            print(f"  First divergence: {result.first_divergence_seed_level}")
        
        # Show first 3 experience records
        for i, record in enumerate(result.experience_records[:3]):
            print(f"\n  Experience {i}: {record.experience_id}")
            print(f"    Action: {record.selected_action}")
            print(f"    Legacy pred: {record.legacy_prediction}")
            print(f"    M: {record.motivation_17_12a} vs {record.motivation_17_13b} -> {record.motivation_match}")
            print(f"    G: {record.goals_17_12a:.6f} vs {record.goals_17_13b:.6f} -> {record.goals_match}")
            print(f"    C: {record.correction_17_12a:.6f} vs {record.correction_17_13b:.6f} -> {record.correction_match}")
            print(f"    P: {record.prediction_match} (17.12A={record.prediction_17_12a}, 17.13B={record.prediction_17_13b})")
            if record.first_divergence:
                print(f"    DIVERGENCE: {record.first_divergence}")
    
    artifact = {
        "timestamp": datetime.now().isoformat(),
        "experiment": "Phase 4: Reference Alignment Investigation",
        "decision_rule": "All signals, corrections, and predictions must match exactly (within numerical tolerance) between 17.12A reconstruction and 17.13B production on the same live legacy baseline.",
        "seeds": SEEDS,
        "all_pass": overall_pass,
        "results": [result.to_dict() for result in results],
    }
    
    artifact_dir = Path(__file__).resolve().parent / "results"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "research_17_13_b_phase_4_reference_alignment.json"
    
    with open(artifact_path, "w", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2)
    
    print("\n" + "=" * 80)
    print(f"PHASE 4 OVERALL: {'PASS ✓' if overall_pass else 'FAIL ✗'}")
    print(f"Artifact: {artifact_path}")
    print("=" * 80)
    
    return overall_pass


if __name__ == "__main__":
    success = run_phase_4_alignment_suite()
    raise SystemExit(0 if success else 1)
