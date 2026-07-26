# ADR-002: Why Empirical Policy?

## Status
Accepted

## Context
The planner benefits from a lightweight policy signal that can rank candidate actions using observed experience patterns. A rigid hand-coded policy would be difficult to maintain as the system grows.

## Decision
Use an empirical policy derived from historical planning outcomes and action trajectories. This provides a data-driven prior that can be updated as new behavior is observed.

## Consequences
- Pros: better adaptation, easier experimentation, and a clear path to continual improvement.
- Cons: the policy must be monitored for drift and needs sufficient training data to remain reliable.
