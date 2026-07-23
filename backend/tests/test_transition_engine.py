import unittest

from backend.services.transition_engine import TransitionEngine


class TransitionEngineTests(unittest.TestCase):
    def test_predicts_growth_and_success_probability(self) -> None:
        experiences = [
            type(
                "Experience",
                (),
                {
                    "action": "Build Python Project",
                    "state_before": {"python": 40},
                    "state_delta": {"python": 10},
                    "outcome_value": 0.9,
                },
            )(),
            type(
                "Experience",
                (),
                {
                    "action": "Build Python Project",
                    "state_before": {"python": 45},
                    "state_delta": {"python": 12},
                    "outcome_value": 0.8,
                },
            )(),
            type(
                "Experience",
                (),
                {
                    "action": "Build Python Project",
                    "state_before": {"python": 50},
                    "state_delta": {"python": 11},
                    "outcome_value": 0.85,
                },
            )(),
        ]

        engine = TransitionEngine(experiences=experiences)
        predicted_growth = engine.predict_skill_growth({"python": 48}, "Build Python Project")
        success_probability = engine.predict_success_probability({"python": 48}, "Build Python Project")

        self.assertEqual(predicted_growth["python"], 11)
        self.assertAlmostEqual(success_probability, 0.85)

    def test_generalizes_for_unseen_action_family(self) -> None:
        experiences = [
            type(
                "Experience",
                (),
                {
                    "action": "Build Python Project",
                    "state_before": {"python": 40},
                    "state_delta": {"python": 10},
                    "outcome_value": 0.9,
                },
            )(),
        ]

        engine = TransitionEngine(experiences=experiences)
        predicted_growth = engine.predict_skill_growth({"python": 48}, "Build AI Stock Predictor")
        success_probability = engine.predict_success_probability({"python": 48}, "Build AI Stock Predictor")

        self.assertGreater(predicted_growth["python"], 0)
        self.assertGreater(success_probability, 0)


if __name__ == "__main__":
    unittest.main()
