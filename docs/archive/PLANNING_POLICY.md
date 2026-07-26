# Sprint 11.1: Planning Policy

## Purpose

AURA's planning policy is an optional learned layer that estimates promising next actions using execution experience. It complements the digital twin and existing beam-search state score rather than replacing them.

## Flow

Goal
↓
Planning Policy: P(action | state, goal)
↓
Policy-guided Beam Search
↓
Digital Twin
↓
Recommendation

## Components

- `backend/ai/planning_policy.py`: `PlanningPolicy`, `PolicySample`, and `PolicyPrediction`.
- `backend/ai/policy_dataset.py`: converts `ExperienceLog` records into policy samples.
- `backend/ai/policy_trainer.py`: fits and persists the empirical policy artifact.
- `backend/ai/evaluate_policy.py`: reports top-action accuracy and average predicted probability.
- `backend/ai/policy_registry.py`: records policy versions, dataset hashes, sample counts, and benchmark metrics.
- `backend/ai/policy_registry.json`: policy registry storage.

## Learning Behavior

Successful completed actions receive stronger evidence than failed or uncompleted actions. Predictions are conditioned on the goal and the numeric current-state context, with smoothed fallback scores for actions without direct evidence.

## Beam Search Integration

`BeamSearchPlanner` accepts an optional `PlanningPolicy` and `policy_weight`. Existing behavior is unchanged when no policy is supplied. When enabled, each candidate receives a policy score and beam ranking uses:

`state_score + policy_weight * policy_score`

The search result and trace expose `policy_enabled` and `policy_score` for explainability.

## Entropy and Exploration

The policy exposes normalized entropy over the candidate action distribution. High entropy returns `explore`; low entropy returns `exploit`. This signal is available for future diversity-aware search strategies.

## Planner Confidence

Policy-guided search returns planner confidence, policy entropy, and action-level explanations. Planner confidence combines beam state confidence, digital-twin/model confidence, and successful policy support.

## Drift and Coverage

`PolicyDriftDetector` compares policy distributions with KL divergence and total variation. Significant drift sets `retraining_recommended` to true. `PolicyEvaluator` reports overall coverage plus coverage by state dimension and goal.

## Lineage and Rollback

`PolicyRegistry` stores parent policy, dataset hash, sample count, acceptance, benchmark, and decision reason. `PolicyDeployment` rejects candidates that underperform the previous benchmark and restores the previous policy as the active version.

## Benchmark

Policy evaluation reports:

- sample count
- top-action accuracy
- average predicted probability

These metrics are stored in `PolicyRegistry` alongside the policy version and dataset hash.

## Scope and Next Steps

Sprint 11.1 learns action preferences. Sprint 11.2 can make policy guidance the default search mode. Sprint 11.3 should discover recurring action sequences and strategies. Sprint 11.4 can add a meta-planner that selects strategies before invoking the policy.
