from backend.models.goal_state import GoalState
from backend.services.plan_generator import PlanGenerator
from backend.services.plan_evaluator import PlanEvaluator
from backend.services.recommendation_engine import RecommendationEngine

current_state = {"python": 50, "dsa": 30}
goal_state = GoalState(goal="Python Growth", target_skills={"python": 80})
plans = PlanGenerator().generate_candidate_plans(current_state, goal_state)
evaluator = PlanEvaluator()
comparison = evaluator.compare_plans(current_state, goal_state, plans)
sequence = evaluator.digital_twin.simulate_action_sequence(current_state, ["Complete Python Project", "Practice DSA", "Participate in Hackathon"])
recommendation = RecommendationEngine(plan_evaluator=evaluator).recommend_plan(current_state, goal_state, plans)
print("plans", [plan["name"] for plan in plans])
print("comparison", comparison)
print("sequence_final", sequence["final_state"])
print("sequence_history_len", len(sequence["state_history"]))
print("recommendation", recommendation["recommended_plan"])
print("goal_progress", recommendation["evaluation"]["goal_progress"])
