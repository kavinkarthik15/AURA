# AURA Documentation

## 1. Introduction
AURA is a goal-driven planning, reasoning, and continual learning platform that helps users make progress on skill-building objectives by selecting actions, explaining decisions, and learning from outcomes.

## 2. Motivation
AURA is designed to reduce uncertainty in decisions by combining search-based planning with experience-driven guidance, digital twin simulation, and reflection-based correction.

## 3. Research Problem
AURA addresses the challenge of adaptive decision-making under sparse and noisy experience: how to plan effectively, explain choices, learn from execution, and reflect on reasoning quality.

## 4. System Overview
The system includes planning, retrieval, policy learning, reasoning, execution logging, continual learning, and registries for versioned experiment state.

## 5. Overall Architecture
AURA is centered on a loop of:
- goal intake
- beam search planning
- retrieval and policy guidance
- reasoning and counterfactual evaluation
- recommendation generation
- execution and experience logging
- continual learning and registry updates

## 6. Project Structure
Key folders:
- `backend/ai` — AI models, reasoning, reflection, registries, and benchmarks.
- `backend/services` — orchestration, planner, recommendation, and estimator logic.
- `backend/models` — domain models such as `GoalState` and search results.
- `backend/tests` — regression tests for planners, reasoning, and integration.
- `docs` — consolidated documentation, architecture, and benchmarks.

## 7. User State Model
AURA models user state as numeric skill dimensions and progress indicators. The planner and retriever use this state to estimate goal progress and select actions.

## 8. Goal Management
Goals are expressed as target skills and target states. The goal manager normalizes descriptions and exposes them to planning and policy modules for scoring.

## 9. Experience System
AURA logs execution experiences including actions, outcomes, state transitions, and success signals. Past experience is used by retrieval, policy training, and reasoning.

## 10. Digital Twin
The digital twin simulates candidate plans and predicts state transitions without real execution. Digital twin output contributes to planner confidence and post-hoc explanation.

## 11. Planning
Beam search explores candidate sequences and ranks them using state score, policy guidance, retrieval evidence, and confidence signals.

## 12. Policy Learning
The planning policy learns action preferences from execution data. It provides probabilities, entropy, and support-based confidence to augment search ranking.

## 13. Continual Learning
The continual learning pipeline builds training datasets from replayed experiences, trains candidate models, benchmarks them, and gates deployment through registry-backed acceptance.

## 14. Retrieval
Retrieval finds similar historical experiences using hybrid similarity metrics. Retrieved episodes support planning, explanation, and experience-based reasoning.

## 15. Reasoning
The reasoning layer compares candidate plans to retrieved experiences, generates explanations, checks evidence consistency, and surfaces counterfactual alternatives.

## 16. Meta-Reasoning
Meta-reasoning reflects on planning decisions, evidence quality, assumptions, and subsystem health. It reports accept/replan/reject/request_more_information decisions and records contributors such as retrieval, policy, counterfactual, and reasoner.

## 17. Registries
AURA maintains registries for:
- system versions
- policy versions
- reasoning versions
- reflection versions
- research experiment lineage

## 18. Benchmarks
Benchmarks track planning, policy, retrieval, reasoning, and meta-reasoning. Versioned metrics are recorded in registries and used for deployment decisions.

## 19. Experiment Tracking
Experiments are registered with metadata including planner version, policy version, retrieval version, reasoning version, benchmark version, and dataset lineage.

## 20. Testing
Regression tests validate planning, reasoning, reflection, and registry behavior. The suite includes meta-reasoning, strategy selection, and benchmark scoring tests.

## 21. Performance
AURA records subsystem timings for beam search, policy inference, retrieval, reasoning, and execution. These metrics support optimization and benchmark review.

## 22. Current Limitations
Current limitations include sparse experience coverage, approximate calibration, and evolving reflection thresholds that require tuning.

## 23. Future Work
Future work includes more robust strategy planning, richer experience generalization, better calibration, and an integrated dashboard for reflection and benchmark observability.

## 24. References
- `docs/AURA_SYSTEM_ARCHITECTURE.md`
- `docs/architecture.md`
- `docs/frozen_interfaces.md`
- `docs/adr/ADR-001-why-beam-search.md`
- `docs/adr/ADR-002-why-empirical-policy.md`
- `docs/adr/ADR-003-why-retrieval-augmented-planning.md`
- `docs/adr/ADR-004-why-graph-reasoning.md`
- `docs/adr/ADR-005-why-continual-learning.md`
- `backend/ai/reflection_registry.py`
- `backend/services/goal_plan_service.py`
