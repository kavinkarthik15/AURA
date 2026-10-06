# 17.8C — Minimal State/Parameter Structure Analysis

## Objective

Determine the smallest observational state->parameter->prediction structure that can represent predictive information from 17.8A, without modifying production architecture.

## Scope

- Experimental only (`backend/experiments/`)
- No production changes to:
  - CalibrationParameters
  - simulation_engine
  - calibrators
  - production state representation

## Candidate structures

The experiment evaluates a baseline and minimal candidate families:

- Current baseline (`current_bias_only`):
  - intercept only (1 parameter)
  - interpreted as `expected_state_bias` aggregate offset

- Candidate A (dimension-specific biases):
  - `+ motivation`
  - `+ goals`
  - `+ behavior`
  - pairwise combinations
  - all three dimensions

- Candidate B (state-conditioned aggregate):
  - single `aggregate_signal` feature

- Candidate C (minimal linear representation):
  - `beta_0 + beta_1 motivation + beta_2 goals + beta_3 behavior`

## Measurements

For each candidate and each seed:

- parameter count
- held-out MAE, RMSE, R2
- delta MAE / delta RMSE / delta R2 vs baseline
- identifiability indicators:
  - matrix rank
  - condition number
  - full-rank check
  - null-space dimension

## Gates

1. Expressiveness: at least one candidate improves over baseline.
2. Incremental information: improvement beyond baseline is non-trivial.
3. Identifiability: added parameters have distinguishable effects.
4. Minimality: choose the smallest parameterization among sufficient candidates.
5. No production modification.

## Output artifact

Results are written to:

- `backend/experiments/results/research_17_8_c_minimal_structure.json`
