import unittest

from backend.models.simulated_state import SimulatedState
from backend.models.user_state import UserState
from backend.services.simulation_engine import SimulationEngine
from backend.services.snapshot_validation import SnapshotValidationError, validate_snapshot_chain, validate_state_diff
from backend.services.state_diff import calculate_state_diff


class SimulatedStateTests(unittest.TestCase):
    def test_user_state_clone_creates_independent_copy(self):
        real = UserState(
            skills={"python": 60},
            knowledge={"ai": 40},
            projects={"demo": 1},
            goals={"learn": 50},
            learning={"focus": 20},
        )

        simulated = real.clone(simulation_id="sim-001", step=1, snapshot_id="snap-001")

        self.assertIsInstance(simulated, SimulatedState)
        self.assertEqual(real.skills["python"], 60)
        self.assertEqual(simulated.skills["python"], 60)

        simulated.skills["python"] = 80

        self.assertEqual(real.skills["python"], 60)
        self.assertEqual(simulated.skills["python"], 80)

    def test_clone_records_simulation_metadata(self):
        real = UserState(
            skills={"python": 50},
            knowledge={},
            projects={},
            goals={},
            learning={},
        )

        simulated = real.clone(simulation_id="sim-002", step=3, metadata={"scenario": "risk"}, snapshot_id="snap-002")

        self.assertEqual(simulated.simulation_id, "sim-002")
        self.assertEqual(simulated.step, 3)
        self.assertEqual(simulated.metadata["scenario"], "risk")
        self.assertEqual(simulated.source_state_id, None)
        self.assertEqual(simulated.snapshot_id, "snap-002")

    def test_branch_and_advance_create_independent_snapshots(self):
        base = UserState(
            skills={"python": 50},
            knowledge={"ai": 10},
            projects={},
            goals={},
            learning={},
        ).clone(simulation_id="sim-003", step=0, snapshot_id="snap-base")

        branch_a = base.branch(simulation_id="sim-003", step=1, metadata={"branch": "a"})
        branch_b = base.branch(simulation_id="sim-003", step=1, metadata={"branch": "b"})

        branch_a.skills["python"] = 70
        branch_b.skills["python"] = 80

        self.assertEqual(base.skills["python"], 50)
        self.assertEqual(branch_a.skills["python"], 70)
        self.assertEqual(branch_b.skills["python"], 80)
        self.assertEqual(branch_a.parent_snapshot_id, "snap-base")
        self.assertEqual(branch_b.parent_snapshot_id, "snap-base")
        self.assertIsNone(branch_a.snapshot_id)
        self.assertIsNone(branch_b.snapshot_id)

        advanced = branch_a.advance(step=2, metadata={"status": "expanded"})
        self.assertEqual(advanced.step, 2)
        self.assertEqual(advanced.parent_snapshot_id, None)
        self.assertEqual(advanced.metadata["status"], "expanded")
        self.assertEqual(advanced.skills["python"], 70)

    def test_calculate_state_diff_for_snapshots(self):
        before = UserState(
            skills={"python": 50},
            knowledge={"ai": 30},
            projects={},
            goals={},
            learning={"focus": 40},
        )
        after = UserState(
            skills={"python": 65},
            knowledge={"ai": 35},
            projects={},
            goals={},
            learning={"focus": 32},
        )

        diff = calculate_state_diff(before, after)

        self.assertEqual(diff["skills"]["python"], 15)
        self.assertEqual(diff["knowledge"]["ai"], 5)
        self.assertEqual(diff["learning"]["focus"], -8)

    def test_snapshot_validation_prevents_invalid_lineage_and_steps(self):
        parent = UserState(skills={"python": 50}, knowledge={}, projects={}, goals={}, learning={}).clone(
            simulation_id="sim-004",
            step=1,
            snapshot_id="parent-snap",
        )
        child = parent.branch(simulation_id="sim-004", step=2, metadata={"branch": "child"})

        validate_snapshot_chain(child, parent_snapshot=parent)

        invalid_child = parent.branch(simulation_id="sim-004", step=0, metadata={"branch": "invalid"})
        invalid_child.parent_snapshot_id = "missing-parent"

        with self.assertRaises(SnapshotValidationError):
            validate_snapshot_chain(invalid_child, parent_snapshot=parent)

    def test_simulation_engine_can_build_snapshot_result(self):
        engine = SimulationEngine()
        initial = UserState(skills={"python": 50}, knowledge={}, projects={}, goals={}, learning={}).clone(
            simulation_id="sim-005",
            step=0,
            snapshot_id="initial-snap",
        )

        result = engine.simulate_snapshot_action(initial, "Complete Python Project")

        self.assertIsInstance(result["next_snapshot"], SimulatedState)
        self.assertIn("diff", result)
        self.assertEqual(result["next_snapshot"].parent_snapshot_id, initial.snapshot_id)
        self.assertEqual(result["next_snapshot"].simulation_id, initial.simulation_id)
        validate_state_diff(initial, result["next_snapshot"], result["diff"])

    def test_apply_action_creates_child_snapshot_without_mutating_original(self):
        engine = SimulationEngine()
        real_state = UserState(skills={"python": 50}, knowledge={"ai": 20}, projects={}, goals={}, learning={"focus": 30})
        snapshot = real_state.clone(simulation_id="sim-006", step=2, snapshot_id="snap-006")
        snapshot.skills["python"] = 50

        result = engine.apply_action(snapshot, "Complete Python Project", context={"source": "unit-test"})

        self.assertEqual(result["previous_snapshot"].skills["python"], 50)
        self.assertEqual(result["next_snapshot"].skills["python"], 57)
        self.assertEqual(result["next_snapshot"].parent_snapshot_id, snapshot.snapshot_id)
        self.assertEqual(result["next_snapshot"].step, snapshot.step + 1)
        self.assertEqual(result["next_snapshot"].simulation_id, snapshot.simulation_id)
        self.assertEqual(result["action"], "Complete Python Project")
        self.assertEqual(result["next_snapshot"].metadata["action"], "Complete Python Project")
        self.assertEqual(result["diff"]["skills"]["python"], 7)
        self.assertEqual(snapshot.skills["python"], 50)
        self.assertEqual(real_state.skills["python"], 50)
        self.assertEqual(result["next_snapshot"].knowledge["ai"], 20)

    def test_apply_action_rejects_invalid_actions(self):
        engine = SimulationEngine()
        snapshot = UserState(skills={"python": 50}, knowledge={}, projects={}, goals={}, learning={}).clone(
            simulation_id="sim-007",
            step=1,
            snapshot_id="snap-007",
        )

        with self.assertRaises(ValueError):
            engine.apply_action(snapshot, "   ")

    def test_simulate_sequence_applies_actions_in_order_and_stops_on_error(self):
        engine = SimulationEngine()
        initial = UserState(skills={"python": 40}, knowledge={"ai": 10}, projects={}, goals={}, learning={}).clone(
            simulation_id="sim-010",
            step=0,
            snapshot_id="snap-010",
        )

        # define two valid actions and one invalid to cause a stop
        actions = ["Complete Python Exercise", "Complete Python Project", "   "]

        result = engine.simulate_sequence(initial, actions, context={"test": "seq"})

        # first two should succeed, third should cause early stop
        self.assertTrue(result["stopped_early"])
        self.assertEqual(len(result["steps"]), 3)
        # first step produced a next snapshot with incremented step
        first_step = result["steps"][0]
        self.assertEqual(first_step["previous_snapshot"].step, 0)
        self.assertEqual(first_step["next_snapshot"].step, 1)
        # ensure lineage preserved through steps
        self.assertEqual(first_step["next_snapshot"].parent_snapshot_id, initial.snapshot_id)
        # the final step should contain an error for the invalid action
        last = result["steps"][-1]
        self.assertIn("error", last)
