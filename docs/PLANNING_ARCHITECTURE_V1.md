# Planning Architecture V1

## Flow

Goal
 ↓
Beam Search Planner
 ↓
Digital Twin
 ↓
Evaluation
 ↓
Recommendation

## Components

- Beam Search Planner: explores a wider plan space, expands candidate states, prunes weak paths, and keeps the best beam of plans.
- Digital Twin: simulates each plan over time using the learned transition model when available.
- Evaluation: scores candidate plans based on projected goal progress and confidence.
- Recommendation: selects the strongest plan and returns explainability data.

## Output

The planning service returns:

- recommended_plan
- goal_progress
- confidence
- reasoning
- candidate_plans
- candidate_evaluations
- metrics
- search_metrics
- search_trace
