# Coding Guidelines

## Core Principles

- Extend existing modules whenever practical rather than creating parallel implementations.
- Avoid creating new variants such as *_v2.py, *_v3.py, or duplicate capability modules unless explicitly justified.
- New memory operations must go through MemoryManager.
- Every new capability should include tests and documentation.
- Public APIs should remain backward compatible where possible.
- Prefer clear interfaces over ad hoc coupling.

## Architecture Rules

- Planner, reasoner, and meta-reasoner components should interact through stable interfaces.
- Storage details should remain hidden behind the memory orchestration layer.
- New features should be introduced behind existing abstractions where possible.

## Quality Bar

- Keep modules focused and readable.
- Add or update tests for behavioral changes.
- Document new interfaces and integration points.
