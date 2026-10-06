#!/usr/bin/env python3
"""
17.15 MG-Enabled Shadow Validation

Execute MG computation in shadow mode (first time) to answer:
"Does the frozen MG mechanism compute correctly under shadow conditions?
Is MG latency acceptable? Are corrections stable? Is production safe?"

This is the FIRST execution with MG enabled.
MG remains observational (shadow-only); production authority stays with legacy.
"""

import json
import time
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import random

from backend.services.simulation_engine import SimulationEngine
from backend.compatibility.mg_config import MGCompatibilityConfig


class ShadowValidationRunMGEnabled:
    """17.15 MG-enabled shadow validation execution."""

    def __init__(
        self,
        output_dir: Path = None,
        mg_enabled: bool = True,
        seeds: List[int] = None
    ):
        self.output_dir = output_dir or Path("d:/AURA")
        self.mg_enabled = mg_enabled
        self.seeds = seeds or [1000, 2000, 3000, 4000, 5000, 6000]
        self.events: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.start_time = None
        self.end_time = None
        
        # Metrics tracking
        self.metrics = {
            "expected_events": 0,
            "actual_events": 0,
            "missing_events": 0,
            "mg_computation_success": 0,
            "mg_computation_errors": 0,
            "fallback_triggered": 0,
            "production_path_failures": 0,
            "state_mutations": 0,
            "mg_latencies": [],  # For distribution analysis
            "legacy_latencies": [],
            "correction_magnitudes": [],
            "correction_polarities": {"positive": 0, "negative": 0, "zero": 0},
            "motivation_signals": [],
            "goals_signals": [],
            "per_category_events": {},
            "per_seed_events": {},
        }

    def run(self, num_simulations: int = 100) -> Dict[str, Any]:
        """Execute the MG-enabled shadow validation run."""
        self.start_time = datetime.utcnow()

        print(f"\n{'='*80}")
        print(f"17.15 MG-ENABLED SHADOW VALIDATION")
        print(f"{'='*80}")
        print(f"Start Time: {self.start_time.isoformat()}Z")
        print(f"MG Enabled: {self.mg_enabled}")
        print(f"Number of simulations per seed/category: {num_simulations}")
        print(f"Seed set: {self.seeds}")
        print(f"State categories: 4 (low, medium, high, edge)")
        print(f"Expected events: {len(self.seeds)} seeds × {num_simulations} sims × 4 categories = {len(self.seeds) * num_simulations * 4}")
        print(f"{'='*80}\n")

        self.metrics["expected_events"] = len(self.seeds) * num_simulations * 4

        # Run shadow validation with seeds
        try:
            for seed in self.seeds:
                random.seed(seed)
                self.metrics["per_seed_events"][seed] = 0
                
                print(f"Running seed {seed}...")
                
                for sim_idx in range(num_simulations):
                    # Create new engine for each seed (fresh state)
                    # For 17.15: Create config with MG ENABLED (for shadow computation only)
                    # Use frozen coefficients from 17.13B (seed 42 validated set)
                    # This keeps all coefficients frozen per user constraint
                    mg_config = MGCompatibilityConfig(
                        enabled=True,  # ENABLE MG for shadow mode (17.15 first execution)
                        use_motivation=True,  # Enable motivation signal extraction
                        use_goals=True,  # Enable goals signal extraction
                        motivation_coefficient=-3.2807449219261597,  # Frozen from 17.13B seed 42
                        goals_coefficient=-4.990929117526626,  # Frozen from 17.13B seed 42
                        intercept_coefficient=5.347402291610499,  # Frozen from 17.13B seed 42
                        fallback_enabled=True,  # Keep fallback available
                        rollout_percentage=100.0,  # CRITICAL: Must be > 0.0 for is_active() to return True
                    )
                    
                    engine = SimulationEngine(
                        mg_config=mg_config,
                        shadow_event_recorder=self._record_event_with_metrics
                    )

                    # Test state 1: Low skill state
                    try:
                        self._simulate_with_metrics(
                            engine,
                            state={"python": 20, "dsa": 15, "project_mgmt": 10},
                            action="Complete Python Basics",
                            category="low_skill_practice",
                            seed=seed
                        )
                    except Exception as e:
                        self.errors.append(f"Seed {seed} low skill error: {str(e)}")
                        self.metrics["production_path_failures"] += 1

                    # Test state 2: Medium skill state
                    try:
                        self._simulate_with_metrics(
                            engine,
                            state={"python": 50, "dsa": 45, "project_mgmt": 40},
                            action="Complete Python Project",
                            category="project_completion",
                            seed=seed
                        )
                    except Exception as e:
                        self.errors.append(f"Seed {seed} med skill error: {str(e)}")
                        self.metrics["production_path_failures"] += 1

                    # Test state 3: High skill state
                    try:
                        self._simulate_with_metrics(
                            engine,
                            state={"python": 80, "dsa": 85, "project_mgmt": 75},
                            action="Lead Large Team Project",
                            category="high_motivation",
                            seed=seed
                        )
                    except Exception as e:
                        self.errors.append(f"Seed {seed} high skill error: {str(e)}")
                        self.metrics["production_path_failures"] += 1

                    # Test edge cases
                    try:
                        self._simulate_with_metrics(
                            engine,
                            state={},
                            action="Unknown action",
                            category=None,
                            seed=seed
                        )
                    except Exception as e:
                        self.errors.append(f"Seed {seed} edge case error: {str(e)}")
                        self.metrics["production_path_failures"] += 1

                print(f"  Seed {seed}: {self.metrics['per_seed_events'][seed]} events recorded")

        except Exception as e:
            self.errors.append(f"Critical validation error: {str(e)}")
            print(f"ERROR: {e}")

        self.end_time = datetime.utcnow()
        self.metrics["actual_events"] = len(self.events)
        self.metrics["missing_events"] = self.metrics["expected_events"] - self.metrics["actual_events"]

        # Analyze and return results
        return self._analyze_results()

    def _simulate_with_metrics(
        self,
        engine: SimulationEngine,
        state: Dict[str, Any],
        action: str,
        category: Optional[str],
        seed: int
    ) -> None:
        """Execute simulation and track metrics."""
        start = time.time()
        result = engine.simulate_action(state, action, category=category)
        legacy_elapsed = (time.time() - start) * 1000  # Convert to ms
        
        self.metrics["legacy_latencies"].append(legacy_elapsed)
        self.metrics["per_seed_events"][seed] = self.metrics["per_seed_events"].get(seed, 0) + 1
        
        if category not in self.metrics["per_category_events"]:
            self.metrics["per_category_events"][category] = 0
        self.metrics["per_category_events"][category] += 1

    def _record_event_with_metrics(self, event: Dict[str, Any]) -> None:
        """Record shadow event and extract metrics."""
        self.events.append(event)
        
        # Track MG computation success
        if event.get("mg_error"):
            self.metrics["mg_computation_errors"] += 1
        else:
            self.metrics["mg_computation_success"] += 1
        
        # Track fallback
        if event.get("fallback_triggered"):
            self.metrics["fallback_triggered"] += 1
        
        # Track latency
        if event.get("mg_latency_ms") is not None:
            self.metrics["mg_latencies"].append(event["mg_latency_ms"])
        
        # Track corrections
        correction = event.get("mg_correction", {})
        if correction.get("correction_applied"):
            mag = correction.get("correction_value", 0)
            self.metrics["correction_magnitudes"].append(abs(mag))
            if mag > 0:
                self.metrics["correction_polarities"]["positive"] += 1
            elif mag < 0:
                self.metrics["correction_polarities"]["negative"] += 1
            else:
                self.metrics["correction_polarities"]["zero"] += 1
        
        # Track signals
        if event.get("motivation_signal") is not None:
            self.metrics["motivation_signals"].append(event["motivation_signal"])
        if event.get("goals_signal") is not None:
            self.metrics["goals_signals"].append(event["goals_signal"])

    def _analyze_results(self) -> Dict[str, Any]:
        """Analyze collected metrics and generate report."""
        print(f"\n{'='*80}")
        print(f"17.15 EXECUTION METRICS")
        print(f"{'='*80}\n")

        # Event count verification
        print(f"Event Count Verification:")
        print(f"  Expected events: {self.metrics['expected_events']}")
        print(f"  Actual events: {self.metrics['actual_events']}")
        print(f"  Missing: {self.metrics['missing_events']}")
        print(f"  Status: {'[PASS]' if self.metrics['missing_events'] == 0 else '[FAIL]'}\n")

        # MG Computation Success Rate
        total_computations = self.metrics["mg_computation_success"] + self.metrics["mg_computation_errors"]
        if total_computations > 0:
            success_rate = self.metrics["mg_computation_success"] / total_computations * 100
            print(f"MG Computation Success Rate:")
            print(f"  Successful: {self.metrics['mg_computation_success']}")
            print(f"  Errors: {self.metrics['mg_computation_errors']}")
            print(f"  Rate: {success_rate:.2f}%\n")

        # Fallback Rate
        if total_computations > 0:
            fallback_rate = self.metrics["fallback_triggered"] / total_computations * 100
            print(f"Fallback Triggered:")
            print(f"  Count: {self.metrics['fallback_triggered']}")
            print(f"  Rate: {fallback_rate:.2f}%\n")

        # MG Latency Distribution
        if self.metrics["mg_latencies"]:
            mg_latencies = self.metrics["mg_latencies"]
            print(f"MG Latency Distribution (milliseconds):")
            print(f"  Count: {len(mg_latencies)}")
            print(f"  Mean: {statistics.mean(mg_latencies):.3f} ms")
            print(f"  Median: {statistics.median(mg_latencies):.3f} ms")
            print(f"  Min: {min(mg_latencies):.3f} ms")
            print(f"  Max: {max(mg_latencies):.3f} ms")
            if len(mg_latencies) > 1:
                print(f"  Stdev: {statistics.stdev(mg_latencies):.3f} ms")
            if len(mg_latencies) >= 20:
                sorted_latencies = sorted(mg_latencies)
                p95_idx = int(len(sorted_latencies) * 0.95)
                p99_idx = int(len(sorted_latencies) * 0.99)
                print(f"  p95: {sorted_latencies[p95_idx]:.3f} ms")
                print(f"  p99: {sorted_latencies[p99_idx]:.3f} ms")
            print()

        # Correction Distribution
        if self.metrics["correction_magnitudes"]:
            print(f"Correction Magnitude Distribution:")
            print(f"  Count: {len(self.metrics['correction_magnitudes'])}")
            print(f"  Mean magnitude: {statistics.mean(self.metrics['correction_magnitudes']):.6f}")
            print(f"  Median magnitude: {statistics.median(self.metrics['correction_magnitudes']):.6f}")
            print(f"  Max magnitude: {max(self.metrics['correction_magnitudes']):.6f}")
            print()

        # Correction Polarity
        print(f"Correction Polarity:")
        print(f"  Positive: {self.metrics['correction_polarities']['positive']}")
        print(f"  Negative: {self.metrics['correction_polarities']['negative']}")
        print(f"  Zero: {self.metrics['correction_polarities']['zero']}\n")

        # Signal Distributions
        if self.metrics["motivation_signals"]:
            print(f"Motivation Signal Distribution:")
            print(f"  Count: {len(self.metrics['motivation_signals'])}")
            print(f"  Mean: {statistics.mean(self.metrics['motivation_signals']):.3f}")
            print(f"  Median: {statistics.median(self.metrics['motivation_signals']):.3f}")
            print(f"  Min: {min(self.metrics['motivation_signals']):.3f}")
            print(f"  Max: {max(self.metrics['motivation_signals']):.3f}\n")

        if self.metrics["goals_signals"]:
            print(f"Goals Signal Distribution:")
            print(f"  Count: {len(self.metrics['goals_signals'])}")
            print(f"  Mean: {statistics.mean(self.metrics['goals_signals']):.3f}")
            print(f"  Median: {statistics.median(self.metrics['goals_signals']):.3f}")
            print(f"  Min: {min(self.metrics['goals_signals']):.3f}")
            print(f"  Max: {max(self.metrics['goals_signals']):.3f}\n")

        # Per-Category Behavior
        print(f"Per-Category Event Distribution:")
        sorted_categories = sorted(
            self.metrics["per_category_events"].items(),
            key=lambda x: str(x[0]) if x[0] is not None else "zzz_edge_case"
        )
        for category, count in sorted_categories:
            print(f"  {category}: {count} events")
        print()

        # Per-Seed Behavior
        print(f"Per-Seed Event Distribution:")
        for seed, count in sorted(self.metrics["per_seed_events"].items()):
            print(f"  Seed {seed}: {count} events")
        print()

        # Production Path Safety
        print(f"Production Path Safety:")
        print(f"  Failures: {self.metrics['production_path_failures']}")
        print(f"  Status: {'[PASS]' if self.metrics['production_path_failures'] == 0 else '[FAIL]'}\n")

        # Error Summary
        if self.errors:
            print(f"Errors ({len(self.errors)}):")
            for err in self.errors[:10]:  # Show first 10
                print(f"  - {err}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more")
            print()

        # Build comprehensive result
        result = {
            "phase": "17.15",
            "stage": "mg_enabled_shadow_validation",
            "timestamp": self.end_time.isoformat() + "Z" if self.end_time else None,
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else None,
            "mg_enabled": self.mg_enabled,
            "seeds": self.seeds,
            "metrics": self.metrics,
            "execution_status": "COMPLETE",
        }

        # Save results
        self._save_results(result)

        print(f"{'='*80}")
        print(f"Execution complete. Results saved to 17_15_SHADOW_VALIDATION_*.json")
        print(f"{'='*80}")

        return result

    def _save_results(self, result: Dict[str, Any]) -> None:
        """Save execution artifacts."""
        # Save raw events
        events_file = self.output_dir / "17_15_SHADOW_VALIDATION_EVENTS.json"
        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump({"events": self.events}, f, indent=2)
        print(f"\n[OK] Events saved: {events_file}")

        # Save metrics report
        report_file = self.output_dir / "17_15_SHADOW_VALIDATION_REPORT.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        print(f"[OK] Report saved: {report_file}")

        # Save human-readable summary
        summary_file = self.output_dir / "17_15_SHADOW_VALIDATION_COMPLETE.md"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(self._generate_summary())
        print(f"[OK] Summary saved: {summary_file}")

    def _generate_summary(self) -> str:
        """Generate human-readable summary."""
        return f"""# 17.15 MG-Enabled Shadow Validation — Execution Report

**Phase:** 17.15  
**Stage:** MG-Enabled Shadow Validation (First Execution)  
**Date:** {self.start_time.isoformat() if self.start_time else 'unknown'}Z  
**Status:** COMPLETE

## Execution Summary

- **MG Enabled:** {self.mg_enabled}
- **Seeds:** {self.seeds}
- **Expected Events:** {self.metrics['expected_events']}
- **Actual Events:** {self.metrics['actual_events']}
- **Missing Events:** {self.metrics['missing_events']}
- **Duration:** {(self.end_time - self.start_time).total_seconds():.2f} seconds

## Key Metrics

### Event Count
```
Expected: {self.metrics['expected_events']}
Actual:   {self.metrics['actual_events']}
Missing:  {self.metrics['missing_events']}
Status:   {'[PASS]' if self.metrics['missing_events'] == 0 else '[FAIL]'}
```

### MG Computation
```
Success:   {self.metrics['mg_computation_success']}
Errors:    {self.metrics['mg_computation_errors']}
Rate:      {self.metrics['mg_computation_success'] / (self.metrics['mg_computation_success'] + self.metrics['mg_computation_errors']) * 100:.1f}%
```

### Fallback Triggered
```
Count: {self.metrics['fallback_triggered']}
Rate:  {self.metrics['fallback_triggered'] / self.metrics['actual_events'] * 100 if self.metrics['actual_events'] > 0 else 0:.1f}%
```

### MG Latency
```
Samples: {len(self.metrics['mg_latencies'])}
Mean:    {statistics.mean(self.metrics['mg_latencies']):.3f} ms
Median:  {statistics.median(self.metrics['mg_latencies']):.3f} ms
Min:     {min(self.metrics['mg_latencies']) if self.metrics['mg_latencies'] else 'N/A'}
Max:     {max(self.metrics['mg_latencies']) if self.metrics['mg_latencies'] else 'N/A'}
```

### Production Path Safety
```
Failures: {self.metrics['production_path_failures']}
Status:   {'[PASS]' if self.metrics['production_path_failures'] == 0 else '[FAIL]'}
```

## Next Steps

This execution provides the data needed for 17.15 safety analysis.

**Do not interpret as success/failure yet.**

Next: Analyze metrics distributions, per-category behavior, and error patterns.

Then: Apply 17.15 decision gate based on safety analysis results.
"""


def main():
    """Execute 17.15 MG-enabled shadow validation."""
    # Frozen parameters (from 17_15_EXPERIMENT_MANIFEST.md)
    seeds = [1000, 2000, 3000, 4000, 5000, 6000]
    num_simulations = 100
    mg_enabled = True

    runner = ShadowValidationRunMGEnabled(
        output_dir=Path("d:/AURA"),
        mg_enabled=mg_enabled,
        seeds=seeds
    )

    result = runner.run(num_simulations=num_simulations)
    return result


if __name__ == "__main__":
    main()
