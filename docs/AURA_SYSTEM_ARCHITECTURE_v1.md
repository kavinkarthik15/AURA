# AURA System Architecture v1.0

## Overview
AURA is a planning, reasoning, and continual-learning system for goal-driven skill development. The architecture is organized around a core control loop that plans, executes, observes outcomes, and updates learned components.

## Module Hierarchy
- GoalService
- BeamSearchPlanner
- ExperienceRetriever
- PlanningPolicy
- ExperienceReasoner
- CounterfactualPlanner
- ExecutionEngine
- ExperienceLogger
- ContinualLearningPipeline
- PolicyRegistry
- ResearchRegistry
- SystemRegistry

## Data Flow
1. Goal intake is received by GoalService.
2. State analysis and candidate planning are produced by BeamSearchPlanner with retrieval and policy signals.
3. Reasoning and counterfactual modules refine the plan.
4. Recommendation and execution follow the selected plan.
5. Execution outcomes are logged as experiences.
6. Continual learning updates the model and policy.
7. Research registries and reports capture the experiment state.

## Registries
- Model registry tracks model versions.
- Policy registry tracks accepted policy versions.
- Retrieval registry tracks retrieval experiment versions.
- Reasoning registry tracks reasoning benchmark versions.
- Research registry tracks the full experiment lineage.
- System registry tracks the active subsystem versions.

## Learning Cycle
- Collect experience from execution.
- Replay experiences into continual learning.
- Benchmark candidate updates.
- Deploy and register accepted updates.

## Reasoning Cycle
- Analyze prior experiences.
- Generate explanations and evidence.
- Check consistency and counterfactual alternatives.
- Produce reasoning metadata for the planner.

## Planning Cycle
- Score candidate actions.
- Blend policy, retrieval, and confidence signals.
- Select the best plan.
- Return reasoning metadata and benchmark data.
