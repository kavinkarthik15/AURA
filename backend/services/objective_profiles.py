from backend.models.objective_profile import ObjectiveProfile


def build_default_profiles() -> dict[str, ObjectiveProfile]:
    return {
        "career_focused": ObjectiveProfile(
            name="CareerFocusedProfile",
            weights={
                "python_growth": 0.35,
                "project_growth": 0.25,
                "goal_progress": 0.30,
                "difficulty": -0.05,
                "time_cost": -0.05,
            },
        ),
        "balanced_learning": ObjectiveProfile(
            name="BalancedLearningProfile",
            weights={
                "python_growth": 0.20,
                "dsa_growth": 0.20,
                "project_growth": 0.20,
                "confidence": 0.20,
                "goal_progress": 0.20,
            },
        ),
        "placement": ObjectiveProfile(
            name="PlacementProfile",
            weights={
                "dsa_growth": 0.35,
                "python_growth": 0.20,
                "project_growth": 0.15,
                "confidence": 0.15,
                "goal_progress": 0.15,
            },
        ),
    }
