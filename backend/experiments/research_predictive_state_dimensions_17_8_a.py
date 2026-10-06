"""
17.8A: Predictive State Dimension Analysis

Observational diagnostic to answer:

    What information must a calibration state contain for it to predict future outcomes?

This phase does not modify the production calibrator or state model. It analyzes the
predictive value of existing AURA-like state dimensions using the benchmark dataset.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, List

import numpy as np

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator

SKILL_KEYS = ["python", "dsa", "machine_learning", "projects"]
CANDIDATE_DIMENSIONS = [
    "skills",
    "knowledge",
    "projects",
    "goals",
    "learning",
    "motivation",
    "confidence",
    "behavior",
]


def _action_signal(action: str) -> float:
    action_key = action.lower()
    if "project" in action_key or "portfolio" in action_key:
        return 1.0
    if "dsa" in action_key or "interview" in action_key:
        return 0.75
    if "ml" in action_key or "paper" in action_key:
        return 0.8
    if "python" in action_key:
        return 0.9
    return 0.5


@dataclass
class DimensionMeasurement:
    dimension: str
    variation_score: float
    baseline_mae: float
    augmented_mae: float
    delta_mae: float
    baseline_rmse: float
    augmented_rmse: float
    delta_rmse: float
    baseline_r2: float
    augmented_r2: float
    delta_r2: float
    standalone_predictive_strength: float
    conditional_predictive_strength: float
    status: str
    interpretation: str

    def to_dict(self):
        return asdict(self)


@dataclass
class SeedDimensionResult:
    seed: int
    total_events: int
    measurements: List[DimensionMeasurement]

    def to_dict(self):
        return {
            "seed": self.seed,
            "total_events": self.total_events,
            "measurements": [m.to_dict() for m in self.measurements],
        }


@dataclass
class AnalysisResult:
    analysis_date: str
    total_seeds: int
    seed_results: Dict[int, SeedDimensionResult] = field(default_factory=dict)

    def to_dict(self):
        return {
            "analysis_date": self.analysis_date,
            "total_seeds": self.total_seeds,
            "seed_results": {str(seed): result.to_dict() for seed, result in self.seed_results.items()},
        }


class PredictiveStateDimensionAnalyzer:
    """Measure how much each candidate state dimension explains future-state change."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.generator = ResearchBenchmarkGenerator(seed=seed)

    def analyze_seed(self) -> SeedDimensionResult:
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)
        measurements: List[DimensionMeasurement] = []
        targets = self._targets(dataset)
        base_matrix = self._base_skill_matrix(dataset)

        for dimension in CANDIDATE_DIMENSIONS:
            dimension_values = self._dimension_matrix(dataset, dimension)
            if dimension_values.shape[1] == 0:
                continue

            baseline_model = self._fit_linear_model(base_matrix, targets)
            augmented_matrix = np.hstack([base_matrix, dimension_values])
            augmented_model = self._fit_linear_model(augmented_matrix, targets)

            baseline_preds = baseline_model.predict(base_matrix)
            augmented_preds = augmented_model.predict(augmented_matrix)

            baseline_mae = self._mae(targets, baseline_preds)
            augmented_mae = self._mae(targets, augmented_preds)
            delta_mae = baseline_mae - augmented_mae

            baseline_rmse = self._rmse(targets, baseline_preds)
            augmented_rmse = self._rmse(targets, augmented_preds)
            delta_rmse = baseline_rmse - augmented_rmse

            baseline_r2 = self._r2(targets, baseline_preds)
            augmented_r2 = self._r2(targets, augmented_preds)
            delta_r2 = augmented_r2 - baseline_r2

            variation_score = float(pstdev(dimension_values.ravel())) if dimension_values.size > 1 else 0.0
            standalone = max(0.0, float(delta_r2)) if variation_score > 0 else 0.0

            interaction_matrix = self._interaction_matrix(dataset, dimension)
            conditional_model = self._fit_linear_model(np.hstack([base_matrix, interaction_matrix]), targets)
            conditional_preds = conditional_model.predict(np.hstack([base_matrix, interaction_matrix]))
            conditional_strength = max(0.0, float(self._r2(targets, conditional_preds) - baseline_r2))

            status = self._status_label(delta_r2, conditional_strength, variation_score)
            interpretation = self._interpretation(dimension, delta_r2, conditional_strength, variation_score)

            measurements.append(
                DimensionMeasurement(
                    dimension=dimension,
                    variation_score=variation_score,
                    baseline_mae=baseline_mae,
                    augmented_mae=augmented_mae,
                    delta_mae=delta_mae,
                    baseline_rmse=baseline_rmse,
                    augmented_rmse=augmented_rmse,
                    delta_rmse=delta_rmse,
                    baseline_r2=baseline_r2,
                    augmented_r2=augmented_r2,
                    delta_r2=delta_r2,
                    standalone_predictive_strength=standalone,
                    conditional_predictive_strength=conditional_strength,
                    status=status,
                    interpretation=interpretation,
                )
            )

        return SeedDimensionResult(seed=self.seed, total_events=len(dataset.training_experiences), measurements=measurements)

    def _targets(self, dataset) -> np.ndarray:
        values = []
        for experience in dataset.training_experiences:
            actual = {str(k): float(v) for k, v in experience.actual_future_state.items()}
            initial = {str(k): float(v) for k, v in experience.initial_state.items()}
            values.append(mean(actual.values()) - mean(initial.values()))
        return np.asarray(values, dtype=float)

    def _base_skill_matrix(self, dataset) -> np.ndarray:
        rows = []
        for experience in dataset.training_experiences:
            state = experience.initial_state
            rows.append([float(state.get(k, 0.0)) for k in SKILL_KEYS])
        return np.asarray(rows, dtype=float)

    def _dimension_matrix(self, dataset, dimension: str) -> np.ndarray:
        values = []
        for experience in dataset.training_experiences:
            state = experience.initial_state
            if dimension == "skills":
                values.append([float(state.get(k, 0.0)) for k in SKILL_KEYS])
            elif dimension == "knowledge":
                mean_skill = mean([float(state.get(k, 0.0)) for k in SKILL_KEYS])
                values.append([mean_skill])
            elif dimension == "projects":
                values.append([float(state.get("projects", 0.0))])
            elif dimension == "goals":
                goal_alignment = float(mean([float(state.get(k, 0.0)) for k in SKILL_KEYS]) * (1.0 + 0.15 * _action_signal(experience.selected_action)))
                values.append([goal_alignment])
            elif dimension == "learning":
                learning_signal = float(mean([float(state.get(k, 0.0)) for k in SKILL_KEYS]) / 100.0)
                values.append([learning_signal])
            elif dimension == "motivation":
                if experience.category in {"high_motivation", "project_completion"}:
                    val = 1.0
                elif experience.category in {"low_motivation", "low_skill_practice"}:
                    val = 0.0
                else:
                    val = 0.5
                values.append([val])
            elif dimension == "confidence":
                conf = float(max(0.0, min(1.0, mean([float(state.get(k, 0.0)) for k in SKILL_KEYS]) / 100.0)))
                values.append([conf])
            elif dimension == "behavior":
                values.append([_action_signal(experience.selected_action)])
            else:
                values.append([0.0])
        return np.asarray(values, dtype=float)

    def _interaction_matrix(self, dataset, dimension: str) -> np.ndarray:
        base = self._base_skill_matrix(dataset)
        dim_values = self._dimension_matrix(dataset, dimension)
        if dim_values.ndim == 1:
            dim_values = dim_values.reshape(-1, 1)
        interaction = base * dim_values
        return interaction

    def _fit_linear_model(self, X: np.ndarray, y: np.ndarray):
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        design = np.column_stack([np.ones(X.shape[0]), X])
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)

        class Model:
            def __init__(self, coeff):
                self.coeff = coeff

            def predict(self, arr):
                arr2 = np.asarray(arr, dtype=float)
                if arr2.ndim == 1:
                    arr2 = arr2.reshape(-1, 1)
                design2 = np.column_stack([np.ones(arr2.shape[0]), arr2])
                return design2 @ self.coeff

        return Model(coef)

    @staticmethod
    def _mae(actual: np.ndarray, predicted: np.ndarray) -> float:
        return float(np.mean(np.abs(actual - predicted))) if actual.size else 0.0

    @staticmethod
    def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
        return float(np.sqrt(np.mean((actual - predicted) ** 2))) if actual.size else 0.0

    @staticmethod
    def _r2(actual: np.ndarray, predicted: np.ndarray) -> float:
        if actual.size == 0:
            return 0.0
        ss_res = float(np.sum((actual - predicted) ** 2))
        ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
        if ss_tot == 0:
            return 1.0 if ss_res == 0 else 0.0
        return 1.0 - (ss_res / ss_tot)

    @staticmethod
    def _status_label(delta_r2: float, conditional_strength: float, variation_score: float) -> str:
        if delta_r2 > 0.10 or conditional_strength > 0.10:
            return "strong"
        if delta_r2 > 0.02 or conditional_strength > 0.02:
            return "moderate"
        if variation_score < 1e-6:
            return "inactive"
        return "weak"

    @staticmethod
    def _interpretation(dimension: str, delta_r2: float, conditional_strength: float, variation_score: float) -> str:
        if delta_r2 > 0.10:
            return f"{dimension} carries direct predictive information and materially improves the future-state model."
        if conditional_strength > 0.10:
            return f"{dimension} has limited standalone value but strong conditional value when interacting with action/state context."
        if variation_score < 1e-6:
            return f"{dimension} is effectively constant across the benchmark and therefore cannot explain future-state variation."
        return f"{dimension} shows weak predictive signal in the current benchmark and is unlikely to be a meaningful calibration target alone."


