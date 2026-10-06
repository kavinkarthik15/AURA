# Sprint 8 Milestone

## Architecture

- Rule-based transition baseline remains available through the TransitionEngine.
- Learned sequence-aware prediction is provided by SequenceTransitionModel V2.
- Recommendation ranking now relies on projected goal progress from the learned digital twin path.

## Model Versions

- V1: Flat transition model trained from the synthetic transition dataset.
- V2: Sequence-aware transition model using action-history and state context features.

## Dataset Sizes

- training_data.json: 111 dataset records.
- sequence_training_data.json: 111 sequence records.

## Metrics

- V1 MAE: 0.42924314182194623
- V1 MSE: 1.5222462944557205
- V1 R²: 0.9327100705217088
- V2 MAE: 0.4460857487922706
- V2 MSE: 1.2646131025406138
- V2 R²: 0.939589247505658

## Known Issues

- Exact action vocabulary alignment is still lightweight and could be improved for stronger sequence generalization.
- Missing model artifacts should raise a clear ModelNotFoundError and fall back safely to the rule-engine path.
- Registry entries are now auto-logged from training scripts, but continued versioning discipline is required for future retraining cycles.
