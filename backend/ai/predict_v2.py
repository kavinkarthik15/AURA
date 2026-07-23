from __future__ import annotations

from typing import Any, Dict, List

from backend.ai.sequence_transition_model import SequenceTransitionModel


def predict(current_state: Dict[str, Any], history: List[str], action: str) -> Dict[str, float]:
    model = SequenceTransitionModel.load_model()
    return model.predict(current_state, history, action)


if __name__ == "__main__":
    sample_state = {
        "python": 50,
        "machine_learning": 30,
        "dsa": 20,
        "projects": 40,
        "communication": 35,
    }
    sample_history = ["Python Course", "Python Project"]
    sample_action = "Hackathon"
    print(predict(sample_state, sample_history, sample_action))
