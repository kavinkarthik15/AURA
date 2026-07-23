import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.services.experience_service import experience_service
from backend.services.transition_engine import TransitionEngine


def show_transition_prediction(current_state: dict, action: str) -> None:
    engine = TransitionEngine(experiences=experience_service.get_all_experiences())
    predicted_growth = engine.predict_skill_growth(current_state, action)
    success_probability = engine.predict_success_probability(current_state, action)
    future_state = engine.predict_future_state(current_state, action)

    print("==================================")
    print("AURA TRANSITION REPORT")
    print("==================================")
    print()
    print("Current State:")
    for key, value in current_state.items():
        print(f"{key}: {value}")
    print()
    print("Action:")
    print(action)
    print()
    print("Predicted Growth:")
    for key, value in predicted_growth.items():
        print(f"{key}: +{value}")
    print()
    print("Predicted Future State:")
    for key, value in future_state.items():
        print(f"{key}: {value}")
    print()
    print(f"Success Probability: {success_probability:.2f}")
    print(f"Confidence: {success_probability:.2f}")


if __name__ == "__main__":
    show_transition_prediction({"python": 48}, "Build Python Project")
