# Continual Learning Pipeline

The continual-learning pipeline turns execution outcomes into model updates through a repeatable cycle:

Experience
↓
Replay Buffer
↓
Dataset Builder
↓
Trainer
↓
Benchmark
↓
Deployment
↓
Registry

## Components

- Replay Buffer: deduplicates and prioritizes recorded experiences.
- Dataset Builder: converts experience records into training samples.
- Trainer: trains a candidate model from merged base and experience data.
- Benchmark: compares a candidate model against the currently deployed model.
- Deployment: applies configurable acceptance criteria before promoting a model.
- Registry: records lineage, acceptance state, benchmark metrics, and training metadata.

## Acceptance Criteria

The deployment gate accepts a candidate when it improves R² and remains within the MAE tolerance relative to the deployed model.
