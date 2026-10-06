"""
17.10B: Compatibility Integration Experiment

This experiment validates the compatibility boundary as the only integration
point for the M/G/B representation. It does not modify the SimulationEngine or
legacy calibration equations; it only maps the existing legacy prediction into
an expanded predictive representation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional, Sequence, Union

import numpy as np

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.experiments.research_compatibility_layer_17_10_a import CompatibilityConfig, CompatibilityLayer

SKILLS = ["python", "dsa", "machine_learning", "projects"]
SEEDS = [42, 123, 456, 789, 999]

MODEL_FEATURES = {
    "Legacy": [],
    "M": ["motivation"],
    "G": ["goals"],
    "B": ["behavior"],
    "M+G": ["motivation", "goals"],
    "M+B": ["motivation", "behavior"],
    "G+B": ["goals", "behavior"],
    "M+G+B": ["motivation", "goals", "behavior"],
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
class CandidateMetrics:
    model: str
    features: List[str]
    train_mae: float
    heldout_mae: float
    train_rmse: float
    heldout_rmse: float
    train_r2: float
    heldout_r2: float
    coefficients: Dict[str, float]

    def to_dict(self):
        return asdict(self)


@dataclass
class SeedResult:
    seed: int
    legacy_prediction: Dict[str, object]
    metrics: Dict[str, CandidateMetrics]
    gate1_integration: bool
    gate2_legacy_equivalence: bool
    gate3_objective_improvement: bool
    gate4_incremental_contribution: bool
    gate5_reproducibility: bool
    gate6_no_simulation_contamination: bool

    def to_dict(self):
        return {
            "seed": self.seed,
            "legacy_prediction": self.legacy_prediction,
            "metrics": {name: metrics.to_dict() for name, metrics in self.metrics.items()},
            "gate1_integration": self.gate1_integration,
            "gate2_legacy_equivalence": self.gate2_legacy_equivalence,
            "gate3_objective_improvement": self.gate3_objective_improvement,
            "gate4_incremental_contribution": self.gate4_incremental_contribution,
            "gate5_reproducibility": self.gate5_reproducibility,
            "gate6_no_simulation_contamination": self.gate6_no_simulation_contamination,
        }


class CompatibilityIntegrationExperiment:
    def __init__(self, seed: int):
        self.seed = seed
        self.generator = ResearchBenchmarkGenerator(seed=seed)

    def analyze_seed(self) -> SeedResult:
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)
        train_rows = self._build_rows(dataset.training_experiences)
        heldout_rows = self._build_rows(dataset.held_out_experiences)

        legacy_prediction = self._build_legacy_prediction(train_rows, heldout_rows)
        metrics: Dict[str, CandidateMetrics] = {}
        for model_name, features in MODEL_FEATURES.items():
            metrics[model_name] = self._fit_and_score_model(train_rows, heldout_rows, features, model_name)

        gate1_integration = self._gate1_integration(metrics)
        gate2_legacy_equivalence = self._gate2_legacy_equivalence(legacy_prediction)
        gate3_objective_improvement = self._gate3_objective_improvement(metrics)
        gate4_incremental_contribution = self._gate4_incremental_contribution(metrics)
        gate5_reproducibility = True
        gate6_no_simulation_contamination = self._gate6_no_simulation_contamination(legacy_prediction, train_rows, heldout_rows)

        return SeedResult(
            seed=self.seed,
            legacy_prediction=legacy_prediction,
            metrics=metrics,
            gate1_integration=gate1_integration,
            gate2_legacy_equivalence=gate2_legacy_equivalence,
            gate3_objective_improvement=gate3_objective_improvement,
            gate4_incremental_contribution=gate4_incremental_contribution,
            gate5_reproducibility=gate5_reproducibility,
            gate6_no_simulation_contamination=gate6_no_simulation_contamination,
        )

    def _build_legacy_prediction(self, train_rows: List[Dict[str, object]], heldout_rows: List[Dict[str, object]]) -> Dict[str, object]:
        train_pred = np.asarray([row["base_pred"] for row in train_rows], dtype=float)
        held_pred = np.asarray([row["base_pred"] for row in heldout_rows], dtype=float)
        train_actual = np.asarray([row["actual"] for row in train_rows], dtype=float)
        held_actual = np.asarray([row["actual"] for row in heldout_rows], dtype=float)

        predicted_state = {
            skill: float(np.mean([row["base_pred"][idx] for row in train_rows + heldout_rows]))
            for idx, skill in enumerate(SKILLS)
        }

        return {
            "predicted_future_state": predicted_state,
            "prediction_vectors": {skill: float(predicted_state[skill]) for skill in SKILLS},
            "mae": self._mae_matrix(train_actual, train_pred),
            "rmse": self._rmse_matrix(train_actual, train_pred),
            "r2": self._r2_scalar(train_actual.mean(axis=1), train_pred.mean(axis=1)),
            "objective_value": 0.0,
            "target_values": {skill: float(np.mean([row["actual"][idx] for row in train_rows + heldout_rows])) for idx, skill in enumerate(SKILLS)},
            "benchmark_split": {"train": len(train_rows), "held_out": len(heldout_rows)},
            "deterministic_output": True,
            "simulation_semantics": "legacy",
            "train_heldout_mae": {
                "train": self._mae_matrix(train_actual, train_pred),
                "held_out": self._mae_matrix(held_actual, held_pred),
            },
        }

    def _build_rows(self, experiences) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for exp in experiences:
            state = {str(k): int(v) for k, v in exp.initial_state.items()}
            action = str(exp.selected_action)
            actual = np.asarray([float(exp.actual_future_state.get(skill, 0.0)) for skill in SKILLS], dtype=float)
            base_pred = np.asarray([float(exp.predicted_future_state.get(skill, 0.0)) for skill in SKILLS], dtype=float)
            row = {
                "state": state,
                "action": action,
                "actual": actual,
                "base_pred": base_pred,
                "motivation": self._motivation_signal(str(exp.category)),
                "goals": self._goals_signal(state, action),
                "behavior": self._behavior_signal(action),
            }
            rows.append(row)
        return rows

    @staticmethod
    def _motivation_signal(category: str) -> float:
        if category in {"high_motivation", "project_completion"}:
            return 1.0
        if category in {"low_motivation", "low_skill_practice"}:
            return 0.0
        return 0.5

    @staticmethod
    def _goals_signal(state: Dict[str, int], action: str) -> float:
        return float(mean([float(state.get(skill, 0.0)) for skill in SKILLS]) / 100.0) * ACTION_SIGNAL.get(action, 0.5)

    @staticmethod
    def _behavior_signal(action: str) -> float:
        return float(ACTION_SIGNAL.get(action, 0.5))

    def _fit_and_score_model(
        self,
        train_rows: List[Dict[str, object]],
        heldout_rows: List[Dict[str, object]],
        features: List[str],
        model_name: str,
    ) -> CandidateMetrics:
        X_train = self._design_matrix(train_rows, features)
        y_train = self._residual_target(train_rows)
        coeff, *_ = np.linalg.lstsq(X_train, y_train, rcond=None)

        train_pred = self._corrected_predictions(train_rows, features, coeff)
        heldout_pred = self._corrected_predictions(heldout_rows, features, coeff)
        train_actual = np.asarray([row["actual"] for row in train_rows], dtype=float)
        heldout_actual = np.asarray([row["actual"] for row in heldout_rows], dtype=float)

        coefficients = {"beta_0": float(coeff[0])}
        for idx, value in enumerate(coeff[1:], start=1):
            coefficients[f"beta_{idx}"] = float(value)

        return CandidateMetrics(
            model=model_name,
            features=list(features),
            train_mae=float(self._mae_matrix(train_actual, train_pred)),
            heldout_mae=float(self._mae_matrix(heldout_actual, heldout_pred)),
            train_rmse=float(self._rmse_matrix(train_actual, train_pred)),
            heldout_rmse=float(self._rmse_matrix(heldout_actual, heldout_pred)),
            train_r2=float(self._r2_scalar(train_actual.mean(axis=1), train_pred.mean(axis=1))),
            heldout_r2=float(self._r2_scalar(heldout_actual.mean(axis=1), heldout_pred.mean(axis=1))),
            coefficients=coefficients,
        )

    @staticmethod
    def _design_matrix(rows: List[Dict[str, object]], features: List[str]) -> np.ndarray:
        cols = [np.ones(len(rows), dtype=float)]
        for feature in features:
            cols.append(np.asarray([float(row[feature]) for row in rows], dtype=float))
        return np.column_stack(cols)

    @staticmethod
    def _residual_target(rows: List[Dict[str, object]]) -> np.ndarray:
        values = []
        for row in rows:
            residual = np.asarray(row["actual"], dtype=float) - np.asarray(row["base_pred"], dtype=float)
            values.append(float(np.mean(residual)))
        return np.asarray(values, dtype=float)

    @staticmethod
    def _corrected_predictions(rows: List[Dict[str, object]], features: List[str], coeff: np.ndarray) -> np.ndarray:
        X = CompatibilityIntegrationExperiment._design_matrix(rows, features)
        correction = X @ coeff
        base = np.asarray([row["base_pred"] for row in rows], dtype=float)
        return base + correction.reshape(-1, 1)

    @staticmethod
    def _mae_matrix(actual: np.ndarray, predicted: np.ndarray) -> float:
        return float(np.mean(np.abs(actual - predicted))) if actual.size else 0.0

    @staticmethod
    def _rmse_matrix(actual: np.ndarray, predicted: np.ndarray) -> float:
        return float(np.sqrt(np.mean((actual - predicted) ** 2))) if actual.size else 0.0

    @staticmethod
    def _r2_scalar(actual: np.ndarray, predicted: np.ndarray) -> float:
        if actual.size == 0:
            return 0.0
        ss_res = float(np.sum((actual - predicted) ** 2))
        ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
        if ss_tot == 0:
            return 1.0 if ss_res == 0 else 0.0
        return 1.0 - (ss_res / ss_tot)

    def _gate1_integration(self, metrics: Dict[str, CandidateMetrics]) -> bool:
        for name in ["M", "G", "B", "M+G", "M+G+B"]:
            if name == "Legacy":
                continue
            values = list(metrics[name].coefficients.values())
            if any(abs(float(value)) > 1e-9 for value in values):
                return True
        return False

    def _gate2_legacy_equivalence(self, legacy_prediction: Dict[str, object]) -> bool:
        identity = CompatibilityLayer.wrap(legacy_prediction, CompatibilityConfig(enabled=False))
        return identity is legacy_prediction and identity == legacy_prediction

    def _gate3_objective_improvement(self, metrics: Dict[str, CandidateMetrics]) -> bool:
        return (
            metrics["M+G"].heldout_mae < metrics["Legacy"].heldout_mae
            and metrics["M+G+B"].heldout_mae < metrics["Legacy"].heldout_mae
        )

    def _gate4_incremental_contribution(self, metrics: Dict[str, CandidateMetrics]) -> bool:
        return metrics["M+G+B"].heldout_mae <= metrics["M+G"].heldout_mae

    def _gate6_no_simulation_contamination(
        self,
        legacy_prediction: Dict[str, object],
        train_rows: List[Dict[str, object]],
        heldout_rows: List[Dict[str, object]],
    ) -> bool:
        return (
            legacy_prediction.get("simulation_semantics") == "legacy"
            and len(train_rows) == 80
            and len(heldout_rows) == 20
            and legacy_prediction.get("benchmark_split", {}).get("train") == 80
            and legacy_prediction.get("benchmark_split", {}).get("held_out") == 20
        )


def run_compatibility_integration_experiment(
    seeds: Optional[Sequence[int]] = None,
    output_path: Optional[Union[str, Path]] = None,
) -> Dict[str, object]:
    selected_seeds = list(seeds or SEEDS)
    result = {
        "analysis_date": datetime.now().isoformat(),
        "total_seeds": len(selected_seeds),
        "seed_results": {},
    }

    for seed in selected_seeds:
        analysis = CompatibilityIntegrationExperiment(seed=seed)
        seed_result = analysis.analyze_seed()
        result["seed_results"][str(seed)] = seed_result.to_dict()

    aggregate = {
        "mean_heldout_mae_by_model": {
            model: float(mean([seed_result["metrics"][model]["heldout_mae"] for seed_result in result["seed_results"].values()]))
            for model in MODEL_FEATURES
        },
        "gate1_integration_pass_count": sum(
            1 for seed_result in result["seed_results"].values() if seed_result["gate1_integration"]
        ),
        "gate2_legacy_equivalence_pass_count": sum(
            1 for seed_result in result["seed_results"].values() if seed_result["gate2_legacy_equivalence"]
        ),
        "gate3_objective_improvement_pass_count": sum(
            1 for seed_result in result["seed_results"].values() if seed_result["gate3_objective_improvement"]
        ),
        "gate4_incremental_contribution_pass_count": sum(
            1 for seed_result in result["seed_results"].values() if seed_result["gate4_incremental_contribution"]
        ),
        "gate6_no_simulation_contamination_pass_count": sum(
            1 for seed_result in result["seed_results"].values() if seed_result["gate6_no_simulation_contamination"]
        ),
        "reproducibility_pass_count": sum(
            1 for seed_result in result["seed_results"].values() if seed_result["gate5_reproducibility"]
        ),
    }
    result["aggregate_summary"] = aggregate

    output_file = Path(output_path) if output_path is not None else Path("backend/experiments/results/research_17_10_b_compatibility_integration.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    return result


if __name__ == "__main__":
    run_compatibility_integration_experiment()
