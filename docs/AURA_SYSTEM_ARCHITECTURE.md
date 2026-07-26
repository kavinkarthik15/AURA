# AURA System Architecture

## Overview
AURA is an adaptive planning and continual learning platform built around a control loop that plans, executes, observes outcomes, and updates models. It combines beam search planning, retrieval-augmented evidence, policy guidance, reasoning, and meta-reflection.

## Module Hierarchy
- `GoalService`
- `BeamSearchPlanner`
- `ExperienceRetriever`
- `PlanningPolicy`
- `ExperienceReasoner`
- `CounterfactualPlanner`
- `ExecutionEngine`
- `ExperienceLogger`
- `ContinualLearningPipeline`
- `PolicyRegistry`
- `ResearchRegistry`
- `SystemRegistry`
- `ReflectionRegistry`

## Data Flow
1. Goal intake is received by the Goal Service.
2. The planner generates candidate action sequences using beam search.
3. Policy and retrieval signals contribute action rankings.
4. The digital twin simulates candidate plan outcomes.
5. Reasoning compares candidate plans against prior experience.
6. Counterfactual alternatives are generated when needed.
7. The recommendation is selected and returned.
8. Execution outcomes are logged as experiences.
9. Experiences feed replay, training, and continual learning.
10. New candidates are benchmarked, deployed, and registered.

## Planning Cycle
Beam search evaluates state transitions, goal progress, and confidence. Policy guidance and retrieval evidence enrich the search ranking without replacing core search. The planner exposes metadata for explainability and downstream reflection.

## Reasoning and Reflection
The reasoning layer generates explanations, consistency checks, and evidence summaries. Meta-reasoning reflects on the planner decision, evidence sufficiency, assumptions, and subsystem quality to decide whether to accept, replan, reject, or request more information.

## Continual Learning
The continual learning pipeline converts execution data into training datasets, trains candidate models, benchmarks them, and gates deployment using registry-backed acceptance criteria.

## Registries
AURA tracks versioned state through:
- System registry: active subsystem versions.
- Policy registry: policy versions, benchmark results, and deployment decisions.
- Reasoning registry: reasoning version history and benchmark metadata.
- Reflection registry: reflection version, thresholds, metrics, and release metadata.
- Research registry: experiment lineage and dataset/version relationships.

## Research Properties
AURA measures behavior using policy entropy, planner confidence, evidence coverage, retrieval metrics, benchmark results, and reflection outcomes. These metrics enable systematic evaluation and versioned comparison.

## Architecture Goals
- Support reproducible planning and learning experiments.
- Make reasoning and reflection decisions visible and auditable.
- Maintain versioned registry records for models, policies, and reflection logic.
- Preserve ADRs for architectural intent and historical decisions.
