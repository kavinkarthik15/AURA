# Meta-Reasoning Benchmark v1

## Purpose
Provide a reference benchmark for the Reflection Loop and meta-reasoning layer in AURA.

## Key Evaluation Categories
- reflection accuracy
- replanning correctness
- confidence calibration
- assumption detection quality
- self-critique validity
- strategy selection accuracy

## Metrics
- reflection_accuracy: agreement between reflection decision and expected outcome
- replanning_correctness: correct replan decisions when evidence is weak or contradictory
- confidence_calibration: probability calibration between confidence estimates and actual success
- assumption_detection_recall: completeness of surfaced assumptions
- assumption_detection_precision: correctness of surfaced assumptions
- self_critique_quality: how well self-critique identifies subsystem issues
- strategy_selection_accuracy: appropriate selection of reasoning strategy

## Evaluation Guideline
1. Execute planner and reflection loop on goals with varying uncertainty.
2. Annotate expected reflection decisions and verify acceptance/rejection behavior.
3. Judge whether the selected strategy matches goal complexity, evidence sufficiency, and contradictions.
4. Track self-critique signals for retrieval, reasoning, counterfactual, and policy quality.
5. Validate calibration by comparing confidence levels to actual execution outcomes.

## Expected Outcomes
- high confidence + strong evidence => accept
- weak evidence => replan
- contradictory evidence => reject
- missing assumptions => request more information
- successful execution after reflection => reinforce strategy
