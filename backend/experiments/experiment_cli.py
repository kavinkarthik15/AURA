from __future__ import annotations

import argparse
import sys
from backend.experiments.experiment_config import ExperimentConfig
from backend.experiments.experiment_runner import ExperimentRunner


def main(argv=None):
    parser = argparse.ArgumentParser(prog="experiment_cli")
    parser.add_argument("--pairs", type=int, required=True, help="Number of experience pairs")
    parser.add_argument("--learning-rate", type=float, default=0.1)
    parser.add_argument("--apply-accepted", action="store_true")
    parser.add_argument("--no-apply-accepted", dest="apply_accepted", action="store_false")
    parser.set_defaults(apply_accepted=True)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--experiment-id", type=str, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--noise-scale", type=float, default=1.0)

    args = parser.parse_args(argv)

    config = ExperimentConfig(
        pairs=args.pairs,
        learning_rate=args.learning_rate,
        apply_accepted=args.apply_accepted,
        output_dir=args.output_dir,
        experiment_id=args.experiment_id,
        seed=args.seed,
        noise_scale=args.noise_scale,
    )

    runner = ExperimentRunner()
    res = runner.run(config)

    br = res["batch_result"]
    metrics = res["metrics"]
    print(f"Experiment {res['experiment_id']} - pairs={len(br.steps)}")
    print(f"Mean baseline error: {br.mean_baseline_error}")
    print(f"Mean calibrated error: {br.mean_calibrated_error}")
    print(f"Mean improvement: {br.mean_improvement}")
    print(f"Overall acceptance rate: {metrics.acceptance_rate}")
    print(f"Overall rejection rate: {metrics.rejection_rate}")
    print(f"Overall parameter drift: {metrics.parameter_drift}")
    print(f"Rolling baseline MAE: {metrics.rolling_baseline_mae}")
    print(f"Rolling calibrated MAE: {metrics.rolling_calibrated_mae}")
    print(f"Rolling improvement %: {metrics.rolling_improvement_pct}")


if __name__ == "__main__":
    main()
