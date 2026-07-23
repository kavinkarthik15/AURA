import unittest

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

    def test_simulate_plan_returns_sequence_and_summary(self) -> None:
        engine = SimulationEngine()
        result = engine.simulate_plan({"python": 50}, ["Complete Python Project", "Complete DSA Course"])
        self.assertIn("steps", result)
        self.assertGreaterEqual(len(result["steps"]), 2)
        self.assertIn("success_probability", result)
        self.assertIn("predicted_future_state", result)
        self.assertIn("expected_outcome", result)
        self.assertGreaterEqual(result["success_probability"], 0.0)


if __name__ == "__main__":
    unittest.main()
