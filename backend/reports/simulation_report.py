import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.services.simulation_engine import SimulationEngine


def show_simulation_report(current_state: dict, actions: list[str]) -> None:
    engine = SimulationEngine()
    result = engine.simulate_plan(current_state, actions)
    print("==================================")
    print("AURA SIMULATION REPORT")
    print("==================================")
    print()
    print("Input State")
    for skill, value in current_state.items():
        print(f"{skill}: {value}")
    print()
    print("Planned Actions")
    for action in actions:
        print(f"- {action}")
    print()
    print("Predicted Future State")
    for skill, value in result["predicted_future_state"].items():
        print(f"{skill}: {value}")
    print()
    print(f"Confidence: {result['success_probability']:.2f}")
    print(f"Expected Outcome: {result['expected_outcome']}")
    print(f"Summary: {result['summary']}")


if __name__ == "__main__":
    show_simulation_report({"python": 50}, ["Complete Python Project", "Complete DSA Course"])
