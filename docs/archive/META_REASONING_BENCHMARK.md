# Meta-Reasoning Benchmark

## Goal
Evaluate whether AURA can reflect on its own reasoning before acting.

## Metrics
- Confidence calibration
- Reflection quality
- Replanning correctness
- Strategy selection
- Assumption detection

## Suggested Evaluation
1. Run the planner on a simple goal and a novel goal.
2. Compare the reflection decision to expected behavior.
3. Check whether the strategy selector chooses a richer pipeline for uncertain cases.
4. Review whether assumptions are surfaced and critiques trigger replanning when needed.
