"""17.13B Enabled Integration Trace / Differential Diagnosis.

This experiment traces one held-out experience per seed through the exact pipeline:

Benchmark initial state
    -> selected action
    -> Legacy prediction
    -> Motivation signal
    -> Goals signal
    -> MG correction
    -> MG-corrected prediction inside compatibility layer
    -> prediction returned by SimulationEngine
    -> prediction evaluated by the benchmark

It compares the validated 17.12A shadow path against the actual 17.13B production path,
then records the first numerical divergence for each seed.

Important guardrails:
- No coefficient changes
- No mapping changes
- No benchmark changes
- No simulation semantics changes
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.compatibility.mg_compatibility import MGCompatibilityLayer
from backend.compatibility.mg_config import MGCompatibilityConfig
from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.experiments.research_mg_shadow_integration_17_12 import MGShadowIntegrationValidator
from backend.services.simulation_engine import SimulationEngine

SEEDS = [42, 123, 456, 789, 999]
SKILLS = ["python", "dsa", "machine_learning", "projects"]
VALIDATED_COEFFICIENTS = {
    42: {"motivation": -3.2807449219261597, "goals": -4.990929117526626, "intercept": 5.347402291610499},
    123: {"motivation": -2.926512025045623, "goals": -5.966840681018364, "intercept": 5.4524982305536485},
    456: {"motivation": -3.5430610773518003, "goals": -4.761399462830821, "intercept": 5.364756696601368},
    789: {"motivation": -3.102887120621425, "goals": -5.896878903382189, "intercept": 5.595060650317936},
    999: {"motivation": -3.4943725920572044, "goals": -5.102878916446432, "intercept": 5.383562400207635},
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
class TraceRecord:
    seed: int
    action: str
    experience_id: str
    benchmark_initial_state: Dict[str, int]
    legacy_prediction_17_12a: Dict[str, float]
    legacy_prediction_17_13b: Dict[str, float]
    motivation_17_12a: float
    motivation_17_13b: float
    goals_17_12a: float
    goals_17_13b: float
    correction_17_12a: float
    correction_17_13b: float
    mg_prediction_17_12a: Dict[str, float]
    mg_prediction_inside_layer_17_13b: Dict[str, float]
    mg_prediction_returned_by_engine_17_13b: Dict[str, float]
    mg_prediction_evaluated_by_benchmark: Dict[str, float]
    first_divergence: Optional[str]
    diagnosis: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _mae(predicted: Dict[str, Any], actual: Dict[str, Any]) -> float:
    keys = sorted(set(predicted) | set(actual))
    if not keys:
        return 0.0
    return float(sum(abs(float(predicted.get(k, 0.0)) - float(actual.get(k, 0.0))) for k in keys) / len(keys))


def _canonical_float_dict(values: Dict[str, Any]) -> Dict[str, float]:
    return {str(k): float(v) for k, v in values.items()}


def _legacy_prediction_17_13b(state: Dict[str, int], action: str) -> Dict[str, float]:
    engine = SimulationEngine(mg_config=MGCompatibilityConfig.stage_0_disabled())
    result = engine.simulate_action(dict(state), action)
    return _canonical_float_dict(result["predicted_future_state"])


def _apply_correction_to_prediction(base_prediction: Dict[str, Any], correction: float) -> Dict[str, float]:
    corrected = dict(base_prediction)
    for skill in SKILLS:
        if skill in corrected:
            corrected[skill] = float(max(0.0, min(100.0, float(corrected[skill]) + correction)))
    return _canonical_float_dict(corrected)


def _motivation_17_12a(exp_category: str) -> float:
    if exp_category in {"high_motivation", "project_completion"}:
        return 1.0
    if exp_category in {"low_motivation", "low_skill_practice"}:
        return 0.0
    return 0.5


def _goals_17_12a(state: Dict[str, int], action: str) -> float:
    return float(
        (sum(float(state.get(skill, 0.0)) for skill in SKILLS) / len(SKILLS) / 100.0)
        * ACTION_SIGNAL.get(action, 0.5)
    )


def _correction_17_12a(coeffs: Dict[str, float], motivation: float, goals: float) -> float:
    return float(coeffs["intercept"] + coeffs["motivation"] * motivation + coeffs["goals"] * goals)


def _trace_seed(seed: int) -> TraceRecord:
    generator = ResearchBenchmarkGenerator(seed=seed)
    dataset = generator.generate_dataset(training_size=80, held_out_size=20)
    exp = dataset.held_out_experiences[0]
    state = dict(exp.initial_state)
    action = exp.selected_action
    coeffs = VALIDATED_COEFFICIENTS[seed]

    legacy_17_12a = _canonical_float_dict(exp.predicted_future_state)
    legacy_17_13b = _legacy_prediction_17_13b(state, action)

    motivation_17_12a = _motivation_17_12a(str(exp.category))
    motivation_17_13b = MGShadowIntegrationValidator._motivation_signal(str(exp.category))
    goals_17_12a = _goals_17_12a(state, action)
    goals_17_13b = MGShadowIntegrationValidator._goals_signal(state, action)

    correction_17_12a = _correction_17_12a(coeffs, motivation_17_12a, goals_17_12a)
    config = MGCompatibilityConfig.stage_2_controlled(
        rollout_percentage=100.0,
        motivation_coefficient=coeffs["motivation"],
        goals_coefficient=coeffs["goals"],
        intercept_coefficient=coeffs["intercept"],
    )
    layer = MGCompatibilityLayer(config)
    production_legacy = _legacy_prediction_17_13b(state, action)
    mg_prediction_inside_layer_17_13b, metadata = layer.apply(production_legacy, state, action)
    mg_prediction_inside_layer_17_13b = _canonical_float_dict(mg_prediction_inside_layer_17_13b["predicted_future_state"])
    motivation_17_13b_layer = float(metadata.motivation_signal)
    goals_17_13b_layer = float(metadata.goals_signal)
    correction_17_13b = float(metadata.correction_value)

    engine_17_13b = SimulationEngine(mg_config=config)
    engine_result = engine_17_13b.simulate_action(state, action)
    mg_prediction_returned_by_engine_17_13b = _canonical_float_dict(engine_result["predicted_future_state"])

    mg_prediction_17_12a = _apply_correction_to_prediction(legacy_17_12a, correction_17_12a)
    benchmark_prediction = dict(mg_prediction_returned_by_engine_17_13b)
    # The benchmark evaluates the engine-returned prediction directly.
    mg_prediction_evaluated_by_benchmark = benchmark_prediction

    first_divergence = None
    diagnosis = "No divergence detected between validated 17.12A path and 17.13B production path."

    if not all(abs(float(legacy_17_12a.get(skill, 0.0)) - float(legacy_17_13b.get(skill, 0.0))) <= 1e-9 for skill in SKILLS):
        first_divergence = "legacy_prediction"
        diagnosis = "Legacy prediction differs before MG is applied. The production engine is not reproducing the benchmark baseline used by 17.12A."
    elif abs(motivation_17_12a - motivation_17_13b) > 1e-9:
        first_divergence = "motivation_signal"
        diagnosis = "Motivation signal diverges between 17.12A and 17.13B before the correction is computed."
    elif abs(goals_17_12a - goals_17_13b) > 1e-9:
        first_divergence = "goals_signal"
        diagnosis = "Goals signal diverges between 17.12A and 17.13B."
    elif abs(correction_17_12a - correction_17_13b) > 1e-9:
        first_divergence = "correction_value"
        diagnosis = "Correction differs even though the same configuration is used; the layer is not using the frozen 17.12A mapping exactly."
    elif not all(abs(float(mg_prediction_17_12a.get(skill, 0.0)) - float(mg_prediction_inside_layer_17_13b.get(skill, 0.0))) <= 1e-9 for skill in SKILLS):
        first_divergence = "mg_prediction_inside_layer"
        diagnosis = "The compatibility layer returns a different corrected prediction than the 17.12A calculation even with matching signals and correction."
    elif not all(abs(float(mg_prediction_inside_layer_17_13b.get(skill, 0.0)) - float(mg_prediction_returned_by_engine_17_13b.get(skill, 0.0))) <= 1e-9 for skill in SKILLS):
        first_divergence = "mg_prediction_returned_by_engine"
        diagnosis = "The SimulationEngine returns a different prediction than the compatibility layer produced, indicating a downstream overwrite or object mismatch."
    elif not all(abs(float(mg_prediction_returned_by_engine_17_13b.get(skill, 0.0)) - float(mg_prediction_evaluated_by_benchmark.get(skill, 0.0))) <= 1e-9 for skill in SKILLS):
        first_divergence = "benchmark_evaluation"
        diagnosis = "The benchmark is evaluating a different prediction than the engine returned."

    return TraceRecord(
        seed=seed,
        action=action,
        experience_id=exp.experience_id,
        benchmark_initial_state=state,
        legacy_prediction_17_12a=legacy_17_12a,
        legacy_prediction_17_13b=legacy_17_13b,
        motivation_17_12a=motivation_17_12a,
        motivation_17_13b=motivation_17_13b_layer,
        goals_17_12a=goals_17_12a,
        goals_17_13b=goals_17_13b_layer,
        correction_17_12a=correction_17_12a,
        correction_17_13b=correction_17_13b,
        mg_prediction_17_12a=mg_prediction_17_12a,
        mg_prediction_inside_layer_17_13b=mg_prediction_inside_layer_17_13b,
        mg_prediction_returned_by_engine_17_13b=mg_prediction_returned_by_engine_17_13b,
        mg_prediction_evaluated_by_benchmark=mg_prediction_evaluated_by_benchmark,
        first_divergence=first_divergence,
        diagnosis=diagnosis,
    )


def _render_markdown(traces: List[TraceRecord]) -> str:
    lines: List[str] = [
        "# 17.13B Enabled Integration Trace",
        "",
        "This report traces one held-out experience per seed across the exact integration boundary:",
        "",
        "- Benchmark initial state",
        "- selected action",
        "- Legacy prediction",
        "- Motivation signal",
        "- Goals signal",
        "- MG correction",
        "- MG-corrected prediction inside compatibility layer",
        "- prediction returned by SimulationEngine",
        "- prediction evaluated by the benchmark",
        "",
        "## Summary",
        "",
    ]

    for trace in traces:
        lines.append(f"## Seed {trace.seed} — {trace.experience_id}")
        lines.append(f"- Action: {trace.action}")
        lines.append(f"- First divergence: {trace.first_divergence or 'none'}")
        lines.append(f"- Diagnosis: {trace.diagnosis}")
        lines.append("")
        lines.append("### Legacy predictions")
        lines.append(f"- 17.12A: {trace.legacy_prediction_17_12a}")
        lines.append(f"- 17.13B: {trace.legacy_prediction_17_13b}")
        lines.append("")
        lines.append("### Signals")
        lines.append(f"- Motivation: 17.12A={trace.motivation_17_12a}, 17.13B={trace.motivation_17_13b}")
        lines.append(f"- Goals: 17.12A={trace.goals_17_12a}, 17.13B={trace.goals_17_13b}")
        lines.append("")
        lines.append("### Correction")
        lines.append(f"- Correction: 17.12A={trace.correction_17_12a}, 17.13B={trace.correction_17_13b}")
        lines.append("")
        lines.append("### Final predictions")
        lines.append(f"- 17.12A MG: {trace.mg_prediction_17_12a}")
        lines.append(f"- inside layer: {trace.mg_prediction_inside_layer_17_13b}")
        lines.append(f"- returned by engine: {trace.mg_prediction_returned_by_engine_17_13b}")
        lines.append(f"- evaluated by benchmark: {trace.mg_prediction_evaluated_by_benchmark}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def run_trace_suite() -> Dict[str, Any]:
    traces = [_trace_seed(seed) for seed in SEEDS]
    artifact = {
        "timestamp": datetime.now().isoformat(),
        "experiment": "17.13B Enabled Integration Trace",
        "seeds": SEEDS,
        "traces": [t.to_dict() for t in traces],
        "overall_first_divergence_summary": {
            trace.seed: trace.first_divergence for trace in traces
        },
    }

    artifact_dir = Path(__file__).resolve().parent / "results"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / "research_17_13_b_enabled_integration_trace.json"
    markdown_path = artifact_dir / "RESEARCH_17_13_B_ENABLED_INTEGRATION_TRACE.md"

    with open(artifact_path, "w", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2)

    with open(markdown_path, "w", encoding="utf-8") as handle:
        handle.write(_render_markdown(traces))

    print(f"Trace artifact written to: {artifact_path}")
    print(f"Markdown report written to: {markdown_path}")
    return artifact


if __name__ == "__main__":
    run_trace_suite()
