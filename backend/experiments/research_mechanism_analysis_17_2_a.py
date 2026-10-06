"""
17.2A Learning Mechanism Analysis

Investigates HOW the calibration mechanism learns systematic prediction biases.

Research Question:
    Does the calibration mechanism actually learn the underlying systematic 
    prediction bias from experience?

Methodology:
    1. Load 17.0 learnable benchmark with known per-category systematic biases
    2. Track calibration parameters after each training experience
    3. Compare learned expected_state_bias against ground-truth systematic bias
    4. Measure whether learned bias converges toward true bias
    5. Analyze error reduction trajectory during training

Key Metrics:
    - Calibration trajectory: parameter evolution over training
    - Bias convergence: learned bias vs true bias distance
    - Error reduction: MAE decrease as calibration progresses
    - Direction alignment: whether learned bias moves toward correction
"""

from datetime import datetime
from typing import Dict, Any, Optional
from copy import deepcopy
import json

from pydantic import BaseModel, Field

from backend.experiments.research_benchmark_generator import (
    ResearchBenchmarkGenerator,
)
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


class CalibrationParameterSnapshot(BaseModel):
    """Snapshot of calibration parameters at a single training step."""

    step: int  # Training experience index (0-79)
    experience_id: str
    category: str
    expected_state_bias: Dict[str, float] = Field(
        default_factory=dict,
        description="Learned state bias adjustments per skill",
    )
    transition_probability_bias: float = 0.0
    risk_bias: float = 0.0
    uncertainty: float = 0.5
    confidence: float = 0.5
    prediction_error: float  # MAE for this experience
    cumulative_mae: float  # MAE over all seen so far


class BiasComparisonPoint(BaseModel):
    """Comparison between learned bias and true systematic bias at a step."""

    step: int
    experience_id: str
    category: str
    true_systematic_bias: float  # Known from benchmark
    learned_state_bias_avg: float  # Average of learned expected_state_bias
    bias_distance: float  # |learned - true|
    direction_correct: bool  # Whether learned bias sign matches true bias sign
    magnitude_ratio: float  # |learned| / |true| (how close to magnitude)


class MechanismAnalysisResult(BaseModel):
    """Complete mechanism analysis for a single seed."""

    experiment_id: str
    seed: int
    dataset_id: str
    timestamp: str
    learning_rate: float
    bounds: Dict[str, float]

    # Trajectory data
    calibration_trajectory: list[CalibrationParameterSnapshot] = Field(
        default_factory=list,
        description="Calibration parameters over training progression",
    )
    bias_comparisons: list[BiasComparisonPoint] = Field(
        default_factory=list,
        description="Learned vs true bias at each step",
    )

    # Summary statistics
    initial_mae: float  # MAE with no calibration on first experience
    final_mae: float  # MAE with full calibration
    total_mae_reduction: float  # initial_mae - final_mae
    convergence_rate: float  # How quickly bias converges (0-100%)

    # Per-category analysis
    category_bias_distances: Dict[str, float] = Field(
        default_factory=dict,
        description="Average bias distance per category",
    )
    category_direction_accuracy: Dict[str, float] = Field(
        default_factory=dict,
        description="Fraction of steps with correct direction per category",
    )

    # Convergence verdict
    is_learning: bool  # Does final MAE < initial MAE?
    is_converging: bool  # Does bias systematically approach true value?
    learning_explanation: str  # Human-readable summary


