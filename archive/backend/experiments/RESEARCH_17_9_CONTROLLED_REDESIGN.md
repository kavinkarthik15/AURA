# 17.9 Controlled Redesign Experiment

## Objective

Test whether introducing the predictive state dimensions identified in 17.8A-17.8C
causes measurable improvement on the same benchmark objective while controlling
for benchmark data, target outcomes, calibration settings, and simulation semantics.

## Models under test

Primary hypotheses:

- baseline: expected_state_bias-only correction
- motivation_goals: expected_state_bias + motivation + goals
- all_three: expected_state_bias + motivation + goals + behavior

Ablation matrix:

- baseline, M, G, B, MG, MB, GB, MGB

## Controls (no confounding)

The experiment keeps fixed across comparisons:

- same seed and benchmark split
- same initial states and actions
- same target actual outcomes
- same simulation engine and calibration defaults
- same evaluation objective

Only the representation->prediction correction mapping changes.

## Measurements

Per seed and model:

- MAE, RMSE, R2
- delta MAE/RMSE/R2 vs baseline
- prediction delta vs baseline
- causal intervention effects for motivation/goals/behavior

Per seed gates:

- Gate 1: causal activation (added dimensions alter predictions)
- Gate 2: objective improvement over baseline
- Gate 4A: MG improves beyond singletons M and G
- Gate 4B: MGB improves beyond MG

Cross-seed gate:

- Gate 3: reproducibility of objective improvement across seeds

## Output artifact

- backend/experiments/results/research_17_9_controlled_redesign.json

## Scope restriction

This remains observational and experimental only.
No production architecture files are modified.
