import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.models.goal_state import GoalState
from backend.services.goal_planner import GoalPlanner


def show_goal_report(current_state: dict, goal_state: GoalState) -> None:
    planner = GoalPlanner()
    plan = planner.create_plan(current_state, goal_state)

    print("==================================")
    print("AURA GOAL REPORT")
    print("==================================")
    print()
    print("Current State")
    for skill, value in current_state.items():
        print(f"{skill}: {value}")
    print()
    print("Goal State")
    for skill, value in goal_state.target_skills.items():
        print(f"{skill}: {value}")
    print()
    print("Recommended Actions")
    for index, action in enumerate(plan["recommended_actions"], start=1):
        print(f"{index}. {action}")
    print()
    print(f"Estimated Steps: {plan['estimated_steps']}")
    print(f"Goal Success Probability: {plan['success_probability'] * 100:.0f}%")


if __name__ == "__main__":
    show_goal_report({"python": 55, "dsa": 40, "ml": 30}, GoalState(goal="Career Growth", target_skills={"python": 80, "dsa": 70, "ml": 60}))
