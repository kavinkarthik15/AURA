"""
17.8C: Minimal State/Parameter Structure Analysis

Observational phase answering:

    What is the smallest state -> parameter -> prediction structure capable of
    representing the predictive information identified in 17.8A?

This module does NOT modify production calibration architecture. It evaluates
hypothetical representations against the deterministic benchmark.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Dict, List

import numpy as np

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator

SKILL_KEYS = ["python", "dsa", "machine_learning", "projects"]
SEED_SET = [42, 123, 456, 789, 999]

ACTION_SIGNAL = {
    "Python Project": 0.9,
    "DSA Practice": 0.75,
    "ML Course": 0.8,
    "Interview Prep": 0.75,
    "Build Portfolio": 1.0,
    "Research Paper": 0.8,
}

# Candidate structures for minimality test
# Parameter count includes intercept, so it matches the 17.8C gate table.
CANDIDATE_MODELS = [
    {"name": "current_bias_only", "features": [], "family": "current", "parameter_count": 1},
    {"name": "plus_motivation", "features": ["motivation"], "family": "candidate_a", "parameter_count": 2},
    {"name": "plus_goals", "features": ["goals"], "family": "candidate_a", "parameter_count": 2},
    {"name": "plus_behavior", "features": ["behavior"], "family": "candidate_a", "parameter_count": 2},
    {"name": "motivation_goals", "features": ["motivation", "goals"], "family": "candidate_a", "parameter_count": 3},
    {"name": "motivation_behavior", "features": ["motivation", "behavior"], "family": "candidate_a", "parameter_count": 3},
    {"name": "goals_behavior", "features": ["goals", "behavior"], "family": "candidate_a", "parameter_count": 3},
    {"name": "all_three", "features": ["motivation", "goals", "behavior"], "family": "candidate_a", "parameter_count": 4},
    # Candidate B: one aggregate state-conditioned signal.
    {"name": "aggregate_signal", "features": ["aggregate_signal"], "family": "candidate_b", "parameter_count": 2},
    # Candidate C: explicit linear minimal representation over all three.
    {"name": "minimal_linear", "features": ["motivation", "goals", "behavior"], "family": "candidate_c", "parameter_count": 4},
]


@dataclass
class CandidateMetrics:
    model: str
    family: str
    features: List[str]
    parameter_count: int
    train_mae: float
    heldout_mae: float
    delta_mae_vs_baseline: float
    train_rmse: float
    heldout_rmse: float
    delta_rmse_vs_baseline: float
    train_r2: float
    heldout_r2: float
    delta_r2_vs_baseline: float
    coefficients: Dict[str, float]
    supports_incremental_information: bool
    identifiability_rank: int
    identifiability_full_rank: bool
    identifiability_condition_number: float
    identifiable: bool
    nullspace_dimension: int

    def to_dict(self):
        return asdict(self)


@dataclass
class SeedMinimalStructureResult:
    seed: int
    total_events_train: int
    total_events_heldout: int
    runtime_seconds: float
    baseline_model: str
    candidate_metrics: Dict[str, CandidateMetrics]
    gate1_expressiveness: bool
    gate2_incremental_information: bool
    gate3_identifiability: bool
    gate4_minimality: bool
    minimal_sufficient_model: str
    minimal_sufficient_parameter_count: int
    outcome_label: str

    def to_dict(self):
        return {
            "seed": self.seed,
            "total_events_train": self.total_events_train,
            "total_events_heldout": self.total_events_heldout,
            "runtime_seconds": self.runtime_seconds,
            "baseline_model": self.baseline_model,
            "candidate_metrics": {k: v.to_dict() for k, v in self.candidate_metrics.items()},
            "gate1_expressiveness": self.gate1_expressiveness,
            "gate2_incremental_information": self.gate2_incremental_information,
            "gate3_identifiability": self.gate3_identifiability,
            "gate4_minimality": self.gate4_minimality,
            "minimal_sufficient_model": self.minimal_sufficient_model,
            "minimal_sufficient_parameter_count": self.minimal_sufficient_parameter_count,
            "outcome_label": self.outcome_label,
        }


@dataclass
class AnalysisResult:
    analysis_date: str
    total_seeds: int
    seed_results: Dict[int, SeedMinimalStructureResult] = field(default_factory=dict)

    def to_dict(self):
        return {
            "analysis_date": self.analysis_date,
            "total_seeds": self.total_seeds,
            "seed_results": {str(seed): result.to_dict() for seed, result in self.seed_results.items()},
        }


class MinimalStructureAnalyzer:
    """Evaluate hypothetical representational structures without production changes."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.generator = ResearchBenchmarkGenerator(seed=seed)

    def analyze_seed(self) -> SeedMinimalStructureResult:
        start = time.perf_counter()
        dataset = self.generator.generate_dataset(training_size=80, held_out_size=20)

        X_train_all = self._build_feature_matrix(dataset.training_experiences)
        y_train = self._build_target(dataset.training_experiences)
        X_heldout_all = self._build_feature_matrix(dataset.held_out_experiences)
        y_heldout = self._build_target(dataset.held_out_experiences)

        candidate_metrics: Dict[str, CandidateMetrics] = {}

        baseline_name = "current_bias_only"
        baseline_metrics = self._evaluate_model(
            model_spec=next(m for m in CANDIDATE_MODELS if m["name"] == baseline_name),
            X_train_all=X_train_all,
            y_train=y_train,
            X_heldout_all=X_heldout_all,
            y_heldout=y_heldout,
            baseline_mae=None,
            baseline_rmse=None,
            baseline_r2=None,
        )
        candidate_metrics[baseline_name] = baseline_metrics

        for model_spec in CANDIDATE_MODELS:
            if model_spec["name"] == baseline_name:
                continue
            metrics = self._evaluate_model(
                model_spec=model_spec,
                X_train_all=X_train_all,
                y_train=y_train,
                X_heldout_all=X_heldout_all,
                y_heldout=y_heldout,
                baseline_mae=baseline_metrics.heldout_mae,
                baseline_rmse=baseline_metrics.heldout_rmse,
                baseline_r2=baseline_metrics.heldout_r2,
            )
            candidate_metrics[model_spec["name"]] = metrics

        gate1_expressiveness = any(
            m.delta_r2_vs_baseline > 1e-9 for name, m in candidate_metrics.items() if name != baseline_name
        )
        gate2_incremental_information = any(
            m.delta_mae_vs_baseline > 1e-6 for name, m in candidate_metrics.items() if name != baseline_name
        )
        gate3_identifiability = any(
            m.identifiable and m.supports_incremental_information
            for name, m in candidate_metrics.items()
            if name != baseline_name
        )

        sufficient_models = [
            m
            for name, m in candidate_metrics.items()
            if name != baseline_name and m.supports_incremental_information and m.identifiable
        ]

        if sufficient_models:
            best_heldout_mae = min(m.heldout_mae for m in sufficient_models)
            pareto = [m for m in sufficient_models if abs(m.heldout_mae - best_heldout_mae) <= 1e-9]
            minimal = sorted(pareto, key=lambda x: (x.parameter_count, x.model))[0]
            gate4_minimality = True
            minimal_model_name = minimal.model
            minimal_param_count = minimal.parameter_count
            if minimal.parameter_count <= 2:
                outcome_label = "outcome_a_minimal_extension"
            else:
                outcome_label = "outcome_b_multi_dimension_required"
        else:
            gate4_minimality = False
            minimal_model_name = "none"
            minimal_param_count = 0
            outcome_label = "outcome_c_expanded_representation_fails"

        elapsed = time.perf_counter() - start

        return SeedMinimalStructureResult(
            seed=self.seed,
            total_events_train=len(dataset.training_experiences),
            total_events_heldout=len(dataset.held_out_experiences),
            runtime_seconds=float(elapsed),
            baseline_model=baseline_name,
            candidate_metrics=candidate_metrics,
            gate1_expressiveness=gate1_expressiveness,
            gate2_incremental_information=gate2_incremental_information,
            gate3_identifiability=gate3_identifiability,
            gate4_minimality=gate4_minimality,
            minimal_sufficient_model=minimal_model_name,
            minimal_sufficient_parameter_count=minimal_param_count,
            outcome_label=outcome_label,
        )

    def _evaluate_model(
        self,
        model_spec: Dict[str, object],
        X_train_all: Dict[str, np.ndarray],
        y_train: np.ndarray,
        X_heldout_all: Dict[str, np.ndarray],
        y_heldout: np.ndarray,
        baseline_mae: float | None,
        baseline_rmse: float | None,
        baseline_r2: float | None,
    ) -> CandidateMetrics:
        features: List[str] = list(model_spec["features"])
        family = str(model_spec["family"])
        name = str(model_spec["name"])
        parameter_count = int(model_spec["parameter_count"])

        X_train = self._assemble_design_matrix(X_train_all, features)
        X_heldout = self._assemble_design_matrix(X_heldout_all, features)

        coeff, rank, cond_num = self._fit_linear(X_train, y_train)

        y_train_pred = X_train @ coeff
        y_heldout_pred = X_heldout @ coeff

        train_mae = self._mae(y_train, y_train_pred)
        heldout_mae = self._mae(y_heldout, y_heldout_pred)
        train_rmse = self._rmse(y_train, y_train_pred)
        heldout_rmse = self._rmse(y_heldout, y_heldout_pred)
        train_r2 = self._r2(y_train, y_train_pred)
        heldout_r2 = self._r2(y_heldout, y_heldout_pred)

        if baseline_mae is None:
            delta_mae = 0.0
            delta_rmse = 0.0
            delta_r2 = 0.0
        else:
            delta_mae = float(baseline_mae - heldout_mae)
            delta_rmse = float(baseline_rmse - heldout_rmse)
            delta_r2 = float(heldout_r2 - baseline_r2)

        coefficient_map = {"beta_0": float(coeff[0])}
        for idx, feature in enumerate(features, start=1):
            coefficient_map[f"beta_{feature}"] = float(coeff[idx])

        # Full-rank + reasonable conditioning indicates distinguishable parameter effects.
        expected_rank = X_train.shape[1]
        full_rank = bool(int(rank) == int(expected_rank))
        identifiable = bool(full_rank and cond_num < 1e6)
        nullspace_dim = int(max(0, expected_rank - int(rank)))

        supports_incremental = bool((delta_mae > 1e-6) and (delta_r2 > 1e-9))

        return CandidateMetrics(
            model=name,
            family=family,
            features=features,
            parameter_count=parameter_count,
            train_mae=train_mae,
            heldout_mae=heldout_mae,
            delta_mae_vs_baseline=delta_mae,
            train_rmse=train_rmse,
            heldout_rmse=heldout_rmse,
            delta_rmse_vs_baseline=delta_rmse,
            train_r2=train_r2,
            heldout_r2=heldout_r2,
            delta_r2_vs_baseline=delta_r2,
            coefficients=coefficient_map,
            supports_incremental_information=supports_incremental,
            identifiability_rank=int(rank),
            identifiability_full_rank=full_rank,
            identifiability_condition_number=float(cond_num),
            identifiable=identifiable,
            nullspace_dimension=nullspace_dim,
        )

    @staticmethod
    def _assemble_design_matrix(feature_pool: Dict[str, np.ndarray], features: List[str]) -> np.ndarray:
        n_rows = len(next(iter(feature_pool.values())))
        cols = [np.ones(n_rows, dtype=float)]
        for feature in features:
            cols.append(feature_pool[feature])
        return np.column_stack(cols)

    @staticmethod
    def _fit_linear(X: np.ndarray, y: np.ndarray):
        coeff, *_ = np.linalg.lstsq(X, y, rcond=None)
        rank = np.linalg.matrix_rank(X)
        cond_num = np.linalg.cond(X)
        return coeff, rank, cond_num

    @staticmethod
    def _build_target(experiences) -> np.ndarray:
        values = []
        for exp in experiences:
            initial = [float(exp.initial_state.get(k, 0.0)) for k in SKILL_KEYS]
            actual = [float(exp.actual_future_state.get(k, 0.0)) for k in SKILL_KEYS]
            values.append(mean(actual) - mean(initial))
        return np.asarray(values, dtype=float)

    def _build_feature_matrix(self, experiences) -> Dict[str, np.ndarray]:
        motivation = []
        goals = []
        behavior = []
        aggregate_signal = []

        for exp in experiences:
            state = {str(k): float(v) for k, v in exp.initial_state.items()}
            action = str(exp.selected_action)
            category = str(exp.category)

            mean_skill = mean([float(state.get(k, 0.0)) for k in SKILL_KEYS])
            action_signal = float(ACTION_SIGNAL.get(action, 0.5))

            motivation_signal = self._motivation_signal(category)
            goal_signal = float((mean_skill / 100.0) * action_signal)
            behavior_signal = action_signal
            aggregate = float((motivation_signal + goal_signal + behavior_signal) / 3.0)

            motivation.append(motivation_signal)
            goals.append(goal_signal)
            behavior.append(behavior_signal)
            aggregate_signal.append(aggregate)

        return {
            "motivation": np.asarray(motivation, dtype=float),
            "goals": np.asarray(goals, dtype=float),
            "behavior": np.asarray(behavior, dtype=float),
            "aggregate_signal": np.asarray(aggregate_signal, dtype=float),
        }

    @staticmethod
    def _motivation_signal(category: str) -> float:
        if category in {"high_motivation", "project_completion"}:
            return 1.0
        if category in {"low_motivation", "low_skill_practice"}:
            return 0.0
        return 0.5

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


