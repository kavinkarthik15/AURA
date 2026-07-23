import json
import unittest
from pathlib import Path

from backend.ai.sequence_dataset import SequenceDatasetBuilder
from backend.models.goal_state import GoalState
from backend.services.digital_twin import LearnedDigitalTwin
from backend.services.plan_evaluator import PlanEvaluator
from backend.services.recommendation_engine import RecommendationEngine


class TrackingSequenceModel:
    def __init__(self) -> None:
        self.calls = []

    def predict(self, current_state, history, action):
        self.calls.append((dict(current_state), list(history), action))
        return {
            "python_growth": 3.0,
            "machine_learning_growth": 0.5,
            "dsa_growth": 1.0,
            "project_growth": 2.0,
        }


class SequenceModelRuntimeTests(unittest.TestCase):
    def test_recommend_plan_reaches_sequence_model_predict(self) -> None:
        fake_model = TrackingSequenceModel()
        twin = LearnedDigitalTwin(sequence_model=fake_model)
        evaluator = PlanEvaluator(digital_twin=twin)
        engine = RecommendationEngine(plan_evaluator=evaluator)

        current_state = {"python": 50, "dsa": 20, "projects": 10}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})
        plans = [
            {"name": "Plan A", "actions": ["Python Project", "DSA Practice", "Hackathon"]},
        ]

        recommendation = engine.recommend_plan(current_state, goal_state, plans)

        self.assertIsNotNone(recommendation)
        self.assertGreater(recommendation["goal_progress"], 0)
        self.assertGreater(len(fake_model.calls), 0)
        self.assertIn("reasoning", recommendation)
        self.assertIn("action_contributions", recommendation["reasoning"])
        self.assertGreaterEqual(len(recommendation["reasoning"]["action_contributions"]), 1)

    def test_multi_step_history_features_change_after_each_step(self) -> None:
        builder = SequenceDatasetBuilder()
        transitions = [
            {
                "action": "Python Project",
                "state_before": {"python": 50, "dsa": 20},
                "state_after": {"python": 60, "dsa": 20},
            },
            {
                "action": "DSA Practice",
                "state_before": {"python": 60, "dsa": 20},
                "state_after": {"python": 60, "dsa": 27},
            },
            {
                "action": "Hackathon",
                "state_before": {"python": 60, "dsa": 27},
                "state_after": {"python": 68, "dsa": 30},
            },
        ]

        samples = builder._build_sequences_from_transitions(transitions)
        self.assertEqual(len(samples), 3)
        self.assertNotEqual(samples[1]["history_features"], samples[0]["history_features"])
        self.assertNotEqual(samples[2]["history_features"], samples[1]["history_features"])

    def test_registry_records_include_provenance_fields(self) -> None:
        registry_path = Path("backend/ai/model_registry.json")
        with registry_path.open("r", encoding="utf-8") as handle:
            records = json.load(handle)

        self.assertTrue(records)
        for record in records:
            self.assertIn("model_version", record)
            self.assertIn("dataset_version", record)
            self.assertIn("training_data_hash", record)
            self.assertIn("dataset_size", record)
            self.assertIn("mae", record)
            self.assertIn("mse", record)
            self.assertIn("r2", record)
            self.assertTrue(record["training_data_hash"])
            self.assertEqual(record["dataset_version"], "v1")
            self.assertGreater(record["dataset_size"], 0)


if __name__ == "__main__":
    unittest.main()
