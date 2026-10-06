"""
17.4C Variant Runner Helper

Provides utilities to run individual calibration variants using the 17.3A framework
with support for filtering parameters (clipping, confidence gating).
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.services.sign_aware_calibrator import SignAwareCalibratorVariant
from backend.services.digital_twin_calibrator import DigitalTwinCalibrator
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator
from backend.services.simulation_engine import SimulationEngine
from backend.services.transition_engine import TransitionEngine


@dataclass
class VariantResult:
    """Result from running a single calibration variant."""
    variant_name: str
    seed: int
    held_out_mae: float
    baseline_mae: float
    held_out_mae_improvement: float
    overall_direction_accuracy: float
    positive_bias_direction_accuracy: float
    negative_bias_direction_accuracy: float
    max_parameter_drift: float
    final_expected_state_bias: Dict[str, float]
    per_category_mae: Dict[str, float]
    per_category_direction_accuracy: Dict[str, float]


class VariantRunner:
    """Runs individual calibration variants with configurable filtering."""
    
    def __init__(
        self,
        seed: int = 42,
        learning_rate: float = 0.007,
        max_signed_delta: Optional[float] = None,
        error_threshold: Optional[float] = None,
    ):
        self.seed = seed
        self.learning_rate = learning_rate
        self.max_signed_delta = max_signed_delta
        self.error_threshold = error_threshold
        
        self.benchmark_generator = ResearchBenchmarkGenerator(seed=seed)
        self.evaluator = PredictionErrorEvaluator()
        self.simulation_engine = SimulationEngine()
        self.transition_engine = TransitionEngine()
        
        self.bounds = {
            "state_adjustment_max": 0.12,
            "probability_bias_max": 0.012,
            "risk_bias_max": 0.012,
            "uncertainty_increment_max": 0.012,
            "confidence_increment_max": 0.012,
        }
    
    def run_variant(self, variant_name: str) -> VariantResult:
        """Run a single variant and return results."""
        # Generate dataset
        dataset = self.benchmark_generator.generate_dataset(training_size=80, held_out_size=20)
        train_experiences = dataset.training_experiences
        held_out_experiences = dataset.held_out_experiences
        
        # Compute baseline (uncalibrated) errors
        baseline_params = CalibrationParameters()
        baseline_errors = self._compute_errors(held_out_experiences, baseline_params)
        baseline_mae = sum(baseline_errors) / len(baseline_errors) if baseline_errors else 0.0
        
        # Select calibrator based on variant
        if variant_name == 'original':
            calibrator = DigitalTwinCalibrator()
            use_filtering = False
        elif variant_name in ['sign-aware-17.3', 'clipped', 'confidence-gated', 'clipped-confidence-gated']:
            calibrator = SignAwareCalibratorVariant()
            use_filtering = variant_name != 'sign-aware-17.3'
        else:
            raise ValueError(f"Unknown variant: {variant_name}")
        
        # Train calibrator
        trained_params = self._train_calibrator(
            train_experiences,
            baseline_params,
            calibrator,
            use_filtering,
        )
        
        # Evaluate on held-out
        held_out_errors = self._compute_errors(held_out_experiences, trained_params)
        held_out_mae = sum(held_out_errors) / len(held_out_errors) if held_out_errors else 0.0
        
        # Compute accuracy metrics
        overall_dir_acc = self._compute_direction_accuracy(held_out_experiences, trained_params)
        pos_bias_dir_acc = self._compute_positive_bias_accuracy(held_out_experiences, trained_params)
        neg_bias_dir_acc = self._compute_negative_bias_accuracy(held_out_experiences, trained_params)
        
        # Compute parameter drift
        max_drift = self._compute_max_parameter_drift(baseline_params, trained_params)
        
        # Per-category metrics
        per_cat_mae = self._compute_per_category_mae(held_out_experiences, trained_params)
        per_cat_dir_acc = self._compute_per_category_direction_accuracy(held_out_experiences, trained_params)
        
        return VariantResult(
            variant_name=variant_name,
            seed=self.seed,
            held_out_mae=round(held_out_mae, 4),
            baseline_mae=round(baseline_mae, 4),
            held_out_mae_improvement=round(baseline_mae - held_out_mae, 4),
            overall_direction_accuracy=round(overall_dir_acc, 4),
            positive_bias_direction_accuracy=round(pos_bias_dir_acc, 4),
            negative_bias_direction_accuracy=round(neg_bias_dir_acc, 4),
            max_parameter_drift=round(max_drift, 4),
            final_expected_state_bias=trained_params.expected_state_bias,
            per_category_mae=per_cat_mae,
            per_category_direction_accuracy=per_cat_dir_acc,
        )
    
    def _train_calibrator(
        self,
        experiences,
        initial_params: CalibrationParameters,
        calibrator,
        use_filtering: bool = False,
    ) -> CalibrationParameters:
        """Train calibrator on experiences."""
        params = CalibrationParameters(**initial_params.model_dump())
        
        for experience in experiences:
            # Simulate prediction with current parameters
            sim = SimulationEngine(
                transition_engine=self.transition_engine,
                calibration_parameters=params,
            )
            predicted = sim.simulate_action(experience.initial_state, experience.selected_action)
            
            # Create decision outcome
            decision = DecisionOutcome(
                decision_id=experience.experience_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                selected_action=experience.selected_action,
                predicted_state=predicted["predicted_future_state"],
                predicted_trajectory_score=0.5,
                predicted_probability=0.5,
                predicted_risk=0.3,
                predicted_uncertainty=0.2,
                actual_state=experience.actual_future_state,
            )
            
            # Evaluate error
            error_result = self.evaluator.evaluate(decision)
            
            # Apply filtering if enabled (for non-original calibrators)
            if use_filtering and hasattr(error_result, 'signed_state_errors'):
                filtered_errors = self._apply_filtering(error_result.signed_state_errors)
                error_result.signed_state_errors = filtered_errors
            
            # Calibrate
            calibration = calibrator.calibrate(
                error_result, params, self.learning_rate, self.bounds
            )
            params = calibration.updated_parameters
        
        return params
    
    def _apply_filtering(self, signed_errors: Dict[str, float]) -> Dict[str, float]:
        """Apply confidence gating and clipping filters to signed errors."""
        filtered = {}
        
        for category, signed_error in signed_errors.items():
            # Step 1: Confidence gating (error magnitude threshold)
            if self.error_threshold is not None:
                if abs(signed_error) < self.error_threshold:
                    filtered[category] = 0.0  # Ignore small errors
                    continue
            
            # Step 2: Clipping (bound magnitude)
            if self.max_signed_delta is not None:
                clipped_error = max(
                    -self.max_signed_delta,
                    min(self.max_signed_delta, signed_error)
                )
                filtered[category] = clipped_error
            else:
                filtered[category] = signed_error
        
        return filtered
    
    def _compute_errors(
        self, experiences, params: CalibrationParameters
    ) -> List[float]:
        """Compute absolute errors on experiences."""
        errors = []
        
        for experience in experiences:
            sim = SimulationEngine(
                transition_engine=self.transition_engine,
                calibration_parameters=params,
            )
            predicted = sim.simulate_action(experience.initial_state, experience.selected_action)
            predicted_state = predicted["predicted_future_state"]
            actual_state = experience.actual_future_state
            
            for key in set(predicted_state.keys()) | set(actual_state.keys()):
                pred = float(predicted_state.get(key, 0.0) or 0.0)
                true = float(actual_state.get(key, 0.0) or 0.0)
                error = abs(pred - true)
                errors.append(error)
        
        return errors
    
    def _compute_direction_accuracy(self, experiences, params: CalibrationParameters) -> float:
        """Compute overall direction accuracy."""
        correct = 0
        total = 0
        
        for experience in experiences:
            actual = experience.actual_future_state or {}
            predicted_raw = experience.initial_state or {}
            
            for key in set(predicted_raw.keys()) | set(actual.keys()):
                pred_val = float(predicted_raw.get(key, 0.0) or 0.0)
                actual_val = float(actual.get(key, 0.0) or 0.0)
                bias = params.expected_state_bias.get(key, 0.0)
                
                if actual_val > pred_val and bias > 0:
                    correct += 1
                elif actual_val < pred_val and bias < 0:
                    correct += 1
                
                total += 1
        
        return correct / total if total > 0 else 0.0
    
    def _compute_positive_bias_accuracy(self, experiences, params: CalibrationParameters) -> float:
        """Compute direction accuracy for positive-bias (underestimate) cases."""
        correct = 0
        total = 0
        
        for experience in experiences:
            actual = experience.actual_future_state or {}
            predicted_raw = experience.initial_state or {}
            
            for key in set(predicted_raw.keys()) | set(actual.keys()):
                pred_val = float(predicted_raw.get(key, 0.0) or 0.0)
                actual_val = float(actual.get(key, 0.0) or 0.0)
                bias = params.expected_state_bias.get(key, 0.0)
                
                # Count only underestimate cases (actual > predicted)
                if actual_val > pred_val:
                    total += 1
                    if bias > 0:
                        correct += 1
        
        return correct / total if total > 0 else 0.0
    
    def _compute_negative_bias_accuracy(self, experiences, params: CalibrationParameters) -> float:
        """Compute direction accuracy for negative-bias (overestimate) cases."""
        correct = 0
        total = 0
        
        for experience in experiences:
            actual = experience.actual_future_state or {}
            predicted_raw = experience.initial_state or {}
            
            for key in set(predicted_raw.keys()) | set(actual.keys()):
                pred_val = float(predicted_raw.get(key, 0.0) or 0.0)
                actual_val = float(actual.get(key, 0.0) or 0.0)
                bias = params.expected_state_bias.get(key, 0.0)
                
                # Count only overestimate cases (actual < predicted)
                if actual_val < pred_val:
                    total += 1
                    if bias < 0:
                        correct += 1
        
        return correct / total if total > 0 else 0.0
    
    def _compute_max_parameter_drift(
        self,
        baseline: CalibrationParameters,
        trained: CalibrationParameters,
    ) -> float:
        """Compute maximum absolute parameter change."""
        max_drift = 0.0
        
        for key in baseline.expected_state_bias:
            drift = abs(trained.expected_state_bias.get(key, 0.0) - baseline.expected_state_bias[key])
            max_drift = max(max_drift, drift)
        
        return max_drift
    
    def _compute_per_category_mae(
        self,
        experiences,
        params: CalibrationParameters,
    ) -> Dict[str, float]:
        """Compute MAE per category."""
        category_errors: Dict[str, List[float]] = {}
        
        for experience in experiences:
            category = getattr(experience, 'category', 'unknown')
            if category not in category_errors:
                category_errors[category] = []
            
            sim = SimulationEngine(
                transition_engine=self.transition_engine,
                calibration_parameters=params,
            )
            predicted = sim.simulate_action(experience.initial_state, experience.selected_action)
            predicted_state = predicted["predicted_future_state"]
            actual_state = experience.actual_future_state
            
            for key in set(predicted_state.keys()) | set(actual_state.keys()):
                pred = float(predicted_state.get(key, 0.0) or 0.0)
                true = float(actual_state.get(key, 0.0) or 0.0)
                error = abs(pred - true)
                category_errors[category].append(error)
        
        result = {}
        for category, errors in category_errors.items():
            mae = sum(errors) / len(errors) if errors else 0.0
            result[category] = round(mae, 4)
        
        return result
    
    def _compute_per_category_direction_accuracy(
        self,
        experiences,
        params: CalibrationParameters,
    ) -> Dict[str, float]:
        """Compute direction accuracy per category."""
        category_stats: Dict[str, List[bool]] = {}
        
        for experience in experiences:
            category = getattr(experience, 'category', 'unknown')
            if category not in category_stats:
                category_stats[category] = []
            
            actual = experience.actual_future_state or {}
            predicted_raw = experience.initial_state or {}
            
            for key in set(predicted_raw.keys()) | set(actual.keys()):
                pred_val = float(predicted_raw.get(key, 0.0) or 0.0)
                actual_val = float(actual.get(key, 0.0) or 0.0)
                bias = params.expected_state_bias.get(key, 0.0)
                
                is_correct = (
                    (actual_val > pred_val and bias > 0) or
                    (actual_val < pred_val and bias < 0)
                )
                category_stats[category].append(is_correct)
        
        result = {}
        for category, corrects in category_stats.items():
            accuracy = sum(corrects) / len(corrects) if corrects else 0.0
            result[category] = round(accuracy, 4)
        
        return result
