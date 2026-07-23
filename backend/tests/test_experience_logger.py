import unittest

from backend.services.experience_logger import ExperienceLogger
from backend.services.outcome_analyzer import OutcomeAnalyzer


class ExperienceLoggerTests(unittest.TestCase):
    def test_create_experience(self) -> None:
        logger = ExperienceLogger(dataset_path=None)
        experience = logger.log_experience(
            execution_id="exec_20260723_001",
            plan_name="Placement Plan",
            goal_name="Python Growth",
            initial_state={"python": 65},
            predicted_state={"python": 75},
            actual_state={"python": 72},
            actions=["Python Project", "DSA Practice"],
            completed_actions=["Python Project"],
            failed_actions=[],
            skipped_actions=[],
            execution_time=12.5,
            success=True,
        )

        self.assertTrue(experience.experience_id)
        self.assertEqual(experience.experience_version, "v1")
        self.assertEqual(experience.model_version, "v2")
        self.assertEqual(experience.planner_version, "beam_search_v1")
        self.assertEqual(experience.objective_profile, "balanced_learning")
        self.assertEqual(experience.dataset_version, "v1")

    def test_experience_stored(self) -> None:
        logger = ExperienceLogger(dataset_path=None)
        initial_count = len(logger.list_experiences())
        logger.log_experience(
            execution_id="exec_20260723_002",
            plan_name="Placement Plan",
            goal_name="Python Growth",
            initial_state={"python": 65},
            predicted_state={"python": 78},
            actual_state={"python": 74},
            actions=["Python Project", "DSA Practice"],
            completed_actions=["Python Project"],
            failed_actions=[],
            skipped_actions=[],
            execution_time=10.0,
            success=False,
        )

        self.assertGreater(len(logger.list_experiences()), initial_count)

    def test_prediction_error(self) -> None:
        logger = ExperienceLogger(dataset_path=None)
        experience = logger.log_experience(
            execution_id="exec_20260723_003",
            plan_name="Placement Plan",
            goal_name="Python Growth",
            initial_state={"python": 65},
            predicted_state={"python": 75},
            actual_state={"python": 72},
            actions=["Python Project"],
            completed_actions=["Python Project"],
            failed_actions=[],
            skipped_actions=[],
            execution_time=8.0,
            success=True,
        )
        self.assertEqual(experience.prediction_error, 3.0)

    def test_outcome_analysis(self) -> None:
        analyzer = OutcomeAnalyzer()
        experience = {
            "predicted_state": {"python": 78},
            "actual_state": {"python": 74},
            "completed_actions": ["Python Project"],
            "actions": ["Python Project", "DSA Practice"],
            "success": True,
        }
        metrics = analyzer.analyze(experience)

        self.assertIn("prediction_error", metrics)
        self.assertIn("goal_progress", metrics)
        self.assertIn("completion_rate", metrics)
        self.assertIn("success_rate", metrics)
        self.assertIn("confidence_error", metrics)

    def test_execution_linked(self) -> None:
        logger = ExperienceLogger(dataset_path=None)
        experience = logger.log_experience(
            execution_id="exec_20260723_004",
            plan_name="Placement Plan",
            goal_name="Python Growth",
            initial_state={"python": 65},
            predicted_state={"python": 80},
            actual_state={"python": 76},
            actions=["Python Project"],
            completed_actions=["Python Project"],
            failed_actions=[],
            skipped_actions=[],
            execution_time=9.0,
            success=True,
        )
        self.assertEqual(experience.execution_id, "exec_20260723_004")


if __name__ == "__main__":
    unittest.main()
