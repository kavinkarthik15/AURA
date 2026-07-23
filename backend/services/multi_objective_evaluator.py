from typing import Dict, List

from backend.models.goal_state import GoalState
from backend.models.objective_profile import ObjectiveProfile
from backend.models.planning_objectives import PlanningObjectives
from backend.services.digital_twin import LearnedDigitalTwin


class MultiObjectiveEvaluator:
    def __init__(self, digital_twin: LearnedDigitalTwin | None = None) -> None:
        self.digital_twin = digital_twin or LearnedDigitalTwin()

    def evaluate_plan(self, current_state: Dict[str, int], goal_state: GoalState, plan: Dict, profile: ObjectiveProfile | None = None) -> PlanningObjectives:
        simulation = self.digital_twin.simulate_plan(current_state, plan["actions"])
        predicted = simulation.get("predicted_future_state", {})
        python_growth = max(0.0, predicted.get("python", 0) - current_state.get("python", 0))
        dsa_growth = max(0.0, predicted.get("dsa", 0) - current_state.get("dsa", 0))
        project_growth = max(0.0, predicted.get("projects", 0) - current_state.get("projects", 0))
        ml_growth = max(0.0, predicted.get("ml", 0) - current_state.get("ml", 0))

        goal_progress = 0.0
        if goal_state.target_skills:
            progress_values = []
            for skill, target_goal in goal_state.target_skills.items():
                current_value = current_state.get(skill, 0)
                projected_value = predicted.get(skill, current_value)
                target_gap = max(1, target_goal - current_value)
                progress_values.append(max(0, min(1.0, (projected_value - current_value) / target_gap)))
            goal_progress = sum(progress_values) / len(progress_values)

        objectives = PlanningObjectives(
            goal_progress=round(goal_progress, 2),
            python_growth=round(python_growth, 2),
            ml_growth=round(ml_growth, 2),
            dsa_growth=round(dsa_growth, 2),
            project_growth=round(project_growth, 2),
            time_cost=round(max(1.0, len(plan.get("actions", [])) * 1.5), 2),
            difficulty=round(min(1.0, 0.2 + len(plan.get("actions", [])) * 0.1), 2),
            confidence=round(simulation.get("confidence", 0.0), 2),
            energy_cost=round(max(1.0, len(plan.get("actions", [])) * 0.8), 2),
        )
        if profile is not None:
            objectives.profile_score = profile.score(objectives.to_dict())
        return objectives

    def evaluate_plans(self, current_state: Dict[str, int], goal_state: GoalState, plans: List[Dict], profile: ObjectiveProfile | None = None) -> List[Dict]:
        evaluated = []
        for plan in plans:
            objectives = self.evaluate_plan(current_state, goal_state, plan, profile=profile)
            evaluated.append({"plan": plan, "objectives": objectives.to_dict(), "profile_score": getattr(objectives, "profile_score", None)})
        return evaluated
