import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from backend.services.experience_service import ExperienceService


class ExperienceServiceTests(unittest.TestCase):
    def test_add_and_reload_experience(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "experiences.json"
            service = ExperienceService(file_path=file_path)

            expected_timestamp = datetime(2026, 7, 22, 12, 0, 0)
            experience = {
                "experience_id": "exp_0001",
                "timestamp": expected_timestamp,
                "user_id": "user_001",
                "experience_type": "project",
                "state_before": {"python": 60},
                "action": "Complete Python Project",
                "context": {"hours_spent": 15, "stress": 60, "semester": 5},
                "state_after": {"python": 70},
                "outcome_value": 0.8,
            }

            service.add_experience(experience)
            reloaded = service.load_experiences()

            self.assertEqual(len(reloaded), 1)
            self.assertEqual(reloaded[0].experience_id, "exp_0001")
            self.assertEqual(reloaded[0].timestamp, expected_timestamp)
            self.assertEqual(reloaded[0].user_id, "user_001")
            self.assertEqual(reloaded[0].experience_type, "project")
            self.assertEqual(reloaded[0].action, "Complete Python Project")
            self.assertEqual(reloaded[0].state_delta, {"python": 10})
            self.assertAlmostEqual(reloaded[0].outcome_value, 0.8)


if __name__ == "__main__":
    unittest.main()
