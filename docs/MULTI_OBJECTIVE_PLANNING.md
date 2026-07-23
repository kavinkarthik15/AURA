# Multi-Objective Planning

## Objectives
AURA now evaluates plans across multiple objectives instead of relying on a single score.

- goal_progress
- python_growth
- ml_growth
- dsa_growth
- project_growth
- time_cost
- difficulty
- confidence
- energy_cost

## Pareto Optimization
The Pareto optimizer keeps non-dominated plans so that trade-offs remain visible.

## Evaluation Flow
1. Beam search generates candidate plans.
2. The multi-objective evaluator scores each plan across several dimensions.
3. The Pareto optimizer removes dominated plans.
4. The recommendation layer explains the chosen plan and its alternatives.

## Recommendation Examples
A user can now see:
- the best trade-off plan
- the Pareto front of alternatives
- the trade-offs that influenced the recommendation

## Future Enhancements
- Add richer weightings for user preferences.
- Support soft constraints such as daily energy limits.
- Expand the objective set for career-specific planning.
