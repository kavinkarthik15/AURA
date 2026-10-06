"""
17.5A Error-Signal Provenance Analysis

Tracks each calibration event through the entire pipeline to identify where
directional information is lost or corrupted.

Core invariant: For each event,
  error = actual - predicted
  expected_direction = sign(error)
  actual_update_direction = sign(delta)
  direction_match = expected_direction == actual_update_direction

Question: Does the sign-aware calibration pipeline preserve error direction
all the way from (actual - predicted) to expected_state_bias update across all seeds?
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional
from pathlib import Path
from collections import defaultdict

from backend.experiments.research_benchmark_generator import ResearchBenchmarkGenerator
from backend.models.calibration_parameters import CalibrationParameters
from backend.models.decision_outcome import DecisionOutcome
from backend.services.sign_aware_calibrator import SignAwareCalibratorVariant
from backend.services.prediction_error_evaluator import PredictionErrorEvaluator
from backend.services.simulation_engine import SimulationEngine
from backend.services.transition_engine import TransitionEngine


@dataclass
class CalibrationEvent:
    """Records a single calibration event through the full pipeline."""
    seed: int
    step: int
    category: str
    
    # Raw values
    predicted_value: float
    actual_value: float
    
    # Computed errors
    raw_error: float  # actual - predicted
    signed_error: float  # actual - predicted (same as raw, for clarity)
    absolute_error: float  # |actual - predicted|
    
    # State before/after
    expected_state_bias_before: float
    expected_state_bias_delta: float
    expected_state_bias_after: float
    
    # Direction tracking
    expected_direction: int  # sign of error: -1, 0, or 1
    actual_update_direction: int  # sign of delta: -1, 0, or 1
    direction_match: bool  # expected_direction == actual_update_direction
    direction_match_category: str  # "match", "mismatch", "skip_zero_error", "skip_zero_delta"


@dataclass
class SeedProvenanceResult:
    """Results for one seed."""
    seed: int
    total_events: int
    events_with_nonzero_error: int
    events_with_nonzero_delta: int
    total_direction_matches: int
    total_mismatches: int
    direction_accuracy: float  # matches / (matches + mismatches)
    events_skipped_zero_error: int
    events_skipped_zero_delta: int
    events: List[CalibrationEvent] = field(default_factory=list)
    
    # Breakdown by category
    category_stats: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class ProvenanceAnalysisResult:
    """Complete 17.5A analysis result."""
    analysis_date: str
    total_seeds: int
    seeds: List[int]
    learning_rate: float
    seed_results: Dict[int, SeedProvenanceResult] = field(default_factory=dict)
    
    # Aggregate statistics
    aggregate_direction_accuracy: float = 0.0
    aggregate_matches: int = 0
    aggregate_mismatches: int = 0
    
    # Violations summary
    violations_by_category: Dict[str, Dict] = field(default_factory=dict)
    key_findings: List[str] = field(default_factory=list)


class ErrorSignalProvenanceAnalyzer:
    """Analyzes directional consistency throughout calibration pipeline."""
    
    def __init__(self, seed: int = 42, learning_rate: float = 0.007):
        self.seed = seed
        self.learning_rate = learning_rate
        
        self.benchmark_generator = ResearchBenchmarkGenerator(seed=seed)
        self.evaluator = PredictionErrorEvaluator()
        self.calibrator = SignAwareCalibratorVariant()
        self.simulation_engine = SimulationEngine()
        self.transition_engine = TransitionEngine()
        
        self.bounds = {
            "state_adjustment_max": 0.12,
            "probability_bias_max": 0.012,
            "risk_bias_max": 0.012,
            "uncertainty_increment_max": 0.012,
            "confidence_increment_max": 0.012,
        }
        
        self.events: List[CalibrationEvent] = []
    
    def analyze_seed(self) -> SeedProvenanceResult:
        """Run complete provenance analysis for one seed."""
        self.events = []
        
        # Generate dataset
        dataset = self.benchmark_generator.generate_dataset(training_size=80, held_out_size=20)
        train_experiences = dataset.training_experiences
        
        # Initialize parameters
        params = CalibrationParameters()
        
        # Train and track events
        step = 0
        for experience in train_experiences:
            # Simulate prediction with current parameters
            sim = SimulationEngine(
                transition_engine=self.transition_engine,
                calibration_parameters=params,
            )
            prediction_result = sim.simulate_action(experience.initial_state, experience.selected_action)
            predicted = prediction_result.get("predicted_future_state", {})
            
            # Create decision outcome for error evaluation
            decision = DecisionOutcome(
                decision_id=experience.experience_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                selected_action=experience.selected_action,
                predicted_state=predicted,
                predicted_trajectory_score=0.5,
                predicted_probability=0.5,
                predicted_risk=0.3,
                predicted_uncertainty=0.2,
                actual_state=experience.actual_future_state,
            )
            
            # Evaluate error
            error_result = self.evaluator.evaluate(decision)
            
            # Track event for each state dimension
            if error_result.actual_available and error_result.signed_state_errors:
                for key, signed_error in error_result.signed_state_errors.items():
                    predicted_value = float(predicted.get(key, 0.0) or 0.0)
                    actual_value = float(experience.actual_future_state.get(key, 0.0) or 0.0)
                    absolute_error = abs(predicted_value - actual_value)
                    
                    # Get category from experience
                    category = experience.category or "unknown"
                    
                    # Compute expected direction
                    expected_dir = self._sign(signed_error)
                    
                    # Get bias before calibration
                    bias_before = params.expected_state_bias.get(key, 0.0)
                    
                    # Calibrate
                    result = self.calibrator.calibrate(
                        error_result,
                        current_parameters=params,
                        learning_rate=self.learning_rate,
                        bounds=self.bounds,
                    )
                    
                    # Get delta that was applied
                    state_updates = result.updates_applied.get("state_bias", {})
                    delta = state_updates.get(key, 0.0)
                    
                    # Get bias after
                    bias_after = result.updated_parameters.expected_state_bias.get(key, 0.0)
                    
                    # Compute actual direction
                    actual_dir = self._sign(delta)
                    
                    # Determine match status
                    if signed_error == 0:
                        match_category = "skip_zero_error"
                        direction_match = True  # Skip zero errors; don't count as mismatch
                    elif delta == 0:
                        match_category = "skip_zero_delta"
                        direction_match = True  # Skip zero deltas; don't count as mismatch
                    else:
                        match_category = "match" if expected_dir == actual_dir else "mismatch"
                        direction_match = expected_dir == actual_dir
                    
                    # Record event
                    event = CalibrationEvent(
                        seed=self.seed,
                        step=step,
                        category=category,
                        predicted_value=round(predicted_value, 4),
                        actual_value=round(actual_value, 4),
                        raw_error=round(signed_error, 4),
                        signed_error=round(signed_error, 4),
                        absolute_error=round(absolute_error, 4),
                        expected_state_bias_before=round(bias_before, 4),
                        expected_state_bias_delta=round(delta, 4),
                        expected_state_bias_after=round(bias_after, 4),
                        expected_direction=expected_dir,
                        actual_update_direction=actual_dir,
                        direction_match=direction_match,
                        direction_match_category=match_category,
                    )
                    self.events.append(event)
                    
                    step += 1
            
            # Update parameters for next iteration
            params = result.updated_parameters
        
        # Compute statistics
        return self._compute_seed_statistics()
    
    def _sign(self, value: float) -> int:
        """Return -1, 0, or 1 for sign of value."""
        if value < 0:
            return -1
        elif value > 0:
            return 1
        else:
            return 0
    
    def _compute_seed_statistics(self) -> SeedProvenanceResult:
        """Compute statistics from collected events."""
        result = SeedProvenanceResult(
            seed=self.seed,
            total_events=len(self.events),
            events_with_nonzero_error=0,
            events_with_nonzero_delta=0,
            total_direction_matches=0,
            total_mismatches=0,
            direction_accuracy=0.0,
            events_skipped_zero_error=0,
            events_skipped_zero_delta=0,
            events=self.events,
        )
        
        # Aggregate statistics
        category_stats = defaultdict(lambda: {
            "total": 0,
            "matches": 0,
            "mismatches": 0,
            "violations": [],
        })
        
        for event in self.events:
            if event.direction_match_category == "skip_zero_error":
                result.events_skipped_zero_error += 1
            elif event.direction_match_category == "skip_zero_delta":
                result.events_skipped_zero_delta += 1
            else:
                result.events_with_nonzero_error += 1
                result.events_with_nonzero_delta += 1
                
                if event.direction_match:
                    result.total_direction_matches += 1
                    category_stats[event.category]["matches"] += 1
                else:
                    result.total_mismatches += 1
                    category_stats[event.category]["mismatches"] += 1
                    category_stats[event.category]["violations"].append({
                        "step": event.step,
                        "expected_direction": event.expected_direction,
                        "actual_direction": event.actual_update_direction,
                        "signed_error": event.signed_error,
                        "delta": event.expected_state_bias_delta,
                    })
                
                category_stats[event.category]["total"] += 1
        
        # Compute direction accuracy
        total_evaluable = result.total_direction_matches + result.total_mismatches
        if total_evaluable > 0:
            result.direction_accuracy = result.total_direction_matches / total_evaluable
        
        # Store category stats
        result.category_stats = dict(category_stats)
        
        return result


class ResearchPhase17_5_A:
    """Main orchestrator for 17.5A error-signal provenance analysis."""
    
    def __init__(self, seeds: List[int] = None, learning_rate: float = 0.007):
        self.seeds = seeds or [42, 123, 456, 789, 999]
        self.learning_rate = learning_rate
    
    def run(self) -> ProvenanceAnalysisResult:
        """Run complete analysis across all seeds."""
        result = ProvenanceAnalysisResult(
            analysis_date=datetime.now(timezone.utc).isoformat(),
            total_seeds=len(self.seeds),
            seeds=self.seeds,
            learning_rate=self.learning_rate,
        )
        
        print(f"\n{'='*70}")
        print("17.5A Error-Signal Provenance Analysis")
        print(f"{'='*70}")
        print(f"Analyzing {len(self.seeds)} seeds: {self.seeds}")
        print(f"Learning rate: {self.learning_rate}")
        print()
        
        # Run analysis for each seed
        aggregate_matches = 0
        aggregate_mismatches = 0
        all_violations = defaultdict(list)
        
        for seed in self.seeds:
            print(f"Analyzing seed {seed}...", end=" ", flush=True)
            analyzer = ErrorSignalProvenanceAnalyzer(seed=seed, learning_rate=self.learning_rate)
            seed_result = analyzer.analyze_seed()
            result.seed_results[seed] = seed_result
            
            aggregate_matches += seed_result.total_direction_matches
            aggregate_mismatches += seed_result.total_mismatches
            
            # Collect violations
            for category, stats in seed_result.category_stats.items():
                for violation in stats.get("violations", []):
                    all_violations[category].append({
                        "seed": seed,
                        **violation,
                    })
            
            print(f"[DONE] {seed_result.total_direction_matches}/{seed_result.events_with_nonzero_delta} matches")
        
        # Compute aggregate statistics
        total_evaluable = aggregate_matches + aggregate_mismatches
        if total_evaluable > 0:
            result.aggregate_direction_accuracy = aggregate_matches / total_evaluable
        result.aggregate_matches = aggregate_matches
        result.aggregate_mismatches = aggregate_mismatches
        result.violations_by_category = dict(all_violations)
        
        # Generate findings
        result.key_findings = self._generate_findings(result)
        
        return result
    
    def _generate_findings(self, result: ProvenanceAnalysisResult) -> List[str]:
        """Generate key findings from analysis."""
        findings = []
        
        if result.aggregate_direction_accuracy == 1.0:
            findings.append(
                "[FINDING] Error direction is preserved PERFECTLY throughout pipeline "
                "(100% accuracy across all seeds)"
            )
            findings.append(
                "IMPLICATION: Sign propagation works correctly. Move to next hypothesis: "
                "sequence/distribution of errors causes seed-dependent behavior."
            )
        elif result.aggregate_direction_accuracy >= 0.95:
            findings.append(
                f"[FINDING] Error direction is preserved at high rate "
                f"({result.aggregate_direction_accuracy:.1%} accuracy)"
            )
            findings.append(
                f"IMPLICATION: Only {result.aggregate_mismatches} of "
                f"{result.aggregate_matches + result.aggregate_mismatches} updates mismatch. "
                "Minor sign corruption detected."
            )
        else:
            findings.append(
                f"[FINDING] Error direction shows significant corruption "
                f"({result.aggregate_direction_accuracy:.1%} accuracy)"
            )
            findings.append(
                f"IMPLICATION: {result.aggregate_mismatches} mismatches detected. "
                "Sign propagation is broken at pipeline stage."
            )
        
        # Check for seed-specific patterns
        accurate_seeds = [s for s, r in result.seed_results.items() if r.direction_accuracy >= 0.99]
        inaccurate_seeds = [s for s, r in result.seed_results.items() if r.direction_accuracy < 0.99]
        
        if inaccurate_seeds:
            findings.append(
                f"[SEED PATTERN] Seeds with direction issues: {inaccurate_seeds}. "
                f"Seeds with correct direction: {accurate_seeds}"
            )
        
        return findings


def main():
    """Run complete 17.5A analysis."""
    analyzer = ResearchPhase17_5_A(
        seeds=[42, 123, 456, 789, 999],
        learning_rate=0.007,
    )
    result = analyzer.run()
    
    # Print summary tables
    _print_summary_table(result)
    _print_violations_table(result)
    _print_findings(result)
    
    # Save to JSON
    _save_results(result)
    
    return result


def _print_summary_table(result: ProvenanceAnalysisResult) -> None:
    """Print summary table of direction accuracy by seed."""
    print(f"\n{'='*70}")
    print("DIRECTION ACCURACY BY SEED")
    print(f"{'='*70}")
    print(f"{'Seed':<8} {'Events':<10} {'Matches':<12} {'Mismatches':<12} {'Accuracy':<10}")
    print(f"{'-'*70}")
    
    for seed in result.seeds:
        seed_result = result.seed_results[seed]
        total = seed_result.events_with_nonzero_delta
        matches = seed_result.total_direction_matches
        mismatches = seed_result.total_mismatches
        
        if total > 0:
            accuracy = f"{seed_result.direction_accuracy:.1%}"
        else:
            accuracy = "N/A"
        
        print(f"{seed:<8} {total:<10} {matches:<12} {mismatches:<12} {accuracy:<10}")
    
    print(f"{'-'*70}")
    total_all = result.aggregate_matches + result.aggregate_mismatches
    accuracy_all = f"{result.aggregate_direction_accuracy:.1%}"
    print(f"{'TOTAL':<8} {total_all:<10} {result.aggregate_matches:<12} "
          f"{result.aggregate_mismatches:<12} {accuracy_all:<10}")
    print()


def _print_violations_table(result: ProvenanceAnalysisResult) -> None:
    """Print detailed violations breakdown by category."""
    if not result.violations_by_category:
        print(f"\n{'='*70}")
        print("NO VIOLATIONS DETECTED")
        print(f"{'='*70}")
        return
    
    print(f"\n{'='*70}")
    print("VIOLATIONS BY CATEGORY")
    print(f"{'='*70}")
    
    for category in sorted(result.violations_by_category.keys()):
        violations = result.violations_by_category[category]
        print(f"\n{category}:")
        print(f"  Violations: {len(violations)}")
        
        # Sample violations (show first 3)
        for i, v in enumerate(violations[:3]):
            print(f"    [{i+1}] Seed {v['seed']:3d} Step {v['step']:3d}: "
                  f"Expected {v['expected_direction']:+2d}, "
                  f"Got {v['actual_direction']:+2d} "
                  f"(error={v['signed_error']:+.4f}, delta={v['delta']:+.4f})")
        
        if len(violations) > 3:
            print(f"    ... and {len(violations) - 3} more")
    
    print()


def _print_findings(result: ProvenanceAnalysisResult) -> None:
    """Print key findings."""
    print(f"\n{'='*70}")
    print("KEY FINDINGS")
    print(f"{'='*70}")
    for finding in result.key_findings:
        print(f"\n{finding}")
    print()


def _save_results(result: ProvenanceAnalysisResult) -> None:
    """Save results to JSON."""
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / "research_17_5_a_error_signal_provenance.json"
    
    # Convert to dict for JSON serialization
    result_dict = {
        "analysis_date": result.analysis_date,
        "total_seeds": result.total_seeds,
        "seeds": result.seeds,
        "learning_rate": result.learning_rate,
        "aggregate_direction_accuracy": round(result.aggregate_direction_accuracy, 4),
        "aggregate_matches": result.aggregate_matches,
        "aggregate_mismatches": result.aggregate_mismatches,
        "seed_results": {
            seed: {
                "seed": sr.seed,
                "total_events": sr.total_events,
                "events_with_nonzero_error": sr.events_with_nonzero_error,
                "events_with_nonzero_delta": sr.events_with_nonzero_delta,
                "total_direction_matches": sr.total_direction_matches,
                "total_mismatches": sr.total_mismatches,
                "direction_accuracy": round(sr.direction_accuracy, 4),
                "events_skipped_zero_error": sr.events_skipped_zero_error,
                "events_skipped_zero_delta": sr.events_skipped_zero_delta,
                "category_stats": {
                    cat: {
                        "total": stats["total"],
                        "matches": stats["matches"],
                        "mismatches": stats["mismatches"],
                        "violation_count": len(stats.get("violations", [])),
                    }
                    for cat, stats in sr.category_stats.items()
                },
            }
            for seed, sr in result.seed_results.items()
        },
        "violations_by_category": {
            cat: len(vlist) for cat, vlist in result.violations_by_category.items()
        },
        "key_findings": result.key_findings,
    }
    
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(result_dict, f, indent=2)
    
    print(f"Results saved to: {output_file}")


if __name__ == "__main__":
    main()
