import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.services.experience_service import experience_service
from backend.services.state_service import state_service


def main() -> None:
    state = state_service.load_state()
    print(f"Python = {state.skills.get('python')}")

    state_service.increment_skill("python", 5)
    print("\nUpdated...\n")

    state_service.save_state()
    reloaded = state_service.load_state()
    print(f"Python = {reloaded.skills.get('python')}")

    experience = {
        "experience_id": "exp_0001",
        "timestamp": datetime(2026, 7, 22, 12, 0, 0),
        "user_id": "user_001",
        "experience_type": "project",
        "state_before": {"python": 60},
        "action": "Complete Python Project",
        "context": {"hours_spent": 15, "stress": 60, "semester": 5},
        "state_after": {"python": 70},
        "outcome_value": 0.8,
    }

    experience_service.add_experience(experience)
    stored_experiences = experience_service.get_all_experiences()

    print("\nExperience Added\n")
    print(f"Total Experiences: {len(stored_experiences)}")
    print("\nAction:")
    print(stored_experiences[-1].action)
    print("\nOutcome:")
    print(stored_experiences[-1].outcome_value)
    print("\nState Delta:")
    print(stored_experiences[-1].state_delta)


if __name__ == "__main__":
    main()
