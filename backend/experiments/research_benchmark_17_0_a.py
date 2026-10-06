"""
17.0A Research Benchmark Dataset Generator CLI

Generates and persists a deterministic 100-experience benchmark dataset
for research validation of AURA's learning capabilities.

Usage:
    python -m backend.experiments.research_benchmark_17_0_a
    python -m backend.experiments.research_benchmark_17_0_a --seed 123 --training-size 100 --held-out-size 25
    python -m backend.experiments.research_benchmark_17_0_a --list
"""

import argparse
import json
from pathlib import Path
from backend.experiments.research_benchmark_generator import (
    ResearchBenchmarkGenerator,
)
from backend.experiments.research_dataset_persistence import (
    ResearchDatasetPersistence,
)


def main():
    parser = argparse.ArgumentParser(
        description="17.0A Research Benchmark Dataset Generator"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic generation (default: 42)",
    )
    parser.add_argument(
        "--training-size",
        type=int,
        default=80,
        help="Number of training experiences (default: 80)",
    )
    parser.add_argument(
        "--held-out-size",
        type=int,
        default=20,
        help="Number of held-out evaluation experiences (default: 20)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="backend/experiments/data",
        help="Output directory for dataset files (default: backend/experiments/data)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available datasets",
    )
    parser.add_argument(
        "--load",
        type=str,
        help="Load and display a specific dataset by ID",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Display statistics about the generated dataset",
    )

    args = parser.parse_args()

    persistence = ResearchDatasetPersistence(output_dir=args.output_dir)

    if args.list:
        datasets = persistence.list_datasets()
        if datasets:
            print("Available datasets:")
            for dataset_id in datasets:
                print(f"  - {dataset_id}")
        else:
            print("No datasets found.")
        return

    if args.load:
        try:
            dataset = persistence.load_dataset(args.load)
            print(f"\nLoaded dataset: {dataset.dataset_id}")
            print(f"  Seed: {dataset.seed}")
            print(f"  Training experiences: {dataset.training_size()}")
            print(f"  Held-out experiences: {dataset.held_out_size()}")
            print(f"  Total: {dataset.total_size()}")

            if args.stats:
                _print_dataset_statistics(dataset)
        except FileNotFoundError as e:
            print(f"Error: {e}")
        return

    # Generate new dataset
    print(f"Generating research benchmark dataset...")
    print(f"  Seed: {args.seed}")
    print(f"  Training experiences: {args.training_size}")
    print(f"  Held-out experiences: {args.held_out_size}")

    generator = ResearchBenchmarkGenerator(seed=args.seed)
    dataset = generator.generate_dataset(
        training_size=args.training_size, held_out_size=args.held_out_size
    )

    filepath = persistence.save_dataset(dataset)
    print(f"\n[OK] Dataset saved to: {filepath}")
    print(f"  Dataset ID: {dataset.dataset_id}")

    if args.stats:
        print()
        _print_dataset_statistics(dataset)


def _print_dataset_statistics(dataset):
    """Print detailed statistics about the dataset."""
    from collections import defaultdict

    print("\nDataset Statistics:")

    # Categories
    all_experiences = (
        dataset.training_experiences + dataset.held_out_experiences
    )
    by_category = defaultdict(list)
    for exp in all_experiences:
        by_category[exp.category].append(exp)

    print("\n  Experience Categories:")
    for category in sorted(by_category.keys()):
        count = len(by_category[category])
        errors = [exp.prediction_error() for exp in by_category[category]]
        avg_error = sum(errors) / len(errors)
        min_error = min(errors)
        max_error = max(errors)
        print(
            f"    {category:20s}: {count:3d} experiences, "
            f"MAE: avg={avg_error:.2f}, min={min_error:.2f}, max={max_error:.2f}"
        )

    # Overall metrics
    print("\n  Overall Metrics:")
    all_errors = [exp.prediction_error() for exp in all_experiences]
    print(f"    Total experiences: {len(all_experiences)}")
    print(f"    Baseline MAE (all): {sum(all_errors) / len(all_errors):.2f}")
    print(f"    Min MAE: {min(all_errors):.2f}")
    print(f"    Max MAE: {max(all_errors):.2f}")

    # Skills summary
    print("\n  Skills Represented:")
    all_skills = set()
    for exp in all_experiences:
        all_skills.update(exp.initial_state.keys())
    print(f"    {', '.join(sorted(all_skills))}")


if __name__ == "__main__":
    main()