class ResearchPhase17_8_A:
    """Run the 17.8A predictive state dimension analysis across several seeds."""

    def __init__(self, seeds: List[int] | None = None):
        self.seeds = seeds or [42, 123, 456, 789, 999]

    def run(self) -> AnalysisResult:
        result = AnalysisResult(
            analysis_date=datetime.now().isoformat(),
            total_seeds=len(self.seeds),
            seed_results={},
        )

        print("\n" + "=" * 120)
        print("Phase 17.8A: Predictive State Dimension Analysis")
        print("=" * 120)

        for seed in self.seeds:
            analyzer = PredictiveStateDimensionAnalyzer(seed=seed)
            seed_result = analyzer.analyze_seed()
            result.seed_results[seed] = seed_result
            print(f"\nSeed {seed}:")
            for measurement in seed_result.measurements:
                print(
                    f"  - {measurement.dimension:<12} "
                    f"status={measurement.status:<8} "
                    f"delta_r2={measurement.delta_r2:>7.4f} "
                    f"delta_mae={measurement.delta_mae:>7.4f} "
                    f"var={measurement.variation_score:>7.4f}"
                )

        self._save_results(result)
        return result

    def _save_results(self, result: AnalysisResult):
        results_dir = Path("backend/experiments/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / "research_17_8_a_predictive_state_dimensions.json"
        with open(path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\n[OK] Results saved to {path}")


if __name__ == "__main__":
    ResearchPhase17_8_A().run()
