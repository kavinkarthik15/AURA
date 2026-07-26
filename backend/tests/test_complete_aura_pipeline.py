import unittest

from backend.ai.continual_learning import ContinualLearningPipeline
from backend.ai.policy_registry import PolicyRegistry
from backend.ai.research_report import ResearchReportGenerator
from backend.services.beam_search_planner import BeamSearchPlanner
from backend.services.execution_engine import ExecutionEngine
from backend.services.experience_logger import ExperienceLogger
from backend.services.goal_plan_service import GoalPlanService
from backend.services.system_benchmark import SystemBenchmark
from backend.models.goal_state import GoalState


class CompleteAuraPipelineTests(unittest.TestCase):
    def test_complete_pipeline_regression(self) -> None:
        planner = BeamSearchPlanner()
        service = GoalPlanService(beam_search_planner=planner)
        goal_state = GoalState(goal="Placement", target_skills={"python": 50})

        recommendation = service.recommend_goal_plan({"python": 10, "projects": 1}, goal_state)
        self.assertTrue(recommendation["recommended_plan"] or recommendation["best_plan"])

        execution_engine = ExecutionEngine()
        execution_state = execution_engine.start_execution(
            plan_name="plan_1",
            goal_name=goal_state.goal,
            actions=recommendation["recommended_plan"] or recommendation["best_plan"]["actions"],
            confidence=recommendation.get("confidence", 0.0),
        )
        execution_engine.complete_current_action()
        execution_engine.finish_execution()

        logger = ExperienceLogger()
        experience = logger.log_experience(
            execution_id=execution_state.execution_id,
            plan_name=execution_state.plan_name,
            goal_name=execution_state.goal_name,
            initial_state={"python": 10, "projects": 1},
            predicted_state={"python": 20, "projects": 2},
            actual_state={"python": 18, "projects": 2},
            actions=execution_state.pending_actions + execution_state.completed_actions,
            completed_actions=execution_state.completed_actions,
            failed_actions=execution_state.failed_actions,
            skipped_actions=execution_state.skipped_actions,
            execution_time=1.25,
            success=True,
            confidence=execution_state.confidence,
        )
        self.assertTrue(experience.experience_id)

        continual_learning = ContinualLearningPipeline()
        result = continual_learning.run([experience])
        self.assertIn("report", result)

        policy_registry = PolicyRegistry()
        policy_registry.register("policy_v3", "policy_hash", 2, {"top_action_accuracy": 0.9}, accepted=True)
        self.assertEqual(policy_registry.latest()["policy_version"], "policy_v3")

        benchmark = SystemBenchmark()
        metrics = benchmark.evaluate(
            goal_success=0.82,
            planning_accuracy=0.78,
            recommendation_accuracy=0.79,
            policy_accuracy=0.8,
            retrieval_accuracy=0.76,
            reasoning_consistency=0.74,
            counterfactual_quality=0.72,
            execution_success=0.81,
            learning_improvement=0.18,
        )
        self.assertGreater(metrics["overall_intelligence_score"], 0.75)

        report = ResearchReportGenerator().generate_report(
            title="Sprint 11 Report",
            architecture={"planner": "beam_search", "execution": "execution_engine"},
            benchmarks={"overall_intelligence_score": metrics["overall_intelligence_score"]},
            ablation={"hybrid": 0.81},
            performance={"execution_steps": 1},
            improvements=["complete pipeline regression"],
            future_work=["expand benchmark coverage"],
        )
        self.assertIn("Sprint 11 Report", report)


if __name__ == "__main__":
    unittest.main()
