from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Dict, Iterable, List

from sklearn.ensemble import RandomForestRegressor

from backend.ai.model_configs import (
    ACTION_ID_MAP,
    FEATURES,
    MODEL_VERSION,
    TARGETS,
    TARGET_ALIASES,
)
from backend.ai.model_errors import ModelNotFoundError


class TransitionModel:
    """Random forest transition model for predicting state growth from state + action."""

    DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "saved_models" / f"aura_transition_{MODEL_VERSION}.pkl"

    def __init__(self, model: RandomForestRegressor | None = None) -> None:
        self.model = model or RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            n_jobs=-1,
        )
        self.feature_names = list(FEATURES)
        self.target_names = list(TARGETS)

    def _normalize_state(self, current_state: Dict[str, Any]) -> Dict[str, float]:
        normalized: Dict[str, float] = {}
        for feature in self.feature_names:
            value = current_state.get(feature, 0)
            if value is None:
                value = 0
            normalized[feature] = float(value)
        return normalized

    def _action_to_id(self, action: str) -> int:
        normalized = action.strip().lower()
        for candidate, action_id in ACTION_ID_MAP.items():
            if normalized == candidate.lower():
                return int(action_id)
        for candidate, action_id in ACTION_ID_MAP.items():
            if candidate.lower() in normalized:
                return int(action_id)
        return 0

    def _build_feature_vector(self, current_state: Dict[str, Any], action: str) -> List[float]:
        normalized_state = self._normalize_state(current_state)
        vector = [normalized_state[feature] for feature in self.feature_names]
        vector.append(float(self._action_to_id(action)))
        return vector

    def _build_target_vector(self, state_before: Dict[str, Any], state_after: Dict[str, Any]) -> List[float]:
        output: List[float] = []
        for target in self.target_names:
            state_key = TARGET_ALIASES[target]
            before_value = float(state_before.get(state_key, state_before.get(state_key.replace("_growth", ""), 0) or 0))
            after_value = float(state_after.get(state_key, state_after.get(state_key.replace("_growth", ""), 0) or 0))
            output.append(after_value - before_value)
        return output

    def _build_training_arrays(self, dataset: Iterable[Dict[str, Any]]) -> tuple[List[List[float]], List[List[float]]]:
        features: List[List[float]] = []
        targets: List[List[float]] = []

        for record in dataset:
            state_before = record.get("state_before", {})
            state_after = record.get("state_after", {})
            action = record.get("action", "")
            features.append(self._build_feature_vector(state_before, action))
            targets.append(self._build_target_vector(state_before, state_after))

        return features, targets

    def train(self, dataset: Iterable[Dict[str, Any]]) -> "TransitionModel":
        X, y = self._build_training_arrays(dataset)
        self.model.fit(X, y)
        return self

    def predict(self, current_state: Dict[str, Any], action: str) -> Dict[str, float]:
        vector = self._build_feature_vector(current_state, action)
        prediction = self.model.predict([vector])[0]
        return {target: float(value) for target, value in zip(self.target_names, prediction)}

    def save_model(self, output_path: Path | None = None) -> Path:
        target_path = output_path or self.DEFAULT_MODEL_PATH
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("wb") as handle:
            pickle.dump(self, handle)
        return target_path

    @classmethod
    def load_model(cls, model_path: Path | None = None) -> "TransitionModel":
        target_path = model_path or cls.DEFAULT_MODEL_PATH
        if not target_path.exists():
            raise ModelNotFoundError(
                f"TransitionModel artifact was not found at {target_path}. "
                "Train the model first or provide a valid model path."
            )
        with target_path.open("rb") as handle:
            return pickle.load(handle)


def load_training_dataset(dataset_path: Path | None = None) -> List[Dict[str, Any]]:
    target_path = dataset_path or Path(__file__).resolve().parents[1] / "data" / "training_data.json"
    with target_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, dict):
        records = payload.get("records", payload.get("data", []))
        return records
    return payload
