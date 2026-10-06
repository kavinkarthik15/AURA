# 17.8A — Predictive State Dimension Analysis

## Objective

This phase remains observational. It asks a more fundamental question than calibrator tuning:

> Which existing AURA state dimensions actually contain predictive information about future outcome change?

The goal is to identify whether the current state representation is rich enough to support a meaningful predictive calibration problem.

## Method

For each candidate dimension from the current AURA model and benchmark metadata:

- skills
- knowledge
- projects
- goals
- learning
- motivation
- confidence
- behavior

we measure:

1. variation across experiences
2. standalone predictive value against the future-state target
3. conditional predictive value when interacting with the action/context state
4. change in MAE / RMSE / R² relative to the current skill-only baseline

The baseline model is the current skill vector alone:

- python
- dsa
- machine_learning
- projects

The augmented model adds one candidate dimension at a time and evaluates the incremental explanatory power.

## Interpretation rule

- strong: clear direct or conditional predictive gain
- moderate: some signal but not decisive
- weak: minimal predictive value
- inactive: near-zero variability or no predictive contribution

## Expected conclusion

Under the current benchmark, the raw skill vector is the only state signal with clear predictive value. The other AURA dimensions are either:

- derived from the same skill signal,
- weakly varying across experiences,
- action-conditional rather than state-structured,
- or not present in the benchmark state representation at all.

That means the important next question is not how to tune calibration parameters, but whether the state representation encodes enough information for the future-state target to be learnable in the first place.

## Scope restriction

This analysis is deliberately observational and does not modify:

- SignAwareCalibrator
- CalibrationParameters
- SimulationEngine
- prediction equations
- production state model

The purpose is to identify which dimensions are genuinely informative before proposing a redesign.
