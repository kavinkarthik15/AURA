# ADR-001: Why Beam Search?

## Status
Accepted

## Context
The planning stack needs to explore many possible action sequences while remaining computationally tractable. A full search over all possible plans grows quickly and becomes impractical for long horizons.

## Decision
Use beam search as the core planning strategy. Beam search keeps the best-scoring partial plans at each depth and expands them forward, providing a balance between search completeness and runtime efficiency.

## Consequences
- Pros: efficient exploration, easy integration with policy and retrieval signals, and clear explainability for why a plan was selected.
- Cons: beam search is approximate and can miss globally optimal sequences if the beam is too narrow.
