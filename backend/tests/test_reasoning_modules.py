import unittest
from types import SimpleNamespace

from backend.ai.causal_pattern_miner import CausalPatternMiner
from backend.ai.contradiction_detector import ContradictionDetector
from backend.ai.counterfactual_planner import CounterfactualPlanner
from backend.ai.evaluate_reasoning import ReasoningEvaluator
from backend.ai.experience_clusters import ExperienceClusterer
from backend.ai.experience_reasoner import ExperienceReasoner
from backend.ai.explanation_feedback import ExplanationFeedbackLearner
from backend.ai.multi_hop_reasoner import MultiHopReasoner
from backend.ai.plan_explainer import PlanExplainer
from backend.ai.reasoning_graph import ReasoningGraphBuilder
from backend.ai.reasoning_regression_dashboard import ReasoningRegressionDashboard
from backend.ai.experience_retriever import ExperienceRetriever
from backend.ai.reasoning_registry import ReasoningRegistry
from backend.models.goal_state import GoalState
from backend.services.beam_search_planner import BeamSearchPlanner
from backend.services.goal_plan_service import GoalPlanService


class DummyRetriever(ExperienceRetriever):
    def retrieve(self, current_state, goal, next_actions):
        return {
            "retrieval_time_ms": 1.0,
            "matches": [
                SimpleNamespace(
                    experience_id="exp-1",
                    similarity=0.88,
                    success=True,
                    reason="Worked well",
                    completed_actions=["Revision"],
                    actions=["Python Project"],
                    goal_completion=0.75,
                )
            ],
        }

    def compute_adaptive_weight(self, policy_confidence, retrieval_confidence, goal_type):
        return 0.5

    def get_analytics_summary(self):
        return {"hits": 1}


class ReasoningModuleTests(unittest.TestCase):
    def test_reasoning_pipeline(self) -> None:
        reasoner = ExperienceReasoner()
        explainer = PlanExplainer()
        counterfactuals = CounterfactualPlanner()
        contradictions = ContradictionDetector()
        clusters = ExperienceClusterer()
        miner = CausalPatternMiner()
        evaluator = ReasoningEvaluator()
        registry = ReasoningRegistry()

        experiences = [
            {
                "goal_name": "Placement",
                "actions": ["Python Project"],
                "completed_actions": ["Revision"],
                "success": True,
            },
            {
                "goal_name": "Placement",
                "actions": ["Python Project"],
                "completed_actions": ["Revision"],
                "success": False,
            },
        ]
        reasoning = reasoner.analyze(experiences)
        explanation = explainer.explain(
            ["Python Project"], experiences, confidence=reasoning["confidence"], digital_twin_confidence=0.81
        )
        variants = counterfactuals.generate(["Python Project"], [["Revision"]])
        contradiction_report = contradictions.detect(experiences)
        clustered = clusters.cluster(experiences)
        causal_patterns = miner.mine(experiences)
        metrics = evaluator.evaluate(explanation, reasoning, variants, contradiction_report)
        record = registry.register("reasoning_v1", metrics)

        self.assertGreater(reasoning["confidence"], 0.0)
        self.assertTrue(explanation["summary"])
        self.assertTrue(variants)
        self.assertTrue(contradiction_report["detected"])
        self.assertIn("Placement", clustered)
        self.assertTrue(causal_patterns)
        self.assertGreater(metrics["explanation_quality"], 0.0)
        self.assertEqual(record["version"], "reasoning_v1")

    def test_reasoning_metadata_is_exposed_by_planner_and_service(self) -> None:
        planner = BeamSearchPlanner(retriever=DummyRetriever())
        goal_state = GoalState(goal="Placement", target_skills={"python": 50})
        search_result = planner.search({"python": 10, "projects": 1}, goal_state, beam_width=2, max_depth=1)

        self.assertIn("reasoning_confidence", search_result)
        self.assertIn("counterfactual_comparison", search_result)
        self.assertIn("reasoning_trace", search_result)
        self.assertTrue(search_result["consistency_status"]["consistent"])

        service = GoalPlanService(beam_search_planner=planner)
        recommendation = service.recommend_goal_plan({"python": 10, "projects": 1}, goal_state)

        self.assertIn("reasoning_metadata", recommendation)
        self.assertIn("reasoning_confidence", recommendation["reasoning_metadata"])
        self.assertIn("consistent", recommendation["reasoning_metadata"]["consistency_status"])

    def test_feedback_learning_graph_and_multi_hop_reasoning(self) -> None:
        learner = ExplanationFeedbackLearner()
        feedback = learner.record_feedback("exp-1", "unclear", 0.2)
        self.assertEqual(feedback["feedback_count"], 1)
        self.assertLess(feedback["current_weight"], 1.0)

        graph_builder = ReasoningGraphBuilder()
        graph = graph_builder.build(
            [
                {
                    "goal_name": "Placement",
                    "actions": ["Python Project"],
                    "completed_actions": ["Revision"],
                    "success": True,
                },
                {
                    "goal_name": "Placement",
                    "actions": ["Revision"],
                    "completed_actions": ["Mock Interview"],
                    "success": True,
                },
            ]
        )
        self.assertGreater(graph["node_count"], 0)
        self.assertGreater(graph["edge_count"], 0)

        reasoner = MultiHopReasoner()
        chain = reasoner.chain_experiences(
            [
                {
                    "goal_name": "Placement",
                    "actions": ["Python Project"],
                    "completed_actions": ["Revision"],
                    "success": True,
                },
                {
                    "goal_name": "Placement",
                    "actions": ["Revision"],
                    "completed_actions": ["Mock Interview"],
                    "success": True,
                },
            ],
            target_action="Mock Interview",
        )
        self.assertGreater(chain["hop_count"], 0)
        self.assertIn("Mock Interview", chain["selected_actions"])

        dashboard = ReasoningRegressionDashboard()
        summary = dashboard.summarize(
            [{"accuracy": 0.8, "confidence": 0.7}, {"accuracy": 0.9, "confidence": 0.8}],
            accuracy=0.85,
            confidence_calibration=0.82,
            contradiction_rate=0.1,
            benchmark_trend=0.15,
        )
        self.assertIn("accuracy", summary)
        self.assertIn("trend", summary)


if __name__ == "__main__":
    unittest.main()
