"""
17.0B Research Experiment CLI

Run and save the Baseline vs Learning comparison experiment.

Usage:
    python -m backend.experiments.research_experiment_cli_17_0_b
    python -m backend.experiments.research_experiment_cli_17_0_b --dataset research_benchmark_v1_seed_42 --learning-rate 0.1
    python -m backend.experiments.research_experiment_cli_17_0_b --load <experiment_id> --summary
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from backend.experiments.research_experiment_17_0_b import (
    run_research_experiment_17_0_b,
)


def main():
    parser = argparse.ArgumentParser(
        description="17.0B Research Experiment Runner"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="research_benchmark_v1_seed_42",
        help="Research dataset ID to use (default: research_benchmark_v1_seed_42)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.1,
        help="Learning rate for calibration (default: 0.1)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="backend/experiments/results",
        help="Output directory for experiment results (default: backend/experiments/results)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print summary of results after running",
    )
    parser.add_argument(
        "--load",
        type=str,
        help="Load and display a saved experiment result by ID",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed results",
    )

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.load:
        try:
            result = _load_experiment_result(args.load, output_dir)
            print(f"\nLoaded experiment: {result['experiment_id']}")
            _print_experiment_summary(result, verbose=args.verbose)
        except FileNotFoundError as e:
            print(f"Error: {e}")
        return

    # Run experiment
    print(f"Running research experiment 17.0B...")
    print(f"  Dataset: {args.dataset}")
    print(f"  Learning rate: {args.learning_rate}")
    print(f"  Output directory: {output_dir}")
    print()

    result = run_research_experiment_17_0_b(
        dataset_id=args.dataset,
        learning_rate=args.learning_rate,
    )

    # Save result
    result_dict = result.model_dump()
    result_file = (
        output_dir / f"{result.experiment_id}.json"
    )
    with open(result_file, "w") as f:
        json.dump(result_dict, f, indent=2, default=str)

    print(f"[OK] Experiment complete: {result.experiment_id}")
    print(f"[OK] Results saved to: {result_file}")
    print()

    if args.summary:
        _print_experiment_summary(result_dict, verbose=args.verbose)


def _load_experiment_result(experiment_id: str, output_dir: Path) -> dict:
    """Load a saved experiment result."""
    result_file = output_dir / f"{experiment_id}.json"
    if not result_file.exists():
        raise FileNotFoundError(f"Experiment result not found: {result_file}")

    with open(result_file, "r") as f:
        return json.load(f)


def _print_experiment_summary(result: dict, verbose: bool = False):
    """Print a summary of experiment results."""
    print("=" * 70)
    print("RESEARCH EXPERIMENT 17.0B RESULTS")
    print("=" * 70)
    print()
    print(f"Dataset: {result['dataset_id']}")
    print(f"Seed: {result['seed']}")
    print(f"Training experiences: {result['training_size']}")
    print(f"Held-out experiences: {result['held_out_size']}")
    print(f"Learning rate: {result['learning_rate']}")
    print()
    print("-" * 70)
    print("PRIMARY METRICS")
    print("-" * 70)
    print()
    print(f"Baseline MAE (held-out): {result['baseline_mae']:.4f}")
    print(f"Learning MAE (held-out): {result['learning_mae']:.4f}")
    print()
    print(f"Absolute Improvement:    {result['absolute_improvement']:+.4f}")
    print(f"Improvement Percent:     {result['improvement_percent']:+.2f}%")
    print()

    if result["learning_is_better"]:
        print("[SUCCESS] Learning system improved prediction accuracy!")
    else:
        print("[INFO] Learning system did not improve (or equal) baseline.")

    if verbose:
        print()
        print("-" * 70)
        print("DETAILED RESULTS")
        print("-" * 70)
        print()

        print("BASELINE SYSTEM")
        print(f"  Training MAE: {result['baseline_results']['training_predictions'][0] if result['baseline_results']['training_predictions'] else 'N/A'}")
        baseline_preds = result["baseline_results"]["held_out_predictions"]
        if baseline_preds:
            baseline_maes = [p["mae"] for p in baseline_preds]
            print(
                f"  Held-out MAE by experience: min={min(baseline_maes):.4f}, "
                f"max={max(baseline_maes):.4f}, "
                f"avg={sum(baseline_maes)/len(baseline_maes):.4f}"
            )

        print()
        print("LEARNING SYSTEM")
        learning_preds = result["learning_results"]["held_out_predictions"]
        if learning_preds:
            learning_maes = [p["mae"] for p in learning_preds]
            print(
                f"  Held-out MAE by experience: min={min(learning_maes):.4f}, "
                f"max={max(learning_maes):.4f}, "
                f"avg={sum(learning_maes)/len(learning_maes):.4f}"
            )

        print()
        print("FINAL CALIBRATION PARAMETERS")
        final_params = result["learning_results"]["final_calibration_parameters"]
        print(f"  uncertainty: {final_params.get('uncertainty', 'N/A')}")
        print(f"  risk_bias: {final_params.get('risk_bias', 'N/A')}")
        print(
            f"  transition_probability_bias: {final_params.get('transition_probability_bias', 'N/A')}"
        )
        print(f"  confidence: {final_params.get('confidence', 'N/A')}")
        state_bias = final_params.get("expected_state_bias", {})
        if state_bias:
            print(f"  expected_state_bias:")
            for key, val in sorted(state_bias.items()):
                print(f"    {key}: {val}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
