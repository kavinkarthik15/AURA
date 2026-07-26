# Frozen Interfaces v1.0

The following interfaces are treated as stable extension points for Sprint 11 and beyond:

- GoalService: planning entry point for goal-driven recommendations.
- BeamSearchPlanner: core search and reasoning orchestration entry point.
- ExperienceRetriever: retrieval signal provider for planning.
- PlanningPolicy: policy-based next-action scoring.
- Reasoner: explanation and reasoning synthesis interface.
- ExecutionEngine: plan execution orchestration.
- ExperienceLogger: experience capture and storage.
- ContinualLearner: experience-driven learning and model update pipeline.

Future work should extend these interfaces rather than replacing them.
