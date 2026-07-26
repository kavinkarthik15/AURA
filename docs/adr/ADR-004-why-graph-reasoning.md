# ADR-004: Why Graph Reasoning?

## Status
Accepted

## Context
Linear traces capture a single chain of reasoning, but future research requires a structure that can connect multiple evidence pieces, inferred patterns, and candidate actions.

## Decision
Represent reasoning as a graph of evidence nodes, inferred pattern nodes, and action nodes. This supports richer analysis, multi-hop reasoning, and future research into causal structure.

## Consequences
- Pros: flexible structure, better support for multi-step inference, and clearer visualization of reasoning dependencies.
- Cons: slightly more complex than a simple trace and requires additional tooling for visualization and analysis.