class ResearchPhase17_8_C:
    """Run 17.8C minimal structure analysis across seeds."""

    def __init__(self, seeds: List[int] | None = None):
        self.seeds = seeds or SEED_SET

    def run(self) -> AnalysisResult:
        result = AnalysisResult(
            analysis_date=datetime.now().isoformat(),
            total_seeds=len(self.seeds),
            seed_results={},
        )

        print("\n" + "=" * 120)
        print("Phase 17.8C: Minimal State/Parameter Structure Analysis")
        print("=" * 120)

        for seed in self.seeds:
            analyzer = MinimalStructureAnalyzer(seed=seed)
            seed_result = analyzer.analyze_seed()
            result.seed_results[seed] = seed_result

            print(f"\nSeed {seed}: runtime={seed_result.runtime_seconds:.3f}s")
            print(
                f"  gates: expressiveness={seed_result.gate1_expressiveness} "
                f"incremental={seed_result.gate2_incremental_information} "
                f"identifiability={seed_result.gate3_identifiability} "
                f"minimality={seed_result.gate4_minimality}"
            )
            print(
                f"  minimal_sufficient_model={seed_result.minimal_sufficient_model} "
                f"params={seed_result.minimal_sufficient_parameter_count} "
                f"outcome={seed_result.outcome_label}"
            )

            baseline = seed_result.candidate_metrics[seed_result.baseline_model]
            for name, metrics in seed_result.candidate_metrics.items():
                print(
                    f"  - {name:<22} p={metrics.parameter_count} "
                    f"heldout_mae={metrics.heldout_mae:>7.4f} "
                    f"dMAE={metrics.delta_mae_vs_baseline:>8.4f} "
                    f"dR2={metrics.delta_r2_vs_baseline:>8.4f} "
                    f"ident={str(metrics.identifiable):<5}"
                )
                if name == baseline.model:
                    continue

        self._save_results(result)
        return result

    def _save_results(self, result: AnalysisResult):
        results_dir = Path("backend/experiments/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / "research_17_8_c_minimal_structure.json"
        with open(path, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\n[OK] Results saved to {path}")


if __name__ == "__main__":
    ResearchPhase17_8_C().run()
