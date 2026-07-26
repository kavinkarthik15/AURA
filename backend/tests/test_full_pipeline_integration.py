import tempfile
import unittest
from pathlib import Path

from backend.ai.continual_learning import ContinualLearningPipeline
from backend.ai.policy_dataset import PolicyDatasetBuilder
from backend.ai.policy_registry import PolicyRegistry
from backend.ai.policy_trainer import PolicyTrainer
from backend.models.experience_log import ExperienceLog
from backend.models.goal_state import GoalState
from backend.services.execution_engine import ExecutionEngine
from backend.services.experience_logger import ExperienceLogger
from backend.services.goal_plan_service import GoalPlanService


class FullPipelineIntegrationTests(unittest.TestCase):
    def test_goal_to_policy_update_pipeline(self) -> None:
        current_state = {"python": 50, "dsa": 20, "projects": 10}
        goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})
        recommendation = GoalPlanService().recommend_goal_plan(current_state, goal_state)
        actions = recommendation["best_plan"]["actions"]
        self.assertTrue(actions)

        execution = ExecutionEngine()
        execution_state = execution.start_execution("Plan 1", goal_state.goal, actions, confidence=recommendation["confidence"])
        while execution.next_action():
            execution.complete_current_action()
        execution_state = execution.finish_execution()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)
            logger = ExperienceLogger(dataset_path=temp_path / "experience_dataset.json")
            experience = logger.log_experience(
                execution_id=execution_state.execution_id,
                plan_name=execution_state.plan_name,
                goal_name=execution_state.goal_name,
                initial_state=current_state,
                predicted_state=recommendation["expected_future_state"],
                actual_state={"python": 55, "dsa": 25, "projects": 11},
                actions=actions,
                completed_actions=execution_state.completed_actions,
                failed_actions=execution_state.failed_actions,
                skipped_actions=execution_state.skipped_actions,
                execution_time=0.01,
                success=True,
                confidence=execution_state.confidence,
            )

            learning = ContinualLearningPipeline()
            learning.registry = learning.registry.__class__(registry_path=temp_path / "model_registry.json")
            learning.trainer.registry = learning.registry
            learning.trainer.output_dir = temp_path / "models"
            result = learning.run([experience], base_dataset=[])

            policy_samples = PolicyDatasetBuilder().build_samples([experience])
            policy_result = PolicyTrainer().train(policy_samples, output_path=temp_path / "policy.json")
            policy_registry = PolicyRegistry(temp_path / "policy_registry.json")
            policy_record = policy_registry.register(
                policy_result["policy_version"],
                policy_result["dataset_hash"],
                policy_result["sample_count"],
                {"pipeline": "integration"},
            )

            self.assertTrue(result["candidate"]["model_path"])
            self.assertIn("report", result)
            self.assertTrue(policy_record["policy_version"])
            self.assertTrue((temp_path / "policy.json").exists())


if __name__ == "__main__":
    unittest.main()
