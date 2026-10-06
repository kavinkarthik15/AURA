"""Single-input mapping equivalence diagnosis for 17.13B.

This is a minimal, seed-by-seed comparison between the validated 17.12A signal
construction and the real 17.13B production boundary. It intentionally avoids
changing coefficients or production semantics.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from backend.compatibility.mg_config import MGCompatibilityConfig
from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.experiments.research_mg_shadow_integration_17_12 import MGShadowIntegrationValidator
from backend.services.simulation_engine import SimulationEngine

SEEDS = [42, 123, 456, 789, 999]
VALIDATED_COEFFICIENTS = {
    42: {"motivation": 0.45, "goals": 0.38, "intercept": 0.05},
    123: {"motivation": 0.52, "goals": 0.42, "intercept": 0.08},
    456: {"motivation": 0.48, "goals": 0.40, "intercept": 0.06},
    789: {"motivation": 0.50, "goals": 0.39, "intercept": 0.07},
    999: {"motivation": 0.46, "goals": 0.41, "intercept": 0.05},
}
ACTION_SIGNAL = {
    "Python Project": 0.9,
    "DSA Practice": 0.75,
    "ML Course": 0.8,
    "Interview Prep": 0.75,
    "Build Portfolio": 1.0,
    "Research Paper": 0.8,
}


@dataclass
class MappingComparison:
    seed: int
    experience_id: str
    action: str
    category: str
    legacy_state_keys: List[str]
    legacy_state: Dict[str, int]
    state_contract_match: bool
    seventeen_twelve_a_motivation_signal: float
    seventeen_thirteen_b_motivation_signal: float
    motivation_signal_match: bool
    seventeen_twelve_a_goals_signal: float
    seventeen_thirteen_b_goals_signal: float
    goals_signal_match: bool
    seventeen_twelve_a_correction: float
    seventeen_thirteen_b_correction: float
    correction_match: bool
    seventeen_twelve_a_prediction: Dict[str, int]
    seventeen_thirteen_b_prediction: Dict[str, int]
    prediction_match: bool
    source_17_13_b: str
    fallback_17_13_b: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _legacy_prediction_for_state(state: Dict[str, int], action: str) -> Dict[str, Any]:
    engine = SimulationEngine(mg_config=MGCompatibilityConfig.stage_0_disabled())
    return engine.simulate_action(state, action)


def _mg_prediction_for_state(state: Dict[str, int], action: str, coeffs: Dict[str, float]) -> Dict[str, Any]:
    config = MGCompatibilityConfig.stage_2_controlled(
        rollout_percentage=100.0,
        motivation_coefficient=coeffs["motivation"],
        goals_coefficient=coeffs["goals"],
        intercept_coefficient=coeffs["intercept"],
    )
    engine = SimulationEngine(mg_config=config)
    return engine.simulate_action(state, action)


def _apply_correction_to_legacy_prediction(legacy_prediction: Dict[str, Any], correction: float) -> Dict[str, int]:
    future_state = dict(legacy_prediction["predicted_future_state"])
    for skill_name in ["python", "dsa", "machine_learning", "projects"]:
        if skill_name in future_state:
            future_state[skill_name] = max(0, min(100, int(future_state[skill_name] + correction)))
    return future_state


def _run_single_seed(seed: int) -> MappingComparison:
    generator = ResearchBenchmarkGenerator(seed=seed)
    dataset = generator.generate_dataset(training_size=80, held_out_size=20)
    exp = dataset.held_out_experiences[0]
    state = dict(exp.initial_state)
    coeffs = VALIDATED_COEFFICIENTS[seed]

    legacy_prediction = _legacy_prediction_for_state(state, exp.selected_action)
    mg_prediction = _mg_prediction_for_state(state, exp.selected_action, coeffs)

    t12_motivation = MGShadowIntegrationValidator._motivation_signal(str(exp.category))
    t12_goals = MGShadowIntegrationValidator._goals_signal(state, exp.selected_action)
    t12_correction = coeffs["intercept"] + coeffs["motivation"] * t12_motivation + coeffs["goals"] * t12_goals
    t12_prediction = _apply_correction_to_legacy_prediction(legacy_prediction, t12_correction)

    metadata = mg_prediction.get("_mg_metadata", {})
    t13_motivation = float(metadata.get("motivation_signal", 0.0))
    t13_goals = float(metadata.get("goals_signal", 0.0))
    t13_correction = float(metadata.get("correction_value", 0.0))
    t13_prediction = dict(mg_prediction.get("predicted_future_state", {}))

    # 17.12A receives a flat skill dictionary and computes Goals from that state.
    # 17.13B passes the same flat dict into SimulationEngine, but the MG layer
    # expects a nested "goals" object and therefore reads zero values.
    state_contract_match = True

    return MappingComparison(
        seed=seed,
        experience_id=exp.experience_id,
        action=exp.selected_action,
        category=exp.category,
        legacy_state_keys=sorted(state.keys()),
        legacy_state=state,
        state_contract_match=("goals" not in state),
        seventeen_twelve_a_motivation_signal=t12_motivation,
        seventeen_thirteen_b_motivation_signal=t13_motivation,
        motivation_signal_match=abs(t12_motivation - t13_motivation) <= 1e-9,
        seventeen_twelve_a_goals_signal=t12_goals,
        seventeen_thirteen_b_goals_signal=t13_goals,
        goals_signal_match=abs(t12_goals - t13_goals) <= 1e-9,
        seventeen_twelve_a_correction=t12_correction,
        seventeen_thirteen_b_correction=t13_correction,
        correction_match=abs(t12_correction - t13_correction) <= 1e-9,
        seventeen_twelve_a_prediction=t12_prediction,
        seventeen_thirteen_b_prediction=t13_prediction,
        prediction_match=(t12_prediction == t13_prediction),
        source_17_13_b=str(metadata.get("source", "legacy")),
        fallback_17_13_b=bool(metadata.get("fallback_triggered", False)),
    )


def run_diagnosis() -> Dict[str, Any]:
    results = [_run_single_seed(seed) for seed in SEEDS]
    payload = {
        "timestamp": datetime.now().isoformat(),
        "experiment": "17.13B single-input mapping equivalence diagnosis",
        "seeds": SEEDS,
        "results": [item.to_dict() for item in results],
        "overall_equivalence": all(
            r.goals_signal_match and r.motivation_signal_match and r.correction_match and r.prediction_match and r.source_17_13_b == "mg"
            for r in results
        ),
    }
    artifact_dir = Path(__file__).resolve().parent / "results"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "research_17_13_b_mapping_diagnosis.json"
    with open(artifact_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return payload, artifact_path


if __name__ == "__main__":
    payload, artifact_path = run_diagnosis()
    for item in payload["results"]:
        print(f"Seed {item['seed']}: {item['experience_id']} / {item['action']}")
        print(f"  17.12A motivation={item['seventeen_twelve_a_motivation_signal']:.6f}, 17.13B motivation={item['seventeen_thirteen_b_motivation_signal']:.6f} -> {'✓' if item['motivation_signal_match'] else '✗'}")
        print(f"  17.12A goals={item['seventeen_twelve_a_goals_signal']:.6f}, 17.13B goals={item['seventeen_thirteen_b_goals_signal']:.6f} -> {'✓' if item['goals_signal_match'] else '✗'}")
        print(f"  17.12A correction={item['seventeen_twelve_a_correction']:.6f}, 17.13B correction={item['seventeen_thirteen_b_correction']:.6f} -> {'✓' if item['correction_match'] else '✗'}")
        print(f"  Prediction match={'✓' if item['prediction_match'] else '✗'} | source={item['source_17_13_b']} | fallback={item['fallback_17_13_b']}")
    print(f"OVERALL_EQUIVALENCE={'PASS' if payload['overall_equivalence'] else 'FAIL'}")
    print(f"Artifact: {artifact_path}")
