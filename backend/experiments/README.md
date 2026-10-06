# Backend Experiment Runner

This package provides a reproducible experiment runner for the AURA closed-loop calibration and validation pipeline.

## CLI entrypoint

Run the experiment runner from the repository root:

```bash
python -m backend.experiments.experiment_cli --pairs 2 --output-dir ./experiments/out --experiment-id my_exp
```

## Supported CLI arguments

- `--pairs`: number of experience pairs to generate (required)
- `--learning-rate`: calibration learning rate (default: `0.1`)
- `--apply-accepted`: apply accepted calibration proposals (default: enabled)
- `--no-apply-accepted`: disable applying accepted proposals
- `--output-dir`: directory to write persistence outputs
- `--experiment-id`: base name for saved files
- `--seed`: PRNG seed for synthetic experience generation
- `--noise-scale`: scale of synthetic actual-state deviations

## Outputs

When `--output-dir` is provided, the runner writes three files:

- `experiment_id.json` — full experiment record as JSON
- `experiment_id.jsonl` — metadata followed by one JSON step record per line
- `experiment_id.csv` — step-level summary rows for analysis

## Example

```bash
python -m backend.experiments.experiment_cli \
  --pairs 3 \
  --learning-rate 0.05 \
  --output-dir backend/experiments/out \
  --experiment-id closed_loop_eval \
  --seed 42
```

The CLI also prints a short summary with mean baseline error, calibrated error, and improvement.
