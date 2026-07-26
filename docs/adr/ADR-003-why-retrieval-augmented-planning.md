# ADR-003: Why Retrieval-Augmented Planning?

## Status
Accepted

## Context
Planning quality improves when the system can reuse similar past experiences rather than relying only on current state and policy priors. Direct reuse of prior trajectories can provide useful context for new goals.

## Decision
Integrate retrieval-augmented planning so the planner can retrieve similar experiences and incorporate their signals into scoring and explanation.

## Consequences
- Pros: stronger grounding in real outcomes, better explainability, and improved adaptation to familiar scenarios.
- Cons: retrieval quality depends on indexing quality and must be monitored for stale or irrelevant matches.
