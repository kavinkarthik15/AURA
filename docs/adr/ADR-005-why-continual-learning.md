# ADR-005: Why Continual Learning?

## Status
Accepted

## Context
The system should improve over time as new experiences, feedback, and evaluation results arrive. A static model would degrade in relevance and make it harder to adapt to changing goals.

## Decision
Adopt continual learning practices so explanations, policies, and reasoning heuristics can be updated from new feedback and observed outcomes.

## Consequences
- Pros: improved adaptation, better long-term performance, and stronger alignment with user feedback.
- Cons: requires careful monitoring to prevent regressions and feedback loops.
