"""
17.0B Research Experiment Runner

Compares Baseline (no learning) vs Learning (with calibration) on research dataset.

Pipeline:
1. Load research_benchmark_v1_seed_42 (80 training, 20 held-out)
2. Baseline: predict on all 100, no calibration updates
3. Learning: predict on 80 training, calibrate after each, then predict on 20 held-out
4. Compare MAE: baseline_mae vs learning_mae

Success criterion: learning_mae < baseline_mae
"""

from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field

from backend.experiments.research_experience import ResearchDataset
from backend.experiments.research_dataset_persistence import (
    ResearchDatasetPersistence,
)
from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.services.digital_twin_calibrator import DigitalTwinCalibrator
from backend.services.calibration_applier import CalibrationApplier
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator
from backend.services.simulation_engine import SimulationEngine
from backend.services.transition_engine import TransitionEngine
from backend.services.experience_service import experience_service


class ExperiencePredictionRecord(BaseModel):
    """Record of a single prediction on a research experience."""

    experience_id: str
    predicted_future_state: Dict[str, int]
    actual_future_state: Dict[str, int]
    mae: float


class SystemResults(BaseModel):
    """Results for one system (Baseline or Learning)."""

    system_name: str
    final_calibration_parameters: CalibrationParameters
    training_predictions: list[ExperiencePredictionRecord] = Field(
        default_factory=list
    )
    held_out_predictions: list[ExperiencePredictionRecord] = Field(
        default_factory=list
    )

    def training_mae(self) -> float:
        """MAE on training experiences."""
        if not self.training_predictions:
            return 0.0
        errors = [p.mae for p in self.training_predictions]
        return round(sum(errors) / len(errors), 4)

    def held_out_mae(self) -> float:
        """MAE on held-out experiences (primary metric)."""
        if not self.held_out_predictions:
            return 0.0
        errors = [p.mae for p in self.held_out_predictions]
        return round(sum(errors) / len(errors), 4)


class ResearchExperimentResult(BaseModel):
    """Complete results for 17.0B experiment."""

    experiment_id: str
    dataset_id: str
    timestamp: str
    seed: int
    training_size: int
    held_out_size: int
    learning_rate: float

    baseline_results: SystemResults
    learning_results: SystemResults

    baseline_mae: float
    learning_mae: float
    absolute_improvement: float
    improvement_percent: float
    learning_is_better: bool

    model_config = {"validate_assignment": True, "extra": "forbid"}

    def success(self) -> bool:
        """Pass criterion: learning_mae < baseline_mae"""
        return self.learning_is_better


