# 17.10A — Compatibility Layer

## Objective

Create a compatibility layer that wraps the legacy prediction output without modifying the existing SimulationEngine or production calibration behavior. The layer must be explicitly disabled by default and preserve exact legacy output when `enabled=False`.

## Safety invariant

- Disabled compatibility layer => exact identity with legacy prediction path
- No SimulationEngine mutation
- No calibration-equation mutation
- New layer is an integration boundary only

## Configuration contract

```python
CompatibilityConfig(
    enabled=False,
    use_motivation=False,
    use_goals=False,
    use_behavior=False,
)
```

The first gate is strictly:

```python
enabled = False
```

When this is false, the compatibility layer returns the original prediction object unchanged.

## Validation structure

The experiment validates:

- predicted future state
- prediction vectors
- MAE
- RMSE
- R²
- objective value
- target values
- benchmark split
- deterministic output
- simulation semantics

For every seeded output, the compatibility-disabled path must match the legacy path exactly.

## Execution

1. Unit tests via pytest
2. Seed 42 gate
3. Seeds 42, 123, 456, 789, 999
4. Artifact generation
5. Final decision gate

## Decision outcomes

- PASS: disabled compatibility path is behaviorally equivalent to legacy output
- FAIL: disabled path changes simulation behavior, blocking production activation

## Implementation principle

The compatibility layer wraps the current prediction output rather than regenerating or altering the simulation. This ensures 17.9 remains intact and 17.10A remains a safe integration boundary.
