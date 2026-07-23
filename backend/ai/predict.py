from __future__ import annotations

from typing import Any, Dict

from backend.ai.transition_model import TransitionModel


def predict(current_state: Dict[str, Any], action: str) -> Dict[str, float]:
    model = TransitionModel.load_model()
    return model.predict(current_state, action)


if __name__ == "__main__":
    sample_state = {
        "python": 50,
        "machine_learning": 30,
        "dsa": 20,
        "projects": 40,
        "communication": 35,
    }
    sample_action = "Build Python Project"
    print(predict(sample_state, sample_action))
