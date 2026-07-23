from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from sklearn.metrics import mean_absolute_error, mean_squared_error

from backend.ai.transition_model import TransitionModel, load_training_dataset
from backend.services.transition_engine import transition_engine


STATE = {
    "python": 50,
    "machine_learning": 30,
    "dsa": 20,
    "projects": 40,
    "communication": 35,
}
ACTION = "Build Python Project"
ACTION_FAMILY_ALIASES = {
    "build python project": ["build python project", "python project", "complete python project"],
}


def _rule_engine_prediction(state: Dict[str, Any], action: str) -> Dict[str, float]:
    prediction = transition_engine.predict_skill_growth(state, action)
    return {
        "python_growth": float(prediction.get("python", 0.0)),
        "machine_learning_growth": float(prediction.get("machine_learning", 0.0)),
        "dsa_growth": float(prediction.get("dsa", 0.0)),
        "project_growth": float(prediction.get("projects", 0.0)),
    }


def _actual_expected_delta() -> Dict[str, float]:
    dataset = load_training_dataset()
    normalized_action = ACTION.strip().lower()
    accepted_aliases = ACTION_FAMILY_ALIASES.get(normalized_action, [normalized_action])

    matches = [
        record for record in dataset
        if any(alias in record.get("action", "").strip().lower() for alias in accepted_aliases)
    ]

    if not matches:
        return {
            "python_growth": 0.0,
            "machine_learning_growth": 0.0,
            "dsa_growth": 0.0,
            "project_growth": 0.0,
        }

    totals = {
        "python_growth": 0.0,
        "machine_learning_growth": 0.0,
        "dsa_growth": 0.0,
        "project_growth": 0.0,
    }
    for record in matches:
        state_before = record.get("state_before", {})
        state_after = record.get("state_after", {})
        totals["python_growth"] += float(state_after.get("python", 0.0) - state_before.get("python", 0.0))
        totals["machine_learning_growth"] += float(state_after.get("machine_learning", 0.0) - state_before.get("machine_learning", 0.0))
        totals["dsa_growth"] += float(state_after.get("dsa", 0.0) - state_before.get("dsa", 0.0))
        totals["project_growth"] += float(state_after.get("projects", 0.0) - state_before.get("projects", 0.0))

    count = len(matches)
    return {
        "python_growth": round(totals["python_growth"] / count, 4),
        "machine_learning_growth": round(totals["machine_learning_growth"] / count, 4),
        "dsa_growth": round(totals["dsa_growth"] / count, 4),
        "project_growth": round(totals["project_growth"] / count, 4),
    }


def compare_models() -> Dict[str, Any]:
    model = TransitionModel.load_model(Path("backend/ai/saved_models/aura_transition_v1.pkl"))
    ai_prediction = model.predict(STATE, ACTION)
    rule_prediction = _rule_engine_prediction(STATE, ACTION)
    actual = _actual_expected_delta()

    ai_targets = [actual[key] for key in actual]
    ai_pred = [ai_prediction[key] for key in ai_prediction]
    rule_pred = [rule_prediction[key] for key in rule_prediction]

    comparison = {
        "rule_engine_prediction": rule_prediction,
        "ai_model_prediction": ai_prediction,
        "actual_expected_delta": actual,
        "rule_mae": float(mean_absolute_error(ai_targets, rule_pred)),
        "rule_mse": float(mean_squared_error(ai_targets, rule_pred)),
        "ai_mae": float(mean_absolute_error(ai_targets, ai_pred)),
        "ai_mse": float(mean_squared_error(ai_targets, ai_pred)),
    }
    return comparison


if __name__ == "__main__":
    print(compare_models())
