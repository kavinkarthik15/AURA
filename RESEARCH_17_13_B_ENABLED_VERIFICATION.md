# RESEARCH_17_13_B_ENABLED_VERIFICATION

## Objective

Verify whether the actual 17.13B enabled implementation reproduces the validated 17.12A MG behavior under the exact benchmark, seed set, and mapping controls without modifying coefficients or simulation semantics.

## Seeds

42, 123, 456, 789, 999

## Strict acceptance criteria

For each seed, the enabled run must satisfy all of the following:

1. MG actually activates when enabled.
2. Legacy remains unchanged as the comparison baseline.
3. Simulation semantics remain unchanged.
4. The exact MG mapping from 17.11A / 17.12A is used.
5. No coefficient tuning occurs.
6. No fallback occurs during a valid MG run.
7. 17.13B outputs reproduce 17.12A within the established tolerance.
8. Prediction source is correctly reported as MG.
9. No simulation-state mutation occurs.
10. The artifact contains enough per-seed evidence for independent review.

The comparison uses:

- delta_mae = MAE_17.13B_MG - MAE_17.12A_MG
- delta_rmse = RMSE_17.13B_MG - RMSE_17.12A_MG
- delta_r2 = R²_17.13B_MG - R²_17.12A_MG
- delta_improvement_pct = improvement_pct_17.13B_MG - improvement_pct_17.12A_MG

The established tolerance from 17.12A is ±5 percentage points for improvement agreement.

## Decision rule

- A. Reproduces validated behavior → PASS → proceed to 17.13C.
- B. MG improves Legacy but does not reproduce 17.12A → FAIL → investigate integration discrepancy.
- C. MG does not improve or falls back → FAIL → stop and diagnose.

## Current result

The enabled implementation does not reproduce the validated 17.12A behavior. The run fails on all five seeds because the real integration path activates MG but leaves goals_signal at 0.0, which prevents the exact mapping from being applied. This is a production integration discrepancy, not a coefficient-tuning problem.

Artifact:

- [backend/experiments/research_17_13_b_enabled_verification.json](backend/experiments/research_17_13_b_enabled_verification.json)
- [backend/experiments/test_mg_enabled_verification_17_13_b.py](backend/experiments/test_mg_enabled_verification_17_13_b.py)
