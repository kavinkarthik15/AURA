"""
Phase 17.4C: Clipped and Confidence-Gated Signed Updates for Robustness

This experiment tests whether filtering mechanisms (clipping and confidence gating) 
can retain the benefits of signed-error calibration while preventing the accumulation 
drift that caused robustness failures in 17.4A-B.

Design:
1. Original magnitude-only calibrator (baseline)
2. 17.3 sign-aware calibrator (reference)
3. Sign-aware + clipping (bound magnitude of signed updates)
4. Sign-aware + confidence gating (only update if |error| > threshold)
5. Sign-aware + clipping + confidence gating (both filters)

Hypothesis: Filtering mechanisms will reduce parameter drift while retaining directional benefits.

Success Criteria (Primary):
- At least 4/5 seeds improve over baseline without catastrophic parameter drift

Success Criteria (Ideal):
- Win rate >= 80%
- AND negative-bias direction accuracy improves
- AND no category experiences severe degradation
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Tuple, Optional, List
import json
from datetime import datetime
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.models.user_state import UserState
from backend.models.action_catalog import ActionCatalog
from backend.models.experience import Experience
from backend.services.digital_twin import DigitalTwin
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator


# ============================================================================
# CALIBRATOR VARIANTS FOR 17.4C
# ============================================================================

class SignAwareClippedCalibrator:
    """Sign-aware calibrator with clipping to prevent unbounded updates."""
    
    def __init__(
        self,
        learning_rate: float = 0.007,
        state_adjustment_max: float = 0.12,
        max_signed_delta: Optional[float] = None,
    ):
        self.learning_rate = learning_rate
        self.state_adjustment_max = state_adjustment_max
        # Default: half of max_adjustment as clipping bound
        self.max_signed_delta = max_signed_delta or (state_adjustment_max / 2)
    
    def calibrate(
        self,
        user_state: UserState,
        prediction_error: Dict[str, float],  # {category: signed_error}
        confidence: Optional[Dict[str, float]] = None,
        risk_profile: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> UserState:
        """Apply clipped signed updates."""
        calibrated = user_state.deep_copy()
        
        for category, signed_error in prediction_error.items():
            if category not in calibrated.expected_state_bias:
                continue
            
            # Compute signed update with learning rate
            signed_update = self.learning_rate * signed_error
            
            # Clip to prevent unbounded magnitude
            clipped_update = max(
                -self.max_signed_delta,
                min(self.max_signed_delta, signed_update)
            )
            
            # Apply update
            new_bias = calibrated.expected_state_bias[category] + clipped_update
            # Bound to state_adjustment_max
            new_bias = max(-self.state_adjustment_max, min(self.state_adjustment_max, new_bias))
            calibrated.expected_state_bias[category] = new_bias
        
        return calibrated


class SignAwareConfidenceGatedCalibrator:
    """Sign-aware calibrator with confidence gating (error magnitude threshold)."""
    
    def __init__(
        self,
        learning_rate: float = 0.007,
        state_adjustment_max: float = 0.12,
        error_threshold: Optional[float] = None,
    ):
        self.learning_rate = learning_rate
        self.state_adjustment_max = state_adjustment_max
        # Default: 0.5 (ignore errors smaller than 0.5)
        self.error_threshold = error_threshold or 0.5
        
        # Track updates for metrics
        self.updates_accepted = 0
        self.updates_rejected = 0
    
    def calibrate(
        self,
        user_state: UserState,
        prediction_error: Dict[str, float],  # {category: signed_error}
        confidence: Optional[Dict[str, float]] = None,
        risk_profile: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> UserState:
        """Apply signed updates only if |error| > threshold."""
        calibrated = user_state.deep_copy()
        
        for category, signed_error in prediction_error.items():
            if category not in calibrated.expected_state_bias:
                continue
            
            # Check confidence gate: only update if |error| > threshold
            if abs(signed_error) < self.error_threshold:
                self.updates_rejected += 1
                continue
            
            self.updates_accepted += 1
            
            # Compute signed update with learning rate
            signed_update = self.learning_rate * signed_error
            
            # Apply update
            new_bias = calibrated.expected_state_bias[category] + signed_update
            # Bound to state_adjustment_max
            new_bias = max(-self.state_adjustment_max, min(self.state_adjustment_max, new_bias))
            calibrated.expected_state_bias[category] = new_bias
        
        return calibrated


class SignAwareClippedConfidenceGatedCalibrator:
    """Sign-aware calibrator with both clipping and confidence gating."""
    
    def __init__(
        self,
        learning_rate: float = 0.007,
        state_adjustment_max: float = 0.12,
        max_signed_delta: Optional[float] = None,
        error_threshold: Optional[float] = None,
    ):
        self.learning_rate = learning_rate
        self.state_adjustment_max = state_adjustment_max
        self.max_signed_delta = max_signed_delta or (state_adjustment_max / 2)
        self.error_threshold = error_threshold or 0.5
        
        # Track updates for metrics
        self.updates_accepted = 0
        self.updates_rejected = 0
    
    def calibrate(
        self,
        user_state: UserState,
        prediction_error: Dict[str, float],  # {category: signed_error}
        confidence: Optional[Dict[str, float]] = None,
        risk_profile: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> UserState:
        """Apply clipped signed updates only if |error| > threshold."""
        calibrated = user_state.deep_copy()
        
        for category, signed_error in prediction_error.items():
            if category not in calibrated.expected_state_bias:
                continue
            
            # Step 1: Confidence gating
            if abs(signed_error) < self.error_threshold:
                self.updates_rejected += 1
                continue
            
            self.updates_accepted += 1
            
            # Step 2: Compute and clip signed update
            signed_update = self.learning_rate * signed_error
            clipped_update = max(
                -self.max_signed_delta,
                min(self.max_signed_delta, signed_update)
            )
            
            # Step 3: Apply clipped update
            new_bias = calibrated.expected_state_bias[category] + clipped_update
            # Bound to state_adjustment_max
            new_bias = max(-self.state_adjustment_max, min(self.state_adjustment_max, new_bias))
            calibrated.expected_state_bias[category] = new_bias
        
        return calibrated


# ============================================================================
# RESULT MODELS FOR 17.4C
# ============================================================================

@dataclass
class CalibrationVariantMetrics:
    """Metrics for a single calibration variant on a single seed."""
    variant_name: str
    seed: int
    
    # MAE metrics
    held_out_mae: float
    improvement_vs_baseline: float
    
    # Win flag
    beats_baseline: bool
    
    # Direction accuracy
    overall_direction_accuracy: float
    positive_bias_direction_accuracy: float
    negative_bias_direction_accuracy: float
    
    # Parameter drift
    max_absolute_parameter_drift: float
    final_expected_state_bias: Dict[str, float]
    
    # Update statistics
    updates_accepted: int = 0
    updates_rejected: int = 0
    
    # Per-category performance
    per_category_mae: Dict[str, float] = field(default_factory=dict)
    per_category_direction_accuracy: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'variant_name': self.variant_name,
            'seed': self.seed,
            'held_out_mae': round(self.held_out_mae, 4),
            'improvement_vs_baseline': round(self.improvement_vs_baseline, 4),
            'beats_baseline': self.beats_baseline,
            'overall_direction_accuracy': round(self.overall_direction_accuracy, 4),
            'positive_bias_direction_accuracy': round(self.positive_bias_direction_accuracy, 4),
            'negative_bias_direction_accuracy': round(self.negative_bias_direction_accuracy, 4),
            'max_absolute_parameter_drift': round(self.max_absolute_parameter_drift, 4),
            'final_expected_state_bias': {k: round(v, 4) for k, v in self.final_expected_state_bias.items()},
            'updates_accepted': self.updates_accepted,
            'updates_rejected': self.updates_rejected,
            'per_category_mae': {k: round(v, 4) for k, v in self.per_category_mae.items()},
            'per_category_direction_accuracy': {k: round(v, 4) for k, v in self.per_category_direction_accuracy.items()},
        }


@dataclass
class SeedComparisonResult17_4_C:
    """All 5 variants compared for a single seed."""
    seed: int
    variants: Dict[str, CalibrationVariantMetrics] = field(default_factory=dict)
    
    # Derived statistics
    win_count: int = 0
    category_degradation_count: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'seed': self.seed,
            'variants': {name: metrics.to_dict() for name, metrics in self.variants.items()},
            'win_count': self.win_count,
            'category_degradation_count': self.category_degradation_count,
        }


@dataclass
class VariantAggregateStatistics:
    """Aggregate statistics for a single variant across all seeds."""
    variant_name: str
    
    # Counts
    seed_results_count: int
    win_count: int
    
    # MAE statistics
    mean_improvement: float
    std_dev_improvement: float
    
    # Direction accuracy statistics
    mean_direction_accuracy: float
    mean_positive_bias_direction_accuracy: float
    mean_negative_bias_direction_accuracy: float
    
    # Success criterion
    passes_primary_criterion: bool
    passes_ideal_criterion: bool
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'variant_name': self.variant_name,
            'seed_results_count': self.seed_results_count,
            'win_count': self.win_count,
            'win_rate': round(self.win_count / self.seed_results_count, 2) if self.seed_results_count > 0 else 0,
            'mean_improvement': round(self.mean_improvement, 4),
            'std_dev_improvement': round(self.std_dev_improvement, 4),
            'mean_direction_accuracy': round(self.mean_direction_accuracy, 4),
            'mean_positive_bias_direction_accuracy': round(self.mean_positive_bias_direction_accuracy, 4),
            'mean_negative_bias_direction_accuracy': round(self.mean_negative_bias_direction_accuracy, 4),
            'passes_primary_criterion': self.passes_primary_criterion,
            'passes_ideal_criterion': self.passes_ideal_criterion,
        }


@dataclass
class ResearchPhase17_4_CResult:
    """Complete result for Phase 17.4C experiment."""
    timestamp: str
    seed_results: Dict[int, SeedComparisonResult17_4_C] = field(default_factory=dict)
    variant_statistics: Dict[str, VariantAggregateStatistics] = field(default_factory=dict)
    
    # Overall assessment
    recommended_variant: Optional[str] = None
    success_summary: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp,
            'seed_results': {str(seed): result.to_dict() for seed, result in self.seed_results.items()},
            'variant_statistics': {name: stats.to_dict() for name, stats in self.variant_statistics.items()},
            'recommended_variant': self.recommended_variant,
            'success_summary': self.success_summary,
        }


# ============================================================================
# EXPERIMENT RUNNER
# ============================================================================

class ResearchPhase17_4_C:
    """
    Phase 17.4C: Test clipped and confidence-gated signed updates.
    
    Compare 5 calibrator variants across 5 seeds to determine if filtering
    mechanisms can prevent accumulation drift while retaining directional benefits.
    """
    
    VARIANTS = [
        'original',  # Magnitude-only baseline
        'sign-aware-17.3',  # Sign-aware reference
        'clipped',  # Sign-aware + clipping
        'confidence-gated',  # Sign-aware + confidence gating
        'clipped-confidence-gated',  # Sign-aware + both filters
    ]
    
    def __init__(
        self,
        seeds: List[int],
        learning_rate: float = 0.007,
        clipping_bound: Optional[float] = None,
        error_threshold: Optional[float] = None,
    ):
        self.seeds = seeds
        self.learning_rate = learning_rate
        self.clipping_bound = clipping_bound or 0.06  # Half of state_adjustment_max (0.12)
        self.error_threshold = error_threshold or 0.5
        
        self.result = ResearchPhase17_4_CResult(
            timestamp=datetime.now().isoformat()
        )
    
    def run(self) -> ResearchPhase17_4_CResult:
        """Execute the full 17.4C experiment."""
        print(f"\n{'='*80}")
        print(f"Phase 17.4C: Clipped & Confidence-Gated Signed Updates")
        print(f"{'='*80}")
        print(f"Testing {len(self.VARIANTS)} variants across {len(self.seeds)} seeds")
        print(f"Clipping bound: {self.clipping_bound}, Error threshold: {self.error_threshold}")
        print(f"{'='*80}\n")
        
        # Import here to avoid circular imports
        from experiments.research_sign_aware_calibration_17_3_a import (
            ResearchSignAwareCalibration17_3_A
        )
        
        for seed in self.seeds:
            print(f"\n{'-'*80}")
            print(f"SEED {seed}")
            print(f"{'-'*80}")
            
            seed_result = SeedComparisonResult17_4_C(seed=seed)
            
            # Run each variant
            for variant_name in self.VARIANTS:
                print(f"\n  {variant_name}...", end=' ', flush=True)
                
                try:
                    # Run experiment with appropriate configuration
                    result = self._run_variant(variant_name, seed)
                    
                    # Extract metrics
                    metrics = CalibrationVariantMetrics(
                        variant_name=variant_name,
                        seed=seed,
                        held_out_mae=result.held_out_mae,
                        improvement_vs_baseline=result.held_out_mae_improvement,
                        beats_baseline=result.held_out_mae < result.baseline_mae,
                        overall_direction_accuracy=result.overall_direction_accuracy,
                        positive_bias_direction_accuracy=result.positive_bias_direction_accuracy,
                        negative_bias_direction_accuracy=result.negative_bias_direction_accuracy,
                        max_absolute_parameter_drift=result.max_parameter_drift,
                        final_expected_state_bias=result.final_expected_state_bias,
                        per_category_mae=result.per_category_mae,
                        per_category_direction_accuracy=result.per_category_direction_accuracy,
                    )
                    
                    seed_result.variants[variant_name] = metrics
                    
                    status = "[WIN]" if metrics.beats_baseline else "[LOSS]"
                    print(f"{status} | MAE: {metrics.held_out_mae:.4f} | Dir Acc: {metrics.overall_direction_accuracy:.1%}")
                
                except Exception as e:
                    print(f"[ERROR]: {str(e)}")
                    raise
            
            # Compute seed-level statistics
            seed_result.win_count = sum(1 for m in seed_result.variants.values() if m.beats_baseline)
            self.result.seed_results[seed] = seed_result
        
        # Compute aggregate statistics per variant
        self._compute_variant_statistics()
        
        # Generate summary
        self._generate_summary()
        
        return self.result
    
    def _run_variant(self, variant_name: str, seed: int):
        """Run a single variant and return result."""
        from experiments.variant_runner_17_4_c import VariantRunner
        
        # Determine filtering parameters based on variant
        if variant_name == 'original':
            max_signed_delta = None
            error_threshold = None
        elif variant_name == 'sign-aware-17.3':
            max_signed_delta = None
            error_threshold = None
        elif variant_name == 'clipped':
            max_signed_delta = self.clipping_bound
            error_threshold = None
        elif variant_name == 'confidence-gated':
            max_signed_delta = None
            error_threshold = self.error_threshold
        elif variant_name == 'clipped-confidence-gated':
            max_signed_delta = self.clipping_bound
            error_threshold = self.error_threshold
        else:
            raise ValueError(f"Unknown variant: {variant_name}")
        
        # Run variant
        runner = VariantRunner(
            seed=seed,
            learning_rate=self.learning_rate,
            max_signed_delta=max_signed_delta,
            error_threshold=error_threshold,
        )
        
        return runner.run_variant(variant_name)
    
    def _compute_variant_statistics(self):
        """Compute aggregate statistics for each variant across all seeds."""
        for variant_name in self.VARIANTS:
            improvements = []
            wins = 0
            dir_accs = []
            pos_bias_dir_accs = []
            neg_bias_dir_accs = []
            
            for seed_result in self.result.seed_results.values():
                if variant_name in seed_result.variants:
                    metrics = seed_result.variants[variant_name]
                    improvements.append(metrics.improvement_vs_baseline)
                    if metrics.beats_baseline:
                        wins += 1
                    dir_accs.append(metrics.overall_direction_accuracy)
                    pos_bias_dir_accs.append(metrics.positive_bias_direction_accuracy)
                    neg_bias_dir_accs.append(metrics.negative_bias_direction_accuracy)
            
            # Calculate statistics
            import statistics
            mean_improvement = statistics.mean(improvements) if improvements else 0
            std_dev = statistics.stdev(improvements) if len(improvements) > 1 else 0
            mean_dir_acc = statistics.mean(dir_accs) if dir_accs else 0
            mean_pos_bias_dir_acc = statistics.mean(pos_bias_dir_accs) if pos_bias_dir_accs else 0
            mean_neg_bias_dir_acc = statistics.mean(neg_bias_dir_accs) if neg_bias_dir_accs else 0
            
            # Success criteria
            passes_primary = wins >= 4  # At least 4/5 seeds improve
            passes_ideal = (wins >= 4 and mean_dir_acc >= 0.80 and mean_neg_bias_dir_acc >= 0.60)
            
            stats = VariantAggregateStatistics(
                variant_name=variant_name,
                seed_results_count=len(self.result.seed_results),
                win_count=wins,
                mean_improvement=mean_improvement,
                std_dev_improvement=std_dev,
                mean_direction_accuracy=mean_dir_acc,
                mean_positive_bias_direction_accuracy=mean_pos_bias_dir_acc,
                mean_negative_bias_direction_accuracy=mean_neg_bias_dir_acc,
                passes_primary_criterion=passes_primary,
                passes_ideal_criterion=passes_ideal,
            )
            
            self.result.variant_statistics[variant_name] = stats
    
    def _generate_summary(self):
        """Generate experiment summary."""
        print(f"\n{'='*80}")
        print("AGGREGATE STATISTICS")
        print(f"{'='*80}\n")
        
        for variant_name in self.VARIANTS:
            if variant_name not in self.result.variant_statistics:
                continue
            
            stats = self.result.variant_statistics[variant_name]
            print(f"{variant_name:30s} | Wins: {stats.win_count}/5 | MAE Delta: {stats.mean_improvement:+.4f} | Dir Acc: {stats.mean_direction_accuracy:.1%}")
            
            if stats.passes_ideal_criterion:
                print(f"  -> [PASS] IDEAL CRITERION")
            elif stats.passes_primary_criterion:
                print(f"  -> [PASS] PRIMARY CRITERION")
            else:
                print(f"  -> [FAIL] CRITERION")


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def run_research_phase_17_4_c(
    seeds: Optional[List[int]] = None,
    learning_rate: float = 0.007,
    clipping_bound: Optional[float] = None,
    error_threshold: Optional[float] = None,
) -> ResearchPhase17_4_CResult:
    """
    Convenience function to run Phase 17.4C experiment.
    
    Args:
        seeds: List of random seeds to test (default: [42, 123, 456, 789, 999])
        learning_rate: Learning rate for calibration
        clipping_bound: Maximum magnitude for clipped signed updates
        error_threshold: Minimum absolute error magnitude to apply updates
    
    Returns:
        ResearchPhase17_4_CResult with complete results
    """
    if seeds is None:
        seeds = [42, 123, 456, 789, 999]
    
    experiment = ResearchPhase17_4_C(
        seeds=seeds,
        learning_rate=learning_rate,
        clipping_bound=clipping_bound,
        error_threshold=error_threshold,
    )
    
    return experiment.run()


if __name__ == '__main__':
    result = run_research_phase_17_4_c()
    print(f"\n{'='*80}")
    print("Experiment complete!")
    print(f"{'='*80}")