class ResearchMechanismAnalyzer:
    """
    Analyzes how calibration learns systematic prediction biases.

    Process:
    1. Load dataset with known systematic biases per category
    2. Process training experiences one by one
    3. Track calibration parameter evolution
    4. Compare learned bias against ground truth
    5. Produce trajectory and convergence analysis
    """

    # Known systematic biases from benchmark (same as generator)
    CATEGORY_SYSTEMATIC_BIAS: Dict[str, int] = {
        "low_skill_practice": 4,
        "medium_skill_practice": 3,
        "high_skill_practice": -3,
        "low_motivation": 5,
        "high_motivation": -4,
        "mixed_skills": 3,
        "project_completion": 5,
        "plateau": 0,
    }

    def __init__(
        self,
        dataset: Optional[Any] = None,
        seed: int = 42,
        learning_rate: float = 0.007,
        bounds: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize mechanism analyzer.

        Args:
            dataset: Pre-existing research dataset (or None to generate)
            seed: Random seed for benchmark generation
            learning_rate: Calibration learning rate
            bounds: Calibration parameter bounds
        """
        self.seed = seed
        self.learning_rate = learning_rate
        self.bounds = bounds or {
            "state_adjustment_max": 0.12,
            "probability_bias_max": 0.012,
            "risk_bias_max": 0.012,
            "uncertainty_increment_max": 0.012,
            "confidence_increment_max": 0.012,
        }

        # Load or generate dataset
        if dataset is not None:
            self.dataset = dataset
            self.dataset_id = dataset.dataset_id
        else:
            gen = ResearchBenchmarkGenerator(seed=seed)
            self.dataset = gen.generate_dataset(training_size=80, held_out_size=20)
            self.dataset_id = self.dataset.dataset_id

        # Services for prediction and calibration
        self.calibrator = DigitalTwinCalibrator()
        self.applier = CalibrationApplier()
        self.evaluator = PredictionErrorEvaluator()
        self.transition_engine = TransitionEngine()

    def run(self, experiment_id: str = "research_mechanism_17_2_a") -> MechanismAnalysisResult:
        """
        Run mechanism analysis on training dataset.

        Tracks calibration evolution and compares against known systematic biases.

        Returns:
            MechanismAnalysisResult with full trajectory and analysis
        """
        from datetime import datetime as dt

        trajectory: list[CalibrationParameterSnapshot] = []
        bias_comparisons: list[BiasComparisonPoint] = []

        current_params = CalibrationParameters()
        prediction_errors: list[float] = []

        # Process training experiences one by one
        for step_idx, experience in enumerate(self.dataset.training_experiences):
            # Step 1: Get prediction with current calibration parameters
            initial_state = experience.initial_state
            action = experience.selected_action

            # Simulate predicted outcome
            sim = SimulationEngine(
                transition_engine=self.transition_engine,
                calibration_parameters=current_params,
            )
            pred_result = sim.simulate_action(initial_state, action)
            predicted_future = pred_result["predicted_future_state"]

            # Ground truth
            actual_future = experience.actual_future_state

            # Step 2: Evaluate prediction error using DecisionOutcome
            decision = DecisionOutcome(
                decision_id=experience.experience_id,
                timestamp=dt.now().isoformat(),
                selected_action=action,
                predicted_state=predicted_future,
                predicted_trajectory_score=0.5,
                predicted_probability=0.5,
                predicted_risk=0.3,
                predicted_uncertainty=0.2,
                actual_state=actual_future,
            )

            error_result = self.evaluator.evaluate(decision)

            mae = float(error_result.prediction_error) or 0.0
            prediction_errors.append(mae)

            # Step 3: Apply calibration
            calibration_result = self.calibrator.calibrate(
                error_result=error_result,
                current_parameters=current_params,
                learning_rate=self.learning_rate,
                bounds=self.bounds,
            )
            current_params = calibration_result.updated_parameters

            # Step 4: Record trajectory
            trajectory.append(
                CalibrationParameterSnapshot(
                    step=step_idx,
                    experience_id=experience.experience_id,
                    category=experience.category,
                    expected_state_bias=dict(current_params.expected_state_bias),
                    transition_probability_bias=current_params.transition_probability_bias,
                    risk_bias=current_params.risk_bias,
                    uncertainty=current_params.uncertainty,
                    confidence=current_params.confidence,
                    prediction_error=round(mae, 4),
                    cumulative_mae=round(
                        sum(prediction_errors) / len(prediction_errors), 4
                    ),
                )
            )

            # Step 5: Compare learned bias against true systematic bias
            true_bias = float(self.CATEGORY_SYSTEMATIC_BIAS[experience.category])

            # Learned bias: average of expected_state_bias values
            learned_biases = list(current_params.expected_state_bias.values())
            learned_bias_avg = (
                sum(learned_biases) / len(learned_biases) if learned_biases else 0.0
            )

            bias_distance = abs(learned_bias_avg - true_bias)
            direction_correct = (learned_bias_avg * true_bias) >= 0  # Same sign
            magnitude_ratio = (
                abs(learned_bias_avg) / abs(true_bias)
                if true_bias != 0
                else (1.0 if learned_bias_avg == 0 else 0.0)
            )

            bias_comparisons.append(
                BiasComparisonPoint(
                    step=step_idx,
                    experience_id=experience.experience_id,
                    category=experience.category,
                    true_systematic_bias=true_bias,
                    learned_state_bias_avg=round(learned_bias_avg, 4),
                    bias_distance=round(bias_distance, 4),
                    direction_correct=direction_correct,
                    magnitude_ratio=round(magnitude_ratio, 4),
                )
            )

        # Compute summary statistics
        initial_mae = prediction_errors[0] if prediction_errors else 0.0
        final_mae = prediction_errors[-1] if prediction_errors else 0.0
        total_mae_reduction = initial_mae - final_mae

        # Convergence rate: how much bias distance improved
        initial_bias_distances = [
            abs(0.0 - self.CATEGORY_SYSTEMATIC_BIAS[exp.category])
            for exp in self.dataset.training_experiences
        ]
        final_bias_distances = [
            comp.bias_distance for comp in bias_comparisons
        ]
        avg_initial_distance = sum(initial_bias_distances) / len(initial_bias_distances)
        avg_final_distance = sum(final_bias_distances) / len(final_bias_distances)
        convergence_rate = (
            (avg_initial_distance - avg_final_distance) / avg_initial_distance * 100
            if avg_initial_distance > 0
            else 0.0
        )

        # Per-category statistics
        category_bias_distances: Dict[str, float] = {}
        category_direction_correct_counts: Dict[str, int] = {}
        category_total_counts: Dict[str, int] = {}

        for comp in bias_comparisons:
            cat = comp.category
            category_bias_distances[cat] = category_bias_distances.get(cat, 0.0) + (
                comp.bias_distance
            )
            category_direction_correct_counts[cat] = (
                category_direction_correct_counts.get(cat, 0) + int(comp.direction_correct)
            )
            category_total_counts[cat] = category_total_counts.get(cat, 0) + 1

        # Average distances and direction accuracy
        for cat in category_bias_distances:
            category_bias_distances[cat] = round(
                category_bias_distances[cat] / category_total_counts[cat], 4
            )

        category_direction_accuracy: Dict[str, float] = {}
        for cat in category_direction_correct_counts:
            accuracy = (
                category_direction_correct_counts[cat] / category_total_counts[cat]
                * 100
            )
            category_direction_accuracy[cat] = round(accuracy, 1)

        # Verdicts
        is_learning = final_mae < initial_mae
        avg_direction_accuracy = (
            sum(category_direction_accuracy.values())
            / len(category_direction_accuracy)
            if category_direction_accuracy
            else 0.0
        )
        is_converging = (
            convergence_rate > 20.0 and avg_direction_accuracy > 60.0
        )  # >20% convergence + >60% direction accuracy

        if is_learning and is_converging:
            learning_explanation = (
                f"Calibration successfully learned to correct systematic biases. "
                f"MAE reduced by {total_mae_reduction:.4f} ({total_mae_reduction/initial_mae*100:.1f}%), "
                f"bias converged {convergence_rate:.1f}%, "
                f"direction accuracy {avg_direction_accuracy:.1f}%. "
                f"The mechanism learns the true bias through gradient-like updates."
            )
        elif is_learning:
            learning_explanation = (
                f"Calibration reduced MAE ({total_mae_reduction:.4f}, {total_mae_reduction/initial_mae*100:.1f}%), "
                f"but bias convergence is weak ({convergence_rate:.1f}%). "
                f"Learning may work through mechanisms other than explicit bias correction."
            )
        else:
            learning_explanation = (
                f"Calibration did not improve MAE on training set. "
                f"Initial: {initial_mae:.4f}, Final: {final_mae:.4f}. "
                f"Bias convergence: {convergence_rate:.1f}%. "
                f"This suggests learning parameters need tuning or benchmark randomness."
            )

        result = MechanismAnalysisResult(
            experiment_id=experiment_id,
            seed=self.seed,
            dataset_id=self.dataset_id,
            timestamp=datetime.now().isoformat(),
            learning_rate=self.learning_rate,
            bounds=self.bounds,
            calibration_trajectory=trajectory,
            bias_comparisons=bias_comparisons,
            initial_mae=round(initial_mae, 4),
            final_mae=round(final_mae, 4),
            total_mae_reduction=round(total_mae_reduction, 4),
            convergence_rate=round(convergence_rate, 1),
            category_bias_distances=category_bias_distances,
            category_direction_accuracy=category_direction_accuracy,
            is_learning=is_learning,
            is_converging=is_converging,
            learning_explanation=learning_explanation,
        )

        return result


def run_research_mechanism_17_2_a(
    dataset: Optional[Any] = None,
    seed: int = 42,
    learning_rate: float = 0.007,
    bounds: Optional[Dict[str, float]] = None,
    experiment_id: str = "research_mechanism_17_2_a",
) -> MechanismAnalysisResult:
    """
    Convenience function to run mechanism analysis.

    Args:
        dataset: Optional pre-existing research dataset
        seed: Random seed for benchmark (if dataset is None)
        learning_rate: Calibration learning rate
        bounds: Calibration parameter bounds
        experiment_id: Experiment identifier

    Returns:
        MechanismAnalysisResult with full trajectory and analysis
    """
    analyzer = ResearchMechanismAnalyzer(
        dataset=dataset,
        seed=seed,
        learning_rate=learning_rate,
        bounds=bounds,
    )
    return analyzer.run(experiment_id=experiment_id)
