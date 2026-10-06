import unittest

from backend.models.user_state import UserState
from backend.services.simulation_engine import SimulationEngine


class SimulationEngineTests(unittest.TestCase):
    def test_simulate_action_returns_structured_prediction(self) -> None:
        engine = SimulationEngine()
        result = engine.simulate_action({"python": 50}, "Complete Python Project")
        self.assertIn("current_state", result)
        self.assertIn("predicted_future_state", result)
        self.assertIn("confidence", result)
        self.assertIn("expected_outcome", result)
        self.assertGreater(result["predicted_future_state"]["python"], 50)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
        self.assertIn(result["expected_outcome"], {"Positive", "Neutral", "Negative"})

    def test_shadow_event_recorder_preserves_prediction_and_records_schema(self) -> None:
        events = []
        engine = SimulationEngine(shadow_event_recorder=events)
        result = engine.simulate_action({"python": 50}, "Complete Python Project")

        self.assertIn("current_state", result)
        self.assertEqual(len(events), 1)
        event = events[0]
        required_fields = {
            "experience_id",
            "seed",
            "category",
            "action",
            "legacy_prediction",
            "mg_shadow_prediction",
            "mg_correction",
            "motivation_signal",
            "goals_signal",
            "fallback_triggered",
            "fallback_reason",
            "legacy_latency_ms",
            "mg_latency_ms",
            "mg_error",
        }
        self.assertTrue(required_fields.issubset(set(event.keys())))
        self.assertEqual(event["action"], "Complete Python Project")
        self.assertEqual(event["legacy_prediction"], result)
        self.assertEqual(event["mg_shadow_prediction"], result)

    def test_shadow_event_recorder_failure_is_isolated(self) -> None:
        class FailRecorder:
            def record(self, event):
                raise RuntimeError("logging failure")

        engine = SimulationEngine(shadow_event_recorder=FailRecorder())
        result = engine.simulate_action({"python": 50}, "Complete Python Project")

        self.assertIn("current_state", result)
        self.assertIn("predicted_future_state", result)

    def test_shadow_event_recorder_does_not_change_legacy_behavior(self) -> None:
        engine_without_recorder = SimulationEngine()
        engine_with_recorder = SimulationEngine(shadow_event_recorder=[])

        a = engine_without_recorder.simulate_action({"python": 50}, "Complete Python Project")
        b = engine_with_recorder.simulate_action({"python": 50}, "Complete Python Project")

        self.assertEqual(a, b)

    def test_simulate_plan_returns_sequence_and_summary(self) -> None:
        engine = SimulationEngine()
        result = engine.simulate_plan({"python": 50}, ["Complete Python Project", "Complete DSA Course"])
        self.assertIn("steps", result)
        self.assertGreaterEqual(len(result["steps"]), 2)
        self.assertIn("success_probability", result)
        self.assertIn("predicted_future_state", result)
        self.assertIn("expected_outcome", result)
        self.assertGreaterEqual(result["success_probability"], 0.0)

    def test_simulate_probabilistic_action_returns_branches(self) -> None:
        engine = SimulationEngine()
        snapshot = UserState(skills={"python": 50}, knowledge={}, projects={}, goals={}, learning={}).clone(
            simulation_id="sim-prob",
            step=0,
            snapshot_id="prob-001",
        )
        result = engine.simulate_probabilistic_action(snapshot, "Complete Python Project", context={"confidence": 0.8})

        self.assertEqual(result["previous_snapshot"], snapshot)
        self.assertIn("transition", result)
        self.assertIn("branches", result)
        self.assertGreaterEqual(len(result["branches"]), 2)

        total_prob = sum(branch["probability"] for branch in result["branches"])
        self.assertAlmostEqual(total_prob, 1.0, places=4)

        for branch in result["branches"]:
            self.assertIsNot(branch["next_snapshot"], snapshot)
            self.assertEqual(branch["next_snapshot"].parent_snapshot_id, snapshot.snapshot_id)
            self.assertEqual(branch["next_snapshot"].step, snapshot.step + 1)
            self.assertIn("diff", branch)
            self.assertIn("probability", branch)
            self.assertEqual(branch["next_snapshot"].simulation_id, snapshot.simulation_id)


if __name__ == "__main__":
    unittest.main()
