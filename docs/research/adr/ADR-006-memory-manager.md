# ADR-006: Unified Memory Manager for AURA

## Status
Accepted

## Context
AURA has grown from a planning system into a reasoning platform with episodic, semantic, procedural, and reflection signals. Without a single orchestration layer, memory operations become fragmented and difficult to evolve.

## Decision
Introduce a MemoryManager as the single gateway for all memory operations. Planner, reasoner, and reflection components will interact with memory through MemoryManager rather than directly calling storage implementations.

## Consequences
- Memory operations become centralized and easier to audit.
- The system can evolve storage technology without changing planner interfaces.
- The architecture becomes more consistent with the documented memory model.
