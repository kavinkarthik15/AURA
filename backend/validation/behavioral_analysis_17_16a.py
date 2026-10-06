#!/usr/bin/env python3
"""
17.16A Behavioral Analysis - Correction Pattern Analysis

Analyze the frozen 2,400 shadow events to answer:
1. Correction distribution (min, max, mean, median, stdev, percentiles)
2. Signal → correction relationship (motivation, goals)
3. Category behavior comparison
4. Seed consistency
5. Prediction impact (shift magnitude, NOT accuracy)
6. Anomaly analysis

NOTE: This analysis DOES NOT modify frozen events.
NOTE: This analyzes correction behavior, NOT prediction accuracy.
      Accuracy requires ground truth (17.16B).
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import statistics
from collections import defaultdict


class BehavioralAnalysis17_16A:
    """Analyze correction behavior patterns from frozen 2,400 events."""

    def __init__(self, events_file: Path):
        self.events_file = events_file
        self.events: List[Dict[str, Any]] = []
        self.results = {
            "phase": "17.16A",
            "analysis_type": "Correction Pattern Analysis",
            "events_analyzed": 0,
            "sections": {}
        }

    def load_events(self) -> bool:
        """Load frozen 2,400 events."""
        try:
            with open(self.events_file, 'r') as f:
                data = json.load(f)
            self.events = data.get("events", [])
            self.results["events_analyzed"] = len(self.events)
            print(f"Loaded {len(self.events)} events")
            return True
        except Exception as e:
            print(f"Error loading events: {e}")
            return False

    def analyze_correction_distribution(self) -> Dict[str, Any]:
        """
        Analyze: minimum, maximum, mean, median, stdev, percentiles, outliers
        """
        print("\n=== SECTION A: Correction Distribution ===")

        corrections = []
        for event in self.events:
            mg_corr = event.get("mg_correction", {})
            if mg_corr.get("correction_applied"):
                val = mg_corr.get("correction_value", 0)
                corrections.append(val)

        if not corrections:
            print("No corrections found")
            return {"error": "No corrections"}

        # Calculate statistics
        result = {
            "total_corrections": len(corrections),
            "all_applied": len(corrections) == len(self.events),
            "minimum": min(corrections),
            "maximum": max(corrections),
            "mean": statistics.mean(corrections),
            "median": statistics.median(corrections),
            "stdev": statistics.stdev(corrections) if len(corrections) > 1 else 0,
            "q25": self._percentile(corrections, 25),
            "q75": self._percentile(corrections, 75),
            "p95": self._percentile(corrections, 95),
            "p99": self._percentile(corrections, 99),
        }

        # Outlier detection (values > 3 stdev from mean)
        if result["stdev"] > 0:
            mean = result["mean"]
            stdev = result["stdev"]
            outliers = [c for c in corrections if abs(c - mean) > 3 * stdev]
            result["outliers_3sigma"] = len(outliers)
            result["outlier_values"] = sorted(outliers)[:10]  # Top 10
        else:
            result["outliers_3sigma"] = 0
            result["outlier_values"] = []

        # Polarity
        result["positive_count"] = sum(1 for c in corrections if c > 0)
        result["negative_count"] = sum(1 for c in corrections if c < 0)
        result["zero_count"] = sum(1 for c in corrections if c == 0)
        result["positive_pct"] = (result["positive_count"] / len(corrections) * 100) if corrections else 0

        # Print summary
        print(f"Total corrections: {result['total_corrections']}")
        print(f"Range: [{result['minimum']:.6f}, {result['maximum']:.6f}]")
        print(f"Mean: {result['mean']:.6f}, Median: {result['median']:.6f}, StDev: {result['stdev']:.6f}")
        print(f"Percentiles: Q25={result['q25']:.6f}, Q75={result['q75']:.6f}, p95={result['p95']:.6f}, p99={result['p99']:.6f}")
        print(f"Polarity: {result['positive_count']} positive, {result['negative_count']} negative, {result['zero_count']} zero")
        print(f"Outliers (>3σ): {result['outliers_3sigma']}")

        self.results["sections"]["A_correction_distribution"] = result
        return result

    def analyze_signal_correction_relationships(self) -> Dict[str, Any]:
        """
        Analyze: motivation → correction, goals → correction
        """
        print("\n=== SECTION B: Signal → Correction Relationships ===")

        # Collect by motivation signal value
        by_motivation = defaultdict(list)
        by_goals = defaultdict(list)
        by_signal_pair = defaultdict(list)

        for event in self.events:
            corr_val = event.get("mg_correction", {}).get("correction_value", 0)
            mot = event.get("motivation_signal")
            goal = event.get("goals_signal")

            if mot is not None:
                by_motivation[mot].append(corr_val)
            if goal is not None:
                by_goals[round(goal, 4)].append(corr_val)  # Round for bucketing
            if mot is not None and goal is not None:
                pair_key = (mot, round(goal, 4))
                by_signal_pair[pair_key].append(corr_val)

        result = {
            "motivation_levels": {},
            "goals_buckets": {},
            "signal_pair_stability": {}
        }

        # Motivation → Correction
        print("\nMotivation Signal → Correction Magnitude:")
        for mot in sorted(by_motivation.keys()):
            corrections = by_motivation[mot]
            stats = {
                "count": len(corrections),
                "mean": statistics.mean(corrections),
                "median": statistics.median(corrections),
                "stdev": statistics.stdev(corrections) if len(corrections) > 1 else 0,
                "min": min(corrections),
                "max": max(corrections),
            }
            result["motivation_levels"][mot] = stats
            print(f"  Motivation={mot}: mean={stats['mean']:.6f}, stdev={stats['stdev']:.6f}, n={stats['count']}")

        # Goals → Correction
        print("\nGoals Signal → Correction Magnitude:")
        for goals in sorted(by_goals.keys()):
            corrections = by_goals[goals]
            stats = {
                "count": len(corrections),
                "mean": statistics.mean(corrections),
                "median": statistics.median(corrections),
                "stdev": statistics.stdev(corrections) if len(corrections) > 1 else 0,
                "min": min(corrections),
                "max": max(corrections),
            }
            result["goals_buckets"][goals] = stats
            # Only print if we have meaningful sample
            if len(corrections) > 10:
                print(f"  Goals≈{goals}: mean={stats['mean']:.6f}, stdev={stats['stdev']:.6f}, n={stats['count']}")

        # Signal pair consistency (same pair → same correction?)
        print("\nSignal Pair Stability (reproducibility):")
        pair_consistency_issues = []
        for pair, corrections in sorted(by_signal_pair.items()):
            if len(corrections) > 1:
                stdev = statistics.stdev(corrections) if len(corrections) > 1 else 0
                mean = statistics.mean(corrections)
                # High variance for same pair = problematic
                if stdev > 0.01 * mean:  # More than 1% variance
                    pair_consistency_issues.append({
                        "pair": pair,
                        "count": len(corrections),
                        "mean": mean,
                        "stdev": stdev,
                        "cv": stdev / mean if mean != 0 else 0
                    })

        result["signal_pair_consistency_issues"] = len(pair_consistency_issues)
        result["problematic_pairs"] = pair_consistency_issues[:5]  # Top 5
        print(f"Total signal pairs: {len(by_signal_pair)}")
        print(f"Pairs with high variance: {len(pair_consistency_issues)}")

        # Relationship direction: Is it monotonic?
        if len(result["motivation_levels"]) == 2:  # Usually 0.0 and 1.0
            levels = sorted(result["motivation_levels"].keys())
            mean_0 = result["motivation_levels"][levels[0]]["mean"]
            mean_1 = result["motivation_levels"][levels[1]]["mean"]
            direction = "↑" if mean_1 > mean_0 else "↓" if mean_1 < mean_0 else "→"
            print(f"\nMotivation relationship: {levels[0]}→{mean_0:.4f} {direction} {levels[1]}→{mean_1:.4f}")
            result["motivation_monotonic"] = mean_1 >= mean_0

        self.results["sections"]["B_signal_correction"] = result
        return result

    def analyze_category_behavior(self) -> Dict[str, Any]:
        """
        Compare low_skill_practice, project_completion, high_motivation, edge_case
        """
        print("\n=== SECTION C: Category Behavior ===")

        by_category = defaultdict(lambda: {
            "events": [],
            "corrections": [],
            "motivations": [],
            "goals": [],
            "latencies": [],
            "fallbacks": 0
        })

        for event in self.events:
            cat = event.get("category") or "unknown"
            corr = event.get("mg_correction", {}).get("correction_value", 0)
            mot = event.get("motivation_signal")
            goal = event.get("goals_signal")
            lat = event.get("mg_latency_ms", 0)
            fallback = event.get("fallback_triggered", False)

            by_category[cat]["events"].append(event)
            by_category[cat]["corrections"].append(corr)
            if mot is not None:
                by_category[cat]["motivations"].append(mot)
            if goal is not None:
                by_category[cat]["goals"].append(goal)
            by_category[cat]["latencies"].append(lat)
            if fallback:
                by_category[cat]["fallbacks"] += 1

        result = {}
        print("\nCategory-Level Statistics:")
        for cat in sorted([c for c in by_category.keys() if c is not None]):
            data = by_category[cat]
            stats = {
                "event_count": len(data["events"]),
                "correction_mean": statistics.mean(data["corrections"]),
                "correction_median": statistics.median(data["corrections"]),
                "correction_stdev": statistics.stdev(data["corrections"]) if len(data["corrections"]) > 1 else 0,
                "correction_range": (min(data["corrections"]), max(data["corrections"])),
                "motivation_mean": statistics.mean(data["motivations"]) if data["motivations"] else None,
                "goals_mean": statistics.mean(data["goals"]) if data["goals"] else None,
                "latency_mean": statistics.mean(data["latencies"]),
                "latency_p99": self._percentile(data["latencies"], 99),
                "fallback_count": data["fallbacks"],
                "fallback_rate": data["fallbacks"] / len(data["events"]) * 100,
            }
            result[cat] = stats
            print(f"\n{cat}:")
            print(f"  Events: {stats['event_count']}")
            print(f"  Correction: mean={stats['correction_mean']:.6f}, median={stats['correction_median']:.6f}, stdev={stats['correction_stdev']:.6f}")
            print(f"  Correction range: {stats['correction_range']}")
            motivation_str = f"{stats['motivation_mean']:.4f}" if stats['motivation_mean'] is not None else "N/A"
            print(f"  Motivation: {motivation_str}")
            goals_str = f"{stats['goals_mean']:.4f}" if stats['goals_mean'] is not None else "N/A"
            print(f"  Goals: {goals_str}")
            print(f"  Latency: mean={stats['latency_mean']:.4f}ms, p99={stats['latency_p99']:.4f}ms")
            print(f"  Fallback: {stats['fallback_count']} ({stats['fallback_rate']:.2f}%)")

        self.results["sections"]["C_category_behavior"] = result
        return result

    def analyze_seed_consistency(self) -> Dict[str, Any]:
        """
        Compare seeds [1000, 2000, 3000, 4000, 5000, 6000]
        """
        print("\n=== SECTION D: Seed Consistency ===")

        # Extract seed from seed parameter (currently null in events)
        # Instead, we'll use event order: every 100 events per seed
        # Seeds: 1000, 2000, 3000, 4000, 5000, 6000
        # Each: 100 sims × 4 categories = 400 events per seed

        by_seed = defaultdict(list)
        seeds = [1000, 2000, 3000, 4000, 5000, 6000]
        events_per_seed = 400

        for idx, event in enumerate(self.events):
            seed_idx = idx // events_per_seed
            if seed_idx < len(seeds):
                seed = seeds[seed_idx]
                corr = event.get("mg_correction", {}).get("correction_value", 0)
                by_seed[seed].append(corr)

        result = {}
        print("\nSeed-Level Statistics:")
        seed_means = []
        for seed in seeds:
            corrections = by_seed[seed]
            if corrections:
                stats = {
                    "event_count": len(corrections),
                    "mean": statistics.mean(corrections),
                    "median": statistics.median(corrections),
                    "stdev": statistics.stdev(corrections) if len(corrections) > 1 else 0,
                }
                result[seed] = stats
                seed_means.append(stats["mean"])
                print(f"  Seed {seed}: mean={stats['mean']:.6f}, stdev={stats['stdev']:.6f}, n={stats['event_count']}")

        # Consistency check: are seed means similar?
        if seed_means:
            seed_stdev = statistics.stdev(seed_means) if len(seed_means) > 1 else 0
            result["cross_seed_mean"] = statistics.mean(seed_means)
            result["cross_seed_stdev"] = seed_stdev
            result["seed_consistency"] = "stable" if seed_stdev < 0.01 else "variable"
            print(f"\nCross-seed statistics:")
            print(f"  Mean of means: {result['cross_seed_mean']:.6f}")
            print(f"  StDev of means: {seed_stdev:.6f}")
            print(f"  Verdict: {result['seed_consistency']}")

        self.results["sections"]["D_seed_consistency"] = result
        return result

    def analyze_prediction_impact(self) -> Dict[str, Any]:
        """
        Calculate |MG_predicted - Legacy_predicted| per category, per seed
        NOTE: This is prediction SHIFT, not accuracy improvement
        """
        print("\n=== SECTION E: Prediction Impact (Shift Magnitude) ===")

        prediction_shifts = []
        by_category_shift = defaultdict(list)

        for event in self.events:
            legacy_pred = event.get("legacy_prediction", {}).get("predicted_future_state", {})
            mg_pred = event.get("mg_shadow_prediction", {}).get("predicted_future_state", {})
            cat = event.get("category") or "unknown"

            # Calculate shift across all skills
            if legacy_pred and mg_pred:
                shift_per_skill = []
                for skill in legacy_pred:
                    if skill in mg_pred:
                        shift = abs(mg_pred[skill] - legacy_pred[skill])
                        shift_per_skill.append(shift)
                
                if shift_per_skill:
                    avg_shift = statistics.mean(shift_per_skill)
                    prediction_shifts.append(avg_shift)
                    by_category_shift[cat].append(avg_shift)

        result = {
            "shift_distribution": {
                "count": len(prediction_shifts),
                "mean": statistics.mean(prediction_shifts) if prediction_shifts else 0,
                "median": statistics.median(prediction_shifts) if prediction_shifts else 0,
                "stdev": statistics.stdev(prediction_shifts) if len(prediction_shifts) > 1 else 0,
                "min": min(prediction_shifts) if prediction_shifts else 0,
                "max": max(prediction_shifts) if prediction_shifts else 0,
            },
            "by_category": {}
        }

        print("\nPrediction Shift (MG adjusted legacy prediction):")
        print(f"Overall: mean={result['shift_distribution']['mean']:.6f}, stdev={result['shift_distribution']['stdev']:.6f}")

        for cat in sorted(by_category_shift.keys()):
            shifts = by_category_shift[cat]
            cat_stats = {
                "count": len(shifts),
                "mean": statistics.mean(shifts),
                "median": statistics.median(shifts),
                "stdev": statistics.stdev(shifts) if len(shifts) > 1 else 0,
            }
            result["by_category"][cat] = cat_stats
            print(f"  {cat}: mean_shift={cat_stats['mean']:.6f}")

        print("\n⚠️  NOTE: Prediction shift ≠ improvement. We cannot say which is correct without ground truth.")

        self.results["sections"]["E_prediction_impact"] = result
        return result

    def analyze_anomalies(self) -> Dict[str, Any]:
        """
        Look for: very large corrections, unexpected polarity, instability,
        unusual signal/correction combinations
        """
        print("\n=== SECTION F: Anomaly Analysis ===")

        anomalies = {
            "very_large_corrections": [],
            "zero_corrections": [],
            "negative_corrections": [],
            "high_variance_categories": [],
            "high_fallback_categories": [],
            "seed_variance": []
        }

        # Collect corrections
        all_corrections = [e.get("mg_correction", {}).get("correction_value", 0) for e in self.events]
        mean_corr = statistics.mean(all_corrections)
        stdev_corr = statistics.stdev(all_corrections) if len(all_corrections) > 1 else 0

        # Find very large corrections (>2σ above mean)
        for event in self.events:
            corr = event.get("mg_correction", {}).get("correction_value", 0)
            if corr > mean_corr + 2 * stdev_corr:
                anomalies["very_large_corrections"].append({
                    "value": corr,
                    "category": event.get("category"),
                    "motivation": event.get("motivation_signal"),
                    "goals": event.get("goals_signal"),
                })
            if corr == 0:
                anomalies["zero_corrections"].append({
                    "category": event.get("category"),
                })
            if corr < 0:
                anomalies["negative_corrections"].append({
                    "value": corr,
                    "category": event.get("category"),
                })

        print("\nAnomalies Detected:")
        print(f"  Very large corrections (>mean+2σ): {len(anomalies['very_large_corrections'])}")
        if anomalies["very_large_corrections"]:
            for anom in anomalies["very_large_corrections"][:5]:
                print(f"    - Value={anom['value']:.4f}, Cat={anom['category']}, Mot={anom['motivation']}, Goal={anom['goals']}")

        print(f"  Zero corrections: {len(anomalies['zero_corrections'])}")
        print(f"  Negative corrections: {len(anomalies['negative_corrections'])}")
        if anomalies["negative_corrections"]:
            for anom in anomalies["negative_corrections"][:5]:
                print(f"    - Value={anom['value']:.4f}, Cat={anom['category']}")

        # Unexpected signal/correction combinations
        print("\nUnexpected combinations (if any):")
        unexpected = []
        for event in self.events:
            mot = event.get("motivation_signal")
            goal = event.get("goals_signal")
            corr = event.get("mg_correction", {}).get("correction_value", 0)
            # If high motivation + high goals but zero correction = unexpected
            if mot == 1.0 and goal > 0.2 and corr < 0.1:
                unexpected.append({
                    "motivation": mot,
                    "goals": goal,
                    "correction": corr,
                    "category": event.get("category")
                })

        print(f"  High signals but near-zero correction: {len(unexpected)}")

        anomalies["unexpected_combinations"] = len(unexpected)
        self.results["sections"]["F_anomalies"] = anomalies
        return anomalies

    def produce_mechanistic_verdict(self) -> Dict[str, Any]:
        """
        Summary verdict: Is the correction mechanism behaving as intended?
        """
        print("\n=== SECTION G: Mechanistic Sensibility Verdict ===")

        verdict = {
            "mechanism_behaves_sensibly": True,
            "concerns": [],
            "strengths": []
        }

        # Check distribution
        dist = self.results["sections"].get("A_correction_distribution", {})
        if dist.get("outliers_3sigma", 0) > 50:  # More than 2% outliers
            verdict["concerns"].append("High outlier rate suggests occasional wild corrections")
            verdict["mechanism_behaves_sensibly"] = False
        else:
            verdict["strengths"].append("Correction distribution is well-behaved (few outliers)")

        # Check signal relationships
        signals = self.results["sections"].get("B_signal_correction", {})
        if signals.get("signal_pair_consistency_issues", 0) > 10:
            verdict["concerns"].append("Signal pairs show high variance (non-deterministic)")
            verdict["mechanism_behaves_sensibly"] = False
        else:
            verdict["strengths"].append("Signal pairs are reproducible (deterministic)")

        # Check category behavior
        categories = self.results["sections"].get("C_category_behavior", {})
        for cat, stats in categories.items():
            if stats.get("fallback_rate", 0) > 1.0:
                verdict["concerns"].append(f"{cat} has high fallback rate ({stats['fallback_rate']:.2f}%)")
                verdict["mechanism_behaves_sensibly"] = False

        # Check seed consistency
        seeds = self.results["sections"].get("D_seed_consistency", {})
        if seeds.get("seed_consistency") == "variable":
            verdict["concerns"].append("Seed-to-seed behavior varies significantly")
        else:
            verdict["strengths"].append("Seed-to-seed behavior is consistent")

        print(f"\nMechanism Verdict: {'SENSIBLE' if verdict['mechanism_behaves_sensibly'] else 'PROBLEMATIC'}")
        print("\nStrengths:")
        for s in verdict["strengths"]:
            print(f"  ✓ {s}")
        print("\nConcerns:")
        for c in verdict["concerns"]:
            print(f"  ✗ {c}")

        self.results["sections"]["G_mechanistic_verdict"] = verdict
        return verdict

    def produce_17_16b_recommendations(self) -> Dict[str, Any]:
        """
        Based on 17.16A findings, what should 17.16B measure?
        """
        print("\n=== SECTION H: Recommendations for 17.16B (Outcome Study) ===")

        recommendations = {
            "proceed_to_17_16b": True,
            "focus_areas": [],
            "design_notes": []
        }

        verdict = self.results["sections"].get("G_mechanistic_verdict", {})
        if not verdict.get("mechanism_behaves_sensibly"):
            recommendations["proceed_to_17_16b"] = False
            recommendations["design_notes"].append("Mechanism shows problems; fix before outcome study")
        else:
            recommendations["design_notes"].append("Mechanism is sound; proceed to outcome-based validation")

        # Identify which categories to focus on
        categories = self.results["sections"].get("C_category_behavior", {})
        for cat in categories:
            recommendations["focus_areas"].append(f"Validate {cat} outcomes")

        recommendations["design_notes"].append("17.16B must capture: state_before, action, actual_state_after, error_legacy, error_mg")
        recommendations["design_notes"].append("Calculate ΔError = |Actual - MG| - |Actual - Legacy|")
        recommendations["design_notes"].append("Interpret: ΔError < 0 means MG improved prediction")

        print("\nRecommendation: Proceed to 17.16B")
        print("17.16B must capture actual outcomes to measure:")
        print("  Error_Legacy = |Actual - LegacyPrediction|")
        print("  Error_MG = |Actual - MGPrediction|")
        print("  ΔError = Error_MG - Error_Legacy")
        print("\nIf ΔError < 0 for majority of events: MG improved accuracy")
        print("If ΔError ≈ 0: No significant change")
        print("If ΔError > 0: MG made predictions worse")

        self.results["sections"]["H_17_16b_recommendations"] = recommendations
        return recommendations

    def save_results(self, output_file: Path) -> bool:
        """Save complete analysis results."""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n✓ Analysis saved to {output_file}")
            return True
        except Exception as e:
            print(f"Error saving results: {e}")
            return False

    @staticmethod
    def _percentile(data: List[float], p: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0
        sorted_data = sorted(data)
        idx = (p / 100) * (len(sorted_data) - 1)
        lower = int(idx)
        upper = lower + 1
        if upper >= len(sorted_data):
            return sorted_data[lower]
        weight = idx - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight


def main():
    """Execute 17.16A behavioral analysis."""
    events_file = Path("d:/AURA/17_15_SHADOW_VALIDATION_EVENTS.json")
    output_file = Path("d:/AURA/17_16A_BEHAVIORAL_ANALYSIS_RESULTS.json")

    print("=" * 80)
    print("17.16A BEHAVIORAL ANALYSIS - CORRECTION PATTERN ANALYSIS")
    print("=" * 80)

    analyzer = BehavioralAnalysis17_16A(events_file)

    # Load frozen events
    if not analyzer.load_events():
        print("Failed to load events")
        return

    # Execute analyses
    analyzer.analyze_correction_distribution()
    analyzer.analyze_signal_correction_relationships()
    analyzer.analyze_category_behavior()
    analyzer.analyze_seed_consistency()
    analyzer.analyze_prediction_impact()
    analyzer.analyze_anomalies()
    analyzer.produce_mechanistic_verdict()
    analyzer.produce_17_16b_recommendations()

    # Save results
    analyzer.save_results(output_file)

    print("\n" + "=" * 80)
    print("17.16A ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
