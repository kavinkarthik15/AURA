from __future__ import annotations

from typing import Any, Dict

from backend.models.simulated_state import SimulatedState
from backend.services.state_diff import calculate_state_diff


class SnapshotValidationError(ValueError):
    pass


def validate_snapshot_chain(snapshot: SimulatedState, *, parent_snapshot: SimulatedState | None = None) -> None:
    if snapshot.step < 0:
        raise SnapshotValidationError("Snapshot step cannot be negative")

    if parent_snapshot is not None:
        if snapshot.parent_snapshot_id is None:
            raise SnapshotValidationError("Snapshot must link to a parent snapshot")
        if snapshot.parent_snapshot_id != parent_snapshot.snapshot_id:
            raise SnapshotValidationError("Snapshot parent linkage does not match the expected parent")
        if snapshot.step <= parent_snapshot.step:
            raise SnapshotValidationError("Child snapshot step must be greater than the parent step")

    if snapshot.parent_snapshot_id is not None and snapshot.parent_snapshot_id == snapshot.snapshot_id:
        raise SnapshotValidationError("Snapshot cannot be its own parent")


def validate_state_diff(before: Any, after: Any, diff: Dict[str, Dict[str, int]]) -> None:
    expected = calculate_state_diff(before, after)
    if diff != expected:
        raise SnapshotValidationError("State diff does not match the actual snapshot change")
