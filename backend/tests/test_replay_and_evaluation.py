import unittest
from datetime import datetime

from backend.models.experience import Experience
from backend.services.evaluation_service import EvaluationService
from backend.services.experience_replay import ExperienceReplayService
from backend.services.state_diff import calculate_state_diff


class ReplayAndEvaluationTests(unittest.TestCase):
    def test_replay_and_evaluation_helpers(self) -> None:
        experiences = [
            Experience(
                experience_id="exp_0001",
                timestamp=datetime.utcnow(),
                user_id="user_001",
                experience_type="project",
                state_before={"python": 60},
                action="Complete Python Project",
                context={"hours_spent": 15},
                state_after={"python": 70},
                state_delta={"python": 10},
                outcome_value=0.8,
            )
        ]

        replay = ExperienceReplayService(experiences)
        self.assertEqual(len(replay.get_similar_experiences("python")), 1)
        self.assertEqual(len(replay.get_successful_experiences()), 1)
        self.assertEqual(len(replay.get_failed_experiences()), 0)
        self.assertEqual(len(replay.get_recent_experiences(days=30)), 1)

        evaluation = EvaluationService(experiences)
        self.assertEqual(evaluation.prediction_error(10, 8), 2)
        self.assertEqual(evaluation.success_prediction_accuracy(0.8, 0.8), 1)
        self.assertEqual(evaluation.state_prediction_accuracy({"python": 70}, {"python": 70}), 1)

        diff = calculate_state_diff({"python": 60}, {"python": 75})
        self.assertEqual(diff["python"], 15)


if __name__ == "__main__":
    unittest.main()