class ResearchExperiment17_0_B:
    """Run 17.0B experiment comparing Baseline vs Learning."""

    def __init__(
        self,
        dataset: ResearchDataset,
        learning_rate: float = 0.1,
        bounds: Dict[str, float] | None = None,
    ):
        self.dataset = dataset
        self.learning_rate = learning_rate
        self.bounds = bounds or {
            "state_adjustment_max": 5.0,
            "probability_bias_max": 0.2,
            "risk_bias_max": 0.2,
            "uncertainty_increment_max": 0.3,
            "confidence_increment_max": 0.1,
        }
        self.calibrator = DigitalTwinCalibrator()
        self.applier = CalibrationApplier()
        self.error_evaluator = PredictionErrorEvaluator()
        self.transition_engine = TransitionEngine(
            experiences=experience_service.get_all_experiences()
        )

    def run(self, experiment_id: str | None = None) -> ResearchExperimentResult:
        """Run the full experiment."""
        exp_id = (
            experiment_id
            or f"research_17_0_b_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        # Run baseline (no learning)
        baseline_results = self._run_baseline()

        # Run learning system
        learning_results = self._run_learning()

        # Compute metrics
        baseline_mae = baseline_results.held_out_mae()
        learning_mae = learning_results.held_out_mae()
        absolute_improvement = round(baseline_mae - learning_mae, 4)
        improvement_percent = (
            round(
                (absolute_improvement / baseline_mae * 100) if baseline_mae > 0 else 0,
                2,
            )
            if baseline_mae > 0
            else 0.0
        )
        learning_is_better = learning_mae < baseline_mae

        return ResearchExperimentResult(
            experiment_id=exp_id,
            dataset_id=self.dataset.dataset_id,
            timestamp=datetime.now().isoformat(),
            seed=self.dataset.seed,
            training_size=self.dataset.training_size(),
            held_out_size=self.dataset.held_out_size(),
            learning_rate=self.learning_rate,
            baseline_results=baseline_results,
            learning_results=learning_results,
            baseline_mae=baseline_mae,
            learning_mae=learning_mae,
            absolute_improvement=absolute_improvement,
            improvement_percent=improvement_percent,
            learning_is_better=learning_is_better,
        )

    def _run_baseline(self) -> SystemResults:
        """Run baseline system: no learning, predict on all experiences."""
        # Baseline uses empty calibration (no bias)
        baseline_sim = SimulationEngine(
            transition_engine=self.transition_engine,
            calibration_parameters=None,  # No calibration
        )

        # Predict on training (but don't calibrate)
        training_preds = []
        for exp in self.dataset.training_experiences:
            pred_result = baseline_sim.simulate_action(
                exp.initial_state, exp.selected_action
            )
            mae = self._calculate_mae(
                pred_result["predicted_future_state"], exp.actual_future_state
            )
            training_preds.append(
                ExperiencePredictionRecord(
                    experience_id=exp.experience_id,
                    predicted_future_state=pred_result["predicted_future_state"],
                    actual_future_state=exp.actual_future_state,
                    mae=mae,
                )
            )

        # Predict on held-out
        held_out_preds = []
        for exp in self.dataset.held_out_experiences:
            pred_result = baseline_sim.simulate_action(
                exp.initial_state, exp.selected_action
            )
            mae = self._calculate_mae(
                pred_result["predicted_future_state"], exp.actual_future_state
            )
            held_out_preds.append(
                ExperiencePredictionRecord(
                    experience_id=exp.experience_id,
                    predicted_future_state=pred_result["predicted_future_state"],
                    actual_future_state=exp.actual_future_state,
                    mae=mae,
                )
            )

        return SystemResults(
            system_name="Baseline",
            final_calibration_parameters=CalibrationParameters(),
            training_predictions=training_preds,
            held_out_predictions=held_out_preds,
        )

    def _run_learning(self) -> SystemResults:
        """Run learning system: calibrate after each training experience."""
        # Start with empty calibration
        current_params = CalibrationParameters()

        # Predict on training, calibrate after each
        training_preds = []
        for exp in self.dataset.training_experiences:
            # Create simulation engine with current parameters
            sim = SimulationEngine(
                transition_engine=self.transition_engine,
                calibration_parameters=current_params,
            )

            # Predict
            pred_result = sim.simulate_action(
                exp.initial_state, exp.selected_action
            )

            # Record prediction
            mae = self._calculate_mae(
                pred_result["predicted_future_state"], exp.actual_future_state
            )
            training_preds.append(
                ExperiencePredictionRecord(
                    experience_id=exp.experience_id,
                    predicted_future_state=pred_result["predicted_future_state"],
                    actual_future_state=exp.actual_future_state,
                    mae=mae,
                )
            )

            # Calibrate: create DecisionOutcome and evaluate error
            decision = DecisionOutcome(
                decision_id=exp.experience_id,
                timestamp=datetime.now().isoformat(),
                selected_action=exp.selected_action,
                predicted_state=pred_result["predicted_future_state"],
                predicted_trajectory_score=0.5,  # Research: fixed for determinism
                predicted_probability=0.5,  # Research: fixed for determinism
                predicted_risk=0.3,  # Research: fixed for determinism
                predicted_uncertainty=0.2,  # Research: fixed for determinism
                actual_state=exp.actual_future_state,
            )

            error_result = self.error_evaluator.evaluate(decision)

            # Get calibration update
            calib_result = self.calibrator.calibrate(
                error_result,
                current_parameters=current_params,
                learning_rate=self.learning_rate,
                bounds=self.bounds,
            )

            # Apply calibration
            current_params = self.applier.apply(current_params, calib_result)

        # Now predict on held-out with final calibrated parameters
        final_sim = SimulationEngine(
            transition_engine=self.transition_engine,
            calibration_parameters=current_params,
        )

        held_out_preds = []
        for exp in self.dataset.held_out_experiences:
            pred_result = final_sim.simulate_action(
                exp.initial_state, exp.selected_action
            )
            mae = self._calculate_mae(
                pred_result["predicted_future_state"], exp.actual_future_state
            )
            held_out_preds.append(
                ExperiencePredictionRecord(
                    experience_id=exp.experience_id,
                    predicted_future_state=pred_result["predicted_future_state"],
                    actual_future_state=exp.actual_future_state,
                    mae=mae,
                )
            )

        return SystemResults(
            system_name="Learning",
            final_calibration_parameters=current_params,
            training_predictions=training_preds,
            held_out_predictions=held_out_preds,
        )

    def _calculate_mae(
        self, predicted_state: Dict[str, int], actual_state: Dict[str, int]
    ) -> float:
        """Calculate MAE between predicted and actual states."""
        keys = set(predicted_state.keys()) | set(actual_state.keys())
        if not keys:
            return 0.0
        errors = [
            abs(predicted_state.get(k, 0) - actual_state.get(k, 0))
            for k in keys
        ]
        return round(sum(errors) / len(errors), 4)


def run_research_experiment_17_0_b(
    dataset_id: str = "research_benchmark_v1_seed_42",
    learning_rate: float = 0.1,
    experiment_id: str | None = None,
) -> ResearchExperimentResult:
    """
    Convenience function to load dataset and run experiment.

    Args:
        dataset_id: ID of research dataset to use
        learning_rate: Learning rate for calibration
        experiment_id: Optional custom experiment ID

    Returns:
        ResearchExperimentResult with comparison
    """
    persistence = ResearchDatasetPersistence()
    dataset = persistence.load_dataset(dataset_id)

    experiment = ResearchExperiment17_0_B(dataset, learning_rate=learning_rate)
    return experiment.run(experiment_id=experiment_id)
