import unittest

from backend.services.simulation_engine import SimulationEngine, simulation_engine
from backend.models.simulated_state import SimulatedState


class SimulationTrajectoryTests(unittest.TestCase):
    def test_empty_action_sequence_returns_initial_snapshot(self):
        engine = SimulationEngine()
        init = engine.make_snapshot({"python": 5}, simulation_id="sim-1", step=0, snapshot_id="S0")
        traj = engine.simulate_trajectory(init, [])

        self.assertEqual(traj.initial_snapshot.snapshot_id, "S0")
        self.assertEqual(traj.snapshots, [])
        self.assertEqual(traj.actions, [])
        self.assertEqual(traj.final_snapshot.snapshot_id, "S0")

    def test_sequential_actions_produce_ordered_snapshots_and_diffs(self):
        engine = SimulationEngine()
        init = engine.make_snapshot({"python": 1}, simulation_id="sim-2", step=0, snapshot_id="ROOT")
        actions = ["practice python", "complete project", "read docs"]
        traj = engine.simulate_trajectory(init, actions)

        self.assertEqual(traj.initial_snapshot.snapshot_id, "ROOT")
        self.assertEqual(traj.actions, actions)
        self.assertEqual(len(traj.snapshots), 3)
        # parent linkage
        for i in range(1, len(traj.snapshots)):
            self.assertEqual(traj.snapshots[i].parent_snapshot_id, traj.snapshots[i - 1].snapshot_id)
        self.assertEqual(traj.final_snapshot, traj.snapshots[-1])

    def test_original_state_untouched_and_snapshots_mutable(self):
        engine = SimulationEngine()
        init = engine.make_snapshot({"python": 2}, simulation_id="sim-3", step=0, snapshot_id="R0")
        actions = ["practice python"]
        traj = engine.simulate_trajectory(init, actions)

        # original state unchanged
        self.assertEqual(init.skills.get("python"), 2)
        # snapshot is independent mutable
        traj.snapshots[0].skills["python"] = 999
        self.assertNotEqual(init.skills.get("python"), traj.snapshots[0].skills.get("python"))


if __name__ == "__main__":
    unittest.main()
